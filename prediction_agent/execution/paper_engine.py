"""
High-fidelity Paper Execution Engine.
Matches orders against real-time L2 order book depth, calculates realistic slippage,
deducts exchange fees, updates positions, and persists all trades to the SQLite ledger.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict
import asyncio

from prediction_agent.config import settings
from prediction_agent.database.models import (
    OrderRequest, Order, Trade, Position, AccountBalance,
    Platform, OrderSide, OrderType, ContractOutcome, OrderStatus, StrategyType
)
from prediction_agent.database.db import db
from prediction_agent.execution.base import BaseBroker
from prediction_agent.execution.fee_calculator import FeeCalculator
from prediction_agent.connectors.kalshi import KalshiConnector
from prediction_agent.connectors.polymarket import PolymarketConnector
from prediction_agent.connectors.base import OrderBook, PriceLevel

logger = logging.getLogger(__name__)

class PaperExecutionEngine(BaseBroker):
    def __init__(
        self,
        kalshi_connector: Optional[KalshiConnector] = None,
        polymarket_connector: Optional[PolymarketConnector] = None
    ):
        self.kalshi = kalshi_connector or KalshiConnector()
        self.polymarket = polymarket_connector or PolymarketConnector()
        self._open_orders: Dict[str, Order] = {}

    async def get_balance(self) -> AccountBalance:
        return await db.get_account_balance()

    async def get_positions(self) -> List[Position]:
        return await db.get_positions()

    async def get_open_orders(self) -> List[Order]:
        return list(self._open_orders.values())

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self._open_orders:
            order = self._open_orders.pop(order_id)
            order.status = OrderStatus.CANCELLED
            await db.update_order_status(order_id, OrderStatus.CANCELLED, order.filled_quantity)
            logger.info("Cancelled paper order %s", order_id)
            return True
        return False

    async def submit_order(self, req: OrderRequest) -> Order:
        """
        Processes and executes order request with realistic orderbook matching.
        """
        order_id = f"ord_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        
        order = Order(
            id=order_id,
            platform=req.platform,
            market_ticker=req.market_ticker,
            market_title=req.market_title or req.market_ticker,
            outcome=req.outcome,
            side=req.side,
            order_type=req.order_type,
            price=req.price,
            quantity=req.quantity,
            filled_quantity=0,
            status=OrderStatus.PENDING,
            strategy_name=req.strategy_name,
            created_at=now
        )
        await db.insert_order(order)

        # Retrieve live order book depth
        orderbook = await self._fetch_live_book(req.platform, req.market_ticker)
        
        # Match order against live orderbook
        executed_price, filled_qty, slippage = self._match_against_book(
            orderbook=orderbook,
            outcome=req.outcome,
            side=req.side,
            order_type=req.order_type,
            target_price=req.price,
            target_qty=req.quantity
        )

        if filled_qty == 0:
            if req.order_type == OrderType.LIMIT:
                # Store pending limit order
                self._open_orders[order_id] = order
                logger.info("Placed paper limit order %s at %.3f for qty %d", order_id, req.price, req.quantity)
                return order
            else:
                # If market order had no book, fall back to target price
                executed_price = req.price
                filled_qty = req.quantity
                slippage = 0.0

        # Calculate fees
        fee = FeeCalculator.calculate_fee(req.platform, executed_price, filled_qty, req.order_type)
        notional_cost = executed_price * filled_qty

        # Check cash balance for BUY orders
        balance = await db.get_account_balance()
        if req.side == OrderSide.BUY:
            required_cash = notional_cost + fee
            if balance.cash_balance < required_cash:
                logger.warning(
                    "Insufficient paper funds: required $%.2f, available $%.2f",
                    required_cash, balance.cash_balance
                )
                order.status = OrderStatus.REJECTED
                await db.update_order_status(order_id, OrderStatus.REJECTED, 0)
                return order

        # Process position and PnL updates
        realized_pnl = await self._apply_execution(
            order=order,
            executed_price=executed_price,
            filled_qty=filled_qty,
            fee=fee,
            slippage=slippage
        )

        order.status = OrderStatus.FILLED
        order.filled_quantity = filled_qty
        order.filled_at = datetime.now(timezone.utc)
        await db.update_order_status(order_id, OrderStatus.FILLED, filled_qty, order.filled_at)

        logger.info(
            "Paper order %s FILLED: %s %d %s %s @ $%.3f (slippage: $%.3f, fee: $%.4f, pnl: $%.2f)",
            order_id, req.side.value, filled_qty, req.platform.value, req.outcome.value,
            executed_price, slippage, fee, realized_pnl
        )

        return order

    async def _fetch_live_book(self, platform: Platform, ticker: str) -> OrderBook:
        try:
            if platform == Platform.KALSHI:
                return await self.kalshi.fetch_orderbook(ticker)
            elif platform == Platform.POLYMARKET:
                return await self.polymarket.fetch_orderbook(ticker)
        except Exception as e:
            logger.error("Error fetching live book for %s %s: %s", platform, ticker, e)
        return OrderBook(platform=platform, ticker=ticker)

    def _match_against_book(
        self,
        orderbook: OrderBook,
        outcome: ContractOutcome,
        side: OrderSide,
        order_type: OrderType,
        target_price: float,
        target_qty: int
    ) -> tuple[float, int, float]:
        """
        Simulates execution by walking orderbook levels.
        Returns: (executed_vwap, filled_qty, slippage)
        """
        levels: List[PriceLevel] = []
        if side == OrderSide.BUY:
            levels = orderbook.yes_asks if outcome == ContractOutcome.YES else orderbook.no_asks
        else:
            levels = orderbook.yes_bids if outcome == ContractOutcome.YES else orderbook.no_bids

        if not levels:
            # Fallback when book depth is not returned or empty
            return (target_price, target_qty, 0.0)

        best_price = levels[0].price

        # Check limit price cross
        if order_type == OrderType.LIMIT:
            if side == OrderSide.BUY and target_price < best_price:
                # Limit price is below best ask -> not marketable yet
                return (0.0, 0, 0.0)
            elif side == OrderSide.SELL and target_price > best_price:
                # Limit price is above best bid -> not marketable yet
                return (0.0, 0, 0.0)

        # Walk the book to fill target_qty
        remaining = target_qty
        total_cost = 0.0
        filled = 0

        for lvl in levels:
            if order_type == OrderType.LIMIT:
                if side == OrderSide.BUY and lvl.price > target_price:
                    break
                if side == OrderSide.SELL and lvl.price < target_price:
                    break

            take_qty = min(remaining, lvl.quantity)
            if take_qty <= 0:
                continue

            total_cost += (lvl.price * take_qty)
            filled += take_qty
            remaining -= take_qty

            if remaining <= 0:
                break

        if filled == 0:
            return (target_price, target_qty, 0.0)

        vwap = round(total_cost / filled, 4)
        slippage = round(abs(vwap - best_price), 4)

        return (vwap, filled, slippage)

    async def _apply_execution(
        self,
        order: Order,
        executed_price: float,
        filled_qty: int,
        fee: float,
        slippage: float
    ) -> float:
        """
        Updates ledger cash, position records, and computes realized PnL.
        """
        existing_pos = await db.get_position(order.platform, order.market_ticker, order.outcome)
        realized_pnl = 0.0
        notional = executed_price * filled_qty

        if order.side == OrderSide.BUY:
            # Cash decreases by notional + fee
            await db.update_account_balance(
                cash_delta=-(notional + fee),
                realized_pnl_delta=0.0,
                fee_delta=fee
            )
            # Update position (average entry price)
            if existing_pos and existing_pos.quantity > 0:
                new_qty = existing_pos.quantity + filled_qty
                new_avg = ((existing_pos.quantity * existing_pos.avg_entry_price) + notional) / new_qty
                existing_pos.quantity = new_qty
                existing_pos.avg_entry_price = round(new_avg, 4)
                existing_pos.current_price = executed_price
                existing_pos.unrealized_pnl = round((executed_price - new_avg) * new_qty, 2)
                existing_pos.updated_at = datetime.now(timezone.utc)
                await db.upsert_position(existing_pos)
            else:
                new_pos = Position(
                    platform=order.platform,
                    market_ticker=order.market_ticker,
                    market_title=order.market_title,
                    outcome=order.outcome,
                    quantity=filled_qty,
                    avg_entry_price=executed_price,
                    current_price=executed_price,
                    unrealized_pnl=0.0,
                    updated_at=datetime.now(timezone.utc)
                )
                await db.upsert_position(new_pos)

        elif order.side == OrderSide.SELL:
            # Selling / Closing position
            if existing_pos and existing_pos.quantity > 0:
                closed_qty = min(filled_qty, existing_pos.quantity)
                realized_pnl = (executed_price - existing_pos.avg_entry_price) * closed_qty - fee
                remaining_qty = existing_pos.quantity - closed_qty
                
                # Cash increases by notional - fee
                await db.update_account_balance(
                    cash_delta=(notional - fee),
                    realized_pnl_delta=realized_pnl,
                    fee_delta=fee
                )

                existing_pos.quantity = remaining_qty
                existing_pos.current_price = executed_price
                existing_pos.unrealized_pnl = round((executed_price - existing_pos.avg_entry_price) * remaining_qty, 2)
                existing_pos.updated_at = datetime.now(timezone.utc)
                await db.upsert_position(existing_pos)
            else:
                # Short sale / pure cash credit
                await db.update_account_balance(
                    cash_delta=(notional - fee),
                    realized_pnl_delta=0.0,
                    fee_delta=fee
                )

        # Log trade record
        trade = Trade(
            id=f"trd_{uuid.uuid4().hex[:10]}",
            order_id=order.id,
            platform=order.platform,
            market_ticker=order.market_ticker,
            market_title=order.market_title,
            outcome=order.outcome,
            side=order.side,
            price=executed_price,
            quantity=filled_qty,
            fee_paid=fee,
            slippage=slippage,
            realized_pnl=realized_pnl,
            strategy_name=order.strategy_name,
            executed_at=datetime.now(timezone.utc)
        )
        await db.insert_trade(trade)

        return realized_pnl
