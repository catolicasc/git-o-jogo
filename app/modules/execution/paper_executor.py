from sqlalchemy.orm import Session

from app.modules.portfolio.portfolio_service import PortfolioService
from app.shared.db.models import Trade
from app.shared.types.domain import ExecutionRequest, ExecutionResult

from .executor_interface import Executor


class PaperExecutor(Executor):
    def __init__(self, db: Session, mode: str, portfolio_service: PortfolioService) -> None:
        self.db = db
        self.mode = mode
        self.portfolio_service = portfolio_service

    def execute(self, order: ExecutionRequest) -> ExecutionResult:
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            price=order.price,
            quantity=order.quantity,
            status="FILLED",
            rationale=order.rationale,
            mode=self.mode,
            confidence=order.confidence,
            raw_payload=order.model_dump(),
        )
        self.db.add(trade)
        self.db.commit()

        self.portfolio_service.upsert_filled_trade_position(
            symbol=order.symbol, side=order.side, price=order.price, quantity=order.quantity
        )

        return ExecutionResult(
            status="FILLED",
            message="Paper order filled successfully",
            raw_payload=order.model_dump(),
        )
