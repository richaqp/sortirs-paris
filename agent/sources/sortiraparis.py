from __future__ import annotations
import json
import httpx
import dateparser
from datetime import date
from bs4 import BeautifulSoup

from agent.models import Event, TipoPublico
from agent.sources.base import AbstractSource

_CATEGORY_PAGES: list[tuple[str, TipoPublico]] = [
    ("https://www.sortiraparis.com/loisirs/famille/agenda", "Familia"),
    ("https://www.sortiraparis.com/activites-sports/agenda", "Deportivo"),
    ("https://www.sortiraparis.com/salons-et-expos/salons/agenda", "Salón masivo"),
]


def _parse_date(s: str) -> date | None:
    parsed = dateparser.parse(s, languages=["fr"], settings={"RETURN_AS_TIMEZONE_AWARE": False})
    return parsed.date() if parsed else None


def _jsonld_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") == "Event":
                results.append(item)
            elif item.get("@type") == "ItemList":
                for el in item.get("itemListElement", []):
                    it = el.get("item", el)
                    if isinstance(it, dict) and it.get("@type") == "Event":
                        results.append(it)
    return results


def _html_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    for article in soup.select("article, .item-list, .listing-item, [class*='event']"):
        title_el = article.select_one("h2 a, h3 a, .title a, a[title]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if href and not href.startswith("http"):
            href = "https://www.sortiraparis.com" + href
        date_el = article.select_one("time, .dates, .date, .event-date, [class*='date']")
        date_str = date_el.get_text(strip=True) if date_el else ""
        if title and href:
            results.append({"name": title, "url": href, "date_str": date_str})
    return results


class SortirapariSource(AbstractSource):
    name = "sortiraparis"

    async def fetch_events(self, start: date, end: date) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for page_url, tipo in _CATEGORY_PAGES:
                try:
                    resp = await self._get(client, page_url)
                except Exception:
                    continue

                html = resp.text
                jsonld = _jsonld_events(html)

                if jsonld:
                    for item in jsonld:
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
                        offers = item.get("offers", {})
                        if isinstance(offers, dict) and offers.get("price") is not None:
                            price = offers.get("price")
                            currency = offers.get("priceCurrency", "")
                            costo = f"{price} {currency}".strip() if price else "TBA"
                        else:
                            costo = "TBA"
                        seen.add(url_ev)
                        try:
                            events.append(Event(
                                evento=name,
                                fecha_inicio=fecha_inicio,
                                fecha_fin=fecha_fin,
                                lugar=lugar or "Paris",
                                tipo_publico=tipo,
                                link=url_ev,
                                costo=costo,
                                fuente="sortiraparis",
                            ))
                        except Exception:
                            continue
                else:
                    for item in _html_events(html):
                        name = item["name"]
                        url_ev = item["url"]
                        if not name or not url_ev or url_ev in seen:
                            continue
                        fecha_inicio = _parse_date(item["date_str"]) if item["date_str"] else start
                        if not fecha_inicio or fecha_inicio > end or fecha_inicio < start:
                            continue
                        seen.add(url_ev)
                        try:
                            events.append(Event(
                                evento=name,
                                fecha_inicio=fecha_inicio,
                                lugar="Paris",
                                tipo_publico=tipo,
                                link=url_ev,
                                fuente="sortiraparis",
                            ))
                        except Exception:
                            continue

        return events
