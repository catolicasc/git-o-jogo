import json
import re
from contextlib import asynccontextmanager
from datetime import datetime
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bootstrap import AppServices, build_services
from app.config.logging import logger
from app.config.settings import get_settings
from app.integrations.evolution.evolution_client import EvolutionClient
from app.jobs.collect_news_job import collect_news_job
from app.jobs.run_trading_cycle_job import run_trading_cycle
from app.jobs.scan_markets_job import scan_markets_job
from app.shared.db import models  # noqa: F401
from app.shared.db.base import Base
from app.shared.db.models import JobRun
from app.shared.http.http_client import HttpRequestFailed
from app.shared.db.session import SessionLocal, engine, get_db
from app.shared.types.api import LiveOrderRequest, PaperOrderRequest, TestOrderRequest
from app.shared.types.domain import ExecutionRequest
from app.shared.utils.serialize import orm_to_dict

settings = get_settings()
scheduler = BackgroundScheduler()
evolution_client = EvolutionClient()


def get_services(db: Session = Depends(get_db)) -> AppServices:
    return build_services(db, settings.app_mode)


def schedule_jobs() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        lambda: _run_scan_job(),
        trigger="cron",
        minute="*/5",
        id="scan-markets",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_news_job(),
        trigger="cron",
        minute="*/10",
        id="collect-news",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_cycle_job(),
        trigger="cron",
        minute="*/15",
        id="run-trading-cycle",
        replace_existing=True,
    )
    scheduler.start()


def _run_scan_job() -> None:
    with SessionLocal() as db:
        services = build_services(db, settings.app_mode)
        scan_markets_job(
            markets_service=services.markets_service,
            audit_service=services.audit_service,
            mode=settings.app_mode,
        )


def _run_news_job() -> None:
    with SessionLocal() as db:
        services = build_services(db, settings.app_mode)
        collect_news_job(
            news_service=services.news_service,
            audit_service=services.audit_service,
            mode=settings.app_mode,
        )


def _run_cycle_job() -> None:
    with SessionLocal() as db:
        services = build_services(db, settings.app_mode)
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
            portfolio_history_service=services.portfolio_history_service,
            reconciliation_service=services.reconciliation_service,
        )


def _run_cycle_job_safe() -> None:
    try:
        _run_cycle_job()
    except Exception as exc:
        logger.exception("Background trading cycle failed: %s", exc)


def _start_run_cycle_background() -> None:
    thread = Thread(target=_run_cycle_job_safe, daemon=True)
    thread.start()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    schedule_jobs()
    yield
    if scheduler.running:
        scheduler.shutdown()


def _trade_origin(trade: dict) -> str:
    rationale = (trade.get("rationale") or "").strip().lower()
    if rationale == "synced from binance spot account history":
        return "synced_from_binance"
    return "bot_executed"


def _trade_origin_label(origin: str) -> str:
    if origin == "synced_from_binance":
        return "HISTORICO IMPORTADO"
    return "ORDEM DO BOT"


def _format_binance_trade_time(trade: dict) -> str:
    raw_payload = trade.get("raw_payload") or {}
    trade_time = raw_payload.get("time")
    if isinstance(trade_time, (int, float)):
        return datetime.fromtimestamp(trade_time / 1000).strftime("%Y-%m-%d %H:%M:%S")
    created_at = trade.get("created_at")
    if isinstance(created_at, str):
        return created_at.replace("T", " ")[:19]
    return "-"


def _build_symbol_chart_payload(services: AppServices) -> list[dict]:
    snapshots = {
        symbol: services.markets_service.latest_snapshot(symbol)
        for symbol in settings.symbols
    }
    positions = {item.symbol: item for item in services.portfolio_service.list_positions()}
    trades = services.trades_service.list_trades()
    payload: list[dict] = []

    for symbol in settings.symbols:
        snapshot = snapshots.get(symbol)
        if snapshot is None or not snapshot.klines:
            continue

        klines = snapshot.klines[-36:]
        candles = [
            {
                "open_time": int(item[0]),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
            }
            for item in klines
            if len(item) > 4
        ]
        if not candles:
            continue

        current_price = candles[-1]["close"]
        position = positions.get(symbol)
        avg_price = position.average_price if position is not None and position.quantity > 0 else None
        quantity = position.quantity if position is not None else 0
        unrealized_pnl = (
            (current_price - position.average_price) * position.quantity
            if position is not None and position.quantity > 0
            else 0.0
        )
        unrealized_pct = (
            ((current_price - position.average_price) / position.average_price) * 100
            if position is not None and position.quantity > 0 and position.average_price > 0
            else 0.0
        )

        symbol_trades = [trade for trade in trades if trade.symbol == symbol][:8]
        trade_markers = [
            {
                "side": trade.side,
                "price": trade.price,
                "created_at": trade.created_at.isoformat(),
                "origin": _trade_origin(orm_to_dict(trade)),
            }
            for trade in reversed(symbol_trades)
        ]

        status = "NEUTRO"
        status_reason = "Sem posicao aberta"
        if position is not None and position.quantity > 0:
            if unrealized_pnl > 0:
                status = "GANHANDO"
                status_reason = "Posicao aberta acima do preco medio"
            elif unrealized_pnl < 0:
                status = "PERDENDO"
                status_reason = "Posicao aberta abaixo do preco medio"
            else:
                status_reason = "Posicao aberta no zero a zero"
        elif symbol_trades:
            latest_trade = symbol_trades[0]
            edge = current_price - latest_trade.price if latest_trade.side == "BUY" else latest_trade.price - current_price
            if edge > 0:
                status = "ULTIMO SINAL BOM"
                status_reason = "Preco andou a favor do ultimo trade"
            elif edge < 0:
                status = "ULTIMO SINAL RUIM"
                status_reason = "Preco andou contra o ultimo trade"
            else:
                status_reason = "Preco alinhado ao ultimo trade"

        payload.append(
            {
                "symbol": symbol,
                "candles": candles,
                "current_price": current_price,
                "avg_price": avg_price,
                "position_qty": quantity,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pct": round(unrealized_pct, 2),
                "status": status,
                "status_reason": status_reason,
                "trade_markers": trade_markers,
            }
        )

    return payload


app = FastAPI(title="Binance Spot Trading Agent", lifespan=lifespan)


@app.get("/health")
def health(services: AppServices = Depends(get_services)) -> dict:
    return services.health_service.check()


@app.get("/markets")
def list_markets(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.markets_service.list_snapshots()]


@app.get("/markets/{symbol}")
def get_market(symbol: str, services: AppServices = Depends(get_services)) -> dict | None:
    row = services.markets_service.latest_snapshot(symbol.upper())
    return orm_to_dict(row) if row else None


@app.get("/news")
def list_news(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.news_service.list_items()]


@app.get("/theses")
def list_theses(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.research_agent.list_theses()]


@app.get("/trades")
def list_trades(services: AppServices = Depends(get_services)) -> dict:
    grouped = services.trades_service.list_trade_groups()
    bot_executed = [orm_to_dict(row) for row in grouped["bot_executed"]]
    synced_from_binance = [orm_to_dict(row) for row in grouped["synced_from_binance"]]
    all_trades = bot_executed + synced_from_binance

    return {
        "summary": {
            "total": len(all_trades),
            "bot_executed": len(bot_executed),
            "synced_from_binance": len(synced_from_binance),
        },
        "bot_executed": bot_executed,
        "synced_from_binance": synced_from_binance,
    }


@app.get("/orders")
def list_orders(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.trades_service.list_exchange_orders()]


@app.get("/insights")
def list_insights(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.trades_service.list_decision_insights()]


@app.get("/positions")
def list_positions(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.portfolio_service.list_positions()]


@app.get("/audit")
def list_audit(services: AppServices = Depends(get_services)) -> list[dict]:
    return [orm_to_dict(row) for row in services.audit_service.list_logs()]


@app.get("/account")
def account_overview(services: AppServices = Depends(get_services)) -> dict:
    return services.account_service.get_account_overview()


@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)) -> list[dict]:
    statement = select(JobRun).order_by(JobRun.started_at.desc()).limit(50)
    return [orm_to_dict(row) for row in db.scalars(statement)]


@app.get("/performance/summary")
def performance_summary(services: AppServices = Depends(get_services)) -> dict:
    return services.performance_service.get_summary()


@app.get("/performance/charts")
def performance_charts(services: AppServices = Depends(get_services)) -> dict:
    return services.performance_service.get_charts()


@app.get("/portfolio/history")
def portfolio_history(services: AppServices = Depends(get_services)) -> dict:
    services.portfolio_history_service.record_snapshot_if_due(note="history_api", min_interval_minutes=10)
    return services.portfolio_history_service.get_history()


@app.get("/backtest/report")
def backtest_report(services: AppServices = Depends(get_services)) -> dict:
    return services.backtest_service.run(symbols=settings.symbols)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(services: AppServices = Depends(get_services)) -> str:
    services.portfolio_history_service.record_snapshot_if_due(note="dashboard", min_interval_minutes=10)
    summary = services.performance_service.get_summary()
    charts = services.performance_service.get_charts()
    portfolio_history = services.portfolio_history_service.get_history()
    trade_groups = services.trades_service.list_trade_groups()
    quality = services.trades_service.get_bot_quality_summary()
    trade_source_summary = services.trades_service.get_trade_source_summary()
    decision_blockers = services.trades_service.get_decision_blockers_summary()
    ranked_setups = services.research_agent.strategy_stats_service.get_ranked_setups(symbols=settings.symbols)
    symbol_chart_payload = _build_symbol_chart_payload(services)
    latest_bot_trades = [orm_to_dict(row) for row in trade_groups["bot_executed"][:20]]
    latest_imported_trades = [orm_to_dict(row) for row in trade_groups["synced_from_binance"][:20]]
    account_rows = "<tr><td colspan='4'>Configure BINANCE_API_KEY e BINANCE_API_SECRET para ver saldos.</td></tr>"

    if settings.binance_api_key and settings.binance_api_secret:
        try:
            account_overview_data = services.account_service.get_account_overview()
            account_balances = account_overview_data["balances"][:50]
            account_rows = ""
        except Exception as exc:
            account_rows = f"<tr><td colspan='4'>Erro ao consultar Binance: {str(exc)}</td></tr>"
            account_balances = []
    else:
        account_balances = []

    pnl_available = summary.get("pnl_available", True)
    cash_recovery_required = summary.get("cash_recovery_required", False)
    spot_cash_balance = summary.get("spot_cash_balance", summary.get("cash_balance", 0))
    recoverable_cash_balance = summary.get("recoverable_cash_balance", 0)
    tether_total_balance = summary.get("tether_total_balance", summary.get("cash_balance", 0))
    pnl_class = (
        "positive"
        if pnl_available and summary["pnl_abs"] >= 0
        else "negative"
        if pnl_available
        else ""
    )
    allowlist_options = "".join(
        f"<option value='{symbol}'>{symbol}</option>" for symbol in settings.symbols
    )

    equity_svg = _line_chart_svg(
        [point["equity"] for point in charts["equity_curve"]],
        width=720,
        height=220,
        stroke="#14532d",
        fill="#dcfce7",
        empty_label="Sem trades simulados ainda",
    )
    pnl_svg = _bar_chart_svg(
        [item["symbol"] for item in charts["position_bars"]],
        [item["unrealized_pnl"] for item in charts["position_bars"]],
        width=720,
        height=220,
        empty_label="Sem posicoes abertas",
    )
    pnl_text = (
        f"{summary['pnl_abs']:.2f} ({summary['pnl_pct']:.2f}%)"
        if pnl_available
        else "Indisponivel"
    )
    volume_rows = ""
    recent_trades_rows = ""

    subtitle_html = (
        "Acompanhe os trades simulados, capital, PnL e exposicao atual. "
        f"<span class=\"mode-pill\">modo atual: {settings.app_mode}</span>"
    )
    if settings.app_mode == "live" and not pnl_available:
        subtitle_html = (
            "Snapshot de saldos reais da Binance em USDT. "
            "PnL fica indisponivel sem uma linha de base confiavel da conta. "
            f"<span class=\"mode-pill\">modo atual: {settings.app_mode}</span>"
        )
        if cash_recovery_required:
            subtitle_html += (
                f" <span class=\"mode-pill\" style=\"background:#fef3c7;color:#92400e;\">"
                f"LDUSDT recuperavel: {recoverable_cash_balance:.2f}</span>"
            )

    latest_bot_trades_json = json.dumps(latest_bot_trades, default=str)
    latest_imported_trades_json = json.dumps(latest_imported_trades, default=str)
    blockers_json = json.dumps(decision_blockers[:12], default=str)
    top_setups_json = json.dumps(ranked_setups[:12], default=str)
    account_balances_json = json.dumps(account_balances, default=str)
    symbol_notional_json = json.dumps(charts["symbol_notional"], default=str)
    trade_points_json = json.dumps(charts["trade_points"][-50:], default=str)
    symbol_chart_payload_json = json.dumps(symbol_chart_payload, default=str)
    default_chart_symbol = symbol_chart_payload[0]["symbol"] if symbol_chart_payload else ""
    wallet_history_svg = _line_chart_svg(
        [point["equity_brl"] for point in portfolio_history["points"]],
        width=720,
        height=220,
        stroke="#1d4ed8",
        fill="#dbeafe",
        empty_label="Sem historico da carteira ainda",
    )
    wallet_change_class = (
        "positive" if portfolio_history["summary"]["change_brl"] >= 0 else "negative"
    )

    return f"""
    <html>
      <head>
        <title>Trading Agent Dashboard</title>
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f7f4; color: #1f2937; margin: 0; padding: 24px; }}
          .container {{ max-width: 1200px; margin: 0 auto; }}
          h1 {{ margin: 0 0 8px; }}
          .subtitle {{ color: #4b5563; margin-bottom: 24px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
          .card {{ background: white; border-radius: 16px; padding: 18px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }}
          .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: #6b7280; }}
          .value {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
          .row {{ display: grid; grid-template-columns: 1fr; gap: 16px; margin-bottom: 24px; }}
          .two-col {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 24px; }}
          table {{ width: 100%; border-collapse: collapse; }}
          th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }}
          th {{ color: #6b7280; font-weight: 600; }}
          .positive {{ color: #166534; }}
          .negative {{ color: #b91c1c; }}
          .toolbar {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
          .button {{ appearance: none; border: 0; border-radius: 12px; padding: 12px 16px; font-weight: 700; cursor: pointer; }}
          .button-primary {{ background: #14532d; color: white; }}
          .button-secondary {{ background: #e5e7eb; color: #111827; }}
          .button-danger {{ background: #7f1d1d; color: white; }}
          .form-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
          .form-full {{ grid-column: 1 / -1; }}
          input, select {{
            width: 100%;
            box-sizing: border-box;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 14px;
          }}
          .help {{ color: #6b7280; font-size: 13px; margin-top: 6px; }}
          .console {{
            background: #111827;
            color: #e5e7eb;
            border-radius: 16px;
            padding: 16px;
            height: 320px;
            max-height: 320px;
            overflow: auto;
            font-family: ui-monospace, SFMono-Regular, monospace;
            font-size: 13px;
            white-space: pre-wrap;
          }}
          .mode-pill {{
            display: inline-block;
            background: #dcfce7;
            color: #166534;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 700;
            margin-left: 8px;
          }}
          .trade-badge {{
            display: inline-block;
            border-radius: 999px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.03em;
          }}
          .trade-badge-imported {{
            background: #e5e7eb;
            color: #374151;
          }}
          .trade-badge-bot {{
            background: #dcfce7;
            color: #166534;
          }}
          .pager {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin-top: 14px;
            flex-wrap: wrap;
          }}
          .pager-info {{ color: #6b7280; font-size: 13px; }}
          .quality-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
          }}
          .quality-metric {{
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 14px;
          }}
          .quality-metric strong {{
            display: block;
            font-size: 24px;
            margin-top: 6px;
          }}
          .chart-stage {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            padding: 16px;
          }}
          .chart-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
          }}
          .chart-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
            margin-bottom: 12px;
          }}
          .chart-meta .quality-metric strong {{
            font-size: 20px;
          }}
          .chart-canvas {{
            width: 100%;
            height: 360px;
            border-radius: 14px;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
          }}
          .legend {{
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 10px;
            color: #6b7280;
            font-size: 12px;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Autonomous Spot Trading Dashboard</h1>
          <div class="subtitle">{subtitle_html}</div>
          <div class="two-col">
            <div class="card">
              <div class="label">Acoes Rapidas</div>
              <div class="toolbar">
                <button class="button button-primary" onclick="runCycle()">Rodar Trading Cycle</button>
                <button class="button button-secondary" onclick="openJson('/jobs')">Atualizar Jobs</button>
                <button class="button button-secondary" onclick="clearConsole()">Limpar Console</button>
              </div>
              <div class="help">Use o ciclo para coletar dados, gerar tese, avaliar risco e executar conforme o modo atual.</div>
            </div>
            <div class="card">
              <div class="label">Console Operacional</div>
              <div id="console" class="console">Pronto para executar acoes.</div>
            </div>
          </div>
          <div class="grid">
            <div class="card"><div class="label">Equity</div><div class="value">{summary['equity']:.2f}</div></div>
            <div class="card"><div class="label">PnL</div><div class="value {pnl_class}">{pnl_text}</div></div>
            <div class="card"><div class="label">Cash Balance</div><div class="value">{summary['cash_balance']:.2f}</div></div>
            <div class="card"><div class="label">USDT Spot Livre</div><div class="value">{spot_cash_balance:.2f}</div></div>
            <div class="card"><div class="label">LDUSDT Recuperavel</div><div class="value">{recoverable_cash_balance:.2f}</div></div>
            <div class="card"><div class="label">Tether Total</div><div class="value">{tether_total_balance:.2f}</div></div>
            <div class="card"><div class="label">Inventory Value</div><div class="value">{summary['inventory_value']:.2f}</div></div>
            <div class="card"><div class="label">Realized PnL</div><div class="value">{summary['realized_pnl']:.2f}</div></div>
            <div class="card"><div class="label">Unrealized PnL</div><div class="value">{summary['unrealized_pnl']:.2f}</div></div>
            <div class="card"><div class="label">Total Trades</div><div class="value">{summary['total_trades']}</div></div>
            <div class="card"><div class="label">Open Positions</div><div class="value">{summary['open_positions']}</div></div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Status Do Caixa</div>
              <div class="help">{summary.get('cash_note', 'Sem observacoes sobre o caixa.')}</div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Equity Curve</div>
              {equity_svg}
            </div>
            <div class="card">
              <div class="label">PnL por Posicao Aberta</div>
              {pnl_svg}
            </div>
          </div>
          <div class="two-col">
            <div class="card">
              <div class="label">Test Order Binance</div>
              <form class="form-grid" onsubmit="submitTestOrder(event)">
                <div>
                  <label>Simbolo</label>
                  <select name="symbol">{allowlist_options}</select>
                </div>
                <div>
                  <label>Side</label>
                  <select name="side">
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
                <div>
                  <label>Order Type</label>
                  <select name="order_type" onchange="togglePriceField(this, 'test-price-wrapper')">
                    <option value="MARKET">MARKET</option>
                    <option value="LIMIT">LIMIT</option>
                  </select>
                </div>
                <div>
                  <label>Quantidade</label>
                  <input name="quantity" type="number" step="0.00000001" value="0.001" required />
                </div>
                <div id="test-price-wrapper" class="form-full" style="display:none;">
                  <label>Preco</label>
                  <input name="price" type="number" step="0.01" placeholder="Obrigatorio para LIMIT" />
                </div>
                <div class="form-full">
                  <button class="button button-secondary" type="submit">Validar na Binance</button>
                </div>
              </form>
            </div>
          </div>
          <div class="two-col">
            <div class="card">
              <div class="label">Live Order Binance</div>
              <form class="form-grid" onsubmit="submitLiveOrder(event)">
                <div>
                  <label>Simbolo</label>
                  <select name="symbol">{allowlist_options}</select>
                </div>
                <div>
                  <label>Side</label>
                  <select name="side">
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
                <div>
                  <label>Order Type</label>
                  <select name="order_type" onchange="togglePriceField(this, 'live-price-wrapper')">
                    <option value="MARKET">MARKET</option>
                    <option value="LIMIT">LIMIT</option>
                  </select>
                </div>
                <div>
                  <label>Quantidade</label>
                  <input name="quantity" type="number" step="0.00000001" value="0.001" required />
                </div>
                <div id="live-price-wrapper" class="form-full" style="display:none;">
                  <label>Preco</label>
                  <input name="price" type="number" step="0.01" placeholder="Obrigatorio para LIMIT" />
                </div>
                <div class="form-full">
                  <label>Rationale</label>
                  <input name="rationale" type="text" value="Manual live order via dashboard" />
                </div>
                <div>
                  <label>Confidence</label>
                  <input name="confidence" type="number" min="0" max="1" step="0.01" value="1" required />
                </div>
                <div style="display:flex; align-items:end;">
                  <button class="button button-danger" type="submit">Enviar Live Order</button>
                </div>
              </form>
              <div class="help">So funciona com <code>APP_MODE=live</code> e <code>ENABLE_LIVE_TRADING=true</code>.</div>
            </div>
            <div class="card">
              <div class="label">Checagens Uteis</div>
              <div class="toolbar">
                <button class="button button-secondary" onclick="openJson('/trades')">Ver Trades</button>
                <button class="button button-secondary" onclick="openJson('/positions')">Ver Positions</button>
                <button class="button button-secondary" onclick="openJson('/orders')">Ver Orders</button>
                <button class="button button-secondary" onclick="openJson('/insights')">Ver Insights</button>
                <button class="button button-secondary" onclick="openJson('/audit')">Ver Audit</button>
                <button class="button button-secondary" onclick="openJson('/jobs')">Ver Jobs</button>
                <button class="button button-secondary" onclick="openJson('/account')">Ver Account</button>
                <button class="button button-secondary" onclick="openJson('/performance/summary')">Ver Summary</button>
              </div>
              <div class="help">Use `Ver Jobs` para acompanhar o run-cycle em background.</div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Historico Da Carteira</div>
              <div class="grid">
                <div class="card"><div class="label">Comecou Com</div><div class="value">R$ {portfolio_history['summary']['starting_brl']:.2f}</div></div>
                <div class="card"><div class="label">Agora Tem</div><div class="value">R$ {portfolio_history['summary']['current_brl']:.2f}</div></div>
                <div class="card"><div class="label">Variacao</div><div class="value {wallet_change_class}">R$ {portfolio_history['summary']['change_brl']:.2f} ({portfolio_history['summary']['change_pct']:.2f}%)</div></div>
                <div class="card"><div class="label">Snapshots</div><div class="value">{portfolio_history['summary']['points']}</div></div>
              </div>
              {wallet_history_svg}
              <div class="help">Historico automatico da carteira convertido para BRL. Referencia atual em USD: {portfolio_history['summary']['starting_usd']:.2f} -> {portfolio_history['summary']['current_usd']:.2f}.</div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Qualidade Das Acoes Do Bot</div>
              <div class="quality-grid">
                <div class="quality-metric"><span>Veredito</span><strong>{quality['verdict']}</strong></div>
                <div class="quality-metric"><span>Janela</span><strong>{quality['window_days']} dias</strong></div>
                <div class="quality-metric"><span>Decisoes Avaliadas</span><strong>{quality['total_decisions']}</strong></div>
                <div class="quality-metric"><span>Setups Acionaveis</span><strong>{quality['actionable_decisions']}</strong></div>
                <div class="quality-metric"><span>Taxa de Aprovacao</span><strong>{quality['approval_rate']:.2f}%</strong></div>
                <div class="quality-metric"><span>Taxa de Acao</span><strong>{quality['trade_action_rate']:.2f}%</strong></div>
                <div class="quality-metric"><span>Win Rate Resolvido</span><strong>{quality['win_rate']:.2f}%</strong></div>
                <div class="quality-metric"><span>Confianca Media</span><strong>{quality['avg_confidence']:.2f}</strong></div>
                <div class="quality-metric"><span>Wins / Losses / Pending</span><strong>{quality['wins']} / {quality['losses']} / {quality['pending']}</strong></div>
                <div class="quality-metric"><span>Pending EV+ / EV-</span><strong>{quality['positive_ev_pending']} / {quality['negative_ev_pending']}</strong></div>
                <div class="quality-metric"><span>Pending Sem Setup</span><strong>{quality['no_setup_pending']}</strong></div>
                <div class="quality-metric"><span>PnL Medio Resolvido</span><strong>{quality['avg_pnl']:.2f}</strong></div>
              </div>
              <div class="help">A leitura usa os registros de <code>decision_insights</code> do ultimo trimestre para resumir quantas decisoes tiveram setup acionavel, quantas viraram acao e quantas terminaram em ganho ou perda.</div>
            </div>
          </div>
          <div class="two-col">
            <div class="card">
              <div class="label">Ranking Trimestral De Setups</div>
              <table>
                <thead><tr><th>Simbolo</th><th>Setup</th><th>Regime</th><th>EV%</th><th>PF</th><th>Trades</th><th>Status</th></tr></thead>
                <tbody id="setups-table-body"></tbody>
              </table>
              <div class="pager">
                <div id="setups-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('setups-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('setups-table')">Proxima</button>
                </div>
              </div>
            </div>
            <div class="card">
              <div class="label">Por Que As Oportunidades Nao Viraram Trade</div>
              <table>
                <thead><tr><th>Motivo</th><th>Ocorrencias</th></tr></thead>
                <tbody id="blockers-table-body"></tbody>
              </table>
              <div class="pager">
                <div id="blockers-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('blockers-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('blockers-table')">Proxima</button>
                </div>
              </div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Grafico De Velas Das Negociacoes</div>
              <div class="chart-stage">
                <div class="chart-toolbar">
                  <div class="help">Velas recentes com marcacoes de compra e venda. A linha azul mostra o preco medio da posicao quando houver.</div>
                  <select id="candles-symbol-select" onchange="renderCandles(this.value)">
                    {"".join(f"<option value='{item['symbol']}' {'selected' if item['symbol'] == default_chart_symbol else ''}>{item['symbol']}</option>" for item in symbol_chart_payload) or "<option value=''>Sem dados</option>"}
                  </select>
                </div>
                <div id="candles-meta" class="chart-meta"></div>
                <canvas id="candles-canvas" class="chart-canvas" width="1080" height="360"></canvas>
                <div class="legend">
                  <span>Verde: candle de alta</span>
                  <span>Vermelho: candle de baixa</span>
                  <span>Triangulo para cima: BUY</span>
                  <span>Triangulo para baixo: SELL</span>
                  <span>Linha azul: preco medio da posicao</span>
                </div>
              </div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Origem Das Transacoes</div>
              <div class="quality-grid">
                <div class="quality-metric"><span>Ordens Do Bot</span><strong>{trade_source_summary['bot_executed']['count']}</strong></div>
                <div class="quality-metric"><span>Notional Do Bot</span><strong>{trade_source_summary['bot_executed']['gross_notional']:.2f}</strong></div>
                <div class="quality-metric"><span>Historico Importado</span><strong>{trade_source_summary['synced_from_binance']['count']}</strong></div>
                <div class="quality-metric"><span>Notional Importado</span><strong>{trade_source_summary['synced_from_binance']['gross_notional']:.2f}</strong></div>
              </div>
              <div class="help">Separacao entre o que foi executado pelo nosso fluxo e o que so entrou por reconciliacao da Binance.</div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Ordens Do Bot</div>
              <table>
                <thead><tr><th>Origem</th><th>Data Binance</th><th>Simbolo</th><th>Side</th><th>Preco</th><th>Quantidade</th><th>Status</th></tr></thead>
                <tbody id="bot-trades-table-body"></tbody>
              </table>
              <div class="pager">
                <div id="bot-trades-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('bot-trades-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('bot-trades-table')">Proxima</button>
                </div>
              </div>
            </div>
            <div class="card">
              <div class="label">Historico Importado Da Binance</div>
              <table>
                <thead><tr><th>Origem</th><th>Data Binance</th><th>Simbolo</th><th>Side</th><th>Preco</th><th>Quantidade</th><th>Status</th></tr></thead>
                <tbody id="imported-trades-table-body"></tbody>
              </table>
              <div class="pager">
                <div id="imported-trades-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('imported-trades-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('imported-trades-table')">Proxima</button>
                </div>
              </div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Saldos da Binance Spot</div>
              <table>
                <thead><tr><th>Asset</th><th>Free</th><th>Locked</th><th>Total</th></tr></thead>
                <tbody id="balances-table-body">{account_rows}</tbody>
              </table>
              <div class="pager">
                <div id="balances-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('balances-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('balances-table')">Proxima</button>
                </div>
              </div>
            </div>
          </div>
          <div class="row">
            <div class="card">
              <div class="label">Volume por Simbolo</div>
              <table>
                <thead><tr><th>Simbolo</th><th>Volume Negociado (USD)</th></tr></thead>
                <tbody id="volume-table-body">{volume_rows}</tbody>
              </table>
              <div class="pager">
                <div id="volume-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('volume-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('volume-table')">Proxima</button>
                </div>
              </div>
            </div>
            <div class="card">
              <div class="label">Trades Mais Recentes</div>
              <table>
                <thead><tr><th>Timestamp</th><th>Simbolo</th><th>Side</th><th>Notional</th><th>Confidence</th></tr></thead>
                <tbody id="recent-trades-table-body">{recent_trades_rows}</tbody>
              </table>
              <div class="pager">
                <div id="recent-trades-table-info" class="pager-info"></div>
                <div class="toolbar">
                  <button class="button button-secondary" onclick="prevPage('recent-trades-table')">Anterior</button>
                  <button class="button button-secondary" onclick="nextPage('recent-trades-table')">Proxima</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <script>
          const consoleHistory = [];
          const symbolCharts = {symbol_chart_payload_json};
          const paginatedTables = {{
            'bot-trades-table': {{
              page: 1,
              pageSize: 6,
              bodyId: 'bot-trades-table-body',
              infoId: 'bot-trades-table-info',
              emptyCols: 7,
              rows: {latest_bot_trades_json},
              renderRow: (item) => {{
                const imported = ((item.rationale || '').trim().toLowerCase() === 'synced from binance spot account history');
                const badgeClass = imported ? 'trade-badge-imported' : 'trade-badge-bot';
                const badgeLabel = imported ? 'HISTORICO IMPORTADO' : 'ORDEM DO BOT';
                const payload = item.raw_payload || {{}};
                let tradeTime = '-';
                if (typeof payload.time === 'number') {{
                  tradeTime = new Date(payload.time).toLocaleString();
                }} else if (item.created_at) {{
                  tradeTime = String(item.created_at).replace('T', ' ').slice(0, 19);
                }}
                return `<tr><td><span class="trade-badge ${{badgeClass}}">${{badgeLabel}}</span></td><td>${{tradeTime}}</td><td>${{item.symbol}}</td><td>${{item.side}}</td><td>${{Number(item.price || 0).toFixed(8)}}</td><td>${{Number(item.quantity || 0).toFixed(8)}}</td><td>${{item.status || '-'}}</td></tr>`;
              }},
              emptyMessage: 'Nenhuma ordem do bot encontrada.',
            }},
            'imported-trades-table': {{
              page: 1,
              pageSize: 6,
              bodyId: 'imported-trades-table-body',
              infoId: 'imported-trades-table-info',
              emptyCols: 7,
              rows: {latest_imported_trades_json},
              renderRow: (item) => {{
                const payload = item.raw_payload || {{}};
                let tradeTime = '-';
                if (typeof payload.time === 'number') {{
                  tradeTime = new Date(payload.time).toLocaleString();
                }} else if (item.created_at) {{
                  tradeTime = String(item.created_at).replace('T', ' ').slice(0, 19);
                }}
                return `<tr><td><span class="trade-badge trade-badge-imported">HISTORICO IMPORTADO</span></td><td>${{tradeTime}}</td><td>${{item.symbol}}</td><td>${{item.side}}</td><td>${{Number(item.price || 0).toFixed(8)}}</td><td>${{Number(item.quantity || 0).toFixed(8)}}</td><td>${{item.status || '-'}}</td></tr>`;
              }},
              emptyMessage: 'Nenhum trade importado encontrado.',
            }},
            'balances-table': {{
              page: 1,
              pageSize: 8,
              bodyId: 'balances-table-body',
              infoId: 'balances-table-info',
              emptyCols: 4,
              rows: {account_balances_json},
              renderRow: (item) => `<tr><td>${{item.asset}}</td><td>${{Number(item.free || 0).toFixed(8)}}</td><td>${{Number(item.locked || 0).toFixed(8)}}</td><td>${{Number(item.total || 0).toFixed(8)}}</td></tr>`,
              emptyMessage: 'Nenhum saldo encontrado.',
            }},
            'volume-table': {{
              page: 1,
              pageSize: 6,
              bodyId: 'volume-table-body',
              infoId: 'volume-table-info',
              emptyCols: 2,
              rows: {symbol_notional_json},
              renderRow: (item) => `<tr><td>${{item.symbol}}</td><td>${{Number(item.notional || 0).toFixed(2)}}</td></tr>`,
              emptyMessage: 'Sem volume negociado ainda',
            }},
            'recent-trades-table': {{
              page: 1,
              pageSize: 6,
              bodyId: 'recent-trades-table-body',
              infoId: 'recent-trades-table-info',
              emptyCols: 5,
              rows: {trade_points_json},
              renderRow: (item) => `<tr><td>${{String(item.timestamp || '').replace('T', ' ').slice(0, 19)}}</td><td>${{item.symbol}}</td><td>${{item.side}}</td><td>${{Number(item.notional || 0).toFixed(2)}}</td><td>${{Number(item.confidence || 0).toFixed(2)}}</td></tr>`,
              emptyMessage: 'Sem trades simulados ainda',
            }},
            'setups-table': {{
              page: 1,
              pageSize: 6,
              bodyId: 'setups-table-body',
              infoId: 'setups-table-info',
              emptyCols: 7,
              rows: {top_setups_json},
              renderRow: (item) => {{
                const status = item.enabled ? 'ATIVO' : 'DESLIGADO';
                const badgeClass = item.enabled ? 'trade-badge-bot' : 'trade-badge-imported';
                return `<tr><td>${{item.symbol}}</td><td>${{item.setup_id || '-'}}</td><td>${{item.regime || '-'}}</td><td>${{Number(item.expectancy_pct || 0).toFixed(2)}}</td><td>${{String(item.profit_factor || 0)}}</td><td>${{Number(item.trades || 0)}}</td><td><span class="trade-badge ${{badgeClass}}">${{status}}</span></td></tr>`;
              }},
              emptyMessage: 'Sem setups ranqueados no trimestre.',
            }},
            'blockers-table': {{
              page: 1,
              pageSize: 6,
              bodyId: 'blockers-table-body',
              infoId: 'blockers-table-info',
              emptyCols: 2,
              rows: {blockers_json},
              renderRow: (item) => `<tr><td>${{item.reason}}</td><td>${{Number(item.count || 0)}}</td></tr>`,
              emptyMessage: 'Sem bloqueios registrados no trimestre.',
            }},
          }};

          function logConsole(title, payload) {{
            const target = document.getElementById('console');
            const pretty = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
            consoleHistory.push(`[${{new Date().toLocaleString()}}] ${{title}}\\n${{pretty}}`);
            target.textContent = consoleHistory.join('\\n\\n------------------------------\\n\\n');
            target.scrollTop = target.scrollHeight;
          }}

          function clearConsole() {{
            consoleHistory.length = 0;
            document.getElementById('console').textContent = 'Console limpo.';
          }}

          function renderCandles(symbol) {{
            const chart = symbolCharts.find((item) => item.symbol === symbol);
            const canvas = document.getElementById('candles-canvas');
            const meta = document.getElementById('candles-meta');
            if (!canvas || !meta) {{
              return;
            }}

            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            if (!chart || !chart.candles.length) {{
              meta.innerHTML = '<div class="quality-metric"><span>Status</span><strong>Sem dados</strong></div>';
              return;
            }}

            meta.innerHTML = `
              <div class="quality-metric"><span>Status</span><strong>${{chart.status}}</strong></div>
              <div class="quality-metric"><span>Motivo</span><strong>${{chart.status_reason}}</strong></div>
              <div class="quality-metric"><span>Preco Atual</span><strong>${{Number(chart.current_price || 0).toFixed(4)}}</strong></div>
              <div class="quality-metric"><span>PnL Aberto</span><strong>${{Number(chart.unrealized_pnl || 0).toFixed(2)}} (${{Number(chart.unrealized_pct || 0).toFixed(2)}}%)</strong></div>
              <div class="quality-metric"><span>Qtd Posicao</span><strong>${{Number(chart.position_qty || 0).toFixed(6)}}</strong></div>
              <div class="quality-metric"><span>Preco Medio</span><strong>${{chart.avg_price ? Number(chart.avg_price).toFixed(4) : 'N/A'}}</strong></div>
            `;

            const candles = chart.candles;
            const highs = candles.map((item) => item.high);
            const lows = candles.map((item) => item.low);
            let minPrice = Math.min(...lows);
            let maxPrice = Math.max(...highs);

            if (chart.avg_price) {{
              minPrice = Math.min(minPrice, chart.avg_price);
              maxPrice = Math.max(maxPrice, chart.avg_price);
            }}

            const padX = 48;
            const padY = 24;
            const width = canvas.width - padX * 2;
            const height = canvas.height - padY * 2;
            const priceRange = Math.max(maxPrice - minPrice, 0.000001);
            const candleWidth = Math.max(width / candles.length * 0.58, 4);
            const stepX = width / candles.length;

            const priceToY = (price) => padY + (maxPrice - price) / priceRange * height;

            ctx.fillStyle = '#f8fafc';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.strokeStyle = '#d1d5db';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i += 1) {{
              const y = padY + (height / 4) * i;
              ctx.beginPath();
              ctx.moveTo(padX, y);
              ctx.lineTo(canvas.width - padX, y);
              ctx.stroke();

              const value = maxPrice - (priceRange / 4) * i;
              ctx.fillStyle = '#6b7280';
              ctx.font = '12px sans-serif';
              ctx.fillText(value.toFixed(4), 8, y + 4);
            }}

            candles.forEach((candle, index) => {{
              const x = padX + index * stepX + stepX / 2;
              const yHigh = priceToY(candle.high);
              const yLow = priceToY(candle.low);
              const yOpen = priceToY(candle.open);
              const yClose = priceToY(candle.close);
              const rising = candle.close >= candle.open;
              const color = rising ? '#16a34a' : '#dc2626';

              ctx.strokeStyle = color;
              ctx.beginPath();
              ctx.moveTo(x, yHigh);
              ctx.lineTo(x, yLow);
              ctx.stroke();

              ctx.fillStyle = color;
              const bodyTop = Math.min(yOpen, yClose);
              const bodyHeight = Math.max(Math.abs(yClose - yOpen), 2);
              ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
            }});

            if (chart.avg_price) {{
              const avgY = priceToY(chart.avg_price);
              ctx.strokeStyle = '#2563eb';
              ctx.lineWidth = 2;
              ctx.setLineDash([6, 4]);
              ctx.beginPath();
              ctx.moveTo(padX, avgY);
              ctx.lineTo(canvas.width - padX, avgY);
              ctx.stroke();
              ctx.setLineDash([]);
            }}

            const markerCount = chart.trade_markers.length;
            chart.trade_markers.forEach((marker, markerIndex) => {{
              const x = padX + (width / Math.max(markerCount, 1)) * markerIndex + 18;
              const y = priceToY(marker.price);
              const isBuy = marker.side === 'BUY';
              ctx.fillStyle = isBuy ? '#15803d' : '#b91c1c';
              ctx.beginPath();
              if (isBuy) {{
                ctx.moveTo(x, y - 10);
                ctx.lineTo(x - 8, y + 6);
                ctx.lineTo(x + 8, y + 6);
              }} else {{
                ctx.moveTo(x, y + 10);
                ctx.lineTo(x - 8, y - 6);
                ctx.lineTo(x + 8, y - 6);
              }}
              ctx.closePath();
              ctx.fill();
            }});
          }}

          function renderTable(tableKey) {{
            const table = paginatedTables[tableKey];
            const tbody = document.getElementById(table.bodyId);
            const info = document.getElementById(table.infoId);
            if (!tbody || !info) {{
              return;
            }}

            const totalRows = table.rows.length;
            const totalPages = Math.max(Math.ceil(totalRows / table.pageSize), 1);
            table.page = Math.min(Math.max(table.page, 1), totalPages);
            const start = (table.page - 1) * table.pageSize;
            const end = start + table.pageSize;
            const items = table.rows.slice(start, end);

            if (!items.length) {{
              tbody.innerHTML = `<tr><td colspan="${{table.emptyCols}}">${{table.emptyMessage}}</td></tr>`;
              info.textContent = totalRows === 0 ? '0 itens' : `Pagina ${{table.page}} de ${{totalPages}}`;
              return;
            }}

            tbody.innerHTML = items.map(table.renderRow).join('');
            info.textContent = `Mostrando ${{start + 1}}-${{Math.min(end, totalRows)}} de ${{totalRows}} | Pagina ${{table.page}} de ${{totalPages}}`;
          }}

          function prevPage(tableKey) {{
            paginatedTables[tableKey].page -= 1;
            renderTable(tableKey);
          }}

          function nextPage(tableKey) {{
            paginatedTables[tableKey].page += 1;
            renderTable(tableKey);
          }}

          function normalizeForm(form) {{
            const data = Object.fromEntries(new FormData(form).entries());
            for (const key of ['quantity', 'price', 'confidence']) {{
              if (data[key] !== undefined && data[key] !== '') {{
                data[key] = Number(data[key]);
              }} else {{
                delete data[key];
              }}
            }}
            return data;
          }}

          async function postJson(url, payload, title) {{
            try {{
              const response = await fetch(url, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload)
              }});
              const text = await response.text();
              let body;
              try {{
                body = JSON.parse(text);
              }} catch {{
                body = text;
              }}
              if (!response.ok) {{
                logConsole(title + ' falhou', body);
                return;
              }}
              logConsole(title + ' OK', body);
            }} catch (error) {{
              logConsole(title + ' erro', String(error));
            }}
          }}

          function togglePriceField(select, wrapperId) {{
            const wrapper = document.getElementById(wrapperId);
            wrapper.style.display = select.value === 'LIMIT' ? 'block' : 'none';
          }}

          async function runCycle() {{
            await postJson('/jobs/run-cycle', {{}}, 'Trading cycle');
            setTimeout(() => openJson('/jobs'), 500);
          }}

          async function submitTestOrder(event) {{
            event.preventDefault();
            await postJson('/execution/test-order', normalizeForm(event.target), 'Test order');
          }}

          async function submitLiveOrder(event) {{
            event.preventDefault();
            const payload = normalizeForm(event.target);
            const confirmed = window.confirm('Confirma envio de LIVE order real para a Binance Spot?');
            if (!confirmed) {{
              logConsole('Live order cancelada', 'Acao cancelada pelo usuario.');
              return;
            }}
            await postJson('/execution/live-order', payload, 'Live order');
          }}

          async function openJson(url) {{
            try {{
              const response = await fetch(url);
              const body = await response.json();
              logConsole(url, body);
            }} catch (error) {{
              logConsole(url + ' erro', String(error));
            }}
          }}

          Object.keys(paginatedTables).forEach(renderTable);
          if ('{default_chart_symbol}') {{
            renderCandles('{default_chart_symbol}');
          }}
        </script>
      </body>
    </html>
    """


@app.post("/jobs/run-cycle")
def run_cycle() -> dict:
    _start_run_cycle_background()
    return {
        "accepted": True,
        "message": "Trading cycle started in background",
        "mode": settings.app_mode,
        "status_url": "/jobs",
    }


@app.post("/evolution/send-briefing")
def evolution_send_briefing(services: AppServices = Depends(get_services)) -> dict:
    message = services.bot_voice_service.build_briefing()
    response = evolution_client.send_text(settings.evolution_allowed_number, message)
    return {"sent": True, "message": message, "provider_response": response}


@app.post("/webhooks/evolution")
def evolution_webhook(
    payload: dict = Body(...),
    services: AppServices = Depends(get_services),
) -> dict:
    sender, text, from_me = _extract_evolution_message(payload)
    if not sender or not text or from_me:
        return {"processed": False, "reason": "ignored"}

    normalized_allowed = _normalize_number(settings.evolution_allowed_number)
    normalized_sender = _normalize_number(sender)
    if not normalized_sender.endswith(normalized_allowed):
        return {"processed": False, "reason": "sender_not_allowed"}

    reply = services.bot_voice_service.answer_question(text)
    try:
        provider_response = evolution_client.send_text(normalized_sender, reply)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "evolution_send_failed",
                "sender": normalized_sender,
                "reply": reply,
                "message": str(exc),
            },
        ) from exc
    return {
        "processed": True,
        "sender": normalized_sender,
        "question": text,
        "reply": reply,
        "provider_response": provider_response,
    }


@app.post("/execution/test-order")
def execution_test_order(
    request: TestOrderRequest, services: AppServices = Depends(get_services)
) -> dict:
    try:
        result = services.binance_executor.test_order(
            ExecutionRequest(
                symbol=request.symbol.upper(),
                side=request.side.upper(),
                quantity=request.quantity,
                price=request.price or 0,
                rationale="Manual Binance Spot test order",
                confidence=1.0,
                order_type=request.order_type.upper(),
            )
        )
    except HttpRequestFailed as exc:
        raise HTTPException(
            status_code=exc.status_code or 502,
            detail={
                "error": "binance_test_order_failed",
                "symbol": request.symbol.upper(),
                "message": str(exc),
                "provider_status": exc.status_code,
                "provider_response": exc.response_text,
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "binance_test_order_rejected",
                "symbol": request.symbol.upper(),
                "message": str(exc),
            },
        ) from exc
    return result.model_dump()


@app.post("/execution/live-order")
def execution_live_order(
    request: LiveOrderRequest, services: AppServices = Depends(get_services)
) -> dict:
    try:
        result = services.binance_executor.execute(
            ExecutionRequest(
                symbol=request.symbol.upper(),
                side=request.side.upper(),
                quantity=request.quantity,
                price=request.price or 0,
                rationale=request.rationale,
                confidence=request.confidence,
                order_type=request.order_type.upper(),
            )
        )
    except HttpRequestFailed as exc:
        raise HTTPException(
            status_code=exc.status_code or 502,
            detail={
                "error": "binance_live_order_failed",
                "symbol": request.symbol.upper(),
                "message": str(exc),
                "provider_status": exc.status_code,
                "provider_response": exc.response_text,
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "binance_live_order_rejected",
                "symbol": request.symbol.upper(),
                "message": str(exc),
            },
        ) from exc
    services.audit_service.log(
        event_type="execution.live.manual",
        mode=settings.app_mode,
        symbol=request.symbol.upper(),
        message=result.message,
        rationale=request.rationale,
        status=result.status,
        raw_payload={"request": request.model_dump(), "result": result.model_dump()},
    )
    return result.model_dump()


@app.post("/execution/paper-order")
def execution_paper_order(
    request: PaperOrderRequest, services: AppServices = Depends(get_services)
) -> dict:
    result = services.paper_executor.execute(
        ExecutionRequest(
            symbol=request.symbol.upper(),
            side=request.side.upper(),
            quantity=request.quantity,
            price=request.price,
            rationale=request.rationale,
            confidence=request.confidence,
        )
    )
    services.audit_service.log(
        event_type="execution.paper.manual",
        mode=settings.app_mode,
        symbol=request.symbol.upper(),
        message=result.message,
        rationale=request.rationale,
        status=result.status,
        raw_payload={"request": request.model_dump(), "result": result.model_dump()},
    )
    return result.model_dump()


def _line_chart_svg(
    values: list[float],
    *,
    width: int,
    height: int,
    stroke: str,
    fill: str,
    empty_label: str,
) -> str:
    if not values:
        return f"<svg width='{width}' height='{height}'><text x='20' y='40' fill='#6b7280'>{empty_label}</text></svg>"

    min_value = min(values)
    max_value = max(values)
    spread = max(max_value - min_value, 1)
    step_x = width / max(len(values) - 1, 1)

    points = []
    for index, value in enumerate(values):
        x = index * step_x
        y = height - (((value - min_value) / spread) * (height - 30)) - 15
        points.append(f"{x:.2f},{y:.2f}")

    area_points = " ".join(points + [f"{width:.2f},{height:.2f}", f"0,{height:.2f}"])
    line_points = " ".join(points)

    return (
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='{height}'>"
        f"<polygon points='{area_points}' fill='{fill}' opacity='0.8'></polygon>"
        f"<polyline points='{line_points}' fill='none' stroke='{stroke}' stroke-width='3'></polyline>"
        f"</svg>"
    )


def _bar_chart_svg(
    labels: list[str],
    values: list[float],
    *,
    width: int,
    height: int,
    empty_label: str,
) -> str:
    if not values:
        return f"<svg width='{width}' height='{height}'><text x='20' y='40' fill='#6b7280'>{empty_label}</text></svg>"

    max_abs = max(max(abs(value) for value in values), 1)
    bar_width = max((width - 40) / max(len(values), 1) - 12, 20)
    zero_line = height / 2
    bars = []

    for index, value in enumerate(values):
        x = 20 + index * (bar_width + 12)
        scaled = (abs(value) / max_abs) * (height / 2 - 30)
        y = zero_line - scaled if value >= 0 else zero_line
        color = "#16a34a" if value >= 0 else "#dc2626"
        bars.append(
            f"<rect x='{x:.2f}' y='{y:.2f}' width='{bar_width:.2f}' height='{scaled:.2f}' fill='{color}' rx='6'></rect>"
            f"<text x='{x + (bar_width / 2):.2f}' y='{height - 8}' text-anchor='middle' font-size='12' fill='#4b5563'>{labels[index]}</text>"
        )

    return (
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='{height}'>"
        f"<line x1='0' y1='{zero_line:.2f}' x2='{width}' y2='{zero_line:.2f}' stroke='#cbd5e1' stroke-width='2'></line>"
        f"{''.join(bars)}"
        f"</svg>"
    )


def _normalize_number(number: str) -> str:
    return re.sub(r"\D", "", number)


def _extract_evolution_message(payload: dict) -> tuple[str | None, str | None, bool]:
    data = payload.get("data", payload)
    key = data.get("key", {})
    message = data.get("message", {})

    sender = key.get("remoteJid") or data.get("from") or data.get("sender")
    sender_digits = _normalize_number(sender or "")

    text = None
    if "conversation" in message:
        text = message.get("conversation")
    elif "extendedTextMessage" in message:
        text = (message.get("extendedTextMessage") or {}).get("text")
    elif "imageMessage" in message:
        text = (message.get("imageMessage") or {}).get("caption")

    from_me = bool(key.get("fromMe") or data.get("fromMe"))
    return sender_digits or None, text, from_me
