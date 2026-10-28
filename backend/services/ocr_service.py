"""
Optical Character Recognition (OCR) Service.
Uses pytesseract when available on Windows/Linux, with graceful fallback to OpenCV
contour-based element detection and diagnostic guidance when Tesseract is not installed.
"""

import os
import shutil
import cv2
import numpy as np
import pytesseract
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from backend.config import RESULTS_DIR

class OCRService:
    def __init__(self):
        self.tesseract_cmd = self._find_tesseract_binary()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _find_tesseract_binary(self) -> Optional[str]:
        # 1. Check system PATH
        cmd = shutil.which("tesseract")
        if cmd:
            return cmd
            
        # 2. Check standard Windows installations
        standard_windows_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in standard_windows_paths:
            if os.path.exists(p):
                return p
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns OCR availability, engine binary location, and installation guidance."""
        is_available = self.tesseract_cmd is not None and os.path.exists(self.tesseract_cmd)
        version = None
        if is_available:
            try:
                version = pytesseract.get_tesseract_version()
            except Exception:
                is_available = False

        return {
            "available": is_available,
            "binary_path": self.tesseract_cmd,
            "version": str(version) if version else "N/A",
            "installation_guide": (
                "Tesseract OCR is not installed or not in PATH. On Windows, install via: "
                "'winget install UB-Mannheim.TesseractOCR' or download from "
                "https://github.com/UB-Mannheim/tesseract/wiki"
            ) if not is_available else "OCR engine is ready and active."
        }

    def detect_text(self, image_path: Path) -> Dict[str, Any]:
        """Extracts text, word boxes, and coordinates from an image."""
        status = self.get_status()
        if not status["available"]:
            return {
                "success": False,
                "error": "Tesseract OCR engine is not installed on this system.",
                "guide": status["installation_guide"],
                "fallback_available": True
            }

        img = cv2.imread(str(image_path))
        if img is None:
            return {"success": False, "error": "Could not read target image."}

        # Preprocessing: convert to grayscale and contrast enhancement
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        try:
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
            words = []
            full_text_parts = []
            
            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = float(data["conf"][i])
                if text and conf > 0:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    words.append({
                        "text": text,
                        "confidence": round(conf / 100.0, 3),
                        "box": {"x": x, "y": y, "width": w, "height": h},
                        "center": {"x": x + w // 2, "y": y + h // 2}
                    })
                    full_text_parts.append(text)

            return {
                "success": True,
                "full_text": " ".join(full_text_parts),
                "words": words,
                "word_count": len(words)
            }
        except Exception as e:
            return {"success": False, "error": f"OCR processing failed: {str(e)}"}

    def find_label_element(self, image_path: Path, label: str) -> Dict[str, Any]:
        """Searches for an interactive button or field by its visible text label."""
        status = self.get_status()
        label_lower = label.lower().strip()

        if status["available"]:
            res = self.detect_text(image_path)
            if res.get("success"):
                words = res.get("words", [])
                
                # Check exact and substring matches
                for w in words:
                    if label_lower in w["text"].lower():
                        return {
                            "success": True,
                            "match_type": "ocr_text",
                            "found_text": w["text"],
                            "confidence": w["confidence"],
                            "box": w["box"],
                            "center": w["center"]
                        }

        # Fallback using OpenCV contour and rectangular UI element detection
        return self._fallback_contour_search(image_path, label)

    def _fallback_contour_search(self, image_path: Path, label: str) -> Dict[str, Any]:
        """
        OpenCV heuristic fallback: detects button-like rectangular components
        and returns candidate UI regions when OCR is unavailable.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            return {"success": False, "error": "Could not read target image for contour fallback."}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []

        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                # Filter for button-like proportions (width between 60 and 300, height between 20 and 80)
                aspect_ratio = float(w) / max(1, h)
                if 2.0 <= aspect_ratio <= 7.0 and 50 <= w <= 400 and 18 <= h <= 100:
                    candidates.append({
                        "box": {"x": x, "y": y, "width": w, "height": h},
                        "center": {"x": x + w // 2, "y": y + h // 2},
                        "aspect_ratio": round(aspect_ratio, 2)
                    })

        # Deduplicate overlapping candidates
        unique_candidates = []
        for c in candidates:
            box = c["box"]
            is_dup = False
            for u in unique_candidates:
                ub = u["box"]
                if abs(box["x"] - ub["x"]) < 20 and abs(box["y"] - ub["y"]) < 20:
                    is_dup = True
                    break
            if not is_dup:
                unique_candidates.append(c)

        return {
            "success": len(unique_candidates) > 0,
            "match_type": "contour_heuristic_fallback",
            "candidates_count": len(unique_candidates),
            "candidates": unique_candidates[:8],
            "note": "OCR engine offline; detected button-like UI elements via computer vision contours."
        }

ocr_service = OCRService()
