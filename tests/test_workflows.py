import pytest
from core.models import ScanRequest
from core.orchestrator import Orchestrator


def test_workflow_execution():
    orchestrator = Orchestrator()
    request = ScanRequest(
        id="test-req-1",
        target="http://example.com",
        requested_agents=["nmap"],
        priority=1,
        workflow_id="wf-1"
    )
    results = orchestrator.run_scan(request)
    assert isinstance(results, list)
    assert all(hasattr(r, "agent") for r in results)
    assert any(r.agent == "nmap" for r in results)
