from typing import Literal

from pydantic import BaseModel, Field


class ResearchThesis(BaseModel):
    symbol: str
    direction: Literal["BUY", "SELL", "NONE"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    source_urls: list[str] = Field(default_factory=list)
    setup_id: str | None = None
    regime: str | None = None
    stats: dict = Field(default_factory=dict)
    auxiliary_context: dict = Field(default_factory=dict)


class RiskEvaluationResult(BaseModel):
    approved: bool
    final_action: Literal["TRADE", "NO_TRADE"]
    max_usd_exposure: float
    position_notional_usd: float = 0
    position_size_fraction: float = 0
    win_probability: float = 0
    payoff_ratio: float = 0
    expected_value_pct: float = 0
    kelly_fraction: float = 0
    sample_size: int = 0
    warnings: list[str] = Field(default_factory=list)
    rationale: str


class TradeDecision(BaseModel):
    should_trade: bool
    action: Literal["TRADE", "NO_TRADE"]
    side: Literal["BUY", "SELL"] | None = None
    symbol: str
    confidence: float
    quantity: float
    price: float
    rationale: str
    warnings: list[str] = Field(default_factory=list)


class MarketContext(BaseModel):
    symbol: str
    price: float
    bid_price: float | None = None
    ask_price: float | None = None
    spread: float | None = None
    volume_24h: float | None = None
    order_book: dict | None = None
    klines: list | None = None
    indicators: dict | None = None
    macro: dict | None = None


class NewsContext(BaseModel):
    symbol: str | None = None
    title: str
    summary: str | None = None
    url: str
    source: str
    published_at: str


class ExecutionRequest(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    price: float
    quantity: float
    rationale: str
    confidence: float
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"


class ExecutionResult(BaseModel):
    status: Literal["FILLED", "REJECTED", "FAILED", "NEW", "PARTIALLY_FILLED"]
    external_id: str | None = None
    message: str
    raw_payload: dict | None = None
