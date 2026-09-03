#!/usr/bin/env python3
"""Explicitly migrate legacy project metadata representations.

The default mode is read-only.  Pass --apply to persist changes and remove
successfully migrated standalone legacy files.  This utility is intentionally
not part of the steady-state Stage 1 pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import iter_project_directories, load_metadata, write_metadata

LEGACY_JSON = {
    "deployments.json": "deployments",
    "versions.json": "versions",
}
LEGACY_TEXT = ("deployments.txt", "versions.txt")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def migrate_project(project_dir: Path, apply: bool = False) -> tuple[bool, list[str]]:
    metadata = load_metadata(project_dir, allow_missing=True)
    changed = False
    notes: list[str] = []

    if "version" in metadata:
        drive_api = metadata.get("driveApi")
        if not isinstance(drive_api, dict):
            notes.append("conflict: root version cannot migrate without driveApi object")
        elif "version" in drive_api and drive_api["version"] != metadata["version"]:
            notes.append("conflict: root version differs from driveApi.version")
        else:
            drive_api["version"] = metadata["version"]
            metadata.pop("version", None)
            changed = True
            notes.append("migrate root version -> driveApi.version")

    for legacy_key, canonical_key in LEGACY_JSON.items():
        if legacy_key in metadata:
            legacy_value = metadata[legacy_key]
            if canonical_key in metadata and metadata[canonical_key] != legacy_value:
                notes.append(f"conflict: {legacy_key} differs from {canonical_key}")
            else:
                metadata[canonical_key] = legacy_value
                metadata.pop(legacy_key, None)
                changed = True
                notes.append(f"migrate root {legacy_key} -> {canonical_key}")

        legacy_path = project_dir / legacy_key
        if legacy_path.exists():
            legacy_value = _load_json(legacy_path)
            if canonical_key in metadata and metadata[canonical_key] != legacy_value:
                notes.append(f"conflict: standalone {legacy_key} differs from {canonical_key}")
            else:
                metadata[canonical_key] = legacy_value
                changed = True
                notes.append(f"migrate standalone {legacy_key} -> {canonical_key}")
                if apply:
                    legacy_path.unlink()

    for filename in LEGACY_TEXT:
        path = project_dir / filename
        if path.exists():
            notes.append(f"remove obsolete {filename}")
            if apply:
                path.unlink()
            changed = True

    if apply and changed:
        write_metadata(project_dir, metadata)
    return changed, notes


def run(root: Path | None = None, apply: bool = False) -> int:
    base = root if root is not None else REPO_ROOT
    affected = 0
    for project_dir in iter_project_directories(base):
        changed, notes = migrate_project(project_dir, apply=apply)
        if not changed and not notes:
            continue
        affected += 1
        mode = "APPLY" if apply else "DRY-RUN"
        print(f"[{mode}] {project_dir.name}")
        for note in notes:
            print(f"  - {note}")
    return affected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist non-conflicting migrations and delete migrated legacy files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    affected = run(apply=args.apply)
    mode = "applied" if args.apply else "would affect"
    print(f"Legacy metadata migration {mode} {affected} project(s)")


if __name__ == "__main__":
    main()
