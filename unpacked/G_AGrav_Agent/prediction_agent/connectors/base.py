"""
Base schemas and abstract interface for prediction market data connectors.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from prediction_agent.database.models import Platform

class PriceLevel(BaseModel):
    price: float   # In dollars, e.g. 0.54
    quantity: int  # Number of contracts available

class OrderBook(BaseModel):
    platform: Platform
    ticker: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    yes_bids: List[PriceLevel] = Field(default_factory=list) # Best (highest) bids first
    yes_asks: List[PriceLevel] = Field(default_factory=list) # Best (lowest) asks first
    no_bids: List[PriceLevel] = Field(default_factory=list)
    no_asks: List[PriceLevel] = Field(default_factory=list)

class NormalizedMarket(BaseModel):
    platform: Platform
    ticker: str
    title: str
    description: str = ""
    category: str = "general"
    close_time: Optional[datetime] = None
    yes_bid: Optional[float] = None
    yes_ask: Optional[float] = None
    no_bid: Optional[float] = None
    no_ask: Optional[float] = None
    volume_usd: float = 0.0
    open_interest: int = 0
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True

class BaseMarketConnector(ABC):
    @property
    @abstractmethod
    def platform(self) -> Platform:
        pass

    @abstractmethod
    async def fetch_markets(self, limit: int = 100, active_only: bool = True) -> List[NormalizedMarket]:
        pass

    @abstractmethod
    async def fetch_market(self, ticker: str) -> Optional[NormalizedMarket]:
        pass

    @abstractmethod
    async def fetch_orderbook(self, ticker: str) -> OrderBook:
        pass
