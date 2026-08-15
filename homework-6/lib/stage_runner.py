"""Shared per-file execution loop reused by every pipeline stage.

Owns only the mechanical file lifecycle common to every stage's main loop:
list the source directory, copy-or-move each file into processing/, hand it
to the stage's own per-record callback, optionally clear the processing file,
and tally processed/passed/failed from the callback's return value. Every
stage keeps its own directory parameters, defaults, and business logic --
this module knows nothing about what any stage actually does with a record.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict
from time import sleep

from lib.common import (
    clear_processing_file,
    copy_into_processing,
    list_json_files,
    move_into_processing,
)

ProcessFn = Callable[[str, Path], bool]


def run_stage_loop(
    source_dir: Path,
    processing_dir: Path,
    copy_mode: str,
    process_fn: ProcessFn,
    clear_processing: bool = True,
) -> Dict[str, int]:
    """Runs `process_fn(transaction_id, working_path)` once per file in
    `source_dir`, moving or copying each into `processing_dir` first per
    `copy_mode` ("copy" or "move").

    `process_fn` owns everything about a record beyond the file lifecycle:
    reading it, deciding what to do, and writing wherever it belongs. Its
    return value is the sole outcome signal: True counts as passed, False as
    failed, toward the returned {"processed", "passed", "failed"} tally.

    When `clear_processing` is False, the working file in `processing_dir` is
    left for the caller to clear itself (Reporting needs this, since it
    clears each file only after its own later aggregate-and-finalize step).
    """
    if copy_mode not in ("copy", "move"):
        raise ValueError(f"copy_mode must be 'copy' or 'move', got {copy_mode!r}")

    processed = passed = failed = 0
    for src in list_json_files(source_dir):
        transaction_id = src.stem
        working = (
            copy_into_processing(src, processing_dir)
            if copy_mode == "copy"
            else move_into_processing(src, processing_dir)
        )

        outcome = process_fn(transaction_id, working)
        processed += 1
        if outcome:
            passed += 1
        else:
            failed += 1

        if clear_processing:
            clear_processing_file(working)

    return {"processed": processed, "passed": passed, "failed": failed}
