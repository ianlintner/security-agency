# import json

from flask import Flask, Response, jsonify, request, send_from_directory

from core.decision_engine import DecisionEngine
from core.job_manager import JobManager, KubernetesUnavailableError
from core.models import ScanRequest
from core.storage import Storage
from core.orchestrator import Orchestrator
from core.recommendation_engine import RecommendationEngine

app = Flask(__name__)
decision_engine = DecisionEngine()
recommendation_engine = RecommendationEngine(decision_engine)
storage = Storage()
job_manager = JobManager()
orchestrator = Orchestrator(storage=storage, job_manager=job_manager)


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
        workflow_id=data.get("workflow_id"),
        execution_mode=data.get("execution_mode"),
    )
    import asyncio  # pylint: disable=import-outside-toplevel

    results = asyncio.run(orchestrator.run_scan_async(scan_request))
    return jsonify([result.__dict__ for result in results])


@app.route("/jobs", methods=["GET"])
def list_jobs():
    status = request.args.get("status")
    request_id = request.args.get("request_id")
    limit = int(request.args.get("limit", 50))
    jobs = storage.list_k8s_jobs(status=status, request_id=request_id, limit=limit)
    return jsonify(jobs)


@app.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = storage.get_k8s_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Best-effort refresh for pending/running jobs.
    if job.get("status") in ("pending", "running"):
        try:
            live_status = job_manager.get_job_status(job["k8s_job_name"]).value
            if live_status != job.get("status"):
                storage.update_k8s_job_status(job_id, live_status)
                job["status"] = live_status
        except KubernetesUnavailableError:
            # If k8s is not configured, keep DB status.
            pass

    return jsonify(job)


@app.route("/jobs/<job_id>/logs", methods=["GET"])
def get_job_logs(job_id):
    job = storage.get_k8s_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    try:
        logs = job_manager.get_job_logs(job["k8s_job_name"], tail_lines=int(request.args.get("tail", 2000)))
    except KubernetesUnavailableError as e:
        return jsonify({"error": str(e)}), 503

    return Response(logs, mimetype="text/plain")


@app.route("/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    job = storage.get_k8s_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    try:
        job_manager.delete_job(job["k8s_job_name"], cascade=True)
    except KubernetesUnavailableError as e:
        return jsonify({"error": str(e)}), 503

    storage.update_k8s_job_status(job_id, "cancelled")
    return jsonify({"status": "cancelled", "job_id": job_id})


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


@app.route("/request", methods=["POST"])
def handle_request():
    data = request.get_json()
    if not data or "webAddress" not in data:
        return jsonify({"error": "Invalid request, must include 'webAddress'"}), 400

    def generate():
        yield "Processing request...\n"
        # Here we would integrate with orchestrator/AI pipeline
        # For now, simulate streaming output
        yield f"Target: {data['webAddress']}\n"
        if data.get("notes"):
            yield f"Notes: {data['notes']}\n"
        yield "Running AI tasks...\n"
        yield "Completed.\n"

    return Response(generate(), mimetype="text/plain")


@app.route("/recommendations", methods=["POST"])
def get_recommendations():
    data = request.get_json()
    if not data or "scan_results" not in data:
        return jsonify({"error": "Invalid request, must include 'scan_results'"}), 400

    import asyncio  # pylint: disable=import-outside-toplevel

    recommendations = asyncio.run(
        recommendation_engine.generate_recommendations(data["scan_results"])
    )
    return jsonify(recommendations)


@app.route("/history", methods=["GET"])
def list_history():
    limit = int(request.args.get("limit", 50))
    history = storage.list_scan_history(limit=limit)
    return jsonify(history)


@app.route("/results/<request_id>", methods=["GET"])
def get_results(request_id):
    results = storage.get_scan_results(request_id)
    return jsonify(results)


@app.route("/report/<result_id>", methods=["GET"])
def get_report(result_id):
    report = storage.get_scan_report(result_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
