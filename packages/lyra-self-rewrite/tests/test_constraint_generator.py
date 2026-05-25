"""Tests for the constraint-based safe generation module."""

from __future__ import annotations

import pytest

from lyra_self_rewrite.constraint_generator import (
    ConstraintCheck,
    ConstraintGenerator,
    ConstraintReport,
    ConstraintSpec,
    _check_agent,
    _description_to_check,
)
from lyra_self_rewrite.hyper_agent import AgentGene, HyperAgent


def _make_agent(
    agent_id: str = "a1",
    genome_size: int = 3,
    fitness: float = 0.5,
) -> HyperAgent:
    genes = tuple(
        AgentGene(f"g{i}", f"trait{i}", 0.5, 0.0, 1.0)
        for i in range(genome_size)
    )
    return HyperAgent(
        agent_id=agent_id,
        genome=genes,
        fitness=fitness,
        generation=0,
        lineage=(agent_id,),
    )


class TestConstraintSpec:
    def test_spec_creation(self) -> None:
        spec = ConstraintSpec(
            constraint_id="c1",
            description="Must have genes",
            check_function="min_genes",
            severity="hard",
        )
        assert spec.constraint_id == "c1"
        assert spec.severity == "hard"
        assert spec.enabled

    def test_spec_frozen(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        with pytest.raises(AttributeError):
            spec.enabled = False  # type: ignore[misc]

    def test_spec_defaults(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        assert spec.severity == "hard"
        assert spec.enabled

    def test_spec_disabled(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn", enabled=False)
        assert not spec.enabled

    def test_spec_soft_severity(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn", severity="soft")
        assert spec.severity == "soft"


class TestConstraintCheck:
    def test_check_creation(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        check = ConstraintCheck(
            constraint=spec,
            passed=True,
            violations=(),
        )
        assert check.passed
        assert check.violations == ()

    def test_check_with_violations(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        check = ConstraintCheck(
            constraint=spec,
            passed=False,
            violations=("empty genome",),
            score_deduction=0.5,
        )
        assert not check.passed
        assert len(check.violations) == 1

    def test_check_frozen(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        check = ConstraintCheck(spec, True, ())
        with pytest.raises(AttributeError):
            check.passed = False  # type: ignore[misc]


class TestConstraintReport:
    def test_report_all_passed(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        check = ConstraintCheck(spec, True, ())
        report = ConstraintReport(
            checks=(check,),
            all_passed=True,
            score_penalty=0.0,
            recommendations=(),
        )
        assert report.all_passed

    def test_report_with_issues(self) -> None:
        spec = ConstraintSpec("c1", "desc", "fn")
        check = ConstraintCheck(spec, False, ("violation",), score_deduction=0.5)
        report = ConstraintReport(
            checks=(check,),
            all_passed=False,
            score_penalty=0.5,
            recommendations=("fix it",),
        )
        assert not report.all_passed
        assert len(report.recommendations) == 1

    def test_report_frozen(self) -> None:
        report = ConstraintReport((), True, 0.0, ())
        with pytest.raises(AttributeError):
            report.all_passed = False  # type: ignore[misc]


class TestDescriptionToCheck:
    def test_simple_conversion(self) -> None:
        assert _description_to_check("min genes") == "min_genes"

    def test_with_spaces(self) -> None:
        assert (
            _description_to_check("gene values within bounds")
            == "gene_values_within_bounds"
        )

    def test_max_length(self) -> None:
        long_desc = "a" * 100
        result = _description_to_check(long_desc)
        assert len(result) == 64

    def test_with_hyphens(self) -> None:
        assert _description_to_check("non-negative-fitness") == "non_negative_fitness"


class TestCheckAgent:
    def test_min_genes_passes(self) -> None:
        agent = _make_agent(genome_size=3)
        spec = ConstraintSpec("c1", "desc", "min_genes")
        passed, violations = _check_agent(agent, spec)
        assert passed
        assert violations == []

    def test_min_genes_fails_empty(self) -> None:
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        spec = ConstraintSpec("c1", "desc", "min_genes")
        passed, violations = _check_agent(agent, spec)
        assert not passed

    def test_gene_bounds_passes(self) -> None:
        agent = _make_agent()
        spec = ConstraintSpec("c1", "desc", "gene_bounds")
        passed, violations = _check_agent(agent, spec)
        assert passed

    def test_gene_bounds_fails(self) -> None:
        bad_gene = AgentGene("g1", "t", 1.5, 0.0, 1.0)
        agent = HyperAgent("a1", (bad_gene,), 0.0, 0, ("a1",))
        spec = ConstraintSpec("c1", "desc", "gene_bounds")
        passed, violations = _check_agent(agent, spec)
        assert not passed

    def test_non_negative_fitness_passes(self) -> None:
        agent = _make_agent(fitness=0.5)
        spec = ConstraintSpec("c1", "desc", "non_negative_fitness")
        passed, violations = _check_agent(agent, spec)
        assert passed

    def test_non_negative_fitness_negative(self) -> None:
        agent = _make_agent(fitness=-0.5)
        spec = ConstraintSpec("c1", "desc", "non_negative_fitness")
        passed, violations = _check_agent(agent, spec)
        assert not passed

    def test_lineage_minimal_empty(self) -> None:
        agent = HyperAgent("a1", (), 0.0, 0, ())
        spec = ConstraintSpec("c1", "desc", "lineage_minimal")
        passed, violations = _check_agent(agent, spec)
        assert not passed

    def test_max_genes_under_limit(self) -> None:
        agent = _make_agent(genome_size=10)
        spec = ConstraintSpec("c1", "desc", "max_genes")
        passed, violations = _check_agent(agent, spec)
        assert passed

    def test_max_genes_over_limit(self) -> None:
        genes = tuple(
            AgentGene(f"g{i}", f"t{i}", 0.5, 0.0, 1.0)
            for i in range(60)
        )
        agent = HyperAgent("a1", genes, 0.0, 0, ("a1",))
        spec = ConstraintSpec("c1", "desc", "max_genes")
        passed, violations = _check_agent(agent, spec)
        assert not passed

    def test_unknown_check_passes(self) -> None:
        agent = _make_agent()
        spec = ConstraintSpec("c1", "desc", "unknown_check")
        passed, violations = _check_agent(agent, spec)
        assert passed


class TestConstraintGenerator:
    @pytest.mark.asyncio
    async def test_add_constraint(self) -> None:
        generator = ConstraintGenerator()
        spec = await generator.add_constraint("Must have genes", "hard")
        assert spec.constraint_id == "c-1"
        assert spec.description == "Must have genes"

    @pytest.mark.asyncio
    async def test_add_constraint_soft(self) -> None:
        generator = ConstraintGenerator()
        spec = await generator.add_constraint("Soft constraint", "soft")
        assert spec.severity == "soft"

    @pytest.mark.asyncio
    async def test_add_constraint_default_severity(self) -> None:
        generator = ConstraintGenerator()
        spec = await generator.add_constraint("Default severity")
        assert spec.severity == "hard"

    @pytest.mark.asyncio
    async def test_add_multiple_constraints(self) -> None:
        generator = ConstraintGenerator()
        c1 = await generator.add_constraint("First")
        c2 = await generator.add_constraint("Second")
        assert c1.constraint_id == "c-1"
        assert c2.constraint_id == "c-2"

    @pytest.mark.asyncio
    async def test_validate_agent_all_pass(self) -> None:
        generator = ConstraintGenerator()
        agent = _make_agent()
        constraints = (
            ConstraintSpec("c1", "min genes", "min_genes"),
            ConstraintSpec("c2", "bounds", "gene_bounds"),
        )
        report = await generator.validate_agent(agent, constraints)
        assert report.all_passed
        assert report.score_penalty == 0.0

    @pytest.mark.asyncio
    async def test_validate_agent_hard_fail(self) -> None:
        generator = ConstraintGenerator()
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        constraints = (ConstraintSpec("c1", "min genes", "min_genes"),)
        report = await generator.validate_agent(agent, constraints)
        assert not report.all_passed
        assert report.score_penalty == 0.5

    @pytest.mark.asyncio
    async def test_validate_agent_soft_fail(self) -> None:
        generator = ConstraintGenerator()
        agent = HyperAgent("a1", (), 0.0, 0, ())
        constraints = (
            ConstraintSpec("c1", "lineage", "lineage_minimal", severity="soft"),
        )
        report = await generator.validate_agent(agent, constraints)
        assert not report.all_passed
        assert report.score_penalty == 0.1

    @pytest.mark.asyncio
    async def test_validate_agent_disabled_constraint(self) -> None:
        generator = ConstraintGenerator()
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        constraints = (
            ConstraintSpec("c1", "min genes", "min_genes", enabled=False),
        )
        report = await generator.validate_agent(agent, constraints)
        assert report.all_passed  # Disabled constraints always pass

    @pytest.mark.asyncio
    async def test_generate_default_constraints(self) -> None:
        generator = ConstraintGenerator()
        constraints = await generator.generate_default_constraints()
        assert len(constraints) == 5
        assert constraints[0].check_function == "min_genes"
        assert constraints[1].check_function == "gene_bounds"

    @pytest.mark.asyncio
    async def test_filter_by_constraints_all_pass(self) -> None:
        generator = ConstraintGenerator()
        agents = tuple(
            _make_agent(f"a{i}", genome_size=3, fitness=0.5)
            for i in range(3)
        )
        constraints = (ConstraintSpec("c1", "min genes", "min_genes"),)
        filtered = await generator.filter_by_constraints(agents, constraints)
        assert len(filtered) == 3

    @pytest.mark.asyncio
    async def test_filter_by_constraints_some_fail(self) -> None:
        generator = ConstraintGenerator()
        good = _make_agent("good", genome_size=3)
        bad = HyperAgent("bad", (), 0.0, 0, ("bad",))
        agents = (good, bad)
        constraints = (ConstraintSpec("c1", "min genes", "min_genes"),)
        filtered = await generator.filter_by_constraints(agents, constraints)
        assert len(filtered) == 1
        assert filtered[0].agent_id == "good"

    @pytest.mark.asyncio
    async def test_filter_by_constraints_empty(self) -> None:
        generator = ConstraintGenerator()
        filtered = await generator.filter_by_constraints((), ())
        assert filtered == ()

    @pytest.mark.asyncio
    async def test_filter_by_constraints_soft_fail_still_passes(self) -> None:
        generator = ConstraintGenerator()
        agent = _make_agent()
        constraints = (
            ConstraintSpec("c1", "desc", "min_genes", severity="soft"),
        )
        filtered = await generator.filter_by_constraints((agent,), constraints)
        assert len(filtered) == 1

    @pytest.mark.asyncio
    async def test_validate_agent_multiple_hard_fails(self) -> None:
        generator = ConstraintGenerator()
        bad_genes = (AgentGene("g1", "t", 1.5, 0.0, 1.0),)
        agent = HyperAgent("a1", bad_genes, -1.0, 0, ("a1",))
        constraints = (
            ConstraintSpec("c1", "bounds", "gene_bounds"),
            ConstraintSpec("c2", "fitness", "non_negative_fitness"),
        )
        report = await generator.validate_agent(agent, constraints)
        assert not report.all_passed
        assert report.score_penalty == 1.0  # 0.5 + 0.5
