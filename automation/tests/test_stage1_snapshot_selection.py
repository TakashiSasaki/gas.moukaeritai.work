from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_reconciler() -> ModuleType:
    path = REPO_ROOT / "automation" / "stage-1-inventory" / "reconcile-project-registry.py"
    spec = importlib.util.spec_from_file_location("stage1_snapshot_reconcile", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reconciler = load_reconciler()


class Stage1SnapshotSelectionTests(unittest.TestCase):
    def test_latest_snapshot_ignores_legacy_seed_even_when_it_sorts_later(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "data" / "inventory" / "drive-api" / "snapshots"
            directory.mkdir(parents=True)
            timestamped = directory / "20261231-235959.json"
            timestamped.write_text('{"files": []}', encoding="utf-8")
            (directory / "20261231.json").write_text('{"files": []}', encoding="utf-8")
            (directory / "2-not-a-snapshot.json").write_text('{"files": []}', encoding="utf-8")

            self.assertEqual(timestamped, reconciler.latest_snapshot(root))

    def test_latest_snapshot_requires_timestamped_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "data" / "inventory" / "drive-api" / "snapshots"
            directory.mkdir(parents=True)
            (directory / "20261231.json").write_text('{"files": []}', encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                reconciler.latest_snapshot(root)


if __name__ == "__main__":
    unittest.main()
