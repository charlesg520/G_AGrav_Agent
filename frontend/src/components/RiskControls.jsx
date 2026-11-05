import React, { useState } from 'react';
import { Sliders, ShieldCheck, Zap, Save, RefreshCw } from 'lucide-react';

export default function RiskControls({ riskStatus, onUpdateConfig }) {
  const [kellyFraction, setKellyFraction] = useState(riskStatus?.kelly_fraction || 0.35);
  const [maxTradePct, setMaxTradePct] = useState(riskStatus?.max_position_size_pct || 15);
  const [stopLossPct, setStopLossPct] = useState(riskStatus?.stop_loss_pct || 4);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    await onUpdateConfig({
      kelly_fraction: parseFloat(kellyFraction),
      max_position_size_pct: parseFloat(maxTradePct),
      stop_loss_pct: parseFloat(stopLossPct)
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Sliders className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Risk Engine & Strategy Parameters</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            Human-In-The-Loop
          </span>
        </div>
        <button
          onClick={handleSave}
          className={`flex items-center space-x-1.5 px-4 py-1.5 rounded-xl font-mono text-xs font-bold transition-all shadow-md ${
            saved
              ? 'bg-emerald-500 text-black font-bold'
              : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-500/20'
          }`}
        >
          <Save className="w-3.5 h-3.5" />
          <span>{saved ? 'SETTINGS SAVED!' : 'APPLY PARAMETERS'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 font-mono text-xs">
        
        {/* Kelly Criterion Slider */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <div className="flex justify-between items-center mb-2">
            <span className="text-slate-300 font-bold">Kelly Fraction Multiplier</span>
            <span className="text-cyan-400 font-bold text-sm">{kellyFraction}x</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="1.0"
            step="0.05"
            value={kellyFraction}
            onChange={(e) => setKellyFraction(e.target.value)}
            className="w-full accent-cyan-400 bg-slate-800 h-2 rounded-lg cursor-pointer"
          />
          <p className="text-[10px] text-slate-400 mt-2">
            Controls sizing aggressiveness (0.35x = Conservative Half-Kelly).
          </p>
        </div>

        {/* Max Trade Allocation Slider */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <div className="flex justify-between items-center mb-2">
            <span className="text-slate-300 font-bold">Max Position Size %</span>
            <span className="text-cyan-400 font-bold text-sm">{maxTradePct}%</span>
          </div>
          <input
            type="range"
            min="2"
            max="30"
            step="1"
            value={maxTradePct}
            onChange={(e) => setMaxTradePct(e.target.value)}
            className="w-full accent-cyan-400 bg-slate-800 h-2 rounded-lg cursor-pointer"
          />
          <p className="text-[10px] text-slate-400 mt-2">
            Caps maximum allocation permitted for any single position.
          </p>
        </div>

        {/* Default Stop Loss Slider */}
        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <div className="flex justify-between items-center mb-2">
            <span className="text-slate-300 font-bold">Automated Stop Loss %</span>
            <span className="text-cyan-400 font-bold text-sm">{stopLossPct}%</span>
          </div>
          <input
            type="range"
            min="1"
            max="15"
            step="0.5"
            value={stopLossPct}
            onChange={(e) => setStopLossPct(e.target.value)}
            className="w-full accent-cyan-400 bg-slate-800 h-2 rounded-lg cursor-pointer"
          />
          <p className="text-[10px] text-slate-400 mt-2">
            Automated hard stop loss triggered on market updates.
          </p>
        </div>

      </div>
    </div>
  );
}
