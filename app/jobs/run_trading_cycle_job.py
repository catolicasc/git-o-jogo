from datetime import datetime

from app.config.settings import get_settings
from app.modules.agents.decision_engine import DecisionEngine
from app.modules.agents.research_agent import ResearchAgent
from app.modules.agents.risk_agent import RiskAgent
from app.modules.audit.audit_service import AuditService
from app.modules.execution.binance_executor import BinanceExecutor
from app.modules.execution.paper_executor import PaperExecutor
from app.modules.markets.markets_service import MarketsService
from app.modules.news.news_service import NewsService
from app.modules.portfolio.account_service import AccountService
from app.modules.portfolio.portfolio_history_service import PortfolioHistoryService
from app.modules.trades.reconciliation_service import ReconciliationService
from app.shared.db.models import JobRun
from app.shared.types.domain import ExecutionRequest, ResearchThesis
from app.shared.utils.time import elapsed_ms


def _order_symbols_for_live_cycle(
    symbols: list[str],
    live_account_balances: dict[str, dict[str, float]] | None,
) -> list[str]:
    if not live_account_balances:
        return symbols

    prioritized: list[str] = []
    remaining = symbols[:]

    # Prefer reducing XRP exposure first when it exists in the account.
    if "XRPUSDT" in remaining and live_account_balances.get("XRP", {}).get("free", 0) > 0:
        prioritized.append("XRPUSDT")
        remaining.remove("XRPUSDT")

    for symbol in symbols:
        if symbol not in remaining:
            continue
        base_asset = symbol.replace("USDT", "")
        if live_account_balances.get(base_asset, {}).get("free", 0) > 0:
            prioritized.append(symbol)
            remaining.remove(symbol)

    return prioritized + remaining


def _maybe_switch_buy_to_sell_for_cash_recovery(
    *,
    symbol: str,
    thesis: ResearchThesis,
    market_price: float,
    live_account_balances: dict[str, dict[str, float]] | None,
    symbol_assets: dict[str, str] | None,
    default_bankroll_usd: float,
    max_risk_per_trade: float,
) -> ResearchThesis:
    if thesis.direction != "BUY" or not live_account_balances or not symbol_assets:
        return thesis

    quote_asset = symbol_assets["quote_asset"]
    base_asset = symbol_assets["base_asset"]
    quote_free = live_account_balances.get(quote_asset, {}).get("free", 0)
    base_free = live_account_balances.get(base_asset, {}).get("free", 0)
    max_usd_exposure = default_bankroll_usd * max_risk_per_trade
    base_notional = base_free * market_price

    if quote_free >= max_usd_exposure or base_notional < max_usd_exposure * 0.25:
        return thesis

    return ResearchThesis(
        symbol=symbol,
        direction="SELL",
        confidence=max(thesis.confidence, 0.74),
        reasoning=(
            f"{thesis.reasoning} Cash recovery mode active: "
            f"insufficient {quote_asset} for BUY and available {base_asset} position detected, "
            "switching thesis to SELL to free quote balance."
        ),
        source_urls=thesis.source_urls,
    )


def _effective_live_bankroll_usd(
    live_account_balances: dict[str, dict[str, float]] | None,
    symbol_assets: dict[str, str] | None,
    default_bankroll_usd: float,
) -> float:
    if not live_account_balances:
        return default_bankroll_usd

    quote_asset = "USDT"
    if symbol_assets is not None:
        quote_asset = symbol_assets.get("quote_asset", quote_asset)

    quote_free = live_account_balances.get(quote_asset, {}).get("free", 0)
    return quote_free if quote_free > 0 else default_bankroll_usd


def run_trading_cycle(
    *,
    mode: str,
    markets_service: MarketsService,
    news_service: NewsService,
    research_agent: ResearchAgent,
    risk_agent: RiskAgent,
    decision_engine: DecisionEngine,
    audit_service: AuditService,
    paper_executor: PaperExecutor,
    binance_executor: BinanceExecutor | None = None,
    account_service: AccountService | None = None,
    portfolio_history_service: PortfolioHistoryService | None = None,
    reconciliation_service: ReconciliationService | None = None,
) -> dict:
    started_at = datetime.utcnow()
    db = markets_service.db
    job_run = JobRun(job_name="run-trading-cycle", status="RUNNING", mode=mode, started_at=started_at)
    db.add(job_run)
    db.commit()
    settings = get_settings()
    results: list[dict] = []

    try:
        live_account_balances = (
            account_service.get_balance_map()
            if mode == "live" and account_service is not None
            else None
        )

        symbols_to_process = (
            _order_symbols_for_live_cycle(settings.symbols, live_account_balances)
            if mode == "live"
            else settings.symbols
        )

        for symbol in symbols_to_process:
            market = markets_service.collect_snapshot(symbol)
            news_items = news_service.find_recent_by_symbol(symbol)
            thesis = research_agent.generate(symbol, market, news_items)
            daily_trade_usd = risk_agent.get_daily_trade_usd_total()
            symbol_assets = (
                account_service.binance_client.get_symbol_assets(symbol)
                if mode == "live" and account_service is not None
                else None
            )
            effective_bankroll_usd = _effective_live_bankroll_usd(
                live_account_balances=live_account_balances,
                symbol_assets=symbol_assets,
                default_bankroll_usd=settings.default_bankroll_usd,
            )
            thesis = _maybe_switch_buy_to_sell_for_cash_recovery(
                symbol=symbol,
                thesis=thesis,
                market_price=market.price,
                live_account_balances=live_account_balances,
                symbol_assets=symbol_assets,
                default_bankroll_usd=effective_bankroll_usd,
                max_risk_per_trade=settings.max_risk_per_trade,
            )
            symbol_on_cooldown = (
                reconciliation_service.is_symbol_on_cooldown(symbol)
                if reconciliation_service is not None
                else False
            )
            risk = risk_agent.evaluate(
                symbol=symbol,
                thesis=thesis,
                market=market,
                daily_trade_usd=daily_trade_usd,
                account_balances=live_account_balances,
                symbol_assets=symbol_assets,
                symbol_on_cooldown=symbol_on_cooldown,
            )
            decision = decision_engine.decide(symbol=symbol, thesis=thesis, risk=risk, market=market)

            execution = None
            if mode == "paper" and decision.should_trade and decision.side:
                execution = paper_executor.execute(
                    ExecutionRequest(
                        symbol=symbol,
                        side=decision.side,
                        quantity=decision.quantity,
                        price=decision.price,
                        rationale=decision.rationale,
                        confidence=decision.confidence,
                    )
                )

            if mode == "live" and decision.should_trade and decision.side and binance_executor is not None:
                execution = binance_executor.execute(
                    ExecutionRequest(
                        symbol=symbol,
                        side=decision.side,
                        quantity=decision.quantity,
                        price=decision.price,
                        rationale=decision.rationale,
                        confidence=decision.confidence,
                    )
                )

            audit_service.log(
                event_type="trading-cycle.symbol-processed",
                mode=mode,
                symbol=symbol,
                message=f"Decision {decision.side} generated for {symbol}"
                if decision.should_trade
                else f"No trade for {symbol}",
                rationale=decision.rationale,
                status=execution.status if execution else decision.action,
                raw_payload={
                    "market": market.model_dump(),
                    "thesis": thesis.model_dump(),
                    "risk": risk.model_dump(),
                    "decision": decision.model_dump(),
                    "execution": execution.model_dump() if execution else None,
                },
            )

            results.append(
                {
                    "symbol": symbol,
                    "market": market.model_dump(),
                    "thesis": thesis.model_dump(),
                    "risk": risk.model_dump(),
                    "decision": decision.model_dump(),
                    "execution": execution.model_dump() if execution else None,
                }
            )

            if reconciliation_service is not None:
                reconciliation_service.create_decision_insight(
                    symbol=symbol,
                    thesis_direction=thesis.direction,
                    approved=risk.approved,
                    action=decision.action,
                    confidence=decision.confidence,
                    entry_price=decision.price,
                    raw_payload={
                        "market": market.model_dump(),
                        "thesis": thesis.model_dump(),
                        "risk": risk.model_dump(),
                        "decision": decision.model_dump(),
                        "execution": execution.model_dump() if execution else None,
                    },
                )

        if mode == "live" and reconciliation_service is not None:
            reconciliation_service.sync_exchange_state(settings.symbols)

        if portfolio_history_service is not None:
            portfolio_history_service.record_snapshot_if_due(
                note="run_cycle",
                min_interval_minutes=5,
            )

        finished_at = datetime.utcnow()
        job_run.status = "SUCCESS"
        job_run.finished_at = finished_at
        job_run.duration_ms = elapsed_ms(started_at, finished_at)
        job_run.summary = f"Processed {len(results)} symbols"
        job_run.raw_payload = {"results": results}
        db.commit()
        return {"mode": mode, "symbols_processed": len(results), "results": results}
    except Exception as exc:
        finished_at = datetime.utcnow()
        job_run.status = "FAILED"
        job_run.finished_at = finished_at
        job_run.duration_ms = elapsed_ms(started_at, finished_at)
        job_run.summary = str(exc)
        job_run.raw_payload = {"error": str(exc)}
        db.commit()
        audit_service.log(
            event_type="trading-cycle.failed",
            mode=mode,
            message="Trading cycle execution failed",
            status="FAILED",
            raw_payload={"error": str(exc)},
        )
        raise


if __name__ == "__main__":
    from app.bootstrap import build_services
    from app.config.settings import get_settings
    from app.shared.db.session import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        services = build_services(db, settings.app_mode)
        print(
            run_trading_cycle(
                mode=settings.app_mode,
                markets_service=services.markets_service,
                news_service=services.news_service,
                research_agent=services.research_agent,
                risk_agent=services.risk_agent,
                decision_engine=services.decision_engine,
                audit_service=services.audit_service,
                paper_executor=services.paper_executor,
                binance_executor=services.binance_executor,
                account_service=services.account_service,
                reconciliation_service=services.reconciliation_service,
            )
        )
