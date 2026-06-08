"""
Tests for UnifiedAgentRegistry — registration, dispatch, scoring, and statistics.
"""

import pytest

from lyra.agents.base import Agent, AgentCapability
from lyra.agents.unified_registry import AgentMetadata, AgentSource, UnifiedAgentRegistry
from lyra.core.task import Result, Task, TaskType


class MockAgent(Agent):
    """Minimal concrete Agent for registry tests."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

    async def execute(self, task: Task) -> Result:
        return Result(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={"message": "Mock execution"},
        )

    def can_handle(self, task: Task) -> float:
        return 0.8


def _make_cap(
    name: str, task_types: list[TaskType], confidence: float = 0.8,
) -> AgentCapability:
    return AgentCapability(
        name=name,
        description=name,
        task_types=task_types,
        confidence=confidence,
    )


# ===========================================================================
# AgentMetadata
# ===========================================================================

class TestAgentMetadata:

    def test_creation(self):
        agent = MockAgent("test-agent")
        cap = _make_cap("code_gen", [TaskType.CODE_GENERATION])
        metadata = AgentMetadata(
            agent=agent,
            source=AgentSource.LYRA,
            namespace="lyra:test-agent",
            capabilities=[cap],
            languages={"python"},
            frameworks={"pytest"},
            priority=5,
        )
        assert metadata.agent == agent
        assert metadata.source == AgentSource.LYRA
        assert metadata.qualified_name == "lyra:test-agent"
        assert "python" in metadata.languages
        assert "pytest" in metadata.frameworks
        assert metadata.priority == 5

    def test_success_rate_empty(self):
        metadata = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        assert metadata.success_rate == 0.0

    def test_success_rate_partial(self):
        metadata = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        metadata.usage_count = 10
        metadata.success_count = 7
        assert metadata.success_rate == 0.7

    def test_success_rate_perfect(self):
        metadata = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        metadata.usage_count = 5
        metadata.success_count = 5
        assert metadata.success_rate == 1.0

    def test_qualified_name(self):
        agent = MockAgent("my-agent")
        metadata = AgentMetadata(
            agent=agent,
            source=AgentSource.ECC,
            namespace="ecc:my-agent",
            capabilities=[],
        )
        assert metadata.qualified_name == "ecc:my-agent"

    def test_defaults(self):
        metadata = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        assert metadata.languages == set()
        assert metadata.frameworks == set()
        assert metadata.priority == 0
        assert metadata.usage_count == 0
        assert metadata.success_count == 0


# ===========================================================================
# UnifiedAgentRegistry
# ===========================================================================

class TestUnifiedAgentRegistryInit:

    def test_empty_on_creation(self):
        registry = UnifiedAgentRegistry()
        assert registry.agents == {}
        assert registry._capability_index == {}
        assert registry._language_index == {}
        assert registry._framework_index == {}


class TestUnifiedAgentRegistryRegister:

    def test_register_agent(self):
        registry = UnifiedAgentRegistry()
        agent = MockAgent("test-agent")
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(agent, AgentSource.LYRA, [cap])
        assert qn == "lyra:test-agent"
        assert len(registry.agents) == 1

    def test_register_updates_capability_index(self):
        registry = UnifiedAgentRegistry()
        agent = MockAgent("a")
        cap = _make_cap("coding", [TaskType.CODE_GENERATION, TaskType.CODE_REVIEW])
        registry.register(agent, AgentSource.LYRA, [cap])
        assert TaskType.CODE_GENERATION in registry._capability_index
        assert TaskType.CODE_REVIEW in registry._capability_index

    def test_register_updates_language_index(self):
        registry = UnifiedAgentRegistry()
        agent = MockAgent("a")
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(agent, AgentSource.LYRA, [cap], languages={"python", "go"})
        assert "python" in registry._language_index
        assert "go" in registry._language_index

    def test_register_updates_framework_index(self):
        registry = UnifiedAgentRegistry()
        agent = MockAgent("a")
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(agent, AgentSource.LYRA, [cap], frameworks={"django", "flask"})
        assert "django" in registry._framework_index
        assert "flask" in registry._framework_index

    def test_register_multiple_agents_same_task_type(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a1"), AgentSource.LYRA, [cap])
        registry.register(MockAgent("a2"), AgentSource.ECC, [cap])
        assert len(registry._capability_index[TaskType.CODE_GENERATION]) == 2


class TestUnifiedAgentRegistryUnregister:

    def test_unregister_existing(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        assert registry.unregister(qn)
        assert len(registry.agents) == 0

    def test_unregister_nonexistent_returns_false(self):
        registry = UnifiedAgentRegistry()
        assert not registry.unregister("nonexistent")

    def test_unregister_cleans_indexes(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(
            MockAgent("a"), AgentSource.LYRA, [cap],
            languages={"python"}, frameworks={"flask"},
        )
        registry.unregister(qn)
        assert len(registry._capability_index) == 0 or \
            all(len(v) == 0 for v in registry._capability_index.values())
        assert len(registry._language_index) == 0 or \
            all(len(v) == 0 for v in registry._language_index.values())
        assert len(registry._framework_index) == 0 or \
            all(len(v) == 0 for v in registry._framework_index.values())


class TestUnifiedAgentRegistryGet:

    def test_get_existing(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        agent = registry.get(qn)
        assert agent is not None
        assert agent.agent_id == "a"

    def test_get_nonexistent_returns_none(self):
        registry = UnifiedAgentRegistry()
        assert registry.get("lyra:nope") is None


class TestUnifiedAgentRegistryFindCandidates:

    def test_find_by_task_type(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        candidates = registry.find_candidates(task)
        assert len(candidates) == 1
        assert candidates[0].agent.agent_id == "a"

    def test_find_by_task_type_no_match(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        task = Task(type=TaskType.RESEARCH, description="research")
        candidates = registry.find_candidates(task)
        assert candidates == []

    def test_find_by_language(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap], languages={"python"})
        registry.register(MockAgent("b"), AgentSource.LYRA, [cap], languages={"go"})
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        candidates = registry.find_candidates(task, language="python")
        assert len(candidates) == 1
        assert candidates[0].agent.agent_id == "a"

    def test_find_by_language_no_match(self):
        """When no agent has the requested language+capability combo, result is empty."""
        registry = UnifiedAgentRegistry()
        # agent A: python + CODE_GENERATION
        cap_py = _make_cap("py", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("py"), AgentSource.LYRA, [cap_py], languages={"python"})
        # agent B: go + RESEARCH (different capability)
        cap_go = _make_cap("go", [TaskType.RESEARCH])
        registry.register(MockAgent("go"), AgentSource.LYRA, [cap_go], languages={"go"})
        # Ask for CODE_GENERATION + "go" — go IS in the index, but the go-agent
        # doesn't have CODE_GENERATION, so intersection of capability & language is empty.
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        candidates = registry.find_candidates(task, language="go")
        assert candidates == []

    def test_find_by_framework(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("testing", [TaskType.TEST_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap], frameworks={"pytest"})
        task = Task(type=TaskType.TEST_GENERATION, description="test")
        candidates = registry.find_candidates(task, framework="pytest")
        assert len(candidates) == 1
        assert candidates[0].agent.agent_id == "a"

    def test_find_by_framework_no_match(self):
        """When no agent has the requested framework+capability combo, result is empty."""
        registry = UnifiedAgentRegistry()
        # agent A: pytest + TEST_GENERATION
        cap_pt = _make_cap("pt", [TaskType.TEST_GENERATION])
        registry.register(MockAgent("pt"), AgentSource.LYRA, [cap_pt], frameworks={"pytest"})
        # agent B: jest + RESEARCH
        cap_js = _make_cap("js", [TaskType.RESEARCH])
        registry.register(MockAgent("js"), AgentSource.LYRA, [cap_js], frameworks={"jest"})
        # Ask for TEST_GENERATION + "jest" — jest IS in the index, but the jest-agent
        # doesn't have TEST_GENERATION, so intersection is empty.
        task = Task(type=TaskType.TEST_GENERATION, description="test")
        candidates = registry.find_candidates(task, framework="jest")
        assert candidates == []

    def test_find_combined_filters(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(
            MockAgent("a"), AgentSource.LYRA, [cap],
            languages={"python"}, frameworks={"django"},
        )
        registry.register(
            MockAgent("b"), AgentSource.LYRA, [cap],
            languages={"python"}, frameworks={"flask"},
        )
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        candidates = registry.find_candidates(task, language="python", framework="django")
        assert len(candidates) == 1
        assert candidates[0].agent.agent_id == "a"


class TestUnifiedAgentRegistryDispatch:

    def test_dispatch_selects_best_agent(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap], priority=5)
        registry.register(MockAgent("b"), AgentSource.LYRA, [cap], priority=10)
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        agent = registry.dispatch(task)
        assert agent is not None
        assert agent.agent_id == "b"

    def test_dispatch_increments_usage_count(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        registry.dispatch(task)
        assert registry.agents[qn].usage_count == 1

    def test_dispatch_no_candidates_returns_none(self):
        registry = UnifiedAgentRegistry()
        task = Task(type=TaskType.RESEARCH, description="research")
        agent = registry.dispatch(task)
        assert agent is None

    def test_dispatch_with_preferred_source(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("lyra-agent"), AgentSource.LYRA, [cap], priority=5)
        registry.register(MockAgent("ecc-agent"), AgentSource.ECC, [cap], priority=5)
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        agent = registry.dispatch(task, prefer_source=AgentSource.ECC)
        assert agent.agent_id == "ecc-agent"

    def test_dispatch_load_balancing_penalty(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn_a = registry.register(MockAgent("a"), AgentSource.LYRA, [cap], priority=10)
        qn_b = registry.register(MockAgent("b"), AgentSource.LYRA, [cap], priority=10)
        registry.agents[qn_a].usage_count = 15  # triggers penalty
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        agent = registry.dispatch(task)
        assert agent.agent_id == "b"


class TestUnifiedAgentRegistryRecordSuccess:

    def test_record_success_increments(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        registry.record_success(qn)
        assert registry.agents[qn].success_count == 1

    def test_record_success_nonexistent_is_noop(self):
        registry = UnifiedAgentRegistry()
        registry.record_success("lyra:nonexistent")


class TestUnifiedAgentRegistryRecordFailure:

    def test_record_failure_is_currently_noop(self):
        """record_failure is a stub — it should not raise or change state."""
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        registry.record_success(qn)
        previous = registry.agents[qn].success_count
        registry.record_failure(qn)
        assert registry.agents[qn].success_count == previous

    def test_record_failure_nonexistent_is_noop(self):
        registry = UnifiedAgentRegistry()
        registry.record_failure("lyra:nonexistent")


class TestUnifiedAgentRegistryGetStatistics:

    def test_empty_registry(self):
        registry = UnifiedAgentRegistry()
        stats = registry.get_statistics()
        assert stats["total_agents"] == 0
        assert stats["by_source"]["lyra"] == 0
        assert stats["by_source"]["ecc"] == 0
        assert stats["average_success_rate"] == 0.0
        assert stats["total_usage"] == 0

    def test_with_agents(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        qn = registry.register(
            MockAgent("a"), AgentSource.LYRA, [cap],
            languages={"python"},
        )
        registry.agents[qn].usage_count = 3
        registry.agents[qn].success_count = 2

        cap2 = _make_cap("testing", [TaskType.TEST_GENERATION])
        qn2 = registry.register(
            MockAgent("b"), AgentSource.ECC, [cap2],
            languages={"go"},
        )
        registry.agents[qn2].usage_count = 1
        registry.agents[qn2].success_count = 1

        stats = registry.get_statistics()
        assert stats["total_agents"] == 2
        assert stats["by_source"]["lyra"] == 1
        assert stats["by_source"]["ecc"] == 1
        assert "code_generation" in stats["by_capability"]
        assert "test_generation" in stats["by_capability"]
        assert "python" in stats["by_language"]
        assert "go" in stats["by_language"]
        assert stats["total_usage"] == 4
        assert stats["average_success_rate"] == pytest.approx(0.83333, rel=0.01)


class TestUnifiedAgentRegistryListAgents:

    def test_list_all(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        registry.register(MockAgent("b"), AgentSource.ECC, [cap])
        assert len(registry.list_agents()) == 2

    def test_list_by_source(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap])
        registry.register(MockAgent("b"), AgentSource.ECC, [cap])
        lyra_agents = registry.list_agents(source=AgentSource.LYRA)
        assert len(lyra_agents) == 1
        assert lyra_agents[0].agent.agent_id == "a"

    def test_list_by_language(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(MockAgent("a"), AgentSource.LYRA, [cap], languages={"python"})
        registry.register(MockAgent("b"), AgentSource.LYRA, [cap], languages={"go"})
        agents = registry.list_agents(language="python")
        assert len(agents) == 1
        assert agents[0].agent.agent_id == "a"

    def test_list_empty_registry(self):
        registry = UnifiedAgentRegistry()
        assert registry.list_agents() == []


class TestUnifiedAgentRegistryClear:

    def test_clear_empties_everything(self):
        registry = UnifiedAgentRegistry()
        cap = _make_cap("coding", [TaskType.CODE_GENERATION])
        registry.register(
            MockAgent("a"), AgentSource.LYRA, [cap],
            languages={"python"},
        )
        registry.clear()
        assert registry.agents == {}
        assert registry._capability_index == {}
        assert registry._language_index == {}
        assert registry._framework_index == {}


class TestUnifiedAgentRegistryScoring:

    def test_score_includes_priority(self):
        registry = UnifiedAgentRegistry()
        meta = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
            priority=3,
        )
        task = Task(type=TaskType.GENERIC, description="t")
        score = registry._score_agent(meta, task, None)
        assert score == 30.0

    def test_score_includes_success_rate(self):
        registry = UnifiedAgentRegistry()
        meta = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        meta.usage_count = 10
        meta.success_count = 8
        task = Task(type=TaskType.GENERIC, description="t")
        score = registry._score_agent(meta, task, None)
        assert score == 4.0

    def test_score_preferred_source_bonus(self):
        registry = UnifiedAgentRegistry()
        meta = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.ECC,
            namespace="ecc:a",
            capabilities=[],
        )
        task = Task(type=TaskType.GENERIC, description="t")
        score = registry._score_agent(meta, task, AgentSource.ECC)
        assert score == 20.0

    def test_score_load_balancing_penalty(self):
        registry = UnifiedAgentRegistry()
        meta = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        meta.usage_count = 50
        task = Task(type=TaskType.GENERIC, description="t")
        score = registry._score_agent(meta, task, None)
        assert score == -5.0

    def test_score_no_penalty_below_threshold(self):
        registry = UnifiedAgentRegistry()
        meta = AgentMetadata(
            agent=MockAgent("a"),
            source=AgentSource.LYRA,
            namespace="lyra:a",
            capabilities=[],
        )
        meta.usage_count = 10
        task = Task(type=TaskType.GENERIC, description="t")
        score = registry._score_agent(meta, task, None)
        assert score == 0.0


class TestAgentSourceEnum:

    def test_values(self):
        assert AgentSource.LYRA.value == "lyra"
        assert AgentSource.ECC.value == "ecc"
