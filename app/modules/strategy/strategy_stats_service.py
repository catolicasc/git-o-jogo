from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config.settings import get_settings
from app.modules.backtest.backtest_service import BacktestService


class StrategyStatsService:
    def __init__(self, backtest_service: BacktestService) -> None:
        self.settings = get_settings()
        self.backtest_service = backtest_service
        self._cache: dict[tuple[str, str, int, int], dict] = {}

    def get_setup_stats(
        self,
        *,
        symbol: str,
        setup_id: str | None,
        regime: str | None,
    ) -> dict:
        report = self._symbol_report(symbol)
        summary = report.get("summary", {})
        by_setup_regime = {
            item["group"]: item
            for item in report.get("by_setup_regime", [])
        }
        by_setup = {
            item["group"]: item
            for item in report.get("by_setup", [])
        }

        if setup_id and regime:
            key = f"{setup_id}|{regime}"
            if key in by_setup_regime:
                return self._decorate_stats(by_setup_regime[key])

        if setup_id and setup_id in by_setup:
            return self._decorate_stats(by_setup[setup_id])

        return self._decorate_stats(summary, setup_id=setup_id, regime=regime)

    def get_ranked_setups(self, *, symbols: list[str] | None = None) -> list[dict]:
        rankings: list[dict] = []
        for symbol in (symbols or self.settings.symbols):
            report = self._symbol_report(symbol)
            for item in report.get("by_setup_regime", []):
                setup_id, _, regime = item.get("group", "").partition("|")
                enriched = self._decorate_stats(item, setup_id=setup_id, regime=regime)
                rankings.append(
                    {
                        "symbol": symbol,
                        "setup_id": setup_id,
                        "regime": regime,
                        **enriched,
                    }
                )

        return sorted(
            rankings,
            key=lambda item: (
                1 if item.get("enabled") else 0,
                float(item.get("expectancy_pct") or 0),
                float(item.get("profit_factor_value") or 0),
                int(item.get("trades") or 0),
            ),
            reverse=True,
        )

    def _decorate_stats(
        self,
        stats: dict,
        *,
        setup_id: str | None = None,
        regime: str | None = None,
    ) -> dict:
        enriched = dict(stats or {})
        profit_factor = enriched.get("profit_factor", 0)
        try:
            profit_factor_value = float(profit_factor)
        except (TypeError, ValueError):
            profit_factor_value = 999.0 if profit_factor == "inf" else 0.0

        trades = int(enriched.get("trades") or 0)
        expectancy_pct = float(enriched.get("expectancy_pct") or 0)
        kelly_fraction = float(enriched.get("kelly_fraction") or 0)
        enabled = True
        disable_reason = ""

        if setup_id is None:
            enabled = False
            disable_reason = "No active setup"
        elif trades < self.settings.strategy_min_sample_size:
            enabled = False
            disable_reason = (
                f"Sample too small ({trades}/{self.settings.strategy_min_sample_size})"
            )
        elif expectancy_pct <= 0:
            enabled = False
            disable_reason = "Expectancy non-positive in quarter"
        elif profit_factor_value < self.settings.strategy_min_profit_factor:
            enabled = False
            disable_reason = (
                f"Profit factor below threshold ({profit_factor_value:.2f}/{self.settings.strategy_min_profit_factor:.2f})"
            )
        elif kelly_fraction <= 0:
            enabled = False
            disable_reason = "Kelly fraction non-positive"

        enriched["setup_id"] = setup_id
        enriched["regime"] = regime
        enriched["profit_factor_value"] = round(profit_factor_value, 4)
        enriched["enabled"] = enabled
        enriched["disable_reason"] = disable_reason
        return enriched

    def _symbol_report(self, symbol: str) -> dict:
        end_time = int(datetime.now(UTC).timestamp() * 1000)
        start_time = int(
            (datetime.now(UTC) - timedelta(days=self.settings.strategy_review_days)).timestamp()
            * 1000
        )
        cache_key = (
            symbol,
            self.settings.strategy_backtest_interval,
            self.settings.strategy_backtest_limit,
            self.settings.strategy_max_holding_bars,
            start_time,
            end_time,
        )
        if cache_key not in self._cache:
            self._cache[cache_key] = self.backtest_service.run(
                symbols=[symbol],
                interval=self.settings.strategy_backtest_interval,
                limit=self.settings.strategy_backtest_limit,
                max_holding_bars=self.settings.strategy_max_holding_bars,
                start_time=start_time,
                end_time=end_time,
            )
        return self._cache[cache_key]
