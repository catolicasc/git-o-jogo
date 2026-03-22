import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import httpx
import certifi

from app.config.settings import get_settings
from app.integrations.news.news_types import NewsProvider
from app.shared.types.domain import NewsContext


class RssNewsProvider(NewsProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.http_client = httpx.Client(timeout=8.0, verify=certifi.where())

    def fetch_latest(self, symbols: list[str]) -> list[NewsContext]:
        items: list[NewsContext] = []
        urls = list(self.settings.rss_urls)
        urls.append(
            "https://news.google.com/rss/search?q="
            + quote_plus("crypto federal reserve inflation bitcoin")
        )

        for url in urls:
            try:
                response = self.http_client.get(url)
                response.raise_for_status()
                items.extend(self._parse_feed(response.text, symbols, url))
            except Exception:
                continue

        deduped: dict[str, NewsContext] = {}
        for item in items:
            deduped[item.url] = item

        sorted_items = sorted(
            deduped.values(),
            key=lambda item: item.published_at,
            reverse=True,
        )
        return sorted_items[:50]

    def _parse_feed(self, payload: str, symbols: list[str], source_url: str) -> list[NewsContext]:
        root = ET.fromstring(payload)
        parsed_items: list[NewsContext] = []

        for item in root.findall(".//item"):
            title = html.unescape(item.findtext("title", default="").strip())
            link = item.findtext("link", default="").strip()
            description = html.unescape(item.findtext("description", default="").strip())
            pub_date = item.findtext("pubDate", default="")
            published_at = self._normalize_date(pub_date)
            detected_symbol = self._detect_symbol(title, description, symbols)

            parsed_items.append(
                NewsContext(
                    symbol=detected_symbol,
                    title=title,
                    summary=description[:500] if description else None,
                    url=link,
                    source=self._source_name(source_url),
                    published_at=published_at,
                )
            )

        return parsed_items

    def _detect_symbol(self, title: str, description: str, symbols: list[str]) -> str | None:
        haystack = f"{title} {description}".upper()
        aliases = {
            "BTCUSDT": ["BTC", "BITCOIN"],
            "ETHUSDT": ["ETH", "ETHEREUM"],
            "SOLUSDT": ["SOL", "SOLANA"],
            "BNBUSDT": ["BNB", "BINANCE COIN"],
        }

        for symbol in symbols:
            terms = aliases.get(symbol, [symbol.replace("USDT", "")])
            if any(re.search(rf"\b{re.escape(term)}\b", haystack) for term in terms):
                return symbol
        return None

    def _normalize_date(self, value: str) -> str:
        if not value:
            return datetime.now(tz=timezone.utc).isoformat()

        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(tz=timezone.utc).isoformat()

    def _source_name(self, url: str) -> str:
        if "coindesk" in url:
            return "coindesk-rss"
        if "cointelegraph" in url:
            return "cointelegraph-rss"
        if "news.google.com" in url:
            return "google-news-rss"
        return "rss"
