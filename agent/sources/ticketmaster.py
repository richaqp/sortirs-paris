from __future__ import annotations
import httpx
from datetime import date, datetime, timezone

from agent.models import Event, TipoPublico
from agent.sources.base import AbstractSource

_API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

_SEGMENT_MAP: dict[str, TipoPublico] = {
    "Sports": "Deportivo",
    "Music": "Familia",
    "Musique": "Familia",
    "Arts & Theatre": "Familia",
    "Miscellaneous": "Familia",
    "Film": "Familia",
}

_HISPANIC_KEYWORDS = frozenset([
    "flamenco", "salsa", "tango", "latin", "latino", "latina",
    "espagnol", "espanol", "hispanic", "reggaeton", "cumbia",
    "merengue", "bachata", "mariachi", "rumba", "bolero",
])


def _classify(name: str, segment: str) -> TipoPublico:
    lower = name.lower()
    if any(kw in lower for kw in _HISPANIC_KEYWORDS):
        return "Hispano/Latino"
    return _SEGMENT_MAP.get(segment, "Familia")


def _fmt_datetime(d: date) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TicketmasterSource(AbstractSource):
    name = "ticketmaster"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_events(self, start: date, end: date) -> list[Event]:
        if not self._api_key:
            return []

        events: list[Event] = []
        seen: set[str] = set()
        page = 0

        async with httpx.AsyncClient(follow_redirects=True) as client:
            while True:
                params = {
                    "apikey": self._api_key,
                    "city": "Paris",
                    "countryCode": "FR",
                    "startDateTime": _fmt_datetime(start),
                    "endDateTime": _fmt_datetime(end),
                    "size": 50,
                    "page": page,
                    "locale": "fr,en",
                }
                try:
                    resp = await self._get(client, _API_URL, params=params)
                except Exception:
                    break

                data = resp.json()
                raw_events = data.get("_embedded", {}).get("events", [])
                if not raw_events:
                    break

                for ev in raw_events:
                    name = ev.get("name", "").strip()
                    url_ev = ev.get("url", "").strip()
                    if not name or not url_ev or url_ev in seen:
                        continue

                    start_s = ev.get("dates", {}).get("start", {}).get("localDate", "")
                    if not start_s:
                        continue
                    try:
                        fecha_inicio = date.fromisoformat(start_s)
                    except ValueError:
                        continue
                    if fecha_inicio > end or fecha_inicio < start:
                        continue

                    venues = ev.get("_embedded", {}).get("venues", [])
                    lugar = venues[0].get("name", "Paris") if venues else "Paris"

                    classifications = ev.get("classifications") or [{}]
                    segment = (classifications[0].get("segment") or {}).get("name", "")
                    tipo = _classify(name, segment)

                    price_ranges = ev.get("priceRanges") or []
                    if price_ranges:
                        pr = price_ranges[0]
                        mn = pr.get("min", "")
                        mx = pr.get("max", "")
                        cur = pr.get("currency", "")
                        costo = f"{mn}–{mx} {cur}".strip("– ") if mn or mx else "TBA"
                    else:
                        costo = "TBA"

                    # Best 16:9 image available
                    images = ev.get("images") or []
                    imagen = next(
                        (img["url"] for img in images if img.get("ratio") == "16_9" and img.get("width", 0) >= 640),
                        next((img["url"] for img in images), None),
                    )

                    seen.add(url_ev)
                    try:
                        events.append(Event(
                            evento=name,
                            fecha_inicio=fecha_inicio,
                            lugar=lugar,
                            tipo_publico=tipo,
                            link=url_ev,
                            costo=costo,
                            imagen=imagen,
                            fuente="ticketmaster",
                        ))
                    except Exception:
                        continue

                page_info = data.get("page", {})
                if page >= page_info.get("totalPages", 1) - 1:
                    break
                page += 1

        return events
