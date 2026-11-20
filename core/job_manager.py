import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.models import K8sJobStatus


class KubernetesUnavailableError(RuntimeError):
    """Raised when Kubernetes client/config is unavailable but k8s mode is requested."""


@dataclass
class JobCreateResult:
    job_name: str
    namespace: str


class JobManager:
    """Thin wrapper around the Kubernetes Batch API for Job-based executions.

    This class is intentionally defensive:
    - If the kubernetes Python client isn't installed, it can still be imported.
    - If kubeconfig/in-cluster config can't be loaded, it fails with a clear error.

    The orchestrator/API can treat this as an optional capability.
    """

    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or os.getenv("K8S_NAMESPACE", "default")
        self._enabled = False
        self._batch_v1 = None
        self._core_v1 = None

        try:
            # Lazy import so unit tests and local runs don't require the dependency.
            from kubernetes import client, config  # type: ignore

            try:
                config.load_incluster_config()
            except Exception:  # pylint: disable=broad-exception-caught
                # Local dev.
                config.load_kube_config()

            self._batch_v1 = client.BatchV1Api()
            self._core_v1 = client.CoreV1Api()
            self._client = client
            self._enabled = True
        except Exception:  # pylint: disable=broad-exception-caught
            # Either dependency missing or config missing.
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise KubernetesUnavailableError(
                "Kubernetes job execution is not available. Install the 'kubernetes' package "
                "and ensure kubeconfig/in-cluster config is configured."
            )

    def create_job(
        self,
        *,
        job_name: str,
        image: str,
        command: Optional[List[str]] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        backoff_limit: int = 1,
        ttl_seconds_after_finished: int = 3600,
        active_deadline_seconds: Optional[int] = None,
        cpu_request: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        memory_request: Optional[str] = None,
        memory_limit: Optional[str] = None,
    ) -> JobCreateResult:
        self._require_enabled()

        client = self._client

        env_list = []
        if env:
            for k, v in env.items():
                env_list.append(client.V1EnvVar(name=k, value=v))

        resources = None
        if any([cpu_request, cpu_limit, memory_request, memory_limit]):
            resources = client.V1ResourceRequirements(
                requests={
                    **({"cpu": cpu_request} if cpu_request else {}),
                    **({"memory": memory_request} if memory_request else {}),
                },
                limits={
                    **({"cpu": cpu_limit} if cpu_limit else {}),
                    **({"memory": memory_limit} if memory_limit else {}),
                },
            )

        container = client.V1Container(
            name="scan",
            image=image,
            command=command,
            args=args,
            env=env_list,
            resources=resources,
        )

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels=labels, annotations=annotations),
            spec=client.V1PodSpec(restart_policy="Never", containers=[container]),
        )

        spec = client.V1JobSpec(
            template=template,
            backoff_limit=backoff_limit,
            ttl_seconds_after_finished=ttl_seconds_after_finished,
            active_deadline_seconds=active_deadline_seconds,
        )

        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=job_name, labels=labels, annotations=annotations),
            spec=spec,
        )

        self._batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        return JobCreateResult(job_name=job_name, namespace=self.namespace)

    def get_job_status(self, job_name: str) -> K8sJobStatus:
        self._require_enabled()

        try:
            job = self._batch_v1.read_namespaced_job(name=job_name, namespace=self.namespace)
        except Exception:  # pylint: disable=broad-exception-caught
            return K8sJobStatus.UNKNOWN

        status = getattr(job, "status", None)
        if not status:
            return K8sJobStatus.UNKNOWN

        if getattr(status, "active", 0):
            return K8sJobStatus.RUNNING

        if getattr(status, "succeeded", 0):
            return K8sJobStatus.SUCCEEDED

        if getattr(status, "failed", 0):
            return K8sJobStatus.FAILED

        return K8sJobStatus.PENDING

    def _find_job_pods(self, job_name: str) -> List[str]:
        self._require_enabled()
        label_selector = f"job-name={job_name}"
        pods = self._core_v1.list_namespaced_pod(namespace=self.namespace, label_selector=label_selector)
        return [p.metadata.name for p in pods.items if p and p.metadata and p.metadata.name]

    def get_job_logs(self, job_name: str, tail_lines: int = 2000) -> str:
        self._require_enabled()

        pod_names = self._find_job_pods(job_name)
        if not pod_names:
            return ""

        # Prefer the newest pod (last in list is usually fine; be defensive).
        pod_name = pod_names[-1]
        try:
            return self._core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.namespace,
                tail_lines=tail_lines,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            return ""

    def delete_job(self, job_name: str, cascade: bool = True) -> None:
        self._require_enabled()

        propagation_policy = "Foreground" if cascade else "Orphan"
        try:
            self._batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                propagation_policy=propagation_policy,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            return

    def wait_for_completion(
        self,
        job_name: str,
        timeout_seconds: int = 600,
        poll_interval_seconds: float = 2.0,
    ) -> Tuple[K8sJobStatus, float]:
        """Best-effort helper for tests/scripts."""
        self._require_enabled()

        start = time.time()
        while True:
            status = self.get_job_status(job_name)
            if status in (K8sJobStatus.SUCCEEDED, K8sJobStatus.FAILED, K8sJobStatus.CANCELLED):
                return status, time.time() - start

            if time.time() - start >= timeout_seconds:
                return K8sJobStatus.UNKNOWN, time.time() - start

            time.sleep(poll_interval_seconds)
