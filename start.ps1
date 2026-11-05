# PowerShell Start Script for AETHER Autonomous Trading Agent
$Host.UI.RawUI.WindowTitle = "AETHER Trading Agent"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AETHER Autonomous Crypto & Prediction Markets Agent" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Start Backend FastAPI Server
Write-Host "`n[1/2] Starting Python FastAPI Telemetry & Agent Engine..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\backend'; python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -WindowStyle Normal

# Start Frontend Vite Dev Server
Write-Host "[2/2] Starting React Vite Dashboard UI..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; npm run dev" -WindowStyle Normal

# Wait 3 seconds for Vite server to bind port 3000
Start-Sleep -Seconds 3

# Open Web Dashboard UI in default browser
Write-Host "`n[SUCCESS] Systems online! Opening Dashboard UI in browser..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host "`n----------------------------------------------------------" -ForegroundColor Green
Write-Host "Dashboard UI: http://localhost:3000" -ForegroundColor Green
Write-Host "Backend API:  http://localhost:8000/api/state" -ForegroundColor Green
Write-Host "WebSocket:    ws://127.0.0.1:8000/ws" -ForegroundColor Green
Write-Host "----------------------------------------------------------" -ForegroundColor Green
