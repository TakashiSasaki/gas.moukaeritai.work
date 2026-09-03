#!/usr/bin/env python3
"""Materialize Stage 2-selected Apps Script sources through clasp pull."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import (
    ProjectRegistryError,
    get_script_id,
    project_path,
)
from automation.shared.project_validation import CaseInsensitiveNameConflict, validate_files


def _load_sibling(name: str, filename: str) -> ModuleType:
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Stage 3 module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


clasp_client = _load_sibling("stage3_clasp_client", "clasp_client.py")


class MaterializationPlanError(ValueError):
    """Raised before source changes when a Stage 2 plan is unsafe or malformed."""


class PostPullValidationError(RuntimeError):
    """Raised when clasp reports success but the resulting project tree is invalid."""


_EXTENSION_BY_TYPE = {
    "SERVER_JS": ".js",
    "HTML": ".html",
    "JSON": ".json",
}


def _plan_projects(plan: dict[str, Any], base: Path) -> list[dict[str, Any]]:
    if plan.get("schemaVersion") != 1:
        raise MaterializationPlanError("Stage 2 plan schemaVersion must be 1")
    projects = plan.get("projects")
    if not isinstance(projects, list):
        raise MaterializationPlanError("Stage 2 plan projects must be a list")

    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in projects:
        if not isinstance(item, dict):
            raise MaterializationPlanError("each Stage 2 plan project must be an object")
        script_id = item.get("scriptId")
        if not isinstance(script_id, str) or not script_id:
            raise MaterializationPlanError("Stage 2 plan project is missing scriptId")
        if script_id in seen:
            raise MaterializationPlanError(f"duplicate Stage 2 plan project: {script_id}")
        seen.add(script_id)

        materialization = item.get("materialization")
        if not isinstance(materialization, dict) or not isinstance(materialization.get("required"), bool):
            raise MaterializationPlanError(f"{script_id}: materialization.required must be a boolean")
        required = materialization["required"]
        if item.get("lifecycle") == "absent" and required:
            raise MaterializationPlanError(f"{script_id}: absent project must not require materialization")

        canonical = project_path(script_id, base)
        expected_path = canonical.relative_to(base).as_posix()
        if item.get("path") != expected_path:
            raise MaterializationPlanError(
                f"{script_id}: plan path {item.get('path')!r} does not match canonical {expected_path!r}"
            )
        if required:
            if not canonical.is_dir():
                raise MaterializationPlanError(f"{script_id}: canonical project directory is missing")
            if not isinstance(item.get("observation"), dict):
                raise MaterializationPlanError(f"{script_id}: required materialization needs a Stage 2 observation")
        validated.append(item)
    return validated


def _source_relative_path(file_metadata: dict[str, Any], script_id: str) -> PurePosixPath:
    name = file_metadata.get("name")
    file_type = file_metadata.get("type")
    if not isinstance(name, str) or not name:
        raise PostPullValidationError(f"{script_id}: observed Apps Script file is missing a name")
    if "\\" in name:
        raise PostPullValidationError(f"{script_id}: observed Apps Script filename contains a backslash: {name!r}")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise PostPullValidationError(f"{script_id}: observed Apps Script filename is not a safe relative path: {name!r}")
    extension = _EXTENSION_BY_TYPE.get(file_type)
    if extension is None:
        raise PostPullValidationError(f"{script_id}: unsupported Apps Script file type for validation: {file_type!r}")
    return PurePosixPath(str(relative) + extension)


def validate_post_pull(project_dir: Path, script_id: str, observation: dict[str, Any]) -> None:
    """Validate clasp identity and all source files observed before the pull."""
    try:
        materialized_script_id = get_script_id(project_dir)
    except ProjectRegistryError as exc:
        raise PostPullValidationError(f"{script_id}: invalid post-pull .clasp.json: {exc}") from exc
    if materialized_script_id != script_id:
        raise PostPullValidationError(
            f"{script_id}: post-pull .clasp.json scriptId changed to {materialized_script_id!r}"
        )

    files = observation.get("files")
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise PostPullValidationError(f"{script_id}: Stage 2 observation files must be an object list")
    try:
        validate_files(files, script_id)
    except CaseInsensitiveNameConflict as exc:
        raise PostPullValidationError(str(exc)) from exc
    for file_metadata in files:
        relative = _source_relative_path(file_metadata, script_id)
        destination = project_dir.joinpath(*relative.parts)
        if not destination.is_file():
            raise PostPullValidationError(
                f"{script_id}: clasp pull did not materialize observed source file {relative.as_posix()!r}"
            )


def _restore_project(project_dir: Path, backup: Path) -> None:
    try:
        if project_dir.exists():
            shutil.rmtree(project_dir)
        shutil.copytree(backup, project_dir)
    except OSError as exc:
        raise RuntimeError(f"failed to restore {project_dir} after materialization failure: {exc}") from exc


def materialize_plan(
    plan: dict[str, Any],
    root: Path | str | None = None,
    *,
    clasp: Any = None,
) -> dict[str, Any]:
    """Run selected pulls transactionally per project and return deterministic results."""
    clasp = clasp or clasp_client
    base = Path(root).resolve() if root is not None else REPO_ROOT
    projects = _plan_projects(plan, base)
    results: list[dict[str, Any]] = []

    for item in projects:
        script_id = item["scriptId"]
        required = item["materialization"]["required"]
        result: dict[str, Any] = {
            "scriptId": script_id,
            "required": required,
            "attempted": False,
            "materialized": False,
            "error": None,
        }
        if not required:
            results.append(result)
            continue

        project_dir = project_path(script_id, base)
        observation = item["observation"]
        result["attempted"] = True
        with tempfile.TemporaryDirectory(prefix="gas-stage3-") as temporary:
            backup = Path(temporary) / "project-backup"
            shutil.copytree(project_dir, backup)
            try:
                clasp.pull(project_dir)
                validate_post_pull(project_dir, script_id, observation)
                result["materialized"] = True
            except Exception as exc:
                try:
                    _restore_project(project_dir, backup)
                except Exception as restore_exc:
                    raise RuntimeError(
                        f"{script_id}: materialization failed ({exc}) and rollback also failed ({restore_exc})"
                    ) from restore_exc
                result["error"] = str(exc)
                print(f"Error: projects/{script_id} materialization rolled back: {exc}", file=sys.stderr)
        results.append(result)

    return {
        "schemaVersion": 1,
        "projects": results,
        "allRequiredMaterialized": all(
            (not item["required"]) or item["materialized"] for item in results
        ),
    }


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MaterializationPlanError(f"expected JSON object in {path}")
    return payload


def write_json(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize Stage 2-selected Apps Script project sources.")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = materialize_plan(read_json(args.plan))
    except (MaterializationPlanError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    write_json(result, args.output)
    attempted = sum(1 for item in result["projects"] if item["attempted"])
    failed = sum(1 for item in result["projects"] if item["attempted"] and not item["materialized"])
    print(f"Stage 3 attempted {attempted} pull(s); {failed} failed and were rolled back.")
    return 0 if result["allRequiredMaterialized"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
