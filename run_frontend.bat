@echo off
title Clean Water Initiative — Frontend (Next.js)
echo ========================================================
echo  Starting Clean Water Initiative Frontend (Next.js 16)
echo ========================================================
cd /d "%~dp0frontend"

where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 'npm' was not found in your PATH.
    echo Please install Node.js (https://nodejs.org).
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [INFO] First-time setup: Installing npm dependencies...
    call npm install
)

echo [INFO] Launching Next.js dev server on http://localhost:3000 ...
call npm run dev -- --port 3000
if %ERRORLEVEL% neq 0 pause
