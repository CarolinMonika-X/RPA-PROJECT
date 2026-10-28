"""
Database persistence service for execution history, run metrics, and activity logs using SQLite.
All statistics and dashboard metrics are computed strictly from real persisted records.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH

class DatabaseService:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Executions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                workflow_name TEXT,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                step_count INTEGER DEFAULT 0,
                completed_steps INTEGER DEFAULT 0,
                max_confidence REAL DEFAULT 0.0,
                error_summary TEXT,
                screenshot_before TEXT,
                screenshot_after TEXT,
                dry_run INTEGER DEFAULT 0,
                trigger_source TEXT DEFAULT 'manual'
            )
            """)
            
            # Step events table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                step_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                confidence REAL,
                error_message TEXT,
                details_json TEXT,
                FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
            )
            """)
            
            # Execution logs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                step_index INTEGER,
                details_json TEXT,
                FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
            )
            """)
            
            conn.commit()

    def create_execution(self, exec_data: Dict[str, Any]) -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO executions (
                id, workflow_id, workflow_name, status, start_time,
                step_count, dry_run, trigger_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exec_data["id"],
                exec_data.get("workflow_id", ""),
                exec_data.get("workflow_name", "Unknown"),
                exec_data.get("status", "RUNNING"),
                exec_data.get("start_time", datetime.now().isoformat()),
                exec_data.get("step_count", 0),
                1 if exec_data.get("dry_run", False) else 0,
                exec_data.get("trigger_source", "manual")
            ))
            conn.commit()
            return exec_data["id"]

    def update_execution(self, exec_id: str, updates: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for k, v in updates.items():
                fields.append(f"{k} = ?")
                values.append(v)
            values.append(exec_id)
            cursor.execute(f"UPDATE executions SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

    def add_step_event(self, exec_id: str, step_data: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO execution_steps (
                execution_id, step_index, step_name, step_type, status,
                start_time, end_time, duration_seconds, confidence, error_message, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exec_id,
                step_data.get("step_index", 0),
                step_data.get("step_name", ""),
                step_data.get("step_type", ""),
                step_data.get("status", "PENDING"),
                step_data.get("start_time", datetime.now().isoformat()),
                step_data.get("end_time"),
                step_data.get("duration_seconds"),
                step_data.get("confidence"),
                step_data.get("error_message"),
                json.dumps(step_data.get("details", {}))
            ))
            conn.commit()

    def add_log_entry(self, exec_id: str, log_data: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO execution_logs (
                execution_id, timestamp, level, message, step_index, details_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                exec_id,
                log_data.get("timestamp", datetime.now().isoformat()),
                log_data.get("level", "INFO"),
                log_data.get("message", ""),
                log_data.get("step_index"),
                json.dumps(log_data.get("details", {}))
            ))
            conn.commit()

    def get_execution(self, exec_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM executions WHERE id = ?", (exec_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            
            cursor.execute("SELECT * FROM execution_steps WHERE execution_id = ? ORDER BY step_index ASC", (exec_id,))
            res["steps"] = [dict(s) for s in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM execution_logs WHERE execution_id = ? ORDER BY id ASC", (exec_id,))
            res["logs"] = [dict(l) for l in cursor.fetchall()]
            return res

    def list_executions(self, limit: int = 50, status: str = None, workflow: str = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM executions WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if workflow:
                query += " AND workflow_name LIKE ?"
                params.append(f"%{workflow}%")
            query += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates actual dashboard overview statistics strictly from recorded history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM executions")
            total = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COUNT(*) as success FROM executions WHERE status = 'SUCCESS'")
            success = cursor.fetchone()["success"]
            
            cursor.execute("SELECT COUNT(*) as failed FROM executions WHERE status = 'FAILED'")
            failed = cursor.fetchone()["failed"]
            
            cursor.execute("SELECT COUNT(*) as cancelled FROM executions WHERE status = 'CANCELLED'")
            cancelled = cursor.fetchone()["cancelled"]

            cursor.execute("SELECT COUNT(*) as running FROM executions WHERE status = 'RUNNING'")
            running = cursor.fetchone()["running"]

            cursor.execute("SELECT COUNT(*) as awaiting FROM executions WHERE status = 'AWAITING_CONFIRMATION'")
            awaiting = cursor.fetchone()["awaiting"]
            
            cursor.execute("SELECT AVG(duration_seconds) as avg_duration FROM executions WHERE duration_seconds IS NOT NULL AND status IN ('SUCCESS', 'FAILED')")
            avg_dur = cursor.fetchone()["avg_duration"] or 0.0
            
            # Explicit, consistent definition: successful / completed definitive runs (success + failed)
            completed_definitive = success + failed
            success_rate = (success / completed_definitive * 100.0) if completed_definitive > 0 else 0.0
            
            # Most frequently failing steps
            cursor.execute("""
            SELECT step_name, COUNT(*) as fail_count 
            FROM execution_steps 
            WHERE status = 'FAILED' 
            GROUP BY step_name 
            ORDER BY fail_count DESC 
            LIMIT 5
            """)
            failing_steps = [dict(r) for r in cursor.fetchall()]

            # Latest execution record
            cursor.execute("SELECT * FROM executions ORDER BY start_time DESC LIMIT 1")
            latest_row = cursor.fetchone()
            latest_execution = dict(latest_row) if latest_row else None
            
            # Weekly trend (last 7 days)
            trends = []
            today = datetime.now().date()
            for i in range(6, -1, -1):
                day = today - timedelta(days=i)
                day_str = day.isoformat()
                cursor.execute("""
                SELECT 
                    COUNT(*) as total_day,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_day,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_day,
                    SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled_day
                FROM executions 
                WHERE date(start_time) = date(?)
                """, (day_str,))
                row = cursor.fetchone()
                trends.append({
                    "date": day.strftime("%b %d"),
                    "total": row["total_day"] or 0,
                    "success": row["success_day"] or 0,
                    "failed": row["failed_day"] or 0,
                    "cancelled": row["cancelled_day"] or 0
                })
                
            return {
                "total_executions": total,
                "successful_executions": success,
                "failed_executions": failed,
                "cancelled_executions": cancelled,
                "running_executions": running,
                "awaiting_confirmation_executions": awaiting,
                "completed_definitive_runs": completed_definitive,
                "success_rate": round(success_rate, 1),
                "success_rate_formula": "Successful / (Successful + Failed) — Excludes cancelled and active executions",
                "avg_duration": round(avg_dur, 2),
                "failing_steps": failing_steps,
                "latest_execution": latest_execution,
                "weekly_trends": trends
            }

db_service = DatabaseService()
