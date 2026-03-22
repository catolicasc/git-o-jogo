import json

from openai import OpenAI

from app.config.logging import logger
from app.config.settings import get_settings
from app.integrations.llm.llm_types import LlmProvider
from app.shared.types.domain import ResearchThesis


class OpenAiLlmProvider(LlmProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def generate_research_thesis(
        self, symbol: str, market_summary: dict, news_summary: list[dict]
    ) -> ResearchThesis:
        if self.client is None:
            return self._fallback(symbol, market_summary, news_summary)

        prompt = "\n".join(
            [
                "You are a crypto spot research analyst.",
                "Return JSON only with keys: symbol, direction, confidence, reasoning, source_urls.",
                "direction must be BUY, SELL, or NONE.",
                f"Symbol: {symbol}",
                "You must consider indicators, macro context, real news, and market structure.",
                "Prefer NONE when signal quality is mixed.",
                f"Market summary: {json.dumps(market_summary)}",
                f"News summary: {json.dumps(news_summary)}",
            ]
        )

        try:
            response = self.client.responses.create(model="gpt-4.1-mini", input=prompt)
            payload = json.loads(response.output_text)
            return ResearchThesis(
                symbol=payload.get("symbol", symbol),
                direction=payload.get("direction", "NONE"),
                confidence=float(payload.get("confidence", 0)),
                reasoning=payload.get("reasoning", "No reasoning provided"),
                source_urls=payload.get("source_urls", []),
            )
        except Exception as exc:
            logger.warning("OpenAI thesis generation failed, using fallback: %s", exc)
            return self._fallback(symbol, market_summary, news_summary)

    def _fallback(
        self,
        symbol: str,
        market_summary: dict,
        news_summary: list[dict],
    ) -> ResearchThesis:
        indicators = market_summary.get("indicators") or {}
        macro = market_summary.get("macro") or {}
        rsi_value = indicators.get("rsi_14")
        sma_9 = indicators.get("sma_9")
        sma_21 = indicators.get("sma_21")
        fear_greed = (macro.get("fear_and_greed") or {}).get("value")
        symbol_news = [item for item in news_summary if item.get("symbol") in {None, symbol}]

        direction = "NONE"
        confidence = 0.45
        reasons = ["Fallback strategy active."]

        if (
            isinstance(rsi_value, (int, float))
            and isinstance(sma_9, (int, float))
            and isinstance(sma_21, (int, float))
        ):
            if rsi_value < 35 and sma_9 > sma_21:
                direction = "BUY"
                confidence = 0.72
                reasons.append("RSI indicates oversold recovery with bullish short-term trend.")
            elif rsi_value > 68 and sma_9 < sma_21:
                direction = "SELL"
                confidence = 0.72
                reasons.append("RSI indicates overbought weakness with bearish short-term trend.")

        if isinstance(fear_greed, int):
            reasons.append(f"Fear and Greed index at {fear_greed}.")
            if direction == "BUY" and fear_greed < 30:
                confidence += 0.04
            if direction == "SELL" and fear_greed > 70:
                confidence += 0.04

        if symbol_news:
            reasons.append(f"Using {len(symbol_news)} real news items as context.")

        return ResearchThesis(
            symbol=symbol,
            direction=direction,
            confidence=min(confidence, 0.9),
            reasoning=" ".join(reasons),
            source_urls=[item.get("url") for item in symbol_news if item.get("url")],
        )
