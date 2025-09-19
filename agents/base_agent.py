import asyncio
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
        raise NotImplementedError

    def run(self, target: str, request_id: str = "") -> ScanResult:
        """
        Synchronous execution of the agent with configurable request_id.
        """
        args = self.build_args(target)
        stdout, stderr, code = run_subprocess(self.command, args)
        return ScanResult(
            id=f"{self.name}-result",
            request_id=request_id,
            agent=self.name,
            status="completed" if code == 0 else "failed",
            output={"stdout": stdout},
            analysis=None,
            metadata={"stderr": stderr, "exit_code": code},
        )

    async def run_async(self, target: str, request_id: str = "") -> ScanResult:
        """
        Asynchronous execution of the agent with configurable request_id.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run, target, request_id)
