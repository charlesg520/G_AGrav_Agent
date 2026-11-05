from __future__ import annotations

"""Migrate legacy JSON portfolio_db.json into the new SQLite database.

Run once after upgrading to Phase-A:

    python -m scripts.migrate_portfolio

It reads `backend/execution/portfolio_db.json` (if present) and persists the
state via the new `backend.storage` layer.  Existing rows in the SQLite
database are wiped before import.  The JSON file is left untouched so that the
migration script is idempotent.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path when executed with `python -m`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage import storage  # noqa: E402

LEGACY_PATH = PROJECT_ROOT / "backend" / "execution" / "portfolio_db.json"


def migrate() -> None:
    if not LEGACY_PATH.exists():
        print("No legacy portfolio_db.json found. Nothing to migrate.")
        return

    print(f"Loading legacy portfolio from {LEGACY_PATH} …")
    with LEGACY_PATH.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    storage.save_portfolio(
        cash_balance=data.get("cash_balance", 0.0),
        portfolio_value=data.get("portfolio_value", 0.0),
        realized_pnl=data.get("realized_pnl", 0.0),
        positions=data.get("positions", {}),
        trade_history=data.get("trade_history", []),
    )
    print("Migration complete. Portfolio persisted to SQLite database.")


if __name__ == "__main__":
    migrate()
