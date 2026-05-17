#!/usr/bin/env python
"""Fetch Paris events, score with Claude, push to Notion and GitHub."""
import asyncio
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestrator import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente semanal de eventos París")
    parser.add_argument("--start", metavar="YYYY-MM-DD", help="Fecha inicio (default: mañana)")
    parser.add_argument("--end", metavar="YYYY-MM-DD", help="Fecha fin (default: inicio + 8 días)")
    parser.add_argument("--dry-run", action="store_true", help="No escribe a Notion ni hace git push")
    parser.add_argument("--top", type=int, default=20, help="Número de eventos curados (default: 20)")
    args = parser.parse_args()

    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None

    result = asyncio.run(run(start=start, end=end, dry_run=args.dry_run, top_k=args.top))
    if result:
        print(f"\nSemana {result.week_id}: {result.total_scored} eventos curados de {result.total_scraped} scrapeados.")


if __name__ == "__main__":
    main()
