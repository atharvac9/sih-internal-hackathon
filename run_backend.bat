@echo off
title Clean Water Initiative — Backend (FastAPI)
echo ========================================================
echo  Starting Clean Water Initiative Backend API (FastAPI)
echo ========================================================
cd /d "%~dp0backend"

:: Auto-create .env from .env.example if missing
if not exist "%~dp0.env" if not exist "%~dp0backend\.env" (
    if exist "%~dp0.env.example" (
        echo [INFO] First-time setup: Creating initial .env from .env.example (DEMO_MODE=true)...
        copy "%~dp0.env.example" "%~dp0.env" >nul
    )
)

:: 1. Check existing .venv
if exist "%~dp0.venv\Scripts\python.exe" (
    echo [INFO] Detected project virtualenv. Launching FastAPI server...
    "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    goto end
)

:: 2. Try running via uv
where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] Detected 'uv' package manager. Launching FastAPI server...
    uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    goto end
)

:: 3. If python is available, create virtualenv and install dependencies on first run
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] First-time setup: Setting up Python virtual environment...
    python -m venv "%~dp0.venv"
    if exist "%~dp0.venv\Scripts\python.exe" (
        echo [INFO] Installing backend dependencies (this may take a couple minutes)...
        "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0backend\requirements.txt"
        echo [INFO] Launching FastAPI server...
        "%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
        goto end
    )
    echo [INFO] Detected system Python. Launching FastAPI server...
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    goto end
)

echo [ERROR] Neither 'uv' nor 'python' was found in your PATH.
echo Please install Python 3.11+ or uv (https://astral.sh/uv).
pause

:end
