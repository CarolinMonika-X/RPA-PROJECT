"""
Computer Vision & OCR API routes.
Provides endpoints for template matching, canvas cropping, live desktop screenshot,
template management, side-by-side comparison, and OCR text recognition.
"""

from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from pathlib import Path
from backend.config import TEMPLATES_DIR, SCREENSHOTS_DIR, RESULTS_DIR
from backend.services.cv_service import cv_service
from backend.services.ocr_service import ocr_service
from backend.utils.security import safe_resolve_path

cv_bp = Blueprint("cv", __name__, url_prefix="/api")

# --- Static image viewing helpers ---
@cv_bp.route("/images/templates/<path:filename>")
def serve_template_image(filename):
    return send_from_directory(str(TEMPLATES_DIR), filename)

@cv_bp.route("/images/screenshots/<path:filename>")
def serve_screenshot_image(filename):
    return send_from_directory(str(SCREENSHOTS_DIR), filename)

@cv_bp.route("/images/results/<path:filename>")
def serve_result_image(filename):
    return send_from_directory(str(RESULTS_DIR), filename)

# --- CV Lab Endpoints ---

@cv_bp.route("/cv/templates", methods=["GET"])
def list_templates():
    templates = cv_service.list_templates()
    return jsonify({"success": True, "count": len(templates), "data": templates})

@cv_bp.route("/cv/templates", methods=["POST"])
def upload_template():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "Empty filename."}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".png"):
        filename += ".png"

    dest = safe_resolve_path(TEMPLATES_DIR, filename)
    file.save(str(dest))
    return jsonify({"success": True, "message": f"Template '{filename}' uploaded.", "filename": filename}), 201

@cv_bp.route("/cv/templates/<template_name>", methods=["DELETE"])
def delete_template(template_name):
    try:
        path = safe_resolve_path(TEMPLATES_DIR, template_name)
        if not path.exists():
            return jsonify({"success": False, "error": "Template not found."}), 404
        path.unlink()
        return jsonify({"success": True, "message": f"Template '{template_name}' deleted."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@cv_bp.route("/cv/templates/<template_name>/rename", methods=["POST"])
def rename_template(template_name):
    data = request.get_json() or {}
    new_name = data.get("new_name", "").strip()
    if not new_name:
        return jsonify({"success": False, "error": "new_name is required."}), 400
    if not new_name.lower().endswith(".png"):
        new_name += ".png"

    try:
        src = safe_resolve_path(TEMPLATES_DIR, template_name)
        dst = safe_resolve_path(TEMPLATES_DIR, new_name)
        if not src.exists():
            return jsonify({"success": False, "error": "Original template not found."}), 404
        if dst.exists():
            return jsonify({"success": False, "error": "Destination name already exists."}), 409
        src.rename(dst)
        return jsonify({"success": True, "message": f"Renamed to '{new_name}'."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@cv_bp.route("/cv/capture", methods=["POST"])
def capture_desktop():
    try:
        shot_path, w, h = cv_service.capture_screenshot()
        return jsonify({
            "success": True,
            "filename": shot_path.name,
            "width": w,
            "height": h,
            "image_url": f"/api/images/screenshots/{shot_path.name}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to capture desktop: {str(e)}"}), 500

@cv_bp.route("/cv/match", methods=["POST"])
def match_template():
    data = request.get_json() or {}
    screenshot_name = data.get("screenshot_name")
    template_name = data.get("template_name")
    method = data.get("method", "TM_CCOEFF_NORMED")
    multi_scale = bool(data.get("multi_scale", False))
    threshold = float(data.get("threshold", 0.80))

    if not screenshot_name or not template_name:
        return jsonify({"success": False, "error": "screenshot_name and template_name are required."}), 400

    try:
        shot_path = safe_resolve_path(SCREENSHOTS_DIR, screenshot_name)
        if not shot_path.exists():
            return jsonify({"success": False, "error": f"Screenshot '{screenshot_name}' not found."}), 404

        res = cv_service.match_template(
            screenshot_path=shot_path,
            template_name=template_name,
            method_name=method,
            multi_scale=multi_scale,
            threshold=threshold,
            save_annotation=True
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@cv_bp.route("/cv/crop", methods=["POST"])
def crop_template():
    data = request.get_json() or {}
    screenshot_name = data.get("screenshot_name")
    template_name = data.get("template_name")
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    width = int(data.get("width", 0))
    height = int(data.get("height", 0))

    if not screenshot_name or not template_name or width <= 0 or height <= 0:
        return jsonify({"success": False, "error": "Valid screenshot_name, template_name, width and height are required."}), 400

    try:
        shot_path = safe_resolve_path(SCREENSHOTS_DIR, screenshot_name)
        if not shot_path.exists():
            return jsonify({"success": False, "error": f"Screenshot '{screenshot_name}' not found."}), 404

        success, msg, name = cv_service.crop_template_from_image(
            image_path=shot_path,
            template_name=template_name,
            x=x, y=y, width=width, height=height
        )
        code = 201 if success else 400
        return jsonify({"success": success, "message": msg, "template_name": name}), code
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@cv_bp.route("/cv/compare", methods=["POST"])
def compare_templates():
    data = request.get_json() or {}
    t_a = data.get("template_a")
    t_b = data.get("template_b")
    if not t_a or not t_b:
        return jsonify({"success": False, "error": "template_a and template_b are required."}), 400

    res = cv_service.compare_templates(t_a, t_b)
    return jsonify({"success": True, "data": res})

# --- OCR Endpoints ---

@cv_bp.route("/ocr/status", methods=["GET"])
def ocr_status():
    status = ocr_service.get_status()
    return jsonify({"success": True, "data": status})

@cv_bp.route("/ocr/detect", methods=["POST"])
def ocr_detect():
    data = request.get_json() or {}
    screenshot_name = data.get("screenshot_name")
    label = data.get("label")

    if not screenshot_name:
        return jsonify({"success": False, "error": "screenshot_name is required."}), 400

    try:
        shot_path = safe_resolve_path(SCREENSHOTS_DIR, screenshot_name)
        if not shot_path.exists():
            return jsonify({"success": False, "error": f"Screenshot '{screenshot_name}' not found."}), 404

        if label:
            res = ocr_service.find_label_element(shot_path, label)
        else:
            res = ocr_service.detect_text(shot_path)
            
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
