"""
Tests for PrimaryAgent orchestration.
"""

import pytest

from lyra.agents import CodeAgent, PrimaryAgent, ResearchAgent
from lyra.core.task import Task, TaskType


class TestPrimaryAgent:
    """Test PrimaryAgent orchestration."""

    def test_primary_agent_creation(self):
        """Test primary agent creation."""
        primary = PrimaryAgent()

        assert primary.agent_id == "primary"
        assert len(primary.specialists) == 0
        assert len(primary.capabilities) > 0

    def test_register_specialist(self):
        """Test registering specialist agents."""
        primary = PrimaryAgent()
        code_agent = CodeAgent()

        primary.register_specialist(code_agent)

        assert len(primary.specialists) == 1
        assert "code_agent" in primary.specialists

    def test_unregister_specialist(self):
        """Test unregistering specialist agents."""
        primary = PrimaryAgent()
        code_agent = CodeAgent()

        primary.register_specialist(code_agent)
        assert len(primary.specialists) == 1

        primary.unregister_specialist("code_agent")
        assert len(primary.specialists) == 0

    @pytest.mark.asyncio
    async def test_analyze_request(self):
        """Test request analysis."""
        primary = PrimaryAgent()

        # Test code-related request
        task = await primary.analyze_request("Implement a sorting function")
        assert task.type == TaskType.CODE_GENERATION

        # Test research request
        task = await primary.analyze_request("Research Python async patterns")
        assert task.type == TaskType.RESEARCH

        # Test testing request
        task = await primary.analyze_request("Generate tests for auth module")
        assert task.type == TaskType.TEST_GENERATION

    @pytest.mark.asyncio
    async def test_execute_without_specialists(self):
        """Test execution when no specialists available."""
        primary = PrimaryAgent()
        task = Task(type=TaskType.GENERIC, description="Test task")

        result = await primary.execute(task)

        assert result.success is True
        assert result.agent_id == "primary"

    @pytest.mark.asyncio
    async def test_execute_with_specialist(self):
        """Test execution with specialist delegation."""
        primary = PrimaryAgent()
        code_agent = CodeAgent()
        primary.register_specialist(code_agent)

        task = Task(type=TaskType.CODE_GENERATION, description="Generate code")
        result = await primary.execute(task)

        assert result.success is True
        assert result.agent_id == "code_agent"

    @pytest.mark.asyncio
    async def test_select_agent(self):
        """Test agent selection."""
        primary = PrimaryAgent()
        code_agent = CodeAgent()
        research_agent = ResearchAgent()

        primary.register_specialist(code_agent)
        primary.register_specialist(research_agent)

        # Code task should select code agent
        code_task = Task(type=TaskType.CODE_GENERATION, description="Generate code")
        selected = await primary.select_agent(code_task)
        assert selected.agent_id == "code_agent"

        # Research task should select research agent
        research_task = Task(type=TaskType.RESEARCH, description="Research topic")
        selected = await primary.select_agent(research_task)
        assert selected.agent_id == "research_agent"

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel task execution."""
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        primary.register_specialist(ResearchAgent())

        tasks = [
            Task(type=TaskType.CODE_GENERATION, description="Task 1"),
            Task(type=TaskType.RESEARCH, description="Task 2"),
            Task(type=TaskType.GENERIC, description="Task 3"),
        ]

        results = await primary.execute_parallel(tasks)

        assert len(results) == 3
        assert all(isinstance(r, type(results[0])) for r in results)

    def test_get_statistics(self):
        """Test getting orchestration statistics."""
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())
        primary.register_specialist(ResearchAgent())

        stats = primary.get_statistics()

        assert stats["agent_id"] == "primary"
        assert stats["specialists_count"] == 2
        assert "code_agent" in stats["specialists"]
        assert "research_agent" in stats["specialists"]

    @pytest.mark.asyncio
    async def test_handle_request(self):
        """Test handling user requests."""
        primary = PrimaryAgent()
        primary.register_specialist(CodeAgent())

        response = await primary.handle_request("Implement a function")

        assert isinstance(response, str)
        assert "✅" in response or "❌" in response
