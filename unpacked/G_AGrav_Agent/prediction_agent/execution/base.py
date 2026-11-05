"""
Abstract broker interface ensuring seamless switching between Paper Trading and Live API execution.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from prediction_agent.database.models import (
    OrderRequest, Order, Position, AccountBalance
)

class BaseBroker(ABC):
    @abstractmethod
    async def get_balance(self) -> AccountBalance:
        """Retrieves account balance, invested equity, and total portfolio value."""
        pass

    @abstractmethod
    async def submit_order(self, order_request: OrderRequest) -> Order:
        """Submits an order for execution."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancels an open order."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Returns all open positions."""
        pass

    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """Returns all pending/open orders."""
        pass
