# Security Scanner

A Flask-based security scanner that integrates open-source tools like **nmap**, **nikto**, and **sqlmap**.  
It provides a REST API to run scans against a target and aggregates results from multiple agents.

## Features
- Modular agent design with a `BaseAgent` class
- Agents for `nmap`, `nikto`, and `sqlmap`
- Orchestrator to run multiple agents per request
- Flask API with `/scan` endpoint
- Subprocess execution with timeout and error handling
- Pytest test suite
- Dockerfile for containerized deployment
- Makefile for developer workflow
- GitHub Actions CI/CD pipeline
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

## License
MIT
