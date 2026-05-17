from __future__ import annotations
import json
import httpx
import dateparser
from datetime import date
from bs4 import BeautifulSoup

from agent.models import Event
from agent.sources.base import AbstractSource

_AGENDA_URL = "https://www.citizenkid.com/paris/agenda/"


def _parse_date(s: str) -> date | None:
    parsed = dateparser.parse(s, languages=["fr"], settings={"RETURN_AS_TIMEZONE_AWARE": False})
    return parsed.date() if parsed else None


class CitizenkidSource(AbstractSource):
    name = "citizenkid"

    async def fetch_events(self, start: date, end: date) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await self._get(client, _AGENDA_URL)
            except Exception:
                return []

        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Try JSON-LD structured data
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") != "Event":
                    continue
                name = item.get("name", "").strip()
                url_ev = item.get("url", "").strip()
                if not name or not url_ev or url_ev in seen:
                    continue
                start_s = (item.get("startDate") or "")[:10]
                end_s = (item.get("endDate") or start_s)[:10]
                fecha_inicio = _parse_date(start_s)
                if not fecha_inicio:
                    continue
                fecha_fin = _parse_date(end_s) if end_s and end_s != start_s else None
                if fecha_inicio > end or (fecha_fin or fecha_inicio) < start:
                    continue
                loc = item.get("location", {})
                lugar = loc.get("name", "Paris") if isinstance(loc, dict) else "Paris"
                seen.add(url_ev)
                try:
                    events.append(Event(
                        evento=name,
                        fecha_inicio=fecha_inicio,
                        fecha_fin=fecha_fin,
                        lugar=lugar,
                        tipo_publico="Familia",
                        link=url_ev,
                        fuente="citizenkid",
                    ))
                except Exception:
                    continue

        if events:
            return events

        # Fallback: The Events Calendar (WordPress plugin) HTML structure
        selectors = [
            "article[class*='tribe']",
            ".tribe-events-calendar-list__event-article",
            "article.type-tribe_events",
            ".tribe-event",
            "article[class*='event']",
        ]
        for selector in selectors:
            articles = soup.select(selector)
            if articles:
                for article in articles:
                    title_el = article.select_one(
                        "h2 a, h3 a, .tribe-event-title a, a.tribe-event-url, .entry-title a"
                    )
                    if not title_el:
                        continue
                    name = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    if not href or href in seen:
                        continue
                    date_el = article.select_one(
                        ".tribe-event-date-start, abbr.tribe-events-abbr, time, [class*='date']"
                    )
                    date_str = ""
                    if date_el:
                        date_str = date_el.get("title") or date_el.get("datetime") or date_el.get_text(strip=True)
                    fecha_inicio = _parse_date(date_str) if date_str else start
                    if not fecha_inicio or fecha_inicio > end or fecha_inicio < start:
                        continue
                    seen.add(href)
                    try:
                        events.append(Event(
                            evento=name,
                            fecha_inicio=fecha_inicio,
                            lugar="Paris",
                            tipo_publico="Familia",
                            link=href,
                            fuente="citizenkid",
                        ))
                    except Exception:
                        continue
                break

        return events
