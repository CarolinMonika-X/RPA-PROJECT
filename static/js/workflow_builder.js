/**
 * Visual Workflow Builder Module
 * Interactive step builder, reordering, schema validation, dry-run testing, and export/import.
 */

const WorkflowBuilder = {
  currentWorkflow: null,

  init() {
    this.bindEvents();
    const select = document.getElementById("builderWfSelect");
    if (select && select.value) {
      this.loadWorkflow(select.value);
    }
  },

  bindEvents() {
    document.getElementById("builderWfSelect")?.addEventListener("change", (e) => this.loadWorkflow(e.target.value));
    document.getElementById("btnAddStep")?.addEventListener("click", () => this.openAddStepModal());
    document.getElementById("btnSaveWorkflow")?.addEventListener("click", () => this.saveCurrentWorkflow());
    document.getElementById("btnNewWorkflow")?.addEventListener("click", () => this.createNewWorkflow());
    document.getElementById("btnDryRunWorkflow")?.addEventListener("click", () => this.runDryRun());
    document.getElementById("btnExportWfJson")?.addEventListener("click", () => this.exportJson());
    document.getElementById("btnSaveStepConfig")?.addEventListener("click", () => this.commitStepFromModal());
  },

  async loadWorkflow(wfId) {
    if (!wfId) return;
    try {
      const res = await fetch(`/api/workflows/${wfId}`);
      const data = await res.json();
      if (data.success && data.data) {
        this.currentWorkflow = data.data;
        this.renderWorkflow();
      }
    } catch (e) {
      App.toast(`Failed to load workflow: ${e}`, "danger");
    }
  },

  renderWorkflow() {
    if (!this.currentWorkflow) return;

    document.getElementById("wfNameInput").value = this.currentWorkflow.name || "";
    document.getElementById("wfDescInput").value = this.currentWorkflow.description || "";
    document.getElementById("wfVersionBadge").textContent = `Schema v${this.currentWorkflow.version || "2.0"}`;

    const container = document.getElementById("builderStepsContainer");
    if (!container) return;

    if (!this.currentWorkflow.steps || this.currentWorkflow.steps.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:2rem;color:var(--text-muted)">No steps defined yet. Click "Add Step" to begin.</div>`;
      return;
    }

    container.innerHTML = this.currentWorkflow.steps.map((s, idx) => `
      <div class="step-node" data-index="${idx}">
        <div style="display:flex;align-items:center;gap:0.85rem">
          <span class="step-number">${idx + 1}</span>
          <div>
            <div style="font-weight:600;font-size:0.92rem">${s.name}</div>
            <div style="font-size:0.78rem;color:var(--text-muted)">
              Type: <strong style="color:var(--accent-cyan)">${s.type}</strong> | Params: ${JSON.stringify(s.params || {})}
            </div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem">
          <button class="btn btn-secondary" style="padding:0.35rem 0.65rem;font-size:0.75rem" onclick="WorkflowBuilder.moveStep(${idx}, -1)" ${idx === 0 ? 'disabled' : ''}>▲</button>
          <button class="btn btn-secondary" style="padding:0.35rem 0.65rem;font-size:0.75rem" onclick="WorkflowBuilder.moveStep(${idx}, 1)" ${idx === this.currentWorkflow.steps.length - 1 ? 'disabled' : ''}>▼</button>
          <button class="btn btn-secondary" style="padding:0.35rem 0.65rem;font-size:0.75rem" onclick="WorkflowBuilder.openEditStepModal(${idx})">Edit</button>
          <button class="btn btn-danger" style="padding:0.35rem 0.65rem;font-size:0.75rem" onclick="WorkflowBuilder.deleteStep(${idx})">✕</button>
        </div>
      </div>
    `).join("");
  },

  moveStep(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= this.currentWorkflow.steps.length) return;

    const temp = this.currentWorkflow.steps[index];
    this.currentWorkflow.steps[index] = this.currentWorkflow.steps[targetIdx];
    this.currentWorkflow.steps[targetIdx] = temp;
    this.renderWorkflow();
  },

  deleteStep(index) {
    this.currentWorkflow.steps.splice(index, 1);
    this.renderWorkflow();
  },

  openAddStepModal() {
    document.getElementById("stepModalIndex").value = "-1";
    document.getElementById("stepModalName").value = "New Action Step";
    document.getElementById("stepModalType").value = "wait";
    document.getElementById("stepModalParams").value = '{"milliseconds": 500}';
    App.openModal("stepConfigModal");
  },

  openEditStepModal(index) {
    const step = this.currentWorkflow.steps[index];
    document.getElementById("stepModalIndex").value = index.toString();
    document.getElementById("stepModalName").value = step.name;
    document.getElementById("stepModalType").value = step.type;
    document.getElementById("stepModalParams").value = JSON.stringify(step.params || {}, null, 2);
    App.openModal("stepConfigModal");
  },

  commitStepFromModal() {
    const index = parseInt(document.getElementById("stepModalIndex").value, 10);
    const name = document.getElementById("stepModalName").value.trim();
    const type = document.getElementById("stepModalType").value;
    const rawParams = document.getElementById("stepModalParams").value.trim();

    let params = {};
    try {
      params = rawParams ? JSON.parse(rawParams) : {};
    } catch (e) {
      App.toast("Invalid JSON in parameters field.", "danger");
      return;
    }

    if (!name) {
      App.toast("Step name is required.", "danger");
      return;
    }

    const stepObj = {
      id: `step_${Date.now()}`,
      name: name,
      type: type,
      params: params,
      timeout_seconds: 10.0,
      retry_count: 1
    };

    if (index === -1) {
      this.currentWorkflow.steps.push(stepObj);
    } else {
      this.currentWorkflow.steps[index] = stepObj;
    }

    App.closeModal("stepConfigModal");
    this.renderWorkflow();
  },

  async saveCurrentWorkflow() {
    if (!this.currentWorkflow) return;
    this.currentWorkflow.name = document.getElementById("wfNameInput").value.trim();
    this.currentWorkflow.description = document.getElementById("wfDescInput").value.trim();

    try {
      const res = await fetch(`/api/workflows/${this.currentWorkflow.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.currentWorkflow)
      });
      const data = await res.json();
      if (data.success) {
        App.toast("Workflow saved successfully.", "success");
      } else {
        App.toast(data.error || "Save failed.", "danger");
      }
    } catch (e) {
      App.toast(`Save error: ${e}`, "danger");
    }
  },

  createNewWorkflow() {
    const newId = `wf_${Date.now()}`;
    this.currentWorkflow = {
      id: newId,
      name: "New Custom Workflow",
      description: "Custom automated workflow definition.",
      steps: [
        { id: "s1", name: "Initial Pause", type: "wait", params: { milliseconds: 500 } }
      ],
      version: "2.0"
    };
    this.renderWorkflow();
    App.toast("Created new workflow template.", "info");
  },

  async runDryRun() {
    if (!this.currentWorkflow) return;
    App.toast("Initiating dry-run validation...", "info");
    try {
      const res = await fetch("/api/executions/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: this.currentWorkflow.id,
          dry_run: true
        })
      });
      const data = await res.json();
      if (data.success) {
        App.toast(`Dry run initiated (${data.execution_id}). Navigating to Control Center...`, "success");
        window.location.href = `/control-center?id=${data.execution_id}`;
      } else {
        App.toast(data.error || "Dry-run failed to start.", "danger");
      }
    } catch (e) {
      App.toast(`Dry-run start error: ${e}`, "danger");
    }
  },

  exportJson() {
    if (!this.currentWorkflow) return;
    window.location.href = `/api/workflows/export/${this.currentWorkflow.id}`;
  }
};

document.addEventListener("DOMContentLoaded", () => WorkflowBuilder.init());
