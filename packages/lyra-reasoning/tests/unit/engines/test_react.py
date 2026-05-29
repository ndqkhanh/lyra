"""
Comprehensive tests for ReAct (Reasoning + Acting) engine.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from lyra_reasoning.engines.react import ReActEngine, ToolCall, ToolResult
from lyra_reasoning.types import (
    ComputeBudget,
    ReasoningConfig,
    ReasoningStrategy,
    StepType,
)


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    with patch("lyra_reasoning.engines.react.Anthropic") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_tools():
    """Sample tool definitions."""
    return {
        "search": {
            "description": "Search for information",
            "parameters": {"query": "string"},
            "function": lambda query: f"Search results for: {query}",
        },
        "calculate": {
            "description": "Perform calculation",
            "parameters": {"expression": "string"},
            "function": lambda expression: str(eval(expression)),
        },
        "get_weather": {
            "description": "Get weather information",
            "parameters": {"location": "string"},
            "function": lambda location: f"Weather in {location}: Sunny, 72°F",
        },
    }


@pytest.fixture
def react_engine(mock_anthropic_client, sample_tools):
    """Create ReAct engine with mocked client."""
    return ReActEngine(tools=sample_tools)


@pytest.fixture
def basic_config():
    """Basic reasoning configuration."""
    return ReasoningConfig(
        strategy=ReasoningStrategy.REACT,
        model="claude-opus-4-20250514",
        max_steps=10,
        temperature=0.7,
    )


@pytest.fixture
def basic_budget():
    """Basic compute budget."""
    return ComputeBudget(max_tokens=10000, max_steps=15)


class TestToolCall:
    """Test suite for ToolCall dataclass."""

    def test_tool_call_creation(self):
        """Test creating a tool call."""
        tool_call = ToolCall(
            tool_name="search",
            parameters={"query": "test"},
        )
        assert tool_call.tool_name == "search"
        assert tool_call.parameters == {"query": "test"}

    def test_tool_call_with_reasoning(self):
        """Test tool call with reasoning."""
        tool_call = ToolCall(
            tool_name="calculate",
            parameters={"expression": "2+2"},
            reasoning="Need to calculate the sum",
        )
        assert tool_call.reasoning == "Need to calculate the sum"


class TestToolResult:
    """Test suite for ToolResult dataclass."""

    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(
            tool_name="search",
            output="Found results",
            success=True,
        )
        assert result.success is True
        assert result.error is None

    def test_tool_result_error(self):
        """Test error tool result."""
        result = ToolResult(
            tool_name="search",
            output="",
            success=False,
            error="Tool not found",
        )
        assert result.success is False
        assert result.error == "Tool not found"


class TestReActEngine:
    """Test suite for ReActEngine."""

    def test_initialization(self, sample_tools):
        """Test engine initialization."""
        engine = ReActEngine(tools=sample_tools)
        assert engine.client is not None
        assert len(engine.tools) == 3
        assert "search" in engine.tools

    def test_initialization_no_tools(self):
        """Test engine initialization without tools."""
        engine = ReActEngine()
        assert engine.tools == {}

    def test_initialization_with_api_key(self, sample_tools):
        """Test engine initialization with API key."""
        with patch("lyra_reasoning.engines.react.Anthropic") as mock:
            ReActEngine(api_key="test-key", tools=sample_tools)
            mock.assert_called_once_with(api_key="test-key")

    def test_reason_basic_flow(
        self, react_engine, mock_anthropic_client, basic_config, basic_budget
    ):
        """Test basic ReAct reasoning flow."""
        # Mock responses: thought -> action -> observation -> conclusion
        responses = [
            Mock(content=[Mock(text="Thought: I need to search for information")]),
            Mock(content=[Mock(text="Action: search(query='test')")]),
            Mock(content=[Mock(text="Thought: Based on results, I can conclude")]),
            Mock(content=[Mock(text="Answer: Final conclusion")]),
        ]
        mock_anthropic_client.messages.create.side_effect = responses

        trace = react_engine.reason("Test task", basic_budget, basic_config)

        assert trace.task == "Test task"
        assert trace.strategy == ReasoningStrategy.REACT
        assert len(trace.steps) > 0

    def test_parse_action_valid(self, react_engine):
        """Test parsing valid action from text."""
        text = "Action: search(query='machine learning')"
        tool_call = react_engine._parse_action(text)

        assert tool_call is not None
        assert tool_call.tool_name == "search"
        assert "query" in tool_call.parameters

    def test_parse_action_invalid(self, react_engine):
        """Test parsing invalid action."""
        text = "This is just a thought, no action"
        tool_call = react_engine._parse_action(text)

        assert tool_call is None

    def test_parse_action_unknown_tool(self, react_engine):
        """Test parsing action with unknown tool."""
        text = "Action: unknown_tool(param='value')"
        tool_call = react_engine._parse_action(text)

        # Should still parse but tool won't be found during execution
        assert tool_call is not None
        assert tool_call.tool_name == "unknown_tool"

    def test_execute_tool_success(self, react_engine):
        """Test successful tool execution."""
        tool_call = ToolCall(
            tool_name="search",
            parameters={"query": "test"},
        )

        result = react_engine._execute_tool(tool_call)

        assert result.success is True
        assert "Search results" in result.output
        assert result.error is None

    def test_execute_tool_not_found(self, react_engine):
        """Test executing non-existent tool."""
        tool_call = ToolCall(
            tool_name="nonexistent",
            parameters={},
        )

        result = react_engine._execute_tool(tool_call)

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_execute_tool_error(self, react_engine):
        """Test tool execution error."""
        # Add tool that raises error
        react_engine.tools["error_tool"] = {
            "description": "Tool that errors",
            "parameters": {},
            "function": lambda: 1 / 0,  # Division by zero
        }

        tool_call = ToolCall(tool_name="error_tool", parameters={})
        result = react_engine._execute_tool(tool_call)

        assert result.success is False
        assert result.error is not None

    def test_build_tool_descriptions(self, react_engine):
        """Test building tool descriptions."""
        descriptions = react_engine._build_tool_descriptions()

        assert "search" in descriptions
        assert "calculate" in descriptions
        assert "get_weather" in descriptions
        assert "Search for information" in descriptions

    def test_is_final_answer(self, react_engine):
        """Test detecting final answer."""
        assert react_engine._is_final_answer("Answer: This is the final answer")
        assert react_engine._is_final_answer("Final Answer: Done")
        assert react_engine._is_final_answer("Conclusion: We can conclude")
        assert not react_engine._is_final_answer("Thought: Still thinking")
        assert not react_engine._is_final_answer("Action: search()")

    def test_extract_thought(self, react_engine):
        """Test extracting thought from text."""
        text = "Thought: I need to search for information\nAction: search()"
        thought = react_engine._extract_thought(text)

        assert thought == "I need to search for information"

    def test_extract_thought_no_marker(self, react_engine):
        """Test extracting thought without marker."""
        text = "Just some text without thought marker"
        thought = react_engine._extract_thought(text)

        assert thought == text

    def test_reasoning_action_loop(
        self, react_engine, mock_anthropic_client, basic_config, basic_budget
    ):
        """Test complete reasoning-action loop."""
        # Simulate: thought -> action -> observation -> thought -> answer
        responses = [
            Mock(content=[Mock(text="Thought: Need to search\nAction: search(query='AI')")]),
            Mock(
                content=[
                    Mock(
                        text=(
                            "Thought: Got results, now calculate\nAction:"
                            "calculate(expression='2+2')"
                        )
                    )
                ]
            ),
            Mock(content=[Mock(text="Answer: Based on search and calculation, the answer is 4")]),
        ]
        mock_anthropic_client.messages.create.side_effect = responses

        trace = react_engine.reason("Test task", basic_budget, basic_config)

        # Should have multiple steps including actions and observations
        step_types = [step.step_type for step in trace.steps]
        assert StepType.HYPOTHESIS in step_types or StepType.ANALYSIS in step_types
        assert any(
            "Action" in step.content or "Observation" in step.content for step in trace.steps
        )

    def test_max_iterations_limit(
        self, react_engine, mock_anthropic_client, basic_config, basic_budget
    ):
        """Test that reasoning respects max iterations."""
        # Always return thought (never final answer)
        mock_response = Mock()
        mock_response.content = [Mock(text="Thought: Still thinking")]
        mock_anthropic_client.messages.create.return_value = mock_response

        trace = react_engine.reason("Test task", basic_budget, basic_config)

        # Should stop at max_steps
        assert len(trace.steps) <= basic_config.max_steps

    def test_budget_enforcement(self, react_engine, mock_anthropic_client, basic_config):
        """Test budget enforcement."""
        limited_budget = ComputeBudget(max_tokens=100, max_steps=2)

        mock_response = Mock()
        mock_response.content = [Mock(text="Thought: Thinking")]
        mock_anthropic_client.messages.create.return_value = mock_response

        react_engine.reason("Test task", limited_budget, basic_config)

        assert limited_budget.steps_used <= 2

    def test_tool_call_with_multiple_parameters(self, react_engine):
        """Test parsing tool call with multiple parameters."""
        text = "Action: complex_tool(param1='value1', param2='value2', param3=123)"
        tool_call = react_engine._parse_action(text)

        assert tool_call is not None
        assert tool_call.tool_name == "complex_tool"

    def test_context_building(self, react_engine):
        """Test building context with history."""
        from lyra_reasoning.types import ReasoningStep

        history = [
            ReasoningStep(content="Thought: First thought", step_type=StepType.HYPOTHESIS),
            ReasoningStep(content="Action: search(query='test')", step_type=StepType.ANALYSIS),
            ReasoningStep(content="Observation: Found results", step_type=StepType.EVIDENCE),
        ]

        context = react_engine._build_context("Test task", history)

        assert "Test task" in context
        assert "First thought" in context
        assert "search" in context
        assert "Found results" in context

    def test_error_recovery(self, react_engine, mock_anthropic_client, basic_config, basic_budget):
        """Test recovery from tool errors."""
        # First action fails, then succeeds
        responses = [
            Mock(content=[Mock(text="Action: nonexistent_tool()")]),
            Mock(content=[Mock(text="Thought: Tool failed, trying another approach")]),
            Mock(content=[Mock(text="Action: search(query='test')")]),
            Mock(content=[Mock(text="Answer: Success")]),
        ]
        mock_anthropic_client.messages.create.side_effect = responses

        trace = react_engine.reason("Test task", basic_budget, basic_config)

        # Should complete despite initial error
        assert trace.outcome in ["success", "incomplete"]

    def test_no_tools_available(self):
        """Test ReAct with no tools."""
        engine = ReActEngine(tools={})
        config = ReasoningConfig(
            strategy=ReasoningStrategy.REACT,
            model="claude-opus-4-20250514",
            max_steps=5,
        )
        budget = ComputeBudget(max_tokens=5000, max_steps=10)

        with patch("lyra_reasoning.engines.react.Anthropic") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client
            mock_client.messages.create.return_value = Mock(
                content=[Mock(text="Answer: Done without tools")]
            )

            trace = engine.reason("Test task", budget, config)

            # Should still work, just without tool calls
            assert len(trace.steps) > 0


@pytest.mark.integration
class TestReActIntegration:
    """Integration tests for ReAct engine."""

    @pytest.mark.skip(reason="Requires real API key")
    def test_real_react_reasoning(self):
        """Test with real API (requires API key)."""
        tools = {
            "calculate": {
                "description": "Perform mathematical calculation",
                "parameters": {"expression": "string"},
                "function": lambda expression: str(eval(expression)),
            }
        }

        engine = ReActEngine(tools=tools)
        config = ReasoningConfig(
            strategy=ReasoningStrategy.REACT,
            model="claude-opus-4-20250514",
            max_steps=10,
        )
        budget = ComputeBudget(max_tokens=5000, max_steps=15)

        trace = engine.reason(
            "What is 15% of 240? Show your reasoning.",
            budget,
            config,
        )

        assert len(trace.steps) > 0
        assert any("calculate" in step.content.lower() for step in trace.steps)
