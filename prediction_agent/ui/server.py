"""
FastAPI Server hosting REST APIs, WebSocket real-time updates, and the Web Dashboard.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from prediction_agent.config import settings
from prediction_agent.database.db import db
from prediction_agent.database.models import (
    OrderRequest, Order, Position, AccountBalance, StrategyType, Platform
)
from prediction_agent.execution.paper_engine import PaperExecutionEngine
from prediction_agent.connectors.kalshi import KalshiConnector
from prediction_agent.connectors.polymarket import PolymarketConnector
from prediction_agent.agent.assistant import TradingAgentAssistant
from prediction_agent.analytics.quant_metrics import QuantMetricsCalculator
from prediction_agent.analytics.brier_score import BrierAnalytics

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Core singletons
kalshi = KalshiConnector()
polymarket = PolymarketConnector()
engine = PaperExecutionEngine(kalshi, polymarket)
assistant = TradingAgentAssistant(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield
    await kalshi.close()
    await polymarket.close()

app = FastAPI(
    title="Prediction Market Quant & Paper-Trading Agent",
    version="1.0.0",
    description="Professional paper trading and quant edge hunting for Kalshi & Polymarket.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- REST Endpoints ----------------- #

@app.get("/api/portfolio")
async def get_portfolio():
    balance = await db.get_account_balance()
    return balance

@app.get("/api/positions")
async def get_positions():
    return await db.get_positions()

@app.get("/api/trades")
async def get_trades(limit: int = 50):
    return await db.get_trades(limit=limit)

@app.get("/api/opportunities")
async def get_opportunities(limit: int = 50):
    return await db.get_recent_opportunities(limit=limit)

@app.get("/api/analytics")
async def get_analytics():
    snapshots = await db.get_portfolio_history(limit=200)
    trades = await db.get_trades(limit=200)
    metrics = QuantMetricsCalculator.calculate_metrics(snapshots, trades)
    fee_drag = BrierAnalytics.compute_fee_drag(trades)
    return {
        "metrics": metrics,
        "fee_drag": fee_drag
    }

@app.post("/api/scan")
async def trigger_scan():
    """Triggers real-time market scan across Kalshi and Polymarket."""
    res = await assistant._tool_scan_opportunities("")
    opps = await db.get_recent_opportunities(limit=20)
    return {"message": res, "opportunities": opps}

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/api/chat")
async def send_chat(req: ChatRequest):
    response = await assistant.chat(req.session_id, req.message)
    return {"session_id": req.session_id, "response": response}

@app.get("/api/chat/sessions")
async def get_chat_sessions():
    return await assistant.memory.list_sessions(limit=30)

@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    return await assistant.memory.get_session_history(session_id, limit=50)

class NewSessionRequest(BaseModel):
    title: str = "New Strategy Chat"

@app.post("/api/chat/sessions")
async def create_chat_session(req: NewSessionRequest):
    import uuid
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    session = await assistant.memory.get_or_create_session(session_id, req.title)
    return session

@app.post("/api/trade")
async def execute_trade(order_req: OrderRequest):
    """Submits order into the paper execution engine."""
    order = await engine.submit_order(order_req)
    return order

# ----------------- Static UI ----------------- #

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Prediction Agent Server Running. Please create index.html in ui/static.</h1>")
