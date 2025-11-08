# Security Agency 🚀

A Flask-based security scanner that integrates open-source tools like **nmap**, **nikto**, **sqlmap**, **wpscan**, **sublist3r**, and **dirb**.  
It provides a REST API and dashboard to run scans against a target, orchestrates workflows, and aggregates results from multiple agents.

## ⚡ Phase 2: AI Security Scanner Evolution

**We're building the future of AI-powered security scanning!** 🎯

Phase 2 transforms Security Agency into an intelligent, adaptive, and proactive security platform with cutting-edge AI capabilities:

- 🤖 **Predictive Vulnerability Analysis** - Predict vulnerabilities before they're discovered
- 🌐 **Autonomous Attack Surface Discovery** - Continuously map and monitor your attack surface
- 🧠 **Multi-Agent AI Reasoning** - Specialized AI agents that collaborate on security analysis
- 💬 **Natural Language Security Interface** - Chat with your security data
- 🔍 **Real-Time Threat Intelligence** - Context-enriched findings with exploit data
- 🛡️ **Autonomous Remediation** - AI-generated fixes and patches
- 🔧 **DevSecOps Integration** - Seamless CI/CD pipeline security

**📖 [Read the Phase 2 Roadmap](PHASE_2_ROADMAP.md)** | **🚀 [Quick Start Guide](PHASE_2_QUICKSTART.md)**

---

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
- See [PHASE_2_ROADMAP.md](PHASE_2_ROADMAP.md) for the exciting Phase 2 vision and roadmap
- See [PHASE_2_QUICKSTART.md](PHASE_2_QUICKSTART.md) for quick start guide to Phase 2
- See [implementation_plan.md](implementation_plan.md) for progress tracking
- See [.github/phase2-issues/SUB_ISSUES.md](.github/phase2-issues/SUB_ISSUES.md) for individual feature issues
- See `.todo.md` for current phase items

## License
MIT
