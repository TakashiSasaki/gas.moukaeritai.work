from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reconcile_module = load_script(
    "phase2_test_reconcile",
    "automation/stage-1-inventory/reconcile-project-registry.py",
)
index_module = load_script(
    "phase2_test_index",
    "automation/stage-1-inventory/generate-public-project-index.py",
)
detect_module = load_script(
    "phase2_test_detect",
    "automation/stage-2-sync/detect-project-changes.py",
)
refresh_module = load_script(
    "phase2_test_refresh",
    "automation/stage-2-sync/refresh-project-metadata.py",
)
validator_module = load_script(
    "phase2_test_validator",
    "automation/stage-2-sync/validate-project-state.py",
)


def write_project(root: Path, script_id: str, metadata: dict) -> Path:
    directory = root / "projects" / script_id
    directory.mkdir(parents=True)
    (directory / ".clasp.json").write_text(
        json.dumps({"scriptId": script_id}), encoding="utf-8"
    )
    (directory / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    return directory


def write_snapshot(root: Path, files: list[dict], name: str = "20260903-000000.json") -> Path:
    directory = root / "data" / "inventory" / "drive-api" / "snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps({"files": files}), encoding="utf-8")
    return path


class FakeClaspForDetection:
    def check_version(self):
        return None

    def refresh_token(self):
        return None

    def read_access_token(self):
        return "token"


class FakeApiForDetection:
    def __init__(self):
        self.calls: list[str] = []

    def get_project(self, script_id, access_token):
        self.calls.append(script_id)
        return {"scriptId": script_id, "updateTime": "2026-09-03T01:00:00Z"}


class FakeClaspForRefresh:
    def read_access_token(self):
        return None

    def list_deployments(self, project_dir):
        return []

    def list_versions(self, project_dir):
        return []


class Phase2LifecycleContractTests(unittest.TestCase):
    def test_disappeared_project_is_marked_absent_without_source_deletion_and_can_reappear(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(
                root,
                "script-a",
                {"driveApi": {"id": "script-a", "name": "Alpha"}},
            )
            source = project / "Code.js"
            source.write_text("function alpha() {}\n", encoding="utf-8")

            empty_snapshot = write_snapshot(root, [])
            reconcile_module.reconcile(empty_snapshot, root)
            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["lifecycle"]["driveInventory"], "absent")
            self.assertTrue(source.exists())

            present_snapshot = write_snapshot(
                root,
                [{"id": "script-a", "name": "Alpha", "modifiedTime": "2026-09-03T02:00:00Z"}],
                "20260903-010000.json",
            )
            reconcile_module.reconcile(present_snapshot, root)
            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["lifecycle"]["driveInventory"], "present")
            self.assertTrue(source.exists())

    def test_public_index_excludes_absent_projects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(
                root,
                "active",
                {"driveApi": {"id": "active", "name": "Active"}, "lifecycle": {"driveInventory": "present"}},
            )
            write_project(
                root,
                "absent",
                {"driveApi": {"id": "absent", "name": "Absent"}, "lifecycle": {"driveInventory": "absent"}},
            )
            self.assertEqual(index_module.build_index(root), [{"id": "active", "name": "Active"}])

    def test_absent_project_is_not_inspected_or_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_project(
                root,
                "active",
                {
                    "lifecycle": {"driveInventory": "present"},
                    "syncState": {"lastMaterializedAppsScriptUpdateTime": "2026-09-03T00:00:00Z"},
                },
            )
            write_project(
                root,
                "absent",
                {
                    "lifecycle": {"driveInventory": "absent"},
                    "syncState": {"lastMaterializedAppsScriptUpdateTime": "2026-09-03T00:00:00Z"},
                },
            )
            api = FakeApiForDetection()
            plan = detect_module.build_plan(root, clasp=FakeClaspForDetection(), api=api)
            by_id = {item["scriptId"]: item for item in plan["projects"]}
            self.assertEqual(api.calls, ["active"])
            self.assertTrue(by_id["active"]["shouldSync"])
            self.assertFalse(by_id["absent"]["shouldSync"])
            self.assertIsNone(by_id["absent"]["remoteMetadata"])

    def test_failed_pull_does_not_advance_checkpoint_but_success_does(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(
                root,
                "script-a",
                {
                    "lifecycle": {"driveInventory": "present"},
                    "syncState": {"lastMaterializedAppsScriptUpdateTime": "2026-09-03T00:00:00Z"},
                },
            )
            plan = {
                "projects": [
                    {
                        "scriptId": "script-a",
                        "remoteUpdateTime": "2026-09-03T02:00:00Z",
                        "remoteMetadata": {
                            "scriptId": "script-a",
                            "updateTime": "2026-09-03T02:00:00Z",
                        },
                    }
                ]
            }
            clasp = FakeClaspForRefresh()

            refresh_module.refresh_metadata(
                plan,
                {"projects": [{"scriptId": "script-a", "synced": False}]},
                root,
                clasp=clasp,
            )
            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["syncState"]["lastMaterializedAppsScriptUpdateTime"],
                "2026-09-03T00:00:00Z",
            )

            refresh_module.refresh_metadata(
                plan,
                {"projects": [{"scriptId": "script-a", "synced": True}]},
                root,
                clasp=clasp,
            )
            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                metadata["syncState"]["lastMaterializedAppsScriptUpdateTime"],
                "2026-09-03T02:00:00Z",
            )

    def test_state_validator_rejects_unknown_drive_lifecycle(self):
        with self.assertRaises(validator_module.ProjectStateError):
            validator_module.validate_state_contract(
                {"lifecycle": {"driveInventory": "unknown"}}, "script-a"
            )


if __name__ == "__main__":
    unittest.main()
