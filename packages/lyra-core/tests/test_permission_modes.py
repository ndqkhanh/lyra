"""Red tests for Lyra's extended permission modes.

harness_core ships 4 modes (PLAN/DEFAULT/ACCEPT_EDITS/BYPASS); Lyra
adds TDD-aware modes: RED, GREEN, REFACTOR, RESEARCH, RESUME.

Contract from docs/blocks/04-permission-bridge.md:
    - PLAN      : no writes at all, destructive denied
    - RED       : writes allowed only under tests/**
    - GREEN     : writes allowed under src/** (and tests/** is also allowed to
                  accommodate new tests surfaced during implementation)
    - REFACTOR  : writes allowed anywhere, but destructive still asks
    - RESEARCH  : like PLAN but can write under notes/** (scratchpad)
    - RESUME    : inherits caller's last mode; proxy behavior tested separately
    - DEFAULT   : harness_core semantics (writes ask)
    - BYPASS    : anything goes (after hard deny)
"""
from __future__ import annotations

from harness_core.messages import ToolCall

from lyra_core.permissions import (
    Decision,
    LyraMode,
    resolve_lyra_decision,
)


def _call(name: str, **args) -> ToolCall:
    return ToolCall(id="c1", name=name, args=args)


# --- PLAN mode -----------------------------------------------------------------


def test_plan_denies_write_tool() -> None:
    d = resolve_lyra_decision(
        _call("Write", path="src/x.py", content="x"),
        mode=LyraMode.PLAN,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.DENY


def test_plan_allows_read_tool() -> None:
    d = resolve_lyra_decision(
        _call("Read", path="README.md"),
        mode=LyraMode.PLAN,
        tool_writes=False,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


# --- RED mode ------------------------------------------------------------------


def test_red_allows_write_to_tests() -> None:
    d = resolve_lyra_decision(
        _call("Write", path="tests/test_foo.py", content="x"),
        mode=LyraMode.RED,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


def test_red_denies_write_to_src() -> None:
    """RED is for *writing failing tests only*; production edits are GREEN-phase work."""
    d = resolve_lyra_decision(
        _call("Write", path="src/feature.py", content="x"),
        mode=LyraMode.RED,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.DENY
    assert "RED" in d.reason or "tests/" in d.reason.lower()


# --- GREEN mode ----------------------------------------------------------------


def test_green_allows_write_to_src() -> None:
    d = resolve_lyra_decision(
        _call("Edit", path="src/feature.py", old="a", new="b"),
        mode=LyraMode.GREEN,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


def test_green_allows_write_to_tests() -> None:
    """Implementation may uncover the need for more tests; allow tests/** in GREEN."""
    d = resolve_lyra_decision(
        _call("Write", path="tests/test_feature_extra.py", content="x"),
        mode=LyraMode.GREEN,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


def test_green_denies_destructive() -> None:
    d = resolve_lyra_decision(
        _call("Bash", command="rm -rf /"),
        mode=LyraMode.GREEN,
        tool_writes=True,
        tool_risk="destructive",
    )
    assert d.decision in (Decision.DENY, Decision.ASK)


# --- REFACTOR mode -------------------------------------------------------------


def test_refactor_allows_writes_anywhere() -> None:
    d = resolve_lyra_decision(
        _call("Edit", path="src/feature.py", old="a", new="b"),
        mode=LyraMode.REFACTOR,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


def test_refactor_asks_on_destructive() -> None:
    d = resolve_lyra_decision(
        _call("Bash", command="rm -rf node_modules"),
        mode=LyraMode.REFACTOR,
        tool_writes=True,
        tool_risk="destructive",
    )
    assert d.decision is Decision.ASK


# --- RESEARCH mode -------------------------------------------------------------


def test_research_allows_writes_to_notes() -> None:
    d = resolve_lyra_decision(
        _call("Write", path="notes/draft.md", content="x"),
        mode=LyraMode.RESEARCH,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


def test_research_denies_writes_to_src() -> None:
    d = resolve_lyra_decision(
        _call("Edit", path="src/feature.py", old="a", new="b"),
        mode=LyraMode.RESEARCH,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.DENY


# --- BYPASS mode (hard deny still wins) ----------------------------------------


def test_bypass_allows_writes() -> None:
    d = resolve_lyra_decision(
        _call("Write", path="src/feature.py", content="x"),
        mode=LyraMode.BYPASS,
        tool_writes=True,
        tool_risk="low",
    )
    assert d.decision is Decision.ALLOW


# --- tool-less calls (unknown tool) -------------------------------------------


def test_unknown_tool_in_plan_denied_if_writes_unknown() -> None:
    """Safety default: if we cannot classify the tool, PLAN denies."""
    d = resolve_lyra_decision(
        _call("Mystery"),
        mode=LyraMode.PLAN,
        tool_writes=True,
        tool_risk="unknown",
    )
    assert d.decision is Decision.DENY
