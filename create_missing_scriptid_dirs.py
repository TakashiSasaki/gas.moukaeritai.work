# File: create_missing_scriptid_dirs.py
# Description: Extracts scriptIds and their labels from a text file, creates missing scriptId-named directories,
#              and shows progress including human-readable project labels. Supports dry-run mode.

import os
import re
import argparse
import json
import sys

def extract_script_ids_with_labels(file_path):
    """
    Returns a dict: {scriptId: label}
    """
    result = {}
    url_pattern = re.compile(r"^(.*?)\s*-\s*https://script\.google\.com/d/([a-zA-Z0-9_-]+)(?:/edit)?")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = url_pattern.search(line.strip())
            if match:
                label = match.group(1).strip()
                script_id = match.group(2)
                result[script_id] = label
    return result

def extract_existing_script_ids(base_dir):
    """
    Returns a set of scriptIds found in .clasp.json files under subdirectories.
    """
    existing_ids = set()
    for entry in os.listdir(base_dir):
        subdir = os.path.join(base_dir, entry)
        clasp_path = os.path.join(subdir, '.clasp.json')
        if os.path.isdir(subdir) and os.path.isfile(clasp_path):
            try:
                with open(clasp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sid = data.get('scriptId')
                    if sid:
                        existing_ids.add(sid)
            except Exception as e:
                print(f"Warning: Failed to parse {clasp_path}: {e}", file=sys.stderr)
    return existing_ids

def create_missing_dirs(missing_id_to_label, dry_run=False):
    total = len(missing_id_to_label)
    created = []

    for i, (script_id, label) in enumerate(sorted(missing_id_to_label.items()), 1):
        print(f"[{i}/{total}] Creating dir for scriptId: {script_id}  # {label}", end='')
        if dry_run:
            print(" (dry-run)")
        else:
            try:
                os.makedirs(script_id, exist_ok=True)
                print(" (done)")
                created.append(script_id)
            except Exception as e:
                print(f" (error: {e})")
    return created

def main():
    parser = argparse.ArgumentParser(description="Create missing scriptId-named directories based on clasp.json content.")
    parser.add_argument('input_file', help='Text file containing script URLs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without creating anything')
    args = parser.parse_args()

    base_dir = os.getcwd()

    print("Scanning input and existing directories...\n")

    id_to_label = extract_script_ids_with_labels(args.input_file)
    target_ids = set(id_to_label.keys())
    existing_ids = extract_existing_script_ids(base_dir)

    missing_ids = target_ids - existing_ids
    missing_id_to_label = {sid: id_to_label[sid] for sid in missing_ids}

    print(f"Found {len(target_ids)} scriptId(s) in file.")
    print(f"Found {len(existing_ids)} scriptId(s) in existing .clasp.json files.")
    print(f"{len(missing_ids)} scriptId(s) are missing:\n")

    for sid, label in missing_id_to_label.items():
        print(f"  - {sid}  # {label}")

    print()
    created = create_missing_dirs(missing_id_to_label, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\nDry-run complete: {len(created)} directory(ies) would be created.")
    else:
        print(f"\nDone: {len(created)} new directory(ies) created.")

if __name__ == '__main__':
    main()
