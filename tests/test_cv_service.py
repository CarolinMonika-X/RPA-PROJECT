"""
Unit tests for Computer Vision Service: template matching, thresholds, crop, and diagnostics.
"""

import cv2
import numpy as np
from pathlib import Path
from backend.services.cv_service import ComputerVisionService

def test_template_matching_success_and_confidence(tmp_path):
    svc = ComputerVisionService()
    svc.templates_dir = tmp_path / "templates"
    svc.results_dir = tmp_path / "results"
    svc.screenshots_dir = tmp_path / "screenshots"
    svc.templates_dir.mkdir(parents=True)
    svc.results_dir.mkdir(parents=True)
    svc.screenshots_dir.mkdir(parents=True)

    # Create a patterned 300x300 screen
    screen = np.full((300, 300, 3), 220, dtype=np.uint8)
    # Add random background pattern
    for i in range(10):
        cv2.line(screen, (i * 30, 0), (i * 30, 300), (200, 200, 200), 1)

    # Create a patterned button with distinct text and borders
    button_crop = np.full((30, 80, 3), 50, dtype=np.uint8)
    cv2.rectangle(button_crop, (2, 2), (78, 28), (0, 200, 0), 2)
    cv2.putText(button_crop, "SAVE", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Place button at (50, 60)
    screen[60:90, 50:130] = button_crop

    screen_path = svc.screenshots_dir / "screen.png"
    cv2.imwrite(str(screen_path), screen)

    tmpl_path = svc.templates_dir / "test_btn.png"
    cv2.imwrite(str(tmpl_path), button_crop)

    # Match
    res = svc.match_template(
        screenshot_path=screen_path,
        template_name="test_btn.png",
        threshold=0.80,
        multi_scale=False,
        save_annotation=True
    )

    assert res["success"] is True
    assert res["confidence"] >= 0.95
    assert res["box"]["x"] == 50
    assert res["box"]["y"] == 60
    assert res["center"]["x"] == 90
    assert res["center"]["y"] == 75

def test_template_matching_low_confidence_diagnostic(tmp_path):
    svc = ComputerVisionService()
    svc.templates_dir = tmp_path / "templates"
    svc.results_dir = tmp_path / "results"
    svc.screenshots_dir = tmp_path / "screenshots"
    svc.templates_dir.mkdir(parents=True)
    svc.results_dir.mkdir(parents=True)
    svc.screenshots_dir.mkdir(parents=True)

    # Screen with distinct texture A
    screen = np.zeros((150, 150, 3), dtype=np.uint8)
    cv2.circle(screen, (75, 75), 40, (255, 0, 0), -1)
    screen_path = svc.screenshots_dir / "circle_screen.png"
    cv2.imwrite(str(screen_path), screen)

    # Template with completely different texture B
    tmpl = np.zeros((30, 30, 3), dtype=np.uint8)
    cv2.line(tmpl, (0, 0), (30, 30), (0, 255, 255), 2)
    cv2.line(tmpl, (0, 30), (30, 0), (0, 255, 255), 2)
    tmpl_path = svc.templates_dir / "x_tmpl.png"
    cv2.imwrite(str(tmpl_path), tmpl)

    res = svc.match_template(
        screenshot_path=screen_path,
        template_name="x_tmpl.png",
        threshold=0.80,
        save_annotation=False
    )

    assert res["success"] is False
    assert len(res["diagnostics"]) > 0

def test_template_not_found_error(tmp_path):
    svc = ComputerVisionService()
    svc.templates_dir = tmp_path / "templates"
    svc.screenshots_dir = tmp_path / "screenshots"
    svc.templates_dir.mkdir(parents=True)
    svc.screenshots_dir.mkdir(parents=True)

    screen = np.full((50, 50, 3), 128, dtype=np.uint8)
    screen_path = svc.screenshots_dir / "test_screen.png"
    cv2.imwrite(str(screen_path), screen)

    res = svc.match_template(
        screenshot_path=screen_path,
        template_name="non_existent_template.png",
        threshold=0.80
    )

    assert res["success"] is False
    assert "not found" in res["error"].lower()

def test_crop_template_from_image(tmp_path):
    svc = ComputerVisionService()
    svc.templates_dir = tmp_path / "templates"
    svc.templates_dir.mkdir(parents=True)

    screen = np.full((100, 100, 3), 200, dtype=np.uint8)
    screen[10:30, 20:50] = (10, 20, 30)
    screen_path = tmp_path / "source.png"
    cv2.imwrite(str(screen_path), screen)

    success, msg, name = svc.crop_template_from_image(
        image_path=screen_path,
        template_name="cropped_btn.png",
        x=20, y=10, width=30, height=20
    )

    assert success is True
    assert (svc.templates_dir / "cropped_btn.png").exists()
