#!/usr/bin/env python3
"""Fetch the Apps Script inventory from Drive and persist a raw snapshot."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.google_oauth import GoogleOAuthError, acquire_access_token

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
SNAPSHOT_PATTERN = re.compile(r"^\d{8}-\d{6}\.json$")
SNAPSHOT_RETENTION = 5


def repository_root() -> Path:
    return REPO_ROOT


def snapshot_directory(root: Path | None = None) -> Path:
    base = root if root is not None else repository_root()
    return base / "data" / "inventory" / "drive-api" / "snapshots"


def fetch_inventory(access_token: str, session: Any = requests) -> dict[str, list[dict[str, Any]]] | None:
    """Fetch the Drive inventory exhaustively through all result pages.

    A successful HTTP response is not sufficient evidence of completeness:
    Drive can explicitly return ``incompleteSearch: true``. Such a response must
    not be converted into an authoritative negative observation.
    """
    files: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {
            "q": "mimeType = 'application/vnd.google-apps.script' and trashed = false",
            "pageSize": 100,
            "fields": "incompleteSearch, nextPageToken, files(id, name, createdTime, modifiedTime)",
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            response = session.get(
                DRIVE_FILES_URL,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except Exception as exc:
            print(f"Error: Drive inventory request failed: {exc}", file=sys.stderr)
            return None
        if response.status_code != 200:
            print(f"Error: Drive inventory request failed with HTTP status {response.status_code}", file=sys.stderr)
            return None
        try:
            payload = response.json()
        except Exception as exc:
            print(f"Error: Drive inventory response was not valid JSON: {exc}", file=sys.stderr)
            return None
        if not isinstance(payload, dict):
            print("Error: Drive inventory response must be a JSON object", file=sys.stderr)
            return None
        if payload.get("incompleteSearch") is True:
            print(
                "Error: Drive API returned incompleteSearch=true; refusing to treat "
                "this inventory as complete or infer project absence.",
                file=sys.stderr,
            )
            return None
        page_files = payload.get("files", [])
        if not isinstance(page_files, list):
            print("Error: Drive inventory response field 'files' must be a list", file=sys.stderr)
            return None
        files.extend(item for item in page_files if isinstance(item, dict))
        next_page = payload.get("nextPageToken")
        if next_page is not None and (not isinstance(next_page, str) or not next_page):
            print("Error: Drive inventory nextPageToken must be a non-empty string", file=sys.stderr)
            return None
        page_token = next_page
        if not page_token:
            break

    return {"files": files}


def prune_timestamped_snapshots(directory: Path, keep: int = SNAPSHOT_RETENTION) -> None:
    snapshots = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and SNAPSHOT_PATTERN.fullmatch(path.name)
    )
    for stale in snapshots[:-keep] if keep > 0 else snapshots:
        stale.unlink()


def write_snapshot(
    inventory: dict[str, Any],
    directory: Path,
    now: datetime | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    output = directory / f"{timestamp}.json"
    output.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    prune_timestamped_snapshots(directory)
    return output


def main() -> int:
    try:
        access_token = acquire_access_token()
    except GoogleOAuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    inventory = fetch_inventory(access_token)
    if inventory is None:
        return 1
    # Repository-owned evidence that exhaustive pagination completed and Drive
    # did not report an incomplete search. Historical/manual snapshots lacking
    # the marker can prove presence but cannot prove project absence.
    snapshot = {"complete": True, **inventory}
    output = write_snapshot(snapshot, snapshot_directory())
    print(f"Wrote {len(inventory['files'])} Drive inventory entries to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
