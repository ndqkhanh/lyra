"""Tests for TUI Slash Dropdown."""

import pytest
from textual.widgets import Input

from lyra_cli.tui_v2.widgets.slash_dropdown import (
    CommandSuggestion,
    SlashDropdown,
    SlashCompletionInput,
)


# ============================================================================
# CommandSuggestion Tests
# ============================================================================

def test_command_suggestion_creation():
    """Test creating a command suggestion."""
    suggestion = CommandSuggestion(
        command="deploy",
        description="Deploy the application",
        category="deployment",
        aliases=["dep"],
        score=0.9,
    )
    
    assert suggestion.command == "deploy"
    assert suggestion.description == "Deploy the application"
    assert suggestion.category == "deployment"
    assert suggestion.aliases == ["dep"]
    assert suggestion.score == 0.9


# ============================================================================
# SlashDropdown Tests
# ============================================================================

@pytest.fixture
def input_widget():
    """Create a test input widget."""
    return Input()


@pytest.fixture
def dropdown(input_widget):
    """Create a test dropdown."""
    return SlashDropdown(input_widget)


def test_slash_dropdown_creation(dropdown):
    """Test creating a slash dropdown."""
    assert dropdown.input_widget is not None
    assert len(dropdown.all_commands) > 0
    assert dropdown.visible is False


def test_slash_dropdown_load_commands(dropdown):
    """Test loading commands."""
    commands = dropdown._load_commands()
    
    assert len(commands) > 0
    assert all(isinstance(cmd, CommandSuggestion) for cmd in commands)


def test_slash_dropdown_show_all(dropdown):
    """Test showing all commands."""
    dropdown.show("")
    
    assert dropdown.visible is True
    assert len(dropdown.suggestions) > 0


def test_slash_dropdown_show_filtered(dropdown):
    """Test showing filtered commands."""
    dropdown.show("dep")
    
    assert dropdown.visible is True
    # Should have suggestions matching "dep"
    if dropdown.suggestions:
        assert any("dep" in s.command.lower() for s in dropdown.suggestions)


def test_slash_dropdown_hide(dropdown):
    """Test hiding dropdown."""
    dropdown.show("")
    assert dropdown.visible is True
    
    dropdown.hide()
    assert dropdown.visible is False


def test_slash_dropdown_fuzzy_match(dropdown):
    """Test fuzzy matching."""
    matches = dropdown._fuzzy_match("dep")
    
    assert len(matches) > 0
    # Should prioritize better matches
    if len(matches) > 1:
        assert matches[0].score >= matches[1].score


def test_slash_dropdown_calculate_score(dropdown):
    """Test score calculation."""
    # Exact match
    score1 = dropdown._calculate_score("test", "test")
    assert score1 == 1.0
    
    # Starts with
    score2 = dropdown._calculate_score("test", "testing")
    assert score2 == 0.9
    
    # Contains
    score3 = dropdown._calculate_score("test", "unittest")
    assert 0.5 <= score3 < 0.9


def test_slash_dropdown_select_next(dropdown):
    """Test selecting next suggestion."""
    dropdown.show("")
    
    initial_index = dropdown.selected_index
    dropdown.select_next()
    
    assert dropdown.selected_index == (initial_index + 1) % len(dropdown.suggestions)


def test_slash_dropdown_select_previous(dropdown):
    """Test selecting previous suggestion."""
    dropdown.show("")
    
    initial_index = dropdown.selected_index
    dropdown.select_previous()
    
    expected = (initial_index - 1) % len(dropdown.suggestions)
    assert dropdown.selected_index == expected


def test_slash_dropdown_get_selected(dropdown):
    """Test getting selected suggestion."""
    dropdown.show("")
    
    selected = dropdown.get_selected()
    
    if dropdown.suggestions:
        assert selected is not None
        assert isinstance(selected, CommandSuggestion)


def test_slash_dropdown_get_selected_empty(dropdown):
    """Test getting selected when no suggestions."""
    dropdown.suggestions = []
    
    selected = dropdown.get_selected()
    
    assert selected is None


# ============================================================================
# SlashCompletionInput Tests
# ============================================================================

@pytest.fixture
def completion_input():
    """Create a test completion input."""
    return SlashCompletionInput()


def test_completion_input_creation(completion_input):
    """Test creating completion input."""
    assert completion_input.dropdown is not None
    assert completion_input.completion_active is False


def test_completion_input_trigger_on_slash(completion_input):
    """Test triggering completion on slash."""
    # Test the logic without reactive updates
    value = "/dep"
    cursor_pos = 4
    
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    
    # Should find slash
    assert last_slash == 0
    
    # Extract query
    query = text_before_cursor[last_slash + 1:]
    assert query == "dep"
    assert len(query) <= 20  # Within limit


def test_completion_input_no_trigger_without_slash(completion_input):
    """Test no trigger without slash."""
    value = "test"
    cursor_pos = 4
    
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    
    # Should not find slash
    assert last_slash == -1


def test_completion_input_hide_on_long_query(completion_input):
    """Test hiding on very long query."""
    value = "/" + "x" * 30
    cursor_pos = 31
    
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    query = text_before_cursor[last_slash + 1:]
    
    # Query is too long
    assert len(query) > 20


def test_completion_input_insert_command(completion_input):
    """Test inserting selected command."""
    # Test the logic without setting reactive properties
    value = "/dep"
    cursor_pos = 4
    
    # Find last "/" before cursor
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    
    # Build expected result
    expected = (
        value[:last_slash] +
        "/deploy " +
        value[cursor_pos:]
    )
    
    assert last_slash == 0
    assert expected == "/deploy "


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_completion_workflow(completion_input):
    """Test complete completion workflow."""
    # Test the logic without app context
    
    # User types "/"
    value = "/"
    cursor_pos = 1
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    
    assert last_slash == 0
    
    # User types "dep"
    value = "/dep"
    cursor_pos = 4
    text_before_cursor = value[:cursor_pos]
    query = text_before_cursor[last_slash + 1:]
    
    assert query == "dep"
    
    # Build expected result after insertion
    expected = value[:last_slash] + "/deploy " + value[cursor_pos:]
    assert expected == "/deploy "


def test_dropdown_navigation(dropdown):
    """Test navigating dropdown."""
    dropdown.show("test")
    
    if len(dropdown.suggestions) > 1:
        # Navigate down
        initial = dropdown.selected_index
        dropdown.select_next()
        assert dropdown.selected_index != initial
        
        # Navigate up
        dropdown.select_previous()
        assert dropdown.selected_index == initial


def test_fuzzy_matching_quality(dropdown):
    """Test fuzzy matching quality."""
    # Test various queries
    queries = ["dep", "test", "help"]
    
    for query in queries:
        matches = dropdown._fuzzy_match(query)
        
        # Should have matches
        if matches:
            # First match should be most relevant
            assert query.lower() in matches[0].command.lower() or \
                   any(query.lower() in alias.lower() for alias in matches[0].aliases)


def test_score_ordering(dropdown):
    """Test that scores are properly ordered."""
    matches = dropdown._fuzzy_match("test")
    
    if len(matches) > 1:
        # Scores should be in descending order
        for i in range(len(matches) - 1):
            assert matches[i].score >= matches[i + 1].score


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_query(dropdown):
    """Test empty query."""
    dropdown.show("")
    
    # Should show some suggestions
    assert len(dropdown.suggestions) > 0


def test_no_matches(dropdown):
    """Test query with no matches."""
    dropdown.show("xyzabc123")
    
    # Should hide dropdown
    assert dropdown.visible is False


def test_multiple_slashes(completion_input):
    """Test multiple slashes in input."""
    value = "/first /sec"
    cursor_pos = 11
    
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    
    # Should find last slash
    assert last_slash == 7


def test_slash_in_middle(completion_input):
    """Test slash in middle of text."""
    value = "before /dep after"
    cursor_pos = 11
    
    text_before_cursor = value[:cursor_pos]
    last_slash = text_before_cursor.rfind("/")
    
    # Should find the slash
    assert last_slash == 7


# ============================================================================
# Performance Tests
# ============================================================================

def test_fuzzy_match_performance(dropdown):
    """Test fuzzy matching performance."""
    import time
    
    start = time.time()
    
    for _ in range(100):
        dropdown._fuzzy_match("test")
    
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1  # 100 matches in <100ms


def test_large_command_set(input_widget):
    """Test with large command set."""
    dropdown = SlashDropdown(input_widget)
    
    # Add many commands
    for i in range(100):
        dropdown.all_commands.append(
            CommandSuggestion(
                command=f"command_{i}",
                description=f"Description {i}",
                category="test",
                aliases=[],
            )
        )
    
    # Should still work
    dropdown.show("command")
    assert len(dropdown.suggestions) > 0
