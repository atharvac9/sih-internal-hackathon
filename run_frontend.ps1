# Clean Water Initiative — Frontend Runner (PowerShell)
$Host.UI.RawUI.WindowTitle = "Clean Water Initiative — Frontend (Next.js)"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Starting Clean Water Initiative Frontend (Next.js 16)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\frontend"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] 'npm' was not found in your PATH." -ForegroundColor Red
    Write-Host "Please install Node.js (https://nodejs.org)." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] First-time setup: Installing npm packages..." -ForegroundColor Yellow
    npm install
}

Write-Host "[INFO] Launching Next.js dev server on http://localhost:3000 ..." -ForegroundColor Green
npm run dev -- --port 3000
