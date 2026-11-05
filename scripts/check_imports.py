import sys
sys.path.insert(0, '.')
mods = ['backend.config', 'backend.main', 'backend.agents.arbitrage_finder', 'backend.agents.llm_client', 'backend.agents.market_analyzer', 'backend.agents.prediction_reasoner', 'backend.agents.risk_manager', 'backend.execution.connectors', 'backend.execution.oms', 'backend.feeds.crypto_feed', 'backend.feeds.kalshi_feed', 'backend.feeds.prediction_feed', 'backend.storage', 'prediction_agent.main', 'prediction_agent.agent.assistant', 'prediction_agent.analytics.brier_score', 'prediction_agent.analytics.quant_metrics', 'prediction_agent.connectors.base', 'prediction_agent.connectors.kalshi', 'prediction_agent.connectors.polymarket', 'prediction_agent.database.db', 'prediction_agent.database.models', 'prediction_agent.execution.base', 'prediction_agent.execution.fee_calculator', 'prediction_agent.execution.paper_engine', 'prediction_agent.execution.live_bridge', 'prediction_agent.risk.kelly', 'prediction_agent.risk.risk_manager', 'prediction_agent.strategies.base', 'prediction_agent.strategies.cross_market_arb', 'prediction_agent.strategies.dutch_book', 'prediction_agent.strategies.market_maker', 'prediction_agent.strategies.resolution_sniping', 'prediction_agent.ui.cli', 'prediction_agent.ui.server']
failed = []
for m in mods:
    try:
        __import__(m)
    except Exception as e:
        failed.append((m, repr(e)))
for m, e in failed:
    print(f'FAIL {m}: {e}')
print(f'{len(mods)-len(failed)}/{len(mods)} modules import OK')
sys.exit(1 if failed else 0)
