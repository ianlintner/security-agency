from agents.base_agent import BaseAgent


class DirbAgent(BaseAgent):
    """
    Agent wrapper for Dirb.
    """

    def __init__(self):
        super().__init__("dirb", "dirb")
        self.options: dict = {}
        self.target: str = ""
        # pylint: disable=attribute-defined-outside-init

    def build_args(self, target: str) -> list:
        cmd = ["dirb", target]
        for key, value in self.options.items():
            if isinstance(value, bool) and value:
                cmd.append(f"-{key}")
            elif value is not None:
                cmd.extend([f"-{key}", str(value)])
        return cmd

    def parse_output(self, output):
        # Dirb output contains lines with "CODE:URL"
        findings = []
        for line in output.splitlines():
            if "==>" in line or "CODE:" in line:
                findings.append(line.strip())
        return {"findings": findings}
