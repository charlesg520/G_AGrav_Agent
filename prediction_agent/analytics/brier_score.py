"""
Prediction Market Specific Analytics: Brier Score calibration and Edge Realization.
"""

from typing import List, Dict, Any, Tuple
from prediction_agent.database.models import Trade, Position, ContractOutcome

class BrierAnalytics:
    @staticmethod
    def calculate_brier_score(
        predictions_and_outcomes: List[Tuple[float, int]]
    ) -> float:
        """
        Calculates the Brier Score across resolved predictions.
        
        Parameters:
        - predictions_and_outcomes: List of (predicted_prob_0_to_1, actual_outcome_0_or_1)
        
        Returns:
        - Brier Score (0.00 = perfect foresight, 0.25 = uninformative baseline)
        """
        if not predictions_and_outcomes:
            return 0.0

        total_sq_err = sum((p - outcome) ** 2 for p, outcome in predictions_and_outcomes)
        return round(total_sq_err / len(predictions_and_outcomes), 4)

    @staticmethod
    def compute_calibration_curve(
        predictions_and_outcomes: List[Tuple[float, int]],
        num_bins: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Groups predictions into probability bins to assess calibration.
        E.g., for contracts bought around 70%, did ~70% of them resolve to YES?
        """
        if not predictions_and_outcomes:
            return []

        bin_width = 1.0 / num_bins
        bins = []

        for b in range(num_bins):
            low = b * bin_width
            high = (b + 1) * bin_width
            bucket_items = [
                (p, o) for p, o in predictions_and_outcomes
                if (low <= p < high) or (b == num_bins - 1 and low <= p <= high)
            ]

            count = len(bucket_items)
            avg_pred = sum(p for p, _ in bucket_items) / count if count > 0 else (low + high) / 2
            emp_win_rate = sum(o for _, o in bucket_items) / count if count > 0 else 0.0

            bins.append({
                "range": f"{int(low*100)}%-{int(high*100)}%",
                "count": count,
                "avg_predicted_prob": round(avg_pred, 3),
                "empirical_win_rate": round(emp_win_rate, 3),
                "calibration_gap": round(emp_win_rate - avg_pred, 3)
            })

        return bins

    @staticmethod
    def compute_fee_drag(trades: List[Trade]) -> Dict[str, Any]:
        """
        Analyzes the friction impact of transaction fees on returns.
        """
        total_fees = sum(t.fee_paid for t in trades)
        total_notional = sum(t.price * t.quantity for t in trades)
        fee_drag_pct = (total_fees / total_notional) * 100 if total_notional > 0 else 0.0

        return {
            "total_fees_usd": round(total_fees, 4),
            "total_notional_traded": round(total_notional, 2),
            "fee_drag_percentage": round(fee_drag_pct, 3)
        }
