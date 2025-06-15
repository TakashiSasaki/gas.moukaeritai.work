#!/usr/bin/env python3
"""
create_missing_scriptid_dirs.py

This script reads a text file containing lines with a human-readable project name fragment
followed by a Google Apps Script URL. It extracts the ScriptID from each URL, checks whether
there is a corresponding subdirectory whose .clasp.json contains that ScriptID, and for any
missing ones, creates the directory and initializes a .clasp.json file inside it.

Features:
- Progress display
- Dry-run mode (no changes written)
"""

import os
import re
import json
import argparse
import sys


def parse_input_file(input_path):
    """
    Parse the input file to extract (script_id, human_name) tuples.
    Each line should contain a human-readable name fragment before the URL,
    and a URL containing '/d/<SCRIPTID>/' from which the ScriptID is extracted.
    """
    entries = []
    pattern = re.compile(r"/d/([a-zA-Z0-9_-]+)/")

    with open(input_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            human_name = parts[0]
            url = parts[-1]
            match = pattern.search(url)
            if not match:
                print(f"Warning: could not extract ScriptID from URL '{url}'", file=sys.stderr)
                continue
            script_id = match.group(1)
            entries.append((script_id, human_name))
    return entries


def load_existing_scriptids(base_path=os.getcwd()):
    """
    Scan each subdirectory under base_path, load .clasp.json if present,
    and collect the ScriptIDs found.
    """
    existing = set()
    for entry in os.listdir(base_path):
        dir_path = os.path.join(base_path, entry)
        if not os.path.isdir(dir_path):
            continue
        config_path = os.path.join(dir_path, '.clasp.json')
        if os.path.isfile(config_path):
            try:
                data = json.load(open(config_path, encoding='utf-8'))
                sid = data.get('scriptId')
                if sid:
                    existing.add(sid)
            except json.JSONDecodeError:
                print(f"Warning: invalid JSON in {config_path}", file=sys.stderr)
    return existing


def main():
    parser = argparse.ArgumentParser(
        description='Create missing ScriptID directories and .clasp.json files.'
    )
    parser.add_argument(
        'input_file', help='Path to the text file with ScriptID URLs.'
    )
    parser.add_argument(
        '--dry-run', action='store_true', help='Show what would be done without making changes.'
    )
    args = parser.parse_args()

    entries = parse_input_file(args.input_file)
    total = len(entries)
    if total == 0:
        print("No valid entries found in the input file.")
        return

    existing_ids = load_existing_scriptids()

    missing = [ (sid, name) for sid, name in entries if sid not in existing_ids ]
    count = len(missing)
    print(f"{count} scriptId(s) are missing.")

    for idx, (script_id, human_name) in enumerate(missing, start=1):
        print(f"[{idx}/{count}] Missing: {script_id} ({human_name})")
        dir_name = script_id
        if args.dry_run:
            continue
        # Create the directory
        os.makedirs(dir_name, exist_ok=True)
        # Create .clasp.json
        config = {"scriptId": script_id}
        config_path = os.path.join(dir_name, '.clasp.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    if args.dry_run:
        print("Dry-run mode: no directories or files were created.")
    else:
        print("Completed creating missing directories and .clasp.json files.")


if __name__ == '__main__':
    main()
