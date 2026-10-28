"""
Pytest configuration and safety fixtures.
Mocks PyAutoGUI and PyGetWindow to prevent physical mouse/keyboard interactions during testing.
"""

import sys
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app import create_app
from backend.services.db_service import DatabaseService
from backend.services.employee_service import EmployeeService

@pytest.fixture(autouse=True)
def mock_desktop_interactions(monkeypatch):
    """Safely mocks all PyAutoGUI and PyGetWindow operations across all tests."""
    # Create a 200x200 mock screenshot image
    mock_img = Image.new("RGB", (300, 200), color=(200, 200, 200))
    
    monkeypatch.setattr("pyautogui.screenshot", lambda *args, **kwargs: mock_img)
    monkeypatch.setattr("pyautogui.click", MagicMock())
    monkeypatch.setattr("pyautogui.write", MagicMock())
    monkeypatch.setattr("pyautogui.press", MagicMock())
    monkeypatch.setattr("pyautogui.hotkey", MagicMock())
    monkeypatch.setattr("pyautogui.size", lambda: (1920, 1080))
    
    mock_window = MagicMock()
    mock_window.title = "Legacy Employee Management System"
    mock_window.isMinimized = False
    mock_window.activate = MagicMock()
    mock_window.restore = MagicMock()
    
    monkeypatch.setattr("pygetwindow.getWindowsWithTitle", lambda title: [mock_window])

@pytest.fixture
def temp_env(tmp_path):
    """Provides temporary directories for DB, CSV, and templates."""
    db_file = tmp_path / "test_rpa.db"
    csv_file = tmp_path / "test_employees.csv"
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    # Create sample template
    sample_tmpl = Image.new("RGB", (40, 20), color=(100, 100, 100))
    sample_tmpl.save(templates_dir / "save_employee.png")
    
    return {
        "db_path": str(db_file),
        "csv_path": csv_file,
        "templates_dir": templates_dir
    }

@pytest.fixture
def test_app():
    """Provides a configured Flask test client."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client
