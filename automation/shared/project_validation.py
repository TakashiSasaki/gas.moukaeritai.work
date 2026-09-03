"""Validation primitives shared by remote inspection and materialized-state checks."""

from __future__ import annotations

from typing import Any


class CaseInsensitiveNameConflict(ValueError):
    """Raised when Apps Script file names collide on a Windows-style filesystem."""


def windows_case_insensitive_key(name: str) -> str:
    """Approximate Windows ordinal case comparison without full case folding.

    Windows compares through an uppercase-character mapping rather than Unicode
    full case folding. Keep mappings that expand to multiple code points
    unchanged so values such as ``Straße`` and ``STRASSE`` are not falsely
    classified as the same filename.
    """
    mapped: list[str] = []
    for character in name:
        uppercase = character.upper()
        mapped.append(uppercase if len(uppercase) == 1 else character)
    return "".join(mapped)


def find_case_insensitive_name_conflicts(
    files: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    conflicts: list[tuple[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if not isinstance(name, str):
            name = str(name)
        comparison_key = windows_case_insensitive_key(name)
        if comparison_key in seen:
            conflicts.append((seen[comparison_key], name))
        else:
            seen[comparison_key] = name
    return conflicts


def validate_files(files: list[dict[str, Any]], script_id: str) -> None:
    conflicts = find_case_insensitive_name_conflicts(files)
    if not conflicts:
        return
    details = "\n".join(
        f"  Conflict: '{first}' vs '{second}' (identical under Windows-style case comparison)"
        for first, second in conflicts
    )
    raise CaseInsensitiveNameConflict(
        f"ERROR: Case-insensitive filename conflict detected in project {script_id}.\n"
        f"{details}\n"
        "  On Windows these files map to the same path. Remove one of the conflicting "
        "files from the Apps Script project before pulling."
    )
