"""
Employee data service managing CSV persistence, querying, pagination, validation,
automated backup, anomaly detection, and atomic thread-safe transactions.
Preserves existing records in results/employees.csv.
"""

import os
import csv
import re
import shutil
import threading
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from backend.config import EMPLOYEE_CSV_PATH, RESULTS_DIR

class EmployeeService:
    def __init__(self, csv_path: Path = EMPLOYEE_CSV_PATH):
        self.csv_path = Path(csv_path)
        self.backups_dir = self.csv_path.parent / "backups"
        self.lock = threading.RLock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Employee ID", "Name", "Department", "Created At"])

    def create_backup(self, reason: str = "manual") -> str:
        """Creates a timestamped snapshot of employees.csv in results/backups/."""
        with self.lock:
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_reason = re.sub(r"[^a-zA-Z0-9_]", "", reason) or "backup"
            backup_name = f"employees_backup_{ts}_{clean_reason}.csv"
            backup_path = self.backups_dir / backup_name
            
            if self.csv_path.exists():
                shutil.copy2(str(self.csv_path), str(backup_path))
            else:
                with open(backup_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Employee ID", "Name", "Department", "Created At"])
            return backup_name

    def list_backups(self) -> List[Dict[str, Any]]:
        """Lists available CSV backups."""
        with self.lock:
            backups = []
            if self.backups_dir.exists():
                for p in self.backups_dir.glob("*.csv"):
                    stat = p.stat()
                    backups.append({
                        "filename": p.name,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            return backups

    def restore_backup(self, backup_name: str) -> Tuple[bool, str]:
        """Safely restores employees.csv from an existing backup."""
        with self.lock:
            backup_path = (self.backups_dir / backup_name).resolve()
            try:
                backup_path.relative_to(self.backups_dir.resolve())
            except ValueError:
                return False, "Access denied: backup path escapes directory."

            if not backup_path.exists():
                return False, f"Backup '{backup_name}' not found."

            # Create safety snapshot of current before restoring
            self.create_backup("pre_restore")
            shutil.copy2(str(backup_path), str(self.csv_path))
            return True, f"Successfully restored CSV from {backup_name}."

    def get_all_records(self) -> List[Dict[str, str]]:
        with self.lock:
            if not self.csv_path.exists():
                return []
            records = []
            with open(self.csv_path, "r", newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {
                        "Employee ID": row.get("Employee ID", "").strip(),
                        "Name": row.get("Name", "").strip(),
                        "Department": row.get("Department", "").strip(),
                        "Created At": row.get("Created At", "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    if cleaned["Employee ID"]:
                        records.append(cleaned)
            return records

    def audit_records(self) -> Dict[str, Any]:
        """
        Audits existing CSV data for historical anomalies without modifying them.
        Detects duplicates, concatenated text from un-cleared UI fields, and empty names.
        """
        records = self.get_all_records()
        id_counts: Dict[str, int] = {}
        for r in records:
            eid = r["Employee ID"]
            id_counts[eid] = id_counts.get(eid, 0) + 1

        anomalies = []
        for idx, r in enumerate(records, start=1):
            eid = r["Employee ID"]
            name = r["Name"]
            dept = r["Department"]
            reasons = []

            # 1. Duplicate ID check
            if id_counts.get(eid, 0) > 1:
                reasons.append(f"Duplicate Employee ID '{eid}' (appears {id_counts[eid]} times)")

            # 2. Suspicious concatenated strings (e.g. ITemp004, ITemp004emp002)
            if re.search(r"[a-zA-Z]+emp\d+", dept, re.IGNORECASE) or re.search(r"\d{3,}[a-zA-Z]+", dept):
                reasons.append(f"Suspicious concatenated department '{dept}' (likely caused by typing without clearing field)")

            # 3. Missing/blank or abnormal name
            if not name or name == eid:
                reasons.append("Blank or placeholder employee name")
            elif name.lower() in ["it", "cse", "hr"] and dept.lower().startswith(name.lower()):
                reasons.append(f"Name '{name}' matches department prefix (likely typed in wrong field focus)")

            if reasons:
                anomalies.append({
                    "row_index": idx,
                    "record": r,
                    "issues": reasons,
                    "recommended_action": "Review or edit row values using the record editor."
                })

        return {
            "total_records": len(records),
            "anomalies_count": len(anomalies),
            "has_anomalies": len(anomalies) > 0,
            "anomalies": anomalies,
            "explanation": (
                "Historical records with concatenated values (e.g. ITemp004emp002) resulted from "
                "legacy automation typing into Tkinter form entries without clearing existing content first. "
                "OmniRPA now clears input fields (Ctrl+A -> Backspace) before typing to guarantee clean writes."
            )
        }

    def search_and_filter(
        self,
        query: str = "",
        department: str = "",
        sort_by: str = "Created At",
        ascending: bool = False,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        all_records = self.get_all_records()
        filtered = []

        q_lower = query.lower().strip()
        dept_lower = department.lower().strip()

        for rec in all_records:
            match_q = (
                not q_lower
                or q_lower in rec["Employee ID"].lower()
                or q_lower in rec["Name"].lower()
                or q_lower in rec["Department"].lower()
            )
            match_dept = not dept_lower or dept_lower == rec["Department"].lower()
            if match_q and match_dept:
                filtered.append(rec)

        # Sort
        valid_cols = ["Employee ID", "Name", "Department", "Created At"]
        sort_key = sort_by if sort_by in valid_cols else "Created At"
        filtered.sort(key=lambda x: x.get(sort_key, ""), reverse=not ascending)

        # Pagination
        total_items = len(filtered)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        paginated = filtered[start_idx:start_idx + page_size]

        return {
            "records": paginated,
            "total_count": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    def add_employee(self, emp_id: str, name: str, department: str) -> Tuple[bool, str, Optional[Dict[str, str]]]:
        emp_id = emp_id.strip()
        name = name.strip()
        department = department.strip()

        if not emp_id or not name or not department:
            return False, "All fields (Employee ID, Name, Department) are required.", None

        with self.lock:
            records = self.get_all_records()
            # Check for duplicate ID
            for r in records:
                if r["Employee ID"].lower() == emp_id.lower():
                    return False, f"Employee ID '{emp_id}' already exists. Duplicate IDs are rejected for data integrity.", None

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_record = {
                "Employee ID": emp_id,
                "Name": name,
                "Department": department,
                "Created At": created_at
            }

            records.append(new_record)
            self._write_records(records)
            return True, "Employee added successfully.", new_record

    def update_employee(self, emp_id: str, new_name: str, new_department: str) -> Tuple[bool, str]:
        new_name = new_name.strip()
        new_department = new_department.strip()

        if not new_name or not new_department:
            return False, "Name and Department cannot be empty."

        with self.lock:
            records = self.get_all_records()
            found = False
            for r in records:
                if r["Employee ID"] == emp_id:
                    r["Name"] = new_name
                    r["Department"] = new_department
                    found = True
                    break

            if not found:
                return False, f"Employee ID '{emp_id}' not found."

            self._write_records(records)
            return True, "Employee updated successfully."

    def delete_employee(self, emp_id: str) -> Tuple[bool, str]:
        with self.lock:
            records = self.get_all_records()
            initial_len = len(records)
            records = [r for r in records if r["Employee ID"] != emp_id]

            if len(records) == initial_len:
                return False, f"Employee ID '{emp_id}' not found."

            self._write_records(records)
            return True, "Employee deleted successfully."

    def _write_records(self, records: List[Dict[str, str]]):
        """Atomic CSV file write with temp file replacement and fsync."""
        temp_file = self.csv_path.with_suffix(f".tmp_{int(datetime.now().timestamp() * 1000)}")
        try:
            with open(temp_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Employee ID", "Name", "Department", "Created At"])
                for r in records:
                    writer.writerow([r["Employee ID"], r["Name"], r["Department"], r["Created At"]])
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.csv_path)
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

    def get_department_summary(self) -> Dict[str, Any]:
        records = self.get_all_records()
        departments: Dict[str, int] = {}
        for r in records:
            dept = r.get("Department") or "Unassigned"
            departments[dept] = departments.get(dept, 0) + 1
        return {
            "total_employees": len(records),
            "departments": departments
        }

    def verify_record_exists(self, emp_id: str, name: str = None, department: str = None) -> bool:
        records = self.get_all_records()
        for r in records:
            if r["Employee ID"] == emp_id:
                if name and r["Name"] != name:
                    continue
                if department and r["Department"] != department:
                    continue
                return True
        return False

    def import_csv(self, file_content: str) -> Tuple[int, int, List[str]]:
        """Imports CSV records with validation. Returns (added_count, skipped_count, error_messages)."""
        lines = file_content.strip().splitlines()
        if not lines:
            return 0, 0, ["Empty file provided."]

        reader = csv.DictReader(lines)
        if not reader.fieldnames or not {"Employee ID", "Name", "Department"}.issubset(set(reader.fieldnames)):
            return 0, 0, ["Invalid CSV header. Expected columns: Employee ID, Name, Department, Created At"]

        added = 0
        skipped = 0
        errors = []

        existing = {r["Employee ID"].lower(): r for r in self.get_all_records()}
        to_add = []

        for row_num, row in enumerate(reader, start=2):
            eid = row.get("Employee ID", "").strip()
            name = row.get("Name", "").strip()
            dept = row.get("Department", "").strip()
            cat = row.get("Created At", "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not eid or not name or not dept:
                skipped += 1
                errors.append(f"Row {row_num}: Missing required field.")
                continue

            if eid.lower() in existing:
                skipped += 1
                errors.append(f"Row {row_num}: Duplicate ID '{eid}' already exists.")
                continue

            new_item = {
                "Employee ID": eid,
                "Name": name,
                "Department": dept,
                "Created At": cat
            }
            existing[eid.lower()] = new_item
            to_add.append(new_item)
            added += 1

        if to_add:
            with self.lock:
                records = self.get_all_records()
                records.extend(to_add)
                self._write_records(records)

        return added, skipped, errors

employee_service = EmployeeService()
