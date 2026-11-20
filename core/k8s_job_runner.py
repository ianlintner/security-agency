"""Entry-point used inside Kubernetes Jobs to execute a single tool run.

The job container should run something like:

  python -m core.k8s_job_runner --agent nmap --target example.com --request-id req-123

This prints a JSON representation of ScanResult to stdout so logs can be collected.
"""

import argparse
import json
import sys
import time

from agents.nikto_agent import NiktoAgent
from agents.nmap_agent import NmapAgent
from agents.sqlmap_agent import SqlmapAgent
from core.models import ScanResult


def _agents():
    return {
        "nmap": NmapAgent(),
        "nikto": NiktoAgent(),
        "sqlmap": SqlmapAgent(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Security Agency Kubernetes Job Runner")
    parser.add_argument("--agent", required=True, help="Agent/tool name (e.g. nmap, nikto, sqlmap)")
    parser.add_argument("--target", required=True, help="Target to scan")
    parser.add_argument("--request-id", required=True, help="Scan request ID")
    args = parser.parse_args(argv)

    agents = _agents()
    agent = agents.get(args.agent)
    if not agent:
        result = ScanResult(
            id=f"{args.agent}-result",
            request_id=args.request_id,
            agent=args.agent,
            status="failed",
            output={"stdout": ""},
            analysis=None,
            metadata={"stderr": f"Unknown agent: {args.agent}", "exit_code": 127},
        )
        print(json.dumps(result.__dict__))
        return 127

    start = time.time()
    scan_result = agent.run(args.target, request_id=args.request_id)
    # Add a tiny bit of timing metadata for observability.
    scan_result.metadata = scan_result.metadata or {}
    scan_result.metadata["duration_seconds"] = round(time.time() - start, 3)

    print(json.dumps(scan_result.__dict__))
    return 0 if scan_result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
