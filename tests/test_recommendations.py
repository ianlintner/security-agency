import asyncio

import pytest

from core.decision_engine import DecisionEngine
from core.recommendation_engine import RecommendationEngine


class DummyDecisionEngine(DecisionEngine):
    async def process(self, input_payload):
        return {
            "recommendations": [
                {"id": 1, "action": "Patch vulnerable software"},
                {"id": 2, "action": "Update firewall rules"},
            ],
            "prioritized_vulnerabilities": ["CVE-2025-1234", "CVE-2025-5678"],
        }


def test_generate_recommendations_success():
    engine = RecommendationEngine(DummyDecisionEngine())
    scan_results = [{"agent": "nmap", "result": "open ports found"}]
    response = asyncio.run(engine.generate_recommendations(scan_results))
    assert response["status"] == "success"
    assert "recommendations" in response
    assert len(response["recommendations"]) == 2
    assert "prioritized_vulnerabilities" in response


def test_generate_recommendations_error(monkeypatch):
    class FailingDecisionEngine(DecisionEngine):
        async def process(self, input_payload):
            raise Exception("LLM error")

    engine = RecommendationEngine(FailingDecisionEngine())
    scan_results = [{"agent": "nikto", "result": "vulnerabilities found"}]
    response = asyncio.run(engine.generate_recommendations(scan_results))
    assert response["status"] == "error"
    assert "message" in response
