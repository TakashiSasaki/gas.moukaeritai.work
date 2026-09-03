from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.shared.project_registry import load_metadata, write_metadata


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
    "stage3_materialization_test",
    "automation/stage-3-materialization/materialize.py",
)
clasp_client = load_module(
    "stage3_clasp_client_test",
    "automation/stage-3-materialization/clasp_client.py",
)


class FakeClasp:
    def __init__(self, action=None):
        self.action = action
        self.calls: list[Path] = []

    def pull(self, project_dir: Path):
        directory = Path(project_dir)
        self.calls.append(directory)
        if self.action is not None:
            return self.action(directory)
        return ""


def write_project(
    root: Path,
    script_id: str,
    metadata: dict,
    *,
    root_dir: str = ".",
) -> Path:
    project = root / "projects" / script_id
    project.mkdir(parents=True)
    clasp = {"scriptId": script_id}
    if root_dir != ".":
        clasp["rootDir"] = root_dir
    (project / ".clasp.json").write_text(json.dumps(clasp), encoding="utf-8")
    (project / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    source_root = project / root_dir
    source_root.mkdir(parents=True, exist_ok=True)
    return project


def observation(update_time="new", files=None):
    project = {"scriptId": "remote"}
    if update_time is not None:
        project["updateTime"] = update_time
    return {
        "appsScriptApi": project,
        "files": list(files if files is not None else [{"name": "Code", "type": "SERVER_JS"}]),
        "deployments": [{"deploymentId": "d1"}],
        "versions": [{"versionNumber": 2}],
    }


def plan_item(
    script_id: str,
    *,
    required: bool,
    checkpoint="old",
    observed="new",
    lifecycle="present",
    remote=None,
):
    return {
        "scriptId": script_id,
        "path": f"projects/{script_id}",
        "lifecycle": lifecycle,
        "observation": remote,
        "materialization": {
            "required": required,
            "reason": "test",
            "checkpointAppsScriptUpdateTime": checkpoint,
            "observedAppsScriptUpdateTime": observed,
        },
    }


def plan(*items):
    return {
        "schemaVersion": 1,
        "materializationRequired": any(item["materialization"]["required"] for item in items),
        "projects": list(items),
    }


class Stage3MaterializationTests(unittest.TestCase):
    def test_successful_pull_finalizes_checkpoint_and_removes_only_tracked_stale_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "script-1", {
                "driveApi": {"name": "keep"},
                "lifecycle": {"driveInventory": "present"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
                "appsScriptApi": {"updateTime": "old"},
                "files": [{"name": "Old", "type": "SERVER_JS"}],
                "custom": {"preserve": True},
            })
            (project / "Old.js").write_text("old source", encoding="utf-8")
            (project / "LocalOnly.js").write_text("local", encoding="utf-8")

            def pull(directory: Path):
                (directory / "Code.js").write_text("new source", encoding="utf-8")

            remote = observation("new")
            result = stage3.materialize_plan(
                plan(plan_item("script-1", required=True, remote=remote)),
                root,
                clasp=FakeClasp(pull),
            )
            item = result["projects"][0]
            self.assertTrue(item["attempted"])
            self.assertTrue(item["materialized"])
            self.assertTrue(item["finalized"])
            self.assertTrue(item["successful"])
            self.assertTrue(result["allProjectsSuccessful"])
            self.assertTrue((project / "Code.js").exists())
            self.assertFalse((project / "Old.js").exists())
            self.assertTrue((project / "LocalOnly.js").exists())

            metadata = load_metadata(project)
            self.assertEqual({"name": "keep"}, metadata["driveApi"])
            self.assertEqual({"preserve": True}, metadata["custom"])
            self.assertEqual("new", metadata["appsScriptApi"]["updateTime"])
            self.assertEqual(
                "new",
                metadata["syncState"]["lastMaterializedAppsScriptUpdateTime"],
            )
            self.assertEqual([{"deploymentId": "d1"}], metadata["deployments"])
            self.assertEqual([{"versionNumber": 2}], metadata["versions"])

    def test_pull_failure_rolls_back_source_metadata_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {
                "lifecycle": {"driveInventory": "present"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
                "files": [{"name": "Old", "type": "SERVER_JS"}],
            }
            project = write_project(root, "script-1", original)
            (project / "Old.js").write_text("old", encoding="utf-8")

            def fail(directory: Path):
                (directory / "Code.js").write_text("partial", encoding="utf-8")
                raise subprocess.CalledProcessError(1, ["npx", "clasp", "pull"])

            result = stage3.materialize_plan(
                plan(plan_item("script-1", required=True, remote=observation("new"))),
                root,
                clasp=FakeClasp(fail),
            )
            self.assertFalse(result["allProjectsSuccessful"])
            self.assertFalse(result["projects"][0]["materialized"])
            self.assertTrue((project / "Old.js").exists())
            self.assertFalse((project / "Code.js").exists())
            self.assertEqual(original, load_metadata(project))

    def test_post_pull_validation_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {
                "lifecycle": {"driveInventory": "present"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            }
            project = write_project(root, "script-1", original)
            (project / "sentinel.txt").write_text("before", encoding="utf-8")

            result = stage3.materialize_plan(
                plan(plan_item("script-1", required=True, remote=observation("new"))),
                root,
                clasp=FakeClasp(lambda directory: None),
            )
            self.assertFalse(result["allProjectsSuccessful"])
            self.assertEqual("before", (project / "sentinel.txt").read_text(encoding="utf-8"))
            self.assertEqual(original, load_metadata(project))

    def test_metadata_failure_after_write_rolls_back_entire_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {
                "lifecycle": {"driveInventory": "present"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            }
            project = write_project(root, "script-1", original)

            def pull(directory: Path):
                (directory / "Code.js").write_text("new", encoding="utf-8")

            def write_then_fail(directory, metadata):
                write_metadata(directory, metadata)
                raise RuntimeError("simulated finalize failure")

            result = stage3.materialize_plan(
                plan(plan_item("script-1", required=True, remote=observation("new"))),
                root,
                clasp=FakeClasp(pull),
                metadata_writer=write_then_fail,
            )
            self.assertFalse(result["allProjectsSuccessful"])
            self.assertFalse((project / "Code.js").exists())
            self.assertEqual(original, load_metadata(project))

    def test_unchanged_project_refreshes_observation_without_clasp_or_checkpoint_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "script-1", {
                "lifecycle": {"driveInventory": "present"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "same"},
                "appsScriptApi": {"updateTime": "same", "title": "old"},
                "driveApi": {"name": "preserve"},
            })
            clasp = FakeClasp(lambda directory: self.fail("clasp must not run"))
            remote = observation("same", files=[])
            remote["appsScriptApi"]["title"] = "fresh"
            result = stage3.materialize_plan(
                plan(plan_item(
                    "script-1",
                    required=False,
                    checkpoint="same",
                    observed="same",
                    remote=remote,
                )),
                root,
                clasp=clasp,
            )
            self.assertEqual([], clasp.calls)
            self.assertTrue(result["projects"][0]["finalized"])
            self.assertTrue(result["projects"][0]["successful"])
            metadata = load_metadata(project)
            self.assertEqual("same", metadata["syncState"]["lastMaterializedAppsScriptUpdateTime"])
            self.assertEqual("fresh", metadata["appsScriptApi"]["title"])
            self.assertEqual({"name": "preserve"}, metadata["driveApi"])

    def test_legacy_checkpoint_is_made_explicit_before_no_pull_observation_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "script-1", {
                "lifecycle": {"driveInventory": "present"},
                "appsScriptApi": {"updateTime": "same", "title": "legacy"},
            })
            remote = observation("same", files=[])
            result = stage3.materialize_plan(
                plan(plan_item(
                    "script-1",
                    required=False,
                    checkpoint="same",
                    observed="same",
                    remote=remote,
                )),
                root,
                clasp=FakeClasp(),
            )
            self.assertTrue(result["allProjectsSuccessful"])
            self.assertEqual(
                "same",
                load_metadata(project)["syncState"]["lastMaterializedAppsScriptUpdateTime"],
            )

    def test_absent_project_is_untouched_and_never_calls_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {
                "lifecycle": {"driveInventory": "absent"},
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            }
            project = write_project(root, "script-1", original)
            clasp = FakeClasp(lambda directory: self.fail("clasp must not run"))
            result = stage3.materialize_plan(
                plan(plan_item(
                    "script-1",
                    required=False,
                    checkpoint="old",
                    observed=None,
                    lifecycle="absent",
                    remote=None,
                )),
                root,
                clasp=clasp,
            )
            self.assertEqual([], clasp.calls)
            self.assertTrue(result["projects"][0]["successful"])
            self.assertFalse(result["projects"][0]["finalized"])
            self.assertEqual(original, load_metadata(project))

    def test_stale_checkpoint_rejects_entire_plan_before_any_pull(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(root, "a", {
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            })
            write_project(root, "b", {
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "current"},
            })
            clasp = FakeClasp(lambda directory: self.fail("preflight must finish before pulls"))
            with self.assertRaisesRegex(stage3.MaterializationPlanError, "stale Stage 2 plan checkpoint"):
                stage3.materialize_plan(
                    plan(
                        plan_item("a", required=True, checkpoint="old", remote=observation("new")),
                        plan_item("b", required=True, checkpoint="stale", remote=observation("new")),
                    ),
                    root,
                    clasp=clasp,
                )
            self.assertEqual([], clasp.calls)

    def test_success_without_correlated_remote_timestamp_keeps_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, "script-1", {
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            })

            def pull(directory: Path):
                (directory / "Code.js").write_text("source", encoding="utf-8")

            result = stage3.materialize_plan(
                plan(plan_item(
                    "script-1",
                    required=True,
                    checkpoint="old",
                    observed=None,
                    remote=observation(None),
                )),
                root,
                clasp=FakeClasp(pull),
            )
            self.assertTrue(result["allProjectsSuccessful"])
            self.assertEqual(
                "old",
                load_metadata(project)["syncState"]["lastMaterializedAppsScriptUpdateTime"],
            )

    def test_unsafe_remote_filename_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(root, "script-1", {
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            })
            clasp = FakeClasp()
            remote = observation("new", files=[{"name": "../escape", "type": "SERVER_JS"}])
            with self.assertRaisesRegex(stage3.MaterializationPlanError, "unsafe Stage 2 file observation"):
                stage3.materialize_plan(
                    plan(plan_item("script-1", required=True, remote=remote)),
                    root,
                    clasp=clasp,
                )
            self.assertEqual([], clasp.calls)

    def test_root_dir_escape_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(
                root,
                "script-1",
                {"syncState": {"lastMaterializedAppsScriptUpdateTime": "old"}},
                root_dir="../outside",
            )
            clasp = FakeClasp()
            with self.assertRaisesRegex(stage3.MaterializationPlanError, "rootDir escapes"):
                stage3.materialize_plan(
                    plan(plan_item("script-1", required=True, remote=observation("new"))),
                    root,
                    clasp=clasp,
                )
            self.assertEqual([], clasp.calls)

    def test_safe_root_dir_is_honored(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(
                root,
                "script-1",
                {"syncState": {"lastMaterializedAppsScriptUpdateTime": "old"}},
                root_dir="src",
            )

            def pull(directory: Path):
                (directory / "src" / "Code.js").write_text("source", encoding="utf-8")

            result = stage3.materialize_plan(
                plan(plan_item("script-1", required=True, remote=observation("new"))),
                root,
                clasp=FakeClasp(pull),
            )
            self.assertTrue(result["allProjectsSuccessful"])
            self.assertTrue((project / "src" / "Code.js").exists())

    def test_observed_timestamp_mismatch_is_rejected_before_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(root, "script-1", {
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "old"},
            })
            clasp = FakeClasp()
            with self.assertRaisesRegex(stage3.MaterializationPlanError, "does not match"):
                stage3.materialize_plan(
                    plan(plan_item(
                        "script-1",
                        required=True,
                        observed="planned",
                        remote=observation("remote"),
                    )),
                    root,
                    clasp=clasp,
                )
            self.assertEqual([], clasp.calls)

    def test_no_pull_metadata_failure_is_a_workflow_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = {
                "syncState": {"lastMaterializedAppsScriptUpdateTime": "same"},
            }
            project = write_project(root, "script-1", original)

            def fail_writer(directory, metadata):
                raise RuntimeError("write failed")

            result = stage3.materialize_plan(
                plan(plan_item(
                    "script-1",
                    required=False,
                    checkpoint="same",
                    observed="same",
                    remote=observation("same", files=[]),
                )),
                root,
                clasp=FakeClasp(),
                metadata_writer=fail_writer,
            )
            self.assertFalse(result["allProjectsSuccessful"])
            self.assertFalse(result["projects"][0]["successful"])
            self.assertEqual(original, load_metadata(project))

    def test_clasp_retry_uses_only_pull_and_never_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            calls = []

            def runner(args, **kwargs):
                calls.append(list(args))
                if len(calls) == 1:
                    raise subprocess.CalledProcessError(1, args)
                return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

            self.assertEqual("ok", clasp_client.pull(project, runner=runner, retries=1))
            self.assertEqual(
                [["npx", "clasp", "pull"], ["npx", "clasp", "pull"]],
                calls,
            )
            self.assertTrue(all("list" not in call for call in calls))


if __name__ == "__main__":
    unittest.main()
