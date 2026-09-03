#!/usr/bin/env python3
"""Apps Script API I/O primitives for Stage 2.

This module owns HTTP interaction only. Project selection, change detection,
metadata merge policy, and validation belong to higher-level Stage 2 steps.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from typing import Any, Callable

API_ROOT = "https://script.googleapis.com/v1/projects"
_EXCLUDED_FILE_FIELDS = {"source", "functionSet"}


def _request_json(
    url: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any] | None:
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {access_token}")
    try:
        with opener(request) as response:
            payload = json.load(response)
    except Exception as exc:
        print(f"Error fetching Apps Script API resource {url}: {exc}", file=sys.stderr)
        return None
    return payload if isinstance(payload, dict) else None


def get_project(
    script_id: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any] | None:
    """Fetch the complete Apps Script project resource."""
    return _request_json(
        f"{API_ROOT}/{script_id}",
        access_token,
        opener=opener,
    )


def get_project_files_metadata(
    script_id: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]] | None:
    """Fetch `/content` and strip source-bearing fields from each file."""
    payload = _request_json(
        f"{API_ROOT}/{script_id}/content",
        access_token,
        opener=opener,
    )
    if payload is None:
        return None
    files = payload.get("files", [])
    if not isinstance(files, list):
        return None
    return [
        {key: value for key, value in item.items() if key not in _EXCLUDED_FILE_FIELDS}
        for item in files
        if isinstance(item, dict)
    ]
