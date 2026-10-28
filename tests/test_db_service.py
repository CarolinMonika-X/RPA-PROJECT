"""
Unit tests for SQLite persistence and computed dashboard metrics.
"""

from backend.services.db_service import DatabaseService

def test_execution_lifecycle_and_metrics_calculation(tmp_path):
    db_file = tmp_path / "test_metrics.db"
    svc = DatabaseService(db_path=str(db_file))

    # Add sample executions
    svc.create_execution({
        "id": "exec_01",
        "workflow_id": "wf_1",
        "workflow_name": "Workflow One",
        "status": "RUNNING",
        "step_count": 3
    })
    svc.update_execution("exec_01", {
        "status": "SUCCESS",
        "duration_seconds": 4.5,
        "completed_steps": 3,
        "max_confidence": 0.95
    })

    svc.create_execution({
        "id": "exec_02",
        "workflow_id": "wf_1",
        "workflow_name": "Workflow One",
        "status": "RUNNING",
        "step_count": 3
    })
    svc.update_execution("exec_02", {
        "status": "FAILED",
        "duration_seconds": 2.0,
        "completed_steps": 1,
        "error_summary": "Vision confidence below threshold"
    })

    # Add failing step
    svc.add_step_event("exec_02", {
        "step_index": 1,
        "step_name": "Detect Button",
        "step_type": "image_detection",
        "status": "FAILED",
        "error_message": "Low confidence"
    })

    metrics = svc.get_dashboard_metrics()
    assert metrics["total_executions"] == 2
    assert metrics["successful_executions"] == 1
    assert metrics["failed_executions"] == 1
    assert metrics["success_rate"] == 50.0
    assert metrics["avg_duration"] == 3.25
    assert len(metrics["failing_steps"]) == 1
    assert metrics["failing_steps"][0]["step_name"] == "Detect Button"
