import React, { useState } from 'react';
import { Cpu, Terminal, Filter, ShieldCheck, Zap, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function AgentThoughtLog({ thoughts }) {
  const [filter, setFilter] = useState('ALL');

  const filteredThoughts = (thoughts || []).filter(t => {
    if (filter === 'ALL') return true;
    if (filter === 'SIGNAL') return t.type === 'SIGNAL';
    if (filter === 'EXECUTION') return t.type === 'EXECUTION';
    if (filter === 'RISK') return t.type === 'RISK' || t.type === 'WARNING';
    return true;
  });

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Terminal className="w-5 h-5 text-purple-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Agent Cognitive Stream & Reasoning Audit</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
            Live Telemetry
          </span>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
          {['ALL', 'SIGNAL', 'EXECUTION', 'RISK'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg transition-all ${
                filter === f
                  ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-500/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Terminal Container */}
      <div className="bg-[#050811] rounded-xl p-4 font-mono text-xs max-h-[340px] overflow-y-auto space-y-2 border border-slate-800/80 shadow-inner">
        {filteredThoughts.length === 0 ? (
          <div className="text-slate-500 italic text-center py-6">
            Awaiting agent cognitive iteration step...
          </div>
        ) : (
          filteredThoughts.map((t) => {
            const isExec = t.type === 'EXECUTION';
            const isSignal = t.type === 'SIGNAL';
            const isRisk = t.type === 'RISK' || t.type === 'WARNING';

            return (
              <div key={t.id} className="flex items-start space-x-2.5 leading-relaxed py-1 border-b border-slate-900/60 last:border-0 hover:bg-slate-900/30 px-2 rounded">
                <span className="text-slate-500 shrink-0 font-semibold">{t.timestamp}</span>
                
                {/* Agent Badge */}
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                  isExec ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                  isSignal ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' :
                  isRisk ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                  'bg-slate-800 text-slate-300'
                }`}>
                  [{t.agent}]
                </span>

                {/* Message */}
                <span className={`break-words ${
                  isExec ? 'text-emerald-300 font-semibold' :
                  isSignal ? 'text-slate-200' :
                  isRisk ? 'text-amber-300' : 'text-slate-400'
                }`}>
                  {t.message}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
