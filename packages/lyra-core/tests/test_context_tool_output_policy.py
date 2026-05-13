"""Tests for tool_output_policy.py (Phase 4)."""
from __future__ import annotations

from lyra_core.context.tool_output_policy import (
    OutputDeduplicator,
    ReproducibilityClass,
    ReproducibilityClassifier,
    RetentionDecider,
    RetentionLevel,
    ToolOutputPolicy,
)


# ---------------------------------------------------------------------------
# ReproducibilityClassifier
# ---------------------------------------------------------------------------


def test_classify_bash_reproducible():
    c = ReproducibilityClassifier()
    assert c.classify("bash") == ReproducibilityClass.REPRODUCIBLE


def test_classify_read_file_reproducible():
    c = ReproducibilityClassifier()
    assert c.classify("read_file") == ReproducibilityClass.REPRODUCIBLE


def test_classify_ask_user_irreproducible():
    c = ReproducibilityClassifier()
    assert c.classify("ask_user") == ReproducibilityClass.IRREPRODUCIBLE


def test_classify_confirm_irreproducible():
    c = ReproducibilityClassifier()
    assert c.classify("confirm") == ReproducibilityClass.IRREPRODUCIBLE


def test_classify_unknown_short_question_irreproducible():
    c = ReproducibilityClassifier()
    result = c.classify("unknown_tool", output_text="Do you want to proceed?")
    assert result == ReproducibilityClass.IRREPRODUCIBLE


def test_classify_unknown_long_output_reproducible():
    c = ReproducibilityClassifier()
    long_output = "a" * 300
    result = c.classify("unknown_tool", output_text=long_output)
    assert result == ReproducibilityClass.REPRODUCIBLE


def test_classify_case_insensitive():
    c = ReproducibilityClassifier()
    assert c.classify("BASH") == ReproducibilityClass.REPRODUCIBLE
    assert c.classify("Ask_User") == ReproducibilityClass.IRREPRODUCIBLE


# ---------------------------------------------------------------------------
# RetentionDecider
# ---------------------------------------------------------------------------


def test_keep_irreproducible_regardless_of_age():
    d = RetentionDecider(keep_turns=3, summarise_turns=8)
    dec = d.decide(
        "ask_user",
        turn_age=100,
        reproducibility=ReproducibilityClass.IRREPRODUCIBLE,
    )
    assert dec.level == RetentionLevel.KEEP


def test_keep_referenced():
    d = RetentionDecider()
    dec = d.decide("bash", turn_age=50, referenced=True)
    assert dec.level == RetentionLevel.KEEP
    assert "referenced" in dec.reason


def test_keep_recent():
    d = RetentionDecider(keep_turns=3)
    dec = d.decide("bash", turn_age=2)
    assert dec.level == RetentionLevel.KEEP


def test_summarise_medium_age():
    d = RetentionDecider(keep_turns=3, summarise_turns=8)
    dec = d.decide("bash", turn_age=5)
    assert dec.level == RetentionLevel.SUMMARISE


def test_drop_stale():
    d = RetentionDecider(keep_turns=3, summarise_turns=8)
    dec = d.decide("bash", turn_age=15)
    assert dec.level == RetentionLevel.DROP


def test_keep_at_keep_turns_boundary():
    d = RetentionDecider(keep_turns=3, summarise_turns=8)
    assert d.decide("bash", turn_age=3).level == RetentionLevel.KEEP


def test_summarise_at_summarise_boundary():
    d = RetentionDecider(keep_turns=3, summarise_turns=8)
    assert d.decide("bash", turn_age=8).level == RetentionLevel.SUMMARISE


def test_drop_just_past_summarise():
    d = RetentionDecider(keep_turns=3, summarise_turns=8)
    assert d.decide("bash", turn_age=9).level == RetentionLevel.DROP


def test_decision_stores_tool_name_and_age():
    d = RetentionDecider()
    dec = d.decide("read_file", turn_age=2)
    assert dec.tool_name == "read_file"
    assert dec.turn_age == 2


# ---------------------------------------------------------------------------
# OutputDeduplicator
# ---------------------------------------------------------------------------


def test_strip_ansi():
    dedup = OutputDeduplicator()
    text = "\x1b[31mError\x1b[0m: something failed"
    result = dedup.clean(text)
    assert "\x1b" not in result
    assert "Error" in result
    assert "something failed" in result


def test_collapse_blank_lines():
    dedup = OutputDeduplicator()
    text = "line1\n\n\n\n\nline2"
    result = dedup.clean(text)
    assert "\n\n\n" not in result
    assert "line1" in result
    assert "line2" in result


def test_collapse_repeated_lines():
    dedup = OutputDeduplicator()
    text = "same line\nsame line\nsame line\ndifferent"
    result = dedup.clean(text)
    assert "repeated 3×" in result
    assert result.count("same line") == 1


def test_no_collapse_unique_lines():
    dedup = OutputDeduplicator()
    text = "line A\nline B\nline C"
    result = dedup.clean(text)
    assert "line A" in result
    assert "line B" in result
    assert "line C" in result
    assert "repeated" not in result


def test_truncate_long_output():
    dedup = OutputDeduplicator(max_lines=10, head_lines=3, tail_lines=3)
    lines = [f"line {i}" for i in range(20)]
    result = dedup.clean("\n".join(lines))
    result_lines = result.splitlines()
    assert len(result_lines) < 20
    assert "omitted" in result
    assert "line 0" in result
    assert "line 19" in result


def test_no_truncation_short_output():
    dedup = OutputDeduplicator(max_lines=50)
    text = "\n".join(f"line {i}" for i in range(10))
    result = dedup.clean(text)
    assert "omitted" not in result


def test_truncate_stack_trace():
    dedup = OutputDeduplicator(stack_head=2, stack_tail=2)
    # Build a fake traceback with enough frames
    lines = [
        "Traceback (most recent call last):",
        "  File 'a.py', line 1, in main",
        "  File 'b.py', line 2, in foo",
        "  File 'c.py', line 3, in bar",
        "  File 'd.py', line 4, in baz",
        "  File 'e.py', line 5, in qux",
        "RuntimeError: something went wrong",
    ]
    result = dedup.clean("\n".join(lines))
    assert "frames omitted" in result


def test_clean_idempotent_on_clean_text():
    dedup = OutputDeduplicator()
    text = "simple output\nno issues here"
    result = dedup.clean(text)
    assert result == dedup.clean(result)


# ---------------------------------------------------------------------------
# ToolOutputPolicy
# ---------------------------------------------------------------------------


def _tool_msg(name: str, content: str) -> dict:
    return {"role": "tool", "name": name, "content": content}


def _user_msg(content: str) -> dict:
    return {"role": "user", "content": content}


def _assistant_msg(content: str) -> dict:
    return {"role": "assistant", "content": content}


def test_policy_keeps_non_tool_messages():
    policy = ToolOutputPolicy()
    msgs = [_user_msg("hello"), _assistant_msg("hi")]
    result = policy.apply(msgs)
    assert len(result) == 2


def test_policy_cleans_ansi_in_tool_output():
    policy = ToolOutputPolicy()
    msgs = [_tool_msg("bash", "\x1b[32mOK\x1b[0m")]
    result = policy.apply(msgs)
    assert "\x1b" not in result[0]["content"]
    assert "OK" in result[0]["content"]


def test_policy_drops_stale_reproducible():
    policy = ToolOutputPolicy(
        decider=RetentionDecider(keep_turns=1, summarise_turns=2)
    )
    # Add many messages so the tool message is stale
    msgs = [_tool_msg("bash", "old output")] + [
        _user_msg(f"turn {i}") for i in range(10)
    ]
    result = policy.apply(msgs)
    tool_msgs = [m for m in result if m.get("role") == "tool"]
    assert len(tool_msgs) == 0


def test_policy_keeps_irreproducible_even_when_stale():
    policy = ToolOutputPolicy(
        decider=RetentionDecider(keep_turns=1, summarise_turns=2)
    )
    msgs = [_tool_msg("ask_user", "yes, proceed")] + [
        _user_msg(f"turn {i}") for i in range(10)
    ]
    result = policy.apply(msgs)
    tool_msgs = [m for m in result if m.get("role") == "tool"]
    assert len(tool_msgs) == 1


def test_policy_preserves_message_order():
    policy = ToolOutputPolicy()
    msgs = [
        _user_msg("q1"),
        _tool_msg("bash", "output"),
        _assistant_msg("answer"),
    ]
    result = policy.apply(msgs)
    roles = [m["role"] for m in result]
    assert roles[0] == "user"
    assert roles[-1] == "assistant"


def test_policy_does_not_mutate_input():
    policy = ToolOutputPolicy()
    original_content = "\x1b[31mred text\x1b[0m"
    msgs = [_tool_msg("bash", original_content)]
    policy.apply(msgs)
    assert msgs[0]["content"] == original_content
