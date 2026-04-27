from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from microshop.shared.config import event_log_path


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    payload: dict[str, Any]
    created_at: str


def publish(event_type: str, payload: dict[str, Any], path: Path | None = None) -> Event:
    event = Event(
        id=str(uuid4()),
        type=event_type,
        payload=payload,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    target = path or event_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.__dict__, separators=(",", ":")) + "\n")
    return event


def read_events(path: Path | None = None) -> list[Event]:
    target = path or event_log_path()
    if not target.exists():
        return []
    events: list[Event] = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                raw = json.loads(line)
                events.append(Event(**raw))
    return events
