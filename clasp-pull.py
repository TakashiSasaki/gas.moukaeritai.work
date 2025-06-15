#!/usr/bin/env python3
"""
clasp-pull.py

Iterate over all immediate subdirectories of the current working directory.
For each subdirectory containing a .clasp.json file, change into that directory
and execute `clasp pull`, then fetch and save deployments in both TXT and JSON formats,
and versions in both TXT and JSON formats, all via shell invocations with UTF-8 decoding.
"""
import os
import subprocess
import sys
import json
import re


def parse_deployments(raw_text):
    """
    Parse the output of `clasp deployments` into a list of dicts:
    [{"id": ..., "target": ..., "description": ...}, ...]
    """
    lines = raw_text.strip().splitlines()
    deployments = []
    for line in lines[1:]:  # skip header
        m = re.match(r"^-\s+(\S+)\s+@(\S+)(?:\s+-\s+(.*))?", line)
        if m:
            dep_id, target, desc = m.group(1), m.group(2), m.group(3) or ""
            deployments.append({
                "id": dep_id,
                "target": target,
                "description": desc
            })
    return deployments


def parse_versions(raw_text):
    """
    Parse the output of `clasp versions` into a list of dicts:
    [{"version": ..., "description": ...}, ...]
    """
    lines = raw_text.strip().splitlines()
    versions = []
    for line in lines[1:]:  # skip header
        m = re.match(r"^(\d+)\s*-\s*(.*)$", line)
        if m:
            ver_num, desc = m.group(1), m.group(2) or ""
            versions.append({
                "version": int(ver_num),
                "description": desc
            })
    return versions


def main():
    base_dir = os.getcwd()
    entries = os.listdir(base_dir)

    for entry in entries:
        project_dir = os.path.join(base_dir, entry)
        clasp_config = os.path.join(project_dir, '.clasp.json')

        if os.path.isdir(project_dir) and os.path.isfile(clasp_config):
            print(f"Processing project '{entry}'...")
            try:
                os.chdir(project_dir)

                # 1) Pull latest files via shell
                print("  Running `clasp pull` via shell...")
                subprocess.run('clasp pull', shell=True, check=True)

                # 2) Fetch deployments via shell with UTF-8 decoding
                print("  Fetching deployments via shell...")
                proc_dep = subprocess.run(
                    'clasp deployments',
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace'
                )
                raw_dep = proc_dep.stdout
                # Save raw TXT
                with open('deployments.txt', 'w', encoding='utf-8') as f:
                    f.write(raw_dep)
                # Parse and save JSON
                deps = parse_deployments(raw_dep)
                with open('deployments.json', 'w', encoding='utf-8') as f:
                    json.dump(deps, f, ensure_ascii=False, indent=2)

                # 3) Fetch versions via shell with UTF-8 decoding
                print("  Fetching versions via shell...")
                proc_ver = subprocess.run(
                    'clasp versions',
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    encoding='utf-8',
                    errors='replace'
                )
                raw_ver = proc_ver.stdout
                # Save raw TXT
                with open('versions.txt', 'w', encoding='utf-8') as f:
                    f.write(raw_ver)
                # Parse and save JSON
                vers = parse_versions(raw_ver)
                with open('versions.json', 'w', encoding='utf-8') as f:
                    json.dump(vers, f, ensure_ascii=False, indent=2)

                print(f"  Completed project '{entry}'.")

            except subprocess.CalledProcessError as e:
                print(f"Error: command failed in {entry}: {e}", file=sys.stderr)
            finally:
                os.chdir(base_dir)

    print("All projects processed.")


if __name__ == '__main__':
    main()
