import json

from agents.base_agent import BaseAgent


class WPScanAgent(BaseAgent):
    """
    Agent wrapper for WPScan.
    """

    def __init__(self):
        super().__init__("wpscan", "wpscan")
        self.options: dict = {}
        self.target: str = ""
        # type ignore for lint compatibility
        # pylint: disable=attribute-defined-outside-init

    def build_args(self, target: str) -> list:
        cmd = ["wpscan", "--url", target]
        for key, value in self.options.items():
            if isinstance(value, bool) and value:
                cmd.append(f"--{key}")
            elif value is not None:
                cmd.extend([f"--{key}", str(value)])
        return cmd

    def parse_output(self, output):
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw_output": output}
