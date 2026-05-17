from __future__ import annotations
import re
import httpx
import dateparser
from datetime import date
from bs4 import BeautifulSoup

from agent.models import Event
from agent.sources.base import AbstractSource

# Viparis embeds all event data as JS in the page (Nuxt.js)
_EVENT_RE = re.compile(
    r'title:"(?P<title>[^"]+)".*?'
    r'uid:"(?P<uid>[^"]+)".*?'
    r'time:"(?P<time>[^"]+)".*?'
    r'(?:website_url:"(?P<url>[^"]*)")?.*?'
    r'(?:price:"(?P<price>[^"]*)")?',
    re.DOTALL,
)
_DATE_BLOCK_RE = re.compile(r'(\d{2}/\d{2}/\d{4})')


def _parse_viparis_dates(time_str: str) -> tuple[date | None, date | None]:
    time_str = time_str.replace("\\u002F", "/")
    raw_dates = _DATE_BLOCK_RE.findall(time_str)
    if not raw_dates:
        return None, None
    start = dateparser.parse(raw_dates[0], languages=["fr"])
    end = dateparser.parse(raw_dates[-1], languages=["fr"]) if len(raw_dates) > 1 else None
    return (start.date() if start else None, end.date() if end else None)


class ViparisSource(AbstractSource):
    name = "viparis"
    _url = "https://www.viparis.com/"
    _base_event_url = "https://www.viparis.com/fr/manifestation/"

    async def fetch_events(self, start: date, end: date) -> list[Event]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await self._get(client, self._url)
            except Exception:
                return []

        html = resp.text
        events: list[Event] = []
        seen_uids: set[str] = set()

        for m in _EVENT_RE.finditer(html):
            raw_title = m.group("title")
            # Decode unicode escapes, then strip HTML if present
            if "\\u" in raw_title:
                try:
                    raw_title = raw_title.encode().decode("unicode_escape")
                except Exception:
                    pass
            if "<" in raw_title:
                raw_title = BeautifulSoup(raw_title, "lxml").get_text()
            title = raw_title.strip()
            uid = m.group("uid").strip()
            time_raw = m.group("time") or ""
            url = (m.group("url") or "").replace("\\u002F", "/").strip()
            price_raw = (m.group("price") or "").strip() or "TBA"

            if not title or uid in seen_uids:
                continue
            seen_uids.add(uid)

            # Decode unicode escapes in time string
            time_str = time_raw.encode().decode("unicode_escape") if "\\u" in time_raw else time_raw
            fecha_inicio, fecha_fin = _parse_viparis_dates(time_str)
            if not fecha_inicio:
                continue

            # Filter to the requested window
            if fecha_inicio > end or (fecha_fin or fecha_inicio) < start:
                continue

            event_url = self._base_event_url + uid if uid else url
            if not event_url:
                continue

            try:
                events.append(
                    Event(
                        evento=title,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin,
                        lugar="Paris Expo (Viparis)",
                        tipo_publico="Salón masivo",
                        link=event_url,
                        costo=price_raw,
                        fuente="viparis",
                    )
                )
            except Exception:
                continue

        return events
