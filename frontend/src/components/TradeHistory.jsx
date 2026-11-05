import React from 'react';
import { History, CheckCircle2, Zap } from 'lucide-react';

export default function TradeHistory({ trades }) {
  if (!trades || trades.length === 0) {
    return (
      <div className="glass-panel p-5 rounded-2xl mb-6">
        <div className="flex items-center space-x-2 mb-3 pb-2 border-b border-slate-800">
          <History className="w-5 h-5 text-slate-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Trade Execution Audit Trail</h2>
        </div>
        <div className="text-center text-slate-400 font-mono text-sm py-8 bg-slate-950/40 rounded-xl border border-slate-900">
          Awaiting initial automated trade execution...
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <History className="w-5 h-5 text-slate-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Trade Execution Audit Trail</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            {trades.length} Records
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800 pb-2">
              <th className="pb-2 font-bold">TIME</th>
              <th className="pb-2 font-bold">ORDER ID</th>
              <th className="pb-2 font-bold">ASSET</th>
              <th className="pb-2 font-bold">SIDE</th>
              <th className="pb-2 font-bold">EXEC PRICE</th>
              <th className="pb-2 font-bold">ALLOCATED</th>
              <th className="pb-2 font-bold">FEE</th>
              <th className="pb-2 font-bold">STATUS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-900">
            {trades.map((t) => (
              <tr key={t.order_id} className="hover:bg-slate-900/40 transition-colors">
                <td className="py-2.5 text-slate-400">{t.timestamp}</td>
                <td className="py-2.5 font-bold text-cyan-400">{t.order_id}</td>
                <td className="py-2.5 font-semibold text-slate-200">{t.asset}</td>

                <td className="py-2.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    t.side.includes('BUY') || t.side.includes('LONG')
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  }`}>
                    {t.side}
                  </span>
                </td>

                <td className="py-2.5 text-slate-100">${t.execution_price}</td>
                <td className="py-2.5 text-slate-200">${t.allocated_capital}</td>
                <td className="py-2.5 text-slate-400">${t.fee}</td>
                
                <td className="py-2.5">
                  <span className="inline-flex items-center space-x-1 text-emerald-400 font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>FILLED</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
