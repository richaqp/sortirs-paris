from __future__ import annotations
import json
import shutil
from pathlib import Path

from agent.scoring.models import WeekData


def write_week_json(week_data: WeekData, repo_root: Path) -> Path:
    weeks_dir = repo_root / "web" / "content" / "weeks"
    weeks_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(week_data.model_dump_json())

    week_file = weeks_dir / f"{week_data.week_id}.json"
    week_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    latest = weeks_dir / "latest.json"
    shutil.copy(week_file, latest)

    return week_file
