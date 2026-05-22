"""Tests for /contrib command — ECC-style contributing guide.

Tests that the command compiles, runs without error, and produces
meaningful output for each topic section.
"""
from __future__ import annotations

import pytest


class FakeSession:
    pass


def _run(topic: str):
    """Run cmd_contrib and return just the message string."""
    from lyra_cli.interactive.contrib_cmd import cmd_contrib
    result = cmd_contrib(FakeSession(), topic)
    # The registry CommandResult stores in .message;
    # at runtime the session overrides this to also accept .output
    return getattr(result, 'message', getattr(result, 'output', ''))


def test_contrib_overview():
    msg = _run("")
    assert "Contributing" in msg


def test_contrib_pr():
    msg = _run("pr")
    assert "PR" in msg or "pr" in msg


def test_contrib_commits():
    msg = _run("commits")
    assert "feat" in msg or "Conventional" in msg


def test_contrib_review():
    msg = _run("review")
    assert "checklist" in msg.lower()


def test_contrib_gates():
    msg = _run("gates")
    assert "Compilation" in msg or "quality" in msg.lower()


def test_contrib_changelog():
    msg = _run("changelog")
    assert "changelog" in msg.lower()


def test_contrib_unknown():
    msg = _run("unknown_topic")
    assert "unknown" in msg.lower() or "Try" in msg


def test_contrib_all_sections():
    from lyra_cli.interactive.contrib_cmd import SECTIONS
    for topic in SECTIONS:
        msg = _run(topic)
        assert len(msg) > 0
