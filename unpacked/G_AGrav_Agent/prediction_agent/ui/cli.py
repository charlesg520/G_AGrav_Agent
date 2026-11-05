"""
Interactive Terminal UI for the Prediction Market Quant Agent using Rich.
"""

import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

from prediction_agent.database.db import db
from prediction_agent.agent.assistant import TradingAgentAssistant
from prediction_agent.analytics.quant_metrics import QuantMetricsCalculator

console = Console()

async def run_cli_dashboard():
    assistant = TradingAgentAssistant()
    await db.init_db()

    console.clear()
    console.print(Panel(
        Text("AceSammy Prediction Market Quant Agent\nKalshi & Polymarket Paper Trader", justify="center", style="bold cyan"),
        subtitle="[dim]Press Ctrl+C to exit[/dim]"
    ))

    # Fetch live data
    balance = await db.get_account_balance()
    trades = await db.get_trades(limit=10)
    positions = await db.get_positions()
    snapshots = await db.get_portfolio_history(limit=50)
    metrics = QuantMetricsCalculator.calculate_metrics(snapshots, trades)

    # Balance summary table
    bal_table = Table(title="Portfolio Ledger Summary", show_header=True, header_style="bold magenta")
    bal_table.add_column("Total Equity", style="bold green")
    bal_table.add_column("Cash Available", style="cyan")
    bal_table.add_column("Invested Capital", style="blue")
    bal_table.add_column("Realized PnL", style="yellow")
    bal_table.add_column("Sharpe Ratio", style="purple")
    bal_table.add_column("Win Rate", style="magenta")

    bal_table.add_row(
        f"${balance.total_equity:,.2f}",
        f"${balance.cash_balance:,.2f}",
        f"${balance.invested_capital:,.2f}",
        f"${balance.realized_pnl:+,.2f}",
        f"{metrics['sharpe_ratio']:.2f}",
        f"{metrics['win_rate']*100:.1f}%"
    )
    console.print(bal_table)
    console.print()

    # Positions table
    pos_table = Table(title=f"Open Positions ({len(positions)})", show_header=True, header_style="bold blue")
    pos_table.add_column("Platform")
    pos_table.add_column("Market")
    pos_table.add_column("Side")
    pos_table.add_column("Qty")
    pos_table.add_column("Avg Price")
    pos_table.add_column("Unrealized PnL")

    if positions:
        for p in positions:
            pnl_style = "green" if p.unrealized_pnl >= 0 else "red"
            pos_table.add_row(
                p.platform.value,
                p.market_title[:35],
                p.outcome.value,
                str(p.quantity),
                f"${p.avg_entry_price:.3f}",
                Text(f"{p.unrealized_pnl:+,.2f}", style=pnl_style)
            )
    else:
        pos_table.add_row("-", "No open positions", "-", "-", "-", "-")

    console.print(pos_table)
    console.print()

async def run_terminal_chat():
    assistant = TradingAgentAssistant()
    await db.init_db()

    session_id = "terminal_chat_main"
    console.print("[bold green]Connected to Prediction Market Quant Assistant.[/bold green]")
    console.print("[dim]Type your question or 'exit' to quit. Examples: 'portfolio', 'scan', 'inspect Fed', 'positions'.[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]You > [/bold cyan]").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                break

            response = await assistant.chat(session_id, user_input)
            console.print(f"\n[bold green]Agent >[/bold green]\n{response}\n")
        except (KeyboardInterrupt, EOFError):
            break
