"""
Workflow management service.
Handles validation, saving, loading, importing, and exporting JSON workflows with schema versioning.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.config import WORKFLOWS_DIR
from backend.models import Workflow, WorkflowStep
from backend.utils.security import safe_resolve_path

class WorkflowService:
    def __init__(self, workflows_dir: Path = WORKFLOWS_DIR):
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_workflows()

    def _ensure_sample_workflows(self):
        """Creates sample workflows if directory is empty."""
        sample_path = self.workflows_dir / "employee_registration.json"
        if not sample_path.exists():
            wf = Workflow(
                id="wf_employee_registration",
                name="Legacy Employee Registration",
                description="End-to-end automation filling employee credentials, detecting Save button via OpenCV, and verifying CSV records.",
                version="2.0",
                steps=[
                    WorkflowStep(
                        id="s1",
                        type="activate_window",
                        name="Activate Legacy EMS Window",
                        params={"title_pattern": "Legacy Employee Management System"}
                    ),
                    WorkflowStep(
                        id="s2",
                        type="wait",
                        name="Wait for Window Activation",
                        params={"milliseconds": 600}
                    ),
                    WorkflowStep(
                        id="s3",
                        type="type_text",
                        name="Type Employee ID",
                        params={"text": "{{employee_id}}", "interval": 0.05}
                    ),
                    WorkflowStep(
                        id="s4",
                        type="press_key",
                        name="Tab to Name Field",
                        params={"key": "tab"}
                    ),
                    WorkflowStep(
                        id="s5",
                        type="type_text",
                        name="Type Employee Name",
                        params={"text": "{{employee_name}}", "interval": 0.05}
                    ),
                    WorkflowStep(
                        id="s6",
                        type="press_key",
                        name="Tab to Department Field",
                        params={"key": "tab"}
                    ),
                    WorkflowStep(
                        id="s7",
                        type="type_text",
                        name="Type Department",
                        params={"text": "{{department}}", "interval": 0.05}
                    ),
                    WorkflowStep(
                        id="s8",
                        type="screenshot",
                        name="Capture Form Screenshot",
                        params={"label": "form_filled"}
                    ),
                    WorkflowStep(
                        id="s9",
                        type="image_detection",
                        name="Detect Save Button via OpenCV",
                        params={"template_name": "save_employee.png", "threshold": 0.80, "multi_scale": True}
                    ),
                    WorkflowStep(
                        id="s10",
                        type="request_confirmation",
                        name="Explicit User Confirmation Prompt",
                        params={"prompt": "Confirm saving employee record to legacy system?"}
                    ),
                    WorkflowStep(
                        id="s11",
                        type="click_detected",
                        name="Click Save Employee Button",
                        params={"offset_x": 0, "offset_y": 0}
                    ),
                    WorkflowStep(
                        id="s12",
                        type="wait",
                        name="Wait for Dialog",
                        params={"milliseconds": 800}
                    ),
                    WorkflowStep(
                        id="s13",
                        type="press_key",
                        name="Dismiss Confirmation Dialog",
                        params={"key": "enter"}
                    ),
                    WorkflowStep(
                        id="s14",
                        type="validation",
                        name="Verify Record in CSV File",
                        params={"target": "csv", "employee_id": "{{employee_id}}"}
                    )
                ]
            )
            self.save_workflow(wf)

        # Inspection workflow
        inspect_path = self.workflows_dir / "button_inspection.json"
        if not inspect_path.exists():
            wf_insp = Workflow(
                id="wf_button_inspection",
                name="Button Detection & Visual Inspection",
                description="Captures current desktop, runs multi-scale template matching, and reports detection coordinates without clicking.",
                version="2.0",
                steps=[
                    WorkflowStep(
                        id="step_capture",
                        type="screenshot",
                        name="Capture Desktop Screen",
                        params={"label": "inspection_screen"}
                    ),
                    WorkflowStep(
                        id="step_detect",
                        type="image_detection",
                        name="Locate Save Button Template",
                        params={"template_name": "save_employee.png", "threshold": 0.80, "multi_scale": True}
                    )
                ]
            )
            self.save_workflow(wf_insp)

    def list_workflows(self) -> List[Dict[str, Any]]:
        workflows = []
        for file_path in self.workflows_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    workflows.append({
                        "id": data.get("id", file_path.stem),
                        "filename": file_path.name,
                        "name": data.get("name", file_path.stem),
                        "description": data.get("description", ""),
                        "step_count": len(data.get("steps", [])),
                        "version": data.get("version", "2.0"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at")
                    })
            except Exception:
                continue
        workflows.sort(key=lambda x: x["name"])
        return workflows

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        # Try exact filename or match ID
        for file_path in self.workflows_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id") == workflow_id or file_path.stem == workflow_id:
                        return Workflow.from_dict(data)
            except Exception:
                continue
        return None

    def save_workflow(self, workflow: Workflow) -> Tuple[bool, str]:
        errors = workflow.validate()
        if errors:
            return False, "; ".join(errors)

        filename = f"{workflow.id}.json"
        target_path = safe_resolve_path(self.workflows_dir, filename)

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(workflow.to_dict(), f, indent=2)

        return True, f"Workflow '{workflow.name}' saved successfully."

    def delete_workflow(self, workflow_id: str) -> Tuple[bool, str]:
        target_to_delete = None
        for file_path in self.workflows_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id") == workflow_id or file_path.stem == workflow_id:
                        target_to_delete = file_path
                        break
            except Exception:
                continue

        if target_to_delete and target_to_delete.exists():
            target_to_delete.unlink()
            return True, f"Workflow '{workflow_id}' deleted."
        return False, f"Workflow '{workflow_id}' not found."

    def duplicate_workflow(self, workflow_id: str, new_name: str) -> Tuple[bool, str, Optional[Workflow]]:
        orig = self.get_workflow(workflow_id)
        if not orig:
            return False, "Original workflow not found.", None

        new_id = f"wf_{int(os.times().elapsed * 1000)}"
        new_wf = Workflow(
            id=new_id,
            name=new_name or f"{orig.name} (Copy)",
            description=orig.description,
            steps=orig.steps,
            version=orig.version
        )
        success, msg = self.save_workflow(new_wf)
        return success, msg, new_wf if success else None

workflow_service = WorkflowService()
