from __future__ import annotations

import argparse
import re
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


def cleanup_old_files(directory: Path, keep_count: int) -> None:
    """
    Remove old timestamped files (YYYYMMDD-HHMMSS.txt) in the directory,
    keeping only the most recent `keep_count` files.
    """
    if keep_count < 1:
        return

    # Match files like 20260414-131756.txt
    pattern = re.compile(r"^\d{8}-\d{6}\.txt$")

    backups = [
        f for f in directory.iterdir()
        if f.is_file() and pattern.match(f.name)
    ]

    # Sort by name (chronological due to format)
    backups.sort(key=lambda x: x.name)

    if len(backups) > keep_count:
        to_delete = backups[:-keep_count]
        for f in to_delete:
            try:
                f.unlink()
                print(f"Deleted old backup: {f.name}")
            except Exception as e:
                print(f"Warning: Failed to delete {f.name}: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Save raw output of 'clasp list --noShorten' to a file.")
    parser.add_argument(
        "-o", "--output",
        help="Target output path (file or directory). Defaults to a timestamped file in the script's directory."
    )
    parser.add_argument(
        "-k", "--keep",
        type=int,
        default=5,
        help="Number of recent timestamped backups to retain. Set to 0 to skip cleanup. (Default: 5)"
    )

    args = parser.parse_args()

    # Determine output path
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_filename = f"{timestamp}.txt"

    if not args.output:
        output_path = SCRIPT_DIR / default_filename
    else:
        target = Path(args.output)
        if target.is_dir():
            output_path = target / default_filename
        else:
            output_path = target

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    # Write output
    output_path.write_text(result.stdout, encoding="utf-8")
    print(f"Saved: {output_path}")

    # Cleanup old files in the destination directory
    if args.keep > 0:
        cleanup_old_files(output_path.parent, args.keep)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
