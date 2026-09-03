#!/usr/bin/env python3
"""clasp subprocess and authentication-state I/O primitives for Stage 2."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


def read_access_token(path: Path | None = None) -> str | None:
    """Read an access token using every legacy `.clasprc.json` shape."""
    rc_path = path if path is not None else Path.home() / ".clasprc.json"
    if not rc_path.exists():
        return None
    try:
        content = rc_path.read_text(encoding="utf-8")
        if not content.strip():
            return None
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        token = data.get("token")
        if isinstance(token, dict) and token.get("access_token"):
            return str(token["access_token"])
        if data.get("access_token"):
            return str(data["access_token"])
        tokens = data.get("tokens")
        if isinstance(tokens, dict):
            for token_data in tokens.values():
                if isinstance(token_data, dict) and token_data.get("access_token"):
                    return str(token_data["access_token"])
    except Exception as exc:
        print(f"Error reading .clasprc.json: {exc}", file=sys.stderr)
    return None


def check_version(*, runner: Callable[..., Any] = subprocess.run) -> bool:
    """Probe `clasp -v`, retaining the legacy best-effort behavior."""
    try:
        runner("clasp -v", shell=True, check=True)
        return True
    except Exception:
        return False


def refresh_token(*, runner: Callable[..., Any] = subprocess.run) -> bool:
    """Run `clasp list` to prompt clasp to refresh its token state."""
    try:
        runner(
            "clasp list",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        print("Warning: `clasp list` failed. Token might be invalid.", file=sys.stderr)
        return False


def run_with_retry(
    command: str,
    *,
    cwd: str | Path | None = None,
    capture_output: bool = False,
    retries: int = 3,
    runner: Callable[..., Any] = subprocess.run,
    sleeper: Callable[[float], Any] = time.sleep,
) -> Any:
    """Run a clasp command with the legacy refresh-and-retry semantics."""
    if retries < 1:
        raise ValueError("retries must be at least 1")
    for attempt in range(1, retries + 1):
        print(f"  Running: {command} (Attempt {attempt}/{retries})")
        try:
            return runner(
                command,
                shell=True,
                cwd=str(cwd) if cwd is not None else None,
                check=True,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.CalledProcessError as exc:
            print(f"    Command failed with exit code {exc.returncode}.", file=sys.stderr)
            if capture_output:
                print(f"    Stdout: {exc.stdout}", file=sys.stderr)
                print(f"    Stderr: {exc.stderr}", file=sys.stderr)
            if attempt == retries:
                raise
            print("    Attempting to refresh token via `clasp list`...", file=sys.stderr)
            try:
                runner(
                    "clasp list",
                    shell=True,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
            sleeper(2)
    raise AssertionError("unreachable")


def pull(project_dir: str | Path, **kwargs: Any) -> Any:
    return run_with_retry("clasp pull", cwd=project_dir, **kwargs)


def parse_deployments(raw_text: str) -> list[dict[str, str]]:
    deployments: list[dict[str, str]] = []
    for line in raw_text.strip().splitlines()[1:]:
        match = re.match(r"^-\s+(\S+)\s+@(\S+)(?:\s+-\s+(.*))?", line)
        if match:
            deployment_id, target, description = match.group(1), match.group(2), match.group(3) or ""
            deployments.append({
                "id": deployment_id,
                "target": target,
                "description": description,
            })
    return deployments


def list_deployments(project_dir: str | Path, **kwargs: Any) -> list[dict[str, str]]:
    result = run_with_retry(
        "clasp deployments",
        cwd=project_dir,
        capture_output=True,
        **kwargs,
    )
    return parse_deployments(result.stdout)


def parse_versions(raw_text: str) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    for line in raw_text.strip().splitlines()[1:]:
        match = re.match(r"^(\d+)\s*-\s*(.*)$", line)
        if match:
            versions.append({
                "version": int(match.group(1)),
                "description": match.group(2) or "",
            })
    return versions


def list_versions(project_dir: str | Path, **kwargs: Any) -> list[dict[str, Any]]:
    result = run_with_retry(
        "clasp versions",
        cwd=project_dir,
        capture_output=True,
        **kwargs,
    )
    return parse_versions(result.stdout)
