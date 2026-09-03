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


def make_project(
    root: Path,
    script_id: str,
    *,
    lifecycle="present",
    checkpoint="old",
    files=None,
    root_dir=".",
) -> Path:
    project = root / "projects" / script_id
    project.mkdir(parents=True)
    clasp = {"scriptId": script_id}
    if root_dir != ".":
        clasp["rootDir"] = root_dir
    (project / ".clasp.json").write_text(json.dumps(clasp), encoding="utf-8")
    metadata = {
        "lifecycle": {"driveInventory": lifecycle},
        "syncState": {"lastMaterializedAppsScriptUpdateTime": checkpoint},
    }
    if files is not None:
        metadata["files"] = files
    (project / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return project


def remote(update_time="new", files=None):
    return {
        "appsScriptApi": {"scriptId": "script-1", "updateTime": update_time},
        "files": list(files if files is not None else [{"name": "Code", "type": "SERVER_JS"}]),
        "deployments": [],
        "versions": [],
    }


def item(
    script_id="script-1",
    *,
    lifecycle="present",
    required=True,
    checkpoint="old",
    observed="new",
    observation=None,
):
    if lifecycle == "absent":
        selected_observation = None
        selected_observed = None
    else:
        selected_observation = remote(observed) if observation is None else observation
        selected_observed = observed
    return {
        "scriptId": script_id,
        "path": f"projects/{script_id}",
        "lifecycle": lifecycle,
        "observation": selected_observation,
        "materialization": {
            "required": required,
            "reason": "test",
            "checkpointAppsScriptUpdateTime": checkpoint,
            "observedAppsScriptUpdateTime": selected_observed,
        },
    }


def plan(*projects):
    return {
        "schemaVersion": 1,
        "materializationRequired": any(
            p["materialization"]["required"] for p in projects
        ),
        "projects": list(projects),
    }


class Stage3CodexSafetyTests(unittest.TestCase):
    def test_symlinked_canonical_project_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "projects").mkdir()
            target = root / "outside-project"
            target.mkdir()
            (target / ".clasp.json").write_text(
                json.dumps({"scriptId": "script-1"}), encoding="utf-8"
            )
            (target / "metadata.json").write_text(
                json.dumps({
                    "lifecycle": {"driveInventory": "present"},
                    "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
                }),
                encoding="utf-8",
            )
            (root / "projects" / "script-1").symlink_to(
                target, target_is_directory=True
            )
            clasp = FakeClasp()
            with self.assertRaisesRegex(
                stage3.MaterializationPlanError, "must not be a symlink"
            ):
                stage3.materialize_plan(plan(item()), root, clasp=clasp)
            self.assertEqual([], clasp.calls)

    def test_lifecycle_change_rejects_stale_plan_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_project(root, "script-1", lifecycle="absent")
            clasp = FakeClasp()
            with self.assertRaisesRegex(
                stage3.MaterializationPlanError, "stale Stage 2 plan lifecycle"
            ):
                stage3.materialize_plan(
                    plan(item(lifecycle="present")), root, clasp=clasp
                )
            self.assertEqual([], clasp.calls)

    def test_rollback_preserves_internal_and_dangling_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = make_project(root, "script-1")
            (project / "target.txt").write_text("target", encoding="utf-8")
            (project / "linked.txt").symlink_to("target.txt")
            (project / "dangling.txt").symlink_to("missing.txt")

            def fail_validation(directory: Path):
                (directory / "temporary.txt").write_text("partial", encoding="utf-8")

            result = stage3.materialize_plan(
                plan(item()), root, clasp=FakeClasp(fail_validation)
            )
            self.assertFalse(result["allProjectsSuccessful"])
            linked = project / "linked.txt"
            dangling = project / "dangling.txt"
            self.assertTrue(linked.is_symlink())
            self.assertEqual("target.txt", os.readlink(linked))
            self.assertTrue(dangling.is_symlink())
            self.assertEqual("missing.txt", os.readlink(dangling))
            self.assertFalse((project / "temporary.txt").exists())

    def test_expected_source_symlink_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = make_project(root, "script-1")
            outside = root / "outside.js"
            outside.write_text("outside-before", encoding="utf-8")
            (project / "Code.js").symlink_to(outside)
            clasp = FakeClasp()

            with self.assertRaisesRegex(stage3.MaterializationPlanError, "symlink"):
                stage3.materialize_plan(plan(item()), root, clasp=clasp)

            self.assertEqual([], clasp.calls)
            self.assertEqual("outside-before", outside.read_text(encoding="utf-8"))
            self.assertTrue((project / "Code.js").is_symlink())

    def test_stale_source_symlink_cleanup_unlinks_leaf_not_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_files = [{"name": "Old", "type": "SERVER_JS"}]
            project = make_project(root, "script-1", files=old_files)
            target = project / "local-target.txt"
            target.write_text("preserve", encoding="utf-8")
            stale = project / "Old.js"
            stale.symlink_to("local-target.txt")

            def pull(directory: Path):
                (directory / "Code.js").write_text("new", encoding="utf-8")

            result = stage3.materialize_plan(
                plan(item()), root, clasp=FakeClasp(pull)
            )

            self.assertTrue(result["allProjectsSuccessful"])
            self.assertFalse(stale.exists())
            self.assertFalse(stale.is_symlink())
            self.assertEqual("preserve", target.read_text(encoding="utf-8"))
            self.assertTrue((project / "Code.js").is_file())

    def test_drive_qualified_root_dir_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_project(root, "script-1", root_dir="C:/outside")
            clasp = FakeClasp()

            with self.assertRaisesRegex(
                stage3.MaterializationPlanError, "drive-qualified"
            ):
                stage3.materialize_plan(plan(item()), root, clasp=clasp)

            self.assertEqual([], clasp.calls)

    def test_required_flag_must_match_checkpoint_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_project(root, "script-1")
            clasp = FakeClasp()
            inconsistent = item(required=False, checkpoint="old", observed="new")

            with self.assertRaisesRegex(stage3.MaterializationPlanError, "inconsistent"):
                stage3.materialize_plan(plan(inconsistent), root, clasp=clasp)

            self.assertEqual([], clasp.calls)

    def test_top_level_materialization_flag_must_match_projects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_project(root, "script-1")
            clasp = FakeClasp()
            payload = plan(item(required=True))
            payload["materializationRequired"] = False

            with self.assertRaisesRegex(
                stage3.MaterializationPlanError, "does not match its project decisions"
            ):
                stage3.materialize_plan(payload, root, clasp=clasp)

            self.assertEqual([], clasp.calls)


if __name__ == "__main__":
    unittest.main()
