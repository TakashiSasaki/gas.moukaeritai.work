from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from automation.shared import project_registry


class ProjectRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "projects").mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_project(self, script_id: str, metadata: dict | None = None) -> Path:
        project_dir = self.root / "projects" / script_id
        project_dir.mkdir()
        (project_dir / ".clasp.json").write_text(
            json.dumps({"scriptId": script_id}), encoding="utf-8"
        )
        if metadata is not None:
            (project_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        return project_dir

    def test_projects_path_uses_canonical_directory(self) -> None:
        self.assertEqual(project_registry.projects_path(self.root), self.root / "projects")

    def test_iter_project_directories_is_sorted_and_ignores_files(self) -> None:
        self.create_project("b")
        self.create_project("a")
        (self.root / "projects" / "README.txt").write_text("not a project", encoding="utf-8")
        self.assertEqual(
            [path.name for path in project_registry.iter_project_directories(self.root)],
            ["a", "b"],
        )

    def test_project_path_rejects_path_traversal(self) -> None:
        for unsafe in ("", ".", "..", "../outside", "nested/id", "nested\\id"):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(project_registry.ProjectRegistryError):
                    project_registry.project_path(unsafe, self.root)

    def test_get_script_id_reads_clasp_configuration(self) -> None:
        project_dir = self.create_project("script-123")
        self.assertEqual(project_registry.get_script_id(project_dir), "script-123")

    def test_load_metadata_can_allow_missing_for_new_stage_1_project(self) -> None:
        project_dir = self.create_project("script-123")
        self.assertEqual(project_registry.load_metadata(project_dir, allow_missing=True), {})
        with self.assertRaises(project_registry.ProjectRegistryError):
            project_registry.load_metadata(project_dir)

    def test_write_metadata_round_trip_is_utf8_json_object(self) -> None:
        project_dir = self.create_project("script-123")
        metadata = {"driveApi": {"name": "日本語"}, "appsScriptApi": {"updateTime": "t"}}
        project_registry.write_metadata(project_dir, metadata)
        self.assertEqual(project_registry.load_metadata(project_dir), metadata)
        self.assertTrue((project_dir / "metadata.json").read_text(encoding="utf-8").endswith("\n"))

    def test_load_metadata_rejects_non_object_json(self) -> None:
        project_dir = self.create_project("script-123")
        (project_dir / "metadata.json").write_text("[]", encoding="utf-8")
        with self.assertRaises(project_registry.ProjectRegistryError):
            project_registry.load_metadata(project_dir)


if __name__ == "__main__":
    unittest.main()
