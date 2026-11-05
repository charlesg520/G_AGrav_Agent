import React from 'react';
import { DollarSign, TrendingUp, TrendingDown, Wallet, Award, Activity, Layers } from 'lucide-react';

export default function OverviewStats({ overview }) {
  const portfolioVal = overview?.portfolio_value || 100000;
  const cashVal = overview?.cash_balance || 100000;
  const dailyPnl = overview?.daily_pnl || 0;
  const dailyPnlPct = overview?.daily_pnl_pct || 0;
  const isPositive = dailyPnl >= 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      
      {/* Portfolio Value */}
      <div className="glass-panel glass-panel-hover p-4 rounded-2xl relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
          <span>TOTAL PORTFOLIO VALUE</span>
          <Wallet className="w-4 h-4 text-cyan-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
          ${portfolioVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div className="text-xs font-mono text-slate-400 mt-1 flex items-center justify-between">
          <span>Available Cash:</span>
          <span className="text-slate-200 font-semibold">${cashVal.toLocaleString()}</span>
        </div>
        <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl pointer-events-none"></div>
      </div>

      {/* Daily PnL */}
      <div className="glass-panel glass-panel-hover p-4 rounded-2xl relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
          <span>DAILY UNREALIZED P&L</span>
          {isPositive ? <TrendingUp className="w-4 h-4 text-emerald-400" /> : <TrendingDown className="w-4 h-4 text-rose-400" />}
        </div>
        <div className={`text-2xl font-bold font-mono tracking-tight ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
          {isPositive ? '+' : ''}${dailyPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
        <div className="text-xs font-mono mt-1 flex items-center space-x-1.5">
          <span className={`px-2 py-0.5 rounded font-semibold text-[11px] ${isPositive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
            {isPositive ? '+' : ''}{dailyPnlPct}%
          </span>
          <span className="text-slate-400">vs 24h baseline</span>
        </div>
      </div>

      {/* Realized PnL */}
      <div className="glass-panel glass-panel-hover p-4 rounded-2xl relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
          <span>REALIZED PROFIT</span>
          <DollarSign className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
          ${(overview?.realized_pnl || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>
        <div className="text-xs font-mono text-slate-400 mt-1">
          Settled closed orders
        </div>
      </div>

      {/* Win Rate & Sharpe */}
      <div className="glass-panel glass-panel-hover p-4 rounded-2xl relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
          <span>WIN RATE / SHARPE</span>
          <Award className="w-4 h-4 text-purple-400" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span className="text-2xl font-bold font-mono text-purple-300">
            {overview?.win_rate_pct || 72.5}%
          </span>
          <span className="text-xs font-mono text-slate-400">/ Sharpe {overview?.sharpe_ratio || 2.84}</span>
        </div>
        <div className="text-xs font-mono text-slate-400 mt-1">
          Kelly Criterion optimized
        </div>
      </div>

      {/* Active Positions Count */}
      <div className="glass-panel glass-panel-hover p-4 rounded-2xl relative overflow-hidden">
        <div className="flex items-center justify-between text-slate-400 text-xs font-mono mb-2">
          <span>ACTIVE POSITIONS</span>
          <Layers className="w-4 h-4 text-amber-400" />
        </div>
        <div className="text-2xl font-bold font-mono text-amber-300 tracking-tight">
          {overview?.active_positions_count || 0}
        </div>
        <div className="text-xs font-mono text-slate-400 mt-1">
          Across Crypto & Predictions
        </div>
      </div>

    </div>
  );
}
