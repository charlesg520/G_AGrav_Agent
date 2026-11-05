import React from 'react';
import { Layers, XCircle, ArrowUpRight, ArrowDownRight, Zap } from 'lucide-react';

export default function ActivePositions({ positions, onClosePosition }) {
  if (!positions || positions.length === 0) {
    return (
      <div className="glass-panel p-5 rounded-2xl mb-6">
        <div className="flex items-center space-x-2 mb-3 pb-2 border-b border-slate-800">
          <Layers className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Active Portfolio Positions</h2>
        </div>
        <div className="text-center text-slate-400 font-mono text-sm py-8 bg-slate-950/40 rounded-xl border border-slate-900">
          No open positions. Agent scanning for high EV+ opportunities...
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Layers className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Active Portfolio Positions</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold">
            {positions.length} Active
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800 pb-2">
              <th className="pb-2 font-bold">ASSET / EVENT</th>
              <th className="pb-2 font-bold">TYPE & SIDE</th>
              <th className="pb-2 font-bold">UNITS</th>
              <th className="pb-2 font-bold">ENTRY PRICE</th>
              <th className="pb-2 font-bold">MARK PRICE</th>
              <th className="pb-2 font-bold">INVESTED</th>
              <th className="pb-2 font-bold">UNREALIZED P&L</th>
              <th className="pb-2 font-bold text-right">ACTION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900">
            {positions.map((pos) => {
              const pnl = pos.unrealized_pnl || 0;
              const pnlPct = pos.unrealized_pnl_pct || 0;
              const isWin = pnl >= 0;

              return (
                <tr key={pos.asset} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 font-semibold text-slate-100 max-w-[220px] truncate">
                    <div>{pos.asset}</div>
                    {pos.event_question && pos.event_question !== pos.asset && (
                      <div className="text-[10px] text-slate-400 font-normal truncate">{pos.event_question}</div>
                    )}
                  </td>

                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      pos.side.includes('BUY') || pos.side.includes('LONG')
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    }`}>
                      {pos.side}
                    </span>
                  </td>

                  <td className="py-3 text-slate-200">{pos.units}</td>
                  <td className="py-3 text-slate-300">${pos.entry_price}</td>
                  <td className="py-3 text-slate-100 font-bold">${pos.current_price}</td>
                  <td className="py-3 text-slate-200">${pos.total_invested}</td>

                  <td className="py-3 font-bold">
                    <div className={`flex items-center space-x-1 ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isWin ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                      <span>{isWin ? '+' : ''}${pnl} ({isWin ? '+' : ''}{pnlPct}%)</span>
                    </div>
                  </td>

                  <td className="py-3 text-right">
                    <button
                      onClick={() => onClosePosition(pos.asset)}
                      className="px-2.5 py-1 rounded-lg bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800 text-[11px] font-bold transition-all flex items-center space-x-1 ml-auto"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Liquidate</span>
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
