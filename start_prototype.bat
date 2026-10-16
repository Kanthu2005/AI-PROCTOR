@echo off
echo ========================================================
echo   Starting ProctorAI Platform (MVP Prototype)
echo   Assess. Monitor. Evaluate. Hire.
echo ========================================================

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "ProctorAI Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Launching React Vite Frontend on http://localhost:3000 ...
start "ProctorAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================================
echo   ProctorAI is now running!
echo   Landing Page & Portals: http://localhost:3000
echo   Interactive Swagger Docs: http://localhost:8000/docs
echo ========================================================
echo.
