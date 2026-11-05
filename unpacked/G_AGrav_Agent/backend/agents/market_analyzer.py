from typing import Dict, Any, List

class TechnicalMarketAnalyzer:
    """Quantitative Technical Analysis Agent for Crypto Perpetual & Spot Markets."""

    def evaluate(self, crypto_market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        signals = []
        for symbol, data in crypto_market_data.items():
            indicators = data.get("indicators", {})
            rsi = indicators.get("rsi", 50)
            macd = indicators.get("macd", 0)
            macd_signal = indicators.get("macd_signal", 0)
            price = data.get("price", 0)
            funding_rate = data.get("funding_rate", 0)
            orderbook = data.get("orderbook", {})
            imbalance = orderbook.get("imbalance", 0)

            # Strategy 1: RSI Overbought/Oversold + Orderbook Imbalance
            if rsi < 32 and imbalance > 0.15:
                confidence = min(0.92, round((35 - rsi) / 20 + imbalance, 2))
                signals.append({
                    "strategy": "QUANT_RSI_OVERSOLD_REVERSAL",
                    "asset": symbol,
                    "side": "BUY",
                    "market_type": "CRYPTO_PERP",
                    "price": price,
                    "confidence": confidence,
                    "reasoning": f"{symbol} RSI oversold ({rsi}) with strong bid-side imbalance ({imbalance}). Mean reversion setup."
                })
            elif rsi > 68 and imbalance < -0.15:
                confidence = min(0.92, round((rsi - 65) / 20 + abs(imbalance), 2))
                signals.append({
                    "strategy": "QUANT_RSI_OVERBOUGHT_REVERSAL",
                    "asset": symbol,
                    "side": "SELL",
                    "market_type": "CRYPTO_PERP",
                    "price": price,
                    "confidence": confidence,
                    "reasoning": f"{symbol} RSI overbought ({rsi}) with heavy ask-side pressure ({imbalance}). Short setup."
                })

            # Strategy 2: MACD Bullish/Bearish Crossover + Funding Rate Arbitrage
            if macd > macd_signal and macd > 0 and funding_rate < 0.0004:
                signals.append({
                    "strategy": "QUANT_MACD_MOMENTUM_BREAKOUT",
                    "asset": symbol,
                    "side": "BUY",
                    "market_type": "CRYPTO_PERP",
                    "price": price,
                    "confidence": 0.85,
                    "reasoning": f"{symbol} MACD histogram bullish crossover above zero line. Healthy funding rate ({funding_rate*100}%)."
                })

        return signals

market_analyzer = TechnicalMarketAnalyzer()
