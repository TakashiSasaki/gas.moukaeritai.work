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


def load_module(name: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


detect = load_module("stage2_detect_test", "automation/stage-2-sync/detect-project-changes.py")
sync = load_module("stage2_sync_test", "automation/stage-2-sync/sync-project-source.py")
refresh = load_module("stage2_refresh_test", "automation/stage-2-sync/refresh-project-metadata.py")
validate = load_module("stage2_validate_test", "automation/stage-2-sync/validate-project-state.py")


def create_project(root: Path, script_id: str, metadata: dict | None = None) -> Path:
    project = root / "projects" / script_id
    project.mkdir(parents=True)
    (project / ".clasp.json").write_text(
        json.dumps({"scriptId": script_id}),
        encoding="utf-8",
    )
    (project / "metadata.json").write_text(
        json.dumps(metadata or {}),
        encoding="utf-8",
    )
    return project


class DetectClasp:
    def __init__(self, token: str | None):
        self.token = token
        self.version_checks = 0
        self.refreshes = 0

    def check_version(self):
        self.version_checks += 1
        return True

    def refresh_token(self):
        self.refreshes += 1
        return True

    def read_access_token(self):
        return self.token


class DetectApi:
    def __init__(self, remote: dict[str, dict | None]):
        self.remote = remote
        self.calls: list[str] = []

    def get_project(self, script_id: str, access_token: str):
        self.calls.append(script_id)
        return self.remote.get(script_id)


class SyncClasp:
    def __init__(self, failing: set[str] | None = None):
        self.failing = failing or set()
        self.pulled: list[str] = []

    def pull(self, project_dir: Path):
        script_id = project_dir.name
        self.pulled.append(script_id)
        if script_id in self.failing:
            raise subprocess.CalledProcessError(1, "clasp pull")

    def list_deployments(self, project_dir: Path):
        return [{"id": f"dep-{project_dir.name}", "target": "HEAD", "description": ""}]

    def list_versions(self, project_dir: Path):
        return [{"version": 1, "description": project_dir.name}]


class RefreshClasp:
    def __init__(self, token: str | None = "token"):
        self.token = token

    def read_access_token(self):
        return self.token


class RefreshApi:
    def __init__(self, files: list[dict] | None = None, project: dict | None = None):
        self.files = files
        self.project = project
        self.project_calls = 0

    def get_project(self, script_id: str, access_token: str):
        self.project_calls += 1
        return self.project

    def get_project_files_metadata(self, script_id: str, access_token: str):
        return self.files


class Stage2PipelineTests(unittest.TestCase):
    def test_detection_uses_only_canonical_registry_and_preserves_decisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_project(root, "a", {"appsScriptApi": {"updateTime": "2026-01-02T00:00:00Z"}})
            create_project(root, "b", {"appsScriptApi": {"updateTime": "2026-01-01T00:00:00Z"}})
            create_project(root, "c", {})

            # The legacy implementation also scanned root children. The new canonical
            # registry must deliberately ignore this non-authoritative project shape.
            legacy = root / "legacy-project"
            legacy.mkdir()
            (legacy / ".clasp.json").write_text(json.dumps({"scriptId": "legacy"}), encoding="utf-8")

            clasp = DetectClasp("token")
            api = DetectApi({
                "a": {"updateTime": "2026-01-02T00:00:00Z", "title": "A"},
                "b": {"updateTime": "2026-01-03T00:00:00Z", "title": "B"},
                "c": None,
            })
            plan = detect.build_plan(root, clasp=clasp, api=api)
            self.assertEqual(["a", "b", "c"], [item["scriptId"] for item in plan["projects"]])
            self.assertEqual([False, True, True], [item["shouldSync"] for item in plan["projects"]])
            self.assertEqual(["a", "b", "c"], api.calls)
            self.assertEqual(1, clasp.version_checks)
            self.assertEqual(1, clasp.refreshes)

    def test_detection_without_access_token_selects_all_without_api_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            create_project(root, "a", {"appsScriptApi": {"updateTime": "2026-01-02T00:00:00Z"}})
            clasp = DetectClasp(None)
            api = DetectApi({"a": {"updateTime": "2026-01-01T00:00:00Z"}})
            plan = detect.build_plan(root, clasp=clasp, api=api)
            self.assertTrue(plan["projects"][0]["shouldSync"])
            self.assertFalse(plan["accessTokenAvailable"])
            self.assertEqual([], api.calls)

    def test_sync_processes_only_selected_projects_and_continues_after_clasp_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for script_id in ("a", "b", "c"):
                create_project(root, script_id)
            plan = {
                "projects": [
                    {"scriptId": "a", "shouldSync": False},
                    {"scriptId": "b", "shouldSync": True},
                    {"scriptId": "c", "shouldSync": True},
                ]
            }
            clasp = SyncClasp({"c"})
            result = sync.sync_plan(plan, root, clasp=clasp)
            by_id = {item["scriptId"]: item for item in result["projects"]}
            self.assertFalse(by_id["a"]["attempted"])
            self.assertTrue(by_id["b"]["synced"])
            self.assertEqual("dep-b", by_id["b"]["deployments"][0]["id"])
            self.assertTrue(by_id["c"]["attempted"])
            self.assertFalse(by_id["c"]["synced"])
            self.assertIn("exit code 1", by_id["c"]["error"])
            self.assertEqual(["b", "c"], clasp.pulled)

    def test_refresh_merges_namespaces_and_cleans_only_legacy_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = create_project(
                root,
                "a",
                {
                    "driveApi": {"id": "a", "name": "Drive name"},
                    "custom": {"keep": True},
                    "lastUpdated": "legacy",
                    "deployments.json": [{"legacy": True}],
                },
            )
            for filename in ("deployments.json", "deployments.txt", "versions.json", "versions.txt"):
                (project / filename).write_text("legacy", encoding="utf-8")

            remote = {"scriptId": "a", "title": "Remote", "updateTime": "2026-01-03T00:00:00Z"}
            plan = {"projects": [{"scriptId": "a", "shouldSync": True, "remoteMetadata": remote}]}
            result = {
                "projects": [{
                    "scriptId": "a",
                    "attempted": True,
                    "synced": True,
                    "deployments": [{"id": "dep", "target": "HEAD", "description": ""}],
                    "versions": [{"version": 1, "description": "v1"}],
                    "error": None,
                }]
            }
            api = RefreshApi(files=[{"name": "Code", "type": "SERVER_JS"}])
            count = refresh.refresh_metadata(plan, result, root, clasp=RefreshClasp(), api=api)
            self.assertEqual(1, count)
            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual({"id": "a", "name": "Drive name"}, metadata["driveApi"])
            self.assertEqual({"keep": True}, metadata["custom"])
            self.assertEqual(remote, metadata["appsScriptApi"])
            self.assertEqual("dep", metadata["deployments"][0]["id"])
            self.assertEqual(1, metadata["versions"][0]["version"])
            self.assertEqual("Code", metadata["files"][0]["name"])
            self.assertNotIn("lastUpdated", metadata)
            self.assertNotIn("deployments.json", metadata)
            self.assertEqual(0, api.project_calls)
            for filename in ("deployments.json", "deployments.txt", "versions.json", "versions.txt"):
                self.assertFalse((project / filename).exists())

    def test_refresh_collision_fails_before_metadata_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = create_project(root, "a", {"driveApi": {"id": "a"}, "custom": "unchanged"})
            before = (project / "metadata.json").read_bytes()
            plan = {"projects": [{"scriptId": "a", "shouldSync": True, "remoteMetadata": {"updateTime": "new"}}]}
            result = {
                "projects": [{
                    "scriptId": "a",
                    "attempted": True,
                    "synced": True,
                    "deployments": [],
                    "versions": [],
                    "error": None,
                }]
            }
            api = RefreshApi(files=[{"name": "Code"}, {"name": "code"}])
            with self.assertRaises(refresh.validator.CaseInsensitiveNameConflict):
                refresh.refresh_metadata(plan, result, root, clasp=RefreshClasp(), api=api)
            self.assertEqual(before, (project / "metadata.json").read_bytes())

    def test_validator_detects_case_insensitive_conflicts(self):
        self.assertEqual([], validate.find_case_insensitive_name_conflicts([{"name": "Code"}, {"name": "Html"}]))
        self.assertEqual(
            [("Code", "code")],
            validate.find_case_insensitive_name_conflicts([{"name": "Code"}, {"name": "code"}]),
        )
        with self.assertRaises(validate.CaseInsensitiveNameConflict):
            validate.validate_files([{"name": "Code"}, {"name": "code"}], "script")


if __name__ == "__main__":
    unittest.main()
