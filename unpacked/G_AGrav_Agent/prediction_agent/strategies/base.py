"""
Base strategy class and opportunity execution generator.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from prediction_agent.database.models import (
    Opportunity, OrderRequest, StrategyType, AccountBalance
)
from prediction_agent.connectors.base import NormalizedMarket

class BaseStrategy(ABC):
    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        pass

    @abstractmethod
    async def scan(
        self,
        kalshi_markets: List[NormalizedMarket],
        polymarket_markets: List[NormalizedMarket]
    ) -> List[Opportunity]:
        """Scans for market discrepancies and yields actionable opportunities."""
        pass

    @abstractmethod
    async def generate_orders(
        self,
        opp: Opportunity,
        balance: AccountBalance
    ) -> List[OrderRequest]:
        """Converts an opportunity into concrete order requests respecting risk rules."""
        pass
