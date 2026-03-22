from datetime import datetime, timezone

import httpx


class MacroProvider:
    def __init__(self) -> None:
        self.http_client = httpx.Client(timeout=8.0)

    def get_macro_context(self) -> dict:
        fear_and_greed = self._get_fear_and_greed()
        return {
            "fear_and_greed": fear_and_greed,
            "captured_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _get_fear_and_greed(self) -> dict:
        try:
            response = self.http_client.get("https://api.alternative.me/fng/?limit=1")
            response.raise_for_status()
            payload = response.json()
            latest = payload["data"][0]
            return {
                "value": int(latest["value"]),
                "classification": latest["value_classification"],
                "timestamp": latest["timestamp"],
            }
        except Exception:
            return {
                "value": None,
                "classification": "unknown",
                "timestamp": None,
            }
