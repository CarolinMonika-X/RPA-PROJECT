"""
Integration tests for REST API endpoints and health checks.
"""

def test_api_health_endpoint(test_app):
    res = test_app.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "diagnostics" in data

def test_api_metrics_endpoint(test_app):
    res = test_app.get("/api/metrics")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "total_executions" in data["data"]

def test_api_workflows_endpoints(test_app):
    # List
    res = test_app.get("/api/workflows")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    # Create
    new_wf = {
        "id": "wf_api_test",
        "name": "API Test Workflow",
        "description": "Created via test",
        "steps": [{"id": "s1", "name": "Step 1", "type": "wait", "params": {"milliseconds": 100}}]
    }
    create_res = test_app.post("/api/workflows", json=new_wf)
    assert create_res.status_code == 201

    # Fetch
    get_res = test_app.get("/api/workflows/wf_api_test")
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["name"] == "API Test Workflow"

    # Delete
    del_res = test_app.delete("/api/workflows/wf_api_test")
    assert del_res.status_code == 200

def test_api_employees_endpoints(test_app):
    # Summary
    sum_res = test_app.get("/api/employees/summary")
    assert sum_res.status_code == 200
    assert "total_employees" in sum_res.get_json()["data"]

    # Export CSV
    export_res = test_app.get("/api/employees/export")
    assert export_res.status_code == 200
    assert "Employee ID" in export_res.data.decode("utf-8")

def test_api_settings_and_diagnostics(test_app):
    diag_res = test_app.get("/api/diagnostics")
    assert diag_res.status_code == 200
    assert diag_res.get_json()["data"]["status"] == "HEALTHY"

    set_res = test_app.get("/api/settings")
    assert set_res.status_code == 200
    assert "confidence_threshold" in set_res.get_json()["data"]
