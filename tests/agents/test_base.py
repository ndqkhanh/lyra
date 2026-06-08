"""
Tests for agent base classes — AgentCapability, Message, and the abstract Agent.

Uses a local ``ConcreteAgent`` subclass for testing abstract methods.
"""

import asyncio

import pytest

from lyra.agents.base import Agent, AgentCapability, AgentStatus, Message, MessageType
from lyra.core.task import Result, Task, TaskType
from lyra.memory import MemoryType, RetrievalStrategy


# ---------------------------------------------------------------------------
# Concrete subclass used throughout
# ---------------------------------------------------------------------------

class ConcreteAgent(Agent):
    """Minimal concrete Agent subclass for testing."""

    async def execute(self, task: Task) -> Result:
        self.status = AgentStatus.BUSY
        self.current_task = task
        await asyncio.sleep(0.01)
        result = Result(
            task_id=task.task_id,
            success=True,
            data="executed",
            agent_id=self.agent_id,
        )
        self.record_execution(result)
        self.status = AgentStatus.IDLE
        self.current_task = None
        return result

    def can_handle(self, task: Task) -> float:
        cap = self.get_capability(task.type)
        return cap.confidence if cap else 0.0


# ===========================================================================
# AgentCapability
# ===========================================================================

class TestAgentCapability:

    def test_valid_creation(self):
        cap = AgentCapability(
            name="test",
            description="A test capability",
            task_types=[TaskType.CODE_GENERATION],
            confidence=0.85,
        )
        assert cap.name == "test"
        assert cap.description == "A test capability"
        assert cap.task_types == [TaskType.CODE_GENERATION]
        assert cap.confidence == 0.85
        assert cap.estimated_cost == 0.0
        assert cap.estimated_time == 0.0
        assert cap.required_tools == []

    def test_confidence_validation_high(self):
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            AgentCapability(
                name="bad", description="bad", task_types=[TaskType.GENERIC], confidence=1.5,
            )

    def test_confidence_validation_low(self):
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            AgentCapability(
                name="bad", description="bad", task_types=[TaskType.GENERIC], confidence=-0.1,
            )

    def test_confidence_boundaries(self):
        cap0 = AgentCapability("zero", "", [TaskType.GENERIC], confidence=0.0)
        assert cap0.confidence == 0.0
        cap1 = AgentCapability("one", "", [TaskType.GENERIC], confidence=1.0)
        assert cap1.confidence == 1.0


# ===========================================================================
# Message
# ===========================================================================

class TestMessage:

    def test_creation_with_all_fields(self):
        msg = Message(
            from_agent="a1",
            to_agent="a2",
            message_type=MessageType.RESULT,
            content={"key": "value"},
            correlation_id="corr-1",
        )
        assert msg.from_agent == "a1"
        assert msg.to_agent == "a2"
        assert msg.message_type == MessageType.RESULT
        assert msg.content == {"key": "value"}
        assert msg.correlation_id == "corr-1"

    def test_default_timestamp(self):
        msg = Message(
            from_agent="a1",
            to_agent="a2",
            message_type=MessageType.PROGRESS,
            content={},
        )
        assert msg.timestamp is not None

    def test_message_type_values(self):
        assert MessageType.PROGRESS.value == "progress"
        assert MessageType.HELP_REQUEST.value == "help_request"
        assert MessageType.RESULT.value == "result"
        assert MessageType.ERROR.value == "error"
        assert MessageType.STATUS_UPDATE.value == "status_update"


# ===========================================================================
# Agent (via ConcreteAgent)
# ===========================================================================

class TestAgentInit:

    def test_default_initialisation(self):
        agent = ConcreteAgent("my-agent")
        assert agent.agent_id == "my-agent"
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None
        assert agent.capabilities == []
        assert len(agent.execution_history) == 0
        assert agent.metadata == {}

    def test_with_capabilities(self):
        caps = [
            AgentCapability("c1", "desc", [TaskType.CODE_GENERATION], confidence=0.9),
        ]
        agent = ConcreteAgent("cap-agent", capabilities=caps)
        assert len(agent.capabilities) == 1
        assert agent.capabilities[0].name == "c1"

    def test_memory_components_initialised(self):
        agent = ConcreteAgent("mem-agent")
        assert agent.short_term_memory is not None
        assert agent.long_term_memory is not None
        assert agent.memory_retriever is not None
        assert agent.memory_consolidator is not None


class TestAgentStatus:

    @pytest.mark.asyncio
    async def test_lifecycle(self):
        agent = ConcreteAgent("lifecycle")
        assert agent.status == AgentStatus.IDLE

        task = Task(type=TaskType.GENERIC, description="lifecycle task")
        result = await agent.execute(task)

        assert result.success
        # After execute the agent should be back to IDLE
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None


class TestAgentExecute:

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        agent = ConcreteAgent("exec-agent")
        task = Task(type=TaskType.GENERIC, description="exec task")
        result = await agent.execute(task)

        assert result.success
        assert result.agent_id == "exec-agent"
        assert result.task_id == task.task_id
        assert result.data == "executed"

    @pytest.mark.asyncio
    async def test_records_in_history(self):
        agent = ConcreteAgent("hist-agent")
        task = Task(type=TaskType.GENERIC, description="hist task")
        await agent.execute(task)

        assert len(agent.execution_history) == 1
        assert agent.execution_history[0].success

    @pytest.mark.asyncio
    async def test_remembers_current_task(self):
        agent = ConcreteAgent("current-agent")
        task = Task(type=TaskType.GENERIC, description="current task")
        await agent.execute(task)
        # After execution, current_task should be cleared
        assert agent.current_task is None


class TestAgentCanHandle:

    def test_returns_zero_for_no_matching_capability(self):
        agent = ConcreteAgent("no-cap")
        task = Task(type=TaskType.CODE_REVIEW, description="review")
        assert agent.can_handle(task) == 0.0

    def test_returns_confidence_from_capability(self):
        caps = [
            AgentCapability("c", "desc", [TaskType.CODE_GENERATION], confidence=0.75),
        ]
        agent = ConcreteAgent("cap-agent", capabilities=caps)
        task = Task(type=TaskType.CODE_GENERATION, description="gen")
        assert agent.can_handle(task) == 0.75


class TestAgentGetCapability:

    def test_finds_matching_capability(self):
        caps = [
            AgentCapability("c1", "desc", [TaskType.CODE_GENERATION, TaskType.CODE_REVIEW]),
        ]
        agent = ConcreteAgent("a", capabilities=caps)
        cap = agent.get_capability(TaskType.CODE_REVIEW)
        assert cap is not None
        assert cap.name == "c1"

    def test_returns_none_when_not_found(self):
        caps = [AgentCapability("c1", "desc", [TaskType.CODE_GENERATION])]
        agent = ConcreteAgent("a", capabilities=caps)
        assert agent.get_capability(TaskType.RESEARCH) is None


class TestAgentExecutionHistory:

    def test_record_and_retrieve(self):
        agent = ConcreteAgent("hist")
        r1 = Result(task_id="t1", success=True, data="d1", agent_id="hist")
        r2 = Result(task_id="t2", success=False, error="err", agent_id="hist")
        agent.record_execution(r1)
        agent.record_execution(r2)
        assert len(agent.execution_history) == 2

    def test_caps_at_100(self):
        agent = ConcreteAgent("cap-agent")
        for i in range(150):
            agent.record_execution(
                Result(task_id=f"t{i}", success=True, agent_id="cap-agent"),
            )
        assert len(agent.execution_history) == 100

    def test_success_rate(self):
        agent = ConcreteAgent("sr-agent")
        for i in range(7):
            agent.record_execution(Result(task_id=f"s{i}", success=True, agent_id="sr-agent"))
        for i in range(3):
            agent.record_execution(
                Result(task_id=f"f{i}", success=False, error="fail", agent_id="sr-agent"),
            )
        assert agent.get_success_rate() == 0.7  # 7/10

    def test_success_rate_empty(self):
        agent = ConcreteAgent("empty-agent")
        assert agent.get_success_rate() == 0.0

    def test_success_rate_noop_filter(self):
        """get_success_rate with a task_type that doesn't filter — all results included."""
        agent = ConcreteAgent("filter-agent")
        for _ in range(5):
            agent.record_execution(Result(task_id="t", success=True, agent_id="filter-agent"))
        assert agent.get_success_rate(TaskType.GENERIC) == 1.0


class TestAgentSendReceiveMessage:

    @pytest.mark.asyncio
    async def test_send_message_creates_and_prints(self, capsys):
        agent = ConcreteAgent("sender")
        # send_message creates a Message and prints (does not enqueue)
        await agent.send_message("receiver", MessageType.PROGRESS, {"pct": 50})
        captured = capsys.readouterr()
        assert "[sender] -> [receiver]" in captured.out

    @pytest.mark.asyncio
    async def test_receive_message_timeout(self):
        agent = ConcreteAgent("receiver")
        # Empty queue — should get None
        msg = await agent.receive_message()
        assert msg is None

    @pytest.mark.asyncio
    async def test_receive_message_gets_queued(self):
        agent = ConcreteAgent("receiver")
        msg = Message(
            from_agent="sender",
            to_agent="receiver",
            message_type=MessageType.RESULT,
            content={"done": True},
        )
        await agent.message_queue.put(msg)
        received = await agent.receive_message()
        assert received is not None
        assert received.from_agent == "sender"
        assert received.content["done"] is True


class TestAgentReportProgress:

    @pytest.mark.asyncio
    async def test_report_no_current_task(self, capsys):
        agent = ConcreteAgent("prog-agent")
        # No current_task — should no-op gracefully
        await agent.report_progress(0.5, "halfway")
        captured = capsys.readouterr()
        # The method calls send_message which prints - but only if current_task is set
        assert captured.out == ""

    @pytest.mark.asyncio
    async def test_report_with_current_task(self, capsys):
        agent = ConcreteAgent("prog-agent")
        task = Task(type=TaskType.GENERIC, description="progress test")
        agent.current_task = task
        await agent.report_progress(0.5, "halfway")
        captured = capsys.readouterr()
        assert "[prog-agent] -> [coordinator]" in captured.out


class TestAgentRequestHelp:

    @pytest.mark.asyncio
    async def test_request_help_returns_none(self, capsys):
        agent = ConcreteAgent("help-agent")
        result = await agent.request_help("stuck on something")
        # Currently returns None (not implemented)
        assert result is None
        captured = capsys.readouterr()
        assert "[help-agent] -> [coordinator]" in captured.out


class TestAgentRunLoop:

    @pytest.mark.asyncio
    async def test_run_loop_raises_not_implemented(self):
        agent = ConcreteAgent("rl-agent")
        task = Task(type=TaskType.GENERIC, description="rl test")
        with pytest.raises(NotImplementedError, match="does not support run_loop"):
            await agent.run_loop(task, None)  # type: ignore[arg-type]


class TestAgentMemory:

    def test_remember(self, temp_cwd):
        agent = ConcreteAgent("mem-agent")
        agent.remember("Important fact", MemoryType.SEMANTIC, importance=0.9, tags=["facts"])
        stats = agent.long_term_memory.get_statistics()
        assert stats["total_memories"] == 1

    def test_recall(self, temp_cwd):
        agent = ConcreteAgent("recall-agent")
        agent.remember("Python is dynamic", MemoryType.SEMANTIC, tags=["python"])
        agent.remember("Java is static", MemoryType.SEMANTIC, tags=["java"])
        results = agent.recall("Python", limit=5, min_score=0.3)
        assert len(results) >= 1

    def test_recall_with_empty_memory(self, temp_cwd):
        agent = ConcreteAgent("empty-mem")
        results = agent.recall("anything", limit=5)
        assert results == []

    def test_recall_with_filters(self, temp_cwd):
        agent = ConcreteAgent("filt-mem")
        agent.remember("semantic fact", MemoryType.SEMANTIC, tags=["a"])
        agent.remember("episodic event", MemoryType.EPISODIC, tags=["a"])
        results = agent.recall("fact", filters={"type": MemoryType.SEMANTIC})
        assert len(results) == 1

    def test_add_conversation_turn(self, temp_cwd):
        agent = ConcreteAgent("conv-agent")
        agent.add_conversation_turn("user", "Hello")
        agent.add_conversation_turn("agent", "Hi there")
        stats = agent.short_term_memory.get_statistics()
        assert stats["total_turns"] == 2

    def test_get_conversation_context(self):
        agent = ConcreteAgent("ctx-agent")
        agent.add_conversation_turn("user", "What is Python?")
        agent.add_conversation_turn("agent", "A language.")
        ctx = agent.get_conversation_context(max_turns=2)
        assert "user: What is Python?" in ctx
        assert "agent: A language." in ctx

    def test_conversation_context_empty(self):
        agent = ConcreteAgent("empty-ctx")
        ctx = agent.get_conversation_context()
        assert ctx == ""

    def test_working_memory(self):
        agent = ConcreteAgent("wm-agent")
        agent.set_working_memory("key1", "val1")
        assert agent.get_working_memory("key1") == "val1"
        assert agent.get_working_memory("nonexistent", "default") == "default"

    def test_auto_consolidation(self, temp_cwd):
        agent = ConcreteAgent("auto-cons")
        # Add enough turns to cross the consolidation threshold (5)
        for i in range(6):
            agent.add_conversation_turn("user", f"Message {i}")
        ltm_stats = agent.long_term_memory.get_statistics()
        assert ltm_stats["total_memories"] > 0

    def test_manual_consolidation_below_threshold(self):
        agent = ConcreteAgent("man-cons")
        agent.add_conversation_turn("user", "Hello")
        result = agent.consolidate_memories()
        assert result is None

    def test_consolidate_memories_above_threshold(self, temp_cwd):
        agent = ConcreteAgent("man-cons2")
        for i in range(6):
            agent.add_conversation_turn("user", f"Msg {i}")
        result = agent.consolidate_memories()
        assert result is not None
        assert result.memories_created > 0

    def test_memory_statistics(self, temp_cwd):
        agent = ConcreteAgent("stat-agent")
        agent.remember("fact", MemoryType.SEMANTIC)
        agent.add_conversation_turn("user", "Hi")
        stats = agent.get_memory_statistics()
        assert "short_term" in stats
        assert "long_term" in stats
        assert "consolidation" in stats

    def test_save_and_load(self, temp_cwd):
        agent = ConcreteAgent("save-agent")
        agent.remember("Persistent memory", MemoryType.SEMANTIC)
        agent.save_memories()

        # Create new agent (same ID — uses same store path)
        agent2 = ConcreteAgent("save-agent")
        agent2.load_memories()
        stats = agent2.long_term_memory.get_statistics()
        assert stats["total_memories"] == 1

    def test_different_agents_have_separate_memories(self, temp_cwd):
        a1 = ConcreteAgent("a1")
        a2 = ConcreteAgent("a2")
        a1.remember("a1 memory", MemoryType.SEMANTIC)
        a2.remember("a2 memory", MemoryType.SEMANTIC)
        assert a1.long_term_memory.get_statistics()["total_memories"] == 1
        assert a2.long_term_memory.get_statistics()["total_memories"] == 1

    def test_memory_with_metadata(self, temp_cwd):
        agent = ConcreteAgent("meta-agent")
        agent.add_conversation_turn("user", "Important!", metadata={"priority": "high"})
        turns = agent.short_term_memory.turns
        assert turns[0].metadata["priority"] == "high"

    def test_retrieval_strategies(self, temp_cwd):
        agent = ConcreteAgent("strat-agent")
        agent.remember("Python info", MemoryType.SEMANTIC, importance=0.5)
        agent.remember("Important Python", MemoryType.SEMANTIC, importance=0.9)
        kw = agent.recall("Python", strategy=RetrievalStrategy.KEYWORD)
        imp = agent.recall("Python", strategy=RetrievalStrategy.IMPORTANCE)
        hyb = agent.recall("Python", strategy=RetrievalStrategy.HYBRID)
        assert len(kw) > 0
        assert len(imp) > 0
        assert len(hyb) > 0

    def test_memory_with_task_execution(self, temp_cwd):
        agent = ConcreteAgent("task-mem")
        task = Task(type=TaskType.GENERIC, description="sample task")
        asyncio.run(agent.execute(task))
        agent.remember("Completed task", MemoryType.EPISODIC, tags=["task"])
        memories = agent.recall("Completed", limit=5, min_score=0.3)
        assert len(memories) >= 1


class TestAgentRepresentation:

    def test_repr(self):
        agent = ConcreteAgent("repr-agent")
        rep = repr(agent)
        assert "ConcreteAgent" in rep
        assert "repr-agent" in rep
        assert "idle" in rep

    def test_repr_when_busy(self):
        agent = ConcreteAgent("busy-agent")
        agent.status = AgentStatus.BUSY
        rep = repr(agent)
        assert "busy" in rep


# ===========================================================================
# AgentStatus enum
# ===========================================================================

class TestAgentStatusEnum:

    def test_values(self):
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.OFFLINE.value == "offline"
