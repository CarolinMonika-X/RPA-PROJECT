"""
Settings and Environment Diagnostics API routes with server-side validation.
"""

from flask import Blueprint, jsonify, request
from backend.services.system_service import system_service

settings_bp = Blueprint("settings", __name__, url_prefix="/api")

@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    return jsonify({"success": True, "data": system_service.get_settings()})

@settings_bp.route("/settings", methods=["POST"])
def update_settings():
    data = request.get_json() or {}
    success, msg, updated = system_service.save_settings(data)
    code = 200 if success else 400
    return jsonify({"success": success, "message": msg, "data": updated}), code

@settings_bp.route("/diagnostics", methods=["GET"])
def get_diagnostics():
    return jsonify({"success": True, "data": system_service.get_diagnostics()})
