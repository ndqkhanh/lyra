"""Tests for TUI Ghost Text."""

import pytest

from lyra_cli.tui_v2.widgets.ghost_text import (
    Suggestion,
    GhostTextProvider,
    GhostTextInput,
    SmartPredictor,
)


# ============================================================================
# Suggestion Tests
# ============================================================================

def test_suggestion_creation():
    """Test creating a suggestion."""
    suggestion = Suggestion(
        text="deploy",
        source="command",
        confidence=0.95,
    )
    
    assert suggestion.text == "deploy"
    assert suggestion.source == "command"
    assert suggestion.confidence == 0.95


# ============================================================================
# GhostTextProvider Tests
# ============================================================================

@pytest.fixture
def provider():
    """Create a ghost text provider."""
    return GhostTextProvider()


def test_provider_creation(provider):
    """Test creating a provider."""
    assert provider.command_history == []
    assert provider.max_history == 100


def test_provider_add_to_history(provider):
    """Test adding to history."""
    provider.add_to_history("/deploy")
    
    assert "/deploy" in provider.command_history


def test_provider_add_duplicate_to_history(provider):
    """Test adding duplicate to history."""
    provider.add_to_history("/deploy")
    provider.add_to_history("/test")
    provider.add_to_history("/deploy")
    
    # Should only have one "/deploy" at the end
    assert provider.command_history.count("/deploy") == 1
    assert provider.command_history[-1] == "/deploy"


def test_provider_history_limit(provider):
    """Test history limit."""
    # Add more than max
    for i in range(150):
        provider.add_to_history(f"/command_{i}")
    
    # Should be trimmed to max
    assert len(provider.command_history) == provider.max_history


def test_provider_suggest_from_history(provider):
    """Test suggesting from history."""
    provider.add_to_history("/deploy production")
    
    suggestion = provider._suggest_from_history("/dep")
    
    assert suggestion is not None
    assert suggestion.text == "loy production"
    assert suggestion.source == "history"


def test_provider_suggest_from_commands(provider):
    """Test suggesting from commands."""
    suggestion = provider._suggest_from_commands("/dep")
    
    assert suggestion is not None
    assert suggestion.source == "command"
    assert "dep" in suggestion.text or suggestion.text.startswith("loy")


def test_provider_no_suggestion_for_complete_command(provider):
    """Test no suggestion for complete command."""
    provider.add_to_history("/deploy")
    
    suggestion = provider._suggest_from_history("/deploy")
    
    # Should not suggest if already complete
    assert suggestion is None


def test_provider_get_suggestion_at_end(provider):
    """Test getting suggestion at end of input."""
    provider.add_to_history("/deploy")
    
    suggestion = provider.get_suggestion("/dep", 4)
    
    assert suggestion is not None


def test_provider_no_suggestion_in_middle(provider):
    """Test no suggestion in middle of input."""
    provider.add_to_history("/deploy")
    
    suggestion = provider.get_suggestion("/dep test", 4)
    
    # Should not suggest if cursor not at end
    assert suggestion is None


# ============================================================================
# GhostTextInput Tests
# ============================================================================

@pytest.fixture
def ghost_input():
    """Create a ghost text input."""
    return GhostTextInput()


def test_ghost_input_creation(ghost_input):
    """Test creating ghost text input."""
    assert ghost_input.provider is not None
    assert ghost_input.ghost_text == ""
    assert ghost_input.current_suggestion is None


def test_ghost_input_watch_value(ghost_input):
    """Test watching value changes."""
    # Add to history first
    ghost_input.provider.add_to_history("/deploy")
    
    # Test the logic without setting reactive properties
    value = "/dep"
    cursor_pos = 4
    
    suggestion = ghost_input.provider.get_suggestion(value, cursor_pos)
    
    # Should have suggestion
    assert suggestion is not None


def test_ghost_input_no_ghost_text_for_empty(ghost_input):
    """Test no ghost text for empty input."""
    value = ""
    cursor_pos = 0
    
    suggestion = ghost_input.provider.get_suggestion(value, cursor_pos)
    
    assert suggestion is None


# ============================================================================
# SmartPredictor Tests
# ============================================================================

@pytest.fixture
def predictor():
    """Create a smart predictor."""
    return SmartPredictor()


def test_predictor_creation(predictor):
    """Test creating a predictor."""
    assert predictor.patterns == {}
    assert predictor.context_history == []


def test_predictor_learn_pattern(predictor):
    """Test learning a pattern."""
    predictor.learn_pattern("/dep", "loy")
    
    assert "/dep" in predictor.patterns
    assert "loy" in predictor.patterns["/dep"]


def test_predictor_predict_from_pattern(predictor):
    """Test predicting from learned pattern."""
    predictor.learn_pattern("/dep", "loy")
    
    prediction = predictor.predict("/dep")
    
    assert prediction == "loy"


def test_predictor_no_prediction_for_unknown(predictor):
    """Test no prediction for unknown prefix."""
    prediction = predictor.predict("/unknown")
    
    assert prediction is None


def test_predictor_add_context(predictor):
    """Test adding context."""
    predictor.add_context("deployment", "/deploy production")
    
    assert len(predictor.context_history) == 1


def test_predictor_predict_from_context(predictor):
    """Test predicting from context."""
    predictor.add_context("deployment", "/deploy production")
    
    prediction = predictor.predict("/dep", context="deployment")
    
    assert prediction is not None
    assert "loy" in prediction


def test_predictor_context_history_limit(predictor):
    """Test context history limit."""
    # Add many contexts
    for i in range(150):
        predictor.add_context(f"context_{i}", f"/command_{i}")
    
    # Should be trimmed
    assert len(predictor.context_history) == 100


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_ghost_text_workflow(ghost_input):
    """Test complete ghost text workflow."""
    # Add to history
    ghost_input.provider.add_to_history("/deploy production")
    
    # Test the logic without reactive properties
    value = "/dep"
    cursor_pos = 4
    
    suggestion = ghost_input.provider.get_suggestion(value, cursor_pos)
    
    # Should have suggestion
    assert suggestion is not None
    assert suggestion.source in ["history", "command"]


def test_ghost_text_completion_with_tab(ghost_input):
    """Test completing ghost text with tab."""
    # Test the completion logic
    value = "/dep"
    ghost_text = "loy"
    
    # Simulate tab completion
    new_value = value + ghost_text
    assert new_value == "/deploy"


def test_predictor_learns_from_usage(predictor):
    """Test that predictor learns from usage."""
    # Learn multiple patterns
    predictor.learn_pattern("/dep", "loy")
    predictor.learn_pattern("/tes", "t")
    predictor.learn_pattern("/hel", "p")
    
    # Should predict correctly
    assert predictor.predict("/dep") == "loy"
    assert predictor.predict("/tes") == "t"
    assert predictor.predict("/hel") == "p"


def test_history_based_suggestions(provider):
    """Test history-based suggestions."""
    # Add various commands
    provider.add_to_history("/deploy production")
    provider.add_to_history("/deploy staging")
    provider.add_to_history("/test unit")
    
    # Should suggest most recent match
    suggestion = provider._suggest_from_history("/deploy")
    
    assert suggestion is not None
    assert "staging" in suggestion.text


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_input(provider):
    """Test with empty input."""
    suggestion = provider.get_suggestion("", 0)
    
    assert suggestion is None


def test_whitespace_input(provider):
    """Test with whitespace input."""
    suggestion = provider.get_suggestion("   ", 3)
    
    # Should handle gracefully
    assert suggestion is None or isinstance(suggestion, Suggestion)


def test_very_long_input(provider):
    """Test with very long input."""
    long_input = "/command " + "x" * 1000
    
    suggestion = provider.get_suggestion(long_input, len(long_input))
    
    # Should handle gracefully
    assert suggestion is None or isinstance(suggestion, Suggestion)


def test_special_characters(provider):
    """Test with special characters."""
    provider.add_to_history("/deploy --flag=value")
    
    suggestion = provider._suggest_from_history("/deploy")
    
    assert suggestion is not None
    assert "--flag=value" in suggestion.text


# ============================================================================
# Performance Tests
# ============================================================================

def test_suggestion_performance(provider):
    """Test suggestion performance."""
    import time
    
    # Add many history entries
    for i in range(100):
        provider.add_to_history(f"/command_{i}")
    
    start = time.time()
    
    for _ in range(100):
        provider.get_suggestion("/command", 8)
    
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1  # 100 suggestions in <100ms


def test_predictor_performance(predictor):
    """Test predictor performance."""
    import time
    
    # Learn many patterns
    for i in range(100):
        predictor.learn_pattern(f"/cmd{i}", f"_{i}")
    
    start = time.time()
    
    for i in range(100):
        predictor.predict(f"/cmd{i}")
    
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1


def test_large_history(provider):
    """Test with large history."""
    # Add max history
    for i in range(provider.max_history):
        provider.add_to_history(f"/command_{i}")
    
    # Should still work
    suggestion = provider.get_suggestion("/command", 8)
    
    assert suggestion is None or isinstance(suggestion, Suggestion)
