# File: extract_clasp_script_ids.py
# Description: Extracts scriptId from .clasp.json in subdirectories and prints the result as JSON

import os
import json
import sys

from project_paths import iter_project_dirs

def main():
    result = {}
    base_dir = os.getcwd()

    for subdir_path in iter_project_dirs(base_dir):
        entry = os.path.basename(subdir_path)
        clasp_path = os.path.join(subdir_path, '.clasp.json')

        try:
            with open(clasp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                script_id = data.get('scriptId')
                if script_id:
                    result[entry] = script_id
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to read {clasp_path}: {e}", file=sys.stderr)

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
