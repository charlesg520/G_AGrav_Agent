from __future__ import annotations

"""Kalshi data feed connector (demo + prod).

This module provides a minimal wrapper around Kalshi's REST Trade API to fetch
market data.  It is intentionally **read-only** – execution / order placement
is out-of-scope for Phase-A; that will be added in later phases.

Environment variables
---------------------
KALSHI_DEMO_KEY_ID
KALSHI_DEMO_KEY_FILE   Path to the PEM file containing the demo private key
KALSHI_API_KEY         (optional) live API key – if present, overrides demo
KALSHI_BASE_URL        Base URL of the API; defaults to the public demo host

The connector prioritises the *live* `KALSHI_API_KEY` when available, falling
back to the demo credentials otherwise.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_BASE_URL = "https://demo-api.kalshi.com"  # Demo environment
LIVE_BASE_URL = "https://trading-api.kalshi.com"  # Production environment


class KalshiError(RuntimeError):
    """Raised when the Kalshi API returns an error response."""


class KalshiFeed:
    def __init__(self, base_url: Optional[str] = None):
        self.api_key = os.getenv("KALSHI_API_KEY")
        self.demo_key_id = os.getenv("KALSHI_DEMO_KEY_ID")
        self.demo_key_file = os.getenv("KALSHI_DEMO_KEY_FILE")
        self.base_url = base_url or os.getenv("KALSHI_BASE_URL", DEFAULT_BASE_URL)

        # Very simple retry-enabled session so that transient network issues
        # don't blow up the feed loop.
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[502, 503, 504])
        self._session.mount("https://", HTTPAdapter(max_retries=retries))

        # If we have a live API key we can include it.  Demo keys require a
        # signed JWT which is more involved; for Phase-A we focus on the public
        # endpoints which don't need auth.
        if self.api_key:
            self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def list_markets(self, status: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """Return a list of markets filtered by status.

        Parameters
        ----------
        status
            One of "open", "closed", … – see Kalshi docs.
        limit
            Max number of markets to return.
        """
        params = {"status": status, "limit": limit}
        url = f"{self.base_url}/trades/markets"
        resp = self._session.get(url, params=params, timeout=5)
        return self._handle_response(resp).get("markets", [])

    def get_market(self, ticker: str) -> Dict[str, Any]:
        """Return details for a single market."""
        url = f"{self.base_url}/trades/markets/{ticker}"
        resp = self._session.get(url, timeout=5)
        return self._handle_response(resp)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_response(self, resp: requests.Response) -> Dict[str, Any]:
        if resp.status_code >= 400:
            raise KalshiError(f"Kalshi API error {resp.status_code}: {resp.text}")
        try:
            return resp.json()
        except Exception as exc:
            raise KalshiError("Invalid JSON from Kalshi API") from exc


kalshi_feed = KalshiFeed()
