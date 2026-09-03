"""Repository-access primitives for materialized Apps Script projects.

This module deliberately contains no Drive API, Apps Script API, clasp, change
 detection, or documentation-generation business logic.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class ProjectRegistryError(ValueError):
    """Raised when repository project state is malformed or unsafe to access."""


_DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def repository_root() -> Path:
    """Return the repository root containing this automation package."""
    return _DEFAULT_REPOSITORY_ROOT


def projects_path(root: Path | str | None = None) -> Path:
    """Return the canonical `projects/` path for a repository root."""
    base = Path(root).resolve() if root is not None else repository_root()
    return base / "projects"


def iter_project_directories(root: Path | str | None = None) -> tuple[Path, ...]:
    """Return canonical project directories in deterministic name order."""
    base = projects_path(root)
    if not base.exists():
        return ()
    if not base.is_dir():
        raise ProjectRegistryError(f"projects path is not a directory: {base}")
    return tuple(sorted((path for path in base.iterdir() if path.is_dir()), key=lambda path: path.name))


def _validate_script_id(script_id: str) -> str:
    if not isinstance(script_id, str) or not script_id:
        raise ProjectRegistryError("scriptId must be a non-empty string")
    if script_id in {".", ".."} or Path(script_id).name != script_id or "/" in script_id or "\\" in script_id:
        raise ProjectRegistryError(f"scriptId is not safe as a project directory name: {script_id!r}")
    return script_id


def project_path(script_id: str, root: Path | str | None = None) -> Path:
    """Build the canonical `projects/<SCRIPT_ID>/` path without creating it."""
    return projects_path(root) / _validate_script_id(script_id)


def _load_json_object(path: Path, *, allow_missing: bool = False) -> dict[str, Any]:
    if allow_missing and not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProjectRegistryError(f"required repository file is missing: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectRegistryError(f"cannot read JSON object from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProjectRegistryError(f"expected a JSON object in {path}")
    return payload


def load_clasp(project_dir: Path | str) -> dict[str, Any]:
    """Read and validate a project's `.clasp.json` object."""
    return _load_json_object(Path(project_dir) / ".clasp.json")


def get_script_id(project_dir: Path | str) -> str:
    """Read the project's non-empty `scriptId` from `.clasp.json`."""
    payload = load_clasp(project_dir)
    script_id = payload.get("scriptId")
    return _validate_script_id(script_id)


def load_metadata(project_dir: Path | str, *, allow_missing: bool = False) -> dict[str, Any]:
    """Read a project's `metadata.json` object.

    `allow_missing=True` is intended for Stage 1 while materializing a newly
    discovered project. It does not suppress malformed existing metadata.
    """
    return _load_json_object(Path(project_dir) / "metadata.json", allow_missing=allow_missing)


def write_metadata(project_dir: Path | str, metadata: dict[str, Any]) -> None:
    """Atomically replace `metadata.json` with deterministic UTF-8 JSON."""
    directory = Path(project_dir)
    if not directory.is_dir():
        raise ProjectRegistryError(f"project directory does not exist: {directory}")
    if not isinstance(metadata, dict):
        raise ProjectRegistryError("metadata must be a JSON object")

    destination = directory / "metadata.json"
    serialized = json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".metadata.json.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(serialized)
            temporary_name = temporary.name
        os.replace(temporary_name, destination)
    except OSError as exc:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise ProjectRegistryError(f"cannot write metadata to {destination}: {exc}") from exc
