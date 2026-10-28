"""
Configuration module for the AI-Powered RPA Platform.
Resolves paths reliably across Windows environments and enforces safe boundaries.
"""

import os
from pathlib import Path

# Base directory is the project directory containing this backend package
BASE_DIR = Path(__file__).resolve().parent.parent

# Core subdirectories
TEMPLATES_DIR = BASE_DIR / "templates"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
RESULTS_DIR = BASE_DIR / "results"
WORKFLOWS_DIR = BASE_DIR / "workflows"
DATA_DIR = BASE_DIR / "data"

# File paths
EMPLOYEE_CSV_PATH = RESULTS_DIR / "employees.csv"
DB_PATH = DATA_DIR / "rpa_platform.db"
DEFAULT_TEMPLATE_PATH = TEMPLATES_DIR / "save_employee.png"
LATEST_RESULT_IMG = RESULTS_DIR / "automation_result.png"

# Default configuration settings
DEFAULT_CONFIDENCE_THRESHOLD = 0.80
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_STEP_DELAY_MS = 250
MAX_RETRIES = 3
SCREENSHOT_RETENTION_DAYS = 7
APP_TITLE_TARGET = "Legacy Employee Management System"

# Flask Server Config
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000
SECRET_KEY = os.environ.get("RPA_SECRET_KEY", "rpa-dev-secret-key-9a8b7c6d5e4f3a2b1")

# Ensure required runtime directories exist
for directory in [TEMPLATES_DIR, SCREENSHOTS_DIR, RESULTS_DIR, WORKFLOWS_DIR, DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
