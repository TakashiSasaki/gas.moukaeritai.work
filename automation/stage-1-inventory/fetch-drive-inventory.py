#!/usr/bin/env python3
"""Fetch the Apps Script inventory from Drive and persist a raw snapshot.

This module is intentionally limited to external observation. It preserves the
legacy Stage 1 Drive/OAuth and snapshot contracts while moving their ownership
under automation/ and data/.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
SNAPSHOT_PATTERN = re.compile(r"^\d{8}-\d{6}\.json$")
SNAPSHOT_RETENTION = 5


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def snapshot_directory(root: Path | None = None) -> Path:
    base = root if root is not None else repository_root()
    return base / "data" / "inventory" / "drive-api" / "snapshots"


def load_credentials(path: Path | None = None) -> dict[str, Any] | None:
    credentials_path = path if path is not None else Path.home() / ".clasprc.json"
    if not credentials_path.exists():
        return None
    data = json.loads(credentials_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    tokens = data.get("tokens")
    if isinstance(tokens, dict) and isinstance(tokens.get("default"), dict):
        return tokens["default"]
    token = data.get("token")
    return token if isinstance(token, dict) else None


def refresh_access_token(credentials: dict[str, Any], session: Any = requests) -> str | None:
    response = session.post(
        TOKEN_URL,
        data={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    if response.status_code != 200:
        return None
    token = response.json().get("access_token")
    return str(token) if token else None


def fetch_inventory(access_token: str, session: Any = requests) -> dict[str, list[dict[str, Any]]] | None:
    files: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {
            "q": "mimeType = 'application/vnd.google-apps.script' and trashed = false",
            "pageSize": 100,
            "fields": "nextPageToken, files(id, name, createdTime, modifiedTime)",
        }
        if page_token:
            params["pageToken"] = page_token
        response = session.get(
            DRIVE_FILES_URL,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        page_files = payload.get("files", [])
        if not isinstance(page_files, list):
            return None
        files.extend(item for item in page_files if isinstance(item, dict))
        page_token = payload.get("nextPageToken")
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
    inventory: dict[str, list[dict[str, Any]]],
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
    credentials = load_credentials()
    if not credentials:
        return 1
    access_token = refresh_access_token(credentials)
    if not access_token:
        return 1
    inventory = fetch_inventory(access_token)
    if not inventory:
        return 1
    output = write_snapshot(inventory, snapshot_directory())
    print(f"Wrote {len(inventory['files'])} Drive inventory entries to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
