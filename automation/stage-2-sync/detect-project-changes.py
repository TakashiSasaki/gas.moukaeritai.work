#!/usr/bin/env python3
"""Build a deterministic Stage 2 synchronization plan for canonical projects."""

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

from automation.shared.project_registry import get_script_id, iter_project_directories, load_metadata


def _load_sibling(name: str, filename: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Stage 2 module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


clasp_client = _load_sibling("stage2_detect_clasp_client", "clasp_client.py")
apps_script_api = _load_sibling("stage2_detect_apps_script_api", "apps_script_api.py")


def _materialized_update_time(metadata: dict[str, Any]) -> str | None:
    sync_state = metadata.get("syncState")
    if isinstance(sync_state, dict) and sync_state.get("lastMaterializedAppsScriptUpdateTime"):
        return str(sync_state["lastMaterializedAppsScriptUpdateTime"])

    # Compatibility with the pre-contract representation. Before syncState was
    # introduced, appsScriptApi.updateTime was written only after a successful
    # source synchronization, so it is a safe checkpoint fallback during the
    # transition.
    apps_script = metadata.get("appsScriptApi")
    if isinstance(apps_script, dict) and apps_script.get("updateTime"):
        return str(apps_script["updateTime"])
    legacy = metadata.get("lastUpdated")
    return str(legacy) if legacy else None


def _is_absent(metadata: dict[str, Any]) -> bool:
    lifecycle = metadata.get("lifecycle")
    return isinstance(lifecycle, dict) and lifecycle.get("driveInventory") == "absent"


def build_plan(
    root: Path | str | None = None,
    *,
    clasp: Any = None,
    api: Any = None,
) -> dict[str, Any]:
    """Inspect canonical projects and return the Stage 2 synchronization plan."""
    clasp = clasp or clasp_client
    api = api or apps_script_api
    base = Path(root).resolve() if root is not None else REPO_ROOT

    # Preserve the legacy best-effort startup behavior until Stage 2 is cut over
    # to direct OAuth and Apps Script API inspection in the next phase step.
    clasp.check_version()
    clasp.refresh_token()
    access_token = clasp.read_access_token()
    if not access_token:
        print(
            "Warning: Could not read access token from .clasprc.json. "
            "Optimization disabled. Proceeding with full pull.",
            file=sys.stderr,
        )

    entries: list[dict[str, Any]] = []
    for project_dir in iter_project_directories(base):
        script_id = get_script_id(project_dir)
        metadata = load_metadata(project_dir, allow_missing=True)
        local_update_time = _materialized_update_time(metadata)

        if _is_absent(metadata):
            entries.append(
                {
                    "scriptId": script_id,
                    "path": project_dir.relative_to(base).as_posix(),
                    "shouldSync": False,
                    "localUpdateTime": local_update_time,
                    "remoteUpdateTime": None,
                    "remoteMetadata": None,
                }
            )
            continue

        remote_metadata = api.get_project(script_id, access_token) if access_token else None
        remote_update_time = None
        if isinstance(remote_metadata, dict) and remote_metadata.get("updateTime"):
            remote_update_time = str(remote_metadata["updateTime"])

        should_sync = True
        if remote_update_time and local_update_time and remote_update_time <= local_update_time:
            should_sync = False

        entries.append(
            {
                "scriptId": script_id,
                "path": project_dir.relative_to(base).as_posix(),
                "shouldSync": should_sync,
                "localUpdateTime": local_update_time,
                "remoteUpdateTime": remote_update_time,
                "remoteMetadata": remote_metadata,
            }
        )

    return {
        "accessTokenAvailable": bool(access_token),
        "projects": entries,
    }


def write_json(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect Apps Script projects requiring Stage 2 synchronization.")
    parser.add_argument("--output", type=Path, required=True, help="Path for the deterministic synchronization plan JSON.")
    args = parser.parse_args()
    plan = build_plan()
    write_json(plan, args.output)
    selected = sum(1 for item in plan["projects"] if item["shouldSync"])
    print(f"Selected {selected}/{len(plan['projects'])} project(s) for Stage 2 synchronization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
