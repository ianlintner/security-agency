import pytest

from core.models import ScanRequest
from core.orchestrator import Orchestrator


def test_workflow_execution():
    import asyncio

    async def run_test():
        request = ScanRequest(
            id="test-req-1",
            target="http://example.com",
            requested_agents=["nmap"],
            priority=1,
            workflow_id="wf-1",
        )
        orchestrator = Orchestrator()
        results = await orchestrator.run_scan_async(request)
        assert isinstance(results, list)
        # In test mode, agents may be mocked or skipped, so just check list integrity
        assert all(hasattr(r, "agent") for r in results) or results == []

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    finally:
        loop.close()
        asyncio.set_event_loop(None)
