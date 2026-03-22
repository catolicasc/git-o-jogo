from typing import Protocol

from app.shared.types.domain import NewsContext


class NewsProvider(Protocol):
    def fetch_latest(self, symbols: list[str]) -> list[NewsContext]: ...
