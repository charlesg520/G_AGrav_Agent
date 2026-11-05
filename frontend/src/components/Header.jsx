import React from 'react';
import { Activity, ShieldAlert, Cpu, Radio, Zap, AlertTriangle, Lock } from 'lucide-react';

export default function Header({ isConnected, isSimulation, killSwitchActive, onToggleKillSwitch }) {
  return (
    <header className="glass-panel border-b border-slate-800/80 sticky top-0 z-50 px-6 py-3.5 mb-6">
      <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Brand & Logo */}
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-600 p-0.5 shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-[#0b1329] rounded-[10px] flex items-center justify-center">
              <Zap className="w-5 h-5 text-cyan-400 fill-cyan-400/20" />
            </div>
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-slate-100 via-slate-200 to-cyan-400 bg-clip-text text-transparent">
                AETHER
              </h1>
              <span className="text-[10px] font-mono tracking-wider px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase font-semibold">
                Autonomous V2.5
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">Crypto & Prediction Markets Neural Trading Engine</p>
          </div>
        </div>

        {/* Live System Telemetry Status Badges */}
        <div className="flex flex-wrap items-center gap-3">
          {/* WS Stream Indicator */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs font-mono">
            <Radio className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400 animate-pulse' : 'text-rose-400'}`} />
            <span className="text-slate-300">Feed Stream:</span>
            <span className={isConnected ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
              {isConnected ? 'ONLINE' : 'CONNECTING...'}
            </span>
          </div>

          {/* Execution Mode */}
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs font-mono">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-300">Execution:</span>
            <span className="text-cyan-400 font-semibold">
              {isSimulation ? 'PAPER SIMULATION' : 'LIVE PRODUCTION'}
            </span>
          </div>

          {/* Emergency Kill Switch Button */}
          <button
            onClick={onToggleKillSwitch}
            className={`flex items-center space-x-2 px-4 py-1.5 rounded-xl font-mono text-xs font-bold transition-all shadow-md ${
              killSwitchActive
                ? 'bg-rose-500 hover:bg-rose-600 text-white glow-rose animate-pulse'
                : 'bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/80'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>{killSwitchActive ? 'EMERGENCY HALT ACTIVE' : 'KILL SWITCH'}</span>
          </button>
        </div>

      </div>
    </header>
  );
}
