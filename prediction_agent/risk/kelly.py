"""
Binary Option Fractional Kelly Criterion Sizing Engine.
"""

from typing import Tuple

class KellyEngine:
    @staticmethod
    def calculate_kelly_fraction(
        estimated_prob: float,
        market_price: float,
        kelly_scale: float = 0.25
    ) -> float:
        """
        Computes the fractional Kelly allocation for a binary contract.
        
        Parameters:
        - estimated_prob (p): Assessed true probability (0.0 to 1.0)
        - market_price (c): Cost per contract (0.01 to 0.99)
        - kelly_scale: Multiplier (default 0.25 for Quarter-Kelly)
        
        Returns:
        - fraction: Optimal percentage of portfolio capital to allocate (0.0 to 1.0)
        """
        p = max(0.001, min(0.999, estimated_prob))
        c = max(0.001, min(0.999, market_price))

        # If market price >= estimated probability, there is zero or negative edge
        if p <= c:
            return 0.0

        # For binary contracts paying $1.00:
        # Full Kelly f* = (p - c) / (1 - c)
        full_kelly = (p - c) / (1.0 - c)
        
        # Apply fractional multiplier (Half-Kelly, Quarter-Kelly, etc.)
        fractional_kelly = full_kelly * kelly_scale

        # Bound allocation between 0% and 20% max per individual bet to prevent ruin
        return max(0.0, min(0.20, fractional_kelly))

    @classmethod
    def calculate_position_size(
        cls,
        portfolio_equity: float,
        estimated_prob: float,
        market_price: float,
        max_usd_cap: float = 500.0,
        kelly_scale: float = 0.25
    ) -> Tuple[int, float, float]:
        """
        Calculates optimal contracts to buy and total USD committed.
        
        Returns:
        - (contracts_to_buy, total_cost_usd, kelly_fraction_used)
        """
        if market_price <= 0.0 or market_price >= 1.0:
            return 0, 0.0, 0.0

        k_frac = cls.calculate_kelly_fraction(estimated_prob, market_price, kelly_scale)
        if k_frac <= 0.0:
            return 0, 0.0, 0.0

        target_usd = portfolio_equity * k_frac
        capped_usd = min(target_usd, max_usd_cap)

        contracts = int(capped_usd // market_price)
        total_cost = round(contracts * market_price, 2)

        return contracts, total_cost, round(k_frac, 4)
