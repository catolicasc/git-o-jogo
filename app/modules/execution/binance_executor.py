from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.integrations.binance.binance_client import BinanceClient
from app.modules.portfolio.portfolio_service import PortfolioService
from app.shared.db.models import Trade
from app.shared.types.domain import ExecutionRequest, ExecutionResult

from .executor_interface import Executor


class BinanceExecutor(Executor):
    def __init__(
        self,
        db: Session,
        mode: str,
        binance_client: BinanceClient,
        portfolio_service: PortfolioService,
    ) -> None:
        self.db = db
        self.mode = mode
        self.binance_client = binance_client
        self.portfolio_service = portfolio_service
        self.settings = get_settings()

    def execute(self, order: ExecutionRequest) -> ExecutionResult:
        if not self.settings.enable_live_trading:
            raise RuntimeError(
                "Live trading is disabled. Set ENABLE_LIVE_TRADING=true to allow real orders."
            )

        market_price = order.price or self.binance_client.get_current_price(order.symbol)
        account_info = self.binance_client.get_account_info(omit_zero_balances=False)
        balances = {
            balance["asset"]: float(balance["free"]) for balance in account_info.get("balances", [])
        }
        symbol_assets = self.binance_client.get_symbol_assets(order.symbol)
        estimated_notional = order.quantity * market_price

        if order.side == "BUY":
            quote_free = balances.get(symbol_assets["quote_asset"], 0)
            if quote_free < estimated_notional:
                raise RuntimeError(
                    f"Insufficient {symbol_assets['quote_asset']} free balance for live BUY"
                )
        else:
            base_free = balances.get(symbol_assets["base_asset"], 0)
            if base_free < order.quantity:
                raise RuntimeError(
                    f"Insufficient {symbol_assets['base_asset']} free balance for live SELL"
                )

        rules = self.binance_client.get_symbol_rules(order.symbol)
        normalized = self.binance_client.validate_order(
            order.symbol, order.quantity, market_price, rules
        )
        payload = self.binance_client.prepare_order_payload(
            order.symbol,
            order.side,
            normalized["quantity"],
            normalized["price"],
            order.order_type,
        )
        response = self.binance_client.send_live_order(payload)
        status = response.get("status", "NEW")
        executed_quantity = float(response.get("executedQty", payload.quantity))
        executed_quote_qty = float(response.get("cummulativeQuoteQty", 0) or 0)
        executed_price = (
            executed_quote_qty / executed_quantity
            if executed_quantity > 0 and executed_quote_qty > 0
            else market_price
        )

        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            price=executed_price,
            quantity=executed_quantity,
            status=status,
            rationale=order.rationale,
            mode=self.mode,
            confidence=order.confidence,
            raw_payload=response,
        )
        self.db.add(trade)
        self.db.commit()

        if status in {"FILLED", "PARTIALLY_FILLED"} and executed_quantity > 0:
            self.portfolio_service.upsert_filled_trade_position(
                symbol=order.symbol,
                side=order.side,
                price=executed_price,
                quantity=executed_quantity,
            )

        return ExecutionResult(
            status=status,
            external_id=str(response.get("orderId")) if response.get("orderId") else None,
            message="Live order submitted to Binance Spot",
            raw_payload=response,
        )

    def test_order(self, order: ExecutionRequest) -> ExecutionResult:
        market_price = order.price or self.binance_client.get_current_price(order.symbol)
        rules = self.binance_client.get_symbol_rules(order.symbol)
        normalized = self.binance_client.validate_order(
            order.symbol, order.quantity, market_price, rules
        )
        payload = self.binance_client.prepare_order_payload(
            order.symbol,
            order.side,
            normalized["quantity"],
            normalized["price"],
            order.order_type,
        )
        self.binance_client.send_test_order(payload)
        return ExecutionResult(
            status="FILLED",
            message="Binance Spot test order accepted",
            raw_payload=payload.model_dump(),
        )
