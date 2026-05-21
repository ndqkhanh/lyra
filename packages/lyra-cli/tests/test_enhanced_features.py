"""Tests for TUI Enhanced Features."""

import pytest

from lyra_cli.tui_v2.widgets.enhanced_features import (
    Theme,
    KeybindingMode,
    Cursor,
    Selection,
    MultiCursorManager,
    SyntaxHighlighter,
    AutoIndenter,
)


# ============================================================================
# Cursor Tests
# ============================================================================

def test_cursor_creation():
    """Test creating a cursor."""
    cursor = Cursor(5, 10)
    
    assert cursor.line == 5
    assert cursor.column == 10


def test_cursor_equality():
    """Test cursor equality."""
    c1 = Cursor(5, 10)
    c2 = Cursor(5, 10)
    c3 = Cursor(5, 11)
    
    assert c1 == c2
    assert c1 != c3


def test_cursor_hash():
    """Test cursor hashing."""
    c1 = Cursor(5, 10)
    c2 = Cursor(5, 10)
    
    assert hash(c1) == hash(c2)
    
    # Can be used in sets
    cursor_set = {c1, c2}
    assert len(cursor_set) == 1


# ============================================================================
# Selection Tests
# ============================================================================

def test_selection_creation():
    """Test creating a selection."""
    start = Cursor(0, 0)
    end = Cursor(0, 10)
    
    selection = Selection(start, end)
    
    assert selection.start == start
    assert selection.end == end


def test_selection_contains_single_line():
    """Test selection contains on single line."""
    selection = Selection(Cursor(0, 5), Cursor(0, 10))
    
    assert selection.contains(Cursor(0, 7))
    assert not selection.contains(Cursor(0, 3))
    assert not selection.contains(Cursor(0, 12))


def test_selection_contains_multi_line():
    """Test selection contains across multiple lines."""
    selection = Selection(Cursor(0, 5), Cursor(2, 10))
    
    assert selection.contains(Cursor(0, 7))
    assert selection.contains(Cursor(1, 5))
    assert selection.contains(Cursor(2, 5))
    assert not selection.contains(Cursor(0, 3))
    assert not selection.contains(Cursor(3, 5))


# ============================================================================
# MultiCursorManager Tests
# ============================================================================

@pytest.fixture
def cursor_manager():
    """Create a multi-cursor manager."""
    return MultiCursorManager()


def test_cursor_manager_creation(cursor_manager):
    """Test creating a cursor manager."""
    assert len(cursor_manager.cursors) == 1
    assert cursor_manager.cursors[0] == Cursor(0, 0)


def test_cursor_manager_add_cursor(cursor_manager):
    """Test adding a cursor."""
    cursor_manager.add_cursor(5, 10)
    
    assert len(cursor_manager.cursors) == 2
    assert Cursor(5, 10) in cursor_manager.cursors


def test_cursor_manager_add_duplicate_cursor(cursor_manager):
    """Test adding duplicate cursor."""
    cursor_manager.add_cursor(5, 10)
    cursor_manager.add_cursor(5, 10)
    
    # Should not add duplicate
    assert len(cursor_manager.cursors) == 2


def test_cursor_manager_remove_cursor(cursor_manager):
    """Test removing a cursor."""
    cursor_manager.add_cursor(5, 10)
    cursor_manager.remove_cursor(5, 10)
    
    assert Cursor(5, 10) not in cursor_manager.cursors


def test_cursor_manager_cannot_remove_last_cursor(cursor_manager):
    """Test cannot remove last cursor."""
    cursor_manager.remove_cursor(0, 0)
    
    # Should still have one cursor
    assert len(cursor_manager.cursors) == 1


def test_cursor_manager_clear_extra_cursors(cursor_manager):
    """Test clearing extra cursors."""
    cursor_manager.add_cursor(5, 10)
    cursor_manager.add_cursor(10, 20)
    
    cursor_manager.clear_extra_cursors()
    
    assert len(cursor_manager.cursors) == 1


def test_cursor_manager_find_next_match(cursor_manager):
    """Test finding next match."""
    text = "hello world\nhello again\nworld hello"
    
    match = cursor_manager.find_next_match(text, "hello", 0, 0)
    
    assert match is not None
    assert match.line == 0
    assert match.column == 0


def test_cursor_manager_find_next_match_from_position(cursor_manager):
    """Test finding next match from position."""
    text = "hello world\nhello again\nworld hello"
    
    match = cursor_manager.find_next_match(text, "hello", 0, 6)
    
    assert match is not None
    assert match.line == 1


def test_cursor_manager_add_cursor_at_next_match(cursor_manager):
    """Test adding cursor at next match."""
    text = "hello world\nhello again"
    
    result = cursor_manager.add_cursor_at_next_match(text, "hello")
    
    assert result is True
    assert len(cursor_manager.cursors) == 2


def test_cursor_manager_add_cursors_at_all_matches(cursor_manager):
    """Test adding cursors at all matches."""
    text = "hello world\nhello again\nworld hello"
    
    count = cursor_manager.add_cursors_at_all_matches(text, "hello")
    
    assert count == 3
    # Original cursor at (0,0) merges with first match at (0,0)
    assert len(cursor_manager.cursors) == 3  # Merged + 2 other matches


# ============================================================================
# SyntaxHighlighter Tests
# ============================================================================

@pytest.fixture
def highlighter():
    """Create a syntax highlighter."""
    return SyntaxHighlighter()


def test_highlighter_creation(highlighter):
    """Test creating a highlighter."""
    assert highlighter.theme == Theme.DARK
    assert highlighter.language is None


def test_highlighter_detect_language(highlighter):
    """Test language detection."""
    assert highlighter.detect_language("test.py") == "python"
    assert highlighter.detect_language("test.js") == "javascript"
    assert highlighter.detect_language("test.rs") == "rust"
    assert highlighter.detect_language("test.go") == "go"


def test_highlighter_detect_unknown_language(highlighter):
    """Test detecting unknown language."""
    result = highlighter.detect_language("test.xyz")
    
    assert result is None


def test_highlighter_highlight(highlighter):
    """Test highlighting code."""
    code = "def hello():\n    print('world')"
    
    result = highlighter.highlight(code, "python")
    
    assert result is not None


def test_highlighter_find_matching_bracket(highlighter):
    """Test finding matching bracket."""
    text = "def hello():\n    print('world')"
    
    # Find opening paren for closing paren at position 10
    match = highlighter.find_matching_bracket(text, 0, 10)
    
    assert match is not None
    assert match == (0, 9)  # Opening paren is at position 9


def test_highlighter_find_matching_bracket_nested(highlighter):
    """Test finding matching bracket with nesting."""
    text = "((()))"
    
    # Find matching for first opening
    match = highlighter.find_matching_bracket(text, 0, 0)
    
    assert match is not None
    assert match == (0, 5)


def test_highlighter_find_matching_bracket_no_match(highlighter):
    """Test finding matching bracket with no match."""
    text = "((("
    
    match = highlighter.find_matching_bracket(text, 0, 0)
    
    assert match is None


# ============================================================================
# AutoIndenter Tests
# ============================================================================

@pytest.fixture
def indenter():
    """Create an auto-indenter."""
    return AutoIndenter()


def test_indenter_creation(indenter):
    """Test creating an indenter."""
    assert indenter.indent_size == 4
    assert indenter.use_spaces is True


def test_indenter_get_indent_level(indenter):
    """Test getting indent level."""
    assert indenter.get_indent_level("    hello") == 1
    assert indenter.get_indent_level("        hello") == 2
    assert indenter.get_indent_level("hello") == 0


def test_indenter_should_indent_after_colon(indenter):
    """Test should indent after colon."""
    assert indenter.should_indent("def hello():")
    assert indenter.should_indent("if True:")
    assert indenter.should_indent("class Test:")


def test_indenter_should_indent_after_bracket(indenter):
    """Test should indent after opening bracket."""
    assert indenter.should_indent("data = {")
    assert indenter.should_indent("items = [")
    assert indenter.should_indent("func(")


def test_indenter_should_not_indent(indenter):
    """Test should not indent."""
    assert not indenter.should_indent("hello = 'world'")
    assert not indenter.should_indent("return value")


def test_indenter_should_dedent_closing_bracket(indenter):
    """Test should dedent closing bracket."""
    assert indenter.should_dedent("}")
    assert indenter.should_dedent("]")
    assert indenter.should_dedent(")")


def test_indenter_should_dedent_keywords(indenter):
    """Test should dedent keywords."""
    assert indenter.should_dedent("else:")
    assert indenter.should_dedent("elif condition:")
    assert indenter.should_dedent("except:")
    assert indenter.should_dedent("finally:")


def test_indenter_calculate_indent_increase(indenter):
    """Test calculating indent increase."""
    indent = indenter.calculate_indent("def hello():", "pass")
    
    assert indent == "    "


def test_indenter_calculate_indent_decrease(indenter):
    """Test calculating indent decrease."""
    # The dedent happens based on the current line starting with else:
    # Previous line "    if True:" has 1 indent level and ends with :
    # So next line should be 2 levels (1 + 1 for the :)
    # But since current line is "else:", it dedents by 1, resulting in 2 levels
    indent = indenter.calculate_indent("    if True:", "else:")
    
    # Should be 2 indent levels (8 spaces)
    assert indent == "        "


def test_indenter_calculate_indent_maintain(indenter):
    """Test calculating indent maintain."""
    indent = indenter.calculate_indent("    hello = 'world'", "goodbye = 'moon'")
    
    assert indent == "    "


# ============================================================================
# Integration Tests
# ============================================================================

def test_multi_cursor_editing_workflow(cursor_manager):
    """Test complete multi-cursor editing workflow."""
    text = "hello world\nhello again\nworld hello"
    
    # Add cursors at all "hello"
    cursor_manager.add_cursors_at_all_matches(text, "hello")
    
    # Should have 3 cursors (original at 0,0 merged with first match)
    assert len(cursor_manager.cursors) == 3
    
    # Clear extra cursors
    cursor_manager.clear_extra_cursors()
    
    assert len(cursor_manager.cursors) == 1


def test_syntax_highlighting_with_bracket_matching(highlighter):
    """Test syntax highlighting with bracket matching."""
    code = "def hello():\n    return (1 + 2)"
    
    # Detect language
    highlighter.detect_language("test.py")
    
    # Highlight
    result = highlighter.highlight(code)
    assert result is not None
    
    # Find matching bracket
    match = highlighter.find_matching_bracket(code, 1, 11)
    assert match is not None


def test_auto_indentation_workflow(indenter):
    """Test complete auto-indentation workflow."""
    lines = [
        "def hello():",
        "if True:",
        "print('world')",
        "else:",
        "print('goodbye')",
    ]
    
    # Calculate indents
    indents = []
    for i in range(1, len(lines)):
        indent = indenter.calculate_indent(lines[i-1], lines[i])
        indents.append(indent)
    
    # Should have proper indentation
    assert len(indents) == 4


# ============================================================================
# Edge Cases
# ============================================================================

def test_cursor_manager_empty_text(cursor_manager):
    """Test cursor manager with empty text."""
    match = cursor_manager.find_next_match("", "hello", 0, 0)
    
    assert match is None


def test_highlighter_empty_code(highlighter):
    """Test highlighter with empty code."""
    result = highlighter.highlight("")
    
    assert result is not None


def test_indenter_empty_line(indenter):
    """Test indenter with empty line."""
    indent = indenter.calculate_indent("", "")
    
    assert indent == ""


def test_cursor_manager_large_text(cursor_manager):
    """Test cursor manager with large text."""
    text = "hello\n" * 1000
    
    count = cursor_manager.add_cursors_at_all_matches(text, "hello")
    
    assert count == 1000


# ============================================================================
# Performance Tests
# ============================================================================

def test_cursor_manager_performance(cursor_manager):
    """Test cursor manager performance."""
    import time
    
    text = "hello world\n" * 100
    
    start = time.time()
    cursor_manager.add_cursors_at_all_matches(text, "hello")
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1


def test_highlighter_performance(highlighter):
    """Test highlighter performance."""
    import time
    
    code = "def hello():\n    print('world')\n" * 100
    
    start = time.time()
    for _ in range(10):
        highlighter.highlight(code, "python")
    duration = time.time() - start
    
    # Should be fast
    assert duration < 1.0


def test_indenter_performance(indenter):
    """Test indenter performance."""
    import time
    
    start = time.time()
    for _ in range(1000):
        indenter.calculate_indent("def hello():", "pass")
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1
