@echo off
title Clean Water Initiative — Launch All
echo ========================================================
echo  Launching Clean Water Initiative (Backend + Frontend)
echo ========================================================
echo.
echo 1. Starting Backend API window on http://127.0.0.1:8000 ...
start "Clean Water Backend (FastAPI)" cmd /k call "%~dp0run_backend.bat"

echo 2. Starting Frontend Next.js window on http://localhost:3000 ...
start "Clean Water Frontend (Next.js)" cmd /k call "%~dp0run_frontend.bat"

echo.
echo Both servers have been launched in separate terminal windows!
echo - Frontend Dashboard: http://localhost:3000
echo - Backend API Docs:   http://127.0.0.1:8000/docs
echo.
pause
