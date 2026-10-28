"""
System environment diagnostics, settings management, and health checks with server-side bounds validation.
"""

import sys
import os
import json
import platform
import cv2
import pyautogui
from pathlib import Path
from typing import Dict, Any, Tuple
from backend.config import (
    DATA_DIR, TEMPLATES_DIR, RESULTS_DIR, EMPLOYEE_CSV_PATH, DB_PATH,
    DEFAULT_CONFIDENCE_THRESHOLD, DEFAULT_TIMEOUT_SECONDS, MAX_RETRIES
)
from backend.services.ocr_service import ocr_service

SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
    "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
    "max_retries": MAX_RETRIES,
    "screenshot_retention_days": 7,
    "theme": "dark",
    "pyautogui_pause": 0.3,
    "pyautogui_failsafe": True
}

class SystemService:
    def __init__(self):
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    res = DEFAULT_SETTINGS.copy()
                    res.update(saved)
                    return res
            except Exception:
                pass
        return DEFAULT_SETTINGS.copy()

    def validate_settings(self, payload: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Strict server-side validation of setting ranges and data types."""
        cleaned = {}

        if "confidence_threshold" in payload:
            try:
                val = float(payload["confidence_threshold"])
                if not (0.50 <= val <= 0.99):
                    return False, "confidence_threshold must be between 0.50 and 0.99.", {}
                cleaned["confidence_threshold"] = round(val, 2)
            except (ValueError, TypeError):
                return False, "confidence_threshold must be a valid float.", {}

        if "timeout_seconds" in payload:
            try:
                val = int(payload["timeout_seconds"])
                if not (5 <= val <= 300):
                    return False, "timeout_seconds must be between 5 and 300 seconds.", {}
                cleaned["timeout_seconds"] = val
            except (ValueError, TypeError):
                return False, "timeout_seconds must be a valid integer.", {}

        if "pyautogui_pause" in payload:
            try:
                val = float(payload["pyautogui_pause"])
                if not (0.05 <= val <= 2.0):
                    return False, "pyautogui_pause must be between 0.05 and 2.0 seconds.", {}
                cleaned["pyautogui_pause"] = round(val, 2)
            except (ValueError, TypeError):
                return False, "pyautogui_pause must be a valid float.", {}

        if "max_retries" in payload:
            try:
                val = int(payload["max_retries"])
                if not (1 <= val <= 5):
                    return False, "max_retries must be between 1 and 5.", {}
                cleaned["max_retries"] = val
            except (ValueError, TypeError):
                return False, "max_retries must be a valid integer.", {}

        if "screenshot_retention_days" in payload:
            try:
                val = int(payload["screenshot_retention_days"])
                if not (1 <= val <= 90):
                    return False, "screenshot_retention_days must be between 1 and 90 days.", {}
                cleaned["screenshot_retention_days"] = val
            except (ValueError, TypeError):
                return False, "screenshot_retention_days must be a valid integer.", {}

        if "theme" in payload:
            val = str(payload["theme"]).lower().strip()
            if val not in ["dark", "light"]:
                return False, "theme must be either 'dark' or 'light'.", {}
            cleaned["theme"] = val

        return True, "Valid", cleaned

    def save_settings(self, new_settings: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        is_valid, msg, cleaned = self.validate_settings(new_settings)
        if not is_valid:
            return False, msg, self.settings

        self.settings.update(cleaned)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)
        return True, "Settings saved successfully.", self.settings.copy()

    def get_settings(self) -> Dict[str, Any]:
        return self.settings.copy()

    def get_diagnostics(self) -> Dict[str, Any]:
        """Gathers runtime environment diagnostics, versions, and platform integrity checks."""
        try:
            screen_width, screen_height = pyautogui.size()
        except Exception:
            screen_width, screen_height = 0, 0

        # Check template presence
        save_btn_template = (TEMPLATES_DIR / "save_employee.png").exists()

        # Check CSV writeability
        csv_writable = os.access(EMPLOYEE_CSV_PATH.parent, os.W_OK)

        # Check DB
        db_exists = DB_PATH.exists()

        ocr_info = ocr_service.get_status()

        return {
            "python_version": sys.version.split()[0],
            "opencv_version": cv2.__version__,
            "platform": platform.platform(),
            "os_name": platform.system(),
            "screen_resolution": f"{screen_width}x{screen_height}",
            "pyautogui_failsafe": pyautogui.FAILSAFE,
            "pyautogui_pause": pyautogui.PAUSE,
            "ocr_status": ocr_info,
            "save_template_present": save_btn_template,
            "csv_path": str(EMPLOYEE_CSV_PATH),
            "csv_writable": csv_writable,
            "db_path": str(DB_PATH),
            "db_active": db_exists,
            "status": "HEALTHY"
        }

system_service = SystemService()
