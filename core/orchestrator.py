import asyncio

import os
import re
import uuid
from datetime import datetime

# import random
from typing import List

# pylint: disable=too-complex

from agents.nikto_agent import NiktoAgent
from agents.nmap_agent import NmapAgent
from agents.sqlmap_agent import SqlmapAgent
from core.decision_engine import DecisionEngine
from core.event_queue import EventQueue
from core.job_manager import JobManager, KubernetesUnavailableError
from core.models import (
    K8sJobRecord,
    OrchestrationEvent,
    ScanRequest,
    ScanResult,
    Workflow,
    WorkflowStep,
)
from core.storage import Storage


class Orchestrator:  # pylint: disable=too-few-public-methods
    def __init__(self, *, storage: Storage = None, job_manager: JobManager = None):
        self.agents = {
            "nmap": NmapAgent(),
            "nikto": NiktoAgent(),
            "sqlmap": SqlmapAgent(),
        }
        self.queue = EventQueue()
        self.decision_engine = DecisionEngine()
        self.storage = storage or Storage()
        self.max_retries = 2
        self.concurrent_limit = 3
        self.semaphore = asyncio.Semaphore(self.concurrent_limit)

        self.job_manager = job_manager or JobManager(namespace=os.getenv("K8S_NAMESPACE"))
        self.use_k8s_jobs = os.getenv("USE_K8S_JOBS", "0") == "1"
        self.k8s_job_agents = {
            a.strip() for a in os.getenv("K8S_JOB_AGENTS", "").split(",") if a.strip()
        }
        self.k8s_job_image = os.getenv("K8S_JOB_IMAGE", "security-agency/app:latest")
        self.k8s_strict = os.getenv("K8S_STRICT", "0") == "1"

    def _now_iso(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _safe_job_name(self, raw: str) -> str:
        # DNS-1123 label: lowercase alphanumerics + '-' up to 63 chars.
        name = re.sub(r"[^a-z0-9-]+", "-", raw.lower())
        name = re.sub(r"-+", "-", name).strip("-")
        return name[:63] if len(name) > 63 else name

    def _should_run_as_k8s_job(self, request: ScanRequest, agent_name: str) -> bool:
        if not self.use_k8s_jobs:
            return False
        if getattr(request, "execution_mode", None) == "k8s":
            return True
        return agent_name in self.k8s_job_agents

    async def run_scan_async(
        self, request: ScanRequest
    ) -> List[ScanResult]:  # pylint: disable=too-complex,too-many-branches,too-many-statements
        """
        Asynchronous scan execution with scheduling, retries, and parallelism.
        """
        workflow = Workflow(
            id=request.workflow_id or request.id,
            name=f"Workflow-{request.id}",
            steps=[],
            context={},
        )
        self.storage.save_workflow(workflow)

        # Initial steps
        initial_steps = [
            WorkflowStep(
                id=f"{request.id}-{agent}",
                workflow_id=workflow.id,
                agent=agent,
                input={"target": request.target},
                status="pending",
                dependencies=[],
            )
            for agent in (request.requested_agents or self.agents.keys())
        ]

        for step in initial_steps:
            workflow.steps.append(step)
            self.queue.publish(
                OrchestrationEvent(
                    id=step.id, type="scan_started", payload={"step": step.__dict__}
                )
            )

        results: List[ScanResult] = []
        self.storage.save_scan_request(request)

        pending_tasks: set = set()

        async def execute_step(step: WorkflowStep, retries: int = 0):
            async with self.semaphore:
                agent = self.agents.get(step.agent)
                if not agent:
                    return
                try:
                    target = step.input["target"]

                    if self._should_run_as_k8s_job(request, step.agent):
                        # Schedule a Kubernetes Job and return immediately.
                        job_id = str(uuid.uuid4())
                        job_name = self._safe_job_name(
                            f"sa-{step.agent}-{request.id}-{int(datetime.utcnow().timestamp())}"
                        )

                        job_record = K8sJobRecord(
                            id=job_id,
                            request_id=request.id,
                            agent=step.agent,
                            target=target,
                            k8s_job_name=job_name,
                            namespace=self.job_manager.namespace,
                            status="pending",
                            created_at=self._now_iso(),
                            metadata={"mode": "k8s_job"},
                        )

                        try:
                            self.storage.save_k8s_job(job_record)
                            self.job_manager.create_job(
                                job_name=job_name,
                                image=self.k8s_job_image,
                                command=["python", "-m", "core.k8s_job_runner"],
                                args=[
                                    "--agent",
                                    step.agent,
                                    "--target",
                                    target,
                                    "--request-id",
                                    request.id,
                                ],
                                env={
                                    "REQUEST_ID": request.id,
                                    "AGENT": step.agent,
                                    "TARGET": target,
                                },
                                labels={
                                    "app": "security-agency",
                                    "scan-request-id": self._safe_job_name(request.id),
                                    "agent": self._safe_job_name(step.agent),
                                },
                            )
                        except KubernetesUnavailableError as e:
                            # Either fail (strict) or fall back to local.
                            if self.k8s_strict or getattr(request, "execution_mode", None) == "k8s":
                                failed = ScanResult(
                                    id=f"{step.agent}-job-{job_id}",
                                    request_id=request.id,
                                    agent=step.agent,
                                    status="failed",
                                    output={"stdout": ""},
                                    analysis=None,
                                    metadata={"error": str(e), "mode": "k8s_job"},
                                )
                                results.append(failed)
                                self.storage.save_scan_result(failed)
                                self.queue.publish(
                                    OrchestrationEvent(
                                        id=step.id,
                                        type="scan_failed",
                                        payload={"error": str(e)},
                                    )
                                )
                                return
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            # Scheduling failed (API error, RBAC, etc). Avoid retries creating multiple jobs.
                            self.storage.update_k8s_job_status(
                                job_id,
                                "failed",
                                completed_at=self._now_iso(),
                                error_message=str(e),
                            )
                            if self.k8s_strict or getattr(request, "execution_mode", None) == "k8s":
                                failed = ScanResult(
                                    id=f"{step.agent}-job-{job_id}",
                                    request_id=request.id,
                                    agent=step.agent,
                                    status="failed",
                                    output={"stdout": ""},
                                    analysis=None,
                                    metadata={
                                        "job_id": job_id,
                                        "k8s_job_name": job_name,
                                        "namespace": self.job_manager.namespace,
                                        "error": str(e),
                                        "mode": "k8s_job",
                                    },
                                )
                                results.append(failed)
                                self.storage.save_scan_result(failed)
                                self.queue.publish(
                                    OrchestrationEvent(
                                        id=step.id,
                                        type="scan_failed",
                                        payload={"error": str(e)},
                                    )
                                )
                                return

                        # Scheduled successfully.
                        scheduled = ScanResult(
                            id=f"{step.agent}-job-{job_id}",
                            request_id=request.id,
                            agent=step.agent,
                            status="scheduled",
                            output={"stdout": ""},
                            analysis=None,
                            metadata={
                                "job_id": job_id,
                                "k8s_job_name": job_name,
                                "namespace": self.job_manager.namespace,
                            },
                        )
                        results.append(scheduled)
                        self.storage.save_scan_result(scheduled)
                        self.queue.publish(
                            OrchestrationEvent(
                                id=step.id,
                                type="scan_completed",
                                payload={"result": scheduled.__dict__},
                            )
                        )
                        return

                    # Default: local async execution.
                    result = await agent.run_async(target, request.id)
                    results.append(result)
                    self.storage.save_scan_result(result)
                    self.queue.publish(
                        OrchestrationEvent(
                            id=step.id,
                            type="scan_completed",
                            payload={"result": result.__dict__},
                        )
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    if retries < self.max_retries:
                        await execute_step(step, retries + 1)
                    else:
                        self.queue.publish(
                            OrchestrationEvent(
                                id=step.id,
                                type="scan_failed",
                                payload={"error": str(e)},
                            )
                        )

        # Process until there are no more queued events *and* no running tasks.
        while self.queue.size() > 0 or pending_tasks:
            # If we're temporarily out of events, wait for a running task to finish
            # (it will typically publish scan_completed / scan_failed events).
            if self.queue.size() == 0 and pending_tasks:
                done, pending = await asyncio.wait(
                    pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                pending_tasks = pending
                # Loop back to consume any events published by completed tasks.
                continue

            event = self.queue.consume()
            if not event:
                # Avoid tight loop if the queue is momentarily empty.
                await asyncio.sleep(0)
                continue

            if event.type == "scan_started":
                step_data = event.payload["step"]
                step = WorkflowStep(**step_data)
                task = asyncio.create_task(execute_step(step))
                pending_tasks.add(task)

            elif event.type == "scan_completed":
                decision = self.decision_engine.decide_next_steps(workflow, results)
                for next_step in decision.next_steps:
                    self.queue.publish(
                        OrchestrationEvent(
                            id=next_step.id,
                            type="scan_started",
                            payload={"step": next_step.__dict__},
                        )
                    )

            elif event.type == "scan_failed":
                # Failure is terminal for that step; currently we don't enqueue additional steps.
                # Hook: future versions could decide escalation/retry workflows here.
                continue

        return results
