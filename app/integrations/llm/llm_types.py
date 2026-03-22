from typing import Protocol

from app.shared.types.domain import ResearchThesis


class LlmProvider(Protocol):
    def generate_research_thesis(
        self, symbol: str, market_summary: dict, news_summary: list[dict]
    ) -> ResearchThesis: ...
