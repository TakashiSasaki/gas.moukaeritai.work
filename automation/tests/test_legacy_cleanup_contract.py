from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOMATION = REPO_ROOT / "automation"
LEGACY_STAGE2 = AUTOMATION / "stage-2-sync"
LEGACY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "stage-2-sync.yml"
STAGE2 = AUTOMATION / "stage-2-inspection"
STAGE3_CLASP = AUTOMATION / "stage-3-materialization" / "clasp_client.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


class LegacyCleanupContractTests(unittest.TestCase):
    def test_retired_stage2_implementation_and_workflow_are_absent(self):
        self.assertFalse(LEGACY_STAGE2.exists())
        self.assertFalse(LEGACY_WORKFLOW.exists())

    def test_human_readable_clasp_metadata_parsers_are_absent(self):
        forbidden = {"parse_deployments", "parse_versions"}
        found: list[tuple[str, str]] = []
        for path in sorted(AUTOMATION.rglob("*.py")):
            if "tests" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden:
                    found.append((str(path.relative_to(REPO_ROOT)), node.name))
        self.assertEqual([], found)

    def test_stage2_inspection_has_no_subprocess_dependency(self):
        for path in sorted(STAGE2.glob("*.py")):
            self.assertNotIn(
                "subprocess",
                imported_roots(path),
                msg=f"Stage 2 must remain direct-API-only: {path.relative_to(REPO_ROOT)}",
            )

    def test_stage3_clasp_adapter_exposes_pull_as_its_command(self):
        clasp = load_module("legacy_cleanup_stage3_clasp", STAGE3_CLASP)
        self.assertEqual(("clasp", "pull"), clasp.CLASP_PULL)
        self.assertFalse(hasattr(clasp, "parse_deployments"))
        self.assertFalse(hasattr(clasp, "parse_versions"))
        self.assertFalse(hasattr(clasp, "refresh_token"))


if __name__ == "__main__":
    unittest.main()
