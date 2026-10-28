/**
 * OCR & Intelligent Text Recognition Lab Module
 */

const OCRLab = {
  activeScreenshot: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    document.getElementById("btnCaptureForOcr")?.addEventListener("click", () => this.captureDesktop());
    document.getElementById("btnRunOcr")?.addEventListener("click", () => this.runOcr());
    document.getElementById("btnSearchLabel")?.addEventListener("click", () => this.searchLabel());
  },

  async captureDesktop() {
    App.toast("Capturing screenshot for OCR...", "info");
    try {
      const res = await fetch("/api/cv/capture", { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.success) {
        App.toast("Desktop capture failed.", "danger");
        return;
      }
      this.activeScreenshot = data.filename;
      const previewImg = document.getElementById("ocrPreviewImg");
      if (previewImg) {
        previewImg.src = data.image_url;
        previewImg.style.display = "block";
      }
      App.toast("Screenshot ready for text recognition.", "success");
    } catch (e) {
      App.toast(`Capture error: ${e}`, "danger");
    }
  },

  async runOcr() {
    if (!this.activeScreenshot) {
      App.toast("Please capture a desktop screenshot first.", "warning");
      return;
    }

    try {
      App.toast("Extracting text via OCR...", "info");
      const res = await fetch("/api/ocr/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenshot_name: this.activeScreenshot })
      });
      const data = await res.json();

      const resultBox = document.getElementById("ocrResultContent");
      if (!data.success) {
        resultBox.innerHTML = `
          <div style="color:var(--status-warning);margin-bottom:0.5rem"><strong>Notice:</strong> ${data.error}</div>
          <div style="font-size:0.85rem;color:var(--text-secondary)">${data.guide || ""}</div>
        `;
        return;
      }

      resultBox.innerHTML = `
        <div style="margin-bottom:0.75rem;font-weight:600;color:var(--accent-cyan)">Found ${data.word_count} text tokens:</div>
        <div style="background:var(--bg-primary);padding:0.75rem;border-radius:var(--radius-md);margin-bottom:1rem;font-size:0.9rem">
          ${data.full_text || "(No readable text detected)"}
        </div>
      `;
    } catch (e) {
      App.toast(`OCR error: ${e}`, "danger");
    }
  },

  async searchLabel() {
    if (!this.activeScreenshot) {
      App.toast("Please capture a desktop screenshot first.", "warning");
      return;
    }

    const labelInput = document.getElementById("ocrLabelSearchInput");
    const label = labelInput?.value.trim();
    if (!label) {
      App.toast("Please enter a button label to search for.", "warning");
      return;
    }

    try {
      const res = await fetch("/api/ocr/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ screenshot_name: this.activeScreenshot, label: label })
      });
      const data = await res.json();
      const resultBox = document.getElementById("ocrResultContent");

      if (data.success) {
        resultBox.innerHTML = `
          <div class="badge badge-success" style="margin-bottom:0.5rem">Match Found (${data.match_type})</div>
          <div style="font-size:0.9rem;margin-bottom:0.5rem">Found: <strong>${data.found_text || label}</strong></div>
          <div style="font-size:0.85rem;color:var(--text-secondary)">
            Center Coordinates: <strong>x=${data.center?.x}, y=${data.center?.y}</strong>
          </div>
        `;
        App.toast(`Found label element at (${data.center?.x}, ${data.center?.y})`, "success");
      } else {
        resultBox.innerHTML = `
          <div class="badge badge-danger" style="margin-bottom:0.5rem">Not Located</div>
          <div style="font-size:0.85rem;color:var(--text-secondary)">
            ${data.note || "Could not detect element with that label."}
          </div>
        `;
      }
    } catch (e) {
      App.toast(`Search error: ${e}`, "danger");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => OCRLab.init());
