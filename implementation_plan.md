# Implementation Plan

[Overview]  
The goal is to implement an AI-driven orchestration system that coordinates multiple security scanning agents, progressively escalating from basic scans to more advanced exploit testing, using LangChain for LLM-driven decision-making.  

This system will allow a user to submit a website target, trigger an orchestrated workflow of agents, and dynamically decide which follow-up scans to run based on initial results. The orchestration will be autonomous, goal-seeking, and extensible. PostgreSQL will be used for persistence, and an eventing/scheduling system will manage agent execution. Initially, an in-memory queue will be used, with extensibility for distributed eventing later.

[Types]  
We will extend the type system to support orchestration metadata, workflows, and agent results.  

- `AgentConfig` (existing, core/models.py)  
  - Add `capabilities: List[str]` (e.g., "port-scan", "sql-injection")  

- `ScanRequest` (existing, core/models.py)  
  - Fields:  
    - `id: str`  
    - `target: str`  
    - `requested_agents: Optional[List[str]]`  
    - `priority: int`  
    - `workflow_id: Optional[str]` (link to workflow)  

- `ScanResult` (existing, core/models.py)  
  - Fields:  
    - `id: str`  
    - `request_id: str`  
    - `agent: str`  
    - `status: str` (queued, running, completed, failed)  
    - `output: Dict[str, Any]` (dynamic JSON for agent output)  
    - `analysis: Optional[Dict[str, Any]]` (post-processed analysis)  
    - `metadata: Dict[str, Any]`  

- `Workflow` (new, core/models.py)  
  - Fields:  
    - `id: str`  
    - `name: str`  
    - `description: Optional[str]`  
    - `state: str` (active, paused, completed)  
    - `steps: List[WorkflowStep]`  
    - `context: Dict[str, Any]` (dynamic JSON for stateful context)  

- `WorkflowStep` (new, core/models.py)  
  - Fields:  
    - `id: str`  
    - `workflow_id: str`  
    - `agent: str`  
    - `input: Dict[str, Any]` (dynamic JSON for agent input)  
    - `output: Optional[Dict[str, Any]]`  
    - `status: str` (pending, running, completed, failed)  
    - `dependencies: List[str]` (step IDs that must complete first)  

- `OrchestrationEvent` (new, core/models.py)  
  - `id: str`  
  - `type: str` (scan_started, scan_completed, escalation_triggered, workflow_resumed)  
  - `payload: Dict[str, Any]`  

- `AgentDecision` (new, core/models.py)  
  - `workflow_id: str`  
  - `next_steps: List[WorkflowStep]`  
  - `reasoning: str`  

[Files]  
We will add new orchestration and persistence files, and extend existing ones.  

- New files:  
  - `core/decision_engine.py`: LangChain-based orchestration logic.  
  - `core/event_queue.py`: In-memory event queue abstraction (extensible to Redis/Kafka).  
  - `core/storage.py`: PostgreSQL persistence layer for workflows, requests, and results.  
- Modified files:  
  - `core/orchestrator.py`: Integrate event queue, decision engine, and persistence.  
  - `core/models.py`: Add new dataclasses.  
  - `agents/base_agent.py`: Add async execution support.  
  - `app.py`: Extend API to support job submission, workflow management, status retrieval, and results.  
- Config updates:  
  - `requirements.txt`: Add `langchain`, `psycopg2-binary`, `sqlalchemy`.  
  - `Dockerfile`: Add PostgreSQL client dependencies.  

[Functions]  
We will add orchestration and decision functions.  

- New functions:  
  - `DecisionEngine.decide_next_steps(workflow: Workflow, results: List[ScanResult]) -> AgentDecision`  
  - `EventQueue.publish(event: OrchestrationEvent)`  
  - `EventQueue.consume() -> OrchestrationEvent`  
  - `Storage.save_workflow(workflow: Workflow)`  
  - `Storage.save_scan_request(request: ScanRequest)`  
  - `Storage.save_scan_result(result: ScanResult)`  
  - `Storage.update_workflow_state(workflow_id: str, state: str)`  
- Modified functions:  
  - `Orchestrator.run_scan`: Instead of directly running agents, enqueue workflow steps and invoke decision engine.  
  - `BaseAgent.run`: Support async execution and structured results.  

[Classes]  
We will add orchestration and persistence classes.  

- New classes:  
  - `DecisionEngine` (core/decision_engine.py): Wraps LangChain LLM calls to decide next workflow steps.  
  - `EventQueue` (core/event_queue.py): In-memory queue with publish/consume.  
  - `Storage` (core/storage.py): PostgreSQL persistence.  
- Modified classes:  
  - `Orchestrator` (core/orchestrator.py): Integrate decision engine, event queue, and storage.  
  - `BaseAgent` (agents/base_agent.py): Add async run support.  

[Dependencies]  
We will add new dependencies for orchestration and persistence.  

- Add `langchain` for LLM-driven orchestration.  
- Add `psycopg2-binary` and `sqlalchemy` for PostgreSQL.  
- Keep existing `flask`, `pydantic`, `pytest`.  

[Testing]  
We will extend tests to cover workflows, orchestration, and persistence.  

- New tests:  
  - `tests/test_decision_engine.py`: Validate LangChain decision logic with mocked LLM.  
  - `tests/test_event_queue.py`: Validate event publishing/consumption.  
  - `tests/test_storage.py`: Validate PostgreSQL persistence.  
  - `tests/test_workflows.py`: Validate workflow creation, step execution, and resumption.  
- Modified tests:  
  - `tests/test_agents.py`: Ensure agents return structured results.  
  - `tests/test_api.py`: Add tests for workflow submission, status retrieval, and results.  

[Implementation Order]  
We will implement in stages to minimize conflicts.  

1. Extend `core/models.py` with new dataclasses for workflows, steps, and events.  
2. Implement `core/event_queue.py` (in-memory).  
3. Implement `core/storage.py` (PostgreSQL).  
4. Implement `core/decision_engine.py` with LangChain.  
5. Modify `agents/base_agent.py` for async execution.  
6. Modify `core/orchestrator.py` to integrate workflows, queue, storage, and decision engine.  
7. Modify `app.py` to expose new API endpoints for workflows and scans.  
8. Update `requirements.txt` and `Dockerfile`.  
9. Write new tests and update existing ones.  
10. Run end-to-end validation with sample workflows.
