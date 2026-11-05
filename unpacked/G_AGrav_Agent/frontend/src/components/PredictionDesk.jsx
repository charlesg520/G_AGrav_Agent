import React, { useState } from 'react';
import { Target, Sparkles, Clock, Zap, TrendingUp, Award } from 'lucide-react';

export default function PredictionDesk({ events }) {
  const [selectedTimeframe, setSelectedTimeframe] = useState('ALL'); // ALL, SHORT_TERM, LONG_TERM

  if (!events || events.length === 0) {
    return (
      <div className="glass-panel p-6 rounded-2xl text-center text-slate-400 font-mono text-sm">
        Scanning prediction market feeds (Polymarket & Kalshi)...
      </div>
    );
  }

  const filteredEvents = events.filter((ev) => {
    if (selectedTimeframe === 'ALL') return true;
    return ev.timeframe === selectedTimeframe;
  });

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Target className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Prediction Markets Alpha Desk</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            Polymarket & Kalshi
          </span>
        </div>

        {/* Short Term vs Long Term Filter Tabs */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
          {[
            { id: 'ALL', label: 'ALL OPPORTUNITIES' },
            { id: 'SHORT_TERM', label: '⚡ SHORT TERM (15m / 30m / 1h / Sports)' },
            { id: 'LONG_TERM', label: '🏛️ LONG TERM (Macro & Fed)' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedTimeframe(tab.id)}
              className={`px-3 py-1.5 rounded-lg transition-all font-bold ${
                selectedTimeframe === tab.id
                  ? 'bg-cyan-500 text-black shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-4">
        {filteredEvents.map((event) => {
          const yesPrice = event.yes_price;
          const noPrice = event.no_price;
          const fairProb = event.llm_fair_prob;
          const fairProbPct = roundVal(fairProb * 100);
          const impliedProbPct = event.implied_prob_yes;
          const isShortTerm = event.timeframe === 'SHORT_TERM';
          const isYieldArb = event.arbitrage_opportunity;

          return (
            <div key={event.id} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 transition-all">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                
                {/* Question, Timeframe & Metrics Badges */}
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    {/* Timeframe Tag */}
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded flex items-center space-x-1 ${
                      isShortTerm
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    }`}>
                      <Clock className="w-3 h-3" />
                      <span>{event.timeframe_label}</span>
                    </span>

                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {event.platform}
                    </span>

                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700">
                      {event.category}
                    </span>

                    {/* Confidence % Badge */}
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center space-x-1">
                      <Award className="w-3 h-3 text-cyan-400" />
                      <span>CONFIDENCE {event.confidence_pct}%</span>
                    </span>

                    {/* Expected Gain % Badge */}
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1">
                      <TrendingUp className="w-3 h-3 text-emerald-400" />
                      <span>EXPECTED GAIN +{event.expected_gain_pct}%</span>
                    </span>

                    {isYieldArb && (
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse flex items-center space-x-1">
                        <Zap className="w-3 h-3 text-amber-400" />
                        <span>ARBITRAGE ${event.arbitrage_sum}</span>
                      </span>
                    )}
                  </div>
                  
                  <h3 className="font-semibold text-slate-100 text-base mb-1 hover:text-cyan-300 cursor-pointer transition-colors">
                    {event.question}
                  </h3>
                  
                  <p className="text-xs text-slate-400 font-mono italic">
                    Catalyst: "{event.news_headline}"
                  </p>
                </div>

                {/* Probability Bar */}
                <div className="w-full lg:w-72 flex flex-col justify-center bg-slate-950/80 p-3 rounded-lg border border-slate-800">
                  <div className="flex justify-between text-xs font-mono mb-1 text-slate-300">
                    <span>Market: <strong className="text-cyan-400">{impliedProbPct}%</strong></span>
                    <span>AI True: <strong className="text-purple-400">{fairProbPct}%</strong></span>
                  </div>

                  <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mb-1.5 flex">
                    <div className="bg-cyan-500 h-full transition-all duration-500" style={{ width: `${impliedProbPct}%` }}></div>
                    <div className="bg-slate-700 h-full transition-all duration-500" style={{ width: `${100 - impliedProbPct}%` }}></div>
                  </div>

                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden flex">
                    <div className="bg-purple-500 h-full transition-all duration-500" style={{ width: `${fairProbPct}%` }}></div>
                    <div className="bg-slate-700 h-full transition-all duration-500" style={{ width: `${100 - fairProbPct}%` }}></div>
                  </div>
                </div>

                {/* Outcome Odds */}
                <div className="flex items-center space-x-3">
                  <div className="text-center px-3 py-2 rounded-lg bg-emerald-950/40 border border-emerald-800/60 min-w-[80px]">
                    <div className="text-[10px] text-emerald-400 font-mono font-bold">YES</div>
                    <div className="text-base font-bold font-mono text-emerald-300">${yesPrice}</div>
                  </div>

                  <div className="text-center px-3 py-2 rounded-lg bg-rose-950/40 border border-rose-800/60 min-w-[80px]">
                    <div className="text-[10px] text-rose-400 font-mono font-bold">NO</div>
                    <div className="text-base font-bold font-mono text-rose-300">${noPrice}</div>
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

function roundVal(val) {
  return Math.round(val * 10) / 10;
}
