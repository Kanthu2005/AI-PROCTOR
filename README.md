# ProctorAI — Enterprise AI Assessment & Proctoring Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React: 18](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%20%2B%20TS-61DAFB.svg)](https://reactjs.org/)
[![Database: SQLite / PostgreSQL](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-336791.svg)](https://www.postgresql.org/)

**ProctorAI** is a high-integrity, cloud-ready technical screening and online evaluation platform. It combines automated question authoring, an isolated code execution sandbox, real-time computer-vision AI proctoring, server-enforced exam timers, and live integrity surveillance into a single unified solution.

---

## 🌟 Key Capabilities

### 1. 🎓 Candidate Examination Engine
- **Single-Use Invitation Tokens**: Cryptographically secure, expiring invitation tokens (`/api/v1/candidates/verify-token`).
- **Pre-Flight Diagnostics**: Automated webcam, microphone, network latency, and browser lockdown hardware checks.
- **Server-Authoritative Clock**: Official exam duration and countdowns are strictly enforced on the server — client-side clock tampering is impossible.
- **Autosave with Acknowledgement**: Answers are periodically autosaved with server sequence numbers, guaranteeing zero data loss during network blips or page reloads.
- **Tamper-Evident Receipts**: Instant submission confirmation with SHA-256 cryptographic submission receipt hashes.

### 2. 👁️ AI-Assisted Proctoring & Live Surveillance
- **Continuous Biometric Monitoring**: Real-time webcam feeds, gaze tracking, and multi-face computer vision anomaly detection.
- **Environment Lockdown**: Fullscreen exit detection, tab switches, developer tool inspection attempts, and copy/paste restrictions.
- **Live Auditor Console**: Real-time WebSocket connection streaming active candidate telemetry, video feeds, and violation alerts to proctors.
- **Explainable Risk Scoring**: Deterministic risk score calculation with human reviewer escalation (`VALID`, `SUSPICIOUS`, `CONFIRMED_VIOLATION`, `FALSE_POSITIVE`).

### 3. ⚡ Isolated Coding Sandbox
- **Resource Bounds**: Hard limits on memory (128 MB), CPU time (3.0 seconds), processes, and output payload size.
- **Security Boundary**: Candidate code never executes in the main API server process — executed inside a hardened sandbox.
- **Hidden Test Case Protection**: Sample test cases are visible to candidates; hidden benchmark test cases and expected outputs remain strictly confidential on the server.

### 4. 📚 Question Bank & Assessment Studio
- **Multi-Format Question Authoring**: MCQ Single, MCQ Multiple, Descriptive text, and Coding problem statements.
- **Immutable Version History**: Every question revision creates an immutable version snapshot, ensuring assessments already in progress never alter question definitions retroactively.
- **Custom Grading Rubrics**: Configurable positive marks, negative marking, and passing thresholds.

### 5. 🛡️ High-Security Safe Exam Browser (SEB) Integration
- Dedicated mode supporting Safe Exam Browser configuration keys and Browser Exam Key (BEK) verification headers for high-stakes institutional examinations.

---

## 🏗 System Architecture

```
                      +----------------------------------------------------+
                      |     React + Vite + TypeScript Client (SPA)         |
                      |  - Self-Service Authentication & Role Switcher     |
                      |  - Candidate Examination Engine & Diagnostics      |
                      |  - Recruiter Dashboard & Assessment Builder        |
                      |  - Live AI Proctor Surveillance & Telemetry Grid   |
                      +-------------------------+--------------------------+
                                                |
                                    HTTP / REST + WebSockets
                                                |
                                                v
                      +----------------------------------------------------+
                      |          FastAPI Enterprise Backend API            |
                      |  - Argon2id Password Hashing & Short-Lived JWTs    |
                      |  - Server-Authoritative Exam Timer State Machine   |
                      |  - Dynamic Risk Scoring & Computer Vision Rules    |
                      |  - Liveness & Readiness Probes (/health/ready)     |
                      +------------+--------------------+------------------+
                                   |                    |
                                   v                    v
                   +----------------------------+   +----------------------+
                   |    SQLAlchemy Database     |   |    Docker / Subproc  |
                   |  - Local: SQLite           |   |    Coding Sandbox    |
                   |  - Prod: PostgreSQL 15+    |   |  (CPU/Memory Quotas) |
                   +----------------------------+   +----------------------+
```

---

## 💾 Database Architecture

ProctorAI uses **SQLAlchemy ORM** and is database-agnostic:

| Environment | Database | Connection String | Description |
|---|---|---|---|
| **Local Development** *(Default)* | **SQLite** | `sqlite:///./intellitest.db` | Runs locally with zero configuration. Fully ACID-compliant with foreign key enforcement. |
| **Production** | **PostgreSQL** | `postgresql://proctorai_user:<pass>@localhost:5432/proctorai_db` | Enterprise relational database with connection pooling, migrations, and least-privilege user isolation. |

*To switch to PostgreSQL, set the `DATABASE_URL` variable in `backend/.env`.*

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **Node.js 18+** and **npm**
- **Git**

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/Kanthu2005/PROCTOR-AI.git
cd PROCTOR-AI
```

---

### Step 2: Start the Backend (FastAPI)

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   # Windows PowerShell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   ```bash
   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment file:
   ```bash
   # Copy the environment template
   cp .env.example .env
   ```

5. Launch the backend API server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Probe**: [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

---

### Step 3: Start the Frontend (React + Vite)

1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Launch the Vite development server:
   ```bash
   npm run dev
   ```

- **Web Application Portal**: [http://localhost:3000](http://localhost:3000)

---

### Quick Launch on Windows
You can also launch both the backend and frontend simultaneously using the provided batch launcher:
```cmd
start_prototype.bat
```

---

## 👤 User Registration & Role Workspaces

ProctorAI features a **Self-Service Registration System**. You can create your own custom accounts for any of the supported roles:

1. Open [http://localhost:3000/#/login](http://localhost:3000/#/login).
2. Click the **Register** tab.
3. Fill in your name, email, password, and choose your account role:
   - **Enterprise Recruiter (`RECRUITER`)**: Build technical assessments, configure proctoring rules, invite candidates, and evaluate scores.
   - **Live AI Proctor (`PROCTOR`)**: Real-time surveillance dashboard, anomaly alerts, webcam feeds, and integrity verifications.
   - **Question Author (`QUESTION_AUTHOR`)**: Author and manage questions, test cases, and rubrics.
   - **Candidate / Examinee (`CANDIDATE`)**: Take assigned assessments, run diagnostic camera checks, and complete in-browser coding tests.
   - **Organization Admin (`ORG_ADMIN`)**: Manage team workspace policies and security thresholds.
   - **Platform Admin (`PLATFORM_ADMIN`)**: System health, global telemetry, and security audit logs.
4. Click **Create Account & Sign In** — you will be immediately directed to your dedicated workspace.

---

## 🧪 Automated Testing Suite

ProctorAI includes a comprehensive Pytest test suite covering authentication, RBAC, candidate state machines, timer integrity, and sandbox security:

```bash
cd backend
python -m pytest -v
```

### Key Test Suites:
- `tests/test_candidate_assessment_workflow.py`: End-to-end candidate lifecycle (invitation, device checks, start exam, autosave, submission).
- `tests/test_auth_rbac.py` & `test_auth_rbac_phase2.py`: Password hashing, JWT claims, role boundary enforcement, and cross-tenant isolation.
- `tests/test_server_side_evaluation_and_results.py`: MCQ auto-grading, negative marking, ranking ties, and percentile distribution.
- `tests/test_coding_sandbox_adversarial.py`: Memory bombs, infinite loops, fork bombs, and system call isolation.
- `tests/test_proctoring_reviewer_workflow.py`: Anomaly score calculation, webcam verification, and human audit decisions.
- `tests/test_safe_exam_browser_mode.py`: SEB header validation, config key hashing, and lock-down restrictions.

---

## 🔒 Security Best Practices

- **Argon2id Password Hashing**: State-of-the-art password security resistant to GPU/ASIC cracking.
- **Short-Lived JWTs & Secure Cookies**: Access tokens expire in 15 minutes; refresh tokens stored securely with `SameSite=Lax` and CSRF protection.
- **Zero Hardcoded Secrets**: Secret keys and database credentials are fully externalized via environment variables.
- **Non-Root Code Execution**: Sandboxed code execution with restricted system capabilities and dropped root privileges.
- **Authoritative Server Timer**: Deadlines, countdowns, and attempt transitions are strictly validated by the server.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
