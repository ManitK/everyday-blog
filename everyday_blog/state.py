from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def load(path: Path) -> datetime | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text()).get("last_successful_run")
    return datetime.fromisoformat(value) if value else None


def save(path: Path, timestamp: datetime) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"last_successful_run": timestamp.isoformat()}, indent=2) + "\n")
    temporary.replace(path)
