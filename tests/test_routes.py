import json
import os

import pytest

os.environ["TESTING"] = "1"
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Security Agency" in response.data


def test_scan_route_invalid(client):
    response = client.post("/scan", json={})
    assert response.status_code == 400
    assert b"Invalid request" in response.data


def test_scan_route_valid(monkeypatch, client):
    async def fake_run_scan_async(self, scan_request):
        class Result:
            def __init__(self):
                self.agent = "nmap"
                self.output = "scan complete"

        return [Result()]

    monkeypatch.setattr(
        "core.orchestrator.Orchestrator.run_scan_async", fake_run_scan_async
    )

    response = client.post(
        "/scan", json={"target": "http://example.com", "agents": ["nmap"]}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data[0]["agent"] == "nmap"


def test_request_route(client):
    response = client.post(
        "/request", json={"webAddress": "http://example.com", "notes": "test"}
    )
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "Processing request" in body
    assert "Target: http://example.com" in body


def test_recommendations_route_success(monkeypatch, client):
    async def fake_generate(self, scan_results):
        return {"status": "success", "recommendations": [{"id": 1, "action": "fix"}]}

    monkeypatch.setattr(
        "core.recommendation_engine.RecommendationEngine.generate_recommendations",
        fake_generate,
    )

    response = client.post(
        "/recommendations", json={"scan_results": [{"agent": "nmap"}]}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "recommendations" in data


def test_recommendations_route_invalid(client):
    response = client.post("/recommendations", json={})
    assert response.status_code == 400
    assert b"Invalid request" in response.data
