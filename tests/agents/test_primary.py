"""
Tests for PrimaryAgent — orchestration, delegation, parallel execution, and error handling.
"""

import asyncio

import pytest

from lyra.agents.base import Agent, AgentCapability, AgentStatus
from lyra.agents.code_agent import CodeAgent
from lyra.agents.primary import PrimaryAgent
from lyra.agents.research_agent import ResearchAgent
from lyra.agents.review_agent import ReviewAgent
from lyra.agents.test_agent import TestAgent
from lyra.core.task import Result, Task, TaskType


# ---------------------------------------------------------------------------
# Helper: a specialist that always fails
# ---------------------------------------------------------------------------

class FailingSpecialist(Agent):
    """Specialist that always raises during execute."""

    def __init__(self, agent_id: str = "failing"):
        super().__init__(agent_id)

    async def execute(self, task: Task) -> Result:
        self.status = AgentStatus.BUSY
        self.current_task = task
        task.start()
        msg = "intentional failure"
        raise RuntimeError(msg)

    def can_handle(self, task: Task) -> float:
        return 1.0


# ---------------------------------------------------------------------------
# PrimaryAgent creation and registration
# ---------------------------------------------------------------------------

class TestPrimaryAgentInit:

    def test_default_creation(self):
        primary = PrimaryAgent()
        assert primary.agent_id == "primary"
        assert primary.specialists == {}
        assert len(primary.capabilities) == 1
        assert primary.capabilities[0].name == "orchestration"

    def test_custom_id(self):
        primary = PrimaryAgent(agent_id="orchestrator")
        assert primary.agent_id == "orchestrator"


class TestPrimaryAgentSpecialistManagement:

    def test_register_specialist(self):
        primary = PrimaryAgent()
        code_agent = CodeAgent()
        primary.register_specialist(code_agent)
        assert "code_agent" in primary.specialists
        assert primary.specialists["code_agent"] is code_agent

    def test_register_multiple(self):
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        primary.register_specialist(ResearchAgent())
        assert len(primary.specialists) == 2

    def test_unregister_existing(self):
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        primary.unregister_specialist("code_agent")
        assert "code_agent" not in primary.specialists

    def test_unregister_nonexistent(self):
        primary = PrimaryAgent()
        # Should not raise
        primary.unregister_specialist("nonexistent")


class TestPrimaryAgentAnalyzeRequest:

    @pytest.mark.asyncio
    async def test_code_generation_keyword(self):
        primary = PrimaryAgent()
        task = await primary.analyze_request("Implement a sorting function")
        assert task.type == TaskType.CODE_GENERATION

    def test_code_generation_various_phrasings(self):
        """Test that 'code', 'implement', 'refactor' all map to CODE_GENERATION."""
        primary = PrimaryAgent()
        phrases = {"Write code for X": True, "Implement feature Y": True,
                   "Refactor module Z": True, "Build something": False}
        for phrase, should_match in phrases.items():
            task = asyncio.run(primary.analyze_request(phrase))
            if should_match:
                assert task.type == TaskType.CODE_GENERATION, f"Failed for: {phrase}"
            else:
                assert task.type == TaskType.GENERIC, f"Wrong match for: {phrase}"

    @pytest.mark.asyncio
    async def test_test_generation(self):
        primary = PrimaryAgent()
        task = await primary.analyze_request("Generate tests for auth module")
        assert task.type == TaskType.TEST_GENERATION

    @pytest.mark.asyncio
    async def test_research(self):
        primary = PrimaryAgent()
        task = await primary.analyze_request("Research Python async patterns")
        assert task.type == TaskType.RESEARCH

    @pytest.mark.asyncio
    async def test_code_review(self):
        primary = PrimaryAgent()
        task = await primary.analyze_request("Review the authentication module")
        assert task.type == TaskType.CODE_REVIEW

    @pytest.mark.asyncio
    async def test_generic_fallback(self):
        primary = PrimaryAgent()
        task = await primary.analyze_request("What is the weather?")
        assert task.type == TaskType.GENERIC


class TestPrimaryAgentExecute:

    @pytest.mark.asyncio
    async def test_direct_execution_when_no_specialist(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="fallback task")
        result = await primary.execute(task)
        assert result.success
        assert result.agent_id == "primary"
        assert "Acknowledged" in result.data

    @pytest.mark.asyncio
    async def test_delegates_to_specialist(self):
        primary = PrimaryAgent()
        code_agent = CodeAgent()
        primary.register_specialist(code_agent)
        task = Task(type=TaskType.CODE_GENERATION, description="Write code")
        result = await primary.execute(task)
        assert result.success
        assert result.agent_id == "code_agent"

    @pytest.mark.asyncio
    async def test_execute_sets_busy_and_clears(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="status test")
        await primary.execute(task)
        assert primary.status == AgentStatus.IDLE
        assert primary.current_task is None

    @pytest.mark.asyncio
    async def test_execute_sets_task_status(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="timeline test")
        await primary.execute(task)
        assert task.status.value == "completed"

    @pytest.mark.asyncio
    async def test_execute_with_failing_specialist_records_error(self):
        primary = PrimaryAgent()
        specialist = FailingSpecialist()
        primary.register_specialist(specialist)
        task = Task(type=TaskType.GENERIC, description="will fail")
        result = await primary.execute(task)
        assert not result.success
        assert "intentional failure" in result.error
        assert task.status.value == "failed"

    @pytest.mark.asyncio
    async def test_execute_records_history(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="history test")
        await primary.execute(task)
        assert len(primary.execution_history) == 1


class TestPrimaryAgentSelectAgent:

    @pytest.mark.asyncio
    async def test_select_returns_none_when_empty(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        selected = await primary.select_agent(task)
        assert selected is None

    @pytest.mark.asyncio
    async def test_select_best_matching_agent(self):
        primary = PrimaryAgent()
        code = CodeAgent()
        research = ResearchAgent()
        primary.register_specialist(code)
        primary.register_specialist(research)

        task = Task(type=TaskType.CODE_GENERATION, description="code")
        selected = await primary.select_agent(task)
        assert selected is not None
        assert selected.agent_id == "code_agent"

        task2 = Task(type=TaskType.RESEARCH, description="research")
        selected2 = await primary.select_agent(task2)
        assert selected2.agent_id == "research_agent"

    @pytest.mark.asyncio
    async def test_select_skips_busy_agents(self):
        primary = PrimaryAgent()
        code = CodeAgent()
        code.status = AgentStatus.BUSY
        primary.register_specialist(code)
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        selected = await primary.select_agent(task)
        assert selected is None

    @pytest.mark.asyncio
    async def test_returns_highest_confidence(self):
        primary = PrimaryAgent()

        # Both agents handle CODE_GENERATION — the one with higher confidence
        class HighConfAgent(Agent):
            async def execute(self, task: Task) -> Result:
                return Result(task_id=task.task_id, success=True, agent_id=self.agent_id)

            def can_handle(self, task: Task) -> float:
                return 0.95

        class LowConfAgent(Agent):
            async def execute(self, task: Task) -> Result:
                return Result(task_id=task.task_id, success=True, agent_id=self.agent_id)

            def can_handle(self, task: Task) -> float:
                return 0.5

        primary.register_specialist(LowConfAgent("low"))
        primary.register_specialist(HighConfAgent("high"))
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        selected = await primary.select_agent(task)
        assert selected.agent_id == "high"


class TestPrimaryAgentExecuteDirectly:

    @pytest.mark.asyncio
    async def test_execute_directly_returns_acknowledgement(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="direct task")
        result = await primary.execute_directly(task)
        assert result.success
        assert "direct task" in result.data


class TestPrimaryAgentHandleRequest:

    @pytest.mark.asyncio
    async def test_handle_request_success(self):
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        response = await primary.handle_request("Implement a function")
        assert "completed successfully" in response

    @pytest.mark.asyncio
    async def test_handle_request_failure(self):
        primary = PrimaryAgent()
        primary.register_specialist(FailingSpecialist())
        response = await primary.handle_request("Do something")
        assert "Task failed" in response

    @pytest.mark.asyncio
    async def test_handle_request_direct(self):
        primary = PrimaryAgent()
        response = await primary.handle_request("A generic request")
        assert "completed successfully" in response


class TestPrimaryAgentCanHandle:

    def test_always_returns_one(self):
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="anything")
        assert primary.can_handle(task) == 1.0


class TestPrimaryAgentParallelExecution:

    @pytest.mark.asyncio
    async def test_execute_parallel_all_success(self):
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        primary.register_specialist(ResearchAgent())
        tasks = [
            Task(type=TaskType.CODE_GENERATION, description="task 1"),
            Task(type=TaskType.RESEARCH, description="task 2"),
            Task(type=TaskType.GENERIC, description="task 3"),
        ]
        results = await primary.execute_parallel(tasks)
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_parallel_handles_exceptions(self):
        primary = PrimaryAgent()
        primary.register_specialist(FailingSpecialist("failing-1"))
        primary.register_specialist(FailingSpecialist("failing-2"))
        tasks = [
            Task(type=TaskType.GENERIC, description="will fail"),
            Task(type=TaskType.GENERIC, description="also fail"),
        ]
        results = await primary.execute_parallel(tasks)
        assert len(results) == 2
        # Each task delegates to a distinct failing specialist — both fail.
        assert not results[0].success
        assert not results[1].success

    @pytest.mark.asyncio
    async def test_execute_parallel_exception_branch(self, monkeypatch):
        """Exercise the ``isinstance(result, Exception)`` branch in
        ``execute_parallel`` by replacing ``asyncio.gather`` with a stub that
        returns a raw exception."""
        primary = PrimaryAgent()

        async def stub_gather(*_args, **_kwargs):
            return [RuntimeError("simulated gather failure")]

        monkeypatch.setattr(asyncio, "gather", stub_gather)

        tasks = [Task(type=TaskType.GENERIC, description="t1")]
        results = await primary.execute_parallel(tasks)
        assert len(results) == 1
        assert not results[0].success
        assert "simulated gather failure" in results[0].error


class TestPrimaryAgentStatistics:

    def test_get_statistics_empty(self):
        primary = PrimaryAgent()
        stats = primary.get_statistics()
        assert stats["agent_id"] == "primary"
        assert stats["specialists_count"] == 0
        assert stats["specialists"] == []
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_statistics_with_specialists(self):
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        primary.register_specialist(ResearchAgent())
        stats = primary.get_statistics()
        assert stats["specialists_count"] == 2
        assert "code_agent" in stats["specialists"]
        assert "research_agent" in stats["specialists"]
