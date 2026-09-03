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
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage3 = load_module(
    "stage3_final_codex_safety_test",
    "automation/stage-3-materialization/materialize.py",
)


class FakeClasp:
    def __init__(self):
        self.calls: list[Path] = []

    def pull(self, project_dir: Path):
        self.calls.append(Path(project_dir))
        raise AssertionError("clasp must not run when Stage 3 preflight rejects the plan")


def make_project(root: Path, script_id: str = "script-1") -> Path:
    project = root / "projects" / script_id
    project.mkdir(parents=True)
    (project / ".clasp.json").write_text(
        json.dumps({"scriptId": script_id}), encoding="utf-8"
    )
    (project / "metadata.json").write_text(
        json.dumps(
            {
                "lifecycle": {"driveInventory": "present"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            }
        ),
        encoding="utf-8",
    )
    return project


def materialization_plan(*, observed_script_id: str = "script-1") -> dict:
    return {
        "schemaVersion": 1,
        "materializationRequired": True,
        "projects": [
            {
                "scriptId": "script-1",
                "path": "projects/script-1",
                "lifecycle": "present",
                "observation": {
                    "appsScriptApi": {
                        "scriptId": observed_script_id,
                        "updateTime": "new",
                    },
                    "files": [{"name": "Code", "type": "SERVER_JS"}],
                    "deployments": [],
                    "versions": [],
                },
                "materialization": {
                    "required": True,
                    "reason": "test",
                    "checkpointAppsScriptUpdateTime": "old",
                    "observedAppsScriptUpdateTime": "new",
                },
            }
        ],
    }


class Stage3FinalCodexSafetyTests(unittest.TestCase):
    def test_local_windows_case_alias_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = make_project(root)
            local_alias = project / "code.js"
            local_alias.write_text("local-only", encoding="utf-8")
            clasp = FakeClasp()

            with self.assertRaisesRegex(
                stage3.MaterializationPlanError, "Windows case alias"
            ):
                stage3.materialize_plan(materialization_plan(), root, clasp=clasp)

            self.assertEqual([], clasp.calls)
            self.assertEqual("local-only", local_alias.read_text(encoding="utf-8"))
            self.assertFalse((project / "Code.js").exists())

    def test_cross_wired_apps_script_observation_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_project(root)
            clasp = FakeClasp()

            with self.assertRaisesRegex(
                stage3.MaterializationPlanError,
                "observation Apps Script project belongs to 'script-2'",
            ):
                stage3.materialize_plan(
                    materialization_plan(observed_script_id="script-2"),
                    root,
                    clasp=clasp,
                )

            self.assertEqual([], clasp.calls)


if __name__ == "__main__":
    unittest.main()
