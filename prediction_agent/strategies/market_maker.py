"""
Market Making and Bid-Ask Spread Capture Strategy.
Provides passive liquidity inside wide bid-ask spreads to capture round-trip margins.
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

class MarketMakerStrategy(BaseStrategy):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MARKET_MAKING

    async def scan(
        self,
        kalshi_markets: List[NormalizedMarket],
        polymarket_markets: List[NormalizedMarket]
    ) -> List[Opportunity]:
        opportunities: List[Opportunity] = []
        all_markets = kalshi_markets + polymarket_markets

        for m in all_markets:
            if not m.active or not m.yes_bid or not m.yes_ask:
                continue

            spread = m.yes_ask - m.yes_bid
            if spread >= settings.MIN_MM_SPREAD and m.volume_usd > 500:
                # Potential spread capture
                est_fee = FeeCalculator.calculate_fee(m.platform, m.yes_bid, 100, OrderType.LIMIT) / 100 * 2
                net_spread = spread - est_fee

                if net_spread >= 0.02:
                    opp = Opportunity(
                        strategy_name=StrategyType.MARKET_MAKING,
                        description=(
                            f"Spread Capture on {m.platform.value} '{m.title[:40]}...': "
                            f"Bid: ${m.yes_bid:.2f} / Ask: ${m.yes_ask:.2f} (Spread: ${spread:.2f})"
                        ),
                        platform_a=m.platform,
                        ticker_a=m.ticker,
                        theoretical_edge=round(spread, 4),
                        estimated_fees=round(est_fee, 4),
                        net_edge=round(net_spread, 4),
                        timestamp=datetime.now(timezone.utc),
                        actionable=True,
                        metadata={
                            "bid": m.yes_bid,
                            "ask": m.yes_ask,
                            "spread": spread,
                            "title": m.title
                        }
                    )
                    opportunities.append(opp)

        return opportunities

    async def generate_orders(
        self,
        opp: Opportunity,
        balance: AccountBalance
    ) -> List[OrderRequest]:
        bid = opp.metadata.get("bid", 0.0)
        ask = opp.metadata.get("ask", 1.0)
        title = opp.metadata.get("title", opp.ticker_a)

        # Place passive limit orders inside the book
        quote_bid = round(bid + 0.01, 3)
        quote_ask = round(ask - 0.01, 3)

        if quote_bid >= quote_ask:
            return []

        contracts = 50  # Modest quoting size for spread capture

        buy_limit = OrderRequest(
            platform=opp.platform_a,
            market_ticker=opp.ticker_a,
            market_title=title,
            outcome=ContractOutcome.YES,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=quote_bid,
            quantity=contracts,
            strategy_name=StrategyType.MARKET_MAKING
        )

        return [buy_limit]
