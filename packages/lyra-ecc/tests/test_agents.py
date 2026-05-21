"""
Tests for ECC Agent Fleet Integration

Comprehensive test suite for unified agent registry.
"""

import pytest
from lyra_ecc.agents import (
    AgentCategory,
    AgentDefinition,
    AgentDispatchResult,
    UnifiedAgentRegistry,
)


class TestAgentDefinition:
    """Test agent definition dataclass."""

    def test_agent_definition_creation(self):
        """Test creating an agent definition."""
        agent = AgentDefinition(
            name="test-agent",
            category=AgentCategory.DEVELOPMENT,
            description="Test agent",
            capabilities=["testing", "validation"],
            trigger_patterns=["test", "validate"],
        )

        assert agent.name == "test-agent"
        assert agent.category == AgentCategory.DEVELOPMENT
        assert agent.description == "Test agent"
        assert "testing" in agent.capabilities
        assert "test" in agent.trigger_patterns

    def test_agent_definition_immutable(self):
        """Test that agent definitions are immutable."""
        agent = AgentDefinition(
            name="test-agent",
            category=AgentCategory.DEVELOPMENT,
            description="Test agent",
            capabilities=["testing"],
        )

        with pytest.raises(AttributeError):
            agent.name = "modified"  # type: ignore


class TestUnifiedAgentRegistry:
    """Test unified agent registry."""

    def test_registry_initialization(self):
        """Test registry initializes correctly."""
        registry = UnifiedAgentRegistry()
        assert registry is not None
        assert len(registry.agents) > 0

    def test_registry_loads_ecc_agents(self):
        """Test that ECC agents are loaded."""
        registry = UnifiedAgentRegistry()
        ecc_agents = [a for a in registry.agents.values() if a.source == "ECC"]

        assert len(ecc_agents) > 0
        # Check for key ECC agents
        assert "planner" in registry.agents
        assert "executor" in registry.agents
        assert "code-reviewer" in registry.agents

    def test_registry_loads_rsi_agents(self):
        """Test that Lyra RSI agents are loaded."""
        registry = UnifiedAgentRegistry()
        rsi_agents = [a for a in registry.agents.values() if a.source == "Lyra"]

        assert len(rsi_agents) == 7
        # Check for RSI agents
        assert "agent0" in registry.agents
        assert "skillrl" in registry.agents
        assert "alphaevolve" in registry.agents

    def test_get_agent(self):
        """Test getting agent by name."""
        registry = UnifiedAgentRegistry()

        agent = registry.get_agent("planner")
        assert agent is not None
        assert agent.name == "planner"
        assert agent.category == AgentCategory.PLANNING

    def test_get_nonexistent_agent(self):
        """Test getting non-existent agent returns None."""
        registry = UnifiedAgentRegistry()

        agent = registry.get_agent("nonexistent-agent")
        assert agent is None

    def test_list_agents_all(self):
        """Test listing all agents."""
        registry = UnifiedAgentRegistry()

        agents = registry.list_agents()
        assert len(agents) > 0
        assert all(isinstance(a, AgentDefinition) for a in agents)

    def test_list_agents_by_category(self):
        """Test listing agents by category."""
        registry = UnifiedAgentRegistry()

        planning_agents = registry.list_agents(category=AgentCategory.PLANNING)
        assert len(planning_agents) > 0
        assert all(a.category == AgentCategory.PLANNING for a in planning_agents)

    def test_list_agents_by_source(self):
        """Test listing agents by source."""
        registry = UnifiedAgentRegistry()

        ecc_agents = registry.list_agents(source="ECC")
        assert len(ecc_agents) > 0
        assert all(a.source == "ECC" for a in ecc_agents)

        lyra_agents = registry.list_agents(source="Lyra")
        assert len(lyra_agents) == 7
        assert all(a.source == "Lyra" for a in lyra_agents)

    def test_list_agents_by_category_and_source(self):
        """Test listing agents by both category and source."""
        registry = UnifiedAgentRegistry()

        rsi_agents = registry.list_agents(category=AgentCategory.RSI, source="Lyra")
        assert len(rsi_agents) == 7
        assert all(a.category == AgentCategory.RSI for a in rsi_agents)
        assert all(a.source == "Lyra" for a in rsi_agents)

    def test_select_agent_by_trigger_pattern(self):
        """Test agent selection by trigger pattern."""
        registry = UnifiedAgentRegistry()

        # Test planning trigger
        agent_name = registry.select_agent("I need to plan this feature")
        assert agent_name == "planner"

        # Test review trigger (matches critic first due to trigger pattern order)
        agent_name = registry.select_agent("Please review this code")
        assert agent_name in ["critic", "code-reviewer"]  # Both have "review" trigger

        # Test debug trigger (matches tracer first due to trigger pattern order)
        agent_name = registry.select_agent("Help me debug this issue")
        assert agent_name in ["tracer", "debugger"]  # Both have "debug" trigger

    def test_select_agent_by_task_type(self):
        """Test agent selection by task type."""
        registry = UnifiedAgentRegistry()

        # Implementation task
        agent_name = registry.select_agent("Implement user authentication")
        assert agent_name == "executor"

        # Planning task
        agent_name = registry.select_agent("Design the database schema")
        assert agent_name == "planner"

        # Review task
        agent_name = registry.select_agent("Check this code for issues")
        assert agent_name == "code-reviewer"

    def test_select_agent_default_fallback(self):
        """Test agent selection falls back to executor."""
        registry = UnifiedAgentRegistry()

        agent_name = registry.select_agent("Some random task")
        assert agent_name == "executor"

    def test_dispatch_success(self):
        """Test successful agent dispatch."""
        registry = UnifiedAgentRegistry()

        result = registry.dispatch("Plan the implementation")
        assert isinstance(result, AgentDispatchResult)
        assert result.success
        assert result.agent_name == "planner"
        assert result.error is None
        assert "agent" in result.output

    def test_dispatch_nonexistent_agent(self):
        """Test dispatching to non-existent agent."""
        registry = UnifiedAgentRegistry()

        # Manually set selection to return non-existent agent
        registry.agents.pop("executor", None)
        result = registry.dispatch("Some task that would select executor")

        # Should still work because select_agent will find another agent
        assert isinstance(result, AgentDispatchResult)

    def test_get_registry_summary(self):
        """Test getting registry summary."""
        registry = UnifiedAgentRegistry()

        summary = registry.get_registry_summary()

        assert "total_agents" in summary
        assert "ecc_agents" in summary
        assert "rsi_agents" in summary
        assert "by_category" in summary
        assert "agent_names" in summary

        assert summary["total_agents"] > 0
        assert summary["ecc_agents"] > 0
        assert summary["rsi_agents"] == 7
        assert isinstance(summary["by_category"], dict)
        assert isinstance(summary["agent_names"], list)

    def test_agent_categories_complete(self):
        """Test that all agent categories are represented."""
        registry = UnifiedAgentRegistry()

        categories = set(a.category for a in registry.agents.values())

        assert AgentCategory.PLANNING in categories
        assert AgentCategory.DEVELOPMENT in categories
        assert AgentCategory.QUALITY in categories
        assert AgentCategory.SECURITY in categories
        assert AgentCategory.LANGUAGE_SPECIFIC in categories
        assert AgentCategory.RSI in categories


class TestAgentDispatchResult:
    """Test agent dispatch result."""

    def test_dispatch_result_success(self):
        """Test successful dispatch result."""
        result = AgentDispatchResult(
            agent_name="test-agent",
            success=True,
            output={"result": "success"},
        )

        assert result.agent_name == "test-agent"
        assert result.success
        assert result.output == {"result": "success"}
        assert result.error is None

    def test_dispatch_result_failure(self):
        """Test failed dispatch result."""
        result = AgentDispatchResult(
            agent_name="test-agent",
            success=False,
            output=None,
            error="Agent not found",
        )

        assert result.agent_name == "test-agent"
        assert not result.success
        assert result.output is None
        assert result.error == "Agent not found"

    def test_dispatch_result_immutable(self):
        """Test that dispatch results are immutable."""
        result = AgentDispatchResult(
            agent_name="test-agent",
            success=True,
            output={"result": "success"},
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
