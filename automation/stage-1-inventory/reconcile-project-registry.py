#!/usr/bin/env python3
"""Reconcile a Drive inventory snapshot into canonical project registry state.

This is steady-state materialization only.  Historical metadata migration and
public index publication are deliberately separate responsibilities.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import load_metadata, project_path, write_metadata


def snapshot_directory(root: Path | None = None) -> Path:
    base = root if root is not None else REPO_ROOT
    return base / "data" / "inventory" / "drive-api" / "snapshots"


def latest_snapshot(root: Path | None = None) -> Path:
    directory = snapshot_directory(root)
    candidates = sorted(path for path in directory.glob("2*.json") if path.is_file())
    if not candidates:
        raise FileNotFoundError(f"No Drive inventory snapshots found in {directory}")
    return candidates[-1]


def load_snapshot(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list in snapshot {path}")
    return [item for item in payload if isinstance(item, dict)]


def _write_clasp_if_missing(directory: Path, script_id: str) -> None:
    clasp_path = directory / ".clasp.json"
    if clasp_path.exists():
        return
    temporary = clasp_path.with_name(clasp_path.name + ".tmp")
    temporary.write_text(
        json.dumps({"scriptId": script_id, "rootDir": "."}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, clasp_path)


def reconcile(snapshot: Path, root: Path | None = None) -> int:
    base = root if root is not None else REPO_ROOT
    reconciled = 0
    for item in load_snapshot(snapshot):
        raw_id = item.get("id")
        if not isinstance(raw_id, str) or not raw_id:
            continue
        directory = project_path(raw_id, base)
        directory.mkdir(parents=True, exist_ok=True)
        _write_clasp_if_missing(directory, raw_id)

        metadata = load_metadata(directory, allow_missing=True)
        metadata["driveApi"] = item
        write_metadata(directory, metadata)
        reconciled += 1
    return reconciled


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "snapshot",
        nargs="?",
        type=Path,
        help="Drive inventory snapshot; defaults to the latest canonical snapshot",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = args.snapshot or latest_snapshot()
    count = reconcile(snapshot)
    print(f"Reconciled {count} projects from {snapshot}")


if __name__ == "__main__":
    main()
