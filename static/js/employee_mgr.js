/**
 * Employee Records Management Module
 * Connects directly to results/employees.csv with full CRUD, search, filter, pagination, import/export.
 */

const EmployeeMgr = {
  currentPage: 1,
  pageSize: 10,
  searchQuery: "",
  deptFilter: "",
  sortBy: "Created At",
  ascending: false,

  init() {
    this.bindEvents();
    this.fetchRecords();
  },

  bindEvents() {
    const searchInput = document.getElementById("empSearchInput");
    searchInput?.addEventListener("input", (e) => {
      this.searchQuery = e.target.value;
      this.currentPage = 1;
      this.fetchRecords();
    });

    const deptSelect = document.getElementById("empDeptFilter");
    deptSelect?.addEventListener("change", (e) => {
      this.deptFilter = e.target.value;
      this.currentPage = 1;
      this.fetchRecords();
    });

    document.getElementById("btnOpenAddEmployeeModal")?.addEventListener("click", () => {
      document.getElementById("addEmpId").value = "";
      document.getElementById("addEmpName").value = "";
      document.getElementById("addEmpDept").value = "";
      App.openModal("addEmployeeModal");
    });

    document.getElementById("btnSaveNewEmployee")?.addEventListener("click", () => this.saveNewEmployee());
    document.getElementById("btnSaveEditEmployee")?.addEventListener("click", () => this.saveEditEmployee());
    document.getElementById("btnExportEmployeesCsv")?.addEventListener("click", () => {
      window.location.href = "/api/employees/export";
    });

    document.getElementById("csvImportFileInput")?.addEventListener("change", (e) => this.handleCsvImport(e));
  },

  async fetchRecords() {
    const params = new URLSearchParams({
      q: this.searchQuery,
      department: this.deptFilter,
      sort_by: this.sortBy,
      ascending: this.ascending.toString(),
      page: this.currentPage.toString(),
      page_size: this.pageSize.toString()
    });

    try {
      const res = await fetch(`/api/employees?${params.toString()}`);
      const json = await res.json();
      if (json.success && json.data) {
        this.renderTable(json.data.records || []);
        this.renderPagination(json.data);
      }
    } catch (e) {
      App.toast(`Failed to load employee records: ${e}`, "danger");
    }
  },

  renderTable(records) {
    const tbody = document.getElementById("employeeTableBody");
    if (!tbody) return;

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:var(--text-muted)">No matching employee records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = records.map((r) => `
      <tr>
        <td><strong style="color:var(--text-primary)">${r["Employee ID"]}</strong></td>
        <td>${r["Name"]}</td>
        <td><span class="badge badge-info">${r["Department"]}</span></td>
        <td style="color:var(--text-muted);font-size:0.8rem">${r["Created At"]}</td>
        <td style="text-align:right">
          <button class="btn btn-secondary" style="padding:0.3rem 0.6rem;font-size:0.75rem" onclick="EmployeeMgr.openEditModal('${r["Employee ID"]}', '${r["Name"]}', '${r["Department"]}')">Edit</button>
          <button class="btn btn-danger" style="padding:0.3rem 0.6rem;font-size:0.75rem" onclick="EmployeeMgr.deleteEmployee('${r["Employee ID"]}')">Delete</button>
        </td>
      </tr>
    `).join("");
  },

  renderPagination(data) {
    const paginationEl = document.getElementById("employeePagination");
    if (!paginationEl) return;

    paginationEl.innerHTML = `
      <div style="font-size:0.82rem;color:var(--text-muted)">
        Showing page ${data.page} of ${data.total_pages} (${data.total_count} records)
      </div>
      <div style="display:flex;gap:0.4rem">
        <button class="btn btn-secondary" style="padding:0.3rem 0.75rem;font-size:0.8rem" ${data.page <= 1 ? 'disabled' : ''} onclick="EmployeeMgr.goToPage(${data.page - 1})">Previous</button>
        <button class="btn btn-secondary" style="padding:0.3rem 0.75rem;font-size:0.8rem" ${data.page >= data.total_pages ? 'disabled' : ''} onclick="EmployeeMgr.goToPage(${data.page + 1})">Next</button>
      </div>
    `;
  },

  goToPage(page) {
    this.currentPage = page;
    this.fetchRecords();
  },

  async saveNewEmployee() {
    const id = document.getElementById("addEmpId").value.trim();
    const name = document.getElementById("addEmpName").value.trim();
    const dept = document.getElementById("addEmpDept").value.trim();

    if (!id || !name || !dept) {
      App.toast("Please fill in all fields.", "warning");
      return;
    }

    try {
      const res = await fetch("/api/employees", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: id, name: name, department: dept })
      });
      const data = await res.json();
      if (data.success) {
        App.toast("Employee record created.", "success");
        App.closeModal("addEmployeeModal");
        this.fetchRecords();
      } else {
        App.toast(data.error || data.message || "Failed to add employee.", "danger");
      }
    } catch (e) {
      App.toast(`Error creating employee: ${e}`, "danger");
    }
  },

  openEditModal(id, name, dept) {
    document.getElementById("editEmpId").value = id;
    document.getElementById("editEmpName").value = name;
    document.getElementById("editEmpDept").value = dept;
    App.openModal("editEmployeeModal");
  },

  async saveEditEmployee() {
    const id = document.getElementById("editEmpId").value;
    const name = document.getElementById("editEmpName").value.trim();
    const dept = document.getElementById("editEmpDept").value.trim();

    try {
      const res = await fetch(`/api/employees/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, department: dept })
      });
      const data = await res.json();
      if (data.success) {
        App.toast("Employee updated successfully.", "success");
        App.closeModal("editEmployeeModal");
        this.fetchRecords();
      } else {
        App.toast(data.error || "Update failed.", "danger");
      }
    } catch (e) {
      App.toast(`Update error: ${e}`, "danger");
    }
  },

  async deleteEmployee(id) {
    if (!confirm(`Are you sure you want to delete employee record '${id}' from CSV?`)) return;

    try {
      const res = await fetch(`/api/employees/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (data.success) {
        App.toast(`Employee '${id}' deleted.`, "info");
        this.fetchRecords();
      } else {
        App.toast(data.error || "Delete failed.", "danger");
      }
    } catch (e) {
      App.toast(`Delete error: ${e}`, "danger");
    }
  },

  async handleCsvImport(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    App.toast("Importing CSV records...", "info");
    try {
      const res = await fetch("/api/employees/import", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        App.toast(`Imported: ${data.added} added, ${data.skipped} skipped.`, "success");
        this.fetchRecords();
      } else {
        App.toast(data.error || "Import failed.", "danger");
      }
    } catch (err) {
      App.toast(`CSV import error: ${err}`, "danger");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => EmployeeMgr.init());
