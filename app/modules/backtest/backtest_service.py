from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from math import inf, log

from app.config.settings import get_settings
from app.integrations.binance.binance_client import BinanceClient
from app.modules.strategy.strategy_engine import StrategyEngine


@dataclass
class SimulatedTrade:
    symbol: str
    setup: str
    regime: str
    side: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    stop_price: float
    take_profit_price: float
    pnl_pct: float
    pnl_usd: float
    holding_bars: int
    exit_reason: str
    confidence: float
    log_return: float
    max_adverse_excursion_pct: float
    max_favorable_excursion_pct: float


class BacktestService:
    def __init__(self, binance_client: BinanceClient | None = None) -> None:
        self.settings = get_settings()
        self.binance_client = binance_client or BinanceClient()
        self.strategy_engine = StrategyEngine()

    def run(
        self,
        *,
        symbols: list[str] | None = None,
        interval: str | None = None,
        limit: int | None = None,
        initial_capital: float | None = None,
        max_holding_bars: int = 16,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict:
        symbols = symbols or self.settings.symbols
        interval = interval or self.settings.strategy_backtest_interval
        limit = limit or self.settings.strategy_backtest_limit
        initial_capital = initial_capital or self.settings.default_bankroll_usd
        end_time = end_time or int(datetime.now(UTC).timestamp() * 1000)
        if start_time is None:
            start_time = int(
                (datetime.now(UTC) - timedelta(days=self.settings.strategy_review_days)).timestamp()
                * 1000
            )
        all_trades: list[SimulatedTrade] = []

        for symbol in symbols:
            klines = self.binance_client.get_klines(
                symbol,
                interval=interval,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )
            all_trades.extend(
                self._simulate_symbol(
                    symbol=symbol,
                    klines=klines,
                    bankroll_usd=initial_capital,
                    max_holding_bars=max_holding_bars,
                )
            )

        equity_curve = self._build_equity_curve(all_trades, initial_capital)
        return {
            "metadata": {
                "symbols": symbols,
                "interval": interval,
                "bars_requested": limit,
                "start_time": start_time,
                "end_time": end_time,
                "review_days": self.settings.strategy_review_days,
                "initial_capital": round(initial_capital, 2),
                "max_holding_bars": max_holding_bars,
                "stop_loss_pct": self.settings.stop_loss_pct,
                "take_profit_pct": self.settings.take_profit_pct,
                "risk_per_trade": self.settings.max_risk_per_trade,
            },
            "summary": self._summarize_trades(all_trades, initial_capital, equity_curve),
            "by_setup": self._group_summary(all_trades, key_fn=lambda trade: trade.setup),
            "by_setup_regime": self._group_summary(
                all_trades,
                key_fn=lambda trade: f"{trade.setup}|{trade.regime}",
            ),
            "by_regime": self._group_summary(all_trades, key_fn=lambda trade: trade.regime),
            "by_symbol": self._group_summary(all_trades, key_fn=lambda trade: trade.symbol),
            "by_side": self._group_summary(all_trades, key_fn=lambda trade: trade.side),
            "equity_curve": equity_curve,
            "trades": [self._trade_to_dict(trade) for trade in all_trades],
        }

    def _simulate_symbol(
        self,
        *,
        symbol: str,
        klines: list,
        bankroll_usd: float,
        max_holding_bars: int,
    ) -> list[SimulatedTrade]:
        candles = [self._parse_kline(item) for item in klines if len(item) >= 6]
        if len(candles) < 40:
            return []

        trades: list[SimulatedTrade] = []
        active_until = -1
        max_usd_exposure = bankroll_usd * self.settings.max_risk_per_trade

        for index in range(21, len(candles) - 1):
            if index <= active_until:
                continue

            history = candles[: index + 1]
            analysis = self.strategy_engine.analyze_candles(symbol=symbol, candles=history)
            selected = analysis["selected_setup"]
            if selected is None:
                continue

            trade = self._simulate_trade(
                symbol=symbol,
                setup=selected["setup_id"],
                regime=analysis["regime"]["combined_regime"],
                side=selected["side"],
                confidence=selected["confidence"],
                entry_index=index + 1,
                candles=candles,
                max_usd_exposure=max_usd_exposure,
                max_holding_bars=max_holding_bars,
            )
            if trade is None:
                continue

            trades.append(trade)
            active_until = trade.holding_bars + index

        return trades

    def _simulate_trade(
        self,
        *,
        symbol: str,
        setup: str,
        regime: str,
        side: str,
        confidence: float,
        entry_index: int,
        candles: list[dict],
        max_usd_exposure: float,
        max_holding_bars: int,
    ) -> SimulatedTrade | None:
        if entry_index >= len(candles):
            return None

        entry_candle = candles[entry_index]
        entry_price = entry_candle["open"]
        if entry_price <= 0:
            return None

        quantity = max_usd_exposure / entry_price
        stop_pct = self.settings.stop_loss_pct
        take_pct = self.settings.take_profit_pct

        if side == "BUY":
            stop_price = entry_price * (1 - stop_pct)
            take_profit_price = entry_price * (1 + take_pct)
        else:
            stop_price = entry_price * (1 + stop_pct)
            take_profit_price = entry_price * (1 - take_pct)

        max_adverse_excursion_pct = 0.0
        max_favorable_excursion_pct = 0.0
        exit_index = min(entry_index + max_holding_bars, len(candles) - 1)
        exit_price = candles[exit_index]["close"]
        exit_reason = "TIMEOUT"

        for index in range(entry_index, min(entry_index + max_holding_bars + 1, len(candles))):
            candle = candles[index]

            if side == "BUY":
                favorable = ((candle["high"] - entry_price) / entry_price) * 100
                adverse = ((candle["low"] - entry_price) / entry_price) * 100
            else:
                favorable = ((entry_price - candle["low"]) / entry_price) * 100
                adverse = ((entry_price - candle["high"]) / entry_price) * 100

            max_favorable_excursion_pct = max(max_favorable_excursion_pct, favorable)
            max_adverse_excursion_pct = min(max_adverse_excursion_pct, adverse)

            if side == "BUY":
                hit_stop = candle["low"] <= stop_price
                hit_take = candle["high"] >= take_profit_price
            else:
                hit_stop = candle["high"] >= stop_price
                hit_take = candle["low"] <= take_profit_price

            if hit_stop and hit_take:
                exit_price = stop_price
                exit_reason = "STOP_AND_TAKE_SAME_BAR"
                exit_index = index
                break
            if hit_stop:
                exit_price = stop_price
                exit_reason = "STOP_LOSS"
                exit_index = index
                break
            if hit_take:
                exit_price = take_profit_price
                exit_reason = "TAKE_PROFIT"
                exit_index = index
                break

            exit_price = candle["close"]
            exit_index = index

        pnl_pct = (
            ((exit_price - entry_price) / entry_price) * 100
            if side == "BUY"
            else ((entry_price - exit_price) / entry_price) * 100
        )
        pnl_usd = (exit_price - entry_price) * quantity if side == "BUY" else (entry_price - exit_price) * quantity
        log_return = log(exit_price / entry_price) if side == "BUY" else log(entry_price / exit_price)

        return SimulatedTrade(
            symbol=symbol,
            setup=setup,
            regime=regime,
            side=side,
            entry_time=entry_candle["open_time"],
            exit_time=candles[exit_index]["close_time"],
            entry_price=entry_price,
            exit_price=exit_price,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
            pnl_pct=round(pnl_pct, 4),
            pnl_usd=round(pnl_usd, 4),
            holding_bars=exit_index - entry_index + 1,
            exit_reason=exit_reason,
            confidence=confidence,
            log_return=round(log_return, 6),
            max_adverse_excursion_pct=round(max_adverse_excursion_pct, 4),
            max_favorable_excursion_pct=round(max_favorable_excursion_pct, 4),
        )

    def _build_equity_curve(self, trades: list[SimulatedTrade], initial_capital: float) -> list[dict]:
        equity = initial_capital
        points = [{"index": 0, "equity": round(equity, 4), "drawdown_pct": 0.0}]
        peak = equity

        for index, trade in enumerate(sorted(trades, key=lambda item: item.exit_time), start=1):
            equity += trade.pnl_usd
            peak = max(peak, equity)
            drawdown_pct = ((equity - peak) / peak) * 100 if peak else 0.0
            points.append(
                {
                    "index": index,
                    "equity": round(equity, 4),
                    "drawdown_pct": round(drawdown_pct, 4),
                    "symbol": trade.symbol,
                    "setup": trade.setup,
                    "regime": trade.regime,
                }
            )

        return points

    def _summarize_trades(
        self,
        trades: list[SimulatedTrade],
        initial_capital: float,
        equity_curve: list[dict],
    ) -> dict:
        metrics = self._compute_metrics(trades)
        final_equity = equity_curve[-1]["equity"] if equity_curve else initial_capital
        total_return_pct = ((final_equity - initial_capital) / initial_capital) * 100 if initial_capital else 0.0
        max_drawdown_pct = min((point["drawdown_pct"] for point in equity_curve), default=0.0)

        return {
            **metrics,
            "initial_capital": round(initial_capital, 2),
            "final_equity": round(final_equity, 2),
            "net_profit": round(final_equity - initial_capital, 2),
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
        }

    def _group_summary(self, trades: list[SimulatedTrade], *, key_fn) -> list[dict]:
        grouped: dict[str, list[SimulatedTrade]] = {}
        for trade in trades:
            key = key_fn(trade)
            grouped.setdefault(key, []).append(trade)

        return [
            {"group": key, **self._compute_metrics(items)}
            for key, items in sorted(grouped.items())
        ]

    def _compute_metrics(self, trades: list[SimulatedTrade]) -> dict:
        total = len(trades)
        if total == 0:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "win_rate_pct": 0.0,
                "avg_pnl_usd": 0.0,
                "avg_pnl_pct": 0.0,
                "avg_win_usd": 0.0,
                "avg_loss_usd": 0.0,
                "payoff_ratio": 0.0,
                "profit_factor": 0.0,
                "expectancy_usd": 0.0,
                "expectancy_pct": 0.0,
                "avg_holding_bars": 0.0,
            }

        wins = [trade for trade in trades if trade.pnl_usd > 0]
        losses = [trade for trade in trades if trade.pnl_usd < 0]
        breakeven = total - len(wins) - len(losses)
        gross_profit = sum(trade.pnl_usd for trade in wins)
        gross_loss = abs(sum(trade.pnl_usd for trade in losses))
        avg_win_usd = gross_profit / len(wins) if wins else 0.0
        avg_loss_usd = abs(sum(trade.pnl_usd for trade in losses) / len(losses)) if losses else 0.0
        win_rate = len(wins) / total
        loss_rate = len(losses) / total
        expectancy_usd = (win_rate * avg_win_usd) - (loss_rate * avg_loss_usd)
        avg_pnl_usd = sum(trade.pnl_usd for trade in trades) / total
        avg_pnl_pct = sum(trade.pnl_pct for trade in trades) / total
        avg_log_return = sum(trade.log_return for trade in trades) / total
        cumulative_log_return = sum(trade.log_return for trade in trades)
        payoff_ratio = (avg_win_usd / avg_loss_usd) if avg_loss_usd > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else inf if gross_profit > 0 else 0.0
        posterior_win_probability = (len(wins) + 1) / (total + 2)
        kelly_fraction = 0.0
        if avg_loss_usd > 0 and payoff_ratio > 0:
            kelly_fraction = posterior_win_probability - ((1 - posterior_win_probability) / payoff_ratio)
        consistency_pct = (len(wins) / total) * 100 if total else 0.0

        return {
            "trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": breakeven,
            "win_rate_pct": round(win_rate * 100, 2),
            "win_probability": round(posterior_win_probability, 4),
            "avg_pnl_usd": round(avg_pnl_usd, 4),
            "avg_pnl_pct": round(avg_pnl_pct, 4),
            "avg_log_return": round(avg_log_return, 6),
            "cumulative_log_return": round(cumulative_log_return, 6),
            "avg_win_usd": round(avg_win_usd, 4),
            "avg_loss_usd": round(avg_loss_usd, 4),
            "payoff_ratio": round(payoff_ratio, 4),
            "profit_factor": "inf" if profit_factor == inf else round(profit_factor, 4),
            "expectancy_usd": round(expectancy_usd, 4),
            "expectancy_pct": round(avg_pnl_pct, 4),
            "kelly_fraction": round(max(0.0, min(kelly_fraction, 1.0)), 4),
            "consistency_pct": round(consistency_pct, 2),
            "avg_holding_bars": round(sum(trade.holding_bars for trade in trades) / total, 2),
        }

    def _parse_kline(self, item: list) -> dict:
        return {
            "open_time": int(item[0]),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5]),
            "close_time": int(item[6]),
        }

    def _trade_to_dict(self, trade: SimulatedTrade) -> dict:
        return {
            "symbol": trade.symbol,
            "setup": trade.setup,
            "regime": trade.regime,
            "side": trade.side,
            "entry_time": trade.entry_time,
            "exit_time": trade.exit_time,
            "entry_price": round(trade.entry_price, 6),
            "exit_price": round(trade.exit_price, 6),
            "stop_price": round(trade.stop_price, 6),
            "take_profit_price": round(trade.take_profit_price, 6),
            "pnl_pct": trade.pnl_pct,
            "pnl_usd": trade.pnl_usd,
            "holding_bars": trade.holding_bars,
            "exit_reason": trade.exit_reason,
            "confidence": trade.confidence,
            "log_return": trade.log_return,
            "max_adverse_excursion_pct": trade.max_adverse_excursion_pct,
            "max_favorable_excursion_pct": trade.max_favorable_excursion_pct,
        }
