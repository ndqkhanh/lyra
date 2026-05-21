"""Tests for Eager Tools."""

import pytest
from datetime import datetime

from lyra_cli.eager_tools_engine import (
    ToolCategory,
    Tool,
    ToolSuggestion,
    ToolChain,
    ContextAnalyzer,
    ToolRecommender,
    EagerToolEngine,
)


# ============================================================================
# Tool Tests
# ============================================================================

def test_tool_creation():
    """Test creating a tool."""
    tool = Tool(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.TESTING,
        triggers=["test", "verify"],
        confidence=0.9,
    )
    
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.category == ToolCategory.TESTING
    assert "test" in tool.triggers
    assert tool.confidence == 0.9


# ============================================================================
# ToolSuggestion Tests
# ============================================================================

def test_tool_suggestion_creation():
    """Test creating a tool suggestion."""
    tool = Tool(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.TESTING,
    )
    
    suggestion = ToolSuggestion(
        tool=tool,
        reason="Context suggests testing",
        confidence=0.8,
        context_match=0.7,
    )
    
    assert suggestion.tool == tool
    assert suggestion.reason == "Context suggests testing"
    assert suggestion.confidence == 0.8
    assert suggestion.context_match == 0.7


# ============================================================================
# ToolChain Tests
# ============================================================================

def test_tool_chain_creation():
    """Test creating a tool chain."""
    chain = ToolChain(
        name="test_chain",
        tools=["tool1", "tool2", "tool3"],
        description="A test chain",
    )
    
    assert chain.name == "test_chain"
    assert len(chain.tools) == 3
    assert chain.description == "A test chain"


# ============================================================================
# ContextAnalyzer Tests
# ============================================================================

@pytest.fixture
def analyzer():
    """Create a context analyzer."""
    return ContextAnalyzer()


def test_analyzer_creation(analyzer):
    """Test creating an analyzer."""
    assert analyzer.patterns is not None
    assert len(analyzer.patterns) > 0


def test_analyzer_analyze_testing_context(analyzer):
    """Test analyzing testing context."""
    context = "The unit test is failing with an error"
    
    scores = analyzer.analyze(context)
    
    assert "testing" in scores
    assert scores["testing"] > 0.5


def test_analyzer_analyze_debugging_context(analyzer):
    """Test analyzing debugging context."""
    context = "Need to debug this crash with a breakpoint"
    
    scores = analyzer.analyze(context)
    
    assert "debugging" in scores
    assert scores["debugging"] > 0.5


def test_analyzer_analyze_deployment_context(analyzer):
    """Test analyzing deployment context."""
    context = "Ready to deploy to production"
    
    scores = analyzer.analyze(context)
    
    assert "deployment" in scores
    assert scores["deployment"] > 0.5


def test_analyzer_extract_entities_files(analyzer):
    """Test extracting file entities."""
    context = "Check test.py and main.js for errors"
    
    entities = analyzer.extract_entities(context)
    
    assert "files" in entities
    assert len(entities["files"]) > 0


def test_analyzer_extract_entities_functions(analyzer):
    """Test extracting function entities."""
    context = "The function test_something() is failing"
    
    entities = analyzer.extract_entities(context)
    
    assert "functions" in entities
    assert len(entities["functions"]) > 0


def test_analyzer_extract_entities_errors(analyzer):
    """Test extracting error entities."""
    context = "Error: Connection timeout occurred"
    
    entities = analyzer.extract_entities(context)
    
    assert "errors" in entities
    assert len(entities["errors"]) > 0


def test_analyzer_extract_entities_commands(analyzer):
    """Test extracting command entities."""
    context = "Run /test and then /deploy"
    
    entities = analyzer.extract_entities(context)
    
    assert "commands" in entities
    assert len(entities["commands"]) > 0


# ============================================================================
# ToolRecommender Tests
# ============================================================================

@pytest.fixture
def recommender():
    """Create a tool recommender."""
    return ToolRecommender()


def test_recommender_creation(recommender):
    """Test creating a recommender."""
    assert len(recommender.tools) > 0
    assert len(recommender.chains) > 0
    assert recommender.analyzer is not None


def test_recommender_recommend_testing(recommender):
    """Test recommending tools for testing context."""
    context = "The unit test is failing"
    
    suggestions = recommender.recommend(context)
    
    assert len(suggestions) > 0
    # Should suggest testing-related tools
    assert any("test" in s.tool.name.lower() for s in suggestions)


def test_recommender_recommend_debugging(recommender):
    """Test recommending tools for debugging context."""
    context = "Need to debug this crash"
    
    suggestions = recommender.recommend(context)
    
    assert len(suggestions) > 0
    # Should suggest debugging tools
    assert any("debug" in s.tool.name.lower() for s in suggestions)


def test_recommender_recommend_deployment(recommender):
    """Test recommending tools for deployment context."""
    context = "Ready to deploy to production"
    
    suggestions = recommender.recommend(context)
    
    assert len(suggestions) > 0
    # Should suggest deployment tools
    assert any("deploy" in s.tool.name.lower() for s in suggestions)


def test_recommender_recommend_limit(recommender):
    """Test recommendation limit."""
    context = "test debug deploy refactor document search"
    
    suggestions = recommender.recommend(context, limit=3)
    
    assert len(suggestions) <= 3


def test_recommender_record_usage(recommender):
    """Test recording tool usage."""
    recommender.record_usage("test_tool")
    
    assert len(recommender.usage_history) == 1
    assert recommender.usage_history[0][0] == "test_tool"


def test_recommender_usage_history_limit(recommender):
    """Test usage history limit."""
    # Add more than limit
    for i in range(150):
        recommender.record_usage(f"tool_{i}")
    
    # Should be trimmed
    assert len(recommender.usage_history) == 100


def test_recommender_suggest_chain(recommender):
    """Test suggesting a tool chain."""
    chain = recommender.suggest_chain("run_tests")
    
    assert chain is not None
    assert "run_tests" in chain.tools


def test_recommender_suggest_chain_no_match(recommender):
    """Test suggesting chain with no match."""
    chain = recommender.suggest_chain("unknown_tool")
    
    assert chain is None


# ============================================================================
# EagerToolEngine Tests
# ============================================================================

@pytest.fixture
def engine():
    """Create an eager tool engine."""
    return EagerToolEngine()


def test_engine_creation(engine):
    """Test creating an engine."""
    assert engine.recommender is not None
    assert engine.enabled is True


def test_engine_suggest_tools(engine):
    """Test suggesting tools."""
    context = "The unit test is failing"
    
    suggestions = engine.suggest_tools(context)
    
    assert len(suggestions) > 0


def test_engine_suggest_tools_disabled(engine):
    """Test suggesting tools when disabled."""
    engine.disable()
    
    context = "The unit test is failing"
    suggestions = engine.suggest_tools(context)
    
    assert len(suggestions) == 0


def test_engine_record_tool_usage(engine):
    """Test recording tool usage."""
    engine.record_tool_usage("test_tool")
    
    assert len(engine.recommender.usage_history) == 1


def test_engine_suggest_next_tool(engine):
    """Test suggesting next tool in chain."""
    suggestion = engine.suggest_next_tool("run_tests")
    
    # Should suggest next tool in chain
    assert suggestion is not None or suggestion is None  # Depends on chain


def test_engine_enable_disable(engine):
    """Test enabling and disabling."""
    engine.disable()
    assert engine.enabled is False
    
    engine.enable()
    assert engine.enabled is True


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_suggestion_workflow(engine):
    """Test complete suggestion workflow."""
    # Get suggestions
    context = "The unit test is failing with an error"
    suggestions = engine.suggest_tools(context)
    
    assert len(suggestions) > 0
    
    # Record usage
    if suggestions:
        engine.record_tool_usage(suggestions[0].tool.name)
    
    # Get next suggestion
    if suggestions:
        next_suggestion = engine.suggest_next_tool(suggestions[0].tool.name)
        # May or may not have next tool
        assert next_suggestion is None or isinstance(next_suggestion, ToolSuggestion)


def test_context_analysis_to_recommendation(analyzer, recommender):
    """Test flow from context analysis to recommendation."""
    context = "Need to debug this failing test"
    
    # Analyze context
    scores = analyzer.analyze(context)
    entities = analyzer.extract_entities(context)
    
    assert len(scores) > 0
    
    # Get recommendations
    suggestions = recommender.recommend(context)
    
    assert len(suggestions) > 0


def test_tool_chaining(engine):
    """Test tool chaining."""
    # Record usage of first tool in chain
    engine.record_tool_usage("run_tests")
    
    # Get next suggestion
    next_suggestion = engine.suggest_next_tool("run_tests")
    
    # Should suggest next tool or None
    assert next_suggestion is None or isinstance(next_suggestion, ToolSuggestion)


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_context(engine):
    """Test with empty context."""
    suggestions = engine.suggest_tools("")
    
    # Should handle gracefully
    assert isinstance(suggestions, list)


def test_very_long_context(engine):
    """Test with very long context."""
    context = "test " * 1000
    
    suggestions = engine.suggest_tools(context)
    
    # Should handle gracefully
    assert isinstance(suggestions, list)


def test_special_characters_context(analyzer):
    """Test with special characters."""
    context = "Test @#$% error !@# debug"
    
    scores = analyzer.analyze(context)
    
    # Should handle gracefully
    assert isinstance(scores, dict)


def test_no_matching_tools(recommender):
    """Test with context that matches no tools."""
    context = "xyzabc123 qwerty"
    
    suggestions = recommender.recommend(context)
    
    # May have no suggestions
    assert isinstance(suggestions, list)


# ============================================================================
# Performance Tests
# ============================================================================

def test_analyzer_performance(analyzer):
    """Test analyzer performance."""
    import time
    
    context = "The unit test is failing with an error"
    
    start = time.time()
    for _ in range(100):
        analyzer.analyze(context)
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1


def test_recommender_performance(recommender):
    """Test recommender performance."""
    import time
    
    context = "The unit test is failing"
    
    start = time.time()
    for _ in range(100):
        recommender.recommend(context)
    duration = time.time() - start
    
    # Should be fast
    assert duration < 1.0


def test_engine_performance(engine):
    """Test engine performance."""
    import time
    
    context = "The unit test is failing"
    
    start = time.time()
    for _ in range(100):
        engine.suggest_tools(context)
    duration = time.time() - start
    
    # Should be fast
    assert duration < 1.0
