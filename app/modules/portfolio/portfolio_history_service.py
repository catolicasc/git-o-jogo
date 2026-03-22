from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.integrations.binance.binance_client import BinanceClient
from app.shared.db.models import PortfolioSnapshot

from .performance_service import PerformanceService


class PortfolioHistoryService:
    def __init__(
        self,
        db: Session,
        performance_service: PerformanceService,
        binance_client: BinanceClient,
    ) -> None:
        self.db = db
        self.performance_service = performance_service
        self.binance_client = binance_client
        self.settings = get_settings()

    def record_snapshot_if_due(
        self,
        *,
        note: str = "auto",
        min_interval_minutes: int = 10,
    ) -> PortfolioSnapshot:
        latest = self.db.scalar(
            select(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.created_at.desc())
            .limit(1)
        )
        if latest is not None and latest.created_at >= datetime.utcnow() - timedelta(minutes=min_interval_minutes):
            return latest

        summary = self.performance_service.get_summary()
        usd_brl_rate = self._get_usd_brl_rate()
        snapshot = PortfolioSnapshot(
            mode=self.settings.app_mode,
            equity_usd=summary["equity"],
            equity_brl=summary["equity"] * usd_brl_rate,
            cash_balance_usd=summary["cash_balance"],
            inventory_value_usd=summary["inventory_value"],
            usd_brl_rate=usd_brl_rate,
            valuation_source=summary.get("valuation_source"),
            note=note,
            raw_payload=summary,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def get_history(self, *, limit: int = 200) -> dict:
        snapshots = list(
            self.db.scalars(
                select(PortfolioSnapshot)
                .order_by(PortfolioSnapshot.created_at.asc())
                .limit(limit)
            )
        )

        if not snapshots:
            return {
                "summary": {
                    "starting_brl": 0.0,
                    "current_brl": 0.0,
                    "change_brl": 0.0,
                    "change_pct": 0.0,
                    "starting_usd": 0.0,
                    "current_usd": 0.0,
                },
                "points": [],
            }

        starting = snapshots[0]
        current = snapshots[-1]
        change_brl = current.equity_brl - starting.equity_brl
        change_pct = (change_brl / starting.equity_brl) * 100 if starting.equity_brl else 0.0

        return {
            "summary": {
                "starting_brl": round(starting.equity_brl, 2),
                "current_brl": round(current.equity_brl, 2),
                "change_brl": round(change_brl, 2),
                "change_pct": round(change_pct, 2),
                "starting_usd": round(starting.equity_usd, 2),
                "current_usd": round(current.equity_usd, 2),
                "points": len(snapshots),
            },
            "points": [
                {
                    "timestamp": snapshot.created_at.isoformat(),
                    "equity_usd": round(snapshot.equity_usd, 2),
                    "equity_brl": round(snapshot.equity_brl, 2),
                    "cash_balance_usd": round(snapshot.cash_balance_usd, 2),
                    "inventory_value_usd": round(snapshot.inventory_value_usd, 2),
                    "usd_brl_rate": round(snapshot.usd_brl_rate, 4),
                    "valuation_source": snapshot.valuation_source,
                    "note": snapshot.note,
                }
                for snapshot in snapshots
            ],
        }

    def _get_usd_brl_rate(self) -> float:
        all_prices = self.binance_client.get_all_prices()
        direct = all_prices.get("USDTBRL")
        if direct and direct > 0:
            return direct

        inverse = all_prices.get("BRLUSDT")
        if inverse and inverse > 0:
            return 1 / inverse

        return 1.0
