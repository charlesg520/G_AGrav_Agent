"""
Polymarket connector for Gamma API (markets & metadata) and CLOB API (order books & depth).
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx

from prediction_agent.config import settings
from prediction_agent.connectors.base import BaseMarketConnector, NormalizedMarket, OrderBook, PriceLevel
from prediction_agent.database.models import Platform

logger = logging.getLogger(__name__)

class PolymarketConnector(BaseMarketConnector):
    def __init__(self, gamma_base: Optional[str] = None, clob_base: Optional[str] = None):
        self.gamma_base = (gamma_base or settings.POLYMARKET_GAMMA_BASE).rstrip("/")
        self.clob_base = (clob_base or settings.POLYMARKET_CLOB_BASE).rstrip("/")
        self.client = httpx.AsyncClient(timeout=12.0)
        self._token_cache: Dict[str, Dict[str, str]] = {} # ticker -> { "YES": token_id, "NO": token_id }

    @property
    def platform(self) -> Platform:
        return Platform.POLYMARKET

    async def close(self):
        await self.client.aclose()

    async def fetch_markets(self, limit: int = 100, active_only: bool = True) -> List[NormalizedMarket]:
        """
        Fetches top markets from Polymarket Gamma API ordered by volume.
        """
        url = f"{self.gamma_base}/markets"
        params = {
            "limit": min(limit, 100),
            "active": "true" if active_only else "false",
            "closed": "false" if active_only else "true",
            "order": "volumeNum",
            "ascending": "false"
        }

        normalized: List[NormalizedMarket] = []
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            markets = resp.json()

            for m in markets:
                m_id = str(m.get("id"))
                question = m.get("question", "")
                vol = float(m.get("volumeNum") or 0.0)

                # Parse outcome prices
                outcome_prices = m.get("outcomePrices")
                yes_price = None
                no_price = None
                if outcome_prices:
                    if isinstance(outcome_prices, str):
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except Exception:
                            outcome_prices = []
                    if len(outcome_prices) >= 2:
                        try:
                            yes_price = float(outcome_prices[0])
                            no_price = float(outcome_prices[1])
                        except Exception:
                            pass

                # Parse token IDs
                tokens = m.get("clobTokenIds")
                tok_list = []
                if tokens:
                    if isinstance(tokens, str):
                        try:
                            tok_list = json.loads(tokens)
                        except Exception:
                            tok_list = []
                    elif isinstance(tokens, list):
                        tok_list = tokens

                if len(tok_list) >= 2:
                    self._token_cache[m_id] = {
                        "YES": tok_list[0],
                        "NO": tok_list[1]
                    }

                # Approximate bids/asks from mid/last if orderbook not queried yet
                yes_bid = round(yes_price - 0.01, 3) if yes_price and yes_price > 0.01 else yes_price
                yes_ask = round(yes_price + 0.01, 3) if yes_price and yes_price < 0.99 else yes_price
                no_bid = round(no_price - 0.01, 3) if no_price and no_price > 0.01 else no_price
                no_ask = round(no_price + 0.01, 3) if no_price and no_price < 0.99 else no_price

                close_time_str = m.get("endDate")
                close_dt = None
                if close_time_str:
                    try:
                        close_dt = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                nm = NormalizedMarket(
                    platform=Platform.POLYMARKET,
                    ticker=m_id,
                    title=question,
                    description=m.get("description", "") or "",
                    category=m.get("category", "general"),
                    close_time=close_dt,
                    yes_bid=yes_bid,
                    yes_ask=yes_ask,
                    no_bid=no_bid,
                    no_ask=no_ask,
                    volume_usd=vol,
                    open_interest=0,
                    raw_data={
                        "conditionId": m.get("conditionId"),
                        "slug": m.get("slug"),
                        "clobTokenIds": tok_list
                    },
                    active=not m.get("closed", False)
                )
                normalized.append(nm)
        except Exception as e:
            logger.error("Failed to fetch Polymarket markets: %s", e)

        return normalized

    async def fetch_market(self, ticker: str) -> Optional[NormalizedMarket]:
        """
        Fetches individual market by ID or slug.
        """
        url = f"{self.gamma_base}/markets/{ticker}"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            m = resp.json()
            if not m:
                return None

            m_id = str(m.get("id", ticker))
            tokens = m.get("clobTokenIds")
            tok_list = []
            if tokens:
                if isinstance(tokens, str):
                    try:
                        tok_list = json.loads(tokens)
                    except Exception:
                        pass
                elif isinstance(tokens, list):
                    tok_list = tokens

            if len(tok_list) >= 2:
                self._token_cache[m_id] = {"YES": tok_list[0], "NO": tok_list[1]}

            return NormalizedMarket(
                platform=Platform.POLYMARKET,
                ticker=m_id,
                title=m.get("question", ""),
                description=m.get("description", "") or "",
                category=m.get("category", "general"),
                volume_usd=float(m.get("volumeNum") or 0.0),
                raw_data={"conditionId": m.get("conditionId"), "clobTokenIds": tok_list},
                active=not m.get("closed", False)
            )
        except Exception as e:
            logger.error("Failed to fetch Polymarket market %s: %s", ticker, e)
            return None

    async def fetch_orderbook(self, ticker: str) -> OrderBook:
        """
        Fetches full L2 order book from Polymarket CLOB.
        """
        book = OrderBook(platform=Platform.POLYMARKET, ticker=ticker)

        # Retrieve token ID from cache or fetch market
        tokens = self._token_cache.get(ticker)
        if not tokens:
            await self.fetch_market(ticker)
            tokens = self._token_cache.get(ticker)

        if not tokens or "YES" not in tokens:
            logger.warning("No CLOB token ID found for Polymarket ticker %s", ticker)
            return book

        yes_token_id = tokens["YES"]
        url = f"{self.clob_base}/book"
        try:
            resp = await self.client.get(url, params={"token_id": yes_token_id})
            if resp.status_code == 200:
                data = resp.json()
                bids = data.get("bids", [])
                asks = data.get("asks", [])

                for b in bids:
                    p = float(b.get("price", 0.0))
                    s = int(float(b.get("size", 0.0)))
                    book.yes_bids.append(PriceLevel(price=p, quantity=s))
                    # Corresponding NO ask
                    no_ask_p = round(1.0 - p, 4)
                    book.no_asks.append(PriceLevel(price=no_ask_p, quantity=s))

                for a in asks:
                    p = float(a.get("price", 0.0))
                    s = int(float(a.get("size", 0.0)))
                    book.yes_asks.append(PriceLevel(price=p, quantity=s))
                    # Corresponding NO bid
                    no_bid_p = round(1.0 - p, 4)
                    book.no_bids.append(PriceLevel(price=no_bid_p, quantity=s))

                book.yes_bids.sort(key=lambda x: x.price, reverse=True)
                book.yes_asks.sort(key=lambda x: x.price, reverse=False)
                book.no_bids.sort(key=lambda x: x.price, reverse=True)
                book.no_asks.sort(key=lambda x: x.price, reverse=False)
        except Exception as e:
            logger.error("Failed to fetch Polymarket CLOB orderbook for %s: %s", ticker, e)

        return book
