"""Phase M.1 - deterministic activity classifier."""
from __future__ import annotations

import pytest

from lyra_cli.observatory.classifier import (
    Classification,
    TaskCategory,
    classify_turn,
    one_shot_rate,
)
from lyra_cli.observatory.fixtures.sample_transcripts import (
    CODING_HAPPY_PATH,
    CONVERSATION,
    DEBUGGING_SESSION,
    RETRY_STREAK,
)


# --- category resolution ---------------------------------------------------

@pytest.mark.parametrize(
    "user_input,expected",
    [
        ("fix the failing test in tests/foo.py", "debugging"),
        ("debug why the login route 500s",        "debugging"),
        ("add a settings page",                   "feature"),
        ("implement payment webhook",             "feature"),
        ("refactor the user service",             "refactor"),
        ("rename getCwd to getCurrentWorkingDirectory", "refactor"),
        ("write unit tests for the cart",         "test"),
        ("explain how routing works",             "explore"),
        ("how does the auth middleware work",     "explore"),
        ("plan the migration to postgres",        "plan"),
        ("delegate this to a subagent",           "delegation"),
        ("git status",                            "git"),
        ("commit and push",                       "git"),
        ("npm run build",                         "build"),
        ("brainstorm naming for the new module",  "brainstorm"),
        ("hi, what can you help me with",         "conversation"),
        ("yo",                                    "conversation"),
    ],
)
def test_classify_via_user_input_keywords(user_input: str, expected: TaskCategory):
    row = {"kind": "turn", "turn": 1, "user_input": user_input, "mode": "agent"}
    assert classify_turn(row).category == expected


def test_classify_falls_through_to_general():
    row = {"kind": "turn", "turn": 1,
           "user_input": "asdfghjkl qwerty", "mode": "agent"}
    assert classify_turn(row).category == "general"


# --- tool-based signals override weak keyword matches ----------------------

def test_edit_tool_in_assistant_promotes_to_coding():
    row = {"kind": "chat", "turn": 1,
           "user": "do the thing",
           "assistant": "I'll Edit(src/foo.py) to add the guard."}
    cls = classify_turn(row)
    assert cls.category == "coding"
    assert "tool:Edit" in cls.signals


def test_bash_tool_alone_does_not_promote_to_coding():
    row = {"kind": "chat", "turn": 1, "user": "list files",
           "assistant": "I'll run Bash(ls -la)."}
    assert classify_turn(row).category != "coding"


# --- mode-aware tie-breaks -------------------------------------------------

def test_plan_mode_biases_toward_plan_for_neutral_input():
    row = {"kind": "turn", "user_input": "do the next step", "mode": "plan"}
    assert classify_turn(row).category == "plan"


def test_debug_mode_biases_toward_debugging():
    row = {"kind": "turn", "user_input": "this is broken", "mode": "debug"}
    assert classify_turn(row).category == "debugging"


# --- retry counter & one-shot rate -----------------------------------------

def test_retry_streak_increments_on_same_category():
    prev = None
    streaks: list[int] = []
    for row in RETRY_STREAK:
        cls = classify_turn(row, prev=prev)
        streaks.append(cls.retry_streak)
        prev = cls
    assert streaks == [1, 2, 3]


def test_was_retry_false_on_first_turn():
    cls = classify_turn(RETRY_STREAK[0], prev=None)
    assert cls.was_retry is False
    assert cls.retry_streak == 1


def test_was_retry_true_on_subsequent_same_category():
    first = classify_turn(RETRY_STREAK[0], prev=None)
    second = classify_turn(RETRY_STREAK[1], prev=first)
    assert second.was_retry is True


def test_streak_resets_on_category_change():
    code = {"kind": "turn", "user_input": "implement X", "mode": "agent"}
    convo = {"kind": "turn", "user_input": "thanks!", "mode": "ask"}
    a = classify_turn(code, prev=None)
    b = classify_turn(convo, prev=a)
    assert b.retry_streak == 1
    assert b.was_retry is False


def test_one_shot_rate_two_codings_one_retry():
    rows = [
        {"kind": "turn", "user_input": "implement X", "mode": "agent"},
        {"kind": "turn", "user_input": "still broken, try again",
         "mode": "agent"},
        {"kind": "turn", "user_input": "implement Y", "mode": "agent"},
    ]
    rate = one_shot_rate(rows)
    assert rate == pytest.approx(2 / 3, abs=0.001)


def test_one_shot_rate_zero_codings_returns_one():
    """Convention: vacuous one-shot rate is 1.0 (no failures observed)."""
    assert one_shot_rate(CONVERSATION) == 1.0


# --- robustness ------------------------------------------------------------

def test_missing_user_input_falls_through_to_general():
    assert classify_turn({"kind": "turn"}).category == "general"


def test_chat_kind_with_no_assistant_does_not_crash():
    cls = classify_turn({"kind": "chat", "user": "hi"})
    assert isinstance(cls, Classification)


def test_command_field_classifies_as_general_for_slash_only():
    """Pure slash commands (no LLM) shouldn't pollute coding metrics."""
    row = {"kind": "turn", "command": "rewind", "user_input": "/rewind 1"}
    assert classify_turn(row).category == "general"


# --- confidence ------------------------------------------------------------

def test_strong_signal_yields_high_confidence():
    row = {"kind": "chat", "user": "fix the bug",
           "assistant": "Edit(src/x.py)... fixed the off-by-one."}
    assert classify_turn(row).confidence >= 0.8


def test_weak_keyword_yields_modest_confidence():
    row = {"kind": "turn", "user_input": "thing"}
    assert 0.0 <= classify_turn(row).confidence <= 0.5


# --- fixture round-trip ----------------------------------------------------

def test_fixtures_classify_as_expected():
    """Sanity check: shared fixtures resolve to their named categories."""
    coding_turns = [r for r in CODING_HAPPY_PATH if r.get("kind") == "turn"]
    debug_turns = [r for r in DEBUGGING_SESSION if r.get("kind") == "turn"]
    convo_turns = [r for r in CONVERSATION if r.get("kind") == "turn"]
    assert classify_turn(debug_turns[0]).category == "debugging"
    assert classify_turn(convo_turns[0]).category == "conversation"
    assert any(classify_turn(r).category in ("plan", "feature")
               for r in coding_turns)
