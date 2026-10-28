"""
Flask Application Factory for the AI-Powered RPA Automation Platform.
Assembles blueprints, configures static and template paths, and sets up error handlers.
"""

from flask import Flask, jsonify, render_template
from pathlib import Path
from backend.config import BASE_DIR, SECRET_KEY
from backend.routes.view_routes import view_bp
from backend.routes.api_routes import api_bp
from backend.routes.cv_routes import cv_bp
from backend.routes.employee_routes import employee_bp
from backend.routes.settings_routes import settings_bp

def create_app(test_config=None) -> Flask:
    template_dir = BASE_DIR / "templates_web"
    static_dir = BASE_DIR / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )

    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max upload

    if test_config:
        app.config.update(test_config)

    # Register Blueprints
    app.register_blueprint(view_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(cv_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(settings_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if hasattr(error, 'description') and error.description:
            msg = error.description
        else:
            msg = "Resource not found"
        return jsonify({"success": False, "error": msg}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "error": "Internal server error occurred."}), 500

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
