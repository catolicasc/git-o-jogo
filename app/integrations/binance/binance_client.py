from time import time

from app.config.logging import logger
from app.config.settings import get_settings
from app.integrations.binance.binance_signer import sign_binance_query
from app.integrations.binance.binance_types import BinanceSymbolRules, PreparedOrderPayload
from app.shared.http.http_client import HttpClient
from app.shared.utils.math import round_down


class BinanceClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.binance_base_url
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret
        self.http_client = HttpClient()

    # Public market data endpoint: current Spot ticker price.
    def get_current_price(self, symbol: str) -> float:
        response = self.http_client.request(
            "GET", f"{self.base_url}/api/v3/ticker/price", params={"symbol": symbol}
        )
        return float(response["price"])

    # Public market data endpoint: current Spot ticker prices for all symbols.
    def get_all_prices(self) -> dict[str, float]:
        response = self.http_client.request("GET", f"{self.base_url}/api/v3/ticker/price")
        if not isinstance(response, list):
            return {}
        return {
            item["symbol"]: float(item["price"])
            for item in response
            if isinstance(item, dict) and item.get("symbol") and item.get("price")
        }

    # Public market data endpoint: best bid/ask.
    def get_book_ticker(self, symbol: str) -> dict:
        response = self.http_client.request(
            "GET", f"{self.base_url}/api/v3/ticker/bookTicker", params={"symbol": symbol}
        )
        return {
            "bid_price": float(response["bidPrice"]),
            "ask_price": float(response["askPrice"]),
            "bid_qty": float(response["bidQty"]),
            "ask_qty": float(response["askQty"]),
        }

    # Public market data endpoint: Spot order book.
    def get_order_book(self, symbol: str, limit: int = 20) -> dict:
        return self.http_client.request(
            "GET",
            f"{self.base_url}/api/v3/depth",
            params={"symbol": symbol, "limit": limit},
        )

    # Public market data endpoint: Spot klines.
    def get_klines(
        self,
        symbol: str,
        interval: str = "15m",
        limit: int = 50,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list:
        params: dict[str, str | int] = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        response = self.http_client.request(
            "GET",
            f"{self.base_url}/api/v3/klines",
            params=params,
        )
        return response if isinstance(response, list) else []

    # Public market data endpoint: exchange info and symbol filters.
    def get_exchange_info(self, symbol: str | None = None) -> dict:
        params = {"symbol": symbol} if symbol else None
        return self.http_client.request("GET", f"{self.base_url}/api/v3/exchangeInfo", params=params)

    # Signed endpoint: Spot account information and balances.
    def get_account_info(self, omit_zero_balances: bool = True) -> dict:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance API credentials are required for account information")

        params: dict[str, str | int] = {
            "timestamp": int(time() * 1000),
            "omitZeroBalances": "true" if omit_zero_balances else "false",
            "recvWindow": 5000,
        }
        query = sign_binance_query(params, self.api_secret)
        return self.http_client.request(
            "GET",
            f"{self.base_url}/api/v3/account?{query}",
            headers={"X-MBX-APIKEY": self.api_key},
        )

    def get_symbol_assets(self, symbol: str) -> dict[str, str]:
        exchange_info = self.get_exchange_info(symbol)
        entry = next((item for item in exchange_info["symbols"] if item["symbol"] == symbol), None)
        if entry is None:
            raise RuntimeError(f"Symbol {symbol} not found on Binance Spot exchange info")
        return {
            "base_asset": entry["baseAsset"],
            "quote_asset": entry["quoteAsset"],
        }

    def get_open_orders(self, symbol: str) -> list[dict]:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance API credentials are required for open orders")

        params: dict[str, str | int] = {
            "symbol": symbol,
            "timestamp": int(time() * 1000),
            "recvWindow": 5000,
        }
        query = sign_binance_query(params, self.api_secret)
        response = self.http_client.request(
            "GET",
            f"{self.base_url}/api/v3/openOrders?{query}",
            headers={"X-MBX-APIKEY": self.api_key},
        )
        return response if isinstance(response, list) else []

    def get_all_orders(self, symbol: str, limit: int = 20) -> list[dict]:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance API credentials are required for order history")

        params: dict[str, str | int] = {
            "symbol": symbol,
            "limit": limit,
            "timestamp": int(time() * 1000),
            "recvWindow": 5000,
        }
        query = sign_binance_query(params, self.api_secret)
        response = self.http_client.request(
            "GET",
            f"{self.base_url}/api/v3/allOrders?{query}",
            headers={"X-MBX-APIKEY": self.api_key},
        )
        return response if isinstance(response, list) else []

    def get_my_trades(self, symbol: str, limit: int = 20) -> list[dict]:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance API credentials are required for trade history")

        params: dict[str, str | int] = {
            "symbol": symbol,
            "limit": limit,
            "timestamp": int(time() * 1000),
            "recvWindow": 5000,
        }
        query = sign_binance_query(params, self.api_secret)
        response = self.http_client.request(
            "GET",
            f"{self.base_url}/api/v3/myTrades?{query}",
            headers={"X-MBX-APIKEY": self.api_key},
        )
        return response if isinstance(response, list) else []

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        exchange_info = self.get_exchange_info(symbol)
        entry = next((item for item in exchange_info["symbols"] if item["symbol"] == symbol), None)
        if entry is None:
            raise RuntimeError(f"Symbol {symbol} not found on Binance Spot exchange info")

        lot_size = next((item for item in entry["filters"] if item["filterType"] == "LOT_SIZE"), {})
        min_notional = next(
            (
                item
                for item in entry["filters"]
                if item["filterType"] in {"MIN_NOTIONAL", "NOTIONAL"}
            ),
            {},
        )
        price_filter = next(
            (item for item in entry["filters"] if item["filterType"] == "PRICE_FILTER"),
            {},
        )

        return BinanceSymbolRules(
            min_qty=float(lot_size.get("minQty", 0)),
            max_qty=float(lot_size.get("maxQty", 999999999)),
            step_size=float(lot_size.get("stepSize", 0.000001)),
            min_notional=float(min_notional.get("minNotional", 10)),
            tick_size=float(price_filter.get("tickSize", 0.01)),
        )

    def validate_order(self, symbol: str, quantity: float, price: float, rules: BinanceSymbolRules) -> dict:
        notional = quantity * price
        if quantity < rules.min_qty:
            raise RuntimeError(f"Quantity below minQty for {symbol}")
        if quantity > rules.max_qty:
            raise RuntimeError(f"Quantity above maxQty for {symbol}")
        if notional < rules.min_notional:
            raise RuntimeError(f"Order notional below minNotional for {symbol}")

        normalized_quantity = round_down(quantity, rules.step_size)
        normalized_price = round_down(price, rules.tick_size or 0.01)
        if normalized_quantity <= 0:
            raise RuntimeError(f"Quantity becomes invalid after step size normalization for {symbol}")

        return {
            "quantity": normalized_quantity,
            "price": normalized_price,
            "notional": notional,
        }

    def prepare_order_payload(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str = "LIMIT",
    ) -> PreparedOrderPayload:
        payload = PreparedOrderPayload(
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=f"{quantity:.8f}",
            timestamp=int(time() * 1000),
        )
        if order_type == "LIMIT":
            payload.price = f"{price:.8f}"
            payload.timeInForce = "GTC"
        return payload

    # Signed endpoint: Spot test order. Validates signature and exchange filters without placing a real order.
    def send_test_order(self, payload: PreparedOrderPayload) -> dict:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance API credentials are required for signed test order")

        cleaned_payload = {
            key: value
            for key, value in payload.model_dump().items()
            if value is not None
        }
        query = sign_binance_query(cleaned_payload, self.api_secret)
        try:
            return self.http_client.request(
                "POST",
                f"{self.base_url}/api/v3/order/test?{query}",
                headers={"X-MBX-APIKEY": self.api_key},
            )
        except Exception as exc:
            self.safe_log_signature_error(exc)
            raise

    # Signed endpoint: live Spot order. Keep behind feature flag.
    def send_live_order(self, payload: PreparedOrderPayload) -> dict:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance API credentials are required for live order")

        cleaned_payload = {
            key: value
            for key, value in payload.model_dump().items()
            if value is not None
        }
        query = sign_binance_query(cleaned_payload, self.api_secret)
        try:
            return self.http_client.request(
                "POST",
                f"{self.base_url}/api/v3/order?{query}",
                headers={"X-MBX-APIKEY": self.api_key},
            )
        except Exception as exc:
            self.safe_log_signature_error(exc)
            raise

    def safe_log_signature_error(self, error: Exception) -> None:
        logger.error("Binance signature or signed endpoint error: %s", error)
