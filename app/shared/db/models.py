from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Float)
    bid_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    order_book: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    klines: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), unique=True)
    source: Mapped[str] = mapped_column(String(100))
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Thesis(Base):
    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    source_urls: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(16))
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class RiskEvaluation(Base):
    __tablename__ = "risk_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    approved: Mapped[bool] = mapped_column(Boolean)
    final_action: Mapped[str] = mapped_column(String(16))
    max_usd_exposure: Mapped[float] = mapped_column(Float)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(16))
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True)
    quantity: Mapped[float] = mapped_column(Float)
    average_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(16))
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ExchangeOrder(Base):
    __tablename__ = "exchange_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange_order_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    order_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    orig_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    executed_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[str] = mapped_column(String(16))
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class DecisionInsight(Base):
    __tablename__ = "decision_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(16))
    thesis_direction: Mapped[str] = mapped_column(String(16))
    approved: Mapped[bool] = mapped_column(Boolean)
    action: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_label: Mapped[str | None] = mapped_column(String(24), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    equity_usd: Mapped[float] = mapped_column(Float)
    equity_brl: Mapped[float] = mapped_column(Float)
    cash_balance_usd: Mapped[float] = mapped_column(Float)
    inventory_value_usd: Mapped[float] = mapped_column(Float)
    usd_brl_rate: Mapped[float] = mapped_column(Float)
    valuation_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
