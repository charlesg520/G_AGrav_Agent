from typing import Dict, Any, Optional
from config import config

class RiskManagerEngine:
    """Enterprise Risk Engine enforcing Fractional Kelly Sizing, Drawdown Circuit Breakers & Stop-Losses."""

    def __init__(self):
        self.kill_switch_activated: bool = False
        self.daily_pnl_pct: float = 0.0
        self.total_portfolio_value: float = config.INITIAL_CAPITAL

    def activate_kill_switch(self):
        """Immediately halts all automated order executions."""
        self.kill_switch_activated = True

    def deactivate_kill_switch(self):
        self.kill_switch_activated = False

    def validate_and_size_trade(self, signal: Dict[str, Any], available_capital: float) -> Optional[Dict[str, Any]]:
        """Evaluates trade signal, computes Kelly position size, and validates risk constraints."""
        
        # 1. Circuit Breakers Check
        if self.kill_switch_activated:
            return None
        
        if self.daily_pnl_pct <= -config.MAX_DAILY_DRAWDOWN_PCT:
            # Daily drawdown circuit breaker hit!
            return None

        price = signal.get("price", 1.0)
        confidence = signal.get("confidence", 0.5)
        market_type = signal.get("market_type", "CRYPTO_PERP")
        edge = signal.get("expected_gain_pct", 0.0) / 100.0  # convert to decimal
        settlement_hours = signal.get("hours_to_settlement", 9999)

        # --- New Phase-A hard risk filters ---
        # 1) Minimum edge 10%
        if edge < 0.10:
            return None
        # 2) Settlement must be within 48h
        if settlement_hours > 48:
            return None

        # 2. Position Sizing via Fractional Kelly Criterion
        if market_type == "PREDICTION_MARKET":
            fair_p = signal.get("fair_probability", 0.5)
            if signal.get("strategy") == "PREDICTION_YIELD_ARBITRAGE":
                # Risk-free arbitrage: standard fixed safe sizing (e.g. 10% of portfolio)
                kelly_pct = 0.10
            else:
                # Binary Kelly: f* = (p * b - q) / b
                b = (1.0 - price) / max(price, 0.01)
                q = 1.0 - fair_p
                raw_kelly = (fair_p * b - q) / max(b, 0.01) if b > 0 else 0
                kelly_pct = max(0.01, min(raw_kelly * config.KELLY_FRACTION, config.MAX_POSITION_SIZE_PCT))
        else:
            # Crypto Perps Sizing based on confidence & volatility
            kelly_pct = max(0.02, min(confidence * 0.12 * config.KELLY_FRACTION, config.MAX_POSITION_SIZE_PCT))

        # Calculate dollar allocation
        target_allocation = available_capital * kelly_pct
        target_allocation = min(target_allocation, available_capital * config.MAX_POSITION_SIZE_PCT)

        if target_allocation < 10.0:  # Minimum trade threshold $10
            return None

        # 3. Calculate Risk Exit Levels (Stop Loss / Take Profit)
        side = signal.get("side", "BUY")
        if "BUY" in side or "LONG" in side:
            stop_loss = round(price * (1.0 - config.STOP_LOSS_PCT), 4)
            take_profit = round(price * (1.0 + config.TAKE_PROFIT_PCT), 4)
        else:
            stop_loss = round(price * (1.0 + config.STOP_LOSS_PCT), 4)
            take_profit = round(price * (1.0 - config.TAKE_PROFIT_PCT), 4)

        trade_order = {
            **signal,
            "allocated_capital": round(target_allocation, 2),
            "kelly_fraction_used": round(kelly_pct, 4),
            "quantity": round(target_allocation / max(price, 0.001), 2),
            "stop_loss_price": stop_loss,
            "take_profit_price": take_profit,
            "timestamp": signal.get("timestamp")
        }

        return trade_order

risk_manager = RiskManagerEngine()
