from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STAGE1 = REPO_ROOT / ".github" / "workflows" / "stage-1-inventory.yml"
STAGE23 = REPO_ROOT / ".github" / "workflows" / "stage-2-3-sync.yml"


class WorkflowContractTests(unittest.TestCase):
    def test_stage2_runs_after_stage1_only_on_success(self):
        workflow = STAGE23.read_text(encoding="utf-8")
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)

    def test_stage1_stages_snapshot_retention_deletions(self):
        workflow = STAGE1.read_text(encoding="utf-8")
        self.assertIn("git add -A data/inventory/drive-api/snapshots", workflow)
        self.assertNotIn("git add data/inventory/drive-api/snapshots/*.json", workflow)

    def test_stage2_clasp_install_is_version_pinned(self):
        workflow = STAGE23.read_text(encoding="utf-8")
        self.assertIn("npm install -g @google/clasp@3.4.1", workflow)
        self.assertNotIn("npm install -g @google/clasp\n", workflow)


if __name__ == "__main__":
    unittest.main()
