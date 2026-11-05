import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import OverviewStats from './components/OverviewStats';
import PredictionDesk from './components/PredictionDesk';
import CryptoDesk from './components/CryptoDesk';
import AgentThoughtLog from './components/AgentThoughtLog';
import AgentChatBox from './components/AgentChatBox';
import ActivePositions from './components/ActivePositions';
import RiskControls from './components/RiskControls';
import TradeHistory from './components/TradeHistory';

export default function App() {
  const [telemetry, setTelemetry] = useState({
    overview: {
      portfolio_value: 100000.0,
      cash_balance: 100000.0,
      realized_pnl: 0.0,
      unrealized_pnl: 0.0,
      daily_pnl: 0.0,
      daily_pnl_pct: 0.0,
      active_positions_count: 0,
      is_simulation: true,
      kill_switch_active: false,
      win_rate_pct: 72.5,
      sharpe_ratio: 2.84,
    },
    crypto_markets: [],
    prediction_events: [],
    agent_thoughts: [],
    active_positions: [],
    trade_history: [],
    risk_status: {
      kelly_fraction: 0.35,
      max_position_size_pct: 15,
      stop_loss_pct: 4,
      max_daily_drawdown_pct: 5,
      kill_switch_activated: false
    }
  });

  const [isConnected, setIsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('DASHBOARD'); // DASHBOARD, CHAT, PREDICTION, CRYPTO, RISK, AUDIT
  const socketRef = useRef(null);

  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:8000/ws`;
    
    function connectWS() {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setTelemetry(data);
        } catch (e) {
          console.error("WS Parse error:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setTimeout(connectWS, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };

      socketRef.current = ws;
    }

    connectWS();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  const handleToggleKillSwitch = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/kill-switch', { method: 'POST' });
      const data = await res.json();
      setTelemetry((prev) => ({
        ...prev,
        overview: { ...prev.overview, kill_switch_active: data.kill_switch_active }
      }));
    } catch (e) {
      console.error('Kill switch toggle error:', e);
    }
  };

  const handleClosePosition = async (asset) => {
    try {
      await fetch('http://localhost:8000/api/close-position', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset })
      });
    } catch (e) {
      console.error('Close position error:', e);
    }
  };

  const handleUpdateConfig = async (newConfig) => {
    try {
      await fetch('http://localhost:8000/api/update-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
    } catch (e) {
      console.error('Update config error:', e);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col">
      {/* Top Header */}
      <Header
        isConnected={isConnected}
        isSimulation={telemetry.overview.is_simulation}
        killSwitchActive={telemetry.overview.kill_switch_active}
        onToggleKillSwitch={handleToggleKillSwitch}
      />

      {/* Main Content Area */}
      <main className="max-w-[1600px] mx-auto px-6 flex-1 w-full pb-12">
        
        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 mb-6 border-b border-slate-800/80 pb-3 font-mono text-xs">
          {[
            { id: 'DASHBOARD', label: 'OVERVIEW TERMINAL' },
            { id: 'CHAT', label: '💬 AI AGENT CHAT' },
            { id: 'PREDICTION', label: 'PREDICTION MARKETS' },
            { id: 'CRYPTO', label: 'CRYPTO PERPETUALS' },
            { id: 'RISK', label: 'RISK & STRATEGY ENGINE' },
            { id: 'AUDIT', label: 'TRADE AUDIT LOG' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl transition-all font-bold tracking-wider ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-300 border border-cyan-500/40 shadow-lg shadow-cyan-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard Overview View */}
        {activeTab === 'DASHBOARD' && (
          <div>
            <OverviewStats overview={telemetry.overview} />
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <ActivePositions
                positions={telemetry.active_positions}
                onClosePosition={handleClosePosition}
              />
              <AgentThoughtLog thoughts={telemetry.agent_thoughts} />
            </div>

            <AgentChatBox
              portfolioOverview={telemetry.overview}
              activePositions={telemetry.active_positions}
            />

            <PredictionDesk events={telemetry.prediction_events} />
            <CryptoDesk cryptoMarkets={telemetry.crypto_markets} />
          </div>
        )}

        {/* AI Agent Chat Tab */}
        {activeTab === 'CHAT' && (
          <div>
            <AgentChatBox
              portfolioOverview={telemetry.overview}
              activePositions={telemetry.active_positions}
            />
            <AgentThoughtLog thoughts={telemetry.agent_thoughts} />
          </div>
        )}

        {/* Prediction Markets Tab */}
        {activeTab === 'PREDICTION' && (
          <div>
            <PredictionDesk events={telemetry.prediction_events} />
            <ActivePositions
              positions={telemetry.active_positions.filter(p => p.market_type === 'PREDICTION_MARKET')}
              onClosePosition={handleClosePosition}
            />
          </div>
        )}

        {/* Crypto Perpetuals Tab */}
        {activeTab === 'CRYPTO' && (
          <div>
            <CryptoDesk cryptoMarkets={telemetry.crypto_markets} />
            <ActivePositions
              positions={telemetry.active_positions.filter(p => p.market_type !== 'PREDICTION_MARKET')}
              onClosePosition={handleClosePosition}
            />
          </div>
        )}

        {/* Risk & Strategy Settings Tab */}
        {activeTab === 'RISK' && (
          <div>
            <RiskControls
              riskStatus={telemetry.risk_status}
              onUpdateConfig={handleUpdateConfig}
            />
            <AgentThoughtLog thoughts={telemetry.agent_thoughts} />
          </div>
        )}

        {/* Audit Log Tab */}
        {activeTab === 'AUDIT' && (
          <div>
            <TradeHistory trades={telemetry.trade_history} />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-4 px-6 text-center text-xs font-mono text-slate-500">
        AETHER Neural Autonomous Trading Infrastructure v2.5 | Polymer CLOB & Hyperliquid Protocol Connectors Enabled
      </footer>
    </div>
  );
}
