from flask import Flask, request, jsonify, send_from_directory
from core.models import ScanRequest
from core.orchestrator import Orchestrator

app = Flask(__name__)
orchestrator = Orchestrator()


@app.route("/scan", methods=["POST"])
def scan():
    data = request.get_json()
    if not data or "target" not in data:
        return jsonify({"error": "Invalid request, must include 'target'"}), 400

    scan_request = ScanRequest(
        id=data.get("id", "req-1"),
        target=data["target"],
        requested_agents=data.get("agents", []),
        priority=data.get("priority", 0),
        workflow_id=data.get("workflow_id")
    )
    results = orchestrator.run_scan(scan_request)
    return jsonify([result.__dict__ for result in results])


@app.route("/workflow/<workflow_id>", methods=["GET"])
def get_workflow(workflow_id):
    # Placeholder: would fetch from storage
    return jsonify({"workflow_id": workflow_id, "status": "active"})


@app.route("/")
def serve_frontend():
    return send_from_directory("frontend", "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("frontend", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
