@echo off
REM ============================================================
REM  R & D LIMS - local launcher
REM  Starts the FastAPI backend (port 8443) and the Vite
REM  frontend (port 5174), each in its own window.
REM ============================================================

setlocal
REM  Resolve paths relative to this script, so it runs from anywhere.
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend-v2"
set "FRONTEND=%ROOT%frontend-react"

echo ============================================================
echo   Starting R ^& D LIMS
echo   Backend : http://127.0.0.1:8443   (API docs: /docs)
echo   Frontend: http://localhost:5174
echo ============================================================
echo.

REM  --- Backend ---
if not exist "%BACKEND%\.env" (
    echo [WARN] %BACKEND%\.env not found. Copy .env.example to .env first.
)
echo Launching backend...
start "R&D LIMS - Backend" cmd /k "cd /d "%BACKEND%" && python -m uvicorn src.main:app --host 127.0.0.1 --port 8443"

REM  --- Frontend ---
echo Launching frontend...
if not exist "%FRONTEND%\node_modules" (
    echo node_modules missing - running npm install first...
    start "R&D LIMS - Frontend" cmd /k "cd /d "%FRONTEND%" && npm install && npm run dev"
) else (
    start "R&D LIMS - Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"
)

REM  Give the frontend a few seconds to boot, then open the browser.
timeout /t 6 /nobreak >nul
start "" "http://localhost:5174"

echo.
echo Both services are starting in separate windows.
echo Close those windows (or press Ctrl+C in them) to stop the app.
endlocal
