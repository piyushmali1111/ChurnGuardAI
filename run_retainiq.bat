@echo off
title RetainIQ Launcher
color 0A
cls

echo =====================================================================
echo                RETAINIQ: AI CHURN PREVENTION SYSTEM                  
echo =====================================================================
echo.
echo [*] Checking prerequisites...

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [!] ERROR: Python is not found in your PATH.
    echo     Please install Python 3.10+ or add it to your environment variables.
    pause
    exit /b 1
)

:: Check Node / NPM
where npm >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [!] ERROR: npm is not found in your PATH.
    echo     Please install Node.js (v18+) or add it to your environment variables.
    pause
    exit /b 1
)

echo [+] Python and Node/NPM verified.
echo.

:: Check ML model artifact
if not exist "backend\models\churn_model.pkl" (
    echo [*] Churn model artifact not found. Training model now...
    cd backend
    python app\ml\train_churn_model.py
    cd ..
    echo [+] Model trained successfully!
    echo.
)

echo =====================================================================
echo [1/3] Starting Backend Server (FastAPI + LangGraph + Uvicorn)...
echo       URL: http://127.0.0.1:8000
echo       API Docs: http://127.0.0.1:8000/docs
echo =====================================================================
start "RetainIQ Backend (FastAPI :8000)" cmd /k "cd /d %~dp0backend && title RetainIQ Backend (FastAPI :8000) && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: Wait 3 seconds for backend to start up and seed database
timeout /t 3 /nobreak >nul

echo.
echo =====================================================================
echo [2/3] Starting Frontend Server (Next.js 14 + Tailwind)...
echo       URL: http://localhost:3000
echo =====================================================================
start "RetainIQ Frontend (Next.js :3000)" cmd /k "cd /d %~dp0frontend && title RetainIQ Frontend (Next.js :3000) && npm run dev"

:: Wait 4 seconds for frontend to bundle
timeout /t 4 /nobreak >nul

echo.
echo =====================================================================
echo [3/3] Opening RetainIQ in your default web browser...
echo =====================================================================
start http://localhost:3000

echo.
echo =====================================================================
echo               RetainIQ is now running successfully!                  
echo =====================================================================
echo.
echo  * Frontend:      http://localhost:3000
echo  * Backend API:   http://127.0.0.1:8000
echo  * Swagger Docs:  http://127.0.0.1:8000/docs
echo  * WebSockets:    ws://127.0.0.1:8000/ws/agent-activity
echo.
echo  Press any key to close this launcher window.
echo  (The Backend and Frontend console windows will remain running in background)
echo =====================================================================
pause >nul
