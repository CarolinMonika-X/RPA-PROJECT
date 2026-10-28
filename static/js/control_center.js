/**
 * Automation Control Center Module
 * Handles starting runs, live log polling, step tracking, explicit confirmation, and abort.
 */

const ControlCenter = {
  currentExecId: null,
  pollTimer: null,
  logIndex: 0,

  init() {
    this.bindEvents();
    // Check if there's an ongoing run or query param
    const urlParams = new URLSearchParams(window.location.search);
    const execId = urlParams.get("id");
    if (execId) {
      this.attachToExecution(execId);
    }
  },

  bindEvents() {
    const startBtn = document.getElementById("startExecutionBtn");
    if (startBtn) {
      startBtn.addEventListener("click", () => this.startRun());
    }

    const abortBtn = document.getElementById("abortExecutionBtn");
    if (abortBtn) {
      abortBtn.addEventListener("click", () => this.abortRun());
    }

    const confirmYesBtn = document.getElementById("confirmActionYesBtn");
    if (confirmYesBtn) {
      confirmYesBtn.addEventListener("click", () => this.sendConfirmation("CONFIRM"));
    }

    const confirmNoBtn = document.getElementById("confirmActionNoBtn");
    if (confirmNoBtn) {
      confirmNoBtn.addEventListener("click", () => this.sendConfirmation("CANCEL"));
    }
  },

  async startRun() {
    const wfSelect = document.getElementById("workflowSelect");
    const empId = document.getElementById("inputEmpId")?.value.trim() || "EMP002";
    const empName = document.getElementById("inputEmpName")?.value.trim() || "Automation Test";
    const dept = document.getElementById("inputDept")?.value.trim() || "IT";
    const dryRun = document.getElementById("dryRunCheckbox")?.checked || false;

    if (!wfSelect || !wfSelect.value) {
      App.toast("Please select a workflow to execute.", "error");
      return;
    }

    const payload = {
      workflow_id: wfSelect.value,
      params: {
        employee_id: empId,
        employee_name: empName,
        department: dept
      },
      dry_run: dryRun
    };

    try {
      const res = await fetch("/api/executions/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        App.toast(data.error || "Failed to start execution.", "danger");
        return;
      }

      App.toast(`Execution ${data.execution_id} started.`, "success");
      this.attachToExecution(data.execution_id);
    } catch (e) {
      App.toast(`Network error starting run: ${e}`, "danger");
    }
  },

  attachToExecution(execId) {
    this.currentExecId = execId;
    this.logIndex = 0;
    document.getElementById("terminalLogs").innerHTML = "";
    document.getElementById("abortExecutionBtn")?.removeAttribute("disabled");
    document.getElementById("confirmationPromptCard")?.style.setProperty("display", "none");
    this.updateStatusBadge("RUNNING");

    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = setInterval(() => this.pollExecutionStatus(), 800);
    this.pollExecutionStatus();
  },

  async pollExecutionStatus() {
    if (!this.currentExecId) return;

    try {
      // Fetch details and logs
      const [resExec, resLogs] = await Promise.all([
        fetch(`/api/executions/${this.currentExecId}`),
        fetch(`/api/executions/${this.currentExecId}/logs?since=${this.logIndex}`)
      ]);

      const execData = await resExec.json();
      const logsData = await resLogs.json();

      if (execData.success && execData.data) {
        const run = execData.data;
        this.updateStatusBadge(run.status);
        this.renderSteps(run.steps || []);

        if (run.status === "AWAITING_CONFIRMATION") {
          document.getElementById("confirmationPromptCard")?.style.setProperty("display", "block");
        } else {
          document.getElementById("confirmationPromptCard")?.style.setProperty("display", "none");
        }

        if (run.screenshot_after) {
          const afterImg = document.getElementById("previewScreenshotAfter");
          if (afterImg) {
            afterImg.src = `/api/images/screenshots/${run.screenshot_after}`;
            afterImg.style.display = "block";
          }
        }

        // Terminal finished states
        if (["SUCCESS", "FAILED", "CANCELLED"].includes(run.status)) {
          clearInterval(this.pollTimer);
          this.pollTimer = null;
          document.getElementById("abortExecutionBtn")?.setAttribute("disabled", "true");
          if (run.status === "SUCCESS") {
            App.toast("Workflow execution completed successfully!", "success");
          } else {
            App.toast(`Workflow ended with status: ${run.status}`, "danger");
          }
        }
      }

      if (logsData.success && logsData.entries) {
        this.appendLogs(logsData.entries);
        this.logIndex += logsData.entries.length;
      }
    } catch (e) {
      console.warn("Polling error:", e);
    }
  },

  renderSteps(steps) {
    const container = document.getElementById("executionStepList");
    if (!container) return;

    if (!steps || steps.length === 0) {
      container.innerHTML = `<div style="color:var(--text-muted);font-size:0.85rem">Steps queued for execution...</div>`;
      return;
    }

    container.innerHTML = steps.map((s, idx) => {
      let badgeCls = "badge-info";
      if (s.status === "SUCCESS") badgeCls = "badge-success";
      if (s.status === "FAILED") badgeCls = "badge-danger";
      if (s.status === "RUNNING") badgeCls = "badge-warning";

      return `
        <div class="step-node" style="padding:0.75rem 1rem">
          <div style="display:flex;align-items:center;gap:0.75rem">
            <span class="step-number">${idx + 1}</span>
            <div>
              <div style="font-weight:600;font-size:0.88rem;color:var(--text-primary)">${s.step_name}</div>
              <div style="font-size:0.75rem;color:var(--text-muted)">Type: ${s.step_type} | ${s.duration_seconds ? s.duration_seconds + 's' : 'pending'}</div>
            </div>
          </div>
          <div>
            <span class="badge ${badgeCls}">${s.status}</span>
          </div>
        </div>
      `;
    }).join("");
  },

  appendLogs(entries) {
    const term = document.getElementById("terminalLogs");
    if (!term) return;

    entries.forEach((l) => {
      const line = document.createElement("div");
      line.className = "terminal-line";
      let levelClass = "terminal-info";
      if (l.level === "WARN") levelClass = "terminal-warn";
      if (l.level === "ERROR") levelClass = "terminal-error";

      line.innerHTML = `
        <span class="terminal-time">[${l.timestamp}]</span>
        <span class="${levelClass}">[${l.level}]</span>
        <span>${l.message}</span>
      `;
      term.appendChild(line);
    });

    term.scrollTop = term.scrollHeight;
  },

  async sendConfirmation(action) {
    if (!this.currentExecId) return;

    try {
      const res = await fetch(`/api/executions/${this.currentExecId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: action })
      });
      const data = await res.json();
      if (data.success) {
        App.toast(`Confirmation '${action}' submitted.`, "info");
        document.getElementById("confirmationPromptCard")?.style.setProperty("display", "none");
      } else {
        App.toast(data.error || "Failed to confirm.", "danger");
      }
    } catch (e) {
      App.toast(`Confirmation request failed: ${e}`, "danger");
    }
  },

  async abortRun() {
    if (!this.currentExecId) return;

    try {
      const res = await fetch(`/api/executions/${this.currentExecId}/abort`, {
        method: "POST"
      });
      const data = await res.json();
      if (data.success) {
        App.toast("Cancellation requested.", "warning");
      } else {
        App.toast(data.error || "Abort failed.", "danger");
      }
    } catch (e) {
      App.toast(`Abort request failed: ${e}`, "danger");
    }
  },

  updateStatusBadge(status) {
    const badge = document.getElementById("executionStatusBadge");
    if (!badge) return;

    badge.className = "badge";
    if (status === "RUNNING") badge.classList.add("badge-warning");
    else if (status === "AWAITING_CONFIRMATION") badge.classList.add("badge-warning");
    else if (status === "SUCCESS") badge.classList.add("badge-success");
    else if (status === "FAILED") badge.classList.add("badge-danger");
    else badge.classList.add("badge-info");

    badge.innerHTML = `<span class="badge-dot"></span> ${status}`;
  }
};

document.addEventListener("DOMContentLoaded", () => ControlCenter.init());
