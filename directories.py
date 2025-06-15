# File: extract_clasp_script_ids.py
# Description: Extracts scriptId from .clasp.json in subdirectories and prints the result as JSON

import os
import json
import sys

def main():
    result = {}
    base_dir = os.getcwd()

    for entry in os.listdir(base_dir):
        subdir_path = os.path.join(base_dir, entry)
        clasp_path = os.path.join(subdir_path, '.clasp.json')

        if os.path.isdir(subdir_path) and os.path.isfile(clasp_path):
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
