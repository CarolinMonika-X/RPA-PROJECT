"""
Computer Vision Service powered by OpenCV and Pillow.
Supports template matching, multi-scale detection, multi-method comparisons,
ROI interactive cropping, screenshot capture, annotations, dimension validation, and diagnostics.
"""

import os
import cv2
import numpy as np
import pyautogui
from PIL import Image
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from backend.config import TEMPLATES_DIR, SCREENSHOTS_DIR, RESULTS_DIR, DEFAULT_CONFIDENCE_THRESHOLD
from backend.utils.security import safe_resolve_path

class ComputerVisionService:
    def __init__(self):
        self.templates_dir = Path(TEMPLATES_DIR)
        self.screenshots_dir = Path(SCREENSHOTS_DIR)
        self.results_dir = Path(RESULTS_DIR)

    def capture_screenshot(self, filename: str = None) -> Tuple[Path, int, int]:
        """Captures the current desktop screen and saves it."""
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
        out_path = self.screenshots_dir / filename
        screenshot = pyautogui.screenshot()
        screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(out_path), screen_np)
        
        height, width = screen_np.shape[:2]
        return out_path, width, height

    def validate_template_dimensions(self, width: int, height: int, screen_w: int = None, screen_h: int = None) -> Dict[str, Any]:
        """
        Validates template dimensions against minimum and maximum discrete UI element bounds.
        Prevents full-screen or entire-window crops from being treated as button templates.
        """
        errors = []
        warnings = []

        if width < 15 or height < 15:
            errors.append(f"Template region is too small ({width}x{height} px). Minimum allowed is 15x15 px.")

        if width > 800 or height > 500:
            errors.append(f"Template dimensions ({width}x{height} px) exceed maximum element limit (800x500 px). Avoid cropping entire windows.")

        if screen_w and screen_h:
            if width > 0.65 * screen_w or height > 0.65 * screen_h:
                errors.append(f"Crop covers over 65% of screen ({width}x{height} vs {screen_w}x{screen_h}). Must crop discrete UI buttons or icons.")

        aspect_ratio = width / max(1, height)
        if aspect_ratio > 25.0 or aspect_ratio < 0.04:
            warnings.append(f"Extreme aspect ratio ({aspect_ratio:.1f}). Ensure selection surrounds the full button.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "width": width,
            "height": height
        }

    def list_templates(self) -> List[Dict[str, Any]]:
        """Lists all stored template images with metadata and dimension health checks."""
        templates = []
        for file_path in self.templates_dir.glob("*.png"):
            img = cv2.imread(str(file_path))
            h, w = (img.shape[:2]) if img is not None else (0, 0)
            dim_check = self.validate_template_dimensions(w, h)
            
            # Check variance
            has_variance = True
            if img is not None:
                has_variance = float(np.std(img)) >= 0.1

            templates.append({
                "name": file_path.name,
                "stem": file_path.stem,
                "path": str(file_path),
                "width": w,
                "height": h,
                "is_valid_size": dim_check["valid"],
                "dimension_errors": dim_check["errors"],
                "has_features": has_variance,
                "size_bytes": file_path.stat().st_size,
                "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        templates.sort(key=lambda x: x["name"])
        return templates

    def match_template(
        self,
        screenshot_path: Path,
        template_name: str,
        method_name: str = "TM_CCOEFF_NORMED",
        multi_scale: bool = False,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        save_annotation: bool = True
    ) -> Dict[str, Any]:
        """
        Executes OpenCV template matching against a target screenshot.
        Supports TM_CCOEFF_NORMED, TM_CCORR_NORMED, and TM_SQDIFF_NORMED,
        along with multi-scale matching across scaling factors.
        """
        template_file = safe_resolve_path(self.templates_dir, template_name)
        if not template_file.exists():
            return {
                "success": False,
                "confidence": 0.0,
                "threshold": threshold,
                "error": f"Template '{template_name}' not found.",
                "diagnostics": ["Verify that the template image exists in the templates folder."]
            }

        screen_img = cv2.imread(str(screenshot_path))
        template_img = cv2.imread(str(template_file))

        if screen_img is None:
            return {"success": False, "confidence": 0.0, "error": "Could not read target screenshot."}
        if template_img is None:
            return {"success": False, "confidence": 0.0, "error": "Could not read template image."}

        s_h, s_w = screen_img.shape[:2]
        t_h, t_w = template_img.shape[:2]

        if t_h > s_h or t_w > s_w:
            return {
                "success": False,
                "confidence": 0.0,
                "threshold": threshold,
                "error": f"Template dimensions ({t_w}x{t_h}) exceed screenshot dimensions ({s_w}x{s_h}).",
                "diagnostics": [
                    "The template was captured at higher resolution than the current display.",
                    "Recapture the template using the Computer Vision Lab canvas cropper."
                ]
            }

        # Guard against zero-variance degenerate cases
        if np.std(template_img) < 0.1:
            return {
                "success": False,
                "confidence": 0.0,
                "threshold": threshold,
                "error": "Template has zero variance (blank/flat uniform color).",
                "diagnostics": ["The template contains no distinct visual edges or text features."]
            }

        methods_map = {
            "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
            "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
            "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED
        }
        cv_method = methods_map.get(method_name, cv2.TM_CCOEFF_NORMED)

        best_confidence = -1.0
        best_location = (0, 0)
        best_scale = 1.0
        best_w, best_h = t_w, t_h

        scales = [1.0]
        if multi_scale:
            scales = [0.80, 0.90, 1.0, 1.10, 1.25]

        for scale in scales:
            new_w = int(t_w * scale)
            new_h = int(t_h * scale)
            if new_h > s_h or new_w > s_w or new_w < 5 or new_h < 5:
                continue

            scaled_template = cv2.resize(template_img, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
            res = cv2.matchTemplate(screen_img, scaled_template, cv_method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            if cv_method == cv2.TM_SQDIFF_NORMED:
                # For SQDIFF, 0 is perfect match, invert for confidence
                curr_conf = 1.0 - min_val
                curr_loc = min_loc
            else:
                curr_conf = max_val
                curr_loc = max_loc

            if curr_conf > best_confidence:
                best_confidence = curr_conf
                best_location = curr_loc
                best_scale = scale
                best_w, best_h = new_w, new_h

        is_match = best_confidence >= threshold
        bx, by = best_location
        center_x = bx + best_w // 2
        center_y = by + best_h // 2

        annotation_filename = None
        if save_annotation:
            annotated = screen_img.copy()
            box_color = (0, 255, 0) if is_match else (0, 0, 255)
            # Draw bounding box
            cv2.rectangle(annotated, (bx, by), (bx + best_w, by + best_h), box_color, 3)
            # Draw center crosshair
            cv2.drawMarker(annotated, (center_x, center_y), box_color, markerType=cv2.MARKER_CROSS, markerSize=16, thickness=2)
            # Draw badge
            label = f"{template_name} ({best_confidence:.1%})"
            cv2.putText(annotated, label, (bx, max(24, by - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)
            
            annotation_filename = f"detected_{template_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            annot_path = self.results_dir / annotation_filename
            cv2.imwrite(str(annot_path), annotated)

        diagnostics = []
        if not is_match:
            diagnostics.append(f"Confidence {best_confidence:.1%} is below required threshold {threshold:.1%}.")
            if best_confidence > 0.50:
                diagnostics.append("Moderate visual similarity detected. Try multi-scale matching (0.8x-1.25x) or adjusting DPI scaling.")
            else:
                diagnostics.append("The target button or element was not found on screen. Check if the target window is active, unminimized, and unobstructed.")
        else:
            diagnostics.append(f"Element verified with {best_confidence:.1%} confidence at screen coordinates ({center_x}, {center_y}).")

        return {
            "success": is_match,
            "confidence": round(float(best_confidence), 4),
            "threshold": threshold,
            "method": method_name,
            "scale": best_scale,
            "box": {
                "x": bx,
                "y": by,
                "width": best_w,
                "height": best_h
            },
            "center": {
                "x": center_x,
                "y": center_y
            },
            "annotation_image": annotation_filename,
            "diagnostics": diagnostics
        }

    def crop_template_from_image(self, image_path: Path, template_name: str, x: int, y: int, width: int, height: int) -> Tuple[bool, str, Optional[str]]:
        """Crops a region from an image and saves it as a new template with strict size and aspect validation."""
        if not template_name.endswith(".png"):
            template_name += ".png"
            
        target_path = safe_resolve_path(self.templates_dir, template_name)
        img = cv2.imread(str(image_path))
        if img is None:
            return False, "Could not load source image.", None

        h, w = img.shape[:2]
        x1 = max(0, min(x, w - 1))
        y1 = max(0, min(y, h - 1))
        x2 = max(x1 + 1, min(x + width, w))
        y2 = max(y1 + 1, min(y + height, h))

        crop_w = x2 - x1
        crop_h = y2 - y1

        # Strict validation
        dim_check = self.validate_template_dimensions(crop_w, crop_h, screen_w=w, screen_h=h)
        if not dim_check["valid"]:
            return False, "; ".join(dim_check["errors"]), None

        crop = img[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            return False, "Selected region is too small to serve as an identifiable template.", None

        if float(np.std(crop)) < 0.1:
            return False, "Selected region contains uniform flat color with no distinguishable edges or text.", None

        cv2.imwrite(str(target_path), crop)
        return True, f"Template '{template_name}' successfully created ({crop_w}x{crop_h} px).", template_name

    def compare_templates(self, template_a: str, template_b: str) -> Dict[str, Any]:
        """Compares two templates side-by-side."""
        path_a = safe_resolve_path(self.templates_dir, template_a)
        path_b = safe_resolve_path(self.templates_dir, template_b)

        if not path_a.exists() or not path_b.exists():
            return {"error": "One or both template files not found."}

        img_a = cv2.imread(str(path_a))
        img_b = cv2.imread(str(path_b))

        h_a, w_a = img_a.shape[:2]
        h_b, w_b = img_b.shape[:2]

        # Resize img_b to match img_a for difference calculation
        resized_b = cv2.resize(img_b, (w_a, h_a))
        diff = cv2.absdiff(img_a, resized_b)
        mean_diff = np.mean(diff)
        similarity = max(0.0, 1.0 - (mean_diff / 255.0))

        return {
            "template_a": {"name": template_a, "width": w_a, "height": h_a},
            "template_b": {"name": template_b, "width": w_b, "height": h_b},
            "similarity": round(float(similarity), 4),
            "dimensions_match": (w_a == w_b and h_a == h_b)
        }

cv_service = ComputerVisionService()
