from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


api = load_module("stage2_apps_script_api", "automation/stage-2-sync/apps_script_api.py")
clasp = load_module("stage2_clasp_client", "automation/stage-2-sync/clasp_client.py")


class Stage2IoTests(unittest.TestCase):
    def test_apps_script_project_request_preserves_url_and_authorization(self):
        seen = {}

        def opener(request):
            seen["url"] = request.full_url
            seen["authorization"] = request.get_header("Authorization")
            return io.StringIO(json.dumps({"scriptId": "script-1", "updateTime": "now"}))

        result = api.get_project("script-1", "token-1", opener=opener)
        self.assertEqual("script-1", result["scriptId"])
        self.assertEqual("https://script.googleapis.com/v1/projects/script-1", seen["url"])
        self.assertEqual("Bearer token-1", seen["authorization"])

    def test_apps_script_content_strips_source_fields_only(self):
        def opener(_request):
            return io.StringIO(json.dumps({"files": [{
                "name": "Code",
                "type": "SERVER_JS",
                "source": "secret source",
                "functionSet": {"values": []},
                "updateTime": "now",
            }]}))

        self.assertEqual(
            [{"name": "Code", "type": "SERVER_JS", "updateTime": "now"}],
            api.get_project_files_metadata("script-1", "token", opener=opener),
        )

    def test_apps_script_failure_returns_none(self):
        def opener(_request):
            raise OSError("offline")

        self.assertIsNone(api.get_project("script-1", "token", opener=opener))
        self.assertIsNone(api.get_project_files_metadata("script-1", "token", opener=opener))

    def test_clasp_access_token_legacy_shapes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".clasprc.json"
            cases = [
                ({"token": {"access_token": "nested"}}, "nested"),
                ({"access_token": "root"}, "root"),
                ({"tokens": {"default": {"access_token": "multi"}}}, "multi"),
            ]
            for payload, expected in cases:
                path.write_text(json.dumps(payload), encoding="utf-8")
                self.assertEqual(expected, clasp.read_access_token(path))

    def test_clasp_retry_refreshes_token_and_waits(self):
        calls = []
        sleeps = []
        failed = False

        def runner(command, **kwargs):
            nonlocal failed
            calls.append(command)
            if command == "clasp pull" and not failed:
                failed = True
                raise subprocess.CalledProcessError(1, command)
            return SimpleNamespace(stdout="", stderr="", returncode=0)

        result = clasp.run_with_retry(
            "clasp pull",
            cwd="project",
            runner=runner,
            sleeper=sleeps.append,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual(["clasp pull", "clasp list", "clasp pull"], calls)
        self.assertEqual([2], sleeps)

    def test_clasp_parsers_preserve_legacy_shapes(self):
        self.assertEqual(
            [{"id": "dep-1", "target": "HEAD", "description": "production"}],
            clasp.parse_deployments("2 Deployments.\n- dep-1 @HEAD - production\n"),
        )
        self.assertEqual(
            [{"version": 7, "description": "release"}],
            clasp.parse_versions("2 Versions.\n7 - release\n"),
        )

    def test_clasp_list_helpers_capture_cli_output(self):
        commands = []

        def runner(command, **_kwargs):
            commands.append(command)
            if command == "clasp deployments":
                return SimpleNamespace(stdout="Deployments.\n- dep-1 @HEAD - prod\n")
            return SimpleNamespace(stdout="Versions.\n3 - stable\n")

        self.assertEqual(
            [{"id": "dep-1", "target": "HEAD", "description": "prod"}],
            clasp.list_deployments("project", runner=runner, sleeper=lambda _seconds: None),
        )
        self.assertEqual(
            [{"version": 3, "description": "stable"}],
            clasp.list_versions("project", runner=runner, sleeper=lambda _seconds: None),
        )
        self.assertEqual(["clasp deployments", "clasp versions"], commands)


if __name__ == "__main__":
    unittest.main()
