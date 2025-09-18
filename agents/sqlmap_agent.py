from agents.base_agent import BaseAgent


class SqlmapAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="sqlmap", command="sqlmap")

    def build_args(self, target: str) -> list:
        return ["-u", target, "--batch"]
