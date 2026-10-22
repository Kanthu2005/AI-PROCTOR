# ProctorAI - Frontend

Modern, high-performance React + Vite frontend for **ProctorAI**, an AI-powered assessment, live proctoring, and evaluation platform.

## Features

- **Candidate Examination Engine**:
  - Token-validated exam access and verification flow.
  - Multi-stage onboarding: System diagnostics (camera, mic, network, fullscreen), instructions, identity verification, and exam consent.
  - Delivery mode visibility: Standard Browser (with explicit OS limitation disclaimer) vs Verified Safe Exam Browser (SEB) mode.
  - Rich question renderers: Single/multiple-choice MCQs and multi-language coding questions with embedded code editor and test execution.
  - Live proctoring monitoring with automatic face tracking, focus loss/tab switch detection, clipboard paste tracking, and anti-cheating alerts.
- **Recruiter & Admin Hub**:
  - Consolidated into canonical `PLATFORM_ADMIN` and `RECRUITER` views.
  - Live candidate attempt monitoring with risk-tier sorting and review workflows.
  - Assessment builder with dynamic rules, timing constraints, and negative marking configurations.
  - Question bank management with versioning, difficulty tagging, and multi-language support.
  - Results & Analytics view with candidate drilldown, manual descriptive grading with AI score suggestions, and official decision release (`PASSED`, `SHORTLISTED`, `FAILED`, `REJECTED`).
  - Cohort Code Similarity & Integrity Analysis with interactive threshold filters (60%-95%) and investigative advisory notices.
  - Cohort analytics, percentile rankings, and native CSV/PDF export.
- **Live Proctor Reviewer Portal**:
  - Real-time candidate feed inspection with WebSocket anomaly event telemetry.
  - Incident verification, manual warnings, human review decisions, and escalation controls.

## Tech Stack

- **Framework**: React 18, Vite 5
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **Routing**: Client-side hash routing with history synchronization
- **Communication**: REST API + WebSockets (`/api` and `/ws` reverse-proxied to backend)

## Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure `VITE_API_BASE_URL` points to your running backend:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```
The application will launch on `http://localhost:3000`.

### 4. Build for Production
```bash
npm run build
```
Build outputs are generated in the `dist/` directory.

## License
MIT
