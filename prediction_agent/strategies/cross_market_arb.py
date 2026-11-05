"""
Cross-Platform Arbitrage Strategy between Kalshi and Polymarket.
Scans for identical underlying events across both exchanges and captures risk-free
pricing discrepancies when (Yes_Ask_PlatformA + No_Ask_PlatformB < 1.00 - fees).
"""

import re
import logging
from typing import List, Tuple, Set, Optional
from datetime import datetime, timezone

from prediction_agent.config import settings
from prediction_agent.connectors.base import NormalizedMarket
from prediction_agent.database.models import (
    Opportunity, OrderRequest, StrategyType, Platform,
    OrderSide, OrderType, ContractOutcome, AccountBalance
)
from prediction_agent.strategies.base import BaseStrategy
from prediction_agent.execution.fee_calculator import FeeCalculator
from prediction_agent.risk.kelly import KellyEngine

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "will", "the", "a", "an", "in", "by", "before", "on", "of", "to", "at",
    "be", "is", "for", "or", "and", "next", "new", "who", "what", "which"
}

def clean_tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}

def compute_similarity(title_a: str, title_b: str) -> float:
    tokens_a = clean_tokens(title_a)
    tokens_b = clean_tokens(title_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)

class CrossMarketArbitrageStrategy(BaseStrategy):
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.CROSS_MARKET_ARB

    async def scan(
        self,
        kalshi_markets: List[NormalizedMarket],
        polymarket_markets: List[NormalizedMarket]
    ) -> List[Opportunity]:
        opportunities: List[Opportunity] = []

        for km in kalshi_markets:
            if not km.active:
                continue

            for pm in polymarket_markets:
                if not pm.active:
                    continue

                # Compute semantic / keyword similarity
                sim = compute_similarity(km.title, pm.title)
                if sim < 0.40:  # Match threshold
                    continue

                # Scenario 1: Buy YES on Polymarket, Buy NO on Kalshi
                if pm.yes_ask and km.no_ask:
                    cost = pm.yes_ask + km.no_ask
                    p_fee = FeeCalculator.calculate_polymarket_fee(pm.yes_ask, 100, OrderType.MARKET) / 100
                    k_fee = FeeCalculator.calculate_kalshi_fee(km.no_ask, 100, OrderType.MARKET) / 100
                    est_fees = p_fee + k_fee
                    net_edge = 1.0 - cost - est_fees

                    if net_edge >= settings.MIN_ARB_NET_EDGE:
                        opp = Opportunity(
                            strategy_name=StrategyType.CROSS_MARKET_ARB,
                            description=(
                                f"Cross-Platform Arb: Buy YES on Polymarket (${pm.yes_ask:.2f}) + "
                                f"Buy NO on Kalshi (${km.no_ask:.2f}) on '{km.title[:45]}...'"
                            ),
                            platform_a=Platform.POLYMARKET,
                            ticker_a=pm.ticker,
                            platform_b=Platform.KALSHI,
                            ticker_b=km.ticker,
                            theoretical_edge=round(1.0 - cost, 4),
                            estimated_fees=round(est_fees, 4),
                            net_edge=round(net_edge, 4),
                            timestamp=datetime.now(timezone.utc),
                            actionable=True,
                            metadata={
                                "leg_a": {"platform": "POLYMARKET", "outcome": "YES", "price": pm.yes_ask, "title": pm.title},
                                "leg_b": {"platform": "KALSHI", "outcome": "NO", "price": km.no_ask, "title": km.title},
                                "similarity": round(sim, 2)
                            }
                        )
                        opportunities.append(opp)

                # Scenario 2: Buy YES on Kalshi, Buy NO on Polymarket
                if km.yes_ask and pm.no_ask:
                    cost = km.yes_ask + pm.no_ask
                    k_fee = FeeCalculator.calculate_kalshi_fee(km.yes_ask, 100, OrderType.MARKET) / 100
                    p_fee = FeeCalculator.calculate_polymarket_fee(pm.no_ask, 100, OrderType.MARKET) / 100
                    est_fees = k_fee + p_fee
                    net_edge = 1.0 - cost - est_fees

                    if net_edge >= settings.MIN_ARB_NET_EDGE:
                        opp = Opportunity(
                            strategy_name=StrategyType.CROSS_MARKET_ARB,
                            description=(
                                f"Cross-Platform Arb: Buy YES on Kalshi (${km.yes_ask:.2f}) + "
                                f"Buy NO on Polymarket (${pm.no_ask:.2f}) on '{km.title[:45]}...'"
                            ),
                            platform_a=Platform.KALSHI,
                            ticker_a=km.ticker,
                            platform_b=Platform.POLYMARKET,
                            ticker_b=pm.ticker,
                            theoretical_edge=round(1.0 - cost, 4),
                            estimated_fees=round(est_fees, 4),
                            net_edge=round(net_edge, 4),
                            timestamp=datetime.now(timezone.utc),
                            actionable=True,
                            metadata={
                                "leg_a": {"platform": "KALSHI", "outcome": "YES", "price": km.yes_ask, "title": km.title},
                                "leg_b": {"platform": "POLYMARKET", "outcome": "NO", "price": pm.no_ask, "title": pm.title},
                                "similarity": round(sim, 2)
                            }
                        )
                        opportunities.append(opp)

        return opportunities

    async def generate_orders(
        self,
        opp: Opportunity,
        balance: AccountBalance
    ) -> List[OrderRequest]:
        """
        Creates synchronized order requests for both legs of the cross-platform arbitrage.
        """
        leg_a = opp.metadata.get("leg_a", {})
        leg_b = opp.metadata.get("leg_b", {})
        if not leg_a or not leg_b:
            return []

        # Target allocation based on net edge
        target_allocation_usd = min(balance.cash_balance * 0.10, settings.MAX_POSITION_SIZE_USD)
        total_pair_cost = leg_a["price"] + leg_b["price"]
        
        if total_pair_cost <= 0:
            return []

        contracts = max(1, int(target_allocation_usd // total_pair_cost))

        order_a = OrderRequest(
            platform=Platform(leg_a["platform"]),
            market_ticker=opp.ticker_a,
            market_title=leg_a.get("title", ""),
            outcome=ContractOutcome(leg_a["outcome"]),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=leg_a["price"],
            quantity=contracts,
            strategy_name=StrategyType.CROSS_MARKET_ARB
        )

        order_b = OrderRequest(
            platform=Platform(leg_b["platform"]),
            market_ticker=opp.ticker_b or "",
            market_title=leg_b.get("title", ""),
            outcome=ContractOutcome(leg_b["outcome"]),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=leg_b["price"],
            quantity=contracts,
            strategy_name=StrategyType.CROSS_MARKET_ARB
        )

        return [order_a, order_b]
