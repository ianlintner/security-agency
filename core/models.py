from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


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
    execution_mode: Optional[str] = None  # local | k8s


@dataclass
class ScanResult:
    id: str
    request_id: str
    agent: str
    status: str  # queued, running, completed, failed
    output: Dict[str, Any]
    analysis: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class K8sJobStatus(str, Enum):
    """Lifecycle status for long-running scan execution in Kubernetes."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass
class K8sJobRecord:
    """Persistence model for a Kubernetes Job associated with a scan request."""

    id: str
    request_id: str
    agent: str
    target: str
    k8s_job_name: str
    namespace: str
    status: str = K8sJobStatus.PENDING.value
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
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


@dataclass
class ScanHistoryEntry:
    id: str
    target: str
    requested_agents: Optional[List[str]]
    priority: int
    workflow_id: Optional[str]


@dataclass
class ScanReport:
    id: str
    request_id: str
    agent: str
    status: str
    output: Dict[str, Any]
    analysis: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
