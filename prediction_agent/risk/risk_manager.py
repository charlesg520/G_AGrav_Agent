"""
Portfolio Risk Management and Safety Circuit Breakers.
"""

import logging
from typing import Tuple
from prediction_agent.config import settings
from prediction_agent.database.models import OrderRequest, OrderSide

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(
        self,
        max_position_size_usd: float = settings.MAX_POSITION_SIZE_USD,
        max_portfolio_exposure: float = settings.MAX_PORTFOLIO_EXPOSURE,
        max_drawdown_limit: float = settings.MAX_DRAWDOWN_LIMIT
    ):
        self.max_position_size = max_position_size_usd
        self.max_exposure = max_portfolio_exposure
        self.max_drawdown = max_drawdown_limit

    def validate_order(
        self,
        req: OrderRequest,
        portfolio_equity: float,
        cash_balance: float,
        current_drawdown: float = 0.0
    ) -> Tuple[bool, int, str]:
        """
        Validates order against drawdown limits, cash reserves, and maximum position caps.
        Returns: (approved, adjusted_quantity, reason)
        """
        # 1. Circuit breaker: Max drawdown breach
        if current_drawdown > self.max_drawdown:
            return False, 0, f"Order rejected: Portfolio drawdown ({current_drawdown:.1%}) exceeds circuit breaker ({self.max_drawdown:.1%})"

        # Sells are always permitted to de-risk
        if req.side == OrderSide.SELL:
            return True, req.quantity, "Sell order approved for de-risking"

        # 2. Minimum cash reserve check
        min_cash_required = portfolio_equity * (1.0 - self.max_exposure)
        available_spending_cash = max(0.0, cash_balance - min_cash_required)

        if available_spending_cash <= 0.0:
            return False, 0, f"Order rejected: Portfolio cash ({cash_balance:.2f}) at or below reserve buffer ({min_cash_required:.2f})"

        # 3. Maximum position dollar cap
        target_cost = req.price * req.quantity
        allowed_cost = min(target_cost, self.max_position_size, available_spending_cash)

        if allowed_cost < target_cost:
            adjusted_qty = int(allowed_cost // req.price)
            if adjusted_qty <= 0:
                return False, 0, f"Order rejected: Allowed allocation ($ {allowed_cost:.2f}) cannot purchase 1 contract at ${req.price:.2f}"
            return True, adjusted_qty, f"Order quantity adjusted from {req.quantity} to {adjusted_qty} to comply with risk caps"

        return True, req.quantity, "Order approved within risk parameters"
