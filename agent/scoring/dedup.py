from __future__ import annotations
import json
from pathlib import Path


def load_recent_shown_links(repo_root: Path, weeks: int = 4) -> set[str]:
    """Return the set of event links that appeared in the last N weekly JSONs."""
    weeks_dir = repo_root / "web" / "content" / "weeks"
    if not weeks_dir.exists():
        return set()

    json_files = sorted(weeks_dir.glob("????-W??.json"), reverse=True)
    links: set[str] = set()
    for path in json_files[:weeks]:
        try:
            data = json.loads(path.read_text())
            for ev in data.get("events", []):
                if ev.get("link"):
                    links.add(ev["link"])
        except Exception:
            continue
    return links
