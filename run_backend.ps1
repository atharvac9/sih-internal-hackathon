# Clean Water Initiative — Backend Runner (PowerShell)
$Host.UI.RawUI.WindowTitle = "Clean Water Initiative — Backend (FastAPI)"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Starting Clean Water Initiative Backend API (FastAPI)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\backend"

if (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe") {
    Write-Host "[INFO] Detected project virtualenv. Launching FastAPI server..." -ForegroundColor Green
    & "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] Detected 'uv'. Launching FastAPI server..." -ForegroundColor Green
    uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] Detected system Python. Launching FastAPI server..." -ForegroundColor Green
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} else {
    Write-Host "[ERROR] Neither 'uv' nor 'python' was found in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.11+ or uv (https://astral.sh/uv)." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
}
