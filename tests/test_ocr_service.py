"""
Unit tests for OCR Service and contour-based element fallback.
"""

import cv2
import numpy as np
from backend.services.ocr_service import OCRService

def test_ocr_status_reporting():
    ocr = OCRService()
    status = ocr.get_status()
    assert "available" in status
    assert "installation_guide" in status

def test_contour_heuristic_fallback_detects_buttons(tmp_path):
    ocr = OCRService()
    
    # Create an image containing a rectangular button (120x35) with contrasting border
    img = np.full((300, 400, 3), 240, dtype=np.uint8)
    # Draw button box
    cv2.rectangle(img, (100, 100), (220, 135), (80, 80, 80), -1)
    cv2.rectangle(img, (99, 99), (221, 136), (20, 20, 20), 2)

    img_path = tmp_path / "button_canvas.png"
    cv2.imwrite(str(img_path), img)

    res = ocr._fallback_contour_search(img_path, "Save Employee")
    assert res["success"] is True
    assert res["match_type"] == "contour_heuristic_fallback"
    assert res["candidates_count"] >= 1
    # Check center is roughly (160, 117)
    first_c = res["candidates"][0]
    assert 90 <= first_c["center"]["x"] <= 230
    assert 90 <= first_c["center"]["y"] <= 145
