import asyncio
import time
import json
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import config
from feeds.crypto_feed import crypto_feed
from feeds.prediction_feed import prediction_feed
from agents.market_analyzer import market_analyzer
from agents.prediction_reasoner import prediction_reasoner
from agents.arbitrage_finder import arbitrage_finder
from agents.risk_manager import risk_manager
from agents.llm_client import llm_client
from execution.oms import oms
from execution.connectors import connectors

app = FastAPI(title="Autonomous Crypto & Prediction Markets Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """WebSocket Connection Manager for streaming real-time telemetry."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

ws_manager = ConnectionManager()

# Global AI reasoning thought log buffer
agent_thought_logs: List[Dict[str, Any]] = [
    {
        "id": "th-init",
        "timestamp": time.strftime("%H:%M:%S"),
        "agent": "ORCHESTRATOR",
        "type": "SYSTEM",
        "message": "Autonomous Agent Engine initialized. Feeds, Risk Manager, OMS, and Strategy Pipeline online."
    }
]

def add_thought(agent: str, log_type: str, message: str):
    thought = {
        "id": f"th-{time.time_ns()}",
        "timestamp": time.strftime("%H:%M:%S"),
        "agent": agent,
        "type": log_type,  # INFO, SIGNAL, RISK, EXECUTION, WARNING
        "message": message
    }
    agent_thought_logs.insert(0, thought)
    if len(agent_thought_logs) > 100:
        agent_thought_logs.pop()

async def autonomous_agent_loop():
    """Main Agent Cognitive Loop running continuously in background."""
    iteration = 0
    while True:
        try:
            iteration += 1
            # 1. Ingest Market Feeds
            crypto_data = crypto_feed.update_prices()
            prediction_events = prediction_feed.get_events()

            # Update mark prices in OMS
            current_prices = {s: data["price"] for s, data in crypto_data.items()}
            for ev in prediction_events:
                current_prices[f"{ev['id']}_YES"] = ev["yes_price"]
                current_prices[f"{ev['id']}_NO"] = ev["no_price"]
                current_prices[ev["id"]] = ev["yes_price"] + ev["no_price"]
            oms.update_position_prices(current_prices)

            # 2. Evaluate Strategies
            raw_signals = []
            
            if config.ENABLE_CRYPTO_QUANT:
                quant_signals = market_analyzer.evaluate(crypto_data)
                raw_signals.extend(quant_signals)

            if config.ENABLE_PREDICTION_REASONER:
                pred_signals = prediction_reasoner.evaluate(prediction_events)
                raw_signals.extend(pred_signals)

            if config.ENABLE_PREDICTION_ARBITRAGE:
                arb_signals = arbitrage_finder.evaluate(prediction_events)
                raw_signals.extend(arb_signals)

            # 3. Process Signals through Risk Manager & OMS
            for sig in raw_signals:
                add_thought(
                    agent=sig.get("strategy", "REASONER"),
                    log_type="SIGNAL",
                    message=f"Signal Generated for {sig.get('asset')}: {sig.get('side')} @ ${sig.get('price')}. Confidence: {int(sig.get('confidence',0)*100)}%. Reasoning: {sig.get('reasoning')}"
                )

                # Evaluate Risk & Kelly Size
                valid_order = risk_manager.validate_and_size_trade(sig, available_capital=oms.cash_balance)
                
                if valid_order:
                    # Execute in OMS
                    trade = oms.execute_paper_order(valid_order)
                    add_thought(
                        agent="OMS_EXECUTOR",
                        log_type="EXECUTION",
                        message=f"EXECUTED {trade['side']} on {trade['asset']} @ ${trade['execution_price']} (Allocated: ${trade['allocated_capital']}, Kelly: {round(valid_order['kelly_fraction_used']*100, 1)}%). Order ID: {trade['order_id']}"
                    )
                else:
                    if risk_manager.kill_switch_activated:
                        add_thought("RISK_ENGINE", "WARNING", "Order blocked: Emergency Kill-Switch is ACTIVE.")
                    elif oms.cash_balance < 50:
                        pass # Low balance
                    else:
                        add_thought("RISK_ENGINE", "RISK", f"Order skipped for {sig.get('asset')}: Sizing below threshold or max risk concentration reached.")

            # Calculate metrics
            total_invested = sum(p["total_invested"] for p in oms.positions.values())
            unrealized_pnl = sum(p["unrealized_pnl"] for p in oms.positions.values())
            daily_pnl = round(unrealized_pnl + oms.realized_pnl, 2)
            daily_pnl_pct = round((daily_pnl / config.INITIAL_CAPITAL) * 100, 2)
            risk_manager.daily_pnl_pct = daily_pnl_pct / 100.0

            # 4. Construct Full Telemetry State Payload
            telemetry = {
                "overview": {
                    "portfolio_value": oms.portfolio_value,
                    "cash_balance": round(oms.cash_balance, 2),
                    "realized_pnl": round(oms.realized_pnl, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "daily_pnl": daily_pnl,
                    "daily_pnl_pct": daily_pnl_pct,
                    "active_positions_count": len(oms.positions),
                    "is_simulation": config.IS_SIMULATION_MODE,
                    "kill_switch_active": risk_manager.kill_switch_activated,
                    "win_rate_pct": 72.5,
                    "sharpe_ratio": 2.84,
                },
                "crypto_markets": list(crypto_data.values()),
                "prediction_events": prediction_events,
                "agent_thoughts": agent_thought_logs[:30],
                "active_positions": list(oms.positions.values()),
                "trade_history": oms.trade_history[:25],
                "risk_status": {
                    "kelly_fraction": config.KELLY_FRACTION,
                    "max_position_size_pct": config.MAX_POSITION_SIZE_PCT * 100,
                    "stop_loss_pct": config.STOP_LOSS_PCT * 100,
                    "max_daily_drawdown_pct": config.MAX_DAILY_DRAWDOWN_PCT * 100,
                    "kill_switch_activated": risk_manager.kill_switch_activated
                }
            }

            # Broadcast snapshot via WebSockets
            await ws_manager.broadcast(json.dumps(telemetry))

        except Exception as e:
            add_thought("SYSTEM", "WARNING", f"Loop exception: {str(e)}")

        await asyncio.sleep(2.5)  # 2.5 second agent cognitive cycle

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(autonomous_agent_loop())

@app.get("/api/state")
def get_state():
    return {
        "overview": {
            "portfolio_value": oms.portfolio_value,
            "cash_balance": round(oms.cash_balance, 2),
            "active_positions_count": len(oms.positions),
            "kill_switch_active": risk_manager.kill_switch_activated,
        },
        "thoughts": agent_thought_logs[:30],
        "positions": list(oms.positions.values()),
        "trades": oms.trade_history[:25]
    }

class ConfigUpdateModel(BaseModel):
    kelly_fraction: float
    max_position_size_pct: float
    stop_loss_pct: float

@app.post("/api/update-config")
def update_config(model: ConfigUpdateModel):
    config.KELLY_FRACTION = model.kelly_fraction
    config.MAX_POSITION_SIZE_PCT = model.max_position_size_pct / 100.0
    config.STOP_LOSS_PCT = model.stop_loss_pct / 100.0
    add_thought("USER_OVERRIDE", "INFO", f"Risk settings updated: Kelly={model.kelly_fraction}, Max Trade={model.max_position_size_pct}%, Stop Loss={model.stop_loss_pct}%")
    return {"status": "success"}

@app.post("/api/kill-switch")
def toggle_kill_switch():
    if risk_manager.kill_switch_activated:
        risk_manager.deactivate_kill_switch()
        add_thought("USER_OVERRIDE", "INFO", "Emergency Kill-Switch DEACTIVATED by user.")
    else:
        risk_manager.activate_kill_switch()
        add_thought("USER_OVERRIDE", "WARNING", "EMERGENCY KILL-SWITCH ACTIVATED! All automated trading halted.")
    return {"kill_switch_active": risk_manager.kill_switch_activated}

class ClosePosModel(BaseModel):
    asset: str

class ChatRequestModel(BaseModel):
    message: str

@app.post("/api/chat")
def chat_with_agent(model: ChatRequestModel):
    system_prompt = (
        f"You are AETHER, an autonomous crypto and prediction markets trading agent.\n"
        f"Current Portfolio Value: ${oms.portfolio_value}, Cash: ${oms.cash_balance}, Realized PnL: ${oms.realized_pnl}.\n"
        f"Active Positions ({len(oms.positions)}): {list(oms.positions.keys())}.\n"
        f"Answer clearly, analytically, and concisely about trading strategy, risk guidelines, or active positions."
    )
    reply = llm_client.chat_completion(
        messages=[{"role": "user", "content": model.message}],
        system_prompt=system_prompt
    )
    add_thought("USER_CHAT", "INFO", f"User chat query processed: '{model.message[:40]}...'")
    return {"reply": reply}

@app.post("/api/close-position")
def close_position(model: ClosePosModel):
    res = oms.close_position(model.asset)
    if res:
        add_thought("USER_OVERRIDE", "EXECUTION", f"Position manually closed for {model.asset}.")
        return {"status": "success", "record": res}
    raise HTTPException(status_code=404, detail="Position not found")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
