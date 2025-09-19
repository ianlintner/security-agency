import os
import sys

import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import os

os.environ["TESTING"] = "1"
from app import app


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_scan_invalid_request(client):
    response = client.post("/scan", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_scan_with_unknown_agent(client):
    response = client.post(
        "/scan", json={"target": "http://example.com", "agents": ["unknown"]}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    if data:  # if orchestrator returns results
        assert isinstance(data[0], dict)
        assert "status" in data[0] or "agent" in data[0] or "output" in data[0]
