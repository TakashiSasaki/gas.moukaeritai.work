#!/usr/bin/env python3
"""
clasp-pull.py

Iterate over all immediate subdirectories of the current working directory.
For each subdirectory containing a .clasp.json file, change into that directory
and execute `clasp pull` via the shell to sync local files with the remote Apps Script project.
"""
import os
import subprocess
import sys


def main():
    base_dir = os.getcwd()
    entries = os.listdir(base_dir)

    for entry in entries:
        project_dir = os.path.join(base_dir, entry)
        clasp_config = os.path.join(project_dir, '.clasp.json')

        # Only consider immediate subdirectories with a .clasp.json file
        if os.path.isdir(project_dir) and os.path.isfile(clasp_config):
            print(f"Pulling project in '{entry}' via shell...")
            try:
                # Change to the project directory
                os.chdir(project_dir)
                # Run clasp pull via shell
                subprocess.run('clasp pull', shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error: `clasp pull` failed in {entry}: {e}", file=sys.stderr)
            finally:
                # Change back to the base directory
                os.chdir(base_dir)

    print("All projects processed.")


if __name__ == '__main__':
    main()
