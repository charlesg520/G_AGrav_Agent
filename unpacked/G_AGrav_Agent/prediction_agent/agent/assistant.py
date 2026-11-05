"""
Conversational Trading Agent Assistant with persistent memory, multi-provider LLM support,
and live prediction market tool-calling.
Supports OpenAI, Anthropic Claude, DeepSeek, Groq, Gemini, local Ollama, or built-in heuristic mode.
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from prediction_agent.config import settings
from prediction_agent.database.db import db
from prediction_agent.agent.memory import ChatMemoryManager
from prediction_agent.execution.paper_engine import PaperExecutionEngine
from prediction_agent.connectors.kalshi import KalshiConnector
from prediction_agent.connectors.polymarket import PolymarketConnector
from prediction_agent.strategies.cross_market_arb import CrossMarketArbitrageStrategy
from prediction_agent.strategies.dutch_book import DutchBookStrategy
from prediction_agent.strategies.market_maker import MarketMakerStrategy
from prediction_agent.strategies.resolution_sniping import ResolutionSnipingStrategy
from prediction_agent.analytics.quant_metrics import QuantMetricsCalculator
from prediction_agent.database.models import StrategyType, Platform, OrderSide, ContractOutcome

logger = logging.getLogger(__name__)

class TradingAgentAssistant:
    def __init__(
        self,
        paper_engine: Optional[PaperExecutionEngine] = None,
        memory: Optional[ChatMemoryManager] = None
    ):
        self.kalshi = KalshiConnector()
        self.polymarket = PolymarketConnector()
        self.engine = paper_engine or PaperExecutionEngine(self.kalshi, self.polymarket)
        self.memory = memory or ChatMemoryManager()
        
        # Strategies
        self.cross_arb = CrossMarketArbitrageStrategy()
        self.dutch_book = DutchBookStrategy()
        self.market_maker = MarketMakerStrategy()
        self.resolution_sniping = ResolutionSnipingStrategy()

    async def chat(self, session_id: str, user_prompt: str) -> str:
        """
        Receives user prompt, executes relevant quant/market tools, and responds with persistent memory context.
        """
        # Ensure session exists
        await self.memory.get_or_create_session(session_id, title=user_prompt[:30])
        
        # Save user message
        await self.memory.add_message(session_id, role="user", content=user_prompt)

        # Retrieve history & cross-session context
        history = await self.memory.get_session_history(session_id, limit=10)
        past_sessions_summary = await self.memory.get_cross_session_summary(session_id, limit=3)

        # Check if an external LLM provider is requested (OpenAI, Claude, DeepSeek, Groq, Ollama)
        if settings.LLM_PROVIDER != "heuristic":
            try:
                llm_response = await self._generate_with_llm(user_prompt, history, past_sessions_summary)
                if llm_response:
                    await self.memory.add_message(session_id, role="assistant", content=llm_response)
                    return llm_response
            except Exception as e:
                logger.warning("LLM provider %s failed (%s), falling back to native engine", settings.LLM_PROVIDER, e)

        # Built-in deterministic quant tool router
        response_text = await self._route_and_execute(user_prompt, history, past_sessions_summary)

        # Save assistant response
        await self.memory.add_message(session_id, role="assistant", content=response_text)
        return response_text

    async def _generate_with_llm(
        self,
        prompt: str,
        history: List[Any],
        cross_session_summary: str
    ) -> Optional[str]:
        """
        Routes the user conversation and live market telemetry through LiteLLM to any supported provider:
        OpenAI, Claude, DeepSeek, Groq, Gemini, Ollama, etc.
        """
        try:
            import litellm
        except ImportError:
            logger.error("litellm is not installed.")
            return None

            # Silence litellm verbose logs
        litellm.suppress_debug_info = True

        # Resolve model string
        model_name = self._resolve_model_name()
        
        # Fetch real-time portfolio telemetry for the LLM
        balance = await db.get_account_balance()
        positions = await db.get_positions()
        
        system_prompt = (
            "You are the AceSammy Quantitative Trading Assistant, an expert AI agent managing "
            "a professional prediction market paper-trading portfolio across Kalshi and Polymarket.\n\n"
            f"LIVE TELEMETRY:\n"
            f"- Trading Mode: {settings.TRADING_MODE}\n"
            f"- Cash Balance: ${balance.cash_balance:,.2f}\n"
            f"- Invested Capital: ${balance.invested_capital:,.2f}\n"
            f"- Total Equity: ${balance.total_equity:,.2f}\n"
            f"- Unrealized PnL: ${balance.unrealized_pnl:+,.2f}\n"
            f"- Realized PnL: ${balance.realized_pnl:+,.2f}\n"
            f"- Open Positions Count: {len(positions)}\n\n"
            f"STRATEGIES ACTIVE:\n"
            "- Cross-Market Arbitrage (Kalshi vs Polymarket)\n"
            "- Mutually Exclusive Multi-Outcome Dutch Book Arbitrage\n"
            "- Market Making & Inside Spread Capture\n"
            "- Resolution Convergence (Certainty Sniping)\n\n"
            f"MEMORY OF PAST SESSIONS:\n{cross_session_summary}\n\n"
            "Answer questions clearly, mathematically, and objectively. Format numbers in clean Markdown tables when helpful."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for m in history[-6:]:
            messages.append({"role": m.role if m.role in ["user", "assistant"] else "user", "content": m.content})
        messages.append({"role": "user", "content": prompt})

        # Set API keys dynamically if provided in settings
        env_kwargs = {}
        if settings.OPENAI_API_KEY:
            env_kwargs["api_key"] = settings.OPENAI_API_KEY
        elif settings.ANTHROPIC_API_KEY:
            env_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
        elif settings.DEEPSEEK_API_KEY:
            env_kwargs["api_key"] = settings.DEEPSEEK_API_KEY
        elif settings.GROQ_API_KEY:
            env_kwargs["api_key"] = settings.GROQ_API_KEY
        elif settings.GEMINI_API_KEY:
            env_kwargs["api_key"] = settings.GEMINI_API_KEY
        elif settings.OPENROUTER_API_KEY:
            env_kwargs["api_key"] = settings.OPENROUTER_API_KEY

        if settings.OPENAI_BASE_URL:
            env_kwargs["api_base"] = settings.OPENAI_BASE_URL
        elif settings.LLM_PROVIDER == "ollama":
            env_kwargs["api_base"] = settings.OLLAMA_BASE_URL

        resp = await litellm.acompletion(
            model=model_name,
            messages=messages,
            **env_kwargs
        )
        return resp.choices[0].message.content

    def _resolve_model_name(self) -> str:
        provider = settings.LLM_PROVIDER
        custom_model = settings.LLM_MODEL.strip()

        if provider == "openai":
            return custom_model or "gpt-4o"
        elif provider == "anthropic":
            return custom_model or "claude-3-5-sonnet-20241022"
        elif provider == "deepseek":
            return f"deepseek/{custom_model or 'deepseek-chat'}"
        elif provider == "groq":
            return f"groq/{custom_model or 'llama-3.3-70b-versatile'}"
        elif provider == "gemini":
            return f"gemini/{custom_model or 'gemini-2.5-flash'}"
        elif provider == "ollama":
            return f"ollama/{settings.OLLAMA_MODEL or 'llama3.2'}"
        elif provider == "openrouter":
            return f"openrouter/{custom_model or 'anthropic/claude-3.5-sonnet'}"
        return "gpt-4o"

    async def _route_and_execute(
        self,
        prompt: str,
        history: List[Any],
        cross_session_summary: str
    ) -> str:
        lower = prompt.lower()

        # 1. Portfolio & Performance Query
        if any(w in lower for w in ["portfolio", "performance", "balance", "pnl", "equity", "how are we doing", "sharpe", "stats"]):
            return await self._tool_get_portfolio_report()

        # 2. Scan for Arbitrage & Edge Opportunities
        elif any(w in lower for w in ["scan", "arbitrage", "opportunities", "edges", "find arb", "dutch book", "sniping"]):
            return await self._tool_scan_opportunities(prompt)

        # 3. Positions and Open Orders Query
        elif any(w in lower for w in ["positions", "holdings", "open orders", "trades"]):
            return await self._tool_get_positions_report()

        # 4. Market Inspection (e.g., "inspect fed", "look up elon mars", "check polymarket")
        elif any(w in lower for w in ["inspect", "look up", "check market", "odds for", "search"]):
            return await self._tool_inspect_market(prompt)

        # 5. Risk / Parameter Adjustment
        elif any(w in lower for w in ["risk", "kelly", "max position", "drawdown", "exposure"]):
            return await self._tool_handle_risk_settings(prompt)

        # 6. Past chats / memory query
        elif any(w in lower for w in ["past chat", "previous chat", "remember", "history", "what did we talk about"]):
            return f"### Memory Context\nHere is a recap of your recent conversations across sessions:\n\n{cross_session_summary}\n\nYou can ask me specific questions about any previous strategy or trade discussion!"

        # Default Help / General Prediction Market Quant Advice
        else:
            return (
                "### Prediction Market Quant Agent Active\n"
                f"Currently running in **{settings.TRADING_MODE} TRADING** mode.\n"
                f"Conversational Intelligence Engine: **{settings.LLM_PROVIDER.upper()}**\n\n"
                "Here are actions you can request:\n"
                "- **'Portfolio'**: View cash, invested equity, realized/unrealized PnL, win rate, and Sharpe ratio.\n"
                "- **'Scan'**: Run real-time edge scanners across Kalshi and Polymarket (Cross-Market Arb, Dutch Book, Spread Capture, Resolution Sniping).\n"
                "- **'Positions'**: View current open positions, entry prices, and unrealized returns.\n"
                "- **'Inspect <topic>'**: Search and inspect live order books and implied probabilities (e.g. *'inspect Mars'* or *'inspect Fed'*).\n"
                "- **'Risk'**: View or adjust Fractional Kelly sizing and exposure limits.\n"
                "- **'Past chats'**: Review past sessions and strategic notes.\n\n"
                f"{cross_session_summary}"
            )

    async def _tool_get_portfolio_report(self) -> str:
        balance = await db.get_account_balance()
        trades = await db.get_trades(limit=200)
        snapshots = await db.get_portfolio_history(limit=100)
        metrics = QuantMetricsCalculator.calculate_metrics(snapshots, trades)

        report = [
            "### Portfolio & Performance Analytics",
            f"- **Execution Mode**: `{settings.TRADING_MODE}` (Paper-Trading simulation with live depth matching)",
            f"- **Total Portfolio Equity**: `${balance.total_equity:,.2f}`",
            f"- **Available Cash**: `${balance.cash_balance:,.2f}`",
            f"- **Invested Capital**: `${balance.invested_capital:,.2f}`",
            f"- **Unrealized PnL**: `${balance.unrealized_pnl:+,.2f}`",
            f"- **Realized PnL**: `${balance.realized_pnl:+,.2f}`",
            f"- **Total Exchange Fees Paid**: `${balance.total_fees_paid:,.4f}`",
            "",
            "#### Quantitative Risk & Edge Metrics",
            f"- **Win Rate**: `{metrics['win_rate']*100:.1f}%` ({metrics['winning_trades']} wins / {metrics['total_trades']} total trades)",
            f"- **Profit Factor**: `{metrics['profit_factor']}`",
            f"- **Max Drawdown**: `{metrics['max_drawdown']*100:.2f}%`",
            f"- **Annualized Sharpe Ratio**: `{metrics['sharpe_ratio']}`",
            f"- **Sortino Ratio**: `{metrics['sortino_ratio']}`",
            f"- **Open Positions**: `{balance.open_positions_count}` active market contracts"
        ]
        return "\n".join(report)

    async def _tool_get_positions_report(self) -> str:
        positions = await db.get_positions()
        if not positions:
            return "### Open Positions\n*You currently have no open positions. Use `scan` to find market edges and initiate paper trades.*"

        rows = [
            "### Current Open Positions",
            "| Platform | Market / Event | Side | Qty | Avg Entry | Current Price | Unrealized PnL |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |"
        ]
        for p in positions:
            pnl_color = f"+${p.unrealized_pnl:.2f}" if p.unrealized_pnl >= 0 else f"-${abs(p.unrealized_pnl):.2f}"
            rows.append(
                f"| **{p.platform.value}** | {p.market_title[:35]}... | {p.outcome.value} | {p.quantity} | "
                f"${p.avg_entry_price:.3f} | ${p.current_price:.3f} | `{pnl_color}` |"
            )

        return "\n".join(rows)

    async def _tool_scan_opportunities(self, prompt: str) -> str:
        # Fetch fresh markets from both platforms
        k_markets = await self.kalshi.fetch_markets(limit=60, active_only=True)
        p_markets = await self.polymarket.fetch_markets(limit=60, active_only=True)

        found_opps = []

        # Run all edge scanners
        arb_opps = await self.cross_arb.scan(k_markets, p_markets)
        dutch_opps = await self.dutch_book.scan(k_markets, p_markets)
        mm_opps = await self.market_maker.scan(k_markets, p_markets)
        sniping_opps = await self.resolution_sniping.scan(k_markets, p_markets)

        found_opps.extend(arb_opps)
        found_opps.extend(dutch_opps)
        found_opps.extend(mm_opps)
        found_opps.extend(sniping_opps)

        # Persist opportunities to DB
        for opp in found_opps:
            await db.log_opportunity(opp)

        if not found_opps:
            return (
                "### Live Market Scan Results\n"
                f"Scanned **{len(k_markets)} Kalshi markets** and **{len(p_markets)} Polymarket markets**.\n\n"
                "No cross-platform pricing discrepancies exceeded our minimum net edge thresholds right now. "
                "The agent continuously monitors live books in the background."
            )

        # Format top 6 opportunities
        rows = [
            f"### Market Edges Detected ({len(found_opps)} opportunities found)",
            f"*Scanned {len(k_markets)} Kalshi markets & {len(p_markets)} Polymarket markets*",
            "",
            "| Strategy | Market / Description | Net Edge | Actionable |",
            "| :--- | :--- | :---: | :---: |"
        ]

        for opp in found_opps[:6]:
            edge_pct = f"{opp.net_edge * 100:.1f}%"
            rows.append(f"| **{opp.strategy_name.value}** | {opp.description[:55]}... | `{edge_pct}` | {'Yes' if opp.actionable else 'No'} |")

        rows.append("\nTo execute any of these opportunities in realistic paper trading, ask me to *'execute top opportunity'* or *'trade cross arb'*.")
        return "\n".join(rows)

    async def _tool_inspect_market(self, prompt: str) -> str:
        # Extract search query
        query = re.sub(r"(inspect|look up|check market|odds for|search)", "", prompt, flags=re.IGNORECASE).strip()
        if not query:
            query = "mars"

        k_markets = await self.kalshi.fetch_markets(limit=50, active_only=False)
        p_markets = await self.polymarket.fetch_markets(limit=50, active_only=False)

        matches = []
        for m in k_markets + p_markets:
            if query.lower() in m.title.lower() or query.lower() in m.ticker.lower():
                matches.append(m)

        if not matches:
            return f"### Market Inspection\nNo markets found matching `{query}` on Kalshi or Polymarket right now."

        res = [f"### Live Market Quotes for '{query}'"]
        for m in matches[:5]:
            yb = f"${m.yes_bid:.2f}" if m.yes_bid else "N/A"
            ya = f"${m.yes_ask:.2f}" if m.yes_ask else "N/A"
            res.append(
                f"- **[{m.platform.value}]** `{m.ticker}`: **{m.title}**\n"
                f"  - Yes Bid: `{yb}` | Yes Ask: `{ya}` | 24h Vol: `${m.volume_usd:,.0f}`"
            )

        return "\n".join(res)

    async def _tool_handle_risk_settings(self, prompt: str) -> str:
        return (
            "### Risk Management Controls\n"
            f"- **Fractional Kelly Scale**: `{settings.DEFAULT_KELLY_FRACTION}` (Quarter-Kelly conservative capital preservation)\n"
            f"- **Max Position Cap**: `${settings.MAX_POSITION_SIZE_USD:,.2f}` per trade\n"
            f"- **Max Portfolio Exposure**: `{settings.MAX_PORTFOLIO_EXPOSURE*100:.0f}%` (leaves {int((1-settings.MAX_PORTFOLIO_EXPOSURE)*100)}% dry powder)\n"
            f"- **Circuit Breaker Drawdown Limit**: `{settings.MAX_DRAWDOWN_LIMIT*100:.0f}%`\n"
            f"- **Arbitrage Net Edge Cutoff**: `{settings.MIN_ARB_NET_EDGE*100:.1f}%` net of all fees"
        )
