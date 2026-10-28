/**
 * Computer Vision Lab Module
 * Interactive canvas screenshot cropper, multi-scale template matching, and OpenCV diagnostics.
 */

const CVLab = {
  activeScreenshot: null,
  cropState: { isDragging: false, startX: 0, startY: 0, currX: 0, currY: 0 },
  imageObj: null,

  init() {
    this.bindEvents();
    this.initCanvas();
  },

  bindEvents() {
    document.getElementById("btnCaptureLiveDesktop")?.addEventListener("click", () => this.captureLiveDesktop());
    document.getElementById("btnRunDetection")?.addEventListener("click", () => this.runDetection());
    document.getElementById("btnSaveCroppedTemplate")?.addEventListener("click", () => this.saveCroppedRegion());

    const fileInput = document.getElementById("screenshotFileInput");
    fileInput?.addEventListener("change", (e) => this.handleImageUpload(e));
  },

  initCanvas() {
    const canvas = document.getElementById("cvCanvas");
    if (!canvas) return;

    canvas.addEventListener("mousedown", (e) => this.onMouseDown(e));
    canvas.addEventListener("mousemove", (e) => this.onMouseMove(e));
    canvas.addEventListener("mouseup", (e) => this.onMouseUp(e));
  },

  async captureLiveDesktop() {
    App.toast("Capturing current desktop...", "info");
    try {
      const res = await fetch("/api/cv/capture", { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.success) {
        App.toast(data.error || "Failed to capture desktop.", "danger");
        return;
      }

      this.activeScreenshot = data.filename;
      this.loadImageToCanvas(data.image_url);
      App.toast(`Screenshot captured (${data.width}x${data.height}).`, "success");
    } catch (e) {
      App.toast(`Desktop capture error: ${e}`, "danger");
    }
  },

  loadImageToCanvas(src) {
    const canvas = document.getElementById("cvCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    this.imageObj = new Image();
    this.imageObj.onload = () => {
      canvas.width = this.imageObj.width;
      canvas.height = this.imageObj.height;
      ctx.drawImage(this.imageObj, 0, 0);

      document.getElementById("imgDimensionsBadge").textContent = `${this.imageObj.width} x ${this.imageObj.height} px`;
      document.getElementById("canvasPlaceholder")?.style.setProperty("display", "none");
      canvas.style.display = "block";
    };
    this.imageObj.src = src;
  },

  onMouseDown(e) {
    const canvas = document.getElementById("cvCanvas");
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    this.cropState.isDragging = true;
    this.cropState.startX = (e.clientX - rect.left) * scaleX;
    this.cropState.startY = (e.clientY - rect.top) * scaleY;
    this.cropState.currX = this.cropState.startX;
    this.cropState.currY = this.cropState.startY;
  },

  onMouseMove(e) {
    if (!this.cropState.isDragging || !this.imageObj) return;
    const canvas = document.getElementById("cvCanvas");
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    this.cropState.currX = (e.clientX - rect.left) * scaleX;
    this.cropState.currY = (e.clientY - rect.top) * scaleY;

    this.redrawCanvasWithSelection();
  },

  onMouseUp(e) {
    if (!this.cropState.isDragging) return;
    this.cropState.isDragging = false;
    this.redrawCanvasWithSelection();

    // Calculate crop rectangle
    const x = Math.round(Math.min(this.cropState.startX, this.cropState.currX));
    const y = Math.round(Math.min(this.cropState.startY, this.cropState.currY));
    const w = Math.round(Math.abs(this.cropState.currX - this.cropState.startX));
    const h = Math.round(Math.abs(this.cropState.currY - this.cropState.startY));

    if (w > 5 && h > 5) {
      document.getElementById("cropCoordsBadge").textContent = `Region: x=${x}, y=${y}, w=${w}, h=${h}`;
      document.getElementById("cropControlsPanel")?.style.setProperty("display", "flex");
    }
  },

  redrawCanvasWithSelection() {
    const canvas = document.getElementById("cvCanvas");
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(this.imageObj, 0, 0);

    const x = Math.min(this.cropState.startX, this.cropState.currX);
    const y = Math.min(this.cropState.startY, this.cropState.currY);
    const w = Math.abs(this.cropState.currX - this.cropState.startX);
    const h = Math.abs(this.cropState.currY - this.cropState.startY);

    // Darken surrounding
    ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
    ctx.fillRect(0, 0, canvas.width, y);
    ctx.fillRect(0, y, x, h);
    ctx.fillRect(x + w, y, canvas.width - (x + w), h);
    ctx.fillRect(0, y + h, canvas.width, canvas.height - (y + h));

    // Draw box
    ctx.strokeStyle = "#8B5CF6";
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);
  },

  async saveCroppedRegion() {
    if (!this.activeScreenshot) {
      App.toast("Please capture or load a screenshot first.", "error");
      return;
    }

    const nameInput = document.getElementById("newTemplateNameInput");
    const tmplName = nameInput?.value.trim();
    if (!tmplName) {
      App.toast("Please enter a template name.", "error");
      return;
    }

    const x = Math.round(Math.min(this.cropState.startX, this.cropState.currX));
    const y = Math.round(Math.min(this.cropState.startY, this.cropState.currY));
    const w = Math.round(Math.abs(this.cropState.currX - this.cropState.startX));
    const h = Math.round(Math.abs(this.cropState.currY - this.cropState.startY));

    try {
      const res = await fetch("/api/cv/crop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          screenshot_name: this.activeScreenshot,
          template_name: tmplName,
          x: x, y: y, width: w, height: h
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        App.toast(data.error || "Failed to crop template.", "danger");
        return;
      }

      App.toast(data.message, "success");
      setTimeout(() => window.location.reload(), 1000);
    } catch (e) {
      App.toast(`Error cropping template: ${e}`, "danger");
    }
  },

  async runDetection() {
    if (!this.activeScreenshot) {
      App.toast("Please capture a desktop screenshot first.", "warning");
      return;
    }

    const templateSelect = document.getElementById("cvTemplateSelect");
    const methodSelect = document.getElementById("cvMethodSelect");
    const thresholdInput = document.getElementById("cvThresholdSlider");
    const multiScale = document.getElementById("cvMultiScaleCheck")?.checked || false;

    const payload = {
      screenshot_name: this.activeScreenshot,
      template_name: templateSelect?.value,
      method: methodSelect?.value,
      threshold: parseFloat(thresholdInput?.value || 0.80),
      multi_scale: multiScale
    };

    try {
      App.toast("Executing template matching...", "info");
      const res = await fetch("/api/cv/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (!res.ok || data.error) {
        App.toast(data.error || "Matching error", "danger");
        return;
      }

      // Display results
      this.renderMatchResults(data);
    } catch (e) {
      App.toast(`Matching error: ${e}`, "danger");
    }
  },

  renderMatchResults(result) {
    const panel = document.getElementById("detectionResultsPanel");
    if (!panel) return;

    panel.style.display = "block";
    const confBadge = document.getElementById("matchConfidenceBadge");
    const confVal = (result.confidence * 100).toFixed(2);
    confBadge.textContent = `${confVal}% Confidence`;
    confBadge.className = `badge ${result.success ? 'badge-success' : 'badge-danger'}`;

    document.getElementById("matchLocationLabel").textContent = 
      `Coordinates: x=${result.box.x}, y=${result.box.y} (Center: ${result.center.x}, ${result.center.y}) | Scale: ${result.scale}x`;

    const diagList = document.getElementById("diagnosticsList");
    if (diagList) {
      diagList.innerHTML = (result.diagnostics || []).map(d => `<li>${d}</li>`).join("");
    }

    if (result.annotation_image) {
      this.loadImageToCanvas(`/api/images/results/${result.annotation_image}`);
    }
  }
};

document.addEventListener("DOMContentLoaded", () => CVLab.init());
