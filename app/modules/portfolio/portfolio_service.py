from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.db.models import Position


class PortfolioService:
    def __init__(self, db: Session, mode: str) -> None:
        self.db = db
        self.mode = mode

    def upsert_filled_trade_position(self, *, symbol: str, side: str, price: float, quantity: float) -> Position | None:
        position = self.db.scalar(select(Position).where(Position.symbol == symbol).limit(1))

        if position is None and side == "SELL":
            return None

        if position is None:
            position = Position(
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                current_price=price,
                realized_pnl=0,
                unrealized_pnl=0,
                status="OPEN",
                mode=self.mode,
                raw_payload={"symbol": symbol, "side": side, "price": price, "quantity": quantity},
            )
            self.db.add(position)
            self.db.commit()
            self.db.refresh(position)
            return position

        if side == "BUY":
            total_quantity = position.quantity + quantity
            weighted_cost = (position.quantity * position.average_price) + (quantity * price)
            average_price = weighted_cost / total_quantity
            position.quantity = total_quantity
            position.average_price = average_price
            position.current_price = price
            position.unrealized_pnl = (price - average_price) * total_quantity
        else:
            remaining_quantity = max(position.quantity - quantity, 0)
            realized_pnl = (price - position.average_price) * quantity
            position.quantity = remaining_quantity
            position.current_price = price
            position.realized_pnl = (position.realized_pnl or 0) + realized_pnl
            position.unrealized_pnl = (price - position.average_price) * remaining_quantity
            position.status = "OPEN" if remaining_quantity > 0 else "CLOSED"

        position.raw_payload = {"symbol": symbol, "side": side, "price": price, "quantity": quantity}
        self.db.commit()
        self.db.refresh(position)
        return position

    def list_positions(self) -> list[Position]:
        return list(self.db.scalars(select(Position).order_by(Position.updated_at.desc())))
