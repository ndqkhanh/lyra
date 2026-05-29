"""Tests for the rewrite generation module."""

from __future__ import annotations

import pytest
from lyra_self_rewrite.hyper_agent import AgentGene, HyperAgent
from lyra_self_rewrite.rewrite_generator import (
    GeneratedRewrite,
    RewriteGenerator,
    RewriteLibrary,
    RewriteTemplate,
)


def _make_agent(
    agent_id: str = "a1",
    fitness: float = 0.8,
    gene_values: dict[str, float] | None = None,
) -> HyperAgent:
    values = gene_values or {"speed": 0.8, "creativity": 0.5, "thoroughness": 0.3}
    genes = tuple(
        AgentGene(f"g-{k}", k, v, 0.0, 1.0) for k, v in values.items()
    )
    return HyperAgent(
        agent_id=agent_id,
        genome=genes,
        fitness=fitness,
        generation=0,
        lineage=(agent_id,),
    )


class TestRewriteTemplate:
    def test_template_creation(self) -> None:
        template = RewriteTemplate(
            template_id="opt-loop",
            pattern="for $idx in range($n):",
            replacement="for $item in $collection:",
            applicable_genes=("speed", "efficiency"),
        )
        assert template.template_id == "opt-loop"
        assert "speed" in template.applicable_genes
        assert len(template.applicable_genes) == 2

    def test_template_frozen(self) -> None:
        template = RewriteTemplate("t1", "pattern", "replacement", ())
        with pytest.raises(AttributeError):
            template.pattern = "new"  # type: ignore[misc]

    def test_template_empty_genes(self) -> None:
        template = RewriteTemplate("t1", "p", "r", ())
        assert template.applicable_genes == ()


class TestGeneratedRewrite:
    def test_rewrite_creation(self) -> None:
        template = RewriteTemplate("t1", "p", "r", ("speed",))
        rewrite = GeneratedRewrite(
            rewrite_id="rw-001",
            agent_id="a1",
            template=template,
            generated_code="print('hello')",
            confidence=0.85,
        )
        assert rewrite.rewrite_id == "rw-001"
        assert rewrite.confidence == 0.85

    def test_rewrite_frozen(self) -> None:
        template = RewriteTemplate("t1", "p", "r", ())
        rewrite = GeneratedRewrite("rw-001", "a1", template, "code", 0.5)
        with pytest.raises(AttributeError):
            rewrite.confidence = 0.9  # type: ignore[misc]

    def test_rewrite_empty_code(self) -> None:
        template = RewriteTemplate("t1", "p", "r", ())
        rewrite = GeneratedRewrite("rw-001", "a1", template, "", 0.5)
        assert rewrite.generated_code == ""


class TestRewriteLibrary:
    def test_library_creation(self) -> None:
        templates = (
            RewriteTemplate("t1", "p", "r", ("s1",)),
            RewriteTemplate("t2", "p", "r", ("s2",)),
        )
        lib = RewriteLibrary(
            templates=templates,
            total_templates=2,
            categories=("opt", "refactor"),
        )
        assert lib.total_templates == 2
        assert len(lib.categories) == 2

    def test_library_empty(self) -> None:
        lib = RewriteLibrary(templates=(), total_templates=0, categories=())
        assert lib.total_templates == 0


class TestRewriteGenerator:
    @pytest.mark.asyncio
    async def test_load_templates(self) -> None:
        generator = RewriteGenerator()
        lib = await generator.load_templates()
        assert lib.total_templates >= 5
        assert "optimisation" in lib.categories

    @pytest.mark.asyncio
    async def test_generate_rewrites(self) -> None:
        generator = RewriteGenerator()
        agent = _make_agent(gene_values={"speed": 0.9})
        lib = await generator.load_templates()
        rewrites = await generator.generate_rewrites(agent, lib)
        # Speed-based agent should match templates
        assert len(rewrites) > 0

    @pytest.mark.asyncio
    async def test_generate_rewrites_no_match(self) -> None:
        generator = RewriteGenerator()
        agent = _make_agent(gene_values={"unknown_trait": 0.5})
        lib = await generator.load_templates()
        rewrites = await generator.generate_rewrites(agent, lib)
        assert len(rewrites) == 0

    @pytest.mark.asyncio
    async def test_generate_rewrites_empty_genome(self) -> None:
        generator = RewriteGenerator()
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        lib = await generator.load_templates()
        rewrites = await generator.generate_rewrites(agent, lib)
        assert rewrites == ()

    @pytest.mark.asyncio
    async def test_generate_rewrites_with_all_traits(self) -> None:
        generator = RewriteGenerator()
        agent = _make_agent(
            gene_values={
                "speed": 0.9,
                "efficiency": 0.8,
                "thoroughness": 0.7,
                "creativity": 0.6,
                "exploration": 0.5,
                "conservatism": 0.4,
            }
        )
        lib = await generator.load_templates()
        rewrites = await generator.generate_rewrites(agent, lib)
        # Should match many templates
        assert len(rewrites) >= 3

    @pytest.mark.asyncio
    async def test_generate_rewrites_generated_code_not_empty(self) -> None:
        generator = RewriteGenerator()
        agent = _make_agent(gene_values={"speed": 0.9})
        lib = await generator.load_templates()
        rewrites = await generator.generate_rewrites(agent, lib)
        for rw in rewrites:
            assert len(rw.generated_code) > 0

    @pytest.mark.asyncio
    async def test_generate_rewrites_confidence_range(self) -> None:
        generator = RewriteGenerator()
        agent = _make_agent(gene_values={"speed": 0.9})
        lib = await generator.load_templates()
        rewrites = await generator.generate_rewrites(agent, lib)
        for rw in rewrites:
            assert 0.0 <= rw.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_validate_rewrite_passes(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ("speed",))
        rewrite = GeneratedRewrite(
            rewrite_id="rw-1",
            agent_id="a1",
            template=template,
            generated_code="# some code",
            confidence=0.9,
        )
        assert await generator.validate_rewrite(rewrite)

    @pytest.mark.asyncio
    async def test_validate_rewrite_empty_code(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rewrite = GeneratedRewrite("rw-1", "a1", template, "", 0.9)
        assert not await generator.validate_rewrite(rewrite)

    @pytest.mark.asyncio
    async def test_validate_rewrite_whitespace_code(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rewrite = GeneratedRewrite("rw-1", "a1", template, "   ", 0.9)
        assert not await generator.validate_rewrite(rewrite)

    @pytest.mark.asyncio
    async def test_validate_rewrite_bad_confidence(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rewrite = GeneratedRewrite("rw-1", "a1", template, "code", 1.5)
        assert not await generator.validate_rewrite(rewrite)

    @pytest.mark.asyncio
    async def test_validate_rewrite_empty_id(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rewrite = GeneratedRewrite("", "a1", template, "code", 0.5)
        assert not await generator.validate_rewrite(rewrite)

    @pytest.mark.asyncio
    async def test_apply_best_rewrite(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rw1 = GeneratedRewrite("rw-1", "a1", template, "code1", 0.7)
        rw2 = GeneratedRewrite("rw-2", "a1", template, "code2", 0.9)
        rw3 = GeneratedRewrite("rw-3", "a1", template, "code3", 0.8)
        best = await generator.apply_best_rewrite((rw1, rw2, rw3), threshold=0.75)
        assert best is not None
        assert best.rewrite_id == "rw-2"

    @pytest.mark.asyncio
    async def test_apply_best_rewrite_empty(self) -> None:
        generator = RewriteGenerator()
        best = await generator.apply_best_rewrite((), threshold=0.8)
        assert best is None

    @pytest.mark.asyncio
    async def test_apply_best_rewrite_none_above_threshold(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rw = GeneratedRewrite("rw-1", "a1", template, "code", 0.5)
        best = await generator.apply_best_rewrite((rw,), threshold=0.8)
        assert best is None

    @pytest.mark.asyncio
    async def test_apply_best_rewrite_default_threshold(self) -> None:
        generator = RewriteGenerator()
        template = RewriteTemplate("t1", "p", "r", ())
        rw = GeneratedRewrite("rw-1", "a1", template, "code", 0.9)
        best = await generator.apply_best_rewrite((rw,))
        assert best is not None
        assert best.rewrite_id == "rw-1"
