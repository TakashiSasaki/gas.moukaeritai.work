from __future__ import annotations

import importlib.util
import json
import os
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
    "stage3_codex_safety_test",
    "automation/stage-3-materialization/materialize.py",
)


class FakeClasp:
    def __init__(self, action=None):
        self.action = action
        self.calls: list[Path] = []

    def pull(self, project_dir: Path):
        directory = Path(project_dir)
        self.calls.append(directory)
        if self.action:
            return self.action(directory)
        return None


def make_project(root: Path, script_id: str, *, lifecycle="present", checkpoint="old") -> Path:
    project = root / "projects" / script_id
    project.mkdir(parents=True)
    (project / ".clasp.json").write_text(json.dumps({"scriptId": script_id}), encoding="utf-8")
    (project / "metadata.json").write_text(
        json.dumps({
            "lifecycle": {"driveInventory": lifecycle},
            "syncState": {"lastMaterializedAppsScriptUpdateTime": checkpoint},
        }),
        encoding="utf-8",
    )
    return project


def remote(update_time="new"):
    return {
        "appsScriptApi": {"scriptId": "script-1", "updateTime": update_time},
        "files": [{"name": "Code", "type": "SERVER_JS"}],
        "deployments": [],
        "versions": [],
    }


def item(script_id="script-1", *, lifecycle="present", required=True, checkpoint="old"):
    return {
        "scriptId": script_id,
        "path": f"projects/{script_id}",
        "lifecycle": lifecycle,
        "observation": None if lifecycle == "absent" else remote(),
        "materialization": {
            "required": required,
            "reason": "test",
            "checkpointAppsScriptUpdateTime": checkpoint,
            "observedAppsScriptUpdateTime": None if lifecycle == "absent" else "new",
        },
    }


def plan(*projects):
    return {
        "schemaVersion": 1,
        "materializationRequired": any(p["materialization"]["required"] for p in projects),
        "projects": list(projects),
    }


class Stage3CodexSafetyTests(unittest.TestCase):
    def test_symlinked_canonical_project_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "projects").mkdir()
            target = root / "outside-project"
            target.mkdir()
            (target / ".clasp.json").write_text(json.dumps({"scriptId": "script-1"}), encoding="utf-8")
            (target / "metadata.json").write_text(
                json.dumps({
                    "lifecycle": {"driveInventory": "present"},
                    "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
                }),
                encoding="utf-8",
            )
            (root / "projects" / "script-1").symlink_to(target, target_is_directory=True)
            clasp = FakeClasp()
            with self.assertRaisesRegex(stage3.MaterializationPlanError, "must not be a symlink"):
                stage3.materialize_plan(plan(item()), root, clasp=clasp)
            self.assertEqual([], clasp.calls)

    def test_lifecycle_change_rejects_stale_plan_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_project(root, "script-1", lifecycle="absent")
            clasp = FakeClasp()
            with self.assertRaisesRegex(stage3.MaterializationPlanError, "stale Stage 2 plan lifecycle"):
                stage3.materialize_plan(plan(item(lifecycle="present")), root, clasp=clasp)
            self.assertEqual([], clasp.calls)

    def test_rollback_preserves_internal_and_dangling_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = make_project(root, "script-1")
            (project / "target.txt").write_text("target", encoding="utf-8")
            (project / "linked.txt").symlink_to("target.txt")
            (project / "dangling.txt").symlink_to("missing.txt")

            def fail_validation(directory: Path):
                # Do not materialize Code.js, forcing post-pull validation failure.
                (directory / "temporary.txt").write_text("partial", encoding="utf-8")

            result = stage3.materialize_plan(plan(item()), root, clasp=FakeClasp(fail_validation))
            self.assertFalse(result["allProjectsSuccessful"])
            linked = project / "linked.txt"
            dangling = project / "dangling.txt"
            self.assertTrue(linked.is_symlink())
            self.assertEqual("target.txt", os.readlink(linked))
            self.assertTrue(dangling.is_symlink())
            self.assertEqual("missing.txt", os.readlink(dangling))
            self.assertFalse((project / "temporary.txt").exists())


if __name__ == "__main__":
    unittest.main()
