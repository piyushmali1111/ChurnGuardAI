@echo off
title Stop ChurnGuardAI Servers
color 0E
cls

echo =====================================================================
echo                STOPPING churnguardai SERVERS (Ports 8000 & 3000)         
echo =====================================================================
echo.

echo [*] Stopping processes listening on Port 8000 (FastAPI)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo     Killing PID %%a...
    taskkill /F /PID %%a >nul 2>nul
)

echo [*] Stopping processes listening on Port 3000 (Next.js)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo     Killing PID %%a...
    taskkill /F /PID %%a >nul 2>nul
)

echo.
echo [+] ChurnGuardAI servers stopped successfully.
echo.
pause
