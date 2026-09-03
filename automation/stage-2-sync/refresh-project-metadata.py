#!/usr/bin/env python3
"""Refresh project metadata after successful Stage 2 source synchronization."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import load_metadata, project_path, write_metadata

LEGACY_ROOT_KEYS = (
    "lastUpdated",
    "name",
    "createdTime",
    "modifiedTime",
    "titleByClaspList",
    "titleByDriveApi",
    "application.json",
    "deployments.json",
    "versions.json",
)
LEGACY_STANDALONE_FILES = (
    "deployments.json",
    "deployments.txt",
    "versions.json",
    "versions.txt",
)


def _load_sibling(name: str, filename: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Stage 2 module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


clasp_client = _load_sibling("stage2_refresh_clasp_client", "clasp_client.py")
apps_script_api = _load_sibling("stage2_refresh_apps_script_api", "apps_script_api.py")
validator = _load_sibling("stage2_refresh_validator", "validate-project-state.py")


def _cleanup_standalone_files(project_dir: Path) -> None:
    for filename in LEGACY_STANDALONE_FILES:
        try:
            (project_dir / filename).unlink(missing_ok=True)
        except OSError:
            # Preserve legacy cleanup semantics: stale auxiliary cleanup is best effort.
            pass


def _advance_materialization_checkpoint(
    metadata: dict[str, Any],
    remote_metadata: dict[str, Any] | None,
    plan_item: dict[str, Any],
) -> None:
    update_time = None
    if isinstance(remote_metadata, dict) and remote_metadata.get("updateTime"):
        update_time = str(remote_metadata["updateTime"])
    elif plan_item.get("remoteUpdateTime"):
        update_time = str(plan_item["remoteUpdateTime"])
    if not update_time:
        return

    sync_state = metadata.get("syncState")
    if not isinstance(sync_state, dict):
        sync_state = {}
        metadata["syncState"] = sync_state
    sync_state["lastMaterializedAppsScriptUpdateTime"] = update_time


def refresh_metadata(
    plan: dict[str, Any],
    sync_result: dict[str, Any],
    root: Path | str | None = None,
    *,
    clasp: Any = None,
    api: Any = None,
    state_validator: Any = None,
) -> int:
    """Merge remote metadata and advance checkpoints only for successful syncs."""
    clasp = clasp or clasp_client
    api = api or apps_script_api
    state_validator = state_validator or validator
    base = Path(root).resolve() if root is not None else REPO_ROOT

    plan_projects = plan.get("projects", [])
    result_projects = sync_result.get("projects", [])
    if not isinstance(plan_projects, list) or not isinstance(result_projects, list):
        raise ValueError("plan.projects and sync_result.projects must be lists")

    plan_by_id = {
        item["scriptId"]: item
        for item in plan_projects
        if isinstance(item, dict) and isinstance(item.get("scriptId"), str)
    }
    access_token = clasp.read_access_token()
    refreshed = 0

    for result in result_projects:
        if not isinstance(result, dict) or not result.get("synced"):
            continue
        script_id = result.get("scriptId")
        if not isinstance(script_id, str) or not script_id:
            raise ValueError("synced result is missing scriptId")
        plan_item = plan_by_id.get(script_id)
        if plan_item is None:
            raise ValueError(f"sync result has no matching plan entry: {script_id}")

        project_dir = project_path(script_id, base)
        remote_metadata = plan_item.get("remoteMetadata")
        if not isinstance(remote_metadata, dict):
            remote_metadata = api.get_project(script_id, access_token) if access_token else None

        files_metadata = None
        if access_token:
            files_metadata = api.get_project_files_metadata(script_id, access_token)
            if files_metadata is not None:
                # This must happen before any metadata write so a collision remains workflow-fatal
                # without partially updating repository metadata.
                state_validator.validate_files(files_metadata, script_id)

        metadata = load_metadata(project_dir, allow_missing=True)
        if isinstance(remote_metadata, dict):
            metadata["appsScriptApi"] = remote_metadata
        metadata["deployments"] = clasp.list_deployments(project_dir)
        metadata["versions"] = clasp.list_versions(project_dir)
        if files_metadata is not None:
            metadata["files"] = files_metadata
        _advance_materialization_checkpoint(metadata, remote_metadata, plan_item)

        for key in LEGACY_ROOT_KEYS:
            metadata.pop(key, None)

        write_metadata(project_dir, metadata)
        _cleanup_standalone_files(project_dir)
        refreshed += 1

    return refreshed


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh metadata after successful Stage 2 source synchronization.")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--sync-result", type=Path, required=True)
    args = parser.parse_args()
    try:
        count = refresh_metadata(read_json(args.plan), read_json(args.sync_result))
    except validator.CaseInsensitiveNameConflict as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Refreshed metadata for {count} synchronized project(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
