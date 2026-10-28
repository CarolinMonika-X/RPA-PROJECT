"""
Unit tests for EmployeeService: CRUD, duplicate detection, pagination, and CSV import/export.
"""

from backend.services.employee_service import EmployeeService

def test_add_and_get_employee_records(temp_env):
    svc = EmployeeService(csv_path=temp_env["csv_path"])
    
    success, msg, rec = svc.add_employee("EMP100", "Alice Smith", "Engineering")
    assert success is True
    assert rec["Employee ID"] == "EMP100"
    
    records = svc.get_all_records()
    assert len(records) == 1
    assert records[0]["Name"] == "Alice Smith"

def test_prevent_duplicate_employee_ids(temp_env):
    svc = EmployeeService(csv_path=temp_env["csv_path"])
    
    svc.add_employee("EMP101", "Bob Brown", "Sales")
    # Duplicate ID attempt
    dup_success, dup_msg, _ = svc.add_employee("EMP101", "Bob Duplicate", "Marketing")
    assert dup_success is False
    assert "already exists" in dup_msg
    
    # Verify count remained 1
    assert len(svc.get_all_records()) == 1

def test_search_and_filter_records(temp_env):
    svc = EmployeeService(csv_path=temp_env["csv_path"])
    svc.add_employee("EMP201", "Charlie Day", "Finance")
    svc.add_employee("EMP202", "Dennis Reynolds", "Bar Management")
    svc.add_employee("EMP203", "Dee Reynolds", "Bar Management")

    # Search by query
    res = svc.search_and_filter(query="Reynolds")
    assert res["total_count"] == 2

    # Filter by department
    res_dept = svc.search_and_filter(department="Finance")
    assert res_dept["total_count"] == 1
    assert res_dept["records"][0]["Name"] == "Charlie Day"

def test_update_and_delete_employee(temp_env):
    svc = EmployeeService(csv_path=temp_env["csv_path"])
    svc.add_employee("EMP301", "Frank Reynolds", "Finance")

    # Update
    up_success, up_msg = svc.update_employee("EMP301", "Frank Reynolds", "Executive")
    assert up_success is True
    records = svc.get_all_records()
    assert records[0]["Department"] == "Executive"

    # Delete
    del_success, del_msg = svc.delete_employee("EMP301")
    assert del_success is True
    assert len(svc.get_all_records()) == 0

def test_import_csv_validation(temp_env):
    svc = EmployeeService(csv_path=temp_env["csv_path"])
    svc.add_employee("EMP401", "Existing User", "HR")

    csv_data = """Employee ID,Name,Department,Created At
EMP401,Duplicate User,HR,2026-10-28 12:00:00
EMP402,Valid User One,Operations,2026-10-28 12:00:00
EMP403,Valid User Two,IT,2026-10-28 12:00:00
,Bad Row Missing ID,IT,2026-10-28 12:00:00
"""
    added, skipped, errors = svc.import_csv(csv_data)
    assert added == 2
    assert skipped == 2  # One duplicate + one missing ID
    assert len(svc.get_all_records()) == 3
