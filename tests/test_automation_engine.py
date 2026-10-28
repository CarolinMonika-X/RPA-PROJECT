"""
Unit tests for Automation Engine: state transitions, concurrency locks, and confirmation brokers.
"""

import time
import pytest
from backend.services.automation_engine import AutomationEngine
from backend.models import Workflow, WorkflowStep
from unittest.mock import MagicMock, patch

def test_engine_concurrency_lock():
    engine = AutomationEngine()

    mock_wf = Workflow(
        id="wf_mock",
        name="Mock Workflow",
        description="Testing locks",
        steps=[WorkflowStep(id="s1", name="Wait", type="wait", params={"milliseconds": 1500})]
    )

    with patch("backend.services.workflow_service.workflow_service.get_workflow", return_value=mock_wf):
        # Start first execution
        res1 = engine.start_execution("wf_mock", dry_run=True)
        assert res1["success"] is True
        assert engine.is_running() is True

        # Try to start a concurrent execution while first is active
        res2 = engine.start_execution("wf_mock", dry_run=True)
        assert res2["success"] is False
        assert "currently running" in res2["error"].lower()

        # Abort first execution
        engine.cancel_execution(res1["execution_id"])
        time.sleep(0.5)

def test_engine_explicit_confirmation_cycle():
    engine = AutomationEngine()

    mock_wf = Workflow(
        id="wf_confirm_test",
        name="Confirmation Test",
        description="Testing confirmation pause",
        steps=[
            WorkflowStep(id="s1", name="Wait", type="wait", params={"milliseconds": 100}),
            WorkflowStep(id="s2", name="Confirm Gate", type="request_confirmation", params={"prompt": "Confirm save?"}),
            WorkflowStep(id="s3", name="Finish", type="wait", params={"milliseconds": 100})
        ]
    )

    with patch("backend.services.workflow_service.workflow_service.get_workflow", return_value=mock_wf):
        res = engine.start_execution("wf_confirm_test", dry_run=True)
        exec_id = res["execution_id"]

        # Wait until engine reaches AWAITING_CONFIRMATION
        timeout = 3.0
        start = time.time()
        while time.time() - start < timeout:
            if engine.current_state == "AWAITING_CONFIRMATION":
                break
            time.sleep(0.1)

        assert engine.current_state == "AWAITING_CONFIRMATION"

        # Provide confirmation via API handler
        confirm_res = engine.respond_confirmation(exec_id, "CONFIRM")
        assert confirm_res["success"] is True

        # Wait for completion
        time.sleep(0.5)
        assert engine.current_state == "IDLE"
