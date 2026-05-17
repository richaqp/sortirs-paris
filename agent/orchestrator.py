from __future__ import annotations
import asyncio
import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from agent.models import Event
from agent.notion_writer import NotionWriter
from agent.scoring.rule_scorer import EventScorer
from agent.scoring.dedup import load_recent_shown_links
from agent.scoring.models import WeekData
from agent.sources.parisdata import ParisDataSource
from agent.sources.ticketmaster import TicketmasterSource
from agent.sources.viparis import ViparisSource

_REPO_ROOT = Path(__file__).parent.parent


def next_week_range() -> tuple[date, date]:
    today = date.today()
    return today + timedelta(days=1), today + timedelta(days=8)


def _week_id(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


async def run(
    start: date | None = None,
    end: date | None = None,
    dry_run: bool = False,
    top_k: int = 20,
) -> WeekData | None:
    load_dotenv()

    if start is None or end is None:
        start, end = next_week_range()

    print(f"\nBuscando eventos París: {start} → {end}")
    print(f"Modo: {'DRY RUN' if dry_run else 'LIVE'}\n")

    sources = [
        ViparisSource(),
        ParisDataSource(),
        TicketmasterSource(api_key=os.getenv("TICKETMASTER_API_KEY", "")),
    ]

    results = await asyncio.gather(
        *[s.fetch_events(start, end) for s in sources],
        return_exceptions=True,
    )

    all_events: list[Event] = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            print(f"  [{source.name}] Error: {result}")
        else:
            print(f"  [{source.name}] {len(result)} eventos encontrados")
            all_events.extend(result)

    # Dedup within batch
    seen: set[str] = set()
    unique: list[Event] = []
    for ev in all_events:
        if ev.link not in seen:
            seen.add(ev.link)
            unique.append(ev)

    # Dedup against recent weeks (exclude already shown)
    recent_links = load_recent_shown_links(_REPO_ROOT)
    fresh = [ev for ev in unique if ev.link not in recent_links]
    print(f"\nTotal únicos: {len(unique)} ({len(unique) - len(fresh)} ya mostrados en semanas previas → {len(fresh)} frescos)")

    # Score with rules-based scorer
    scorer = EventScorer()
    print(f"  [scorer] Evaluando {len(fresh)} eventos con reglas…")
    scored = await scorer.score_all(fresh)
    curated = scorer.merge(fresh, scored, top_k=top_k)

    print(f"  [scorer] Top {len(curated)} seleccionados")
    for ev in curated:
        print(f"    [{ev.score}] {ev.titulo_fr[:55]:55s} — {ev.razon[:60]}")

    week_data = WeekData(
        week_id=_week_id(start),
        range_start=start,
        range_end=end,
        generated_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
        total_scraped=len(unique),
        total_scored=len(curated),
        events=curated,
    )

    if dry_run:
        print("\n[dry-run] Notion y git push omitidos.")
        return week_data

    # Write to Notion (all unique events, not just curated)
    notion_token = os.getenv("NOTION_TOKEN", "")
    notion_db = os.getenv("NOTION_DATABASE_ID", "")
    if notion_token and notion_db:
        writer = NotionWriter(token=notion_token, database_id=notion_db)
        created, skipped = await writer.upsert_events(unique)
        print(f"\nNotion: {created} creados, {skipped} ya existían")
    else:
        print("\nNotion: credenciales no configuradas, omitido")

    return week_data
