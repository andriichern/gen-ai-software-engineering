"""Loading the transaction dataset from an overridable source.

The source is never hardcoded to a specific file's contents; it defaults to
sample-transactions.json only when nothing else is given, and may equally be
a directory of one-file-per-transaction JSON records.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_transactions(source: str) -> list[dict]:
    """Load transaction records from a JSON array file or a directory of
    one-record-per-file JSON files. Read-only; never modifies the source."""
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"transaction dataset not found: {path}")

    if path.is_dir():
        records = []
        for record_path in sorted(path.glob("*.json")):
            records.append(json.loads(record_path.read_text()))
        return records

    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return [data]
