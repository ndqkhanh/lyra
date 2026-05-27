"""Tests for Skill Weaver package."""

from __future__ import annotations

import asyncio

import pytest

from lyra_skill_weaver import (
    # Core
    SkillType,
    CompositionPattern,
    SkillStatus,
    SkillMetadata,
    SkillIO,
    SkillDefinition,
    SkillEdge,
    SkillGraph,
    SkillRegistry,
    CompositionPlan,
    SkillWeaver,
    # Composers
    SequentialComposer,
    ParallelComposer,
    ConditionalComposer,
    IterativeComposer,
    MasterComposer,
    # Discovery
    DiscoveryMethod,
    SkillDiscoveryEngine,
    # Optimizer
    OptimizationObjective,
    CompositionProfiler,
    PlanCache,
    CompositionOptimizer,
    # Exceptions
    SkillNotFoundError,
    SkillConflictError,
    CompositionError,
    CircularDependencyError,
    ValidationError,
    DiscoveryError,
    OptimizationError,
)


def make_skill(
    skill_id,
    name="",
    outputs=None,
    inputs=None,
    dependencies=None,
    conflicts=None,
    quality=0.8,
    cost=0.1,
    latency=100.0,
):
    return SkillDefinition(
        metadata=SkillMetadata(
            skill_id=skill_id,
            name=name or skill_id,
            status=SkillStatus.ACTIVE,
        ),
        skill_type=SkillType.PRIMITIVE,
        inputs=[SkillIO(name=i, type_hint="Any") for i in (inputs or [])],
        outputs=[SkillIO(name=o, type_hint="Any") for o in (outputs or [])],
        dependencies=dependencies or [],
        conflicts=conflicts or [],
        quality_score=quality,
        estimated_cost=cost,
        avg_latency_ms=latency,
    )


# ── SkillRegistry ──────────────────────────────────────────────────────


class TestSkillRegistry:
    def test_register_skill(self):
        reg = SkillRegistry()
        skill = make_skill("m1", "test", outputs=["result"])
        reg.register(skill)
        assert reg.skill_count == 1
        assert reg.get("m1") is not None

    def test_unregister(self):
        reg = SkillRegistry()
        reg.register(make_skill("test_1"))
        assert reg.unregister("test_1")
        assert reg.skill_count == 0

    def test_find_by_output(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["code", "tests"]))
        reg.register(make_skill("s2", outputs=["plan"]))
        results = reg.find_by_output("code")
        assert len(results) == 1

    def test_find_by_capability(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["code"]))
        reg.register(make_skill("s2", outputs=["code", "tests"]))
        found = reg.find_by_capability(set(), {"code"})
        assert len(found) == 2

    def test_graph_dependencies(self):
        reg = SkillRegistry()
        reg.register(make_skill("A", outputs=["a"]))
        reg.register(make_skill("B", outputs=["b"], dependencies=["A"]))
        deps = reg.graph.get_dependencies("B")
        assert "A" in deps

    def test_list_skills_empty(self):
        reg = SkillRegistry()
        assert reg.skill_count == 0


# ── SkillGraph ──────────────────────────────────────────────────────────


class TestSkillGraph:
    def test_add_and_remove_node(self):
        g = SkillGraph()
        g.add_node(make_skill("A"))
        assert g.has_node("A")
        g.remove_node("A")
        assert not g.has_node("A")

    def test_topological_sort(self):
        g = SkillGraph()
        g.add_node(make_skill("A"))
        g.add_node(make_skill("B"))
        g.add_node(make_skill("C"))
        g.add_edge(SkillEdge(source_id="B", target_id="A", edge_type="depends_on"))
        g.add_edge(SkillEdge(source_id="C", target_id="B", edge_type="depends_on"))
        order = g.topological_sort()
        assert order == ["A", "B", "C"]  # Dependencies first

    def test_circular_dependency(self):
        g = SkillGraph()
        g.add_node(make_skill("A"))
        g.add_node(make_skill("B"))
        g.add_edge(SkillEdge(source_id="A", target_id="B", edge_type="depends_on"))
        g.add_edge(SkillEdge(source_id="B", target_id="A", edge_type="depends_on"))
        with pytest.raises(CircularDependencyError):
            g.topological_sort()

    def test_get_dependents(self):
        g = SkillGraph()
        g.add_node(make_skill("A"))
        g.add_node(make_skill("B"))
        g.add_edge(SkillEdge(source_id="B", target_id="A", edge_type="depends_on"))
        dependents = g.get_dependents("A")
        assert "B" in dependents

    def test_get_conflicts(self):
        g = SkillGraph()
        g.add_node(make_skill("A"))
        g.add_node(make_skill("B"))
        g.add_edge(SkillEdge(source_id="A", target_id="B", edge_type="conflicts_with"))
        conflicts = g.get_conflicts("A")
        assert "B" in conflicts

    def test_shortest_path(self):
        g = SkillGraph()
        g.add_node(make_skill("A"))
        g.add_node(make_skill("B"))
        g.add_node(make_skill("C"))
        g.add_edge(SkillEdge(source_id="A", target_id="B", edge_type="depends_on"))
        g.add_edge(SkillEdge(source_id="B", target_id="C", edge_type="depends_on"))
        path = g.shortest_path("A", "C")
        assert path == ["A", "B", "C"]


# ── SkillWeaver ────────────────────────────────────────────────────────


class TestSkillWeaver:
    def test_creation(self):
        w = SkillWeaver()
        assert w.registry is not None

    def test_register_and_weave(self):
        w = SkillWeaver()
        skill = make_skill("s1", "code_gen", outputs=["code", "tests"], inputs=["spec"])
        w.register_skill(skill)
        plan = asyncio.run(w.weave("code_generation", {"complexity": 0.5}))
        assert isinstance(plan, CompositionPlan)

    def test_register_skills_batch(self):
        w = SkillWeaver()
        skills = [make_skill("s1", outputs=["a"]), make_skill("s2", outputs=["b"])]
        w.register_skills(skills)
        assert w.registry.skill_count == 2

    def test_validate_plan_valid(self):
        w = SkillWeaver()
        w.register_skill(make_skill("s1", outputs=["result"]))
        plan = CompositionPlan(plan_id="t", modules=["s1"], expected_outputs=["result"])
        valid, issues = w.validate_plan(plan)
        assert valid

    def test_validate_plan_missing(self):
        w = SkillWeaver()
        plan = CompositionPlan(modules=["nonexistent"])
        valid, issues = w.validate_plan(plan)
        assert not valid
        assert len(issues) > 0


# ── Composers ──────────────────────────────────────────────────────────


class TestSequentialComposer:
    def test_build(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["code"]))
        comp = SequentialComposer(reg)
        plan = comp.build(["code"])
        assert len(plan.modules) > 0

    def test_build_empty(self):
        reg = SkillRegistry()
        comp = SequentialComposer(reg)
        with pytest.raises(CompositionError):
            comp.build(["code"])


class TestParallelComposer:
    def test_build(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["analysis"]))
        reg.register(make_skill("s2", outputs=["summary"]))
        comp = ParallelComposer(reg)
        plan = comp.build(["analysis", "summary"])
        assert len(plan.modules) > 0


class TestConditionalComposer:
    def test_build(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["result_a"]))
        reg.register(make_skill("s2", outputs=["result_b"]))
        comp = ConditionalComposer(reg)
        plan = comp.build("x > 0", ["result_a"], ["result_b"])
        assert plan.pattern == CompositionPattern.CONDITIONAL


class TestIterativeComposer:
    def test_build(self):
        reg = SkillRegistry()
        reg.register(make_skill("refine", outputs=["optimized_result"], inputs=["input"]))
        comp = IterativeComposer(reg, max_iterations=5)
        plan = comp.build("refine", "conv_check")
        assert plan.pattern == CompositionPattern.ITERATIVE


class TestMasterComposer:
    def test_compose_sequential(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["result"]))
        mc = MasterComposer(reg)
        plan = mc.compose(["result"], pattern=CompositionPattern.SEQUENTIAL)
        assert plan.pattern == CompositionPattern.SEQUENTIAL

    def test_get_available_patterns(self):
        reg = SkillRegistry()
        mc = MasterComposer(reg)
        patterns = mc.get_available_patterns()
        assert len(patterns) > 0


# ── Optimizer ──────────────────────────────────────────────────────────


class TestPlanCache:
    def test_put_and_get(self):
        cache = PlanCache(max_size=10)
        plan = CompositionPlan(plan_id="test", modules=["s1"])
        key = cache.compute_key(["result"], CompositionPattern.SEQUENTIAL)
        cache.put(key, plan)
        assert cache.get(key) is not None
        assert cache.get(key).plan_id == "test"

    def test_cache_miss(self):
        cache = PlanCache()
        assert cache.get("nonexistent") is None

    def test_invalidate(self):
        cache = PlanCache()
        key = cache.compute_key(["r"], CompositionPattern.SEQUENTIAL)
        cache.put(key, CompositionPlan(plan_id="test"))
        assert cache.invalidate(key)
        assert cache.size == 0

    def test_clear(self):
        cache = PlanCache()
        key = cache.compute_key(["r"], CompositionPattern.SEQUENTIAL)
        cache.put(key, CompositionPlan(plan_id="t"))
        cache.clear()
        assert cache.size == 0


class TestCompositionProfiler:
    def test_record_execution(self):
        profiler = CompositionProfiler(SkillRegistry())
        result = profiler.record_execution("p1", {"s1": 100.0, "s2": 200.0}, cost=0.5)
        assert result.plan_id == "p1"
        assert result.execution_time_ms == 300.0

    def test_get_skill_stats(self):
        profiler = CompositionProfiler(SkillRegistry())
        profiler.record_execution("p1", {"s1": 100.0})
        profiler.record_execution("p2", {"s1": 200.0})
        stats = profiler.get_skill_stats("s1")
        assert stats["count"] == 2


class TestCompositionOptimizer:
    def test_optimize(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1", outputs=["r"], cost=0.5, quality=0.7))
        reg.register(make_skill("s2", outputs=["r"], cost=0.1, quality=0.9))
        plan = CompositionPlan(plan_id="p1", modules=["s1"], estimated_cost=0.5)
        opt = CompositionOptimizer(reg)
        result = asyncio.run(opt.optimize(plan))
        assert result.optimized_plan is not None

    def test_find_bottlenecks(self):
        reg = SkillRegistry()
        reg.register(make_skill("s1"))
        profiler = CompositionProfiler(reg)
        profiler.record_execution("p1", {"s1": 5000.0})
        opt = CompositionOptimizer(reg, profiler=profiler)
        plan = CompositionPlan(modules=["s1"])
        bottlenecks = opt.find_bottlenecks(plan)
        assert len(bottlenecks) > 0


# ── Discovery ──────────────────────────────────────────────────────────


class TestSkillDiscoveryEngine:
    @pytest.mark.asyncio
    async def test_discover_from_directory_empty(self):
        import tempfile
        import os
        from pathlib import Path
        reg = SkillRegistry()
        engine = SkillDiscoveryEngine(reg)
        with tempfile.TemporaryDirectory() as tmpdir:
            skills = await engine.discover_from_directory(Path(tmpdir))
            assert isinstance(skills, list)

    def test_evaluate_quality(self):
        reg = SkillRegistry()
        engine = SkillDiscoveryEngine(reg)
        skill = make_skill("test", "TestSkill", outputs=["r"])
        report = engine.evaluate_quality(skill)
        assert report.skill_id == "test"
        assert report.overall_score > 0

    def test_analyze_gaps(self):
        reg = SkillRegistry()
        engine = SkillDiscoveryEngine(reg)
        gaps = engine.analyze_gaps(["missing_capability"])
        assert "missing_capability" in gaps.missing_capabilities


# ── Exceptions ────────────────────────────────────────────────────────


class TestExceptions:
    def test_skill_not_found(self):
        with pytest.raises(SkillNotFoundError):
            raise SkillNotFoundError("x")

    def test_skill_conflict(self):
        with pytest.raises(SkillConflictError):
            raise SkillConflictError("A", "B", "reason")

    def test_composition_error(self):
        with pytest.raises(CompositionError):
            raise CompositionError("fail")

    def test_circular_dependency(self):
        with pytest.raises(CircularDependencyError):
            raise CircularDependencyError(["A", "B", "A"])

    def test_validation_error(self):
        with pytest.raises(ValidationError):
            raise ValidationError("s", "bad")

    def test_discovery_error(self):
        with pytest.raises(DiscoveryError):
            raise DiscoveryError("src", "reason")

    def test_optimization_error(self):
        with pytest.raises(OptimizationError):
            raise OptimizationError("comp_id", "reason")
