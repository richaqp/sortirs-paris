from __future__ import annotations
import httpx
from abc import ABC, abstractmethod
from datetime import date
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from agent.models import Event

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


class AbstractSource(ABC):
    name: str

    @abstractmethod
    async def fetch_events(self, start: date, end: date) -> list[Event]:
        ...

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def _get(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        response = await client.get(url, headers=DEFAULT_HEADERS, timeout=20, **kwargs)
        response.raise_for_status()
        return response
