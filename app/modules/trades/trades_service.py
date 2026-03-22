from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.shared.db.models import DecisionInsight, ExchangeOrder, Trade


class TradesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.review_days = get_settings().strategy_review_days

    def list_trades(self) -> list[Trade]:
        return list(self.db.scalars(select(Trade).order_by(Trade.created_at.desc()).limit(100)))

    def list_trade_groups(self) -> dict[str, list[Trade]]:
        trades = self.list_trades()
        synced_from_binance: list[Trade] = []
        bot_executed: list[Trade] = []

        for trade in trades:
            rationale = (trade.rationale or "").strip().lower()
            if rationale == "synced from binance spot account history":
                synced_from_binance.append(trade)
            else:
                bot_executed.append(trade)

        return {
            "bot_executed": bot_executed,
            "synced_from_binance": synced_from_binance,
        }

    def get_trade_source_summary(self) -> dict:
        grouped = self.list_trade_groups()
        bot_executed = grouped["bot_executed"]
        synced_from_binance = grouped["synced_from_binance"]

        def summarize(items: list[Trade]) -> dict:
            gross_notional = sum((item.price or 0) * (item.quantity or 0) for item in items)
            return {
                "count": len(items),
                "gross_notional": round(gross_notional, 2),
            }

        return {
            "bot_executed": summarize(bot_executed),
            "synced_from_binance": summarize(synced_from_binance),
            "total_count": len(bot_executed) + len(synced_from_binance),
        }

    def list_exchange_orders(self) -> list[ExchangeOrder]:
        return list(
            self.db.scalars(
                select(ExchangeOrder).order_by(ExchangeOrder.updated_at.desc()).limit(100)
            )
        )

    def list_decision_insights(self) -> list[DecisionInsight]:
        return list(
            self.db.scalars(
                select(DecisionInsight).order_by(DecisionInsight.updated_at.desc()).limit(100)
            )
        )

    def get_bot_quality_summary(self) -> dict:
        window_start = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=self.review_days)
        insights = [
            item for item in self.list_decision_insights()
            if item.created_at >= window_start
        ]
        if not insights:
            return {
                "window_days": self.review_days,
                "total_decisions": 0,
                "actionable_decisions": 0,
                "approved_count": 0,
                "blocked_count": 0,
                "trade_actions": 0,
                "resolved_count": 0,
                "wins": 0,
                "losses": 0,
                "pending": 0,
                "positive_ev_pending": 0,
                "negative_ev_pending": 0,
                "no_setup_pending": 0,
                "approval_rate": 0.0,
                "trade_action_rate": 0.0,
                "win_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_pnl": 0.0,
                "verdict": "Sem dados suficientes no trimestre",
            }

        approved_count = sum(1 for item in insights if item.approved)
        blocked_count = len(insights) - approved_count
        trade_actions = sum(1 for item in insights if item.action == "TRADE")
        actionable_decisions = 0
        wins = sum(1 for item in insights if item.outcome_label == "WIN")
        losses = sum(1 for item in insights if item.outcome_label == "LOSS")
        pending = sum(1 for item in insights if item.outcome_label == "PENDING")
        resolved_count = wins + losses
        avg_confidence = sum(item.confidence for item in insights) / len(insights)
        positive_ev_pending = 0
        negative_ev_pending = 0
        no_setup_pending = 0

        for item in insights:
            payload = item.raw_payload or {}
            thesis = payload.get("thesis") or {}
            stats = thesis.get("stats") or {}
            setup_id = thesis.get("setup_id")
            ev = float(stats.get("expectancy_pct") or 0)

            if setup_id:
                actionable_decisions += 1

            if item.outcome_label != "PENDING":
                continue

            if not setup_id:
                no_setup_pending += 1
            elif ev > 0:
                positive_ev_pending += 1
            else:
                negative_ev_pending += 1

        resolved_pnls = [
            (item.realized_pnl or 0) + (item.unrealized_pnl or 0)
            for item in insights
            if item.outcome_label in {"WIN", "LOSS"}
        ]
        avg_pnl = sum(resolved_pnls) / len(resolved_pnls) if resolved_pnls else 0.0

        approval_rate = (approved_count / len(insights)) * 100 if insights else 0.0
        trade_action_rate = (trade_actions / len(insights)) * 100 if insights else 0.0
        win_rate = (wins / resolved_count) * 100 if resolved_count else 0.0

        if actionable_decisions == 0:
            verdict = "Trimestre sem setups acionaveis"
        elif resolved_count == 0 and positive_ev_pending > 0:
            verdict = "Trimestre em observacao, com setups favoraveis pendentes"
        elif resolved_count == 0:
            verdict = "Coletando historico trimestral para avaliar"
        elif win_rate >= 60:
            verdict = "Trimestre forte ate aqui"
        elif win_rate >= 45:
            verdict = "Trimestre misto, precisa acompanhar"
        else:
            verdict = "Trimestre fraco, vale revisar estrategia"

        return {
            "window_days": self.review_days,
            "total_decisions": len(insights),
            "actionable_decisions": actionable_decisions,
            "approved_count": approved_count,
            "blocked_count": blocked_count,
            "trade_actions": trade_actions,
            "resolved_count": resolved_count,
            "wins": wins,
            "losses": losses,
            "pending": pending,
            "positive_ev_pending": positive_ev_pending,
            "negative_ev_pending": negative_ev_pending,
            "no_setup_pending": no_setup_pending,
            "approval_rate": round(approval_rate, 2),
            "trade_action_rate": round(trade_action_rate, 2),
            "win_rate": round(win_rate, 2),
            "avg_confidence": round(avg_confidence, 2),
            "avg_pnl": round(avg_pnl, 2),
            "verdict": verdict,
        }

    def get_decision_blockers_summary(self) -> list[dict]:
        window_start = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=self.review_days)
        insights = [
            item for item in self.list_decision_insights()
            if item.created_at >= window_start
        ]
        buckets: dict[str, int] = {}

        for item in insights:
            payload = item.raw_payload or {}
            thesis = payload.get("thesis") or {}
            risk = payload.get("risk") or {}
            warnings = risk.get("warnings") or []
            setup_id = thesis.get("setup_id")
            stats = thesis.get("stats") or {}

            reason = "Trade executado"
            if item.action != "TRADE":
                if warnings:
                    reason = warnings[0]
                elif not setup_id:
                    reason = "Sem setup ativo no candle"
                elif not bool(stats.get("enabled", True)):
                    reason = stats.get("disable_reason") or "Setup trimestral desativado"
                else:
                    reason = "Decisao terminou em no-trade"

            buckets[reason] = buckets.get(reason, 0) + 1

        return [
            {"reason": reason, "count": count}
            for reason, count in sorted(buckets.items(), key=lambda item: item[1], reverse=True)
        ]
