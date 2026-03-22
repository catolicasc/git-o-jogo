from __future__ import annotations

from app.config.settings import get_settings
from app.shared.types.domain import MarketContext, ResearchThesis
from app.shared.utils.indicators import momentum, rsi, simple_moving_average, volatility


class StrategyEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_thesis(
        self,
        *,
        symbol: str,
        market: MarketContext,
        analysis: dict | None = None,
        setup_stats: dict | None = None,
        auxiliary_context: dict | None = None,
    ) -> ResearchThesis:
        analysis = analysis or self.analyze_market(symbol=symbol, market=market)
        selected_setup = analysis["selected_setup"]
        auxiliary_context = auxiliary_context or {}
        llm_context = auxiliary_context.get("llm_summary")
        context_suffix = f" Aux={llm_context}" if llm_context else ""

        if selected_setup is None:
            return ResearchThesis(
                symbol=symbol,
                direction="NONE",
                confidence=0.45,
                reasoning=(
                    f"No deterministic setup active. Regime={analysis['regime']['combined_regime']} "
                    f"trend={analysis['regime']['trend_regime']} volatility={analysis['regime']['volatility_regime']}."
                    f"{context_suffix}"
                ),
                source_urls=auxiliary_context.get("source_urls", []),
                regime=analysis["regime"]["combined_regime"],
                stats=setup_stats or {},
                auxiliary_context=auxiliary_context,
            )

        if setup_stats and not bool(setup_stats.get("enabled", True)):
            return ResearchThesis(
                symbol=symbol,
                direction="NONE",
                confidence=0.45,
                reasoning=(
                    f"Setup {selected_setup['setup_id']} desativado pela revisao trimestral. "
                    f"Regime={analysis['regime']['combined_regime']} "
                    f"motivo={setup_stats.get('disable_reason', 'Edge insuficiente')}."
                    f"{context_suffix}"
                ),
                source_urls=auxiliary_context.get("source_urls", []),
                setup_id=selected_setup["setup_id"],
                regime=analysis["regime"]["combined_regime"],
                stats=setup_stats or {},
                auxiliary_context=auxiliary_context,
            )

        direction = "BUY" if selected_setup["side"] == "BUY" else "SELL"
        posterior_win_probability = float((setup_stats or {}).get("win_probability") or 0)
        derived_confidence = selected_setup["confidence"]
        if posterior_win_probability > 0:
            derived_confidence = max(derived_confidence, min(posterior_win_probability, 0.95))
        reasoning = (
            f"Setup={selected_setup['setup_id']} regime={analysis['regime']['combined_regime']} "
            f"entry_rule={selected_setup['entry_rule']} "
            f"exit_rule=stop {self.settings.stop_loss_pct * 100:.1f}% / take {self.settings.take_profit_pct * 100:.1f}% "
            f"confidence={derived_confidence:.2f}."
        )
        if setup_stats:
            reasoning += (
                f" Historical pwin={float(setup_stats.get('win_probability', 0)):.2f} "
                f"ev={float(setup_stats.get('expectancy_pct', 0)):.2f}% "
                f"kelly={float(setup_stats.get('kelly_fraction', 0)):.2f} "
                f"samples={int(setup_stats.get('trades', 0))}."
            )
        if context_suffix:
            reasoning += context_suffix

        return ResearchThesis(
            symbol=symbol,
            direction=direction,
            confidence=min(derived_confidence, 0.95),
            reasoning=reasoning,
            source_urls=auxiliary_context.get("source_urls", []),
            setup_id=selected_setup["setup_id"],
            regime=analysis["regime"]["combined_regime"],
            stats=setup_stats or {},
            auxiliary_context=auxiliary_context,
        )

    def analyze_market(self, *, symbol: str, market: MarketContext) -> dict:
        candles = [self._parse_kline(item) for item in market.klines or [] if len(item) >= 6]
        return self.analyze_candles(symbol=symbol, candles=candles)

    def analyze_candles(self, *, symbol: str, candles: list[dict]) -> dict:
        indicators = self._build_indicator_snapshot(candles)
        regime = self._classify_regime(indicators)
        setups = self._detect_setups(symbol=symbol, indicators=indicators, regime=regime)
        selected_setup = max(setups, key=lambda item: item["confidence"]) if setups else None
        return {
            "symbol": symbol,
            "regime": regime,
            "indicators": indicators,
            "setups": setups,
            "selected_setup": selected_setup,
        }

    def _build_indicator_snapshot(self, candles: list[dict]) -> dict:
        closes = [item["close"] for item in candles]
        highs = [item["high"] for item in candles]
        lows = [item["low"] for item in candles]
        volumes = [item["volume"] for item in candles]

        sma_9 = simple_moving_average(closes, 9)
        sma_21 = simple_moving_average(closes, 21)
        rsi_14 = rsi(closes, 14)
        momentum_10 = momentum(closes, 10)
        volatility_14 = volatility(closes, 14)
        last_close = closes[-1] if closes else None
        last_high = highs[-1] if highs else None
        last_low = lows[-1] if lows else None
        last_volume = volumes[-1] if volumes else None
        volume_avg_10 = simple_moving_average(volumes, 10)

        trend_strength_pct = 0.0
        if last_close and sma_9 and sma_21 and last_close > 0:
            trend_strength_pct = abs(sma_9 - sma_21) / last_close * 100

        normalized_volatility_pct = 0.0
        if last_close and volatility_14 and last_close > 0:
            normalized_volatility_pct = volatility_14 / last_close * 100

        recent_breakout_high = max(highs[-20:-1]) if len(highs) >= 20 else None
        recent_breakout_low = min(lows[-20:-1]) if len(lows) >= 20 else None

        return {
            "last_close": last_close,
            "last_high": last_high,
            "last_low": last_low,
            "last_volume": last_volume,
            "sma_9": sma_9,
            "sma_21": sma_21,
            "rsi_14": rsi_14,
            "momentum_10": momentum_10,
            "volatility_14": volatility_14,
            "volume_avg_10": volume_avg_10,
            "trend_strength_pct": trend_strength_pct,
            "normalized_volatility_pct": normalized_volatility_pct,
            "recent_breakout_high": recent_breakout_high,
            "recent_breakout_low": recent_breakout_low,
        }

    def _classify_regime(self, indicators: dict) -> dict:
        trend_regime = "UNDEFINED"
        trend_direction = "FLAT"
        volatility_regime = "LOW_VOL"

        sma_9 = indicators["sma_9"]
        sma_21 = indicators["sma_21"]
        momentum_10 = indicators["momentum_10"]
        trend_strength_pct = indicators["trend_strength_pct"]
        normalized_volatility_pct = indicators["normalized_volatility_pct"]

        if isinstance(normalized_volatility_pct, (int, float)) and normalized_volatility_pct >= 1.1:
            volatility_regime = "HIGH_VOL"

        if (
            isinstance(sma_9, (int, float))
            and isinstance(sma_21, (int, float))
            and isinstance(momentum_10, (int, float))
        ):
            if sma_9 > sma_21 and momentum_10 > 0.4 and trend_strength_pct >= 0.18:
                trend_regime = "TRENDING"
                trend_direction = "UP"
            elif sma_9 < sma_21 and momentum_10 < -0.4 and trend_strength_pct >= 0.18:
                trend_regime = "TRENDING"
                trend_direction = "DOWN"
            else:
                trend_regime = "RANGING"

        return {
            "trend_regime": trend_regime,
            "trend_direction": trend_direction,
            "volatility_regime": volatility_regime,
            "combined_regime": f"{trend_regime}_{volatility_regime}_{trend_direction}",
        }

    def _detect_setups(self, *, symbol: str, indicators: dict, regime: dict) -> list[dict]:
        setups: list[dict] = []

        last_close = indicators["last_close"]
        sma_9 = indicators["sma_9"]
        sma_21 = indicators["sma_21"]
        rsi_14 = indicators["rsi_14"]
        momentum_10 = indicators["momentum_10"]
        volume_avg_10 = indicators["volume_avg_10"]
        last_volume = indicators["last_volume"]
        recent_breakout_high = indicators["recent_breakout_high"]
        recent_breakout_low = indicators["recent_breakout_low"]

        trend_direction = regime["trend_direction"]
        trend_regime = regime["trend_regime"]
        volatility_regime = regime["volatility_regime"]

        if not isinstance(last_close, (int, float)):
            return setups

        if (
            trend_regime == "TRENDING"
            and trend_direction == "UP"
            and isinstance(rsi_14, (int, float))
            and isinstance(sma_21, (int, float))
            and rsi_14 <= 38
            and last_close >= sma_21 * 0.995
        ):
            setups.append(
                self._setup(
                    symbol=symbol,
                    setup_id="rsi_oversold_trend_long",
                    side="BUY",
                    confidence=0.74,
                    entry_rule="RSI <= 38 com tendencia de alta e preco acima/encostando na SMA21",
                )
            )

        if (
            trend_regime == "TRENDING"
            and trend_direction == "DOWN"
            and isinstance(rsi_14, (int, float))
            and isinstance(sma_21, (int, float))
            and rsi_14 >= 62
            and last_close <= sma_21 * 1.005
        ):
            setups.append(
                self._setup(
                    symbol=symbol,
                    setup_id="rsi_overbought_trend_short",
                    side="SELL",
                    confidence=0.74,
                    entry_rule="RSI >= 62 com tendencia de baixa e preco abaixo/encostando na SMA21",
                )
            )

        if (
            trend_regime == "TRENDING"
            and trend_direction == "UP"
            and isinstance(recent_breakout_high, (int, float))
            and isinstance(last_volume, (int, float))
            and isinstance(volume_avg_10, (int, float))
            and last_close > recent_breakout_high
            and last_volume >= volume_avg_10 * 1.35
        ):
            setups.append(
                self._setup(
                    symbol=symbol,
                    setup_id="breakout_volume_long",
                    side="BUY",
                    confidence=0.78 if volatility_regime == "HIGH_VOL" else 0.73,
                    entry_rule="Fechamento acima da maxima de 20 candles com expansao de volume",
                )
            )

        if (
            trend_regime == "TRENDING"
            and trend_direction == "DOWN"
            and isinstance(recent_breakout_low, (int, float))
            and isinstance(last_volume, (int, float))
            and isinstance(volume_avg_10, (int, float))
            and last_close < recent_breakout_low
            and last_volume >= volume_avg_10 * 1.35
        ):
            setups.append(
                self._setup(
                    symbol=symbol,
                    setup_id="breakout_volume_short",
                    side="SELL",
                    confidence=0.78 if volatility_regime == "HIGH_VOL" else 0.73,
                    entry_rule="Fechamento abaixo da minima de 20 candles com expansao de volume",
                )
            )

        if (
            trend_regime == "TRENDING"
            and trend_direction == "UP"
            and isinstance(sma_9, (int, float))
            and isinstance(sma_21, (int, float))
            and isinstance(rsi_14, (int, float))
            and sma_21 <= last_close <= sma_9 * 1.005
            and 42 <= rsi_14 <= 58
        ):
            setups.append(
                self._setup(
                    symbol=symbol,
                    setup_id="pullback_sma_long",
                    side="BUY",
                    confidence=0.7,
                    entry_rule="Pullback entre SMA21 e SMA9 em tendencia de alta",
                )
            )

        if (
            trend_regime == "TRENDING"
            and trend_direction == "DOWN"
            and isinstance(sma_9, (int, float))
            and isinstance(sma_21, (int, float))
            and isinstance(rsi_14, (int, float))
            and sma_9 * 0.995 <= last_close <= sma_21
            and 42 <= rsi_14 <= 58
        ):
            setups.append(
                self._setup(
                    symbol=symbol,
                    setup_id="pullback_sma_short",
                    side="SELL",
                    confidence=0.7,
                    entry_rule="Pullback entre SMA9 e SMA21 em tendencia de baixa",
                )
            )

        return setups

    def _setup(
        self,
        *,
        symbol: str,
        setup_id: str,
        side: str,
        confidence: float,
        entry_rule: str,
    ) -> dict:
        return {
            "symbol": symbol,
            "setup_id": setup_id,
            "side": side,
            "confidence": confidence,
            "entry_rule": entry_rule,
            "stop_loss_pct": self.settings.stop_loss_pct,
            "take_profit_pct": self.settings.take_profit_pct,
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
