"""
Fee calculations modeling actual exchange fee structures for Kalshi and Polymarket.
"""

from prediction_agent.database.models import Platform, OrderSide, OrderType

class FeeCalculator:
    @staticmethod
    def calculate_kalshi_fee(price: float, quantity: int, order_type: OrderType = OrderType.MARKET) -> float:
        """
        Kalshi charges a variable fee per contract based on probability.
        Roughly: fee_per_contract = min(0.02, max(0.005, 0.07 * price * (1.0 - price)))
        Maker orders receive discounted or zero fees on select promotions.
        """
        # Binary option variance curve: highest at 50 cents (0.50 * 0.50 = 0.25)
        p = max(0.01, min(0.99, price))
        base_rate = 0.07 * p * (1.0 - p)
        fee_per_contract = min(0.02, max(0.002, base_rate))
        
        if order_type == OrderType.LIMIT:
            # Maker discount (approx 50% discount)
            fee_per_contract *= 0.5
            
        total_fee = fee_per_contract * quantity
        return round(total_fee, 4)

    @staticmethod
    def calculate_polymarket_fee(price: float, quantity: int, order_type: OrderType = OrderType.MARKET) -> float:
        """
        Polymarket CLOB charges 0% maker and 0% taker fees on most standard prediction markets.
        A nominal 0.1% or gas proxy can be included for hyper-realistic simulation.
        """
        # Nominal friction buffer: 0.05% of notional
        notional = price * quantity
        nominal_friction = notional * 0.0005
        return round(nominal_friction, 4)

    @classmethod
    def calculate_fee(cls, platform: Platform, price: float, quantity: int, order_type: OrderType = OrderType.MARKET) -> float:
        if platform == Platform.KALSHI:
            return cls.calculate_kalshi_fee(price, quantity, order_type)
        elif platform == Platform.POLYMARKET:
            return cls.calculate_polymarket_fee(price, quantity, order_type)
        return 0.0
