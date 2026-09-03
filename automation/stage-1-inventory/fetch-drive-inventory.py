#!/usr/bin/env python3
"""Fetch the Apps Script inventory from Drive and persist a raw snapshot.

This module is intentionally limited to external observation.  It does not
materialize projects or publish the public project index.
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
SCRIPT_MIME_TYPE = "application/vnd.google-apps.script"
SNAPSHOT_PATTERN = re.compile(r"^\d{8}-\d{6}\.json$")
SNAPSHOT_RETENTION = 5
FIELDS = (
    "nextPageToken, "
    "files(id,name,createdTime,modifiedTime,version,webViewLink,owners)"
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def snapshot_directory(root: Path | None = None) -> Path:
    base = root if root is not None else repository_root()
    return base / "data" / "inventory" / "drive-api" / "snapshots"


def load_credentials(path: Path | None = None) -> dict[str, Any]:
    credentials_path = path if path is not None else Path.home() / ".clasprc.json"
    with credentials_path.open("r", encoding="utf-8") as handle:
        credentials = json.load(handle)
    if not isinstance(credentials, dict):
        raise ValueError(f"Expected JSON object in {credentials_path}")
    return credentials


def refresh_access_token(
    credentials: dict[str, Any], session: Any = requests
) -> str:
    response = session.post(
        TOKEN_URL,
        data={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("OAuth token refresh did not return access_token")
    return str(token)


def fetch_inventory(access_token: str, session: Any = requests) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params: dict[str, Any] = {
        "q": f"mimeType='{SCRIPT_MIME_TYPE}' and trashed=false",
        "fields": FIELDS,
        "pageSize": 1000,
    }
    files: list[dict[str, Any]] = []

    while True:
        response = session.get(DRIVE_FILES_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        page_files = payload.get("files", [])
        if not isinstance(page_files, list):
            raise RuntimeError("Drive API response contains a non-list files field")
        files.extend(item for item in page_files if isinstance(item, dict))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
        params["pageToken"] = page_token

    return files


def prune_timestamped_snapshots(directory: Path, keep: int = SNAPSHOT_RETENTION) -> None:
    snapshots = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and SNAPSHOT_PATTERN.fullmatch(path.name)
    )
    for stale in snapshots[:-keep] if keep > 0 else snapshots:
        stale.unlink()


def write_snapshot(
    inventory: list[dict[str, Any]],
    directory: Path,
    now: datetime | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    output = directory / f"{timestamp}.json"
    output.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    prune_timestamped_snapshots(directory)
    return output


def main() -> None:
    credentials = load_credentials()
    access_token = refresh_access_token(credentials)
    inventory = fetch_inventory(access_token)
    output = write_snapshot(inventory, snapshot_directory())
    print(f"Wrote {len(inventory)} Drive inventory entries to {output}")


if __name__ == "__main__":
    main()
