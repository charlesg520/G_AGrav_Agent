import os
from pydantic import BaseModel

class SystemConfig(BaseModel):
    # Operating Mode
    IS_SIMULATION_MODE: bool = True
    INITIAL_CAPITAL: float = 100000.0  # $100,000 Starting balance
    
    # Flexible OpenAI-Compatible LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, deepseek, openrouter, ollama, anthropic, gemini
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    # Risk Management Settings
    MAX_POSITION_SIZE_PCT: float = 0.03  # Max 3% per single trade (Phase-A update)
    KELLY_FRACTION: float = 0.35  # Fractional Kelly multiplier
    MAX_DAILY_DRAWDOWN_PCT: float = 0.05  # Max 5% loss per day
    STOP_LOSS_PCT: float = 0.04  # Default 4% stop loss
    TAKE_PROFIT_PCT: float = 0.08  # Default 8% take profit
    LEVERAGE_LIMIT: float = 3.0  # Max leverage for crypto perps
    
    # Active Strategies
    ENABLE_PREDICTION_ARBITRAGE: bool = True
    ENABLE_PREDICTION_REASONER: bool = True
    ENABLE_CRYPTO_QUANT: bool = True
    ENABLE_ONCHAIN_MOMENTUM: bool = True
    
    # Execution Settings
    SLIPPAGE_TOLERANCE_BPS: int = 15
    PAPER_SLIPPAGE_SIMULATION_BPS: int = 10
    PAPER_FEE_BPS: int = 5  # 0.05% fee per trade
    
    # Exchange API Connectors
    POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
    HYPERLIQUID_API_KEY: str = os.getenv("HYPERLIQUID_API_KEY", "")
    KALSHI_API_KEY: str = os.getenv("KALSHI_API_KEY", "")

config = SystemConfig()
