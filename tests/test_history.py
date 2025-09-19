import pytest
from core.storage import Storage
from core.models import ScanRequest, ScanResult
import os

@pytest.fixture
def storage():
    os.environ["TESTING"] = "1"
    return Storage()

def test_save_and_list_history(storage):
    req = ScanRequest(id="req1", target="http://example.com", requested_agents=["nmap"])
    storage.save_scan_request(req)
    history = storage.list_scan_history()
    assert any(entry["id"] == "req1" for entry in history)

def test_save_and_get_results(storage):
    req = ScanRequest(id="req2", target="http://test.com", requested_agents=["nikto"])
    storage.save_scan_request(req)
    result = ScanResult(
        id="res1",
        request_id="req2",
        agent="nikto",
        status="completed",
        output={"data": "ok"},
    )
    storage.save_scan_result(result)
    results = storage.get_scan_results("req2")
    assert any(r["id"] == "res1" for r in results)

def test_get_scan_report(storage):
    req = ScanRequest(id="req3", target="http://abc.com", requested_agents=["sqlmap"])
    storage.save_scan_request(req)
    result = ScanResult(
        id="res2",
        request_id="req3",
        agent="sqlmap",
        status="completed",
        output={"data": "ok"},
    )
    storage.save_scan_result(result)
    report = storage.get_scan_report("res2")
    assert report["id"] == "res2"
