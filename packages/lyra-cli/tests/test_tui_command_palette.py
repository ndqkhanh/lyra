"""Tests for TUI v2 Command Palette Modal.

Tests the Textual-based command palette that provides fuzzy-searchable
command access via Ctrl+K in the TUI.
"""
from __future__ import annotations

import pytest

from lyra_cli.tui_v2.modals.command_palette import CommandPaletteModal


def test_command_palette_modal_composes():
    """Test that the modal composes without errors."""
    modal = CommandPaletteModal()
    assert modal is not None
    assert modal.picker_title == "Command Palette"


def test_command_palette_entries_loads_from_registry():
    """Test that entries() loads all commands from registry."""
    from lyra_cli.commands.registry import COMMAND_REGISTRY
    
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    # Should have same number of entries as registry
    assert len(entries) == len(COMMAND_REGISTRY)
    
    # Each entry should have required fields
    for entry in entries:
        assert entry.key  # Command name
        assert entry.label  # Display label
        assert entry.description  # Description with category
        assert entry.meta  # Metadata dict


def test_command_palette_entries_include_aliases():
    """Test that command aliases are included in labels."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    # Find a command with aliases (e.g., "fork" has "branch" alias)
    fork_entry = next((e for e in entries if e.key == "fork"), None)
    
    if fork_entry:
        # Label should include aliases
        assert "branch" in fork_entry.label.lower()


def test_command_palette_entries_sorted_by_category():
    """Test that entries are sorted by category then name."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    # Extract categories in order
    categories = [e.meta["Category"] for e in entries]
    
    # Should be sorted (allowing for same category appearing multiple times)
    prev_category = ""
    for category in categories:
        # Within same category, names should be sorted
        # Across categories, should be alphabetical
        assert category >= prev_category or category == prev_category
        prev_category = category


def test_command_palette_preview_shows_command_details():
    """Test that preview shows detailed command information."""
    modal = CommandPaletteModal()
    
    # Get first command
    entries = modal.entries()
    if entries:
        first_key = entries[0].key
        preview = modal._preview(first_key)
        
        # Preview should contain command name
        assert first_key in preview.lower()
        
        # Should contain "Description" label
        assert "description" in preview.lower()


def test_command_palette_preview_handles_missing_command():
    """Test that preview handles non-existent command gracefully."""
    modal = CommandPaletteModal()
    preview = modal._preview("nonexistent_command_xyz")
    
    # Should show "not found" message
    assert "not found" in preview.lower()


def test_command_palette_preview_shows_aliases():
    """Test that preview shows command aliases."""
    modal = CommandPaletteModal()
    
    # Find a command with aliases
    entries = modal.entries()
    fork_entry = next((e for e in entries if e.key == "fork"), None)
    
    if fork_entry:
        preview = modal._preview("fork")
        # Should mention aliases
        assert "alias" in preview.lower()


def test_command_palette_entries_have_metadata():
    """Test that all entries have proper metadata."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    for entry in entries:
        # Each entry should have metadata
        assert entry.meta is not None
        assert "Category" in entry.meta
        assert "Description" in entry.meta
        
        # If command has aliases, metadata should include them
        if "(" in entry.label:  # Aliases shown in label
            assert "Aliases" in entry.meta


def test_command_palette_entries_unique_keys():
    """Test that all entry keys are unique."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    keys = [e.key for e in entries]
    assert len(keys) == len(set(keys))  # No duplicates


def test_command_palette_entries_non_empty():
    """Test that we have at least some commands."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    # Should have at least a few basic commands
    assert len(entries) > 0
    
    # Should have common commands
    keys = [e.key for e in entries]
    assert "help" in keys or "model" in keys or "fork" in keys


def test_command_palette_preview_formatting():
    """Test that preview uses Rich formatting."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    if entries:
        preview = modal._preview(entries[0].key)
        
        # Should use Rich markup
        assert "[" in preview and "]" in preview
        
        # Should have multiple lines
        assert "\n" in preview


def test_command_palette_entries_include_category_in_description():
    """Test that category is included in description."""
    modal = CommandPaletteModal()
    entries = modal.entries()
    
    for entry in entries:
        # Description should include category in brackets
        assert "[" in entry.description
        assert "]" in entry.description
        assert entry.meta["Category"] in entry.description
