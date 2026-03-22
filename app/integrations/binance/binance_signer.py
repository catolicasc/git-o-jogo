import hashlib
import hmac
from urllib.parse import urlencode


def sign_binance_query(params: dict[str, str | int | float], secret: str) -> str:
    query = urlencode(params)
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={signature}"
