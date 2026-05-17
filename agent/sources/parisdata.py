from __future__ import annotations
import httpx
from datetime import date, datetime, timezone

from agent.models import Event, TipoPublico
from agent.sources.base import AbstractSource

_API_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/que-faire-a-paris-/records"

# Tags that identify sports events
_SPORT_TAGS = frozenset(["Sport", "Sports"])

# Audience substrings that indicate children/family
_FAMILY_AUDIENCE = ("enfants", "famille")
_TEEN_AUDIENCE = ("jeunes",)

_HISPANIC_KEYWORDS = frozenset([
    "flamenco", "salsa", "tango", "latin", "latino", "latina",
    "espagnol", "espanol", "hispanic", "reggaeton", "cumbia",
    "merengue", "bachata", "mariachi", "coréen", "brasil", "brésil",
])

# Tags we care about — anything else is filtered out to keep volume manageable
_RELEVANT_TAGS = frozenset([
    "Concert", "Festival", "Théâtre", "Danse", "Expo", "Enfants",
    "Sport", "Loisirs", "Spectacle musical", "Atelier", "Cinéma",
    "Salon", "Foire",
])


def _classify(title: str, audience: str, tags: str) -> TipoPublico:
    t = title.lower()
    if any(kw in t for kw in _HISPANIC_KEYWORDS):
        return "Hispano/Latino"
    tag_set = {tag.strip() for tag in tags.split(";")}
    if tag_set & _SPORT_TAGS:
        return "Deportivo"
    if "Salon" in tag_set or "Foire" in tag_set:
        return "Salón masivo"
    aud = audience.lower()
    if any(kw in aud for kw in _FAMILY_AUDIENCE) or "Enfants" in tag_set:
        return "Familia"
    if any(kw in aud for kw in _TEEN_AUDIENCE):
        return "Adolescentes"
    return "Familia"


def _fmt_date(d: date) -> str:
    return d.isoformat()


def _parse_iso(s: str) -> date | None:
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        return None


def _format_price(price_type: str, price_detail: str) -> str:
    if price_type == "gratuit":
        return "Gratuito"
    if price_detail:
        # strip HTML tags
        import re
        clean = re.sub(r"<[^>]+>", "", price_detail).strip()
        return clean[:100] if clean else price_type.capitalize()
    return price_type.capitalize() if price_type else "TBA"


class ParisDataSource(AbstractSource):
    name = "parisdata"

    async def fetch_events(self, start: date, end: date) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        offset = 0
        limit = 100

        async with httpx.AsyncClient(follow_redirects=True) as client:
            while len(events) < 200:
                params = {
                    "limit": limit,
                    "offset": offset,
                    "where": (
                        f"date_start >= '{_fmt_date(start)}'"
                        f" AND date_start <= '{_fmt_date(end)}'"
                    ),
                    "order_by": "rank DESC",
                    "lang": "fr",
                }
                try:
                    resp = await self._get(client, _API_URL, params=params)
                except Exception:
                    break

                data = resp.json()
                records = data.get("results", [])
                if not records:
                    break

                for rec in records:
                    title = (rec.get("title") or "").strip()
                    url_ev = rec.get("url") or rec.get("access_link") or ""
                    url_ev = url_ev.strip()
                    if not title or not url_ev or url_ev in seen:
                        continue

                    tags = rec.get("qfap_tags") or ""
                    # Skip events with no relevant tags
                    tag_set = {t.strip() for t in tags.split(";")}
                    if _RELEVANT_TAGS and not (tag_set & _RELEVANT_TAGS):
                        continue

                    fecha_inicio = _parse_iso(rec.get("date_start") or "")
                    if not fecha_inicio:
                        continue
                    fecha_fin = _parse_iso(rec.get("date_end") or "")
                    if fecha_fin == fecha_inicio:
                        fecha_fin = None

                    if fecha_inicio > end or (fecha_fin or fecha_inicio) < start:
                        continue

                    audience = rec.get("audience") or ""
                    tipo = _classify(title, audience, tags)

                    lugar = rec.get("address_name") or "Paris"
                    costo = _format_price(rec.get("price_type") or "", rec.get("price_detail") or "")

                    seen.add(url_ev)
                    try:
                        events.append(Event(
                            evento=title,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            lugar=lugar,
                            tipo_publico=tipo,
                            link=url_ev,
                            costo=costo,
                            fuente="parisdata",
                        ))
                    except Exception:
                        continue

                total = data.get("total_count", 0)
                offset += limit
                if offset >= total or offset >= 300:
                    break

        return events
