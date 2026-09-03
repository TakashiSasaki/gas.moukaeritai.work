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


detect = load_module("phase2_checkpoint_detect", "automation/stage-2-sync/detect-project-changes.py")
refresh = load_module("phase2_checkpoint_refresh", "automation/stage-2-sync/refresh-project-metadata.py")


def write_project(root: Path, metadata: dict) -> Path:
    project = root / "projects" / "script-a"
    project.mkdir(parents=True)
    (project / ".clasp.json").write_text(json.dumps({"scriptId": "script-a"}), encoding="utf-8")
    (project / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return project


class RefreshClasp:
    def read_access_token(self):
        return "token"

    def list_deployments(self, _project_dir):
        return []

    def list_versions(self, _project_dir):
        return []


class PostPullApi:
    def get_project(self, _script_id, _access_token):
        return {"scriptId": "script-a", "updateTime": "2026-09-03T03:00:00Z"}

    def get_project_files_metadata(self, _script_id, _access_token):
        return [{"name": "Code", "type": "SERVER_JS"}]


class CheckpointCorrelationTests(unittest.TestCase):
    def test_post_pull_observation_never_advances_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(
                root,
                {"appsScriptApi": {"scriptId": "script-a", "updateTime": "2026-09-03T01:00:00Z"}},
            )
            plan = {
                "projects": [{
                    "scriptId": "script-a",
                    "shouldSync": True,
                    "remoteUpdateTime": None,
                    "remoteMetadata": None,
                }]
            }
            sync_result = {"projects": [{"scriptId": "script-a", "synced": True}]}

            refresh.refresh_metadata(
                plan,
                sync_result,
                root,
                clasp=RefreshClasp(),
                api=PostPullApi(),
            )

            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual("2026-09-03T03:00:00Z", metadata["appsScriptApi"]["updateTime"])
            self.assertEqual(
                "2026-09-03T01:00:00Z",
                metadata["syncState"]["lastMaterializedAppsScriptUpdateTime"],
            )

    def test_empty_explicit_sync_state_blocks_remote_observation_fallback(self):
        metadata = {
            "syncState": {},
            "appsScriptApi": {"updateTime": "2026-09-03T03:00:00Z"},
        }
        self.assertIsNone(detect._materialized_update_time(metadata))

    def test_pre_pull_plan_observation_is_the_only_advance_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root, {})
            plan = {
                "projects": [{
                    "scriptId": "script-a",
                    "shouldSync": True,
                    "remoteUpdateTime": "2026-09-03T02:00:00Z",
                    "remoteMetadata": {
                        "scriptId": "script-a",
                        "updateTime": "2026-09-03T02:00:00Z",
                    },
                }]
            }
            sync_result = {"projects": [{"scriptId": "script-a", "synced": True}]}

            refresh.refresh_metadata(
                plan,
                sync_result,
                root,
                clasp=RefreshClasp(),
                api=PostPullApi(),
            )

            metadata = json.loads((project / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "2026-09-03T02:00:00Z",
                metadata["syncState"]["lastMaterializedAppsScriptUpdateTime"],
            )
            self.assertEqual("2026-09-03T02:00:00Z", metadata["appsScriptApi"]["updateTime"])


if __name__ == "__main__":
    unittest.main()
