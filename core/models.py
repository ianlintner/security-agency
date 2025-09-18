from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class AgentConfig:
    name: str
    command: str
    args: Optional[List[str]] = None


@dataclass
class ScanRequest:
    target: str
    agents: List[str]


@dataclass
class ScanResult:
    agent: str
    success: bool
    output: str
    errors: Optional[str] = None
    metadata: Optional[Dict] = None
