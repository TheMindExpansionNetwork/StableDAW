@echo off
title Stable Audio 3 - Dev Launcher
echo ========================================
echo   Stable Audio 3 - Development Server
echo ========================================
echo.

:: Kill any stale processes on our ports
echo Cleaning up stale processes...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    echo   Killing PID %%a on port 5173
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8600 " ^| findstr "LISTENING"') do (
    echo   Killing PID %%a on port 8600
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Start the backend API server (port 8600)
echo [1/2] Starting backend API server on port 8600...
start "SA3 Backend" cmd /k "cd /d %~dp0 && .venv\Scripts\activate && python -m backend.run"

:: Give backend a moment to bind
timeout /t 3 /nobreak >nul

:: Start the frontend dev server (port 5173)
echo [2/2] Starting frontend dev server on port 5173...
start "SA3 Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers starting:
echo   Backend API:  http://localhost:8600
echo   Frontend UI:  http://localhost:5173
echo.
echo Press any key to open the UI in your browser...
pause >nul
start http://localhost:5173