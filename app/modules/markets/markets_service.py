from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.binance.binance_client import BinanceClient
from app.integrations.news.macro_provider import MacroProvider
from app.shared.db.models import MarketSnapshot
from app.shared.types.domain import MarketContext
from app.shared.utils.indicators import momentum, rsi, simple_moving_average, volatility


class MarketsService:
    def __init__(self, db: Session, binance_client: BinanceClient, macro_provider: MacroProvider) -> None:
        self.db = db
        self.binance_client = binance_client
        self.macro_provider = macro_provider

    def collect_snapshot(self, symbol: str) -> MarketContext:
        price = self.binance_client.get_current_price(symbol)
        book_ticker = self.binance_client.get_book_ticker(symbol)
        order_book = self.binance_client.get_order_book(symbol)
        klines = self.binance_client.get_klines(symbol)
        indicators = self._build_indicators(klines)
        macro = self.macro_provider.get_macro_context()

        snapshot = MarketContext(
            symbol=symbol,
            price=price,
            bid_price=book_ticker["bid_price"],
            ask_price=book_ticker["ask_price"],
            spread=book_ticker["ask_price"] - book_ticker["bid_price"],
            order_book=order_book,
            klines=klines,
            indicators=indicators,
            macro=macro,
        )

        model = MarketSnapshot(
            symbol=symbol,
            price=snapshot.price,
            bid_price=snapshot.bid_price,
            ask_price=snapshot.ask_price,
            spread=snapshot.spread,
            volume_24h=snapshot.volume_24h,
            order_book=snapshot.order_book,
            klines=snapshot.klines,
            raw_payload=snapshot.model_dump(),
        )
        self.db.add(model)
        self.db.commit()
        return snapshot

    def _build_indicators(self, klines: list) -> dict:
        closes = [float(item[4]) for item in klines if len(item) > 4]
        volumes = [float(item[5]) for item in klines if len(item) > 5]

        return {
            "sma_9": simple_moving_average(closes, 9),
            "sma_21": simple_moving_average(closes, 21),
            "rsi_14": rsi(closes, 14),
            "momentum_10": momentum(closes, 10),
            "volatility_14": volatility(closes, 14),
            "volume_avg_10": simple_moving_average(volumes, 10),
            "last_close": closes[-1] if closes else None,
        }

    def list_snapshots(self) -> list[MarketSnapshot]:
        statement = select(MarketSnapshot).order_by(MarketSnapshot.created_at.desc()).limit(100)
        return list(self.db.scalars(statement))

    def latest_snapshot(self, symbol: str) -> MarketSnapshot | None:
        statement = (
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol)
            .order_by(MarketSnapshot.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)
