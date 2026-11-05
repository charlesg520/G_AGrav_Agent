"""
Quantitative Performance and Risk Metrics Engine.
Computes Sharpe Ratio, Sortino Ratio, Maximum Drawdown, Win Rate, and Profit Factor.
"""

import math
from typing import List, Dict, Any
from datetime import datetime
from prediction_agent.database.models import PortfolioSnapshot, Trade

class QuantMetricsCalculator:
    @staticmethod
    def calculate_metrics(
        snapshots: List[PortfolioSnapshot],
        trades: List[Trade],
        risk_free_rate_annual: float = 0.04
    ) -> Dict[str, Any]:
        """
        Computes full performance analytics from portfolio history snapshots and executed trades.
        """
        metrics: Dict[str, Any] = {
            "total_trades": len(trades),
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_realized_pnl": 0.0,
            "total_fees_paid": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "current_equity": 0.0,
            "starting_equity": 0.0,
            "total_return_pct": 0.0
        }

        # Trade-level statistics
        gross_profit = 0.0
        gross_loss = 0.0
        closed_trades = [t for t in trades if t.realized_pnl != 0.0]

        for t in trades:
            metrics["total_fees_paid"] += t.fee_paid
            metrics["total_realized_pnl"] += t.realized_pnl

        for t in closed_trades:
            if t.realized_pnl > 0:
                metrics["winning_trades"] += 1
                gross_profit += t.realized_pnl
            elif t.realized_pnl < 0:
                metrics["losing_trades"] += 1
                gross_loss += abs(t.realized_pnl)

        if closed_trades:
            metrics["win_rate"] = round(metrics["winning_trades"] / len(closed_trades), 4)

        if gross_loss > 0:
            metrics["profit_factor"] = round(gross_profit / gross_loss, 2)
        elif gross_profit > 0:
            metrics["profit_factor"] = 99.99  # No losses recorded yet

        # Equity curve & Drawdown
        if snapshots:
            metrics["starting_equity"] = snapshots[0].total_equity
            metrics["current_equity"] = snapshots[-1].total_equity
            if metrics["starting_equity"] > 0:
                metrics["total_return_pct"] = round(
                    (metrics["current_equity"] - metrics["starting_equity"]) / metrics["starting_equity"], 4
                )

            # Maximum Drawdown calculation
            peak = snapshots[0].total_equity
            max_dd = 0.0
            daily_returns: List[float] = []

            for i in range(1, len(snapshots)):
                eq = snapshots[i].total_equity
                if eq > peak:
                    peak = eq
                elif peak > 0:
                    dd = (peak - eq) / peak
                    if dd > max_dd:
                        max_dd = dd

                prev_eq = snapshots[i - 1].total_equity
                if prev_eq > 0:
                    ret = (eq - prev_eq) / prev_eq
                    daily_returns.append(ret)

            metrics["max_drawdown"] = round(max_dd, 4)

            # Sharpe and Sortino Ratios
            if len(daily_returns) >= 2:
                mean_ret = sum(daily_returns) / len(daily_returns)
                variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
                std_dev = math.sqrt(variance)

                # Daily risk-free rate approximation (252 trading days)
                daily_rf = risk_free_rate_annual / 252.0

                if std_dev > 0:
                    sharpe = ((mean_ret - daily_rf) / std_dev) * math.sqrt(252)
                    metrics["sharpe_ratio"] = round(sharpe, 2)

                # Downside deviation for Sortino
                downside_diffs = [min(0.0, r - daily_rf) ** 2 for r in daily_returns]
                downside_dev = math.sqrt(sum(downside_diffs) / len(daily_returns))
                if downside_dev > 0:
                    sortino = ((mean_ret - daily_rf) / downside_dev) * math.sqrt(252)
                    metrics["sortino_ratio"] = round(sortino, 2)

        return metrics
