"""
Configuration settings for the Prediction Market Quant & Paper-Trading Agent.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Trading Execution Mode
    TRADING_MODE: Literal["PAPER", "LIVE"] = "PAPER"
    CONFIRM_LIVE_TRADING: bool = False  # Safety lock for future live trading
    
    # Paper Trading Balance
    INITIAL_PAPER_BALANCE: float = 10000.0  # USD / USDC
    
    # Persistence
    DB_PATH: Path = BASE_DIR / "prediction_agent.db"
    
    # Market Endpoints (Public APIs for market data and orderbooks)
    KALSHI_API_BASE: str = "https://api.elections.kalshi.com/trade-api/v2"
    POLYMARKET_GAMMA_BASE: str = "https://gamma-api.polymarket.com"
    POLYMARKET_CLOB_BASE: str = "https://clob.polymarket.com"
    
    # Live Trading Credentials (Optional, only used when TRADING_MODE='LIVE')
    KALSHI_API_KEY: str = ""
    KALSHI_PRIVATE_KEY_PATH: str = ""
    POLYMARKET_PRIVATE_KEY: str = ""
    POLYMARKET_API_KEY: str = ""
    POLYMARKET_API_SECRET: str = ""
    POLYMARKET_PASSPHRASE: str = ""
    
    # Risk Management Settings
    DEFAULT_KELLY_FRACTION: float = 0.25     # Quarter-Kelly for conservative capital preservation
    MAX_POSITION_SIZE_USD: float = 500.0     # Maximum allocated to any single trade
    MAX_PORTFOLIO_EXPOSURE: float = 0.70     # Keep at least 30% as dry powder cash
    MAX_DRAWDOWN_LIMIT: float = 0.15         # Circuit breaker: stop opening new trades if drawdown > 15%
    
    # Strategy Thresholds
    MIN_ARB_NET_EDGE: float = 0.015          # Minimum 1.5% edge after all fees for cross-market arb
    MIN_DUTCH_BOOK_EDGE: float = 0.020       # Minimum 2.0% profit for Dutch book baskets
    MIN_MM_SPREAD: float = 0.040             # Minimum 4.0c spread to quote market-making orders
    CONVERGENCE_MIN_PROBABILITY: float = 0.96 # Sniping threshold for near-certain resolution
    
    # Web Dashboard & API
    DASHBOARD_HOST: str = "127.0.0.1"
    DASHBOARD_PORT: int = 8000
    
    # Multi-Provider LLM Settings for Conversational Assistant
    # Supports: "heuristic", "openai", "anthropic", "deepseek", "groq", "gemini", "ollama", "openrouter"
    LLM_PROVIDER: Literal[
        "heuristic", "openai", "anthropic", "deepseek", "groq", "gemini", "ollama", "openrouter"
    ] = "heuristic"
    LLM_MODEL: str = ""                      # e.g. "gpt-4o", "claude-3-5-sonnet", "deepseek-chat", "llama3.2"
    
    # Provider API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    
    # Custom / Local Endpoint (Ollama or OpenAI-compatible endpoint)
    OPENAI_BASE_URL: str = ""                # e.g. for vLLM, OpenRouter, LocalAI
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
