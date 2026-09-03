from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_module(name: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


detect = load_module("phase2_change_detect", "automation/stage-2-sync/detect-project-changes.py")


class Clasp:
    def check_version(self):
        return True

    def refresh_token(self):
        return True

    def read_access_token(self):
        return "token"


class Api:
    def __init__(self, update_time: str):
        self.update_time = update_time

    def get_project(self, script_id, access_token):
        return {"scriptId": script_id, "updateTime": self.update_time}


def write_project(root: Path, checkpoint: str) -> None:
    project = root / "projects" / "script-a"
    project.mkdir(parents=True)
    (project / ".clasp.json").write_text(json.dumps({"scriptId": "script-a"}), encoding="utf-8")
    (project / "metadata.json").write_text(
        json.dumps({
            "lifecycle": {"driveInventory": "present"},
            "syncState": {"lastMaterializedAppsScriptUpdateTime": checkpoint},
        }),
        encoding="utf-8",
    )


class ChangeDetectionTests(unittest.TestCase):
    def test_only_exact_checkpoint_match_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = "2026-09-03T00:00:00Z"
            write_project(root, checkpoint)

            equal = detect.build_plan(root, clasp=Clasp(), api=Api(checkpoint))
            self.assertFalse(equal["projects"][0]["shouldSync"])

            # A different value remains synchronization-worthy even if lexical
            # ordering would call it older, or RFC3339 precision differs.
            older = detect.build_plan(root, clasp=Clasp(), api=Api("2026-09-02T23:59:59Z"))
            self.assertTrue(older["projects"][0]["shouldSync"])
            fractional = detect.build_plan(root, clasp=Clasp(), api=Api("2026-09-03T00:00:00.100Z"))
            self.assertTrue(fractional["projects"][0]["shouldSync"])


if __name__ == "__main__":
    unittest.main()
