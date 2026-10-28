"""
OmniRPA Platform Launcher.
Starts the Flask server with REST API, Web UI, and managed automation subprocess engine.
"""

import sys
import os
from pathlib import Path

# Ensure backend package is in Python path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from backend.app import create_app
from backend.config import SERVER_HOST, SERVER_PORT
from backend.services.system_service import system_service
from backend.services.db_service import db_service
from backend.services.workflow_service import workflow_service

def main():
    print("=" * 70)
    print("  AI-POWERED RPA AUTOMATION PLATFORM")
    print("  Image-Based Legacy Automation Upgrade")
    print("=" * 70)

    # Initialize services
    diag = system_service.get_diagnostics()
    print(f"[*] Python Runtime:     Python {diag['python_version']}")
    print(f"[*] Computer Vision:    OpenCV {diag['opencv_version']}")
    print(f"[*] Display Resolution: {diag['screen_resolution']}")
    print(f"[*] OCR Tesseract:     {'Available' if diag['ocr_status']['available'] else 'Offline (Fallback Heuristic Active)'}")
    print(f"[*] CSV Records File:   {diag['csv_path']}")
    print(f"[*] SQLite Database:    {diag['db_path']}")
    print("-" * 70)
    print(f"[*] Server URL:         http://{SERVER_HOST}:{SERVER_PORT}")
    print("=" * 70)

    app = create_app()
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)

if __name__ == "__main__":
    main()
