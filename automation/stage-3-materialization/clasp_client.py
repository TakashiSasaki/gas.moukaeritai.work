"""Minimal clasp adapter for Stage 3 source materialization.

Steady-state Stage 3 uses clasp only for ``clasp pull``. Token refresh is owned
by clasp itself; this adapter never invokes ``clasp list`` or metadata commands.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Callable

CLASP_PULL = ("clasp", "pull")
DEFAULT_ATTEMPTS = 2
DEFAULT_RETRY_DELAY_SECONDS = 2


class ClaspPullError(RuntimeError):
    """Raised after clasp pull exhausts its retry budget."""


def pull(
    project_dir: Path | str,
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    runner: Callable[..., Any] = subprocess.run,
    sleeper: Callable[[float], Any] = time.sleep,
) -> None:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    directory = Path(project_dir)
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, attempts + 1):
        try:
            runner(
                list(CLASP_PULL),
                cwd=directory,
                check=True,
                text=True,
                capture_output=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt < attempts:
                sleeper(retry_delay_seconds)
    assert last_error is not None
    stderr = (last_error.stderr or "").strip() if isinstance(last_error.stderr, str) else ""
    detail = f": {stderr[:1000]}" if stderr else ""
    raise ClaspPullError(
        f"clasp pull failed after {attempts} attempt(s) with exit code {last_error.returncode}{detail}"
    ) from last_error
