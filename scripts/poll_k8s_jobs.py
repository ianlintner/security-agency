"""One-shot poller suitable for running as a Kubernetes CronJob.

It refreshes status for any Storage-tracked jobs in (pending|running).

Usage:
  python scripts/poll_k8s_jobs.py

Environment:
  DATABASE_URL   - database connection string
  K8S_NAMESPACE  - namespace where jobs run
"""

from datetime import datetime

from core.job_manager import JobManager, KubernetesUnavailableError
from core.storage import Storage


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def main() -> int:
    storage = Storage()
    job_manager = JobManager()

    if not job_manager.enabled:
        raise KubernetesUnavailableError(
            "Kubernetes job execution is not available; poller cannot run."
        )

    active = storage.list_active_k8s_jobs(limit=500)
    updated = 0

    for job in active:
        status = job_manager.get_job_status(job["k8s_job_name"]).value
        if status != job.get("status"):
            completed_at = _now_iso() if status in ("succeeded", "failed", "cancelled") else None
            storage.update_k8s_job_status(job["id"], status, completed_at=completed_at)
            updated += 1

    print(f"polled={len(active)} updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
