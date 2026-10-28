/**
 * Global UI & Utility Module
 * Theme management, Command Palette, Toasts, Modals, and Sidebar
 */

const App = {
  init() {
    this.initTheme();
    this.initSidebar();
    this.initCommandPalette();
    this.initModals();
  },

  // --- Theme Management ---
  initTheme() {
    const savedTheme = localStorage.getItem("rpa_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);

    const themeToggleBtn = document.getElementById("themeToggleBtn");
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("rpa_theme", next);
        this.toast(`Theme switched to ${next} mode`, "info");
      });
    }
  },

  // --- Sidebar Collapse ---
  initSidebar() {
    const sidebar = document.querySelector(".sidebar");
    const toggleBtn = document.getElementById("sidebarToggleBtn");
    if (sidebar && toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("collapsed");
        localStorage.setItem("sidebar_collapsed", sidebar.classList.contains("collapsed"));
      });

      if (localStorage.getItem("sidebar_collapsed") === "true") {
        sidebar.classList.add("collapsed");
      }
    }
  },

  // --- Command Palette (Ctrl+K / Cmd+K) ---
  initCommandPalette() {
    const overlay = document.getElementById("cmdPaletteOverlay");
    const input = document.getElementById("cmdPaletteInput");
    const triggerBtn = document.getElementById("cmdPaletteTrigger");

    if (!overlay || !input) return;

    const openPalette = () => {
      overlay.classList.add("active");
      input.value = "";
      input.focus();
      this.filterCommands("");
    };

    const closePalette = () => {
      overlay.classList.remove("active");
    };

    if (triggerBtn) triggerBtn.addEventListener("click", openPalette);

    window.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (overlay.classList.contains("active")) {
          closePalette();
        } else {
          openPalette();
        }
      } else if (e.key === "Escape" && overlay.classList.contains("active")) {
        closePalette();
      }
    });

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closePalette();
    });

    input.addEventListener("input", (e) => {
      this.filterCommands(e.target.value);
    });
  },

  filterCommands(query) {
    const items = document.querySelectorAll(".cmd-item");
    const q = query.toLowerCase().trim();
    items.forEach((item) => {
      const text = item.textContent.toLowerCase();
      item.style.display = !q || text.includes(q) ? "flex" : "none";
    });
  },

  // --- Modal Helpers ---
  initModals() {
    document.querySelectorAll("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const modal = btn.closest(".modal-overlay");
        if (modal) modal.classList.remove("active");
      });
    });

    document.querySelectorAll(".modal-overlay").forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.remove("active");
      });
    });
  },

  openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.add("active");
  },

  closeModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.remove("active");
  },

  // --- Toast Notifications ---
  toast(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "error" || type === "danger") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#06B6D4" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `
      ${iconSvg}
      <div style="flex:1">${message}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
};

document.addEventListener("DOMContentLoaded", () => App.init());
