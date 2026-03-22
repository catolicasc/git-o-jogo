from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.integrations.news.news_types import NewsProvider
from app.shared.db.models import NewsItem
from app.shared.types.domain import NewsContext


class NewsService:
    def __init__(self, db: Session, news_provider: NewsProvider) -> None:
        self.db = db
        self.news_provider = news_provider

    def collect(self, symbols: list[str]) -> list[NewsContext]:
        items = self.news_provider.fetch_latest(symbols)
        for item in items:
            existing = self.db.scalar(select(NewsItem).where(NewsItem.url == item.url).limit(1))
            if existing is None:
                existing = NewsItem(url=item.url, title=item.title, source=item.source, published_at=datetime.fromisoformat(item.published_at))
                self.db.add(existing)

            existing.symbol = item.symbol
            existing.title = item.title
            existing.summary = item.summary
            existing.source = item.source
            existing.published_at = datetime.fromisoformat(item.published_at)
            existing.raw_payload = item.model_dump()

        self.db.commit()
        return items

    def list_items(self) -> list[NewsItem]:
        return list(self.db.scalars(select(NewsItem).order_by(NewsItem.published_at.desc()).limit(100)))

    def find_recent_by_symbol(self, symbol: str) -> list[NewsContext]:
        statement = (
            select(NewsItem)
            .where(or_(NewsItem.symbol == symbol, NewsItem.symbol.is_(None)))
            .order_by(NewsItem.published_at.desc())
            .limit(20)
        )
        records = list(self.db.scalars(statement))
        return [
            NewsContext(
                symbol=item.symbol,
                title=item.title,
                summary=item.summary,
                url=item.url,
                source=item.source,
                published_at=item.published_at.isoformat(),
            )
            for item in records
        ]
