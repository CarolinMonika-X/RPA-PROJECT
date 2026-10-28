"""
Web UI View Routes rendering Jinja2 HTML templates.
"""

from flask import Blueprint, render_template, abort
from backend.services.db_service import db_service
from backend.services.workflow_service import workflow_service
from backend.services.cv_service import cv_service
from backend.services.employee_service import employee_service
from backend.services.system_service import system_service
from backend.services.ocr_service import ocr_service

view_bp = Blueprint("views", __name__)

@view_bp.route("/")
def dashboard():
    metrics = db_service.get_dashboard_metrics()
    recent_runs = db_service.list_executions(limit=8)
    recent_employees = employee_service.get_all_records()[-5:]
    dept_summary = employee_service.get_department_summary()
    templates = cv_service.list_templates()
    workflows = workflow_service.list_workflows()
    diagnostics = system_service.get_diagnostics()
    
    return render_template(
        "dashboard.html",
        active_page="dashboard",
        metrics=metrics,
        recent_runs=recent_runs,
        recent_employees=recent_employees,
        dept_summary=dept_summary,
        templates=templates,
        workflows=workflows,
        diagnostics=diagnostics
    )

@view_bp.route("/control-center")
def control_center():
    workflows = workflow_service.list_workflows()
    recent_runs = db_service.list_executions(limit=10)
    return render_template(
        "control_center.html",
        active_page="control-center",
        workflows=workflows,
        recent_runs=recent_runs
    )

@view_bp.route("/workflow-builder")
def workflow_builder():
    workflows = workflow_service.list_workflows()
    templates = cv_service.list_templates()
    return render_template(
        "workflow_builder.html",
        active_page="workflow-builder",
        workflows=workflows,
        templates=templates
    )

@view_bp.route("/cv-lab")
def cv_lab():
    templates = cv_service.list_templates()
    return render_template(
        "cv_lab.html",
        active_page="cv-lab",
        templates=templates
    )

@view_bp.route("/ocr-lab")
def ocr_lab():
    status = ocr_service.get_status()
    return render_template(
        "ocr_lab.html",
        active_page="ocr-lab",
        ocr_status=status
    )

@view_bp.route("/employees")
def employees():
    dept_summary = employee_service.get_department_summary()
    return render_template(
        "employees.html",
        active_page="employees",
        dept_summary=dept_summary
    )

@view_bp.route("/history")
def history():
    runs = db_service.list_executions(limit=50)
    metrics = db_service.get_dashboard_metrics()
    return render_template(
        "history.html",
        active_page="history",
        runs=runs,
        metrics=metrics
    )

@view_bp.route("/history/<exec_id>")
def execution_detail(exec_id):
    run = db_service.get_execution(exec_id)
    if not run:
        abort(404, description="Execution not found.")
    return render_template(
        "execution_detail.html",
        active_page="history",
        run=run
    )

@view_bp.route("/library")
def library():
    workflows = workflow_service.list_workflows()
    templates = cv_service.list_templates()
    return render_template(
        "library.html",
        active_page="library",
        workflows=workflows,
        templates=templates
    )

@view_bp.route("/settings")
def settings():
    diagnostics = system_service.get_diagnostics()
    current_settings = system_service.get_settings()
    return render_template(
        "settings.html",
        active_page="settings",
        diagnostics=diagnostics,
        settings=current_settings
    )
