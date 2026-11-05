# G_AGrav_Agent — How to Run

## Prerequisites
- Python 3.12+
- Node.js 22+
- pip / npm

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (LLM provider, exchange APIs, etc.)
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## Running

### Option 1: Start scripts (Windows)
```powershell
.\start.ps1          # PowerShell
start.bat            # CMD
```

### Option 2: Manual startup (all platforms)

**Terminal 1 — 内部内部路由信息信息 FastAPI server:**
```bash
cd 内部内部路由信息信息
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend Vite dev server:**
```bash
cd frontend
npm run dev
```

**Terminal 3 (optional) — Prediction agent CLI:**
```bash
python prediction_agent/ui/cli.py
```

## Access

- **Dashboard UI:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs (Swagger)
- **WebSocket:** ws://127.0.0.1:8000/ws

## Architecture

- `backend/` — FastAPI telemetry & agent orchestration server
- `frontend/` — React Vite dashboard UI
- `prediction_agent/` — Autonomous prediction market agent (importable)

## Status

- ✅ Phase-A bootstrap complete
- ✅ SQLite persistence, risk management, Kalshi connector
- ⚠️ CI workflow `.github/workflows/ci.yml` pending (requires `workflow` scope on GitHub token)
