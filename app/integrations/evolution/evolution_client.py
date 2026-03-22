import re

import httpx

from app.config.settings import get_settings


class EvolutionClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.http_client = httpx.Client(timeout=10.0)

    def is_configured(self) -> bool:
        return all(
            [
                self.settings.evolution_api_base_url,
                self.settings.evolution_api_key,
                self.settings.evolution_api_instance,
            ]
        )

    def send_text(self, number: str, text: str) -> dict:
        if not self.is_configured():
            raise RuntimeError("Evolution API is not configured")

        payload = {
            "number": self._normalize_number(number),
            "text": text,
        }
        response = self.http_client.post(
            f"{self.settings.evolution_api_base_url}/message/sendText/{self.settings.evolution_api_instance}",
            headers={
                "apikey": self.settings.evolution_api_key or "",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Evolution API send_text failed ({response.status_code}): {response.text}"
            )
        return response.json()

    def _normalize_number(self, number: str) -> str:
        digits = re.sub(r"\D", "", number)
        if digits.endswith("@s.whatsapp.net"):
            digits = digits.replace("@s.whatsapp.net", "")
        if digits.startswith("55"):
            return digits
        if len(digits) == 8 or len(digits) == 9:
            return f"55{digits}"
        return digits
