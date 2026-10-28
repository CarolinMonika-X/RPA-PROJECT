"""
Automation Engine & Process Manager.
Executes workflows, coordinates computer vision matching, manages execution state transitions,
enforces desktop concurrency locks, provides interactive confirmation broker, and captures logs.
"""

import time
import uuid
import threading
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import pyautogui
import pygetwindow as gw
from backend.config import APP_TITLE_TARGET, SCREENSHOTS_DIR, RESULTS_DIR
from backend.models import Workflow, WorkflowStep
from backend.services.db_service import db_service
from backend.services.cv_service import cv_service
from backend.services.ocr_service import ocr_service
from backend.services.employee_service import employee_service
from backend.services.workflow_service import workflow_service
from backend.utils.logger import ExecutionLogger

class AutomationEngine:
    def __init__(self):
        self.lock = threading.RLock()
        self.active_execution_id: Optional[str] = None
        self.active_thread: Optional[threading.Thread] = None
        self.current_state: str = "IDLE"  # IDLE, RUNNING, AWAITING_CONFIRMATION, COMPLETED
        self.cancel_requested: bool = False
        self.confirmation_event = threading.Event()
        self.confirmation_response: Optional[str] = None
        self.active_logger: Optional[ExecutionLogger] = None
        self.last_detection_result: Optional[Dict[str, Any]] = None

    def is_running(self) -> bool:
        with self.lock:
            return self.current_state in ["RUNNING", "AWAITING_CONFIRMATION"]

    def start_execution(
        self,
        workflow_id: str,
        input_params: Dict[str, Any] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Starts an execution of the given workflow.
        Enforces desktop concurrency locking to prevent multiple runs from interfering.
        """
        input_params = input_params or {}
        workflow = workflow_service.get_workflow(workflow_id)
        if not workflow:
            return {"success": False, "error": f"Workflow '{workflow_id}' not found."}

        with self.lock:
            if self.current_state in ["RUNNING", "AWAITING_CONFIRMATION"]:
                return {
                    "success": False,
                    "error": "Another automation execution is currently running. Desktop control is locked to avoid collision.",
                    "active_execution_id": self.active_execution_id
                }

            exec_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            self.active_execution_id = exec_id
            self.current_state = "RUNNING"
            self.cancel_requested = False
            self.confirmation_event.clear()
            self.confirmation_response = None
            self.active_logger = ExecutionLogger(exec_id)
            self.last_detection_result = None

            # Record initial execution in SQLite
            db_service.create_execution({
                "id": exec_id,
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "status": "RUNNING",
                "start_time": datetime.now().isoformat(),
                "step_count": len(workflow.steps),
                "dry_run": dry_run,
                "trigger_source": "web_dashboard"
            })

            # Launch runner in background thread
            self.active_thread = threading.Thread(
                target=self._run_workflow_worker,
                args=(exec_id, workflow, input_params, dry_run),
                daemon=True
            )
            self.active_thread.start()

            return {
                "success": True,
                "execution_id": exec_id,
                "status": "RUNNING",
                "workflow_name": workflow.name,
                "step_count": len(workflow.steps),
                "dry_run": dry_run
            }

    def respond_confirmation(self, exec_id: str, action: str) -> Dict[str, Any]:
        """User responds to explicit confirmation prompt via Web UI."""
        with self.lock:
            if self.active_execution_id != exec_id or self.current_state != "AWAITING_CONFIRMATION":
                return {"success": False, "error": "Execution is not currently awaiting confirmation."}

            self.confirmation_response = action.strip().upper()
            self.confirmation_event.set()
            return {"success": True, "action": self.confirmation_response}

    def cancel_execution(self, exec_id: str) -> Dict[str, Any]:
        """Cancels an ongoing automation execution."""
        with self.lock:
            if self.active_execution_id != exec_id:
                return {"success": False, "error": "Specified execution is not currently active."}

            self.cancel_requested = True
            # Unblock confirmation if waiting
            self.confirmation_response = "CANCEL"
            self.confirmation_event.set()
            return {"success": True, "message": "Cancellation request sent to execution engine."}

    def get_status(self) -> Dict[str, Any]:
        """Returns current engine status, active run, and latest logs."""
        with self.lock:
            status = {
                "state": self.current_state,
                "active_execution_id": self.active_execution_id,
                "last_detection": self.last_detection_result
            }
            if self.active_logger:
                status["recent_logs"] = self.active_logger.get_entries(since_index=0)
            return status

    def _substitute_variables(self, text: str, params: Dict[str, Any]) -> str:
        for k, v in params.items():
            text = text.replace(f"{{{{{k}}}}}", str(v))
        return text

    def _run_workflow_worker(
        self,
        exec_id: str,
        workflow: Workflow,
        input_params: Dict[str, Any],
        dry_run: bool
    ):
        """Worker thread executing the steps of the workflow."""
        start_time = datetime.now()
        logger = self.active_logger
        logger.info(f"Starting workflow '{workflow.name}' (Dry-run: {dry_run})")
        
        # Take before-screenshot
        before_screenshot = None
        try:
            shot_path, _, _ = cv_service.capture_screenshot(f"before_{exec_id}.png")
            before_screenshot = shot_path.name
        except Exception as e:
            logger.warn(f"Initial screenshot capture warning: {e}")

        completed_steps = 0
        error_summary = None
        final_status = "SUCCESS"
        max_confidence = 0.0
        detected_coords = None

        for idx, step in enumerate(workflow.steps):
            if self.cancel_requested:
                final_status = "CANCELLED"
                error_summary = "Execution cancelled by user."
                logger.warn("Execution cancelled by user request.")
                break

            step_start = datetime.now()
            logger.info(f"Executing Step {idx+1}/{len(workflow.steps)}: {step.name}", step_index=idx)
            step_status = "RUNNING"
            step_error = None
            step_details = {}

            try:
                # 1. ACTIVATE WINDOW
                if step.type == "activate_window":
                    title = step.params.get("title_pattern", APP_TITLE_TARGET)
                    if not dry_run:
                        windows = gw.getWindowsWithTitle(title)
                        if not windows:
                            raise RuntimeError(f"Target application window '{title}' was not found. Please launch python main.py first.")
                        app_win = windows[0]
                        if app_win.isMinimized:
                            app_win.restore()
                        app_win.activate()
                        time.sleep(0.5)
                        logger.info(f"Activated window: {app_win.title}")
                    else:
                        logger.info(f"[Dry-Run] Simulated window activation for: {title}")

                # 2. WAIT
                elif step.type == "wait":
                    ms = step.params.get("milliseconds", 500)
                    time.sleep(ms / 1000.0)

                # 3. TYPE TEXT
                elif step.type == "type_text":
                    raw_text = step.params.get("text", "")
                    text_to_type = self._substitute_variables(raw_text, input_params)
                    interval = float(step.params.get("interval", 0.05))
                    clear_first = bool(step.params.get("clear_first", True))
                    if not dry_run:
                        if clear_first:
                            pyautogui.hotkey("ctrl", "a")
                            time.sleep(0.04)
                            pyautogui.press("backspace")
                            time.sleep(0.04)
                        pyautogui.write(text_to_type, interval=interval)
                        logger.info(f"Typed text into active element ({len(text_to_type)} chars, cleared_first={clear_first})")
                    else:
                        logger.info(f"[Dry-Run] Simulated typing: '{text_to_type}' (cleared_first={clear_first})")

                # 4. PRESS KEY
                elif step.type == "press_key":
                    key = step.params.get("key", "tab")
                    if not dry_run:
                        pyautogui.press(key)
                        logger.info(f"Pressed key: {key}")
                    else:
                        logger.info(f"[Dry-Run] Simulated pressing key: {key}")

                # 5. SCREENSHOT
                elif step.type == "screenshot":
                    shot_label = step.params.get("label", f"step_{idx+1}")
                    shot_path, w, h = cv_service.capture_screenshot(f"{exec_id}_{shot_label}.png")
                    step_details["screenshot"] = shot_path.name
                    logger.info(f"Captured screenshot: {shot_path.name} ({w}x{h})")

                # 6. IMAGE DETECTION
                elif step.type == "image_detection":
                    tmpl_name = step.params.get("template_name", "save_employee.png")
                    thresh = float(step.params.get("threshold", 0.80))
                    multi_scale = bool(step.params.get("multi_scale", True))
                    
                    # Capture current screen to match against
                    current_shot_path, _, _ = cv_service.capture_screenshot(f"detect_screen_{exec_id}.png")
                    match_res = cv_service.match_template(
                        current_shot_path,
                        template_name=tmpl_name,
                        threshold=thresh,
                        multi_scale=multi_scale,
                        save_annotation=True
                    )
                    
                    conf = match_res.get("confidence", 0.0)
                    max_confidence = max(max_confidence, conf)
                    step_details["confidence"] = conf
                    step_details["match_result"] = match_res
                    self.last_detection_result = match_res

                    if not match_res.get("success"):
                        raise RuntimeError(
                            f"Image detection confidence {conf:.2%} fell below required threshold {thresh:.2%}. "
                            f"Diagnostics: {'; '.join(match_res.get('diagnostics', []))}"
                        )
                    
                    detected_coords = (match_res["center"]["x"], match_res["center"]["y"])
                    logger.info(f"Detected '{tmpl_name}' with {conf:.2%} confidence at {detected_coords}")

                # 7. REQUEST CONFIRMATION (Critical safety requirement)
                elif step.type == "request_confirmation":
                    prompt_msg = step.params.get("prompt", "Confirm saving employee record to legacy system?")
                    logger.warn(f"EXPLICIT CONFIRMATION REQUIRED: {prompt_msg}")
                    
                    with self.lock:
                        self.current_state = "AWAITING_CONFIRMATION"
                    
                    db_service.update_execution(exec_id, {"status": "AWAITING_CONFIRMATION"})
                    
                    # Wait for user input via UI or timeout (60 seconds)
                    confirmed = self.confirmation_event.wait(timeout=60.0)
                    with self.lock:
                        self.current_state = "RUNNING"
                        
                    if not confirmed or self.confirmation_response != "CONFIRM":
                        raise RuntimeError("Explicit confirmation was declined or timed out. Automation halted for safety.")
                    
                    logger.info("Explicit user confirmation granted. Proceeding with execution.")

                # 8. CLICK DETECTED
                elif step.type == "click_detected":
                    if not detected_coords:
                        raise RuntimeError("No detected element coordinates available to click. Run image_detection step first.")
                    
                    offset_x = int(step.params.get("offset_x", 0))
                    offset_y = int(step.params.get("offset_y", 0))
                    click_x = detected_coords[0] + offset_x
                    click_y = detected_coords[1] + offset_y

                    if not dry_run:
                        pyautogui.click(click_x, click_y)
                        logger.info(f"Clicked detected element at ({click_x}, {click_y})")
                    else:
                        logger.info(f"[Dry-Run] Simulated click at ({click_x}, {click_y})")

                # 9. OCR DETECT
                elif step.type == "ocr_detect":
                    search_text = step.params.get("search_text", "Save Employee")
                    current_shot_path, _, _ = cv_service.capture_screenshot(f"ocr_screen_{exec_id}.png")
                    ocr_res = ocr_service.find_label_element(current_shot_path, search_text)
                    step_details["ocr_result"] = ocr_res
                    
                    if not ocr_res.get("success"):
                        raise RuntimeError(f"OCR element detection failed for '{search_text}'.")
                    
                    if "center" in ocr_res:
                        detected_coords = (ocr_res["center"]["x"], ocr_res["center"]["y"])
                    elif ocr_res.get("candidates"):
                        c = ocr_res["candidates"][0]
                        detected_coords = (c["center"]["x"], c["center"]["y"])

                    logger.info(f"OCR located '{search_text}' at {detected_coords}")

                # 10. VALIDATION
                elif step.type == "validation":
                    target = step.params.get("target", "csv")
                    emp_id = self._substitute_variables(step.params.get("employee_id", ""), input_params)
                    
                    if target == "csv" and emp_id:
                        if not dry_run:
                            # Recheck CSV file
                            verified = employee_service.verify_record_exists(emp_id)
                            if not verified:
                                raise RuntimeError(f"Record validation failed: Employee ID '{emp_id}' not found in CSV.")
                            logger.info(f"Verified Employee ID '{emp_id}' successfully saved in results/employees.csv")
                        else:
                            logger.info(f"[Dry-Run] Simulated CSV record verification for '{emp_id}'")

                step_status = "SUCCESS"
                completed_steps += 1

            except Exception as ex:
                step_status = "FAILED"
                step_error = str(ex)
                logger.error(f"Step '{step.name}' failed: {step_error}", step_index=idx)
                
                # Capture failure screenshot
                try:
                    fail_shot, _, _ = cv_service.capture_screenshot(f"fail_{exec_id}_step_{idx+1}.png")
                    step_details["failure_screenshot"] = fail_shot.name
                except Exception:
                    pass

                if not step.continue_on_failure:
                    final_status = "FAILED"
                    error_summary = step_error
                    break

            finally:
                step_end = datetime.now()
                step_duration = (step_end - step_start).total_seconds()
                
                # Persist step event
                db_service.add_step_event(exec_id, {
                    "step_index": idx,
                    "step_name": step.name,
                    "step_type": step.type,
                    "status": step_status,
                    "start_time": step_start.isoformat(),
                    "end_time": step_end.isoformat(),
                    "duration_seconds": round(step_duration, 3),
                    "confidence": step_details.get("confidence"),
                    "error_message": step_error,
                    "details": step_details
                })

        # Capture after-screenshot
        after_screenshot = None
        try:
            after_shot, _, _ = cv_service.capture_screenshot(f"after_{exec_id}.png")
            after_screenshot = after_shot.name
        except Exception:
            pass

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # Update final execution in SQLite
        db_service.update_execution(exec_id, {
            "status": final_status,
            "end_time": end_time.isoformat(),
            "duration_seconds": round(total_duration, 2),
            "completed_steps": completed_steps,
            "max_confidence": round(max_confidence, 4),
            "error_summary": error_summary,
            "screenshot_before": before_screenshot,
            "screenshot_after": after_screenshot
        })

        # Save all logged entries to DB
        if logger:
            for log_entry in logger.get_entries():
                db_service.add_log_entry(exec_id, log_entry)

        with self.lock:
            self.current_state = "IDLE"
            self.active_execution_id = None
            logger.info(f"Workflow finished with status: {final_status} (Duration: {total_duration:.2f}s)")

automation_engine = AutomationEngine()
