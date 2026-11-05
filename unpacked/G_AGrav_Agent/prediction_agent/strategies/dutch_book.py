"""
Multi-Outcome Dutch Book Arbitrage Strategy.
Exploits pricing inefficiencies in categorical events where mutually exclusive outcomes
fail to sum to 100% (Sum of Asks < 1.00 or Sum of Bids > 1.00).
"""

import logging
from typing import List, Dict
from collections import defaultdict
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

class DutchBookStrategy(BaseStrategy):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.DUTCH_BOOK

    async def scan(
        self,
        kalshi_markets: List[NormalizedMarket],
        polymarket_markets: List[NormalizedMarket]
    ) -> List[Opportunity]:
        opportunities: List[Opportunity] = []
        
        # Group Kalshi markets by event_ticker
        kalshi_events: Dict[str, List[NormalizedMarket]] = defaultdict(list)
        for m in kalshi_markets:
            ev_ticker = m.raw_data.get("event_ticker")
            if ev_ticker:
                kalshi_events[ev_ticker].append(m)

        for ev_ticker, markets in kalshi_events.items():
            if len(markets) < 2:
                continue

            # Mutually exclusive sum check
            total_ask = 0.0
            valid_basket = True
            legs = []

            for m in markets:
                if m.yes_ask and m.yes_ask > 0:
                    total_ask += m.yes_ask
                    legs.append({"ticker": m.ticker, "price": m.yes_ask, "title": m.title})
                else:
                    valid_basket = False
                    break

            if valid_basket and total_ask > 0:
                est_fee_per_leg = 0.005
                total_fees = len(legs) * est_fee_per_leg
                net_edge = 1.0 - total_ask - total_fees

                if net_edge >= settings.MIN_DUTCH_BOOK_EDGE:
                    opp = Opportunity(
                        strategy_name=StrategyType.DUTCH_BOOK,
                        description=(
                            f"Dutch Book Basket Arb on Kalshi event {ev_ticker}: "
                            f"Sum of Asks = ${total_ask:.3f} (< $1.00 across {len(legs)} outcomes)"
                        ),
                        platform_a=Platform.KALSHI,
                        ticker_a=ev_ticker,
                        theoretical_edge=round(1.0 - total_ask, 4),
                        estimated_fees=round(total_fees, 4),
                        net_edge=round(net_edge, 4),
                        timestamp=datetime.now(timezone.utc),
                        actionable=True,
                        metadata={"legs": legs, "total_ask": round(total_ask, 4)}
                    )
                    opportunities.append(opp)

        return opportunities

    async def generate_orders(
        self,
        opp: Opportunity,
        balance: AccountBalance
    ) -> List[OrderRequest]:
        legs = opp.metadata.get("legs", [])
        if not legs:
            return []

        total_ask = opp.metadata.get("total_ask", 1.0)
        max_alloc = min(balance.cash_balance * 0.15, settings.MAX_POSITION_SIZE_USD)
        contracts = max(1, int(max_alloc // total_ask))

        orders: List[OrderRequest] = []
        for leg in legs:
            orders.append(
                OrderRequest(
                    platform=opp.platform_a,
                    market_ticker=leg["ticker"],
                    market_title=leg.get("title", ""),
                    outcome=ContractOutcome.YES,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    price=leg["price"],
                    quantity=contracts,
                    strategy_name=StrategyType.DUTCH_BOOK
                )
            )

        return orders
