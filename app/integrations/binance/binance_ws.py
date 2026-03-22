import asyncio
import json
from collections.abc import Awaitable, Callable

import websockets

from app.config.logging import logger
from app.config.settings import get_settings


class BinanceWsClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._running = False

    async def connect(
        self,
        symbols: list[str],
        stream_type: str = "trade",
        on_event: Callable[[dict], Awaitable[None]] | None = None,
    ) -> None:
        self._running = True
        stream_path = "/".join(f"{symbol.lower()}@{stream_type}" for symbol in symbols)
        if len(symbols) == 1:
            url = f"{self.settings.binance_ws_url}/{stream_path}"
        else:
            url = self.settings.binance_ws_url.replace("/ws", "/stream") + f"?streams={stream_path}"

        while self._running:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as websocket:
                    logger.info("Connected to Binance Spot websocket for %s", ",".join(symbols))
                    async for message in websocket:
                        payload = json.loads(message)
                        if on_event is not None:
                            await on_event(payload)
            except Exception as exc:
                logger.warning("Binance websocket disconnected, reconnecting: %s", exc)
                await asyncio.sleep(3)

    def stop(self) -> None:
        self._running = False
