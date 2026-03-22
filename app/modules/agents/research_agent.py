from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.llm.llm_types import LlmProvider
from app.modules.strategy.strategy_engine import StrategyEngine
from app.modules.strategy.strategy_stats_service import StrategyStatsService
from app.shared.db.models import Thesis
from app.shared.types.domain import MarketContext, NewsContext, ResearchThesis


class ResearchAgent:
    def __init__(
        self,
        db: Session,
        llm_provider: LlmProvider,
        mode: str,
        strategy_stats_service: StrategyStatsService,
    ) -> None:
        self.db = db
        self.llm_provider = llm_provider
        self.mode = mode
        self.strategy_engine = StrategyEngine()
        self.strategy_stats_service = strategy_stats_service

    def generate(self, symbol: str, market: MarketContext, news: list[NewsContext]) -> ResearchThesis:
        analysis = self.strategy_engine.analyze_market(symbol=symbol, market=market)
        selected_setup = analysis["selected_setup"]
        setup_stats = self.strategy_stats_service.get_setup_stats(
            symbol=symbol,
            setup_id=selected_setup["setup_id"] if selected_setup else None,
            regime=analysis["regime"]["combined_regime"],
        )
        auxiliary_context = self._build_auxiliary_context(symbol=symbol, market=market, news=news)
        thesis = self.strategy_engine.build_thesis(
            symbol=symbol,
            market=market,
            analysis=analysis,
            setup_stats=setup_stats,
            auxiliary_context=auxiliary_context,
        )

        self.db.add(
            Thesis(
                symbol=thesis.symbol,
                direction=thesis.direction,
                confidence=thesis.confidence,
                reasoning=thesis.reasoning,
                source_urls=thesis.source_urls,
                rationale=thesis.reasoning,
                mode=self.mode,
                raw_payload=thesis.model_dump(),
            )
        )
        self.db.commit()
        return thesis

    def _build_auxiliary_context(
        self,
        *,
        symbol: str,
        market: MarketContext,
        news: list[NewsContext],
    ) -> dict:
        news_payload = [item.model_dump() for item in news[:5]]
        market_payload = market.model_dump()

        try:
            auxiliary = self.llm_provider.generate_research_thesis(
                symbol=symbol,
                market_summary=market_payload,
                news_summary=news_payload,
            )
            return {
                "llm_summary": auxiliary.reasoning,
                "source_urls": auxiliary.source_urls,
            }
        except Exception:
            return {
                "llm_summary": "",
                "source_urls": [],
            }

    def list_theses(self) -> list[Thesis]:
        return list(self.db.scalars(select(Thesis).order_by(Thesis.created_at.desc()).limit(100)))
