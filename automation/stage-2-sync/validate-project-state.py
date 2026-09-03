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
from automation.shared.project_validation import (
    CaseInsensitiveNameConflict,
    find_case_insensitive_name_conflicts,
    validate_files,
    windows_case_insensitive_key,
)


class ProjectStateError(ValueError):
    """Raised when lifecycle or synchronization state violates its contract."""


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
