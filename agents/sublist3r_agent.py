"""Sublist3r agent wrapper."""

from agents.base_agent import BaseAgent


class Sublist3rAgent(BaseAgent):
    """
    Agent wrapper for Sublist3r.
    """

    def __init__(self):
        super().__init__("sublist3r", "sublist3r")
        self.options: dict = {}

    def build_args(self, target: str) -> list:
        args = ["-d", target, "-o", "-"]
        for key, value in self.options.items():
            if isinstance(value, bool) and value:
                args.append(f"-{key}")
            elif value is not None:
                args.extend([f"-{key}", str(value)])
        return args

    def parse_output(self, output):
        # Sublist3r outputs a list of subdomains, one per line
        subdomains = [line.strip() for line in output.splitlines() if line.strip()]
        return {"subdomains": subdomains}
