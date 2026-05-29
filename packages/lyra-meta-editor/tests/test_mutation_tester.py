"""Tests for the mutation_tester module."""

from __future__ import annotations

import pytest
from lyra_meta_editor import (
    Mutant,
    MutationConfig,
    MutationTester,
    MutationTestError,
    MutationTestResult,
)


class TestMutationConfig:
    """Tests for MutationConfig."""

    def test_defaults(self) -> None:
        cfg = MutationConfig()
        assert cfg.mutation_rate == 0.1
        assert cfg.max_mutants == 50
        assert cfg.kill_timeout == 5.0


class TestMutant:
    """Tests for Mutant."""

    def test_creation(self) -> None:
        m = Mutant(
            mutant_id="id1",
            original_code="x = 1",
            mutated_code="x = 2",
            mutation_type="replace_constant",
            location=(1, 0),
        )
        assert m.mutant_id == "id1"
        assert m.mutation_type == "replace_constant"
        assert m.location == (1, 0)

    def test_immutable(self) -> None:
        m = Mutant("id", "orig", "mut", "type", (1, 0))
        with pytest.raises(AttributeError):
            m.mutant_id = "new"  # type: ignore[misc]


class TestMutationTestResult:
    """Tests for MutationTestResult."""

    def test_killed(self) -> None:
        mutant = Mutant("id", "o", "m", "t", (0, 0))
        result = MutationTestResult(mutant=mutant, killed=True, killed_by="test failed")
        assert result.killed is True
        assert result.killed_by == "test failed"


class TestMutationTester:
    """Tests for MutationTester."""

    @pytest.mark.asyncio
    async def test_generate_mutants_and_to_or(self) -> None:
        source = "x = a and b\n"
        mutants = await MutationTester.generate_mutants(source)
        types = [m.mutation_type for m in mutants]
        assert "replace_and_with_or" in types

    @pytest.mark.asyncio
    async def test_generate_mutants_or_to_and(self) -> None:
        source = "x = a or b\n"
        mutants = await MutationTester.generate_mutants(source)
        types = [m.mutation_type for m in mutants]
        assert "replace_or_with_and" in types

    @pytest.mark.asyncio
    async def test_generate_mutants_invert_if(self) -> None:
        source = "if a > b:\n    pass\n"
        mutants = await MutationTester.generate_mutants(source)
        types = [m.mutation_type for m in mutants]
        assert "invert_if" in types

    @pytest.mark.asyncio
    async def test_generate_mutants_no_operators(self) -> None:
        source = "x = 1\ny = 2\n"
        mutants = await MutationTester.generate_mutants(source)
        assert len(mutants) == 0

    @pytest.mark.asyncio
    async def test_generate_mutants_syntax_error(self) -> None:
        with pytest.raises(MutationTestError, match="parse"):
            await MutationTester.generate_mutants("if x:\n")

    @pytest.mark.asyncio
    async def test_generate_mutants_max_mutants(self) -> None:
        source = "x = a and b\n"
        config = MutationConfig(max_mutants=0)
        mutants = await MutationTester.generate_mutants(source, config)
        assert len(mutants) == 0

    @pytest.mark.asyncio
    async def test_generate_mutants_empty_source(self) -> None:
        mutants = await MutationTester.generate_mutants("")
        assert len(mutants) == 0

    @pytest.mark.asyncio
    async def test_mutant_has_unique_ids(self) -> None:
        source = "x = a and b\nif c > d:\n    pass\n"
        mutants = await MutationTester.generate_mutants(source)
        ids = [m.mutant_id for m in mutants]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_mutant_preserves_structure(self) -> None:
        source = "def foo():\n    return a and b\n"
        mutants = await MutationTester.generate_mutants(source)
        for m in mutants:
            assert "def foo()" in m.mutated_code

    @pytest.mark.asyncio
    async def test_mutated_code_differs(self) -> None:
        source = "x = a and b\n"
        mutants = await MutationTester.generate_mutants(source)
        for m in mutants:
            assert m.mutated_code != m.original_code

    @pytest.mark.asyncio
    async def test_mutant_id_is_string(self) -> None:
        source = "x = a and b\n"
        mutants = await MutationTester.generate_mutants(source)
        for m in mutants:
            assert isinstance(m.mutant_id, str)

    def test_compute_mutation_score_all_killed(self) -> None:
        results = tuple(
            MutationTestResult(
                mutant=Mutant(f"id{i}", "o", "m", "t", (0, 0)),
                killed=True,
            )
            for i in range(4)
        )
        score = MutationTester.compute_mutation_score(results)
        assert score == 1.0

    def test_compute_mutation_score_none_killed(self) -> None:
        results = tuple(
            MutationTestResult(
                mutant=Mutant(f"id{i}", "o", "m", "t", (0, 0)),
                killed=False,
            )
            for i in range(4)
        )
        score = MutationTester.compute_mutation_score(results)
        assert score == 0.0

    def test_compute_mutation_score_partial(self) -> None:
        results = (
            MutationTestResult(
                mutant=Mutant("id1", "o", "m", "t", (0, 0)),
                killed=True,
            ),
            MutationTestResult(
                mutant=Mutant("id2", "o", "m", "t", (0, 0)),
                killed=False,
            ),
        )
        score = MutationTester.compute_mutation_score(results)
        assert score == 0.5

    def test_compute_mutation_score_empty(self) -> None:
        score = MutationTester.compute_mutation_score(())
        assert score == 0.0

    def test_compute_mutation_score_rounds(self) -> None:
        results = tuple(
            MutationTestResult(
                mutant=Mutant(f"id{i}", "o", "m", "t", (0, 0)),
                killed=i < 3,
            )
            for i in range(7)
        )
        score = MutationTester.compute_mutation_score(results)
        import math
        assert math.isclose(score, 3 / 7, rel_tol=1e-3)

    @pytest.mark.asyncio
    async def test_mutant_correct_mutation_type(self) -> None:
        source = "x = a and b\n"
        mutants = await MutationTester.generate_mutants(source)
        for m in mutants:
            assert m.mutation_type in (
                "replace_and_with_or", "replace_or_with_and", "invert_if"
            )

    @pytest.mark.asyncio
    async def test_mutant_location(self) -> None:
        source = "x = a and b\n"
        mutants = await MutationTester.generate_mutants(source)
        for m in mutants:
            assert len(m.location) == 2

    @pytest.mark.asyncio
    async def test_complex_source_multiple_mutants(self) -> None:
        source = (
            "if a > b:\n"
            "    x = a and b\n"
            "elif b > c:\n"
            "    y = a or b\n"
        )
        mutants = await MutationTester.generate_mutants(source)
        assert len(mutants) >= 1

    @pytest.mark.asyncio
    async def test_generate_mutants_with_if_no_compare(self) -> None:
        # If node with truthy test (not a Compare) should not be inverted
        source = "if True:\n    pass\n"
        mutants = await MutationTester.generate_mutants(source)
        types = [m.mutation_type for m in mutants]
        assert "invert_if" not in types
