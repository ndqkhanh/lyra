"""Tests for CISuggestionsWidget — context-aware inline suggestions.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.textual


def test_suggestions_widget_init():
    from lyra_cli.tui_v2.widgets.ci_suggestions import CISuggestionsWidget
    w = CISuggestionsWidget()
    assert w is not None
    assert w.expanded is False


def test_suggestions_toggle():
    from lyra_cli.tui_v2.widgets.ci_suggestions import CISuggestionsWidget
    w = CISuggestionsWidget()
    w.action_toggle_suggestions()
    assert w.expanded is True
    w.action_toggle_suggestions()
    assert w.expanded is False


def test_detect_context_no_keys():
    from lyra_cli.tui_v2.widgets.ci_suggestions import _detect_context
    suggestions = _detect_context()
    assert isinstance(suggestions, list)
    for emoji, suggestion, cmd in suggestions:
        assert isinstance(emoji, str)
        assert isinstance(suggestion, str)
        assert isinstance(cmd, str)
