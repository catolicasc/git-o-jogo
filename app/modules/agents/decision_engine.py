from app.shared.types.domain import MarketContext, ResearchThesis, RiskEvaluationResult, TradeDecision


class DecisionEngine:
    def decide(
        self,
        *,
        symbol: str,
        thesis: ResearchThesis,
        risk: RiskEvaluationResult,
        market: MarketContext,
    ) -> TradeDecision:
        if not risk.approved or thesis.direction == "NONE":
            return TradeDecision(
                should_trade=False,
                action="NO_TRADE",
                side=None,
                symbol=symbol,
                confidence=thesis.confidence,
                quantity=0,
                price=market.price,
                rationale=f"{thesis.reasoning} {risk.rationale}".strip(),
                warnings=risk.warnings,
            )

        side = "BUY" if thesis.direction == "BUY" else "SELL"
        quantity = risk.position_notional_usd / market.price if market.price > 0 else 0
        return TradeDecision(
            should_trade=True,
            action="TRADE",
            side=side,
            symbol=symbol,
            confidence=thesis.confidence,
            quantity=quantity,
            price=market.price,
            rationale=f"{thesis.reasoning} {risk.rationale}".strip(),
            warnings=risk.warnings,
        )
