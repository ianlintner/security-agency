# Security Agency 🚀

A Flask-based security scanner that integrates open-source tools like **nmap**, **nikto**, **sqlmap**, **wpscan**, **sublist3r**, and **dirb**.  
It provides a REST API and dashboard to run scans against a target, orchestrates workflows, and aggregates results from multiple agents.

## Features
- Modular agent design with a `BaseAgent` class
- Agents for `nmap`, `nikto`, `sqlmap`, `wpscan`, `sublist3r`, and `dirb`
- Orchestrator with scheduling, retries, and parallel execution
- Decision engine powered by LangChain + GPT-4
- Flask API with `/scan` and `/request` endpoints
- Frontend dashboard with real-time updates and visualization
- Persistent storage with PostgreSQL
- Authentication & RBAC (coming soon)
- Pytest test suite (unit, integration, e2e)
- Dockerfile with multi-stage builds
- Makefile for developer workflow
- GitHub Actions CI/CD pipeline with preview deployments
- Poetry and venv support

## Installation

### Using venv
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Using Poetry
```bash
poetry install
```

## Usage
Run the Flask app:
```bash
python app.py
```

Send a scan request:
```bash
curl -X POST http://localhost:5000/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "http://example.com", "agents": ["nmap", "nikto", "sqlmap"]}'
```

## Testing
```bash
pytest
```

## Documentation
- See `.todo.md` for roadmap
- See `implementation_plan.md` for progress tracking

## License
MIT
