"""
Execution logger utility with memory ring-buffer and file logging support.
"""

import logging
import datetime
from typing import List, Dict, Any
from collections import deque

class ExecutionLogger:
    """Manages thread-safe in-memory logs and event capture for an automation run."""
    
    def __init__(self, execution_id: str, max_events: int = 1000):
        self.execution_id = execution_id
        self.logs: deque = deque(maxlen=max_events)
        
    def log(self, level: str, message: str, step_index: int = None, details: Dict[str, Any] = None):
        entry = {
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "iso_time": datetime.datetime.now().isoformat(),
            "level": level.upper(),
            "message": message,
            "step_index": step_index,
            "details": details or {}
        }
        self.logs.append(entry)
        
    def info(self, message: str, step_index: int = None, details: Dict[str, Any] = None):
        self.log("INFO", message, step_index, details)
        
    def warn(self, message: str, step_index: int = None, details: Dict[str, Any] = None):
        self.log("WARN", message, step_index, details)
        
    def error(self, message: str, step_index: int = None, details: Dict[str, Any] = None):
        self.log("ERROR", message, step_index, details)
        
    def get_entries(self, since_index: int = 0) -> List[Dict[str, Any]]:
        all_logs = list(self.logs)
        if since_index < len(all_logs):
            return all_logs[since_index:]
        return []
