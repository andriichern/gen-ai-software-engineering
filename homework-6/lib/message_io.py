"""Low-level helpers for reading/writing the lean per-hop message envelopes
that stages exchange through shared/processing/ and shared/output/.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from lib.models import StageContext


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def build_envelope(source_stage: str, target_stage: str, data: dict) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "timestamp": now_iso(),
        "source_stage": source_stage,
        "target_stage": target_stage,
        "message_type": "transaction",
        "data": data,
    }


def context_from_envelope_data(data: dict) -> StageContext:
    return StageContext.from_dict(data)


def clear_directory(path: Path) -> None:
    """Delete every file directly inside path, leaving the directory itself
    and any subdirectories untouched. Never deletes shared/ itself."""
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()
