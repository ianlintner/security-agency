from abc import ABC, abstractmethod
from core.models import ScanResult
from core.utils import run_subprocess


class BaseAgent(ABC):
    def __init__(self, name: str, command: str):
        self.name = name
        self.command = command

    @abstractmethod
    def build_args(self, target: str) -> list:
        """
        Build the CLI arguments for the tool.
        """
        pass

    def run(self, target: str) -> ScanResult:
        args = self.build_args(target)
        stdout, stderr, code = run_subprocess(self.command, args)
        return ScanResult(
            agent=self.name,
            success=(code == 0),
            output=stdout,
            errors=stderr if code != 0 else None,
            metadata={"exit_code": code}
        )
