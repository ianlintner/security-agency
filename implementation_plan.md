# Implementation Plan

[Overview]  
The goal is to build a Flask-based security scanner that orchestrates hacking agents powered by off-the-shelf open-source CLI tools, integrated through Python glue code.

This system will expose a REST API via Flask to manage scanning tasks, invoke different security tools (like `nmap`, `nikto`, `sqlmap`, etc.), and aggregate results. The architecture will separate concerns into API endpoints, agent orchestration, and tool adapters. The scanner will be modular, allowing new tools to be added easily. This implementation is needed to provide a flexible, extensible security testing framework that leverages existing OSS tools while providing a unified interface.

[Types]  
The type system will define structured data for scan requests, results, and agent configurations.

- **ScanRequest**:  
  - `id: str` (UUID)  
  - `target: str` (hostname/IP/URL)  
  - `tools: List[str]` (names of tools to run)  
  - `options: Dict[str, Any]` (tool-specific options)  

- **ScanResult**:  
  - `id: str` (UUID)  
  - `tool: str`  
  - `status: str` (success/failure)  
  - `output: str` (raw CLI output)  
  - `parsed: Dict[str, Any]` (structured findings)  

- **AgentConfig**:  
  - `name: str`  
  - `command: str` (CLI command template)  
  - `parser: Callable[[str], Dict[str, Any]]`  

[Files]  
The project will introduce new files for Flask app, agents, and configuration.

- **New files**:  
  - `app.py` → Flask entrypoint, API routes  
  - `agents/base_agent.py` → Abstract base class for agents  
  - `agents/nmap_agent.py` → Wrapper for `nmap`  
  - `agents/nikto_agent.py` → Wrapper for `nikto`  
  - `agents/sqlmap_agent.py` → Wrapper for `sqlmap`  
  - `core/orchestrator.py` → Orchestrates multiple agents per scan request  
  - `core/models.py` → Defines ScanRequest, ScanResult, AgentConfig dataclasses  
  - `core/utils.py` → Helper functions (UUID generation, subprocess execution)  
  - `requirements.txt` → Flask, requests, pydantic, etc.  
  - `tests/test_api.py` → API endpoint tests  
  - `tests/test_agents.py` → Agent integration tests  

- **Modified files**: None (empty repo).  
- **Deleted files**: None.  
- **Configuration updates**: Add `requirements.txt` with Flask and dependencies.

[Functions]  
Functions will handle API requests, agent execution, and result aggregation.

- **New functions**:  
  - `create_app() -> Flask` in `app.py` (initialize Flask app)  
  - `register_routes(app: Flask)` in `app.py` (define API endpoints)  
  - `run_scan(request: ScanRequest) -> List[ScanResult]` in `core/orchestrator.py`  
  - `execute_command(command: str) -> str` in `core/utils.py`  
  - `parse_output(tool: str, output: str) -> Dict[str, Any]` in `core/utils.py`  

- **Modified functions**: None.  
- **Removed functions**: None.

[Classes]  
Classes will encapsulate agent logic and data models.

- **New classes**:  
  - `BaseAgent` in `agents/base_agent.py` (abstract class with `run(target, options)`)  
  - `NmapAgent`, `NiktoAgent`, `SqlmapAgent` in respective files (implement `BaseAgent`)  
  - `ScanRequest`, `ScanResult`, `AgentConfig` in `core/models.py`  

- **Modified classes**: None.  
- **Removed classes**: None.

[Dependencies]  
Dependencies will include Flask for API, Pydantic for validation, and Requests for HTTP.

- Flask (API framework)  
- Pydantic (data validation)  
- Requests (optional, for external integrations)  
- Pytest (testing)  

[Testing]  
Testing will cover API endpoints and agent execution.

- `tests/test_api.py`: Test `/scan` endpoint with mock agents  
- `tests/test_agents.py`: Test each agent wrapper with sample CLI output  
- Use pytest fixtures for mock subprocess calls  
- Validate structured parsing of tool outputs  

[Implementation Order]  
The implementation will proceed in structured steps.

1. Create project structure with `app.py`, `core/`, `agents/`, `tests/`  
2. Implement `core/models.py` with dataclasses  
3. Implement `core/utils.py` with subprocess execution and parsing  
4. Implement `agents/base_agent.py` and concrete agents (`nmap`, `nikto`, `sqlmap`)  
5. Implement `core/orchestrator.py` to run multiple agents per request  
6. Implement Flask API in `app.py` with `/scan` endpoint  
7. Add `requirements.txt` with dependencies  
8. Write tests for API and agents  
9. Run and validate end-to-end scan workflow
