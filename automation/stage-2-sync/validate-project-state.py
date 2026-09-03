#!/usr/bin/env python3
"""Validate materialized project state without performing external I/O."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import get_script_id, iter_project_directories, load_metadata


class CaseInsensitiveNameConflict(ValueError):
    """Raised when Apps Script file names collide on a case-insensitive filesystem."""


class ProjectStateError(ValueError):
    """Raised when lifecycle or synchronization state violates its contract."""


def windows_case_insensitive_key(name: str) -> str:
    """Approximate Windows ordinal filename comparison without full case folding.

    Windows case-insensitive filename matching uses an uppercase-character table:
    each input character maps to at most one comparison character. Python's
    ``casefold()`` is intentionally stronger and can perform multi-character
    expansions such as ``ß -> ss``, which would reject filenames that Windows
    can keep distinct. Use only one-code-point uppercase mappings here and leave
    characters unchanged when Python's full uppercase mapping expands them.
    """
    mapped: list[str] = []
    for character in name:
        uppercase = character.upper()
        mapped.append(uppercase if len(uppercase) == 1 else character)
    return "".join(mapped)


def find_case_insensitive_name_conflicts(files: list[dict[str, Any]]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    conflicts: list[tuple[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if not isinstance(name, str):
            name = str(name)
        comparison_key = windows_case_insensitive_key(name)
        if comparison_key in seen:
            conflicts.append((seen[comparison_key], name))
        else:
            seen[comparison_key] = name
    return conflicts


def validate_files(files: list[dict[str, Any]], script_id: str) -> None:
    conflicts = find_case_insensitive_name_conflicts(files)
    if not conflicts:
        return
    details = "\n".join(
        f"  Conflict: '{first}' vs '{second}' (identical under Windows-style case comparison)"
        for first, second in conflicts
    )
    raise CaseInsensitiveNameConflict(
        f"ERROR: Case-insensitive filename conflict detected in project {script_id}.\n"
        f"{details}\n"
        "  On Windows these files map to the same path. Remove one of the conflicting "
        "files from the Apps Script project before pulling."
    )


def validate_state_contract(metadata: dict[str, Any], script_id: str) -> None:
    lifecycle = metadata.get("lifecycle")
    if lifecycle is not None:
        if not isinstance(lifecycle, dict):
            raise ProjectStateError(f"{script_id}: lifecycle must be an object")
        drive_inventory = lifecycle.get("driveInventory")
        if drive_inventory not in {"present", "absent"}:
            raise ProjectStateError(
                f"{script_id}: lifecycle.driveInventory must be 'present' or 'absent'"
            )

    sync_state = metadata.get("syncState")
    if sync_state is not None:
        if not isinstance(sync_state, dict):
            raise ProjectStateError(f"{script_id}: syncState must be an object")
        checkpoint = sync_state.get("lastMaterializedAppsScriptUpdateTime")
        if checkpoint is not None and (not isinstance(checkpoint, str) or not checkpoint):
            raise ProjectStateError(
                f"{script_id}: syncState.lastMaterializedAppsScriptUpdateTime must be a non-empty string"
            )


def validate_repository(root: Path | str | None = None) -> None:
    for project_dir in iter_project_directories(root):
        script_id = get_script_id(project_dir)
        metadata = load_metadata(project_dir, allow_missing=True)
        validate_state_contract(metadata, script_id)
        files = metadata.get("files")
        if isinstance(files, list):
            validate_files(files, script_id)


def main() -> int:
    try:
        validate_repository()
    except (CaseInsensitiveNameConflict, ProjectStateError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Project-state validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
