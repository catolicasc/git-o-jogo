from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_port: int = Field(default=3000, alias="APP_PORT")
    node_env: str = Field(default="development", alias="NODE_ENV")
    app_mode: str = Field(default="paper", alias="APP_MODE")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/trading_agent",
        alias="DATABASE_URL",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    binance_api_key: str | None = Field(default=None, alias="BINANCE_API_KEY")
    binance_api_secret: str | None = Field(default=None, alias="BINANCE_API_SECRET")
    binance_base_url: str = Field(default="https://api.binance.com", alias="BINANCE_BASE_URL")
    binance_ws_url: str = Field(
        default="wss://stream.binance.com:9443/ws", alias="BINANCE_WS_URL"
    )
    enable_live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")
    symbol_allowlist: str = Field(default="BTCUSDT,ETHUSDT", alias="SYMBOL_ALLOWLIST")
    default_bankroll_usd: float = Field(default=10000, alias="DEFAULT_BANKROLL_USD")
    max_risk_per_trade: float = Field(default=0.01, alias="MAX_RISK_PER_TRADE")
    news_provider_api_key: str | None = Field(default=None, alias="NEWS_PROVIDER_API_KEY")
    symbol_cooldown_minutes: int = Field(default=60, alias="SYMBOL_COOLDOWN_MINUTES")
    stop_loss_pct: float = Field(default=0.03, alias="STOP_LOSS_PCT")
    take_profit_pct: float = Field(default=0.05, alias="TAKE_PROFIT_PCT")
    max_symbol_exposure_pct: float = Field(default=0.20, alias="MAX_SYMBOL_EXPOSURE_PCT")
    strategy_backtest_interval: str = Field(default="4h", alias="STRATEGY_BACKTEST_INTERVAL")
    strategy_backtest_limit: int = Field(default=1000, alias="STRATEGY_BACKTEST_LIMIT")
    strategy_max_holding_bars: int = Field(default=16, alias="STRATEGY_MAX_HOLDING_BARS")
    strategy_min_sample_size: int = Field(default=8, alias="STRATEGY_MIN_SAMPLE_SIZE")
    strategy_min_profit_factor: float = Field(default=1.05, alias="STRATEGY_MIN_PROFIT_FACTOR")
    kelly_fraction_multiplier: float = Field(default=0.25, alias="KELLY_FRACTION_MULTIPLIER")
    strategy_review_days: int = Field(default=90, alias="STRATEGY_REVIEW_DAYS")
    reconciliation_window_hours: int = Field(default=24, alias="RECONCILIATION_WINDOW_HOURS")
    news_rss_urls: str = Field(
        default="https://www.coindesk.com/arc/outboundfeeds/rss/,https://cointelegraph.com/rss",
        alias="NEWS_RSS_URLS",
    )
    evolution_api_base_url: str | None = Field(default=None, alias="EVOLUTION_API_BASE_URL")
    evolution_api_key: str | None = Field(default=None, alias="EVOLUTION_API_KEY")
    evolution_api_instance: str | None = Field(default=None, alias="EVOLUTION_API_INSTANCE")
    evolution_allowed_number: str = Field(default="999045076", alias="EVOLUTION_ALLOWED_NUMBER")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def symbols(self) -> list[str]:
        return list(
            dict.fromkeys(
                symbol
                for raw_symbol in self.symbol_allowlist.split(",")
                for symbol in [raw_symbol.strip().upper()]
                if symbol.endswith("USDT") and len(symbol) > 4
            )
        )

    @property
    def rss_urls(self) -> list[str]:
        return [item.strip() for item in self.news_rss_urls.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
