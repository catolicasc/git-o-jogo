from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.integrations.binance.binance_client import BinanceClient
from app.integrations.llm.openai_provider import OpenAiLlmProvider
from app.integrations.news.macro_provider import MacroProvider
from app.integrations.news.rss_news_provider import RssNewsProvider
from app.modules.agents.decision_engine import DecisionEngine
from app.modules.agents.research_agent import ResearchAgent
from app.modules.agents.risk_agent import RiskAgent
from app.modules.audit.audit_service import AuditService
from app.modules.audit.bot_voice_service import BotVoiceService
from app.modules.backtest.backtest_service import BacktestService
from app.modules.execution.binance_executor import BinanceExecutor
from app.modules.execution.paper_executor import PaperExecutor
from app.modules.health.health_service import HealthService
from app.modules.markets.markets_service import MarketsService
from app.modules.news.news_service import NewsService
from app.modules.portfolio.account_service import AccountService
from app.modules.portfolio.portfolio_history_service import PortfolioHistoryService
from app.modules.portfolio.performance_service import PerformanceService
from app.modules.portfolio.portfolio_service import PortfolioService
from app.modules.strategy.strategy_stats_service import StrategyStatsService
from app.modules.trades.reconciliation_service import ReconciliationService
from app.modules.trades.trades_service import TradesService


@dataclass
class AppServices:
    audit_service: AuditService
    bot_voice_service: BotVoiceService
    markets_service: MarketsService
    news_service: NewsService
    research_agent: ResearchAgent
    risk_agent: RiskAgent
    decision_engine: DecisionEngine
    portfolio_service: PortfolioService
    account_service: AccountService
    performance_service: PerformanceService
    portfolio_history_service: PortfolioHistoryService
    paper_executor: PaperExecutor
    binance_executor: BinanceExecutor
    reconciliation_service: ReconciliationService
    trades_service: TradesService
    health_service: HealthService
    backtest_service: BacktestService


def build_services(db: Session, mode: str) -> AppServices:
    binance_client = BinanceClient()
    macro_provider = MacroProvider()
    llm_provider = OpenAiLlmProvider()
    news_provider = RssNewsProvider()
    backtest_service = BacktestService(binance_client)
    strategy_stats_service = StrategyStatsService(backtest_service)
    audit_service = AuditService(db)
    markets_service = MarketsService(db, binance_client, macro_provider)
    news_service = NewsService(db, news_provider)
    research_agent = ResearchAgent(db, llm_provider, mode, strategy_stats_service)
    risk_agent = RiskAgent(db, mode)
    decision_engine = DecisionEngine()
    portfolio_service = PortfolioService(db, mode)
    account_service = AccountService(binance_client)
    performance_service = PerformanceService(db, account_service)
    portfolio_history_service = PortfolioHistoryService(db, performance_service, binance_client)
    bot_voice_service = BotVoiceService(db, mode, performance_service, account_service)
    paper_executor = PaperExecutor(db, mode, portfolio_service)
    binance_executor = BinanceExecutor(db, mode, binance_client, portfolio_service)
    reconciliation_service = ReconciliationService(db, binance_client, mode)
    trades_service = TradesService(db)
    health_service = HealthService(db)

    return AppServices(
        audit_service=audit_service,
        bot_voice_service=bot_voice_service,
        markets_service=markets_service,
        news_service=news_service,
        research_agent=research_agent,
        risk_agent=risk_agent,
        decision_engine=decision_engine,
        portfolio_service=portfolio_service,
        account_service=account_service,
        performance_service=performance_service,
        portfolio_history_service=portfolio_history_service,
        paper_executor=paper_executor,
        binance_executor=binance_executor,
        reconciliation_service=reconciliation_service,
        trades_service=trades_service,
        health_service=health_service,
        backtest_service=backtest_service,
    )
