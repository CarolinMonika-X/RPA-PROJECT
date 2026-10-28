# AI-Powered Image-Based RPA Automation Platform (OmniRPA)

A modern, enterprise-grade, visual Robotic Process Automation (RPA) platform built on Python, OpenCV, Flask, and PyAutoGUI. Transforms legacy desktop GUI automations into an intelligent, observable, and extensible automation system with a high-performance web control center, visual workflow builder, computer vision lab, and real-time execution telemetry.

---

## 1. Project Architecture

The platform separates presentation, process management, vision algorithms, and data persistence cleanly:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Web Dashboard UI (HTML5 / Modern CSS / JS)           │
│  Control Center  │  Workflow Builder  │  CV Lab  │  OCR  │  Employees  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ REST JSON APIs & Web Views
┌────────────────────────────────────▼───────────────────────────────────┐
│                    Flask Application Factory (Port 5000)                │
│       Routes: api_routes, view_routes, cv_routes, employee_routes       │
└───────┬─────────────────┬───────────────────┬──────────────────┬───────┘
        │                 │                   │                  │
        ▼                 ▼                   ▼                  ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────┐  ┌───────────────┐
│  Automation  │  │   Computer    │  │ Optical Char   │  │   Employee    │
│    Engine    │  │  Vision (CV)  │  │  Recognition   │  │ CSV Service   │
│  (State/Lock)│  │ (OpenCV Match)│  │  (pytesseract) │  │  (ThreadSafe) │
└───────┬──────┘  └───────┬───────┘  └────────┬───────┘  └───────┬───────┘
        │                 │                   │                  │
        ▼                 ▼                   ▼                  ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────┐  ┌───────────────┐
│  SQLite DB   │  │ templates/    │  │ Windows OCR or │  │    results/   │
│ (Executions) │  │ save_employee │  │ CV Contours    │  │ employees.csv │
└──────────────┘  └───────────────┘  └────────────────┘  └───────────────┘
```

---

## 2. Key Features

- **Enterprise SaaS Dashboard**: Dark navy and charcoal visual system with glowing violet, cyan, and blue accents, glassmorphic cards, collapsible navigation sidebar, keyboard-accessible command palette (`Ctrl+K`), and toast notifications.
- **Automation Control Center**: Managed background execution engine with sequential step progression tracking, live terminal log streaming (polling 800ms), and emergency stop capabilities.
- **Mandatory Safety Confirmation**: Preserves explicit interactive confirmation before triggering sensitive OS actions (e.g. clicking Save). Never silently bypasses approval.
- **Desktop Concurrency Lock**: Thread-safe locking mechanism preventing concurrent automation jobs from colliding on the mouse and keyboard.
- **Visual Workflow Builder**: Visual pipeline builder to add, edit, duplicate, and reorder steps (`activate_window`, `type_text`, `press_key`, `wait`, `screenshot`, `image_detection`, `request_confirmation`, `click_detected`, `validation`, `ocr_detect`).
- **Computer Vision Lab**: Live desktop screen capture, interactive canvas cropping to create new templates, multi-scale template matching (0.8x to 1.25x), multi-method evaluation (`TM_CCOEFF_NORMED`, `TM_CCORR_NORMED`, `TM_SQDIFF_NORMED`), bounding box annotations, and low-confidence diagnostics.
- **OCR & Text Element Recognition**: Tesseract OCR integration with automatic binary detection, Windows installation guide, and OpenCV contour-based heuristic fallback.
- **Employee Data Management**: Thread-safe CSV CRUD synchronized with `results/employees.csv`. Search, filter by department, pagination, sorting, duplicate ID prevention, and CSV import/export.
- **Audit History & Observability**: SQLite-backed execution history recording durations, step outcomes, detection confidences, and before/after screenshots.

---

## 3. Directory Structure

```
image-based-legacy-automation/
├── main.py                     # [Preserved] Tkinter Legacy Employee Management System
├── auto_automation.py          # [Preserved] Original CLI automation script
├── capture_template.py         # [Preserved] Original template capture script
├── detect_button.py            # [Preserved] Original button detection script
├── requirements.txt            # Python dependencies (Flask, OpenCV, PyAutoGUI, etc.)
├── run_platform.py             # Platform web application runner
├── templates/                  # Saved visual reference templates
│   └── save_employee.png       # Original Save button template
├── results/                    # CSV data and detection results
│   ├── employees.csv           # Preserved employee records
│   └── automation_result.png   # Preserved detection screenshot
├── screenshots/                # Captured desktop screenshots
│   └── desktop.png
├── backend/                    # Modular Python backend architecture
│   ├── app.py                  # Flask app factory
│   ├── config.py               # Paths and runtime defaults
│   ├── models.py               # Workflow and step dataclass schemas
│   ├── routes/
│   │   ├── api_routes.py       # REST API endpoints (executions, workflows, metrics)
│   │   ├── view_routes.py      # Web page renderers
│   │   ├── cv_routes.py        # CV Lab & template crop APIs
│   │   ├── employee_routes.py  # Employee CSV CRUD APIs
│   │   └── settings_routes.py  # Diagnostics & settings APIs
│   ├── services/
│   │   ├── automation_engine.py# Process manager, confirmation broker, locks
│   │   ├── cv_service.py       # OpenCV multi-scale & multi-method matching
│   │   ├── ocr_service.py      # Tesseract & contour fallback engine
│   │   ├── employee_service.py # Thread-safe CSV manager
│   │   ├── workflow_service.py # JSON workflow manager
│   │   ├── db_service.py       # SQLite persistence & metrics computation
│   │   └── system_service.py   # Diagnostics & platform telemetry
│   └── utils/
│       ├── logger.py           # Real-time memory ring logger
│       └── security.py         # Safe path resolution & input sanitation
├── static/                     # Web assets
│   ├── css/app.css             # Enterprise design system stylesheet
│   └── js/                     # Modular frontend controllers
│       ├── app.js              # Theme, Command Palette, Toasts
│       ├── control_center.js   # Automation runner & live polling
│       ├── cv_lab.js           # Interactive canvas cropper & matcher
│       ├── ocr_lab.js          # OCR inspector & label search
│       ├── workflow_builder.js # Visual step builder & JSON validator
│       └── employee_mgr.js     # Search, filter, edit & pagination
├── templates_web/              # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── control_center.html
│   ├── workflow_builder.html
│   ├── cv_lab.html
│   ├── ocr_lab.html
│   ├── employees.html
│   ├── history.html
│   ├── execution_detail.html
│   ├── library.html
│   └── settings.html
├── workflows/                  # Persisted workflow JSON files
│   ├── employee_registration.json
│   └── button_inspection.json
└── tests/                      # Automated unit & integration test suite (24 tests)
    ├── conftest.py             # Pytest fixtures & PyAutoGUI mock
    ├── test_api_routes.py
    ├── test_automation_engine.py
    ├── test_cv_service.py
    ├── test_db_service.py
    ├── test_employee_service.py
    ├── test_ocr_service.py
    └── test_workflow_validator.py
```

---

## 4. Setup and Launch Instructions

### Prerequisites
- Windows 10/11 with Python 3.10+
- The project includes a pre-configured virtual environment in `venv/`.

### 1. Launch the Web Platform
From PowerShell in the project directory:

```powershell
# Navigate into the project folder
cd "C:\Users\CAROLIN\OneDrive\Desktop\RPA PROJECT\image-based-legacy-automation"

# Start the OmniRPA Platform
.\venv\Scripts\python.exe run_platform.py
```
Open your browser to: **`http://127.0.0.1:5000`**

Alternatively, from the workspace root:
```powershell
cd "C:\Users\CAROLIN\OneDrive\Desktop\RPA PROJECT"
.\image-based-legacy-automation\venv\Scripts\python.exe run.py
```

### 2. Launch the Legacy Tkinter App (Target Application)
In a second PowerShell terminal:
```powershell
cd "C:\Users\CAROLIN\OneDrive\Desktop\RPA PROJECT\image-based-legacy-automation"
.\venv\Scripts\python.exe main.py
```
This opens the `Legacy Employee Management System` window.

### 3. Run Automation
You can run automations in two ways:
1. **Via the Web Control Center**: Go to `http://127.0.0.1:5000/control-center`, select "Legacy Employee Registration", fill the employee inputs, and click **Execute Workflow**. When the safety prompt appears, click **Confirm & Save Employee**.
2. **Via Legacy CLI Automation**:
```powershell
.\venv\Scripts\python.exe auto_automation.py
```

---

## 5. OCR Engine Setup (Optional)

The platform runs deterministically even without Tesseract installed by utilizing OpenCV contour-based element detection fallback.

To enable full Optical Character Recognition on Windows:
1. Install via Windows Package Manager:
   ```powershell
   winget install UB-Mannheim.TesseractOCR
   ```
   Or download the installer from: `https://github.com/UB-Mannheim/tesseract/wiki`
2. Ensure `tesseract.exe` is added to your system `PATH` (typically installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`).
3. Check status in the platform under **Settings & Health** (`/settings`) or **OCR & Text Engine** (`/ocr-lab`).

---

## 6. Running the Automated Tests

All tests safely mock PyAutoGUI and PyGetWindow so they run headlessly without clicking or moving your mouse:

```powershell
cd "C:\Users\CAROLIN\OneDrive\Desktop\RPA PROJECT\image-based-legacy-automation"
.\venv\Scripts\python.exe -m pytest tests -v
```

All 24 tests cover:
- Workflow schema validation
- Thread-safe CSV read/write and duplicate ID prevention
- Concurrency locks (preventing colliding runs)
- Explicit user confirmation cycles
- Template matching, multi-scale detection, and low-confidence diagnostics
- OCR availability checks and contour fallback
- SQLite execution persistence and dashboard metrics computation
- REST API endpoints and health checks

---

## 7. REST API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health-check & system diagnostics |
| `GET` | `/api/metrics` | Dashboard statistics computed from SQLite |
| `GET` | `/api/executions` | List recent executions with filters |
| `POST` | `/api/executions/start` | Start a workflow run (`dry_run` supported) |
| `GET` | `/api/executions/<id>` | Get execution status, steps, and logs |
| `GET` | `/api/executions/<id>/logs` | Poll or stream execution logs |
| `POST` | `/api/executions/<id>/confirm` | Provide interactive approval (`CONFIRM`/`CANCEL`) |
| `POST` | `/api/executions/<id>/abort` | Emergency abort running execution |
| `GET` | `/api/workflows` | List saved JSON workflows |
| `POST` | `/api/workflows` | Create a new workflow |
| `POST` | `/api/cv/capture` | Capture live desktop screen |
| `POST` | `/api/cv/match` | Execute OpenCV template matching |
| `POST` | `/api/cv/crop` | Crop new template from canvas selection |
| `GET` | `/api/employees` | Search, filter, and paginate employee CSV records |
| `POST` | `/api/employees` | Add employee record with duplicate ID validation |
| `GET` | `/api/employees/export` | Download employee CSV |
| `POST` | `/api/employees/import` | Upload & import employee CSV |
| `GET` | `/api/settings` | Get platform thresholds & preferences |
| `POST` | `/api/settings` | Save platform thresholds |
| `GET` | `/api/diagnostics` | System versions & environment diagnostics |
