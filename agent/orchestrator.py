from __future__ import annotations
import asyncio
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from agent.models import Event
from agent.notion_writer import NotionWriter
from agent.publisher.github_publisher import push_files_to_github
from agent.publisher.json_writer import write_week_json
from agent.scoring.claude_scorer import ClaudeScorer
from agent.scoring.dedup import load_recent_shown_links
from agent.scoring.models import CuratedEvent, WeekData
from agent.sources.parisdata import ParisDataSource
from agent.sources.ticketmaster import TicketmasterSource
from agent.sources.viparis import ViparisSource

_REPO_ROOT = Path(__file__).parent.parent
_GH_REPO = "richaqp/sortirs-paris"


def next_week_range() -> tuple[date, date]:
    today = date.today()
    return today + timedelta(days=1), today + timedelta(days=8)


def _load_manual_events(repo_root: Path, start: date, end: date) -> list[CuratedEvent]:
    path = repo_root / "profiles" / "manual_events.json"
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text())
    except Exception:
        return []
    events = []
    for i, ev in enumerate(items):
        fi = date.fromisoformat(ev["fecha_inicio"])
        fe_raw = ev.get("fecha_fin")
        fe = date.fromisoformat(fe_raw) if fe_raw else None
        if fi > end or (fe or fi) < start:
            continue
        events.append(CuratedEvent(
            id=f"manual_{i:03d}",
            titulo_fr=ev["titulo_fr"],
            titulo_es=ev.get("titulo_es", ev["titulo_fr"]),
            fecha_inicio=fi,
            fecha_fin=fe if fe and fe != fi else None,
            lugar=ev.get("lugar", "Paris"),
            costo=ev.get("costo", "TBA"),
            tipo_publico=ev.get("tipo_publico", "Familia"),
            link=ev["link"],
            imagen=ev.get("imagen"),
            fuente="manual",
            score=ev.get("score", 8),
            razon=ev.get("razon", ""),
            tags=ev.get("tags", []),
        ))
    return events


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

    # Dedup against recent weeks
    recent_links = load_recent_shown_links(_REPO_ROOT)
    fresh = [ev for ev in unique if ev.link not in recent_links]
    print(f"\nTotal únicos: {len(unique)} ({len(unique) - len(fresh)} ya mostrados → {len(fresh)} frescos)\n")

    # Score with Claude
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    scorer = ClaudeScorer(api_key=api_key)
    print(f"  [scorer] Evaluando {len(fresh)} eventos con Claude {scorer._model}…")
    scored = await scorer.score_all(fresh)
    curated = scorer.merge(fresh, scored, top_k=top_k)

    print(f"\n  [scorer] Top {len(curated)} seleccionados:")
    for ev in curated:
        print(f"    [{ev.score}] {ev.titulo_fr[:55]:55s} — {ev.razon[:65]}")

    # Add manual events (bypass scorer, always included if in date range)
    manual = _load_manual_events(_REPO_ROOT, start, end)
    if manual:
        manual_links = {e.link for e in curated}
        for ev in manual:
            if ev.link not in manual_links:
                curated.append(ev)
                manual_links.add(ev.link)
        curated.sort(key=lambda e: e.score, reverse=True)
        print(f"  [manual] +{len(manual)} eventos manuales añadidos")

    week_data = WeekData(
        week_id=_week_id(start),
        range_start=start,
        range_end=end,
        generated_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
        total_scraped=len(unique),
        total_scored=len(curated),
        events=curated,
    )

    # Always write JSON locally
    json_path = write_week_json(week_data, _REPO_ROOT)
    print(f"\nJSON escrito: {json_path.relative_to(_REPO_ROOT)}")

    if dry_run:
        print("[dry-run] Notion y GitHub push omitidos.")
        return week_data

    # Write to Notion (all unique events)
    notion_token = os.getenv("NOTION_TOKEN", "")
    notion_db = os.getenv("NOTION_DATABASE_ID", "")
    if notion_token and notion_db:
        writer = NotionWriter(token=notion_token, database_id=notion_db)
        created, skipped = await writer.upsert_events(unique)
        print(f"Notion: {created} creados, {skipped} ya existían")

    # Push JSON to GitHub → triggers Vercel auto-deploy
    github_token = os.getenv("GITHUB_TOKEN", "")
    if github_token:
        week_json = json.loads(json_path.read_text())
        latest_json = json.dumps(week_json, ensure_ascii=False, indent=2)
        week_content = json_path.read_text()

        sha = await push_files_to_github(
            files={
                f"web/content/weeks/{week_data.week_id}.json": week_content,
                "web/content/weeks/latest.json": latest_json,
            },
            commit_message=f"feat(eventos): semana {week_data.week_id} — top {len(curated)} eventos",
            github_token=github_token,
            repo=_GH_REPO,
        )
        if sha:
            print(f"GitHub: commit {sha} → Vercel auto-deploy iniciado")
    else:
        print("GitHub: GITHUB_TOKEN no configurado, push omitido")

    return week_data
