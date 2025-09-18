from agents.base_agent import BaseAgent


class NiktoAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="nikto", command="nikto")

    def build_args(self, target: str) -> list:
        return ["-h", target]
