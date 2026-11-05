"""
Database connection, schema migration, and async CRUD operations.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
import aiosqlite

from prediction_agent.config import settings
from prediction_agent.database.models import (
    Position, Order, Trade, AccountBalance, PortfolioSnapshot,
    Opportunity, ChatMessageModel, ChatSessionModel,
    Platform, OrderSide, OrderType, ContractOutcome, OrderStatus, StrategyType
)

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cash_balance REAL NOT NULL,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    total_fees_paid REAL NOT NULL DEFAULT 0.0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    market_title TEXT NOT NULL,
    outcome TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    avg_entry_price REAL NOT NULL,
    current_price REAL NOT NULL,
    unrealized_pnl REAL NOT NULL DEFAULT 0.0,
    updated_at TEXT NOT NULL,
    UNIQUE(platform, market_ticker, outcome)
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    market_title TEXT NOT NULL,
    outcome TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    filled_quantity INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    filled_at TEXT
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    market_ticker TEXT NOT NULL,
    market_title TEXT NOT NULL,
    outcome TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    fee_paid REAL NOT NULL,
    slippage REAL NOT NULL DEFAULT 0.0,
    realized_pnl REAL NOT NULL DEFAULT 0.0,
    strategy_name TEXT NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    cash_balance REAL NOT NULL,
    invested_capital REAL NOT NULL,
    total_equity REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    realized_pnl REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    description TEXT NOT NULL,
    platform_a TEXT NOT NULL,
    ticker_a TEXT NOT NULL,
    platform_b TEXT,
    ticker_b TEXT,
    theoretical_edge REAL NOT NULL,
    estimated_fees REAL NOT NULL,
    net_edge REAL NOT NULL,
    actionable INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);
"""

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or settings.DB_PATH)

    async def init_db(self):
        """Initializes database tables and default account balance if not exists."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(CREATE_TABLES_SQL)
            
            # Initialize account if not present
            cursor = await db.execute("SELECT id FROM account WHERE id = 1")
            row = await cursor.fetchone()
            if not row:
                now_iso = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    """
                    INSERT INTO account (id, cash_balance, realized_pnl, total_fees_paid, updated_at)
                    VALUES (1, ?, 0.0, 0.0, ?)
                    """,
                    (settings.INITIAL_PAPER_BALANCE, now_iso)
                )
            await db.commit()
            logger.info("Database initialized successfully at %s", self.db_path)

    # ------------------ Account & Ledger ------------------ #

    async def get_account_balance(self) -> AccountBalance:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM account WHERE id = 1")
            acc = await cursor.fetchone()
            if not acc:
                return AccountBalance(
                    cash_balance=settings.INITIAL_PAPER_BALANCE,
                    invested_capital=0.0,
                    total_equity=settings.INITIAL_PAPER_BALANCE,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    total_fees_paid=0.0,
                    open_positions_count=0
                )

            # Calculate invested capital and unrealized pnl from open positions
            p_cursor = await db.execute("SELECT quantity, avg_entry_price, current_price FROM positions WHERE quantity > 0")
            positions = await p_cursor.fetchall()
            
            invested_capital = 0.0
            unrealized_pnl = 0.0
            for p in positions:
                invested = p["quantity"] * p["avg_entry_price"]
                current_val = p["quantity"] * p["current_price"]
                invested_capital += invested
                unrealized_pnl += (current_val - invested)

            total_equity = acc["cash_balance"] + invested_capital + unrealized_pnl

            return AccountBalance(
                cash_balance=acc["cash_balance"],
                invested_capital=invested_capital,
                total_equity=total_equity,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=acc["realized_pnl"],
                total_fees_paid=acc["total_fees_paid"],
                open_positions_count=len(positions)
            )

    async def update_account_balance(self, cash_delta: float, realized_pnl_delta: float, fee_delta: float):
        async with aiosqlite.connect(self.db_path) as db:
            now_iso = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """
                UPDATE account
                SET cash_balance = cash_balance + ?,
                    realized_pnl = realized_pnl + ?,
                    total_fees_paid = total_fees_paid + ?,
                    updated_at = ?
                WHERE id = 1
                """,
                (cash_delta, realized_pnl_delta, fee_delta, now_iso)
            )
            await db.commit()

    async def record_portfolio_snapshot(self, snapshot: PortfolioSnapshot):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO portfolio_snapshots (timestamp, cash_balance, invested_capital, total_equity, unrealized_pnl, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.timestamp.isoformat(),
                    snapshot.cash_balance,
                    snapshot.invested_capital,
                    snapshot.total_equity,
                    snapshot.unrealized_pnl,
                    snapshot.realized_pnl
                )
            )
            await db.commit()

    async def get_portfolio_history(self, limit: int = 500) -> List[PortfolioSnapshot]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [
                PortfolioSnapshot(
                    id=r["id"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    cash_balance=r["cash_balance"],
                    invested_capital=r["invested_capital"],
                    total_equity=r["total_equity"],
                    unrealized_pnl=r["unrealized_pnl"],
                    realized_pnl=r["realized_pnl"]
                ) for r in reversed(rows)
            ]

    # ------------------ Positions ------------------ #

    async def get_positions(self) -> List[Position]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM positions WHERE quantity > 0")
            rows = await cursor.fetchall()
            return [
                Position(
                    id=r["id"],
                    platform=Platform(r["platform"]),
                    market_ticker=r["market_ticker"],
                    market_title=r["market_title"],
                    outcome=ContractOutcome(r["outcome"]),
                    quantity=r["quantity"],
                    avg_entry_price=r["avg_entry_price"],
                    current_price=r["current_price"],
                    unrealized_pnl=r["unrealized_pnl"],
                    updated_at=datetime.fromisoformat(r["updated_at"])
                ) for r in rows
            ]

    async def get_position(self, platform: Platform, ticker: str, outcome: ContractOutcome) -> Optional[Position]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM positions WHERE platform = ? AND market_ticker = ? AND outcome = ?",
                (platform.value, ticker, outcome.value)
            )
            r = await cursor.fetchone()
            if not r:
                return None
            return Position(
                id=r["id"],
                platform=Platform(r["platform"]),
                market_ticker=r["market_ticker"],
                market_title=r["market_title"],
                outcome=ContractOutcome(r["outcome"]),
                quantity=r["quantity"],
                avg_entry_price=r["avg_entry_price"],
                current_price=r["current_price"],
                unrealized_pnl=r["unrealized_pnl"],
                updated_at=datetime.fromisoformat(r["updated_at"])
            )

    async def upsert_position(self, pos: Position):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO positions (platform, market_ticker, market_title, outcome, quantity, avg_entry_price, current_price, unrealized_pnl, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, market_ticker, outcome) DO UPDATE SET
                    quantity = excluded.quantity,
                    avg_entry_price = excluded.avg_entry_price,
                    current_price = excluded.current_price,
                    unrealized_pnl = excluded.unrealized_pnl,
                    updated_at = excluded.updated_at
                """,
                (
                    pos.platform.value,
                    pos.market_ticker,
                    pos.market_title,
                    pos.outcome.value,
                    pos.quantity,
                    pos.avg_entry_price,
                    pos.current_price,
                    pos.unrealized_pnl,
                    pos.updated_at.isoformat()
                )
            )
            await db.commit()

    # ------------------ Orders & Trades ------------------ #

    async def insert_order(self, order: Order):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO orders (id, platform, market_ticker, market_title, outcome, side, order_type, price, quantity, filled_quantity, status, strategy_name, created_at, filled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.id,
                    order.platform.value,
                    order.market_ticker,
                    order.market_title,
                    order.outcome.value,
                    order.side.value,
                    order.order_type.value,
                    order.price,
                    order.quantity,
                    order.filled_quantity,
                    order.status.value,
                    order.strategy_name.value,
                    order.created_at.isoformat(),
                    order.filled_at.isoformat() if order.filled_at else None
                )
            )
            await db.commit()

    async def update_order_status(self, order_id: str, status: OrderStatus, filled_quantity: int, filled_at: Optional[datetime] = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE orders
                SET status = ?, filled_quantity = ?, filled_at = ?
                WHERE id = ?
                """,
                (status.value, filled_quantity, filled_at.isoformat() if filled_at else None, order_id)
            )
            await db.commit()

    async def insert_trade(self, trade: Trade):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO trades (id, order_id, platform, market_ticker, market_title, outcome, side, price, quantity, fee_paid, slippage, realized_pnl, strategy_name, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.id,
                    trade.order_id,
                    trade.platform.value,
                    trade.market_ticker,
                    trade.market_title,
                    trade.outcome.value,
                    trade.side.value,
                    trade.price,
                    trade.quantity,
                    trade.fee_paid,
                    trade.slippage,
                    trade.realized_pnl,
                    trade.strategy_name.value,
                    trade.executed_at.isoformat()
                )
            )
            await db.commit()

    async def get_trades(self, limit: int = 100) -> List[Trade]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM trades ORDER BY executed_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [
                Trade(
                    id=r["id"],
                    order_id=r["order_id"],
                    platform=Platform(r["platform"]),
                    market_ticker=r["market_ticker"],
                    market_title=r["market_title"],
                    outcome=ContractOutcome(r["outcome"]),
                    side=OrderSide(r["side"]),
                    price=r["price"],
                    quantity=r["quantity"],
                    fee_paid=r["fee_paid"],
                    slippage=r["slippage"],
                    realized_pnl=r["realized_pnl"],
                    strategy_name=StrategyType(r["strategy_name"]),
                    executed_at=datetime.fromisoformat(r["executed_at"])
                ) for r in rows
            ]

    # ------------------ Opportunities ------------------ #

    async def log_opportunity(self, opp: Opportunity):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO opportunities (timestamp, strategy_name, description, platform_a, ticker_a, platform_b, ticker_b, theoretical_edge, estimated_fees, net_edge, actionable, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opp.timestamp.isoformat(),
                    opp.strategy_name.value,
                    opp.description,
                    opp.platform_a.value,
                    opp.ticker_a,
                    opp.platform_b.value if opp.platform_b else None,
                    opp.ticker_b,
                    opp.theoretical_edge,
                    opp.estimated_fees,
                    opp.net_edge,
                    1 if opp.actionable else 0,
                    json.dumps(opp.metadata)
                )
            )
            await db.commit()

    async def get_recent_opportunities(self, limit: int = 50) -> List[Opportunity]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM opportunities ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [
                Opportunity(
                    strategy_name=StrategyType(r["strategy_name"]),
                    description=r["description"],
                    platform_a=Platform(r["platform_a"]),
                    ticker_a=r["ticker_a"],
                    platform_b=Platform(r["platform_b"]) if r["platform_b"] else None,
                    ticker_b=r["ticker_b"],
                    theoretical_edge=r["theoretical_edge"],
                    estimated_fees=r["estimated_fees"],
                    net_edge=r["net_edge"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    actionable=bool(r["actionable"]),
                    metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {}
                ) for r in rows
            ]

    # ------------------ Persistent Chat Memory ------------------ #

    async def get_or_create_chat_session(self, session_id: str, title: str = "New Session") -> ChatSessionModel:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            now = datetime.now(timezone.utc)
            if not row:
                await db.execute(
                    "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (session_id, title, now.isoformat(), now.isoformat())
                )
                await db.commit()
                return ChatSessionModel(id=session_id, title=title, created_at=now, updated_at=now)
            return ChatSessionModel(
                id=row["id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )

    async def list_chat_sessions(self, limit: int = 30) -> List[ChatSessionModel]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            return [
                ChatSessionModel(
                    id=r["id"],
                    title=r["title"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"])
                ) for r in rows
            ]

    async def add_chat_message(self, message: ChatMessageModel):
        async with aiosqlite.connect(self.db_path) as db:
            now_iso = message.created_at.isoformat()
            await db.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.session_id,
                    message.role,
                    message.content,
                    json.dumps(message.metadata) if message.metadata else None,
                    now_iso
                )
            )
            # Update session's updated_at timestamp
            await db.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_iso, message.session_id))
            await db.commit()

    async def get_chat_messages(self, session_id: str, limit: int = 100) -> List[ChatMessageModel]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                (session_id, limit)
            )
            rows = await cursor.fetchall()
            return [
                ChatMessageModel(
                    id=r["id"],
                    session_id=r["session_id"],
                    role=r["role"],
                    content=r["content"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else None
                ) for r in rows
            ]

# Global DB singleton
db = Database()
