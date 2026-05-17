from __future__ import annotations
import asyncio
import os
from datetime import date, timedelta

from dotenv import load_dotenv

from agent.models import Event
from agent.notion_writer import NotionWriter
from agent.sources.citizenkid import CitizenkidSource
from agent.sources.parisdata import ParisDataSource
from agent.sources.sortiraparis import SortirapariSource
from agent.sources.ticketmaster import TicketmasterSource
from agent.sources.viparis import ViparisSource


def next_week_range() -> tuple[date, date]:
    today = date.today()
    return today + timedelta(days=1), today + timedelta(days=8)


async def run(start: date | None = None, end: date | None = None) -> None:
    load_dotenv()

    if start is None or end is None:
        start, end = next_week_range()

    print(f"Buscando eventos París: {start} → {end}\n")

    sources = [
        ViparisSource(),
        ParisDataSource(),
        SortirapariSource(),
        CitizenkidSource(),
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

    # Deduplicate by link within the batch
    seen: set[str] = set()
    unique: list[Event] = []
    for ev in all_events:
        if ev.link not in seen:
            seen.add(ev.link)
            unique.append(ev)

    print(f"\nTotal eventos únicos: {len(unique)}")

    writer = NotionWriter(
        token=os.environ["NOTION_TOKEN"],
        database_id=os.environ["NOTION_DATABASE_ID"],
    )
    created, skipped = await writer.upsert_events(unique)
    print(f"Notion: {created} creados, {skipped} ya existían (duplicados)")
