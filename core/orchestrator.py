from typing import List
from core.models import ScanRequest, ScanResult
from agents.nmap_agent import NmapAgent
from agents.nikto_agent import NiktoAgent
from agents.sqlmap_agent import SqlmapAgent


class Orchestrator:
    def __init__(self):
        self.agents = {
            "nmap": NmapAgent(),
            "nikto": NiktoAgent(),
            "sqlmap": SqlmapAgent(),
        }

    def run_scan(self, request: ScanRequest) -> List[ScanResult]:
        results = []
        for agent_name in request.agents:
            agent = self.agents.get(agent_name)
            if agent:
                result = agent.run(request.target)
                results.append(result)
            else:
                results.append(
                    ScanResult(
                        agent=agent_name,
                        success=False,
                        output="",
                        errors=f"Agent '{agent_name}' not found",
                    )
                )
        return results
