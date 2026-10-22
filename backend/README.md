# ProctorAI - FastAPI Backend

High-concurrency, enterprise-grade FastAPI backend for **ProctorAI**, an AI-powered assessment, proctoring, and candidate evaluation platform.

## Architecture & Capabilities

- **Role-Based Access Control (RBAC)**: Consolidated onto 3 canonical roles: `PLATFORM_ADMIN`, `RECRUITER`, and `CANDIDATE` (with backward-compatible aliases for legacy mappings).
- **Primary Database**: PostgreSQL (production database `aiprotector` managed via Alembic migrations).
- **Multi-Tenant Data Isolation**: Robust tenant scoping with organization validation on all protected routes to prevent IDOR.
- **Assessment Engine**:
  - Full question bank lifecycle (MCQs, Multi-Select, Coding, Descriptive, SQL) with immutable versioning.
  - Granular rule enforcement (custom durations, time windows, negative marking, randomized pools).
  - Server-authoritative countdown timer with idempotent autosave and duplicate submission protection.
- **Proctoring Telemetry & AI**:
  - WebSocket telemetry streaming (`/ws/proctoring/...`) for real-time risk scoring.
  - Multi-face detection, tab switch tracking, audio anomaly detection, and Safe Exam Browser (SEB) support.
  - No simulated security guarantees: verification failures flag `UNABLE_TO_VERIFY` and require human proctor review.
- **Sandboxed Code Execution**:
  - Secure multi-language evaluation (Python, JavaScript/Node.js, Java) against public and hidden test cases.
  - Real-world compiler checking (Python, JavaScript/Node.js, C++, Java, Rust, Go) with graceful `ENVIRONMENT_COMPILER_UNAVAILABLE` feedback when compilers are not installed.
- **Code Similarity & Integrity Engine**:
  - AST and token-normalized pairwise comparison across candidate coding submissions.
  - Generates similarity scores (`0.0 - 1.0`), match review tiers (`SUSPICIOUS_MATCH`, `MODERATE_SIMILARITY`), and investigative advisory warnings.
- **Evaluation & Result Release**:
  - Server-side authoritative grading with cut-off enforcement.
  - Descriptive answer manual grading with optional AI suggestions requiring human confirmation.
  - Anti-leak result publication policies (`IMMEDIATE`, `MANUAL`, and `SCHEDULED` score withholding with cryptographic submission receipts).
- **Testing**: Pytest (163 test cases with 100% pass rate).

## Setup & Running

### 1. Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure required secrets (`SECRET_KEY`, `DATABASE_URL`) are configured.

### 3. Database Migrations
```bash
alembic upgrade head
```

### 4. Run the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger documentation is available at:
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

### 5. Run Test Suite
```bash
pytest -v
```

## License
MIT
