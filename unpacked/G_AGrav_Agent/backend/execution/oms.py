from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from backend.storage import storage  # New SQLite-backed storage
from config import config

class OrderManagementSystem:
    """Order Management System (OMS) handling Persistent Paper Execution & Real-time Portfolio State."""

    def __init__(self):
        self.cash_balance: float = config.INITIAL_CAPITAL
        self.portfolio_value: float = config.INITIAL_CAPITAL
        self.realized_pnl: float = 0.0
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []

        self._load_from_db()

    def _save_to_db(self):
        """Persists portfolio balance, positions, and history to the SQLite store."""
        try:
            storage.save_portfolio(
                cash_balance=self.cash_balance,
                portfolio_value=self.portfolio_value,
                realized_pnl=self.realized_pnl,
                positions=self.positions,
                trade_history=self.trade_history,
            )
        except Exception as e:
            print(f"[OMS] Error saving portfolio DB: {e}")

    def _load_from_db(self):
        """Loads persistent portfolio balance and trade history from SQLite."""
        try:
            (
                self.cash_balance,
                self.portfolio_value,
                self.realized_pnl,
                self.positions,
                self.trade_history,
            ) = storage.load_portfolio()
        except Exception as e:
            print(f"[OMS] Error loading portfolio DB: {e}")

    def execute_paper_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a paper order with realistic fee and slippage modeling."""
        asset = order["asset"]
        side = order["side"]
        price = order["price"]
        allocated_capital = order["allocated_capital"]
        
        # Apply paper slippage (10 bps) & fees (5 bps)
        slippage_mult = (1 + config.PAPER_SLIPPAGE_SIMULATION_BPS / 10000) if "BUY" in side else (1 - config.PAPER_SLIPPAGE_SIMULATION_BPS / 10000)
        execution_price = round(price * slippage_mult, 4)
        fee = round(allocated_capital * (config.PAPER_FEE_BPS / 10000), 2)
        
        net_capital = allocated_capital - fee
        units = round(net_capital / max(execution_price, 0.001), 2)

        trade_record = {
            "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": time.strftime("%H:%M:%S"),
            "asset": asset,
            "event_question": order.get("event_question", asset),
            "platform": order.get("platform", "Crypto-Perp"),
            "strategy": order.get("strategy", "AUTO_QUANT"),
            "side": side,
            "market_type": order.get("market_type", "CRYPTO_PERP"),
            "execution_price": execution_price,
            "allocated_capital": allocated_capital,
            "units": units,
            "fee": fee,
            "confidence_pct": order.get("confidence_pct", 85),
            "expected_gain_pct": order.get("expected_gain_pct", 12.5),
            "reasoning": order.get("reasoning", ""),
            "status": "FILLED"
        }

        # Deduct cash & update position state
        self.cash_balance -= allocated_capital
        
        if asset in self.positions:
            pos = self.positions[asset]
            pos["units"] += units
            pos["total_invested"] += net_capital
            pos["current_value"] = pos["units"] * execution_price
        else:
            self.positions[asset] = {
                "asset": asset,
                "event_question": order.get("event_question", asset),
                "platform": order.get("platform", "Crypto-Perp"),
                "market_type": order.get("market_type", "CRYPTO_PERP"),
                "side": side,
                "units": units,
                "entry_price": execution_price,
                "current_price": execution_price,
                "total_invested": net_capital,
                "current_value": net_capital,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "confidence_pct": order.get("confidence_pct", 85),
                "expected_gain_pct": order.get("expected_gain_pct", 12.5),
                "stop_loss": order.get("stop_loss_price"),
                "take_profit": order.get("take_profit_price")
            }

        self.trade_history.insert(0, trade_record)
        self._save_to_db()
        return trade_record

    def update_position_prices(self, current_prices: Dict[str, float]):
        """Updates open positions with latest mark prices and calculates PnL."""
        total_pos_value = 0.0
        for asset, pos in list(self.positions.items()):
            side = pos.get("side", "BUY")
            lookup_key = asset
            if side == "BUY_YES":
                lookup_key = f"{asset}_YES"
            elif side == "BUY_NO":
                lookup_key = f"{asset}_NO"

            if lookup_key in current_prices or asset in current_prices:
                new_price = current_prices.get(lookup_key, current_prices.get(asset, pos["current_price"]))
                pos["current_price"] = new_price
                
                pos["current_value"] = round(pos["units"] * new_price, 2)
                pos["unrealized_pnl"] = round(pos["current_value"] - pos["total_invested"], 2)
                pos["unrealized_pnl_pct"] = round((pos["unrealized_pnl"] / pos["total_invested"]) * 100, 2) if pos["total_invested"] > 0 else 0
                
            total_pos_value += pos["current_value"]

        self.portfolio_value = round(self.cash_balance + total_pos_value, 2)

    def close_position(self, asset: str) -> Optional[Dict[str, Any]]:
        """Liquidates / closes an open position."""
        if asset in self.positions:
            pos = self.positions.pop(asset)
            realized = pos["unrealized_pnl"]
            self.realized_pnl += realized
            self.cash_balance += pos["current_value"]
            self.portfolio_value = round(self.cash_balance + sum(p["current_value"] for p in self.positions.values()), 2)
            
            close_record = {
                "order_id": f"ORD-CLOSE-{uuid.uuid4().hex[:6].upper()}",
                "timestamp": time.strftime("%H:%M:%S"),
                "asset": asset,
                "event_question": pos.get("event_question", asset),
                "platform": pos.get("platform"),
                "strategy": "POSITION_CLOSE",
                "side": "CLOSE",
                "market_type": pos.get("market_type"),
                "execution_price": pos["current_price"],
                "allocated_capital": pos["current_value"],
                "units": pos["units"],
                "fee": 0.0,
                "reasoning": f"Manual or automated position close. Realized PnL: ${realized}",
                "status": "FILLED"
            }
            self.trade_history.insert(0, close_record)
            self._save_to_db()
            return close_record
        return None

oms = OrderManagementSystem()
