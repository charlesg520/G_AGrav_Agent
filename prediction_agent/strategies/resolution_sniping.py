"""
Resolution Convergence and Certainty Sniping Strategy.
Scans for contracts trading at 96c-99c where the market outcome is near-certain,
securing high annualized returns as contracts converge to $1.00 at settlement.
"""

import logging
from typing import List
from datetime import datetime, timezone

from prediction_agent.config import settings
from prediction_agent.connectors.base import NormalizedMarket
from prediction_agent.database.models import (
    Opportunity, OrderRequest, StrategyType, Platform,
    OrderSide, OrderType, ContractOutcome, AccountBalance
)
from prediction_agent.strategies.base import BaseStrategy
from prediction_agent.execution.fee_calculator import FeeCalculator

logger = logging.getLogger(__name__)

class ResolutionSnipingStrategy(BaseStrategy):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.RESOLUTION_SNIPING

    async def scan(
        self,
        kalshi_markets: List[NormalizedMarket],
        polymarket_markets: List[NormalizedMarket]
    ) -> List[Opportunity]:
        opportunities: List[Opportunity] = []
        all_markets = kalshi_markets + polymarket_markets

        for m in all_markets:
            if not m.active or not m.yes_ask:
                continue

            price = m.yes_ask
            if settings.CONVERGENCE_MIN_PROBABILITY <= price <= 0.99:
                est_fee = FeeCalculator.calculate_fee(m.platform, price, 100, OrderType.MARKET) / 100
                potential_gain = 1.0 - price
                net_gain = potential_gain - est_fee

                if net_gain > 0.005:  # At least 0.5% net profit on capital
                    opp = Opportunity(
                        strategy_name=StrategyType.RESOLUTION_SNIPING,
                        description=(
                            f"Certainty Sniping on {m.platform.value} '{m.title[:45]}...': "
                            f"Trading at ${price:.2f} (Implied {int(price*100)}%), yielding +${net_gain:.3f} net at $1.00 resolution"
                        ),
                        platform_a=m.platform,
                        ticker_a=m.ticker,
                        theoretical_edge=round(potential_gain, 4),
                        estimated_fees=round(est_fee, 4),
                        net_edge=round(net_gain, 4),
                        timestamp=datetime.now(timezone.utc),
                        actionable=True,
                        metadata={
                            "price": price,
                            "title": m.title,
                            "close_time": m.close_time.isoformat() if m.close_time else None
                        }
                    )
                    opportunities.append(opp)

        return opportunities

    async def generate_orders(
        self,
        opp: Opportunity,
        balance: AccountBalance
    ) -> List[OrderRequest]:
        price = opp.metadata.get("price", 0.97)
        title = opp.metadata.get("title", opp.ticker_a)

        target_usd = min(balance.cash_balance * 0.10, settings.MAX_POSITION_SIZE_USD)
        contracts = max(1, int(target_usd // price))

        order = OrderRequest(
            platform=opp.platform_a,
            market_ticker=opp.ticker_a,
            market_title=title,
            outcome=ContractOutcome.YES,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=price,
            quantity=contracts,
            strategy_name=StrategyType.RESOLUTION_SNIPING
        )

        return [order]
