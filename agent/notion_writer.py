from __future__ import annotations
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from agent.models import Event

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


class NotionWriter:
    def __init__(self, token: str, database_id: str):
        self._database_id = database_id
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": _NOTION_VERSION,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def _request(self, client: httpx.AsyncClient, method: str, path: str, **kwargs) -> dict:
        resp = await client.request(
            method,
            f"{_NOTION_API}{path}",
            headers=self._headers,
            timeout=30,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    async def _get_existing_links(self, client: httpx.AsyncClient) -> set[str]:
        links: set[str] = set()
        cursor = None
        while True:
            body: dict = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            data = await self._request(
                client, "POST", f"/databases/{self._database_id}/query", json=body
            )
            for page in data.get("results", []):
                url_val = page.get("properties", {}).get("Link", {}).get("url")
                if url_val:
                    links.add(url_val)
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
        return links

    def _to_properties(self, event: Event) -> dict:
        date_val: dict = {"start": str(event.fecha_inicio)}
        if event.fecha_fin and event.fecha_fin != event.fecha_inicio:
            date_val["end"] = str(event.fecha_fin)
        return {
            "Evento": {"title": [{"text": {"content": event.evento[:2000]}}]},
            "Lugar": {"rich_text": [{"text": {"content": event.lugar[:2000]}}]},
            "Fecha": {"date": date_val},
            "Tipo de Público": {"select": {"name": event.tipo_publico}},
            "Costo": {"rich_text": [{"text": {"content": event.costo[:2000]}}]},
            "Link": {"url": event.link},
            "Fuente": {"select": {"name": event.fuente}},
        }

    async def upsert_events(self, events: list[Event]) -> tuple[int, int]:
        created = 0
        skipped = 0

        async with httpx.AsyncClient() as client:
            existing = await self._get_existing_links(client)

            for event in events:
                if event.link in existing:
                    skipped += 1
                    continue
                try:
                    await self._request(
                        client, "POST", "/pages",
                        json={
                            "parent": {"database_id": self._database_id},
                            "properties": self._to_properties(event),
                        },
                    )
                    existing.add(event.link)
                    created += 1
                except httpx.HTTPStatusError as exc:
                    print(f"  [notion] Error '{event.evento}': {exc.response.text[:200]}")
                except Exception as exc:
                    print(f"  [notion] Unexpected error: {exc}")

        return created, skipped
