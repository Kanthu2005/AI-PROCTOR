# ProctorAI — Production-Grade AI Online Assessment & Proctoring Platform

ProctorAI is an enterprise-grade AI-powered online evaluation and live proctoring platform. It delivers high-integrity evaluations, automated coding sandboxes, computer vision proctoring, dynamic risk scoring, and cohort analytics.

---

## 🎯 Phase 1 Implementation Status: COMPLETE

Phase 1 establishes the foundational architecture and infrastructure for ProctorAI:
- **Clean Frontend/Backend Structure**: Dedicated `backend/` (FastAPI, SQLAlchemy, Alembic, Pydantic) and `frontend/` (React, Vite, TypeScript, Tailwind CSS).
- **Environment Configuration**: Robust environment variable loading via Pydantic Settings and complete `.env.example` templates across root, backend, and frontend.
- **Dedicated PostgreSQL & Least Privilege**: Dedicated `proctorai_db` database and `proctorai_user` role configuration via `backend/scripts/setup_postgres_least_privilege.sql`.
- **SQLAlchemy Sessions & Connection Pooling**: Production-grade connection pooling (`pool_pre_ping=True`, `pool_size`, `max_overflow`, `pool_recycle`), transactional safety, and Alembic migrations.
- **Health Checks & Error Handling**: Comprehensive liveness (`/health`, `/health/live`) and readiness (`/health/ready`) probes with database connectivity testing, plus consistent JSON exception envelopes.
- **Frontend Routing, Responsive Shell & API Client**: Hash/URL routing, responsive application shell (collapsible mobile navigation drawer + live system health pill), and typed TypeScript API client (`frontend/src/api.ts`).
- **Comprehensive Testing Suite**: 60 automated Pytest test cases covering health checks, configuration, database connectivity, and core platform capabilities.

---

## 🏗 Architecture Overview

```
                      +----------------------------------------------------+
                      |     React + Vite + TypeScript Client (SPA)         |
                      |  - Responsive App Shell & Mobile Drawer Navigation  |
                      |  - Live System & Database Health Telemetry Badge   |
                      |  - Typed API Client (frontend/src/api.ts)          |
                      |  - Candidate Exam Engine & Recruiter Portals       |
                      +-------------------------+--------------------------+
                                                |
                                      HTTP / REST + WebSockets
                                                |
                                                v
                      +----------------------------------------------------+
                      |          FastAPI Enterprise Backend API            |
                      |  - Liveness & Readiness Probes (/health/ready)     |
                      |  - Consistent Exception Envelopes (404, 422, 500)  |
                      |  - Multi-Tenant RBAC Security System               |
                      |  - Authoritative Server Clock & Rules Engine       |
                      +------------+--------------------+------------------+
                                   |                    |
                                   v                    v
                   +---------------------------+   +-----------------------+
                   |  PostgreSQL (Dedicated)   |   |        MongoDB        |
                   |  Database: proctorai_db   |   |   (High-Volume Logs)  |
                   |  Role: proctorai_user     |   |   Telemetry Store     |
                   |  (Least Privilege)        |   +-----------------------+
                   +---------------------------+
```

---

## 🔒 Dedicated PostgreSQL Setup (Least Privilege)

ProctorAI adheres to the principle of least privilege: the application connects to a dedicated database (`proctorai_db`) using a dedicated application user (`proctorai_user`) with restricted schema permissions.

### Option A: Using the Provided SQL Script
Connect to PostgreSQL with your admin client (`psql` or pgAdmin) and execute:
```bash
# In backend/scripts:
psql -U postgres -f backend/scripts/setup_postgres_least_privilege.sql
```

The script performs:
1. Creates dedicated database `proctorai_db` (if not already existing).
2. Creates dedicated role `proctorai_user` with `NOSUPERUSER NOCREATEDB NOCREATEROLE`.
3. Grants `CONNECT, TEMPORARY` strictly to `proctorai_db`.
4. Grants table/sequence privileges only within schema `public` on `proctorai_db`.

### Option B: Using Docker Compose
A production-ready `docker-compose.yml` is provided at the repository root:
```bash
docker-compose up -d postgres mongodb
```
This spins up PostgreSQL configured with the dedicated `proctorai_db` and credentials.

---

## ⚙️ Environment Configuration

Copy the example environment files before launching:

### Root & Backend `.env`
```bash
# Copy backend template
cp backend/.env.example backend/.env
```

Key environment variables in `backend/.env`:
| Variable | Description | Default / Example |
|---|---|---|
| `ENVIRONMENT` | Runtime environment | `development` / `production` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://proctorai_user:<pass>@localhost:5432/proctorai_db` |
| `POSTGRES_SERVER` | PostgreSQL server host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_USER` | Dedicated application user | `proctorai_user` |
| `POSTGRES_PASSWORD` | Secure password | `<CHANGE_TO_YOUR_SECURE_PASSWORD>` |
| `POSTGRES_DB` | Dedicated database name | `proctorai_db` |
| `SECRET_KEY` | JWT signing secret (32+ chars) | `replace-with-a-very-secure-32char-secret` |
| `CORS_ORIGINS` | Permitted browser origins | `http://localhost:3000,http://127.0.0.1:3000` |

### Frontend `.env`
```bash
cp frontend/.env.example frontend/.env
```

---

## 🗄 Alembic Database Migrations

Apply database migrations to keep your database schema up to date:

```powershell
# In the backend directory:
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

To inspect migration status:
```powershell
.\.venv\Scripts\python.exe -m alembic current
```

---

## 🩺 Health Check & Diagnostics Endpoints

ProctorAI provides comprehensive system health endpoints:

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/health` | `GET` | Service Liveness Probe | `{"status": "healthy", "service": "ProctorAI", ...}` |
| `/health/live` | `GET` | Kubernetes / Cloud Liveness | HTTP 200 `healthy` |
| `/health/ready` | `GET` | Readiness & DB Probe (runs `SELECT 1`) | HTTP 200 if connected, HTTP 503 if DB down |
| `/api/v1/health` | `GET` | API Gateway health check | HTTP 200 `healthy` |

Consistent error responses are returned across all endpoints:
```json
{
  "detail": "Descriptive error message",
  "status_code": 404,
  "path": "/api/v1/requested-path"
}
```

---

## 💻 Windows Setup & Local Execution Instructions

### Prerequisites
- **Windows 10 / 11**
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **Node.js 18+ & npm**
- **PostgreSQL 14+** (Local service or Docker container)

---

### Step 1: Backend Setup (PowerShell / Command Prompt)

1. Open PowerShell and navigate to the project directory:
   ```powershell
   cd "C:\Users\KANTHU NAIK\OneDrive\Desktop\PROCTOR-AI\backend"
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(If script execution is disabled in PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

3. Install required Python packages:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure your `.env` file:
   ```powershell
   Copy-Item .env.example .env
   ```
   *(Update `DATABASE_URL` with your PostgreSQL credentials, or leave SQLite default for quick local testing)*

5. Run database migrations:
   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   ```

6. Start the FastAPI backend server:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

- Interactive Swagger API Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health/ready`

---

### Step 2: Frontend Setup (React + Vite + TypeScript)

1. Open a new PowerShell window and navigate to `frontend`:
   ```powershell
   cd "C:\Users\KANTHU NAIK\OneDrive\Desktop\PROCTOR-AI\frontend"
   ```

2. Install dependencies:
   ```powershell
   npm install
   ```

3. Launch the Vite development server:
   ```powershell
   npm run dev
   ```

- Web Application: `http://localhost:3000`

---

### Step 3: Quick Start Using Windows Batch Script
You can launch both the Backend and Frontend with a single double-click using `start_prototype.bat`:
```cmd
start_prototype.bat
```

---

## 🧪 Running Pytest Test Suite

ProctorAI includes 60 automated tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -v
```

### Verified Test Categories (60 Passed):
- `tests/test_phase1_health_and_config.py` (9 tests):
  - Liveness probe (`/health`, `/health/live`)
  - Readiness probe with database connectivity verification (`/health/ready`)
  - Configuration defaults and environment helper properties
  - Database connectivity probe helper (`check_db_connection()`)
  - Consistent error handling envelopes (404 Not Found, 422 Validation)
  - SQLAlchemy session lifecycle and transactional rollback safety
- `tests/test_auth_rbac.py` (8 tests): User registration, JWT login, role boundaries.
- `tests/test_assessment_rules.py` (7 tests): Rules engine, question versioning, negative marking.
- `tests/test_attempt_engine.py` (7 tests): Server timer, autosave, evaluation.
- `tests/test_candidate_invitations.py` (6 tests): Bulk invites, token verification, system checks.
- `tests/test_proctoring_risk.py` (6 tests): Tab switch detection, dynamic risk scoring, human review.
- `tests/test_question_versioning.py` (6 tests): Question types, version immutability.
- `tests/test_recruiter_workflow.py` (6 tests): Recruiter approval workflows and multi-tenant isolation.
- `tests/test_sandbox_and_analytics.py` (5 tests): Sandbox execution, rankings, percentiles.

---

## 🔑 Pre-Seeded Demonstration Accounts

| Role | Email | Password |
|---|---|---|
| Platform Admin | `admin@intellitest.ai` | `Admin@12345` |
| Org Admin | `orgadmin@acme.com` | `Acme@12345` |
| Recruiter | `recruiter@acme.com` | `Recruit@12345` |
| Question Author | `author@acme.com` | `Author@12345` |
| AI Proctor | `proctor@acme.com` | `Proctor@12345` |
| Candidate | `candidate@example.com` | `Candidate@12345` |
