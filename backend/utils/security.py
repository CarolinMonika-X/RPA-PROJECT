"""
Security and validation utilities.
Enforces strict filesystem boundaries, input validation, and prevents arbitrary execution.
"""

import os
from pathlib import Path
from werkzeug.utils import secure_filename
from backend.config import BASE_DIR, TEMPLATES_DIR, SCREENSHOTS_DIR, WORKFLOWS_DIR


def safe_resolve_path(base_dir: Path, filename: str) -> Path:
    """
    Safely resolves a file path within a trusted base directory.
    Rejects directory traversal attempts and dangerous filenames.
    """
    sanitized = secure_filename(filename)
    if not sanitized:
        raise ValueError("Invalid or empty filename provided.")
    
    target_path = (base_dir / sanitized).resolve()
    
    # Must be strictly inside the base directory
    try:
        target_path.relative_to(base_dir.resolve())
    except ValueError:
        raise PermissionError(f"Access denied: path escapes trusted boundary {base_dir}")
        
    return target_path


def sanitize_string(val: str, max_length: int = 120) -> str:
    """Sanitizes text input by trimming and truncating."""
    if not val:
        return ""
    cleaned = str(val).strip()
    return cleaned[:max_length]
