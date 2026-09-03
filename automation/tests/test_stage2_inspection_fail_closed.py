from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module():
    path = REPO_ROOT / "automation" / "stage-2-inspection" / "apps_script_api.py"
    spec = importlib.util.spec_from_file_location("stage2_inspection_fail_closed_api", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


api = load_module()


class Opener:
    def __init__(self, payload):
        self.payload = payload

    def __call__(self, _request):
        return io.StringIO(json.dumps(self.payload))


class Stage2InspectionFailClosedTests(unittest.TestCase):
    def test_deployment_non_object_entry_is_rejected(self):
        with self.assertRaisesRegex(api.AppsScriptApiError, "non-object resource"):
            api.list_deployments(
                "script",
                "token",
                opener=Opener({"deployments": [{"deploymentId": "valid"}, "malformed"]}),
            )

    def test_version_non_object_entry_is_rejected(self):
        with self.assertRaisesRegex(api.AppsScriptApiError, "non-object resource"):
            api.list_versions(
                "script",
                "token",
                opener=Opener({"versions": [{"versionNumber": 1}, None]}),
            )

    def test_content_non_object_entry_is_rejected(self):
        with self.assertRaisesRegex(api.AppsScriptApiError, "non-object resource"):
            api.get_project_files_metadata(
                "script",
                "token",
                opener=Opener({"files": [{"name": "Code"}, 7]}),
            )


if __name__ == "__main__":
    unittest.main()
