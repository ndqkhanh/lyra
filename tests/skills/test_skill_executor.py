"""
Tests for SkillGraph (dependency graph) and SkillExecutor (agent loop).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.skills import (
    CycleError,
    ExecutionStatus,
    Skill,
    SkillCategory,
    SkillExecutor,
    SkillGraph,
    SkillRegistry,
)


# ======================================================================
# SkillGraph tests
# ======================================================================


class TestSkillGraph:
    """Tests for the SkillGraph dependency graph."""

    def test_empty_graph(self) -> None:
        """An empty graph has no nodes, no cycles, and an empty order."""
        g = SkillGraph()
        assert g.get_execution_order() == []
        assert not g.has_cycle()
        assert g.detect_cycles() == []

    def test_single_node(self) -> None:
        """A single node with no edges is valid."""
        g = SkillGraph()
        g.add_node("a")
        assert g.get_execution_order() == ["a"]

    def test_simple_dependency(self) -> None:
        """a depends on b -> b must come before a."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        order = g.get_execution_order()
        assert order.index("b") < order.index("a")

    def test_chain_dependency(self) -> None:
        """a -> b -> c (a depends on b, b depends on c)."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        order = g.get_execution_order()
        assert order.index("c") < order.index("b") < order.index("a")

    def test_diamond_dependency(self) -> None:
        """a depends on b and c, both depend on d -> d first."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("a", "c")
        g.add_dependency("b", "d")
        g.add_dependency("c", "d")
        order = g.get_execution_order()
        assert order.index("d") < order.index("b")
        assert order.index("d") < order.index("c")
        assert order.index("b") < order.index("a")
        assert order.index("c") < order.index("a")

    def test_no_dependency(self) -> None:
        """Independent nodes can be in any order (just check all present)."""
        g = SkillGraph()
        g.add_node("a")
        g.add_node("b")
        g.add_node("c")
        order = g.get_execution_order()
        assert set(order) == {"a", "b", "c"}

    def test_cycle_detection_simple(self) -> None:
        """a -> b -> a is a cycle and should be detected."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "a")
        assert g.has_cycle()
        cycles = g.detect_cycles()
        assert len(cycles) > 0

    def test_cycle_detection_raises(self) -> None:
        """get_execution_order should raise CycleError when a cycle exists."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        g.add_dependency("c", "a")
        with pytest.raises(CycleError):
            g.get_execution_order()

    def test_cycle_error_message(self) -> None:
        """CycleError should contain the cycle path."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "a")
        with pytest.raises(CycleError) as exc:
            g.get_execution_order()
        assert "Cycle detected" in str(exc.value)

    def test_self_loop(self) -> None:
        """A node that depends on itself is a cycle."""
        g = SkillGraph()
        g.add_dependency("x", "x")
        assert g.has_cycle()

    def test_remove_node(self) -> None:
        """Removing a node cleans up all its edges."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        g.remove_node("b")
        order = g.get_execution_order()
        assert "b" not in order

    def test_dependencies_and_dependents(self) -> None:
        """Query direct dependencies and dependents."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("a", "c")
        g.add_dependency("b", "c")
        assert g.dependencies("a") == {"b", "c"}
        assert g.dependencies("b") == {"c"}
        assert g.dependencies("c") == set()
        assert g.dependents("c") == {"a", "b"}
        assert g.dependents("b") == {"a"}

    def test_serialization_roundtrip(self) -> None:
        """to_dict / from_dict round-trip preserves graph structure."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("b", "c")
        data = g.to_dict()
        g2 = SkillGraph.from_dict(data)
        assert g2.get_execution_order() == g.get_execution_order()
        assert g2.dependencies("a") == {"b"}

    def test_from_dict_empty(self) -> None:
        """from_dict({}) produces an empty graph."""
        g = SkillGraph.from_dict({})
        assert g.get_execution_order() == []

    def test_no_cycle_with_multiple_subgraphs(self) -> None:
        """Disconnected subgraphs should not trigger false cycles."""
        g = SkillGraph()
        g.add_dependency("a", "b")
        g.add_dependency("x", "y")
        assert not g.has_cycle()
        order = g.get_execution_order()
        assert len(order) == 4


# ======================================================================
# SkillRegistry + SkillGraph integration tests
# ======================================================================


class TestSkillRegistryGraph:
    """Tests verifying SkillRegistry correctly manages the dependency graph."""

    def test_register_adds_to_graph(self) -> None:
        """Registering a skill with dependencies updates the graph."""
        registry = SkillRegistry()
        skill = Skill(
            name="app-skill",
            description="Depends on base",
            content="content",
            dependencies=["base-skill"],
        )
        registry.register(skill)
        assert registry.graph.dependencies("app-skill") == {"base-skill"}

    def test_register_no_deps(self) -> None:
        """Registering a skill with no deps adds an isolated node."""
        registry = SkillRegistry()
        skill = Skill(
            name="standalone",
            description="No deps",
            content="content",
        )
        registry.register(skill)
        assert "standalone" in registry.graph.get_execution_order()

    def test_unregister_removes_from_graph(self) -> None:
        """Unregistering a skill removes it and its edges."""
        registry = SkillRegistry()
        a = Skill(name="a", description="a", content="c", dependencies=["b"])
        b = Skill(name="b", description="b", content="c")
        registry.register(a)
        registry.register(b)
        registry.unregister("a")
        order = registry.get_execution_order()
        assert "a" not in order

    def test_get_execution_order_integration(self) -> None:
        """Full integration: register chain, verify topological order."""
        registry = SkillRegistry()
        registry.register(Skill(name="c", description="c", content="c"))
        registry.register(
            Skill(name="b", description="b", content="b", dependencies=["c"])
        )
        registry.register(
            Skill(name="a", description="a", content="a", dependencies=["b"])
        )
        order = registry.get_execution_order()
        assert order.index("c") < order.index("b") < order.index("a")

    def test_cycle_integration(self) -> None:
        """Cycle via registry graph raises CycleError."""
        registry = SkillRegistry()
        registry.register(
            Skill(name="a", description="a", content="c", dependencies=["b"])
        )
        registry.register(
            Skill(name="b", description="b", content="c", dependencies=["a"])
        )
        with pytest.raises(CycleError):
            registry.get_execution_order()

    def test_clear_resets_graph(self) -> None:
        """Clearing the registry resets the graph."""
        registry = SkillRegistry()
        registry.register(Skill(name="a", description="a", content="c"))
        registry.clear()
        assert registry.graph.get_execution_order() == []


# ======================================================================
# SkillExecutor tests
# ======================================================================


class TestSkillExecutor:
    """Tests for SkillExecutor — trigger matching, execution, chaining."""

    # -- Fixtures -------------------------------------------------------

    @pytest.fixture
    def registry(self) -> SkillRegistry:
        reg = SkillRegistry()
        reg.register(
            Skill(
                name="format-code",
                description="Format source code",
                content="Apply black and isort formatting.",
                category=SkillCategory.CODING_STANDARDS,
                trigger_patterns=["format", "formatting", "lint"],
            )
        )
        reg.register(
            Skill(
                name="run-tests",
                description="Run test suite",
                content="Execute pytest with coverage.",
                category=SkillCategory.TDD_TESTING,
                trigger_patterns=["test", "testing", "pytest"],
                dependencies=["format-code"],
            )
        )
        reg.register(
            Skill(
                name="deploy",
                description="Deploy to production",
                content="Run deployment pipeline.",
                category=SkillCategory.DEPLOYMENT,
                trigger_patterns=["deploy", "release"],
                dependencies=["run-tests"],
            )
        )
        reg.register(
            Skill(
                name="standalone",
                description="Independent skill",
                content="Does not depend on anything.",
                trigger_patterns=["standalone", "alone"],
            )
        )
        return reg

    @pytest.fixture
    def executor(self, registry: SkillRegistry) -> SkillExecutor:
        return SkillExecutor(registry)

    # -- find_skills ----------------------------------------------------

    def test_find_skills_by_trigger(self, executor: SkillExecutor) -> None:
        """find_skills returns matching skills sorted by score."""
        results = executor.find_skills("I need to run tests and format code")
        names = [s.name for s in results]
        assert "format-code" in names
        assert "run-tests" in names

    def test_find_skills_no_match(self, executor: SkillExecutor) -> None:
        """find_skills returns empty list when nothing matches."""
        assert executor.find_skills("completely unrelated text") == []

    def test_find_best_skill(self, executor: SkillExecutor) -> None:
        """find_best_skill returns the top match."""
        skill = executor.find_best_skill("run pytest tests")
        assert skill is not None
        assert skill.name == "run-tests"

    def test_find_best_skill_no_match(self, executor: SkillExecutor) -> None:
        """find_best_skill returns None when nothing matches."""
        assert executor.find_best_skill("gibberish xyzzy") is None

    # -- execute (single) -----------------------------------------------

    def test_execute_single_skill(self, executor: SkillExecutor) -> None:
        """Execute a single skill without chaining."""
        plan = executor.execute("format-code")
        assert plan.order == ["format-code"]
        result = plan.results["format-code"]
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output == "Apply black and isort formatting."

    def test_execute_unknown_skill(self, executor: SkillExecutor) -> None:
        """Executing a non-existent skill returns a failed result."""
        plan = executor.execute("does-not-exist")
        result = plan.results["does-not-exist"]
        assert result.status == ExecutionStatus.FAILED
        assert "not found" in (result.error or "")

    def test_execute_single_skill_with_trigger(
        self, executor: SkillExecutor
    ) -> None:
        """Trigger text is recorded in the execution result."""
        plan = executor.execute("run-tests", trigger_text="run all tests")
        result = plan.results["run-tests"]
        assert result.triggered_by == "run all tests"

    # -- execute (chained) ----------------------------------------------

    def test_execute_chained_in_topological_order(
        self, executor: SkillExecutor
    ) -> None:
        """Chained execution follows dependency order."""
        plan = executor.execute("deploy", chain=True)
        # The chain should include all transitive deps
        names_in_order = plan.order
        assert "format-code" in names_in_order
        assert "run-tests" in names_in_order
        assert "deploy" in names_in_order
        # Topological: format-code before run-tests before deploy
        assert names_in_order.index("format-code") < names_in_order.index("run-tests")
        assert names_in_order.index("run-tests") < names_in_order.index("deploy")
        # All should succeed
        assert plan.succeeded

    def test_execute_chain_standalone(self, executor: SkillExecutor) -> None:
        """Chaining a standalone skill only runs itself."""
        plan = executor.execute("standalone", chain=True)
        assert plan.order == ["standalone"]
        assert plan.succeeded

    def test_execute_chain_depth_cap(self, executor: SkillExecutor) -> None:
        """max_chain_depth caps how many chained skills execute."""
        # deploy depends on run-tests depends on format-code (depth 3)
        # With max_chain_depth=2, we should only get format-code + run-tests
        plan = executor.execute("deploy", chain=True, max_chain_depth=2)
        names = set(plan.order)
        assert "format-code" in names or "run-tests" in names
        # The whole chain is 3, capped at 2 from root
        assert len(plan.order) <= 2

    # -- execute_multi --------------------------------------------------

    def test_execute_multi(self, executor: SkillExecutor) -> None:
        """execute_multi runs skills matching multiple trigger texts."""
        texts = ["format the code", "run pytest"]
        plans = executor.execute_multi(texts)
        assert len(plans) >= 1
        all_names = set()
        for p in plans:
            for n in p.order:
                all_names.add(n)
        assert "format-code" in all_names

    def test_execute_multi_deduplicates(self, executor: SkillExecutor) -> None:
        """Same skill matched by multiple texts runs only once."""
        texts = ["format the code", "please format", "run tests"]
        plans = executor.execute_multi(texts)
        # "format-code" should appear only in one plan
        format_plans = [p for p in plans if "format-code" in p.order]
        assert len(format_plans) == 1

    # -- custom execute function ----------------------------------------

    def test_custom_execute_fn(self, registry: SkillRegistry) -> None:
        """Custom execute function is called instead of default."""
        calls: list[str] = []

        def my_exec(skill: Skill) -> str:
            calls.append(skill.name)
            return f"executed-{skill.name}"

        ex = SkillExecutor(registry, execute_skill_fn=my_exec)
        plan = ex.execute("standalone")
        assert calls == ["standalone"]
        assert plan.results["standalone"].output == "executed-standalone"

    def test_execute_fn_raises(self, registry: SkillRegistry) -> None:
        """Exception in execute function is captured as a failure."""

        def failing_fn(skill: Skill) -> str:
            raise RuntimeError("something broke")

        ex = SkillExecutor(registry, execute_skill_fn=failing_fn)
        plan = ex.execute("standalone")
        result = plan.results["standalone"]
        assert result.status == ExecutionStatus.FAILED
        assert "something broke" in (result.error or "")

    # -- hooks ----------------------------------------------------------

    def test_before_hook(self, executor: SkillExecutor) -> None:
        """Before hook runs and can modify the result."""
        calls: list[str] = []

        def hook(skill: Skill, result: Any) -> Any:
            calls.append(f"before-{skill.name}")
            return result

        executor.add_before_hook(hook)
        executor.execute("standalone")
        assert "before-standalone" in calls

    def test_after_hook(self, executor: SkillExecutor) -> None:
        """After hook runs with the completed result."""
        captured: list[str] = []

        def hook(skill: Skill, result: Any) -> Any:
            captured.append(f"after-{skill.name}-{result.status.value}")
            return result

        executor.add_after_hook(hook)
        executor.execute("standalone")
        assert "after-standalone-success" in captured

    def test_hooks_called_in_order(self, executor: SkillExecutor) -> None:
        """Before hooks fire, then execution, then after hooks."""
        trace: list[str] = []

        def before(skill: Skill, result: Any) -> Any:
            trace.append("before")
            return result

        def after(skill: Skill, result: Any) -> Any:
            trace.append("after")
            return result

        executor.add_before_hook(before)
        executor.add_after_hook(after)
        executor.execute("standalone")
        assert trace == ["before", "after"]

    # -- history --------------------------------------------------------

    def test_history(self, executor: SkillExecutor) -> None:
        """history tracks all executed plans."""
        assert executor.history == []
        executor.execute("standalone")
        assert len(executor.history) == 1
        executor.execute("format-code")
        assert len(executor.history) == 2

    def test_last_execution(self, executor: SkillExecutor) -> None:
        """last_execution returns the most recent plan."""
        assert executor.last_execution() is None
        executor.execute("standalone")
        plan = executor.last_execution()
        assert plan is not None
        assert "standalone" in plan.order

    # -- ExecutionPlan helpers ------------------------------------------

    def test_execution_plan_summary(self, executor: SkillExecutor) -> None:
        """ExecutionPlan.summary provides correct stats."""
        plan = executor.execute("standalone")
        summary = plan.summary
        assert summary["total"] == 1
        assert summary["succeeded"] == 1
        assert summary["failed"] == 0

    def test_execution_plan_succeeded_property(
        self, executor: SkillExecutor
    ) -> None:
        """succeeded is True when all skills pass, False otherwise."""
        plan = executor.execute("standalone")
        assert plan.succeeded

        plan2 = executor.execute("does-not-exist")
        assert not plan2.succeeded

    # -- edge cases -----------------------------------------------------

    def test_execute_with_empty_registry(self) -> None:
        """Executor with empty registry fails gracefully."""
        empty_reg = SkillRegistry()
        ex = SkillExecutor(empty_reg)
        plan = ex.execute("anything")
        result = plan.results["anything"]
        assert result.status == ExecutionStatus.FAILED

    def test_execute_chain_with_cycle_handling(self) -> None:
        """Executor handles cycle gracefully via error result."""
        reg = SkillRegistry()
        reg.register(
            Skill(name="a", description="a", content="c", dependencies=["b"])
        )
        reg.register(
            Skill(name="b", description="b", content="c", dependencies=["a"])
        )
        ex = SkillExecutor(reg)

        # Direct cycle via get_execution_order
        plan = ex.execute("a", chain=True)
        result = plan.results["a"]
        assert result.status == ExecutionStatus.FAILED

    def test_execute_result_to_dict(self, executor: SkillExecutor) -> None:
        """ExecutionResult.to_dict returns serializable dict."""
        plan = executor.execute("standalone")
        result = plan.results["standalone"]
        d = result.to_dict()
        assert d["skill_name"] == "standalone"
        assert d["status"] == "success"
        assert d["output"] == "Does not depend on anything."
        assert d["error"] is None
        assert isinstance(d["duration_ms"], float)
        assert isinstance(d["timestamp"], float)

    @pytest.mark.parametrize(
        "depth,expected_status",
        [
            (0, ExecutionStatus.SUCCESS),
            (1, ExecutionStatus.SUCCESS),
            (5, ExecutionStatus.SUCCESS),
        ],
    )
    def test_execute_various_chain_depths(
        self,
        executor: SkillExecutor,
        depth: int,
        expected_status: ExecutionStatus,
    ) -> None:
        """Executing with various chain depths succeeds."""
        plan = executor.execute(
            "format-code", chain=True, max_chain_depth=depth
        )
        for r in plan.results.values():
            assert r.status == expected_status


class TestSkillGraphFromRegistryDepGraphs:
    """Verifies graph interactions through the registry."""

    def test_diamond_through_registry(self) -> None:
        """Register a diamond dependency pattern and verify order."""
        reg = SkillRegistry()
        reg.register(Skill(name="base", description="b", content="c"))
        reg.register(
            Skill(
                name="left",
                description="l",
                content="c",
                dependencies=["base"],
            )
        )
        reg.register(
            Skill(
                name="right",
                description="r",
                content="c",
                dependencies=["base"],
            )
        )
        reg.register(
            Skill(
                name="top",
                description="t",
                content="c",
                dependencies=["left", "right"],
            )
        )
        order = reg.get_execution_order()
        assert order.index("base") < order.index("left")
        assert order.index("base") < order.index("right")
        assert order.index("left") < order.index("top")
        assert order.index("right") < order.index("top")
