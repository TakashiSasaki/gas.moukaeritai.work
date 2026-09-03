#!/usr/bin/env python3
"""Fail-closed structured Apps Script API I/O for Stage 2 inspection."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Callable

API_ROOT = "https://script.googleapis.com/v1/projects"
_EXCLUDED_FILE_FIELDS = {"source", "functionSet"}
_FILE_METADATA_FIELDS = (
    "files(name,type,lastModifyUser(domain,email,name,photoUrl),createTime,updateTime)"
)


class AppsScriptApiError(RuntimeError):
    """Raised when a required Apps Script API observation cannot be obtained."""


def _request_json(
    url: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {access_token}")
    try:
        with opener(request) as response:
            payload = json.load(response)
    except Exception as exc:
        raise AppsScriptApiError(f"Apps Script API request failed for {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AppsScriptApiError(f"Apps Script API response must be an object: {url}")
    return payload


def _object_list(payload: dict[str, Any], field: str, url: str) -> list[dict[str, Any]]:
    values = payload.get(field, [])
    if not isinstance(values, list):
        raise AppsScriptApiError(f"Apps Script API response field {field!r} must be a list: {url}")
    if any(not isinstance(item, dict) for item in values):
        raise AppsScriptApiError(
            f"Apps Script API response field {field!r} contains a non-object resource: {url}"
        )
    return values


def _paged_resources(
    base_url: str,
    access_token: str,
    field: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    page_token: str | None = None
    seen_tokens: set[str] = set()
    while True:
        url = base_url
        if page_token:
            url += "?" + urllib.parse.urlencode({"pageToken": page_token})
        payload = _request_json(url, access_token, opener=opener)
        resources.extend(_object_list(payload, field, url))
        next_token = payload.get("nextPageToken")
        if next_token is None:
            break
        if not isinstance(next_token, str) or not next_token:
            raise AppsScriptApiError(f"Apps Script API nextPageToken must be a non-empty string: {url}")
        if next_token in seen_tokens:
            raise AppsScriptApiError(f"Apps Script API repeated pagination token for {base_url}")
        seen_tokens.add(next_token)
        page_token = next_token
    return resources


def get_project(
    script_id: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    return _request_json(f"{API_ROOT}/{script_id}", access_token, opener=opener)


def get_project_files_metadata(
    script_id: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"fields": _FILE_METADATA_FIELDS})
    url = f"{API_ROOT}/{script_id}/content?{query}"
    payload = _request_json(url, access_token, opener=opener)
    files = _object_list(payload, "files", url)
    # Keep the defensive filter so tests/custom openers and future server changes
    # cannot accidentally place source bodies or function metadata in the plan.
    return [
        {key: value for key, value in item.items() if key not in _EXCLUDED_FILE_FIELDS}
        for item in files
    ]


def list_deployments(
    script_id: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    return _paged_resources(
        f"{API_ROOT}/{script_id}/deployments",
        access_token,
        "deployments",
        opener=opener,
    )


def list_versions(
    script_id: str,
    access_token: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[dict[str, Any]]:
    return _paged_resources(
        f"{API_ROOT}/{script_id}/versions",
        access_token,
        "versions",
        opener=opener,
    )
