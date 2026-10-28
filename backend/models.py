"""
Domain models and schema definitions for the RPA Platform.
Enforces typed schemas for workflows, executions, computer vision results, and employee records.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

VALID_STEP_TYPES = [
    "activate_window",
    "type_text",
    "press_key",
    "wait",
    "screenshot",
    "image_detection",
    "click_detected",
    "request_confirmation",
    "ocr_detect",
    "validation",
    "conditional"
]

@dataclass
class WorkflowStep:
    id: str
    type: str
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 10.0
    retry_count: int = 1
    continue_on_failure: bool = False
    
    def validate(self) -> List[str]:
        errors = []
        if self.type not in VALID_STEP_TYPES:
            errors.append(f"Step '{self.name}': Invalid type '{self.type}'. Must be one of {VALID_STEP_TYPES}")
        if not self.name or not self.name.strip():
            errors.append("Step name cannot be empty.")
            
        # Parameter validation
        if self.type == "activate_window" and not self.params.get("title_pattern"):
            errors.append(f"Step '{self.name}': 'title_pattern' is required for activate_window.")
        elif self.type == "type_text" and "text" not in self.params:
            errors.append(f"Step '{self.name}': 'text' is required for type_text.")
        elif self.type == "press_key" and not self.params.get("key"):
            errors.append(f"Step '{self.name}': 'key' is required for press_key.")
        elif self.type == "image_detection" and not self.params.get("template_name"):
            errors.append(f"Step '{self.name}': 'template_name' is required for image_detection.")
        elif self.type == "ocr_detect" and not self.params.get("search_text"):
            errors.append(f"Step '{self.name}': 'search_text' is required for ocr_detect.")
            
        return errors

@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    version: str = "2.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [asdict(step) for step in self.steps],
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        steps_data = data.get("steps", [])
        steps = [
            WorkflowStep(
                id=s.get("id", str(idx + 1)),
                type=s.get("type", "wait"),
                name=s.get("name", f"Step {idx + 1}"),
                params=s.get("params", {}),
                timeout_seconds=float(s.get("timeout_seconds", 10.0)),
                retry_count=int(s.get("retry_count", 1)),
                continue_on_failure=bool(s.get("continue_on_failure", False))
            )
            for idx, s in enumerate(steps_data)
        ]
        return cls(
            id=str(data.get("id", "workflow_default")),
            name=str(data.get("name", "Untitled Workflow")),
            description=str(data.get("description", "")),
            steps=steps,
            version=str(data.get("version", "2.0")),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )

    def validate(self) -> List[str]:
        errors = []
        if not self.name or not self.name.strip():
            errors.append("Workflow name cannot be empty.")
        if not self.steps:
            errors.append("Workflow must contain at least one step.")
        for step in self.steps:
            errors.extend(step.validate())
        return errors
