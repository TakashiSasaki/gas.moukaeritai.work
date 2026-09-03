from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime
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


fetcher = load_module(
    "stage1_fetch_drive_inventory",
    "automation/stage-1-inventory/fetch-drive-inventory.py",
)
reconciler = load_module(
    "stage1_reconcile_project_registry",
    "automation/stage-1-inventory/reconcile-project-registry.py",
)
generator = load_module(
    "stage1_generate_public_project_index",
    "automation/stage-1-inventory/generate-public-project-index.py",
)
migrator = load_module(
    "maintenance_migrate_legacy_project_metadata",
    "automation/maintenance/migrate-legacy-project-metadata.py",
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeDriveSession:
    def __init__(self):
        self.calls = []
        self.pages = [
            {"files": [{"id": "one"}], "nextPageToken": "page-2"},
            {"files": [{"id": "two"}]},
        ]

    def get(self, url, headers, params, timeout):
        self.calls.append(dict(params))
        return FakeResponse(self.pages[len(self.calls) - 1])


class Stage1InventoryTests(unittest.TestCase):
    def test_drive_inventory_paginates(self):
        session = FakeDriveSession()
        result = fetcher.fetch_inventory("token", session=session)
        self.assertEqual([{"id": "one"}, {"id": "two"}], result)
        self.assertNotIn("pageToken", session.calls[0])
        self.assertEqual("page-2", session.calls[1]["pageToken"])

    def test_snapshot_retention_preserves_legacy_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "20260406.json").write_text("[]\n", encoding="utf-8")
            for second in range(6):
                fetcher.write_snapshot(
                    [],
                    directory,
                    now=datetime(2026, 4, 14, 8, 7, 50 + second),
                )
            timestamped = sorted(
                path.name for path in directory.iterdir() if fetcher.SNAPSHOT_PATTERN.fullmatch(path.name)
            )
            self.assertEqual(5, len(timestamped))
            self.assertTrue((directory / "20260406.json").exists())

    def test_reconcile_only_updates_drive_api_and_creates_clasp(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "projects" / "script-1"
            project.mkdir(parents=True)
            (project / "metadata.json").write_text(
                json.dumps(
                    {
                        "appsScriptApi": {"updateTime": "old"},
                        "deployments.json": [{"legacy": True}],
                        "driveApi": {"id": "script-1", "name": "Old"},
                    }
                ),
                encoding="utf-8",
            )
            snapshot = root / "snapshot.json"
            snapshot.write_text(
                json.dumps([{"id": "script-1", "name": "New", "version": "2"}]),
                encoding="utf-8",
            )

            count = reconciler.reconcile(snapshot, root=root)

            self.assertEqual(1, count)
            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual("New", metadata["driveApi"]["name"])
            self.assertEqual({"updateTime": "old"}, metadata["appsScriptApi"])
            self.assertIn("deployments.json", metadata)
            self.assertNotIn("deployments", metadata)
            clasp = json.loads((project / ".clasp.json").read_text(encoding="utf-8"))
            self.assertEqual({"scriptId": "script-1", "rootDir": "."}, clasp)

    def test_public_index_uses_materialized_drive_metadata_and_sorts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for script_id, name in (("b", "Zulu"), ("a", "Alpha")):
                project = root / "projects" / script_id
                project.mkdir(parents=True)
                (project / "metadata.json").write_text(
                    json.dumps({"driveApi": {"id": script_id, "name": name}}),
                    encoding="utf-8",
                )
            ignored = root / "projects" / "ignored"
            ignored.mkdir(parents=True)
            (ignored / "metadata.json").write_text(json.dumps({"appsScriptApi": {}}), encoding="utf-8")

            entries = generator.build_index(root)
            self.assertEqual(
                [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Zulu"}],
                entries,
            )

    def test_legacy_migration_is_explicit_and_dry_run_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "projects" / "script-1"
            project.mkdir(parents=True)
            original = {
                "driveApi": {"id": "script-1"},
                "version": "7",
                "deployments.json": [{"deploymentId": "d1"}],
            }
            metadata_path = project / "metadata.json"
            metadata_path.write_text(json.dumps(original), encoding="utf-8")

            changed, notes = migrator.migrate_project(project, apply=False)
            self.assertTrue(changed)
            self.assertTrue(notes)
            self.assertEqual(original, json.loads(metadata_path.read_text(encoding="utf-8")))

            changed, _ = migrator.migrate_project(project, apply=True)
            self.assertTrue(changed)
            migrated = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual("7", migrated["driveApi"]["version"])
            self.assertEqual([{"deploymentId": "d1"}], migrated["deployments"])
            self.assertNotIn("version", migrated)
            self.assertNotIn("deployments.json", migrated)

    def test_legacy_migration_preserves_conflicting_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "projects" / "script-1"
            project.mkdir(parents=True)
            metadata_path = project / "metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "driveApi": {"id": "script-1"},
                        "deployments": [{"deploymentId": "canonical"}],
                        "deployments.json": [{"deploymentId": "legacy"}],
                    }
                ),
                encoding="utf-8",
            )

            changed, notes = migrator.migrate_project(project, apply=True)
            self.assertFalse(changed)
            self.assertTrue(any(note.startswith("conflict:") for note in notes))
            result = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIn("deployments.json", result)
            self.assertEqual([{"deploymentId": "canonical"}], result["deployments"])


if __name__ == "__main__":
    unittest.main()
