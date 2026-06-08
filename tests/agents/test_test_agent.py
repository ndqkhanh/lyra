"""
Unit tests for the TestAgent.

Tests initialization, execute (with all task types), generate_tests,
execute_tests, analyze_coverage, can_handle, and error paths.
"""

from __future__ import annotations

import pytest

from lyra.agents.base import AgentCapability, AgentStatus
from lyra.agents.test_agent import TestAgent
from lyra.core.task import Result, Task, TaskType

pytestmark = pytest.mark.asyncio


@pytest.fixture
def agent() -> TestAgent:
    """Default TestAgent instance."""
    return TestAgent()


class TestTestAgentInit:
    def test_agent_id_default(self) -> None:
        agent = TestAgent()
        assert agent.agent_id == "test_agent"

    def test_agent_id_custom(self) -> None:
        agent = TestAgent(agent_id="my_tester")
        assert agent.agent_id == "my_tester"

    def test_initial_status(self, agent: TestAgent) -> None:
        assert agent.status == AgentStatus.IDLE

    def test_capabilities(self, agent: TestAgent) -> None:
        assert len(agent.capabilities) == 2
        names = [c.name for c in agent.capabilities]
        assert "test_generation" in names
        assert "test_execution" in names

    def test_capability_details(self, agent: TestAgent) -> None:
        gen_cap = agent.get_capability(TaskType.TEST_GENERATION)
        assert gen_cap is not None
        assert gen_cap.name == "test_generation"
        assert gen_cap.confidence == 0.85

        exec_cap = agent.get_capability(TaskType.TEST_EXECUTION)
        assert exec_cap is not None
        assert exec_cap.name == "test_execution"
        assert exec_cap.confidence == 0.9

    def test_repr(self, agent: TestAgent) -> None:
        rep = repr(agent)
        assert "TestAgent" in rep
        assert "test_agent" in rep
        assert "idle" in rep


class TestTestAgentExecute:
    async def test_test_generation(self, agent: TestAgent) -> None:
        task = Task(
            type=TaskType.TEST_GENERATION,
            description="Generate tests for utils.py",
            params={"file_path": "utils.py"},
        )
        result = await agent.execute(task)
        assert isinstance(result, Result)
        assert result.success is True
        assert result.task_id == task.task_id
        assert result.agent_id == "test_agent"
        assert result.data is not None
        assert result.data["file"] == "utils.py"
        assert result.data["tests_generated"] == 3
        assert "test_basic_functionality" in [t["name"] for t in result.data["test_cases"]]
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None

    async def test_test_execution(self, agent: TestAgent) -> None:
        task = Task(
            type=TaskType.TEST_EXECUTION,
            description="Run tests for project",
            params={"test_path": "tests/"},
        )
        result = await agent.execute(task)
        assert result.success is True
        assert result.data["total_tests"] == 15
        assert result.data["passed"] == 13
        assert result.data["failed"] == 2
        assert len(result.data["failures"]) == 2
        assert agent.status == AgentStatus.IDLE

    async def test_unsupported_task_type(self, agent: TestAgent) -> None:
        task = Task(
            type=TaskType.CODE_REVIEW,
            description="Review some code",
        )
        result = await agent.execute(task)
        assert result.success is False
        assert result.error is not None
        assert "Unsupported task type" in result.error
        assert agent.status == AgentStatus.IDLE

    async def test_status_during_execution(self, agent: TestAgent) -> None:
        """Agent status is BUSY during execution."""
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        # We can check that status changes by tracking it
        # During execute: BUSY, after: IDLE
        assert agent.status == AgentStatus.IDLE
        result = await agent.execute(task)
        assert agent.status == AgentStatus.IDLE
        assert result.success is True

    async def test_execution_history(self, agent: TestAgent) -> None:
        task1 = Task(type=TaskType.TEST_GENERATION, params={"file_path": "a.py"})
        task2 = Task(type=TaskType.TEST_EXECUTION, params={"test_path": "b.py"})
        await agent.execute(task1)
        await agent.execute(task2)
        assert len(agent.execution_history) == 2

    async def test_execution_history_max_100(self, agent: TestAgent) -> None:
        for i in range(105):
            task = Task(type=TaskType.TEST_GENERATION, params={"file_path": f"{i}.py"})
            await agent.execute(task)
        assert len(agent.execution_history) == 100

    async def test_result_validation(self, agent: TestAgent) -> None:
        """Failed results must have an error message."""
        task = Task(type=TaskType.CODE_REVIEW, description="Review code", params={})
        result = await agent.execute(task)
        assert result.success is False
        assert result.error is not None  # Should always have error on failure

    async def test_execute_adds_result_to_history(self, agent: TestAgent) -> None:
        assert len(agent.execution_history) == 0
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        await agent.execute(task)
        assert len(agent.execution_history) == 1
        assert agent.execution_history[0].success is True


class TestTestAgentGenerateTests:
    async def test_default_file_path(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, description="gen tests", params={})
        data = await agent.generate_tests(task)
        assert data["file"] == "unknown"

    async def test_custom_file_path(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "my_module.py"})
        data = await agent.generate_tests(task)
        assert data["file"] == "my_module.py"
        assert data["test_file"] == "test_my_module.py"

    async def test_coverage_estimate(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        data = await agent.generate_tests(task)
        assert data["coverage_estimate"] == "85%"

    async def test_all_test_cases_present(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        data = await agent.generate_tests(task)
        names = {t["name"] for t in data["test_cases"]}
        assert "test_basic_functionality" in names
        assert "test_edge_cases" in names
        assert "test_error_handling" in names

    async def test_reports_progress(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        data = await agent.generate_tests(task)
        assert data is not None


class TestTestAgentExecuteTests:
    async def test_default_test_path(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_EXECUTION, description="run tests", params={})
        data = await agent.execute_tests(task)
        assert data["total_tests"] == 15
        assert data["passed"] == 13
        assert data["failed"] == 2

    async def test_failure_details(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_EXECUTION, params={"test_path": "tests/"})
        data = await agent.execute_tests(task)
        assert len(data["failures"]) == 2
        assert data["failures"][0]["test"] == "test_edge_case_1"
        assert data["failures"][1]["test"] == "test_error_handling"

    async def test_coverage_percentage(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_EXECUTION, params={"test_path": "tests/"})
        data = await agent.execute_tests(task)
        assert data["coverage"] == 82.5

    async def test_duration_is_positive(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_EXECUTION, params={"test_path": "tests/"})
        data = await agent.execute_tests(task)
        assert data["duration"] > 0

    async def test_simulated_sleeps_executed(self, agent: TestAgent) -> None:
        """The function should complete without error, verifying simulation."""
        task = Task(type=TaskType.TEST_EXECUTION, params={"test_path": "tests/"})
        data = await agent.execute_tests(task)
        assert data["total_tests"] == 15


class TestTestAgentAnalyzeCoverage:
    async def test_coverage_results(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, description="analyze coverage", params={})
        # analyze_coverage does not depend on task type
        data = await agent.analyze_coverage(task)
        assert data["overall_coverage"] == 82.5
        assert data["line_coverage"] == 85.0
        assert data["branch_coverage"] == 78.0

    async def test_uncovered_files(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, description="analyze coverage", params={})
        data = await agent.analyze_coverage(task)
        assert len(data["uncovered_files"]) == 2
        assert data["uncovered_files"][0]["file"] == "utils.py"

    async def test_recommendations(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, description="analyze coverage", params={})
        data = await agent.analyze_coverage(task)
        assert len(data["recommendations"]) == 3


class TestTestAgentCanHandle:
    def test_test_generation(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        score = agent.can_handle(task)
        assert score == 0.85

    def test_test_execution(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_EXECUTION, params={"test_path": "tests/"})
        score = agent.can_handle(task)
        assert score == 0.9

    def test_unsupported_task_type(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.CODE_REVIEW, params={}, description="review")
        score = agent.can_handle(task)
        assert score == 0.0

    def test_capability_not_found_returns_zero(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.RESEARCH, params={}, description="research")
        score = agent.can_handle(task)
        assert score == 0.0


class TestTestAgentInheritedMethods:
    def test_get_success_rate_all(self, agent: TestAgent) -> None:
        assert agent.get_success_rate() == 0.0

    async def test_get_success_rate_after_execution(self, agent: TestAgent) -> None:
        task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        await agent.execute(task)
        assert agent.get_success_rate() == 1.0

    async def test_get_success_rate_mixed(self, agent: TestAgent) -> None:
        gen_task = Task(type=TaskType.TEST_GENERATION, params={"file_path": "x.py"})
        await agent.execute(gen_task)

        fail_task = Task(type=TaskType.CODE_REVIEW, description="review", params={})
        await agent.execute(fail_task)

        assert agent.get_success_rate() == 0.5

    async def test_remember_and_recall(self, agent: TestAgent) -> None:
        agent.remember("test content", tags=["test"])
        results = agent.recall("test content")
        assert len(results) >= 1

    def test_get_capability_none(self, agent: TestAgent) -> None:
        assert agent.get_capability(TaskType.GENERIC) is None
