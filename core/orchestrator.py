import asyncio

# import random
from typing import List

# pylint: disable=too-complex

from agents.nikto_agent import NiktoAgent
from agents.nmap_agent import NmapAgent
from agents.sqlmap_agent import SqlmapAgent
from core.decision_engine import DecisionEngine
from core.event_queue import EventQueue
from core.models import (
    OrchestrationEvent,
    ScanRequest,
    ScanResult,
    Workflow,
    WorkflowStep,
)
from core.storage import Storage


class Orchestrator:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.agents = {
            "nmap": NmapAgent(),
            "nikto": NiktoAgent(),
            "sqlmap": SqlmapAgent(),
        }
        self.queue = EventQueue()
        self.decision_engine = DecisionEngine()
        self.storage = Storage()
        self.max_retries = 2
        self.concurrent_limit = 3
        self.semaphore = asyncio.Semaphore(self.concurrent_limit)

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

        async def execute_step(step: WorkflowStep, retries: int = 0):
            async with self.semaphore:
                agent = self.agents.get(step.agent)
                if not agent:
                    return
                try:
                    result = await agent.run_async(step.input["target"])
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

        while self.queue.size() > 0:
            event = self.queue.consume()
            if not event:
                continue

            if event.type == "scan_started":
                step_data = event.payload["step"]
                step = WorkflowStep(**step_data)
                asyncio.create_task(execute_step(step))

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

        return results
