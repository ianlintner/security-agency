from agents.base_agent import BaseAgent


class NmapAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="nmap", command="nmap")

    def build_args(self, target: str) -> list:
        return ["-sV", target]
