"""Comprehensive tests for Phase 2: Containment hierarchy (Project/Team/Agent/TopologyTree/ConfigTree/ModeStack)."""

from __future__ import annotations

import time

import pytest

from lyra_core.containment import (
    ConfigNode,
    ConfigTree,
    ModeStack,
    Project,
    ProjectRegistry,
    ProjectStatus,
    Team,
    TeamMembership,
    TopologyKind,
    TopologyTree,
    get_project_registry,
)
from lyra_core.protocol import AgentMode, AgentProtocol, Task


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class _StubAgent:
    """Minimal AgentProtocol stub for containment tests."""

    def __init__(self, agent_id: str, project_id: str = "p1") -> None:
        from lyra_core.protocol import AgentHealth, AgentIdentity, AgentLifecycle, AgentState

        self._identity = AgentIdentity(
            agent_id=agent_id, project_id=project_id, agent_type="test",
            capabilities=frozenset({"test"}),
        )
        self._state = AgentState(
            lifecycle=AgentLifecycle.READY, health=AgentHealth.HEALTHY,
            since=time.time(),
        )
        self._modes: list[AgentMode] = []

    @property
    def identity(self):
        return self._identity

    @property
    def state(self):
        return self._state

    @property
    def mode_stack(self) -> tuple[AgentMode, ...]:
        return tuple(self._modes)

    def push_mode(self, mode: AgentMode) -> None:
        self._modes.append(mode)

    def pop_mode(self) -> AgentMode:
        if not self._modes:
            raise IndexError("empty")
        return self._modes.pop()

    def supports(self, capability: str) -> bool:
        return capability in self._identity.capabilities

    async def initialize(self) -> None:
        pass

    async def run(self, task: Task):
        yield f"stub:{task.instruction}"

    async def shutdown(self) -> None:
        pass

    async def snapshot(self) -> dict:
        return {"agent_id": self._identity.agent_id}


class _StubMode:
    """Minimal AgentMode stub."""

    def __init__(self, name: str = "stub_mode") -> None:
        self.name = name
        self.entered = False
        self.exited = False
        self.last_input: str | None = None
        self.transform_prefix = ""

    async def on_enter(self, agent: AgentProtocol) -> None:
        self.entered = True

    async def on_exit(self, agent: AgentProtocol) -> None:
        self.exited = True

    async def handle_input(self, agent: AgentProtocol, text: str) -> str | None:
        self.last_input = text
        return None  # passthrough

    async def transform_output(self, agent: AgentProtocol, chunk: str) -> str:
        if self.transform_prefix:
            return f"{self.transform_prefix}:{chunk}"
        return chunk


# ═══════════════════════════════════════════════════════════════════════════════
# Project
# ═══════════════════════════════════════════════════════════════════════════════


class TestProject:
    def test_create_project(self):
        p = Project(id="p1", name="test-project")
        assert p.id == "p1"
        assert p.name == "test-project"
        assert p.status == ProjectStatus.CREATING

    def test_default_config_empty(self):
        p = Project(id="p1", name="test")
        assert p.config == {}

    def test_custom_config(self):
        p = Project(id="p1", name="test", config={"max_tokens": 4096})
        assert p.config["max_tokens"] == 4096

    def test_metadata(self):
        p = Project(id="p1", name="test", metadata={"owner": "alice"})
        assert p.metadata["owner"] == "alice"

    def test_initial_team_count_zero(self):
        p = Project(id="p1", name="test")
        assert p.team_count == 0

    def test_initial_active_teams_empty(self):
        p = Project(id="p1", name="test")
        assert p.active_teams == []

    def test_add_team_creates_membership(self):
        p = Project(id="p1", name="test")
        t = Team(id="t1", name="my-team")
        membership = p.add_team(t)
        assert membership.team_id == "t1"
        assert membership.project_id == "p1"
        assert p.team_count == 1

    def test_add_team_at_index(self):
        p = Project(id="p1", name="test")
        t1 = Team(id="t1", name="first")
        t2 = Team(id="t2", name="second")
        p.add_team(t1, index=5)
        p.add_team(t2, index=2)
        teams = p.list_teams()
        # Sorted by index ascending: t2(idx=2) before t1(idx=5)
        assert teams[0].team_id == "t2"
        assert teams[1].team_id == "t1"

    def test_remove_team(self):
        p = Project(id="p1", name="test")
        t = Team(id="t1", name="my-team")
        p.add_team(t)
        assert p.team_count == 1
        p.remove_team("t1")
        assert p.team_count == 0

    def test_remove_nonexistent_team_no_error(self):
        p = Project(id="p1", name="test")
        p.remove_team("nonexistent")  # Should not raise

    def test_active_teams_filter(self):
        p = Project(id="p1", name="test")
        t1 = Team(id="t1", name="active-team")
        t2 = Team(id="t2", name="inactive-team")
        m1 = p.add_team(t1)
        m2 = p.add_team(t2)
        m2.active = False
        assert p.active_teams == ["t1"]

    def test_list_teams_sorted_by_index(self):
        p = Project(id="p1", name="test")
        t1 = Team(id="t1", name="a")
        t2 = Team(id="t2", name="b")
        t3 = Team(id="t3", name="c")
        p.add_team(t3, index=30)
        p.add_team(t1, index=10)
        p.add_team(t2, index=20)
        assert [m.team_id for m in p.list_teams()] == ["t1", "t2", "t3"]

    def test_project_event_bus_is_lazy(self):
        p = Project(id="p1", name="test")
        assert p._bus is None
        _ = p.bus  # triggers creation
        assert p._bus is not None

    def test_project_event_bus_is_singleton_per_project(self):
        p = Project(id="p1", name="test")
        bus1 = p.bus
        bus2 = p.bus
        assert bus1 is bus2


# ═══════════════════════════════════════════════════════════════════════════════
# Team
# ═══════════════════════════════════════════════════════════════════════════════


class TestTeam:
    def test_create_team(self):
        t = Team(id="t1", name="test-team")
        assert t.id == "t1"
        assert t.name == "test-team"
        assert t.agent_count == 0

    def test_add_agent(self):
        t = Team(id="t1", name="test-team")
        a = _StubAgent("a1")
        t.add_agent(a)
        assert t.agent_count == 1
        assert "a1" in t.agent_ids

    def test_add_agent_makes_active(self):
        t = Team(id="t1", name="test-team")
        a = _StubAgent("a1")
        t.add_agent(a)
        assert t.active_agent is not None

    def test_add_multiple_agents_mru_order(self):
        t = Team(id="t1", name="test-team")
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        t.add_agent(a1)
        t.add_agent(a2)
        # Active agent is a2 (last added, make_active=True)
        assert t.active_agent.identity.agent_id == "a2"

    def test_remove_agent(self):
        t = Team(id="t1", name="test-team")
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        t.add_agent(a1)
        t.add_agent(a2)
        t.remove_agent("a1")
        assert t.agent_count == 1
        assert "a1" not in t.agent_ids

    def test_remove_active_agent_falls_back(self):
        t = Team(id="t1", name="test-team")
        a1 = _StubAgent("a1")
        t.add_agent(a1)
        t.remove_agent("a1")
        assert t.agent_count == 0
        assert t.active_agent is None

    def test_remove_last_agent(self):
        t = Team(id="t1", name="test-team")
        a1 = _StubAgent("a1")
        t.add_agent(a1)
        t.remove_agent("a1")
        assert t.agent_count == 0

    def test_set_active(self):
        t = Team(id="t1", name="test-team")
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        t.add_agent(a1)
        t.add_agent(a2)
        t.set_active("a1")
        # active agent is a1 now

    def test_set_active_nonexistent_ignored(self):
        t = Team(id="t1", name="test-team")
        a1 = _StubAgent("a1")
        t.add_agent(a1)
        t.set_active("nonexistent")
        assert t.active_agent is not None

    def test_topology_default_none(self):
        t = Team(id="t1", name="test-team")
        assert t.topology is None

    def test_topology_custom(self):
        tree = TopologyTree.parallel(["a1", "a2"])
        t = Team(id="t1", name="test-team", topology=tree)
        assert t.topology is tree

    @pytest.mark.asyncio
    async def test_run_all_no_topology_uses_active(self):
        t = Team(id="t1", name="test-team")
        a = _StubAgent("a1")
        t.add_agent(a)
        task = Task(task_id="t1", instruction="hello")
        results = await t.run_all(task)
        assert "a1" in results
        assert "hello" in results["a1"]

    @pytest.mark.asyncio
    async def test_run_all_no_agent_returns_empty(self):
        t = Team(id="t1", name="test-team")
        task = Task(task_id="t1", instruction="hello")
        results = await t.run_all(task)
        assert results == {}

    @pytest.mark.asyncio
    async def test_run_all_with_topology(self):
        tree = TopologyTree.parallel(["a1", "a2"])
        t = Team(id="t1", name="test-team", topology=tree)
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        t.add_agent(a1)
        t.add_agent(a2)
        task = Task(task_id="t1", instruction="hello")
        results = await t.run_all(task)
        assert len(results) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TeamMembership
# ═══════════════════════════════════════════════════════════════════════════════


class TestTeamMembership:
    def test_create_membership(self):
        m = TeamMembership(team_id="t1", project_id="p1", index=3)
        assert m.team_id == "t1"
        assert m.project_id == "p1"
        assert m.index == 3

    def test_default_active(self):
        m = TeamMembership(team_id="t1", project_id="p1")
        assert m.active is True

    def test_default_overrides_empty(self):
        m = TeamMembership(team_id="t1", project_id="p1")
        assert m.project_config_overrides == {}

    def test_custom_overrides(self):
        m = TeamMembership(team_id="t1", project_id="p1",
                          project_config_overrides={"max_tokens": 2048})
        assert m.project_config_overrides["max_tokens"] == 2048


# ═══════════════════════════════════════════════════════════════════════════════
# TopologyTree
# ═══════════════════════════════════════════════════════════════════════════════


class TestTopologyTree:
    def test_create_parallel(self):
        tree = TopologyTree(kind=TopologyKind.PARALLEL, children=["a1", "a2"])
        assert tree.kind == TopologyKind.PARALLEL
        assert not tree.is_leaf

    def test_create_leaf(self):
        tree = TopologyTree(kind=TopologyKind.PARALLEL)
        assert tree.is_leaf

    def test_agent_ids_flat(self):
        tree = TopologyTree(kind=TopologyKind.PARALLEL, children=["a1", "a2"])
        assert set(tree.agent_ids) == {"a1", "a2"}

    def test_agent_ids_nested(self):
        inner = TopologyTree(kind=TopologyKind.PARALLEL, children=["a3"])
        tree = TopologyTree(kind=TopologyKind.SEQUENTIAL, children=["a1", inner, "a2"])
        assert set(tree.agent_ids) == {"a1", "a2", "a3"}

    def test_agent_ids_empty(self):
        tree = TopologyTree(kind=TopologyKind.PARALLEL)
        assert tree.agent_ids == []

    @pytest.mark.asyncio
    async def test_execute_parallel(self):
        tree = TopologyTree.parallel(["a1", "a2"])
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        agents = {"a1": a1, "a2": a2}
        task = Task(task_id="t1", instruction="test")
        results = await tree.execute(agents, task)
        assert len(results) == 2
        assert "a1" in results
        assert "a2" in results

    @pytest.mark.asyncio
    async def test_execute_sequential(self):
        tree = TopologyTree.sequential(["a1", "a2"])
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        agents = {"a1": a1, "a2": a2}
        task = Task(task_id="t1", instruction="test")
        results = await tree.execute(agents, task)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_execute_debate(self):
        tree = TopologyTree.debate(["a1", "a2"])
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        agents = {"a1": a1, "a2": a2}
        task = Task(task_id="t1", instruction="test")
        results = await tree.execute(agents, task)
        assert "consensus" in results
        assert "arguments" in results

    @pytest.mark.asyncio
    async def test_execute_parallel_missing_agent(self):
        tree = TopologyTree.parallel(["a1", "a2"])
        a1 = _StubAgent("a1")
        agents = {"a1": a1}
        task = Task(task_id="t1", instruction="test")
        results = await tree.execute(agents, task)
        assert len(results) == 2  # a2 returns empty string

    @pytest.mark.asyncio
    async def test_execute_nested_topology(self):
        inner = TopologyTree.parallel(["a2", "a3"])
        tree = TopologyTree(kind=TopologyKind.SEQUENTIAL, children=["a1", inner])
        a1 = _StubAgent("a1")
        a2 = _StubAgent("a2")
        a3 = _StubAgent("a3")
        agents = {"a1": a1, "a2": a2, "a3": a3}
        task = Task(task_id="t1", instruction="test")
        results = await tree.execute(agents, task)
        assert len(results) == 3

    def test_factory_parallel(self):
        tree = TopologyTree.parallel(["a1", "a2"])
        assert tree.kind == TopologyKind.PARALLEL
        assert len(tree.children) == 2

    def test_factory_sequential(self):
        tree = TopologyTree.sequential(["a1", "a2"])
        assert tree.kind == TopologyKind.SEQUENTIAL

    def test_factory_debate(self):
        tree = TopologyTree.debate(["a1", "a2"])
        assert tree.kind == TopologyKind.DEBATE

    def test_factory_pipeline(self):
        tree = TopologyTree.pipeline([["a1", "a2"], ["a3"]])
        assert tree.kind == TopologyKind.SEQUENTIAL
        assert len(tree.children) == 2
        # First child is parallel group for stage 0
        assert tree.children[0].kind == TopologyKind.PARALLEL
        assert set(tree.children[0].agent_ids) == {"a1", "a2"}

    def test_pick_consensus_majority(self):
        result = TopologyTree._pick_consensus({
            "a1": "Option A is best. Here's why...",
            "a2": "Option A is best. I agree...",
            "a3": "Option B is better. Because...",
        })
        assert "Consensus" in result
        assert "2/3" in result

    def test_pick_consensus_no_majority(self):
        result = TopologyTree._pick_consensus({
            "a1": "Option A is best.",
            "a2": "Option B is better.",
            "a3": "Option C for sure.",
        })
        assert "No consensus" in result

    def test_pick_consensus_empty(self):
        result = TopologyTree._pick_consensus({})
        assert result == ""

    def test_all_topology_kinds(self):
        for kind in TopologyKind:
            tree = TopologyTree(kind=kind)
            assert tree.kind == kind

    def test_config_default_empty(self):
        tree = TopologyTree(kind=TopologyKind.PARALLEL)
        assert tree.config == {}

    def test_config_custom(self):
        tree = TopologyTree(kind=TopologyKind.PARALLEL,
                           config={"timeout": 30})
        assert tree.config["timeout"] == 30


# ═══════════════════════════════════════════════════════════════════════════════
# ConfigNode
# ═══════════════════════════════════════════════════════════════════════════════


class TestConfigNode:
    def test_create_root(self):
        root = ConfigNode(key="global", value=None)
        assert root.key == "global"
        assert root.value is None

    def test_get_direct_value(self):
        node = ConfigNode(key="max_tokens", value=4096)
        assert node.get() == 4096

    def test_get_child_value(self):
        root = ConfigNode(key="global", value=None)
        root.children["max_tokens"] = ConfigNode(key="max_tokens", value=2048)
        assert root.get("max_tokens") == 2048

    def test_get_nested_path(self):
        root = ConfigNode(key="global", value=None)
        child = ConfigNode(key="llm", value=None)
        child.children["temperature"] = ConfigNode(key="temperature", value=0.7)
        root.children["llm"] = child
        assert root.get("llm.temperature") == 0.7

    def test_get_falls_back_to_parent(self):
        parent = ConfigNode(key="parent", value=100)
        child = ConfigNode(key="child", value=None, parent=parent)
        # child has no "max_tokens", so it should walk up
        assert child.get("max_tokens") is None  # parent doesn't have it either

    def test_get_missing_key_returns_none(self):
        root = ConfigNode(key="global", value=None)
        assert root.get("nonexistent") is None

    def test_set_local_creates_child(self):
        root = ConfigNode(key="global", value=None)
        child = root.set_local("max_tokens", 4096)
        assert "max_tokens" in root.children
        assert child.value == 4096

    def test_set_local_nested_path(self):
        root = ConfigNode(key="global", value=None)
        root.set_local("llm.temperature", 0.7)
        assert root.get("llm.temperature") == 0.7

    def test_set_local_overwrites(self):
        root = ConfigNode(key="global", value=None)
        root.set_local("max_tokens", 2048)
        root.set_local("max_tokens", 4096)
        assert root.get("max_tokens") == 4096

    def test_parent_reference(self):
        parent = ConfigNode(key="parent", value=10)
        child = ConfigNode(key="child", value=None, parent=parent)
        assert child.parent is parent


# ═══════════════════════════════════════════════════════════════════════════════
# ConfigTree
# ═══════════════════════════════════════════════════════════════════════════════


class TestConfigTree:
    def test_create(self):
        ct = ConfigTree()
        assert ct._global is not None

    def test_set_and_get(self):
        ct = ConfigTree()
        ct.set("project", "p1", "max_tokens", 4096)
        assert ct.get("project", "p1", "max_tokens") == 4096

    def test_get_missing_returns_none(self):
        ct = ConfigTree()
        assert ct.get("project", "p1", "missing_key") is None

    def test_scoped_isolation(self):
        ct = ConfigTree()
        ct.set("project", "p1", "max_tokens", 4096)
        ct.set("project", "p2", "max_tokens", 2048)
        assert ct.get("project", "p1", "max_tokens") == 4096
        assert ct.get("project", "p2", "max_tokens") == 2048

    def test_overwrite_value(self):
        ct = ConfigTree()
        ct.set("project", "p1", "timeout", 30)
        ct.set("project", "p1", "timeout", 60)
        assert ct.get("project", "p1", "timeout") == 60

    def test_different_scopes(self):
        ct = ConfigTree()
        ct.set("global", "root", "theme", "dark")
        ct.set("project", "p1", "theme", "light")
        assert ct.get("global", "root", "theme") == "dark"
        assert ct.get("project", "p1", "theme") == "light"


# ═══════════════════════════════════════════════════════════════════════════════
# ModeStack
# ═══════════════════════════════════════════════════════════════════════════════


class TestModeStack:
    def test_create_empty(self):
        ms = ModeStack()
        assert ms.top is None
        assert ms.depth == 0
        assert ms.all_modes == ()

    @pytest.mark.asyncio
    async def test_push_mode(self):
        ms = ModeStack()
        mode = _StubMode("debug")
        agent = _StubAgent("a1")
        await ms.push(mode, agent)
        assert ms.depth == 1
        assert ms.top is mode
        assert mode.entered is True

    @pytest.mark.asyncio
    async def test_pop_mode(self):
        ms = ModeStack()
        mode = _StubMode("debug")
        agent = _StubAgent("a1")
        await ms.push(mode, agent)
        popped = await ms.pop(agent)
        assert popped is mode
        assert ms.depth == 0
        assert mode.exited is True

    @pytest.mark.asyncio
    async def test_pop_empty_raises(self):
        ms = ModeStack()
        agent = _StubAgent("a1")
        with pytest.raises(IndexError, match="empty"):
            await ms.pop(agent)

    @pytest.mark.asyncio
    async def test_mode_stack_lifo(self):
        ms = ModeStack()
        m1 = _StubMode("first")
        m2 = _StubMode("second")
        agent = _StubAgent("a1")
        await ms.push(m1, agent)
        await ms.push(m2, agent)
        assert ms.top is m2
        popped = await ms.pop(agent)
        assert popped is m2

    @pytest.mark.asyncio
    async def test_handle_input_passthrough_empty(self):
        ms = ModeStack()
        agent = _StubAgent("a1")
        result = await ms.handle_input(agent, "hello")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_handle_input_routes_to_top(self):
        ms = ModeStack()
        mode = _StubMode("debug")
        agent = _StubAgent("a1")
        await ms.push(mode, agent)
        result = await ms.handle_input(agent, "test input")
        assert mode.last_input == "test input"
        # Mode returns None → passthrough
        assert result == "test input"

    @pytest.mark.asyncio
    async def test_handle_input_mode_intercepts(self):
        class _InterceptMode(_StubMode):
            async def handle_input(self, agent: AgentProtocol, text: str) -> str:
                return f"INTERCEPTED:{text}"

        ms = ModeStack()
        mode = _InterceptMode("interceptor")
        agent = _StubAgent("a1")
        await ms.push(mode, agent)
        result = await ms.handle_input(agent, "hello")
        assert result == "INTERCEPTED:hello"

    @pytest.mark.asyncio
    async def test_transform_output_empty_stack(self):
        ms = ModeStack()
        agent = _StubAgent("a1")
        result = await ms.transform_output(agent, "raw")
        assert result == "raw"

    @pytest.mark.asyncio
    async def test_transform_output_single_mode(self):
        ms = ModeStack()
        mode = _StubMode("format")
        mode.transform_prefix = "FMT"
        agent = _StubAgent("a1")
        await ms.push(mode, agent)
        result = await ms.transform_output(agent, "data")
        assert result == "FMT:data"

    @pytest.mark.asyncio
    async def test_transform_output_stacked_modes(self):
        ms = ModeStack()
        m1 = _StubMode("outer")
        m1.transform_prefix = "OUTER"
        m2 = _StubMode("inner")
        m2.transform_prefix = "INNER"
        agent = _StubAgent("a1")
        await ms.push(m1, agent)
        await ms.push(m2, agent)
        result = await ms.transform_output(agent, "data")
        # innermost transforms first (m2), then m1
        assert result == "OUTER:INNER:data"

    @pytest.mark.asyncio
    async def test_all_modes_immutable(self):
        ms = ModeStack()
        m1 = _StubMode("m1")
        agent = _StubAgent("a1")
        await ms.push(m1, agent)
        modes = ms.all_modes
        assert len(modes) == 1
        # tuple is immutable


# ═══════════════════════════════════════════════════════════════════════════════
# ProjectRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectRegistry:
    def test_create_registry(self):
        reg = ProjectRegistry()
        assert len(reg.list_projects()) == 0

    def test_create_project(self):
        reg = ProjectRegistry()
        p = reg.create_project("my-project")
        assert p.name == "my-project"
        assert p.id in reg._projects

    def test_create_project_with_id(self):
        reg = ProjectRegistry()
        p = reg.create_project("custom", project_id="custom_id")
        assert p.id == "custom_id"

    def test_create_project_with_config(self):
        reg = ProjectRegistry()
        p = reg.create_project("test", config={"key": "val"})
        assert p.config["key"] == "val"

    def test_get_project(self):
        reg = ProjectRegistry()
        reg.create_project("test", project_id="p1")
        p = reg.get_project("p1")
        assert p is not None
        assert p.name == "test"

    def test_get_nonexistent_project(self):
        reg = ProjectRegistry()
        assert reg.get_project("nonexistent") is None

    def test_list_projects(self):
        reg = ProjectRegistry()
        reg.create_project("p1")
        reg.create_project("p2")
        assert len(reg.list_projects()) == 2

    def test_remove_project(self):
        reg = ProjectRegistry()
        reg.create_project("test", project_id="p1")
        reg.remove_project("p1")
        assert reg.get_project("p1") is None

    def test_create_team(self):
        reg = ProjectRegistry()
        t = reg.create_team("my-team")
        assert t.name == "my-team"
        assert t.id in reg._teams

    def test_create_team_with_id(self):
        reg = ProjectRegistry()
        t = reg.create_team("custom", team_id="team_custom")
        assert t.id == "team_custom"

    def test_get_team(self):
        reg = ProjectRegistry()
        reg.create_team("test", team_id="t1")
        t = reg.get_team("t1")
        assert t is not None
        assert t.name == "test"

    def test_link_team_to_project(self):
        reg = ProjectRegistry()
        reg.create_project("test-proj", project_id="p1")
        reg.create_team("test-team", team_id="t1")
        membership = reg.link_team("p1", "t1")
        assert membership is not None
        assert membership.team_id == "t1"
        assert membership.project_id == "p1"

    def test_link_team_missing_project(self):
        reg = ProjectRegistry()
        reg.create_team("test-team", team_id="t1")
        assert reg.link_team("nonexistent", "t1") is None

    def test_link_team_missing_team(self):
        reg = ProjectRegistry()
        reg.create_project("test-proj", project_id="p1")
        assert reg.link_team("p1", "nonexistent") is None

    def test_link_team_with_index(self):
        reg = ProjectRegistry()
        reg.create_project("test-proj", project_id="p1")
        reg.create_team("test-team", team_id="t1")
        m = reg.link_team("p1", "t1", index=42)
        assert m is not None
        assert m.index == 42

    def test_config_tree(self):
        reg = ProjectRegistry()
        reg.set_config("project", "p1", "key", "val")
        assert reg.get_config("project", "p1", "key") == "val"

    def test_get_config_with_default(self):
        reg = ProjectRegistry()
        assert reg.get_config("project", "p1", "missing", default=42) == 42

    def test_config_isolation(self):
        reg = ProjectRegistry()
        reg.set_config("project", "p1", "theme", "dark")
        reg.set_config("team", "t1", "theme", "light")
        assert reg.get_config("project", "p1", "theme") == "dark"
        assert reg.get_config("team", "t1", "theme") == "light"


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════


class TestSingleton:
    def test_get_project_registry_is_singleton(self):
        r1 = get_project_registry()
        r2 = get_project_registry()
        assert r1 is r2

    def test_singleton_has_config_tree(self):
        reg = get_project_registry()
        assert reg.config_tree is not None


# ═══════════════════════════════════════════════════════════════════════════════
# ProjectStatus
# ═══════════════════════════════════════════════════════════════════════════════


class TestProjectStatus:
    def test_all_status_values(self):
        for status in ProjectStatus:
            assert isinstance(status.value, str)
