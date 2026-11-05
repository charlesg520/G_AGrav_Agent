"""
Kalshi API v2 connector for market data, pricing, and orderbook depth.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from prediction_agent.config import settings
from prediction_agent.connectors.base import BaseMarketConnector, NormalizedMarket, OrderBook, PriceLevel
from prediction_agent.database.models import Platform

logger = logging.getLogger(__name__)

class KalshiConnector(BaseMarketConnector):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.KALSHI_API_BASE).rstrip("/")
        self.client = httpx.AsyncClient(timeout=12.0)

    @property
    def platform(self) -> Platform:
        return Platform.KALSHI

    async def close(self):
        await self.client.aclose()

    async def fetch_markets(self, limit: int = 100, active_only: bool = True) -> List[NormalizedMarket]:
        """
        Fetches open events and nested markets from Kalshi v2 public API.
        """
        url = f"{self.base_url}/events"
        params = {
            "status": "open",
            "with_nested_markets": "true",
            "limit": min(limit, 100)
        }
        
        normalized: List[NormalizedMarket] = []
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("events", [])

            for ev in events:
                category = ev.get("category", "general")
                event_title = ev.get("title", "")
                markets = ev.get("markets", [])

                for m in markets:
                    ticker = m.get("ticker", "")
                    title = m.get("title") or event_title
                    yes_bid = float(m.get("yes_bid_dollars") or 0.0)
                    yes_ask = float(m.get("yes_ask_dollars") or 0.0)
                    no_bid = float(m.get("no_bid_dollars") or 0.0)
                    no_ask = float(m.get("no_ask_dollars") or 0.0)
                    vol = float(m.get("volume_fp") or 0.0)
                    oi = int(float(m.get("open_interest_fp") or 0.0))

                    if active_only and yes_bid <= 0.0 and yes_ask <= 0.0 and vol <= 0.0:
                        continue

                    close_time_str = m.get("close_time") or m.get("expiration_time")
                    close_dt = None
                    if close_time_str:
                        try:
                            close_dt = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                        except Exception:
                            pass

                    # If no_bid or no_ask wasn't populated explicitly, infer from yes
                    if no_bid <= 0.0 and yes_ask > 0.0:
                        no_bid = round(1.0 - yes_ask, 4)
                    if no_ask <= 0.0 and yes_bid > 0.0:
                        no_ask = round(1.0 - yes_bid, 4)

                    nm = NormalizedMarket(
                        platform=Platform.KALSHI,
                        ticker=ticker,
                        title=title,
                        description=m.get("rules_primary", ""),
                        category=category,
                        close_time=close_dt,
                        yes_bid=yes_bid if yes_bid > 0 else None,
                        yes_ask=yes_ask if yes_ask > 0 else None,
                        no_bid=no_bid if no_bid > 0 else None,
                        no_ask=no_ask if no_ask > 0 else None,
                        volume_usd=vol,
                        open_interest=oi,
                        raw_data={"event_ticker": ev.get("event_ticker"), "series_ticker": ev.get("series_ticker")},
                        active=(m.get("status") == "open")
                    )
                    normalized.append(nm)
        except Exception as e:
            logger.error("Failed to fetch Kalshi markets: %s", e)

        return normalized

    async def fetch_market(self, ticker: str) -> Optional[NormalizedMarket]:
        """
        Fetches individual market by ticker.
        """
        url = f"{self.base_url}/markets/{ticker}"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            m = resp.json().get("market", {})
            if not m:
                return None
            
            yes_bid = float(m.get("yes_bid_dollars") or 0.0)
            yes_ask = float(m.get("yes_ask_dollars") or 0.0)
            no_bid = float(m.get("no_bid_dollars") or 0.0)
            no_ask = float(m.get("no_ask_dollars") or 0.0)
            
            return NormalizedMarket(
                platform=Platform.KALSHI,
                ticker=m.get("ticker", ticker),
                title=m.get("title", ""),
                description=m.get("rules_primary", ""),
                category=m.get("category", "general"),
                yes_bid=yes_bid if yes_bid > 0 else None,
                yes_ask=yes_ask if yes_ask > 0 else None,
                no_bid=no_bid if no_bid > 0 else None,
                no_ask=no_ask if no_ask > 0 else None,
                volume_usd=float(m.get("volume_fp") or 0.0),
                open_interest=int(float(m.get("open_interest_fp") or 0.0)),
                active=(m.get("status") == "open")
            )
        except Exception as e:
            logger.error("Failed to fetch Kalshi market %s: %s", ticker, e)
            return None

    async def fetch_orderbook(self, ticker: str) -> OrderBook:
        """
        Fetches full L2 order book for ticker.
        """
        url = f"{self.base_url}/markets/{ticker}/orderbook"
        book = OrderBook(platform=Platform.KALSHI, ticker=ticker)
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            ob = data.get("orderbook_fp") or data.get("orderbook") or {}

            # Parse yes_dollars
            yes_levels = ob.get("yes_dollars", [])
            for lvl in yes_levels:
                price = float(lvl[0])
                qty = int(float(lvl[1]))
                book.yes_bids.append(PriceLevel(price=price, quantity=qty))
            # Sort yes_bids descending (highest bid first)
            book.yes_bids.sort(key=lambda x: x.price, reverse=True)

            # Parse no_dollars (in Kalshi, no_dollars bid at P implies yes_ask at 1.0 - P)
            no_levels = ob.get("no_dollars", [])
            for lvl in no_levels:
                price = float(lvl[0])
                qty = int(float(lvl[1]))
                book.no_bids.append(PriceLevel(price=price, quantity=qty))
                # Corresponding YES ask
                yes_ask_price = round(1.0 - price, 4)
                book.yes_asks.append(PriceLevel(price=yes_ask_price, quantity=qty))

            book.no_bids.sort(key=lambda x: x.price, reverse=True)
            book.yes_asks.sort(key=lambda x: x.price, reverse=False) # lowest ask first

            # Infer NO asks from YES bids
            for yb in book.yes_bids:
                no_ask_price = round(1.0 - yb.price, 4)
                book.no_asks.append(PriceLevel(price=no_ask_price, quantity=yb.quantity))
            book.no_asks.sort(key=lambda x: x.price, reverse=False)

        except Exception as e:
            logger.error("Failed to fetch Kalshi orderbook for %s: %s", ticker, e)

        return book
