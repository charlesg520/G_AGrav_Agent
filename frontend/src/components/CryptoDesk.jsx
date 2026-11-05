import React from 'react';
import { BarChart2, TrendingUp, TrendingDown, Layers, Zap } from 'lucide-react';

export default function CryptoDesk({ cryptoMarkets }) {
  if (!cryptoMarkets || cryptoMarkets.length === 0) {
    return (
      <div className="glass-panel p-6 rounded-2xl text-center text-slate-400 font-mono text-sm">
        Connecting to Hyperliquid, Kraken Futures & Coinbase Feeds...
      </div>
    );
  }

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <BarChart2 className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Crypto Multi-Exchange Perpetual Futures Terminal</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Hyperliquid • Kraken Futures • Coinbase
          </span>
        </div>
        <div className="text-xs font-mono text-slate-400">
          Cross-Exchange Perpetual Spread Arbitrage Active
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cryptoMarkets.map((market) => {
          const isUp = market.change_24h >= 0;
          const indicators = market.indicators || {};
          const rsi = indicators.rsi || 50;
          const momentum = indicators.momentum || 'NEUTRAL';
          const orderbook = market.orderbook || { imbalance: 0 };
          const imbalance = orderbook.imbalance || 0;
          const exchanges = market.exchanges || {};

          return (
            <div key={market.symbol} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-emerald-500/40 transition-all">
              
              {/* Asset Title & Price */}
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="font-mono font-bold text-base text-slate-100">{market.symbol}</span>
                  <div className="text-[10px] font-mono text-slate-400">OI: {market.open_interest}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-bold text-base text-slate-100">${market.price}</div>
                  <div className={`text-xs font-mono font-semibold flex items-center justify-end space-x-0.5 ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    <span>{isUp ? '+' : ''}{market.change_24h}%</span>
                  </div>
                </div>
              </div>

              {/* Multi-Exchange Perpetual Futures Prices Table */}
              <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 my-2 font-mono text-[11px] space-y-1">
                <div className="flex justify-between text-slate-400 text-[10px] border-b border-slate-800 pb-1 mb-1 font-bold">
                  <span>EXCHANGE PERPETUALS</span>
                  <span>QUOTE</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-cyan-400 font-bold">Hyperliquid (Perp)</span>
                  <span className="text-slate-100 font-bold">{exchanges.hyperliquid || `$${market.price}`}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-purple-400 font-bold">Kraken Futures (Perp)</span>
                  <span className="text-slate-200">{exchanges.kraken_futures || `$${market.price}`}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-blue-400 font-bold">Coinbase Exchange</span>
                  <span className="text-slate-200">{exchanges.coinbase || `$${market.price}`}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-slate-900 text-[10px]">
                  <span className="text-slate-400">Perp Spread:</span>
                  <span className="text-emerald-400 font-bold">+{exchanges.spread_pct || 0.0}%</span>
                </div>
              </div>

              {/* Indicators Badge */}
              <div className="grid grid-cols-3 gap-2 my-2 text-center text-[11px] font-mono">
                <div className="bg-slate-950 p-1.5 rounded border border-slate-800">
                  <div className="text-slate-400 text-[9px]">RSI (14)</div>
                  <div className={`font-bold ${rsi < 35 ? 'text-emerald-400' : rsi > 65 ? 'text-rose-400' : 'text-slate-200'}`}>
                    {rsi}
                  </div>
                </div>

                <div className="bg-slate-950 p-1.5 rounded border border-slate-800">
                  <div className="text-slate-400 text-[9px]">MOMENTUM</div>
                  <div className={`font-bold ${momentum === 'BULLISH' ? 'text-emerald-400' : momentum === 'BEARISH' ? 'text-rose-400' : 'text-slate-300'}`}>
                    {momentum}
                  </div>
                </div>

                <div className="bg-slate-950 p-1.5 rounded border border-slate-800">
                  <div className="text-slate-400 text-[9px]">FUNDING</div>
                  <div className="text-cyan-400 font-bold">
                    {(market.funding_rate * 100).toFixed(3)}%
                  </div>
                </div>
              </div>

            </div>
          );
        })}
      </div>
    </div>
  );
}
