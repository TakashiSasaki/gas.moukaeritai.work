from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def build_clasp_command() -> list[str]:
    for candidate in ("clasp", "clasp.cmd", "clasp.exe"):
        command_path = shutil.which(candidate)
        if command_path:
            return [command_path, "list", "--noShorten"]

    for candidate in ("npx", "npx.cmd", "npx.exe"):
        command_path = shutil.which(candidate)
        if command_path:
            return [command_path, "@google/clasp", "list", "--noShorten"]

    raise FileNotFoundError("Could not find clasp or npx in PATH.")


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = SCRIPT_DIR / f"{timestamp}.txt"

    try:
        command = build_clasp_command()
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 1

    if result.returncode != 0:
        if result.stdout:
            sys.stderr.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        return result.returncode

    output_path.write_text(result.stdout, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
