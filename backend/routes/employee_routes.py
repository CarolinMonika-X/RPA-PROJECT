"""
Employee Management API routes.
Connects directly to results/employees.csv with full CRUD, search, filter, pagination, import/export,
automatic backup, and historical data integrity audit.
"""

from flask import Blueprint, jsonify, request, Response
from backend.services.employee_service import employee_service

employee_bp = Blueprint("employees", __name__, url_prefix="/api/employees")

@employee_bp.route("", methods=["GET"])
def list_employees():
    query = request.args.get("q", "")
    department = request.args.get("department", "")
    sort_by = request.args.get("sort_by", "Created At")
    ascending = request.args.get("ascending", "false").lower() == "true"
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))

    data = employee_service.search_and_filter(
        query=query,
        department=department,
        sort_by=sort_by,
        ascending=ascending,
        page=page,
        page_size=page_size
    )
    return jsonify({"success": True, "data": data})

@employee_bp.route("", methods=["POST"])
def add_employee():
    data = request.get_json() or {}
    emp_id = data.get("employee_id") or data.get("Employee ID") or ""
    name = data.get("name") or data.get("Name") or ""
    department = data.get("department") or data.get("Department") or ""

    success, msg, rec = employee_service.add_employee(emp_id, name, department)
    code = 201 if success else 400
    return jsonify({"success": success, "message": msg, "data": rec}), code

@employee_bp.route("/<emp_id>", methods=["PUT"])
def update_employee(emp_id):
    data = request.get_json() or {}
    name = data.get("name") or data.get("Name") or ""
    department = data.get("department") or data.get("Department") or ""

    success, msg = employee_service.update_employee(emp_id, name, department)
    code = 200 if success else 400
    return jsonify({"success": success, "message": msg}), code

@employee_bp.route("/<emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    success, msg = employee_service.delete_employee(emp_id)
    code = 200 if success else 404
    return jsonify({"success": success, "message": msg}), code

@employee_bp.route("/summary", methods=["GET"])
def get_summary():
    summary = employee_service.get_department_summary()
    return jsonify({"success": True, "data": summary})

@employee_bp.route("/audit", methods=["GET"])
def audit_data():
    audit_res = employee_service.audit_records()
    return jsonify({"success": True, "data": audit_res})

@employee_bp.route("/backup", methods=["POST"])
def create_backup():
    data = request.get_json() or {}
    reason = data.get("reason", "manual_user_snapshot")
    backup_file = employee_service.create_backup(reason)
    return jsonify({"success": True, "message": f"Backup created: {backup_file}", "backup_file": backup_file}), 201

@employee_bp.route("/backups", methods=["GET"])
def list_backups():
    backups = employee_service.list_backups()
    return jsonify({"success": True, "data": backups})

@employee_bp.route("/restore", methods=["POST"])
def restore_backup():
    data = request.get_json() or {}
    backup_name = data.get("backup_file", "")
    if not backup_name:
        return jsonify({"success": False, "error": "backup_file is required."}), 400
    success, msg = employee_service.restore_backup(backup_name)
    code = 200 if success else 400
    return jsonify({"success": success, "message": msg}), code

@employee_bp.route("/export", methods=["GET"])
def export_csv():
    records = employee_service.get_all_records()
    output = "Employee ID,Name,Department,Created At\r\n"
    for r in records:
        output += f"{r['Employee ID']},{r['Name']},{r['Department']},{r['Created At']}\r\n"

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=employees_export.csv"}
    )

@employee_bp.route("/import", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400
    file = request.files["file"]
    content = file.read().decode("utf-8", errors="replace")
    
    # Automatic safety snapshot before import
    employee_service.create_backup("pre_import")
    
    added, skipped, errors = employee_service.import_csv(content)
    return jsonify({
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors
    })
