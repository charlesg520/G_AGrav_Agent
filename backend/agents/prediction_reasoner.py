from typing import Dict, Any, List

class PredictionReasonerAgent:
    """Probabilistic AI Reasoning Agent for Prediction Markets (Short & Long Term)."""

    def evaluate(self, prediction_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        signals = []
        for event in prediction_events:
            yes_price = event["yes_price"]
            no_price = event["no_price"]
            llm_fair_prob = event["llm_fair_prob"]
            question = event["question"]
            news = event["news_headline"]
            timeframe_label = event.get("timeframe_label", "GENERAL")
            
            ev_yes = round((llm_fair_prob * 1.0) - yes_price, 3)
            fair_no_prob = 1.0 - llm_fair_prob
            ev_no = round((fair_no_prob * 1.0) - no_price, 3)

            confidence_pct = event.get("confidence_pct", 85)
            expected_gain_pct = event.get("expected_gain_pct", 15.0)

            # Signal threshold: EV > +$0.05 per $1 contract
            if ev_yes >= 0.05:
                signals.append({
                    "strategy": "PREDICTION_PROBABILISTIC_EDGE",
                    "asset": event["id"],
                    "event_question": question,
                    "platform": event["platform"],
                    "timeframe": event.get("timeframe", "LONG_TERM"),
                    "timeframe_label": timeframe_label,
                    "side": "BUY_YES",
                    "market_type": "PREDICTION_MARKET",
                    "price": yes_price,
                    "fair_probability": llm_fair_prob,
                    "market_implied_prob": round(yes_price * 100, 1),
                    "ev": ev_yes,
                    "confidence": min(0.98, round(confidence_pct / 100.0, 2)),
                    "confidence_pct": confidence_pct,
                    "expected_gain_pct": expected_gain_pct,
                    "reasoning": f"[{timeframe_label}] EV (+${ev_yes}/share). Fair Prob ({llm_fair_prob*100}%) vs Market ({yes_price*100}%). Gain: +{expected_gain_pct}%. Catalyst: '{news}'"
                })
            elif ev_no >= 0.05:
                signals.append({
                    "strategy": "PREDICTION_PROBABILISTIC_EDGE",
                    "asset": event["id"],
                    "event_question": question,
                    "platform": event["platform"],
                    "timeframe": event.get("timeframe", "LONG_TERM"),
                    "timeframe_label": timeframe_label,
                    "side": "BUY_NO",
                    "market_type": "PREDICTION_MARKET",
                    "price": no_price,
                    "fair_probability": fair_no_prob,
                    "market_implied_prob": round(no_price * 100, 1),
                    "ev": ev_no,
                    "confidence": min(0.98, round(confidence_pct / 100.0, 2)),
                    "confidence_pct": confidence_pct,
                    "expected_gain_pct": expected_gain_pct,
                    "reasoning": f"[{timeframe_label}] EV (+${ev_no}/share for NO). Fair No Prob ({fair_no_prob*100}%) vs Market ({no_price*100}%). Gain: +{expected_gain_pct}%. Catalyst: '{news}'"
                })

        return signals

prediction_reasoner = PredictionReasonerAgent()
