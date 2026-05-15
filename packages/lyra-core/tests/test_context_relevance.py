"""Tests for relevance-scored compaction (Phase CE.2, P1-1)."""
from __future__ import annotations

import pytest

from lyra_core.context.relevance import (
    COMPACT_TOOL_NAME,
    DEFAULT_WEIGHTS,
    RelevanceWeights,
    agent_compact_now,
    compact_messages_relevance,
    score_message,
)


# ────────────────────────────────────────────────────────────────
# score_message
# ────────────────────────────────────────────────────────────────


def test_empty_message_scores_zero():
    br = score_message({"role": "user", "content": ""}, task="edit src/x.py")
    assert br.score == 0.0


def test_file_overlap_signal_fires():
    br = score_message(
        {"role": "assistant", "content": "modified src/x.py at line 12"},
        task="edit src/x.py to add a new endpoint",
    )
    # File overlap is the default 0.35 weight.
    assert br.file_overlap == pytest.approx(DEFAULT_WEIGHTS.file_overlap)
    assert br.score > 0


def test_keyword_signal_saturates_at_three_hits():
    br = score_message(
        {
            "role": "tool",
            "content": "FAIL error blocker regression bug must FIXME",
        },
        task="something unrelated",
    )
    # Keyword weight at saturation == full weight.
    assert br.signal_keywords == pytest.approx(DEFAULT_WEIGHTS.signal_keywords)


def test_keyword_partial_credit():
    br = score_message(
        {"role": "user", "content": "we had one error here"},
        task="task",
    )
    assert 0 < br.signal_keywords < DEFAULT_WEIGHTS.signal_keywords


def test_citation_signal_requires_later_mention_outside_tool():
    msg = {"role": "tool", "tool_call_id": "t-7", "content": "body"}
    later_tool = {"role": "tool", "tool_call_id": "t-8", "content": "t-7 self ref"}
    later_asst = {"role": "assistant", "content": "I will reuse t-7's result"}

    no_cite = score_message(msg, task="t", later_messages=[later_tool])
    yes_cite = score_message(
        msg, task="t", later_messages=[later_tool, later_asst]
    )
    assert no_cite.citation_inbound == 0
    assert yes_cite.citation_inbound == pytest.approx(
        DEFAULT_WEIGHTS.citation_inbound
    )


def test_invariant_density_picks_up_anchors_and_tests():
    msg = {
        "role": "assistant",
        "content": (
            "test_login_rejects_empty failed at src/auth.py:42 — deny: no auth"
        ),
    }
    br = score_message(msg, task="unrelated")
    # 1 file anchor + 1 test name + 1 deny → 3 of 4 → ~0.75 of full weight.
    assert br.invariant_density > 0
    assert br.invariant_density < DEFAULT_WEIGHTS.invariant_density


def test_score_is_clamped_to_one_with_all_signals_max():
    msg = {
        "role": "assistant",
        "tool_call_id": "t-1",
        "content": (
            "src/x.py FAIL error deny test_one test_two test_three test_four "
            "src/x.py:1 src/x.py:2 src/x.py:3 src/x.py:4 deny: a"
        ),
    }
    later = [{"role": "user", "content": "use t-1 again"}]
    br = score_message(msg, task="edit src/x.py", later_messages=later)
    assert br.score == pytest.approx(1.0, abs=1e-6)


def test_score_uses_caller_weights():
    msg = {"role": "user", "content": "src/x.py was changed"}
    w = RelevanceWeights(
        file_overlap=1.0,
        signal_keywords=0.0,
        citation_inbound=0.0,
        invariant_density=0.0,
    )
    br = score_message(msg, task="src/x.py", weights=w)
    assert br.score == pytest.approx(1.0)


# ────────────────────────────────────────────────────────────────
# compact_messages_relevance
# ────────────────────────────────────────────────────────────────


class _StubLLM:
    def __init__(self, text: str = "summary text"):
        self.text = text

    def generate(self, **_kw):
        return {"content": self.text}


def _build_conversation() -> list[dict]:
    """A conversation where one OLD turn pins down a hot file anchor."""
    return [
        {"role": "system", "content": "soul"},
        {"role": "user", "content": "refactor src/api.py"},
        # Old high-signal turn we expect to rescue.
        {
            "role": "assistant",
            "content": "src/api.py:88 has the bug — FAIL test_api_health",
        },
        {"role": "tool", "tool_call_id": "t-1", "content": "tool out 1"},
        {"role": "assistant", "content": "stepping through"},
        {"role": "tool", "tool_call_id": "t-2", "content": "tool out 2"},
        {"role": "assistant", "content": "still going"},
        {"role": "tool", "tool_call_id": "t-3", "content": "tool out 3"},
        # keep_last tail starts here.
        {"role": "assistant", "content": "near the end"},
        {"role": "user", "content": "what now?"},
    ]


def test_relevance_rescues_high_signal_old_turn():
    msgs = _build_conversation()
    out = compact_messages_relevance(
        msgs,
        llm=_StubLLM(),
        task="refactor src/api.py",
        keep_last=2,
        threshold=0.3,
    )
    # The high-signal turn at index 2 (system head len 1 → global idx 2)
    # should be rescued.
    assert 2 in out.rescued_indices
    body_after = [m["content"] for m in out.result.summarised_messages]
    assert any("src/api.py:88" in c for c in body_after if isinstance(c, str))


def test_relevance_short_circuits_when_below_keep_last():
    short = [
        {"role": "system", "content": "soul"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    out = compact_messages_relevance(
        short, llm=_StubLLM(), task="x", keep_last=4
    )
    assert out.rescued_indices == ()
    assert out.result.dropped_count == 0


def test_relevance_high_threshold_rescues_nothing():
    msgs = _build_conversation()
    out = compact_messages_relevance(
        msgs,
        llm=_StubLLM(),
        task="refactor src/api.py",
        keep_last=2,
        threshold=0.99,
    )
    assert out.rescued_indices == ()
    # Still compacted normally.
    assert out.result.dropped_count > 0


def test_relevance_zero_threshold_rescues_anything_scored_above_zero():
    msgs = _build_conversation()
    out = compact_messages_relevance(
        msgs,
        llm=_StubLLM(),
        task="refactor src/api.py",
        keep_last=2,
        threshold=0.0,
    )
    # At threshold=0 anything with any signal is rescued, including
    # the user's leading mention of src/api.py.
    assert len(out.rescued_indices) >= 1


def test_relevance_preserves_summary_for_unrescued_turns():
    msgs = _build_conversation()
    out = compact_messages_relevance(
        msgs,
        llm=_StubLLM(text="generated summary body"),
        task="refactor src/api.py",
        keep_last=2,
        threshold=0.3,
    )
    # Summary block (from the stub LLM) lives in summarised_messages.
    has_summary = any(
        isinstance(m.get("content"), str) and "generated summary body" in m["content"]
        for m in out.result.summarised_messages
    )
    assert has_summary


# ────────────────────────────────────────────────────────────────
# Compact(now=True) tool adapter
# ────────────────────────────────────────────────────────────────


def test_agent_compact_now_returns_status_and_new_transcript():
    msgs = _build_conversation()
    new_msgs, status = agent_compact_now(
        msgs, llm=_StubLLM(), task="refactor src/api.py", keep_last=2
    )
    assert status.ok is True
    assert status.dropped_count >= 1
    assert status.summary_tokens > 0
    # New transcript is shorter (or at most equal) than the original.
    assert len(new_msgs) <= len(msgs) + 2  # rescued may add a couple


def test_agent_compact_now_surfaces_error_without_crashing():
    class _Boom:
        def generate(self, **_kw):
            raise RuntimeError("llm down")

    new_msgs, status = agent_compact_now(
        _build_conversation(),
        llm=_Boom(),
        task="x",
        keep_last=2,
    )
    assert status.ok is False
    assert "llm down" in status.error
    # Original transcript returned unchanged so the loop can keep going.
    assert new_msgs[0]["content"] == "soul"


def test_compact_tool_name_is_exposed():
    assert COMPACT_TOOL_NAME == "Compact"
