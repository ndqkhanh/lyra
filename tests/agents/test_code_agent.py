"""
Tests for CodeAgent — all four capabilities: analysis, generation, refactoring, review.
"""

import pytest

from lyra.agents.code_agent import CodeAgent
from lyra.core.task import Result, Task, TaskType


class TestCodeAgentInit:

    def test_default_id(self):
        agent = CodeAgent()
        assert agent.agent_id == "code_agent"

    def test_four_capabilities(self):
        agent = CodeAgent()
        assert len(agent.capabilities) == 4
        names = {c.name for c in agent.capabilities}
        assert names == {"code_analysis", "code_generation", "refactoring", "code_review"}

    def test_custom_id(self):
        agent = CodeAgent(agent_id="my-code")
        assert agent.agent_id == "my-code"


class TestCodeAgentCanHandle:

    def test_known_task_type(self):
        agent = CodeAgent()
        task = Task(type=TaskType.CODE_ANALYSIS, description="analyze")
        assert agent.can_handle(task) > 0.0

    def test_unknown_task_type(self):
        agent = CodeAgent()
        task = Task(type=TaskType.RESEARCH, description="research")
        assert agent.can_handle(task) == 0.0

    def test_confidence_values(self):
        agent = CodeAgent()
        mapping = {
            TaskType.CODE_ANALYSIS: 0.9,
            TaskType.CODE_GENERATION: 0.85,
            TaskType.CODE_REFACTORING: 0.9,
            TaskType.CODE_REVIEW: 0.85,
        }
        for task_type, expected in mapping.items():
            task = Task(type=task_type, description="test")
            assert agent.can_handle(task) == expected, f"Mismatch for {task_type}"


class TestCodeAgentExecute:

    @pytest.mark.asyncio
    async def test_execute_code_analysis(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_ANALYSIS,
            description="Analyze code",
            params={"file_path": "src/main.py"},
        )
        result = await agent.execute(task)
        assert result.success
        assert result.agent_id == "code_agent"
        assert result.data["file"] == "src/main.py"
        assert "issues" in result.data

    @pytest.mark.asyncio
    async def test_execute_code_generation(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_GENERATION,
            description="Generate a sort function",
            params={"specification": "quicksort"},
        )
        result = await agent.execute(task)
        assert result.success
        assert "Generated code" in result.data["code"]
        assert result.data["language"] == "python"

    @pytest.mark.asyncio
    async def test_execute_code_refactoring(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_REFACTORING,
            description="Refactor module",
            params={"file_path": "src/utils.py"},
        )
        result = await agent.execute(task)
        assert result.success
        assert result.data["file"] == "src/utils.py"
        assert len(result.data["changes_made"]) == 3

    @pytest.mark.asyncio
    async def test_execute_code_review(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_REVIEW,
            description="Review code",
            params={"file_path": "src/app.py"},
        )
        result = await agent.execute(task)
        assert result.success
        assert result.data["file"] == "src/app.py"
        assert result.data["overall_quality"] == "good"

    @pytest.mark.asyncio
    async def test_execute_unsupported_type_returns_error(self):
        agent = CodeAgent()
        task = Task(type=TaskType.RESEARCH, description="research")
        result = await agent.execute(task)
        assert not result.success
        assert "Unsupported task type" in result.error

    @pytest.mark.asyncio
    async def test_execute_sets_status_lifecycle(self):
        agent = CodeAgent()
        task = Task(type=TaskType.CODE_ANALYSIS, description="analyze")
        await agent.execute(task)
        assert agent.status.value == "idle"
        assert agent.current_task is None

    @pytest.mark.asyncio
    async def test_execute_records_history(self):
        agent = CodeAgent()
        task = Task(type=TaskType.CODE_ANALYSIS, description="analyze")
        await agent.execute(task)
        assert len(agent.execution_history) == 1
        assert agent.execution_history[0].success

    @pytest.mark.asyncio
    async def test_execute_generation_default_spec(self):
        agent = CodeAgent()
        task = Task(type=TaskType.CODE_GENERATION, description="Generate code")
        result = await agent.execute(task)
        assert result.success
        assert result.data["code"] != ""

    @pytest.mark.asyncio
    async def test_execute_analysis_no_file_path(self):
        agent = CodeAgent()
        task = Task(type=TaskType.CODE_ANALYSIS, description="analyze")
        result = await agent.execute(task)
        assert result.success
        assert result.data["file"] == "unknown"


class TestCodeAgentCapabilities:

    @pytest.mark.asyncio
    async def test_analyze_code_returns_structured_report(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_ANALYSIS,
            description="full analysis",
            params={"file_path": "src/complex.py"},
        )
        result = await agent.execute(task)
        data = result.data
        assert data["lines_of_code"] == 150
        assert data["complexity"] == "medium"
        assert len(data["issues"]) == 2
        assert len(data["suggestions"]) == 3

    @pytest.mark.asyncio
    async def test_refactor_code_returns_changes(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_REFACTORING,
            description="refactor",
            params={"file_path": "src/old.py"},
        )
        result = await agent.execute(task)
        data = result.data
        assert data["lines_changed"] == 25
        assert data["complexity_improvement"] == "15%"

    @pytest.mark.asyncio
    async def test_review_code_returns_issues(self):
        agent = CodeAgent()
        task = Task(
            type=TaskType.CODE_REVIEW,
            description="review",
            params={"file_path": "src/review.py"},
        )
        result = await agent.execute(task)
        data = result.data
        assert data["issues_found"] == 3
        assert data["critical_issues"] == 0
        assert len(data["comments"]) == 3
