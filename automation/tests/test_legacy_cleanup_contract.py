from __future__ import annotations

import ast
import shlex
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOMATION = REPO_ROOT / "automation"
LEGACY_STAGE2 = AUTOMATION / "stage-2-sync"
LEGACY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "stage-2-sync.yml"
STAGE2 = AUTOMATION / "stage-2-inspection"
STAGE3 = AUTOMATION / "stage-3-materialization"
STAGE3_CLASP = STAGE3 / "clasp_client.py"
STEADY_STATE_ROOTS = (
    AUTOMATION / "stage-1-inventory",
    STAGE2,
    STAGE3,
    AUTOMATION / "shared",
)


def parse_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(parse_tree(path)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def literal_sequence(node: ast.AST) -> tuple[str, ...] | None:
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values: list[str] = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        values.append(item.value)
    return tuple(values)


def command_from_node(node: ast.AST) -> tuple[str, ...] | None:
    sequence = literal_sequence(node)
    if sequence and sequence[0] == "clasp":
        return sequence
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.strip()
        if value.startswith("clasp "):
            try:
                parts = tuple(shlex.split(value))
            except ValueError:
                return None
            return parts if parts and parts[0] == "clasp" else None
    return None


def executable_clasp_commands(path: Path) -> set[tuple[str, ...]]:
    commands: set[tuple[str, ...]] = set()
    tree = parse_tree(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is not None:
                command = command_from_node(value)
                if command:
                    commands.add(command)
        elif isinstance(node, ast.Call) and node.args:
            command = command_from_node(node.args[0])
            if command:
                commands.add(command)
    return commands


def implementation_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "tests" not in path.parts)


class LegacyCleanupContractTests(unittest.TestCase):
    def test_retired_stage2_implementation_and_workflow_are_absent(self):
        self.assertFalse(LEGACY_STAGE2.exists())
        self.assertFalse(LEGACY_WORKFLOW.exists())

    def test_stage2_inspection_tree_has_no_subprocess_dependency(self):
        for path in implementation_files(STAGE2):
            self.assertNotIn(
                "subprocess",
                imported_roots(path),
                msg=f"Stage 2 must remain direct-API-only: {path.relative_to(REPO_ROOT)}",
            )

    def test_only_stage3_clasp_adapter_may_import_subprocess(self):
        offenders: list[str] = []
        for root in STEADY_STATE_ROOTS:
            for path in implementation_files(root):
                if "subprocess" in imported_roots(path) and path != STAGE3_CLASP:
                    offenders.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual([], offenders)

    def test_every_steady_state_clasp_command_is_pull(self):
        found: list[tuple[str, tuple[str, ...]]] = []
        for root in STEADY_STATE_ROOTS:
            for path in implementation_files(root):
                for command in sorted(executable_clasp_commands(path)):
                    found.append((str(path.relative_to(REPO_ROOT)), command))
        self.assertEqual(
            [("automation/stage-3-materialization/clasp_client.py", ("clasp", "pull"))],
            found,
        )

    def test_stage3_clasp_adapter_public_function_surface_is_pull_only(self):
        tree = parse_tree(STAGE3_CLASP)
        public_functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        }
        self.assertEqual({"pull"}, public_functions)

    def test_human_output_metadata_parser_symbols_are_absent(self):
        offenders: list[tuple[str, str]] = []
        for root in STEADY_STATE_ROOTS:
            for path in implementation_files(root):
                for node in ast.walk(parse_tree(path)):
                    if not isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    ):
                        continue
                    normalized = node.name.lower()
                    if "parse" in normalized and (
                        "deploy" in normalized or "version" in normalized
                    ):
                        offenders.append((str(path.relative_to(REPO_ROOT)), node.name))
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
