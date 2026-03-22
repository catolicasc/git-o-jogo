from datetime import datetime

from app.integrations.news.news_types import NewsProvider
from app.shared.types.domain import NewsContext


class MockNewsProvider(NewsProvider):
    def fetch_latest(self, symbols: list[str]) -> list[NewsContext]:
        now = datetime.utcnow().isoformat()
        return [
            NewsContext(
                symbol=symbol,
                title=f"{symbol} market watch",
                summary=f"No external provider configured. Placeholder news context for {symbol}.",
                url=f"https://example.com/news/{symbol.lower()}",
                source="mock-news-provider",
                published_at=now,
            )
            for symbol in symbols
        ]
