import os

import pytest

os.environ["TESTING"] = "1"

from app import app, orchestrator, storage  # pylint: disable=wrong-import-position


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_jobs_list_empty(client):
    resp = client.get("/jobs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_scan_k8s_execution_schedules_job(monkeypatch, client):
    # Force orchestrator into k8s mode for this test without requiring real kube config.
    orchestrator.use_k8s_jobs = True
    orchestrator.k8s_job_agents = {"nmap"}

    class FakeJobManager:
        namespace = "default"

        def create_job(self, **kwargs):
            # Simulate successful scheduling.
            return None

    orchestrator.job_manager = FakeJobManager()

    resp = client.post(
        "/scan",
        json={
            "id": "req-k8s-1",
            "target": "http://example.com",
            "agents": ["nmap"],
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data and data[0]["status"] == "scheduled"
    assert "metadata" in data[0]
    assert "job_id" in data[0]["metadata"]

    job_id = data[0]["metadata"]["job_id"]

    # Verify job record persisted.
    job = storage.get_k8s_job(job_id)
    assert job is not None
    assert job["request_id"] == "req-k8s-1"
    assert job["agent"] == "nmap"

    # GET /jobs/<id> should return persisted job.
    job_resp = client.get(f"/jobs/{job_id}")
    assert job_resp.status_code == 200
    job_data = job_resp.get_json()
    assert job_data["id"] == job_id
