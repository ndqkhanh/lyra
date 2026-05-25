"""Mutation testing for self-modification safety."""

from __future__ import annotations

import ast
import copy
import subprocess  # nosec
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import ClassVar

from .exceptions import MutationTestError


@dataclass(frozen=True)
class MutationConfig:
    """Configuration governing mutation testing."""

    mutation_rate: float = 0.1
    max_mutants: int = 50
    kill_timeout: float = 5.0


@dataclass(frozen=True)
class Mutant:
    """A single code mutation for testing."""

    mutant_id: str
    original_code: str
    mutated_code: str
    mutation_type: str
    location: tuple[int, int]


@dataclass(frozen=True)
class MutationTestResult:
    """Result of testing a single mutant."""

    mutant: Mutant
    killed: bool
    killed_by: str = ""
    test_output: str = ""
    score: float = 0.0


class _BoolOpMutator(ast.NodeTransformer):
    """Replace And with Or and vice versa."""

    def __init__(self, old_op: type[ast.And | ast.Or], new_op: type[ast.And | ast.Or]) -> None:
        self.mutated = False
        self._old = old_op
        self._new = new_op

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.BoolOp:
        if isinstance(node.op, self._old) and not self.mutated:
            node.op = self._new()
            self.mutated = True
        return self.generic_visit(node)  # type: ignore[return-value]


class _IfInverter(ast.NodeTransformer):
    """Swap body and orelse on If nodes with Compare tests."""

    def __init__(self) -> None:
        self.mutated = False

    def visit_If(self, node: ast.If) -> ast.If:
        if not self.mutated and isinstance(node.test, ast.Compare):
            node.body, node.orelse = node.orelse, node.body
            self.mutated = True
        return self.generic_visit(node)  # type: ignore[return-value]


class MutationTester:
    """Mutation testing for self-modification safety."""

    _MUTATION_OPS: ClassVar[dict[str, type]] = {
        "replace_and_with_or": ast.And,
        "replace_or_with_and": ast.Or,
        "invert_if": ast.If,
    }

    @staticmethod
    async def generate_mutants(
        source: str, config: MutationConfig = MutationConfig()
    ) -> tuple[Mutant, ...]:
        """Generate mutant variants of the given source code."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise MutationTestError(f"Cannot parse source: {e}") from e

        mutants: list[Mutant] = []

        # And -> Or mutation
        mt = _BoolOpMutator(ast.And, ast.Or)
        new_tree = mt.visit(copy.deepcopy(tree))
        ast.fix_missing_locations(new_tree)
        if mt.mutated:
            mutated = ast.unparse(new_tree)
            mutants.append(Mutant(
                mutant_id=str(uuid.uuid4()),
                original_code=source,
                mutated_code=mutated,
                mutation_type="replace_and_with_or",
                location=(0, 0),
            ))

        # Or -> And mutation
        mt2 = _BoolOpMutator(ast.Or, ast.And)
        new_tree2 = mt2.visit(copy.deepcopy(tree))
        ast.fix_missing_locations(new_tree2)
        if mt2.mutated:
            mutated = ast.unparse(new_tree2)
            mutants.append(Mutant(
                mutant_id=str(uuid.uuid4()),
                original_code=source,
                mutated_code=mutated,
                mutation_type="replace_or_with_and",
                location=(0, 0),
            ))

        # If body inversion
        mt3 = _IfInverter()
        new_tree3 = mt3.visit(copy.deepcopy(tree))
        ast.fix_missing_locations(new_tree3)
        if mt3.mutated:
            mutated = ast.unparse(new_tree3)
            mutants.append(Mutant(
                mutant_id=str(uuid.uuid4()),
                original_code=source,
                mutated_code=mutated,
                mutation_type="invert_if",
                location=(0, 0),
            ))

        return tuple(mutants[:config.max_mutants])

    @staticmethod
    async def test_mutant(
        mutant: Mutant, test_suite: str
    ) -> MutationTestResult:
        """Run the test suite against a single mutant."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write(mutant.mutated_code)
            mutant_file = f.name

        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    test_suite, "--tb=short", "-q",
                ],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            killed = result.returncode != 0
            output = result.stdout[:500] + result.stderr[:500]
            return MutationTestResult(
                mutant=mutant,
                killed=killed,
                killed_by=result.stderr[:200] if killed else "",
                test_output=output,
            )
        except subprocess.TimeoutExpired:
            return MutationTestResult(
                mutant=mutant,
                killed=True,
                killed_by="timeout",
                test_output="Test timed out",
            )
        except FileNotFoundError:
            raise MutationTestError("pytest not found in PATH")
        finally:
            import os as _os
            try:
                _os.unlink(mutant_file)
            except OSError:
                pass

    @staticmethod
    async def run_mutation_testing(
        source: str, test_suite: str
    ) -> tuple[MutationTestResult, ...]:
        """Run full mutation testing: generate mutants and test each."""
        mutants = await MutationTester.generate_mutants(source)
        results: list[MutationTestResult] = []
        for mutant in mutants:
            result = await MutationTester.test_mutant(mutant, test_suite)
            results.append(result)
        return tuple(results)

    @staticmethod
    def compute_mutation_score(
        results: tuple[MutationTestResult, ...]
    ) -> float:
        """Compute mutation score from test results."""
        if not results:
            return 0.0
        killed = sum(1 for r in results if r.killed)
        return round(killed / len(results), 4)
