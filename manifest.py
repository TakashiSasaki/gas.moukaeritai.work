import json
import os
from typing import Any, Dict

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None

def main():
    with open('gas-project-finder.json', 'r', encoding='utf-8') as f:
        finder_list = json.load(f)
    finder_map: Dict[str, Dict[str, Any]] = {
        entry['id']: entry for entry in finder_list if 'id' in entry
    }

    for root, dirs, files in os.walk('.'):
        if '.clasp.json' in files:
            clasp_path = os.path.join(root, '.clasp.json')
            clasp_data = load_json(clasp_path) or {}
            script_id = clasp_data.get('scriptId')

            metadata: Dict[str, Any] = {}
            if script_id and script_id in finder_map:
                metadata.update(finder_map[script_id])
            if script_id and 'id' not in metadata:
                metadata['id'] = script_id

            metadata['application.json'] = load_json(os.path.join(root, 'application.json'))
            metadata['deployments.json'] = load_json(os.path.join(root, 'deployments.json'))

            with open(os.path.join(root, 'metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
