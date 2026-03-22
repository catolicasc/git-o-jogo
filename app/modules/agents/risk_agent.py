from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.shared.db.models import Position, RiskEvaluation, Trade
from app.shared.types.domain import MarketContext, ResearchThesis, RiskEvaluationResult


class RiskAgent:
    def __init__(self, db: Session, mode: str) -> None:
        self.db = db
        self.mode = mode
        self.settings = get_settings()

    def get_daily_trade_usd_total(self) -> float:
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        trades = list(
            self.db.scalars(
                select(Trade).where(Trade.created_at >= start_of_day, Trade.status == "FILLED")
            )
        )
        return sum(trade.price * trade.quantity for trade in trades)

    def evaluate(
        self,
        *,
        symbol: str,
        thesis: ResearchThesis,
        market: MarketContext,
        daily_trade_usd: float,
        account_balances: dict[str, dict[str, float]] | None = None,
        symbol_assets: dict[str, str] | None = None,
        symbol_on_cooldown: bool = False,
    ) -> RiskEvaluationResult:
        warnings: list[str] = []
        approved = True
        stats = thesis.stats or {}
        effective_bankroll_usd = self._effective_bankroll_usd(
            account_balances=account_balances,
            symbol_assets=symbol_assets,
        )
        max_usd_exposure = effective_bankroll_usd * self.settings.max_risk_per_trade
        sample_size = int(stats.get("trades") or 0)
        win_probability = float(stats.get("win_probability") or thesis.confidence)
        payoff_ratio = float(stats.get("payoff_ratio") or 0)
        expected_value_pct = float(stats.get("expectancy_pct") or 0)
        raw_kelly_fraction = float(stats.get("kelly_fraction") or 0)
        position_size_fraction = min(
            self.settings.max_risk_per_trade,
            max(0.0, raw_kelly_fraction * self.settings.kelly_fraction_multiplier),
        )
        position_notional_usd = effective_bankroll_usd * position_size_fraction
        desired_quantity = position_notional_usd / market.price if market.price > 0 else 0

        if thesis.direction != "NONE" and sample_size < self.settings.strategy_min_sample_size:
            approved = False
            warnings.append(
                f"Insufficient setup sample size ({sample_size}/{self.settings.strategy_min_sample_size})"
            )

        if thesis.direction != "NONE" and expected_value_pct <= 0:
            approved = False
            warnings.append("Expected value is non-positive for this setup and regime")

        if thesis.direction != "NONE" and position_size_fraction <= 0:
            approved = False
            warnings.append("Fractional Kelly sizing returned zero notional")

        if thesis.confidence < 0.70 and thesis.direction != "NONE":
            approved = False
            warnings.append("Confidence below minimum threshold of 0.70")

        if symbol not in self.settings.symbols:
            approved = False
            warnings.append("Symbol not present in allowlist")

        if daily_trade_usd >= effective_bankroll_usd * 0.05:
            approved = False
            warnings.append("Daily notional limit reached")

        open_position = self.db.scalar(select(Position).where(Position.symbol == symbol).limit(1))
        if open_position is not None and thesis.direction == "BUY" and open_position.status == "OPEN":
            approved = False
            warnings.append("Position already open for symbol")

        bids = market.order_book.get("bids", []) if market.order_book else []
        asks = market.order_book.get("asks", []) if market.order_book else []
        top_bid_qty = float(bids[0][1]) if bids else 0
        top_ask_qty = float(asks[0][1]) if asks else 0
        if top_bid_qty < 0.01 or top_ask_qty < 0.01:
            approved = False
            warnings.append("Insufficient top-of-book liquidity")

        if symbol_on_cooldown:
            approved = False
            warnings.append("Symbol is on cooldown after recent trade")

        total_symbol_position = (
            (open_position.quantity * market.price)
            if open_position is not None and open_position.quantity > 0
            else 0
        )
        if total_symbol_position > effective_bankroll_usd * self.settings.max_symbol_exposure_pct:
            approved = False
            warnings.append("Symbol exposure limit reached")

        if (
            open_position is not None
            and open_position.quantity > 0
            and open_position.average_price > 0
        ):
            drawdown = (market.price - open_position.average_price) / open_position.average_price
            if drawdown <= -self.settings.stop_loss_pct and thesis.direction != "SELL":
                approved = False
                warnings.append("Stop loss level reached, only SELL decisions are allowed")
            if drawdown >= self.settings.take_profit_pct and thesis.direction == "BUY":
                approved = False
                warnings.append("Take profit zone reached, avoid adding more exposure")

        if self.mode == "live" and account_balances is not None and symbol_assets is not None:
            quote_balance = account_balances.get(symbol_assets["quote_asset"], {}).get("free", 0)
            base_balance = account_balances.get(symbol_assets["base_asset"], {}).get("free", 0)

            if thesis.direction == "BUY" and quote_balance < position_notional_usd:
                approved = False
                warnings.append(
                    f"Insufficient {symbol_assets['quote_asset']} balance for live BUY"
                )

            if thesis.direction == "SELL" and base_balance < desired_quantity:
                approved = False
                warnings.append(
                    f"Insufficient {symbol_assets['base_asset']} balance for live SELL"
                )

        rationale = (
            "Risk checks approved the thesis for execution."
            if approved
            else f"Risk checks blocked the thesis: {'; '.join(warnings)}"
        )
        rationale = (
            f"{rationale} pwin={win_probability:.2f} payoff={payoff_ratio:.2f} "
            f"ev={expected_value_pct:.2f}% kelly={raw_kelly_fraction:.2f} "
            f"fractional_size={position_size_fraction:.4f} samples={sample_size}."
        )

        result = RiskEvaluationResult(
            approved=approved,
            final_action="TRADE" if approved else "NO_TRADE",
            max_usd_exposure=max_usd_exposure,
            position_notional_usd=position_notional_usd,
            position_size_fraction=position_size_fraction,
            win_probability=win_probability,
            payoff_ratio=payoff_ratio,
            expected_value_pct=expected_value_pct,
            kelly_fraction=raw_kelly_fraction,
            sample_size=sample_size,
            warnings=warnings,
            rationale=rationale,
        )

        self.db.add(
            RiskEvaluation(
                symbol=symbol,
                approved=result.approved,
                final_action=result.final_action,
                max_usd_exposure=result.max_usd_exposure,
                warnings=result.warnings,
                rationale=result.rationale,
                mode=self.mode,
                raw_payload={
                    "symbol": symbol,
                    "thesis": thesis.model_dump(),
                    "market": market.model_dump(),
                    "daily_trade_usd": daily_trade_usd,
                    "account_balances": account_balances,
                    "symbol_assets": symbol_assets,
                    "symbol_on_cooldown": symbol_on_cooldown,
                    "result": result.model_dump(),
                },
            )
        )
        self.db.commit()
        return result

    def _effective_bankroll_usd(
        self,
        *,
        account_balances: dict[str, dict[str, float]] | None,
        symbol_assets: dict[str, str] | None,
    ) -> float:
        if self.mode != "live" or account_balances is None:
            return self.settings.default_bankroll_usd

        quote_asset = "USDT"
        if symbol_assets is not None:
            quote_asset = symbol_assets.get("quote_asset", quote_asset)

        quote_free = account_balances.get(quote_asset, {}).get("free", 0)
        return quote_free if quote_free > 0 else self.settings.default_bankroll_usd
