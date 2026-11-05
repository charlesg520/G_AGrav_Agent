@echo off
title AETHER Autonomous Trading Agent
echo ==========================================================
echo   AETHER Autonomous Crypto & Prediction Markets Agent
echo ==========================================================

echo.
echo [1/2] Starting Python FastAPI Telemetry & Agent Engine...
start "AETHER Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting React Vite Dashboard UI...
start "AETHER Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 3 /nobreak >nul
echo Opening Dashboard UI in default browser...
start http://localhost:3000

echo.
echo ==========================================================
echo Systems online!
echo Dashboard UI: http://localhost:3000
echo Backend API:  http://localhost:8000/api/state
echo WebSocket:    ws://127.0.0.1:8000/ws
echo ==========================================================
