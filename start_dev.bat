@echo off
chcp 65001 >nul
echo ===================================================
echo   URBANPULSE - LOCAL DEV RUNNER (NO DOCKER)
echo ===================================================
echo.

set PYTHONIOENCODING=utf-8

:: Check if db folder exists
if not exist db (
    mkdir db
)

:: Check if web\node_modules exists
if not exist web\node_modules (
    echo [INFO] Installing frontend dependencies in web/...
    cd web
    call npm install
    cd ..
)

echo.
echo [1/2] Starting FastAPI Backend on http://localhost:8000 ...
start "UrbanPulse API (FastAPI)" cmd /k "chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & py -3.13 -m uvicorn api.main:app --reload --port 8000"

echo [2/2] Starting React Vite Frontend on http://localhost:5173 ...
start "UrbanPulse Web (Vite)" cmd /k "cd web & npm run dev"

echo.
echo ===================================================
echo   STACK RUNNING LOCALLY:
echo   - Backend API:  http://localhost:8000
echo   - Swagger Docs: http://localhost:8000/docs
echo   - Web Frontend: http://localhost:5173
echo   - Phase 3 Tests: py -3.13 test_phase3.py
echo ===================================================
echo.
