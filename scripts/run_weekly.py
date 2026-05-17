#!/usr/bin/env python
"""Fetch Paris events for the next 7 days and push to Notion."""
import asyncio
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestrator import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente semanal de eventos París → Notion")
    parser.add_argument("--start", metavar="YYYY-MM-DD", help="Fecha inicio (default: mañana)")
    parser.add_argument("--end", metavar="YYYY-MM-DD", help="Fecha fin (default: inicio + 7 días)")
    args = parser.parse_args()

    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None

    asyncio.run(run(start, end))


if __name__ == "__main__":
    main()
