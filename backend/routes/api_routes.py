"""
Core REST API routes for executions, workflows, metrics, and health diagnostics.
"""

from flask import Blueprint, jsonify, request, send_file, Response
import json
import io
from datetime import datetime
from backend.services.automation_engine import automation_engine
from backend.services.workflow_service import workflow_service
from backend.services.db_service import db_service
from backend.services.system_service import system_service
from backend.models import Workflow

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    diag = system_service.get_diagnostics()
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_state": automation_engine.current_state,
        "diagnostics": diag
    })

@api_bp.route("/metrics", methods=["GET"])
def get_metrics():
    """Dashboard metrics computed from actual persisted history."""
    metrics = db_service.get_dashboard_metrics()
    return jsonify({"success": True, "data": metrics})

# --- Executions ---

@api_bp.route("/executions", methods=["GET"])
def list_executions():
    status = request.args.get("status")
    workflow = request.args.get("workflow")
    limit = int(request.args.get("limit", 50))
    runs = db_service.list_executions(limit=limit, status=status, workflow=workflow)
    return jsonify({"success": True, "count": len(runs), "data": runs})

@api_bp.route("/executions/start", methods=["POST"])
def start_execution():
    data = request.get_json() or {}
    workflow_id = data.get("workflow_id")
    if not workflow_id:
        return jsonify({"success": False, "error": "workflow_id is required."}), 400

    input_params = data.get("params", {})
    dry_run = bool(data.get("dry_run", False))

    res = automation_engine.start_execution(
        workflow_id=workflow_id,
        input_params=input_params,
        dry_run=dry_run
    )

    status_code = 200 if res.get("success") else 409
    return jsonify(res), status_code

@api_bp.route("/executions/<exec_id>", methods=["GET"])
def get_execution(exec_id):
    run = db_service.get_execution(exec_id)
    if not run:
        return jsonify({"success": False, "error": "Execution not found."}), 404
    return jsonify({"success": True, "data": run})

@api_bp.route("/executions/<exec_id>/logs", methods=["GET"])
def get_execution_logs(exec_id):
    since_idx = int(request.args.get("since", 0))
    # If this is the active execution, read from live logger
    if automation_engine.active_execution_id == exec_id and automation_engine.active_logger:
        entries = automation_engine.active_logger.get_entries(since_index=since_idx)
        return jsonify({
            "success": True,
            "status": automation_engine.current_state,
            "entries": entries,
            "is_active": True
        })

    # Otherwise read from DB
    run = db_service.get_execution(exec_id)
    if not run:
        return jsonify({"success": False, "error": "Execution not found."}), 404

    logs = run.get("logs", [])
    if since_idx < len(logs):
        entries = logs[since_idx:]
    else:
        entries = []

    return jsonify({
        "success": True,
        "status": run.get("status"),
        "entries": entries,
        "is_active": False
    })

@api_bp.route("/executions/<exec_id>/confirm", methods=["POST"])
def confirm_execution(exec_id):
    data = request.get_json() or {}
    action = data.get("action", "CONFIRM")
    res = automation_engine.respond_confirmation(exec_id, action)
    code = 200 if res.get("success") else 400
    return jsonify(res), code

@api_bp.route("/executions/<exec_id>/abort", methods=["POST"])
def abort_execution(exec_id):
    res = automation_engine.cancel_execution(exec_id)
    code = 200 if res.get("success") else 400
    return jsonify(res), code

# --- Workflows ---

@api_bp.route("/workflows", methods=["GET"])
def list_workflows():
    wfs = workflow_service.list_workflows()
    return jsonify({"success": True, "data": wfs})

@api_bp.route("/workflows", methods=["POST"])
def create_workflow():
    data = request.get_json() or {}
    try:
        wf = Workflow.from_dict(data)
        success, msg = workflow_service.save_workflow(wf)
        if success:
            return jsonify({"success": True, "message": msg, "data": wf.to_dict()}), 201
        return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/workflows/<wf_id>", methods=["GET"])
def get_workflow(wf_id):
    wf = workflow_service.get_workflow(wf_id)
    if not wf:
        return jsonify({"success": False, "error": "Workflow not found."}), 404
    return jsonify({"success": True, "data": wf.to_dict()})

@api_bp.route("/workflows/<wf_id>", methods=["PUT"])
def update_workflow(wf_id):
    data = request.get_json() or {}
    try:
        data["id"] = wf_id
        wf = Workflow.from_dict(data)
        success, msg = workflow_service.save_workflow(wf)
        if success:
            return jsonify({"success": True, "message": msg, "data": wf.to_dict()})
        return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/workflows/<wf_id>", methods=["DELETE"])
def delete_workflow(wf_id):
    success, msg = workflow_service.delete_workflow(wf_id)
    code = 200 if success else 404
    return jsonify({"success": success, "message": msg}), code

@api_bp.route("/workflows/<wf_id>/duplicate", methods=["POST"])
def duplicate_workflow(wf_id):
    data = request.get_json() or {}
    new_name = data.get("name", "")
    success, msg, new_wf = workflow_service.duplicate_workflow(wf_id, new_name)
    if success:
        return jsonify({"success": True, "message": msg, "data": new_wf.to_dict()}), 201
    return jsonify({"success": False, "error": msg}), 400

@api_bp.route("/workflows/export/<wf_id>", methods=["GET"])
def export_workflow(wf_id):
    wf = workflow_service.get_workflow(wf_id)
    if not wf:
        return jsonify({"success": False, "error": "Workflow not found."}), 404
    content = json.dumps(wf.to_dict(), indent=2)
    return Response(
        content,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename={wf.id}.json"}
    )

@api_bp.route("/workflows/import", methods=["POST"])
def import_workflow():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400
    file = request.files["file"]
    try:
        data = json.load(file)
        wf = Workflow.from_dict(data)
        success, msg = workflow_service.save_workflow(wf)
        if success:
            return jsonify({"success": True, "message": msg, "data": wf.to_dict()}), 201
        return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid workflow file: {str(e)}"}), 400
