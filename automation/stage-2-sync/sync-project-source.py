#!/usr/bin/env python3
"""Synchronize source for projects selected by Stage 2."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import project_path


def _load_sibling(name: str, filename: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Stage 2 module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


clasp_client = _load_sibling("stage2_sync_clasp_client", "clasp_client.py")


def sync_plan(
    plan: dict[str, Any],
    root: Path | str | None = None,
    *,
    clasp: Any = None,
) -> dict[str, Any]:
    """Execute only clasp source pulls, continuing on per-project failures."""
    clasp = clasp or clasp_client
    base = Path(root).resolve() if root is not None else REPO_ROOT
    results: list[dict[str, Any]] = []

    projects = plan.get("projects", [])
    if not isinstance(projects, list):
        raise ValueError("plan.projects must be a list")

    for item in projects:
        if not isinstance(item, dict):
            raise ValueError("each plan project must be an object")
        script_id = item.get("scriptId")
        if not isinstance(script_id, str) or not script_id:
            raise ValueError("plan project is missing scriptId")

        result: dict[str, Any] = {
            "scriptId": script_id,
            "attempted": False,
            "synced": False,
            "error": None,
        }
        if not item.get("shouldSync", True):
            results.append(result)
            continue

        result["attempted"] = True
        directory = project_path(script_id, base)
        try:
            clasp.pull(directory)
            result["synced"] = True
        except subprocess.CalledProcessError as exc:
            result["error"] = f"clasp command failed with exit code {exc.returncode}"
            print(f"Error: command failed in projects/{script_id}: {exc}", file=sys.stderr)
        results.append(result)

    return {"projects": results}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path}")
    return payload


def write_json(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize source for projects selected by a Stage 2 plan.")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = sync_plan(read_json(args.plan))
    write_json(result, args.output)
    failed = sum(1 for item in result["projects"] if item["attempted"] and not item["synced"])
    print(f"Completed source synchronization with {failed} clasp failure(s).")
    # Preserve the legacy per-project clasp failure behavior: log and continue successfully.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
