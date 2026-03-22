from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.integrations.binance.binance_client import BinanceClient
from app.shared.db.models import DecisionInsight, ExchangeOrder, Position, Trade


class ReconciliationService:
    def __init__(self, db: Session, binance_client: BinanceClient, mode: str) -> None:
        self.db = db
        self.binance_client = binance_client
        self.mode = mode
        self.settings = get_settings()

    def sync_exchange_state(self, symbols: list[str]) -> dict:
        synced_orders = 0
        synced_trades = 0

        for symbol in symbols:
            open_orders = self.binance_client.get_open_orders(symbol)
            order_history = self.binance_client.get_all_orders(symbol, limit=20)
            recent_trades = self.binance_client.get_my_trades(symbol, limit=20)

            for order in open_orders + order_history:
                self._upsert_exchange_order(order, symbol)
                synced_orders += 1

            for trade in recent_trades:
                self._sync_trade_from_exchange(trade, symbol)
                synced_trades += 1

        self._refresh_decision_outcomes()
        return {
            "synced_orders": synced_orders,
            "synced_trades": synced_trades,
            "symbols": symbols,
        }

    def _upsert_exchange_order(self, payload: dict, symbol: str) -> None:
        exchange_order_id = str(payload.get("orderId"))
        existing = self.db.scalar(
            select(ExchangeOrder)
            .where(ExchangeOrder.exchange_order_id == exchange_order_id)
            .limit(1)
        )
        if existing is None:
            existing = ExchangeOrder(
                exchange_order_id=exchange_order_id,
                symbol=symbol,
                mode=self.mode,
            )
            self.db.add(existing)

        existing.side = payload.get("side")
        existing.order_type = payload.get("type")
        existing.status = payload.get("status")
        existing.price = float(payload.get("price") or 0)
        existing.orig_qty = float(payload.get("origQty") or 0)
        existing.executed_qty = float(payload.get("executedQty") or 0)
        existing.raw_payload = payload
        self.db.commit()

    def _sync_trade_from_exchange(self, payload: dict, symbol: str) -> None:
        order_id = str(payload.get("orderId"))
        existing = self.db.scalar(
            select(Trade)
            .where(Trade.raw_payload["orderId"].as_string() == order_id)
            .limit(1)
        )
        if existing is None:
            existing = Trade(
                symbol=symbol,
                side="BUY" if payload.get("isBuyer") else "SELL",
                price=float(payload.get("price") or 0),
                quantity=float(payload.get("qty") or 0),
                status="FILLED",
                rationale="Synced from Binance Spot account history",
                mode=self.mode,
                confidence=None,
                raw_payload=payload,
            )
            self.db.add(existing)
            self.db.commit()

    def create_decision_insight(
        self,
        *,
        symbol: str,
        thesis_direction: str,
        approved: bool,
        action: str,
        confidence: float,
        entry_price: float,
        raw_payload: dict,
    ) -> None:
        insight = DecisionInsight(
            symbol=symbol,
            mode=self.mode,
            thesis_direction=thesis_direction,
            approved=approved,
            action=action,
            confidence=confidence,
            entry_price=entry_price,
            current_price=entry_price,
            realized_pnl=0,
            unrealized_pnl=0,
            outcome_label="PENDING",
            raw_payload=raw_payload,
        )
        self.db.add(insight)
        self.db.commit()

    def _refresh_decision_outcomes(self) -> None:
        insights = list(self.db.scalars(select(DecisionInsight)))
        positions = {
            position.symbol: position
            for position in self.db.scalars(select(Position))
        }

        for insight in insights:
            position = positions.get(insight.symbol)
            if position is None:
                continue

            insight.current_price = position.current_price or insight.entry_price
            insight.realized_pnl = position.realized_pnl or 0
            insight.unrealized_pnl = position.unrealized_pnl or 0
            pnl_total = (insight.realized_pnl or 0) + (insight.unrealized_pnl or 0)

            if pnl_total >= insight.entry_price * self.settings.take_profit_pct:
                insight.outcome_label = "WIN"
            elif pnl_total <= -(insight.entry_price * self.settings.stop_loss_pct):
                insight.outcome_label = "LOSS"
            else:
                insight.outcome_label = "PENDING"

        self.db.commit()

    def get_latest_symbol_trade_time(self, symbol: str) -> datetime | None:
        trade = self.db.scalar(
            select(Trade).where(Trade.symbol == symbol).order_by(Trade.created_at.desc()).limit(1)
        )
        return trade.created_at if trade else None

    def is_symbol_on_cooldown(self, symbol: str) -> bool:
        latest_trade_time = self.get_latest_symbol_trade_time(symbol)
        if latest_trade_time is None:
            return False

        cooldown_until = latest_trade_time + timedelta(minutes=self.settings.symbol_cooldown_minutes)
        return datetime.utcnow() < cooldown_until
