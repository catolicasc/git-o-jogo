import time

import certifi
import httpx


class HttpRequestFailed(RuntimeError):
    def __init__(
        self,
        *,
        url: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
        detail = f"HTTP request failed for {url}"
        if status_code is not None:
            detail += f" with status {status_code}"
        if response_text:
            detail += f": {response_text}"
        super().__init__(detail)


class HttpClient:
    def __init__(self, timeout: float = 7.0, retries: int = 2) -> None:
        self.timeout = timeout
        self.retries = retries

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        json: dict | None = None,
    ) -> dict | list:
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, verify=certifi.where()) as client:
                    response = client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers,
                        json=json,
                    )
                    response.raise_for_status()
                    return response.json()
            except httpx.RequestError as exc:
                last_error = exc
                response = getattr(exc, "response", None)
                if response is not None and response.status_code == 429:
                    time.sleep(0.5 * (attempt + 1))
                if attempt == self.retries:
                    break
                time.sleep(0.25 * (attempt + 1))
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response is not None and exc.response.status_code == 429:
                    time.sleep(0.5 * (attempt + 1))
                if attempt == self.retries:
                    break
                time.sleep(0.25 * (attempt + 1))

        response = None
        if isinstance(last_error, httpx.HTTPStatusError):
            response = last_error.response
        elif isinstance(last_error, httpx.RequestError):
            response = getattr(last_error, "response", None)

        raise HttpRequestFailed(
            url=url,
            status_code=response.status_code if response is not None else None,
            response_text=response.text if response is not None else str(last_error) if last_error else None,
        ) from last_error
