from __future__ import annotations

"""SQLite persistence layer backed by SQLModel.

This module provides a **very** small abstraction around a SQLite database to
persist the agent's portfolio state (cash balance, positions, trades, etc.).
It replaces the previous `portfolio_db.json` flat-file.

It is intentionally simple – no fancy repositories or Unit of Work patterns –
just a couple of helper functions that the rest of the codebase can call.

Tables
------
Config
    Single-row table that stores global portfolio metrics such as balances and
    realised PnL.
Position
    Open positions stored as a JSON blob keyed by the asset symbol.  We keep a
    JSON column so that the existing in-memory structure can be stored without
    a dedicated schema migration tool.
Trade
    Executed trades stored as a JSON blob.  We keep them in the same order the
    OMS supplies.
MarketTick (future)
    Stub – currently unused.  Added so that we have a place ready for market
    data snapshots when we need them.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlmodel import Field, Session, SQLModel, create_engine, select

# -----------------------------------------------------------------------------
# Paths / engine
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "portfolio.sqlite"

# Use check_same_thread=False so that we can share the connection across async
# contexts if needed in the future.
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class ConfigModel(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    cash_balance: float = 0.0
    portfolio_value: float = 0.0
    realized_pnl: float = 0.0


class PositionModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asset: str
    # Keep the full position dict serialised to preserve fields without schema
    # churn at this stage of the project.
    data_json: str


class TradeModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: str
    data_json: str


class MarketTickModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    symbol: str
    timestamp: str  # ISO-8601
    price: float


# Ensure tables exist at import time – cheap for SQLite.
SQLModel.metadata.create_all(engine)

# -----------------------------------------------------------------------------
# Storage helpers (public API)
# -----------------------------------------------------------------------------


def save_portfolio(
    *,
    cash_balance: float,
    portfolio_value: float,
    realized_pnl: float,
    positions: Dict[str, Dict[str, Any]],
    trade_history: List[Dict[str, Any]],
) -> None:
    """Persist the complete portfolio snapshot atomically.

    The function *replaces* existing data – positions and trades are fully
    deleted before inserting the new snapshot.  This keeps the logic simple and
    mirrors the behaviour of the previous JSON file which always contained the
    full latest state.
    """

    with Session(engine) as session:
        # Upsert config (single-row)
        cfg = session.get(ConfigModel, 1) or ConfigModel()
        cfg.cash_balance = cash_balance
        cfg.portfolio_value = portfolio_value
        cfg.realized_pnl = realized_pnl
        session.add(cfg)

        from sqlalchemy import delete  # Imported here to avoid heavy import at module load

        # Replace positions
        session.exec(delete(PositionModel))
        session.commit()
        for asset, pdata in positions.items():
            session.add(PositionModel(asset=asset, data_json=json.dumps(pdata, ensure_ascii=False)))

        # Replace trade history (keep max 100 like old code)
        session.exec(delete(TradeModel))
        session.commit()
        for trade in trade_history[:100]:
            session.add(
                TradeModel(
                    order_id=trade.get("order_id", "UNKNOWN"),
                    data_json=json.dumps(trade, ensure_ascii=False),
                )
            )

        session.commit()


def load_portfolio() -> Tuple[float, float, float, Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Load the latest portfolio snapshot.

    Returns
    -------
    cash_balance, portfolio_value, realized_pnl, positions, trade_history
    """

    with Session(engine) as session:
        cfg = session.get(ConfigModel, 1)
        if cfg is None:
            # No DB yet – return defaults so the rest of the app boots with a
            # clean slate.
            return 100_000.0, 100_000.0, 0.0, {}, []

        positions: Dict[str, Dict[str, Any]] = {}
        for row in session.exec(select(PositionModel)):
            try:
                positions[row.asset] = json.loads(row.data_json)
            except Exception:
                # Corrupt row – skip so we don't crash the whole load.
                continue

        trades: List[Dict[str, Any]] = []
        for row in session.exec(select(TradeModel).order_by(TradeModel.id.desc())):
            try:
                trades.append(json.loads(row.data_json))
            except Exception:
                continue

        return cfg.cash_balance, cfg.portfolio_value, cfg.realized_pnl, positions, trades


# -----------------------------------------------------------------------------
# Convenience singleton
# -----------------------------------------------------------------------------

class _StorageFacade:
    """Thin façade so that callers can do `from backend.storage import storage`."""

    def save_portfolio(self, **kwargs):  # type: ignore[override]
        save_portfolio(**kwargs)

    def load_portfolio(self):  # type: ignore[override]
        return load_portfolio()


storage = _StorageFacade()
