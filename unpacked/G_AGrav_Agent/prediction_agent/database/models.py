"""
Data models and schemas for prediction market paper trading, analytics, and chat memory.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Platform(str, Enum):
    KALSHI = "KALSHI"
    POLYMARKET = "POLYMARKET"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class ContractOutcome(str, Enum):
    YES = "YES"
    NO = "NO"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class StrategyType(str, Enum):
    CROSS_MARKET_ARB = "CROSS_MARKET_ARB"
    DUTCH_BOOK = "DUTCH_BOOK"
    MARKET_MAKING = "MARKET_MAKING"
    RESOLUTION_SNIPING = "RESOLUTION_SNIPING"
    MODEL_FAIR_VALUE = "MODEL_FAIR_VALUE"
    MANUAL = "MANUAL"

class Position(BaseModel):
    id: Optional[int] = None
    platform: Platform
    market_ticker: str
    market_title: str
    outcome: ContractOutcome
    quantity: int
    avg_entry_price: float  # Price in dollars (0.01 - 0.99)
    current_price: float
    unrealized_pnl: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderRequest(BaseModel):
    platform: Platform
    market_ticker: str
    market_title: str = ""
    outcome: ContractOutcome
    side: OrderSide
    order_type: OrderType
    price: float  # Target price (or limit price)
    quantity: int
    strategy_name: StrategyType = StrategyType.MANUAL

class Order(BaseModel):
    id: str
    platform: Platform
    market_ticker: str
    market_title: str
    outcome: ContractOutcome
    side: OrderSide
    order_type: OrderType
    price: float
    quantity: int
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.PENDING
    strategy_name: StrategyType = StrategyType.MANUAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None

class Trade(BaseModel):
    id: str
    order_id: str
    platform: Platform
    market_ticker: str
    market_title: str
    outcome: ContractOutcome
    side: OrderSide
    price: float
    quantity: int
    fee_paid: float
    slippage: float = 0.0
    realized_pnl: float = 0.0
    strategy_name: StrategyType = StrategyType.MANUAL
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AccountBalance(BaseModel):
    cash_balance: float
    invested_capital: float
    total_equity: float
    unrealized_pnl: float
    realized_pnl: float
    total_fees_paid: float
    open_positions_count: int

class PortfolioSnapshot(BaseModel):
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cash_balance: float
    invested_capital: float
    total_equity: float
    unrealized_pnl: float
    realized_pnl: float

class Opportunity(BaseModel):
    strategy_name: StrategyType
    description: str
    platform_a: Platform
    ticker_a: str
    platform_b: Optional[Platform] = None
    ticker_b: Optional[str] = None
    theoretical_edge: float  # e.g., 0.035 for 3.5% edge
    estimated_fees: float
    net_edge: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actionable: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatMessageModel(BaseModel):
    id: Optional[int] = None
    session_id: str
    role: str  # "user", "assistant", "system"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[Dict[str, Any]] = None

class ChatSessionModel(BaseModel):
    id: str
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
