"""
Main CLI and server runner for the Prediction Market Quant & Paper-Trading Agent.
"""

import sys
import argparse
import asyncio
import uvicorn

from prediction_agent.config import settings

def main():
    parser = argparse.ArgumentParser(description="Prediction Market Quant & Paper-Trading Agent")
    parser.add_argument("--server", action="store_true", help="Launch the Web Dashboard and API server")
    parser.add_argument("--cli", action="store_true", help="Display the Rich terminal portfolio dashboard")
    parser.add_argument("--scan", action="store_true", help="Run a live market scan for arbitrage and edges")
    parser.add_argument("--chat", action="store_true", help="Start an interactive terminal chat with the agent")

    args = parser.parse_args()

    if args.cli:
        from prediction_agent.ui.cli import run_cli_dashboard
        asyncio.run(run_cli_dashboard())
    elif args.chat:
        from prediction_agent.ui.cli import run_terminal_chat
        asyncio.run(run_terminal_chat())
    elif args.scan:
        async def do_scan():
            from prediction_agent.agent.assistant import TradingAgentAssistant
            from prediction_agent.database.db import db
            await db.init_db()
            assistant = TradingAgentAssistant()
            print("Scanning live Kalshi and Polymarket orderbooks...")
            res = await assistant._tool_scan_opportunities("")
            print("\n" + res)
        asyncio.run(do_scan())
    else:
        # Default: Launch Web Dashboard
        print(f"Starting Prediction Market Quant Dashboard at http://{settings.DASHBOARD_HOST}:{settings.DASHBOARD_PORT}")
        uvicorn.run(
            "prediction_agent.ui.server:app",
            host=settings.DASHBOARD_HOST,
            port=settings.DASHBOARD_PORT,
            reload=False
        )

if __name__ == "__main__":
    main()
