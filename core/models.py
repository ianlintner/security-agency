from dataclasses import dataclass
from typing import List, Dict, Optional, Any


@dataclass
class AgentConfig:
    name: str
    command: str
    args: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None


@dataclass
class ScanRequest:
    id: str
    target: str
    requested_agents: Optional[List[str]] = None
    priority: int = 0
    workflow_id: Optional[str] = None


@dataclass
class ScanResult:
    id: str
    request_id: str
    agent: str
    status: str  # queued, running, completed, failed
    output: Dict[str, Any]
    analysis: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Workflow:
    id: str
    name: str
    description: Optional[str] = None
    state: str = "active"  # active, paused, completed
    steps: List["WorkflowStep"] = None
    context: Dict[str, Any] = None


@dataclass
class WorkflowStep:
    id: str
    workflow_id: str
    agent: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, running, completed, failed
    dependencies: List[str] = None


@dataclass
class OrchestrationEvent:
    id: str
    type: str  # scan_started, scan_completed, escalation_triggered, workflow_resumed
    payload: Dict[str, Any]


@dataclass
class AgentDecision:
    workflow_id: str
    next_steps: List[WorkflowStep]
    reasoning: str
