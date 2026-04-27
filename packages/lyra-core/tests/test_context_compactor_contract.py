"""Contract tests for the real LLM-driven message compactor (v1.7.3).

The v1 ``compact(items, target_tokens)`` function operates on
``ContextItem`` layers for the 5-layer pipeline. This new surface
operates on the *conversation transcript* (``list[dict]`` messages),
keeps the last N turns raw, and summarises everything before into a
single system-role message via an injected LLM callable.

Invariants tested here:

- ``CompactResult`` returns BOTH the kept-raw turns AND the summary so
  the caller can archive the dropped raw turns side-channel before
  writing only the summary into live context (supports ``/uncompact``
  rollback later).
- ``keep_last`` is honoured exactly — the tail N messages pass through
  unmodified.
- SOUL / system role messages at the head are *always* preserved
  verbatim; they are never summarised and never count against
  ``keep_last``.
- ``dropped_count`` equals the number of non-system messages that were
  folded into the summary.
- The summary is a single message with ``role == "system"`` whose
  content begins with a recognisable marker so downstream logging can
  spot compacted runs in a transcript.
- ``summary_tokens`` is computed via the same ``_tok_estimate`` the
  rest of the context pipeline uses so token arithmetic composes.
"""
from __future__ import annotations

from typing import Any

import pytest

from lyra_core.context.compactor import CompactResult, compact_messages
from lyra_core.context.pipeline import _tok_estimate


def _fake_llm(summary: str):
    """Return a callable matching ``AgentLoop._invoke_llm`` shape.

    The real ``AgentLoop`` calls ``llm.generate(messages=..., tools=...)``
    and expects a mapping with ``content`` / ``tool_calls`` / ``stop_reason``.
    Compactor only needs ``content``, so we ship a minimal double.
    """

    calls: list[dict] = []

    def _generate(**kwargs: Any) -> dict:
        calls.append(kwargs)
        return {"content": summary, "tool_calls": [], "stop_reason": "end_turn"}

    _generate.calls = calls  # type: ignore[attr-defined]
    return _generate


def _long_transcript(n: int) -> list[dict]:
    """Build a transcript of ``n`` alternating user/assistant turns."""
    out: list[dict] = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        out.append({"role": role, "content": f"{role} turn #{i}: " + ("x" * 200)})
    return out


# ---- 1. keep_last semantics ---------------------------------------- #


def test_keeps_last_n_turns_raw() -> None:
    messages = _long_transcript(10)
    llm = _fake_llm("summary: earlier turns")

    result = compact_messages(messages, llm=llm, keep_last=4)

    assert isinstance(result, CompactResult)
    assert result.kept_raw == messages[-4:]


# ---- 2. head is summarised via LLM --------------------------------- #


def test_summarises_head_block_via_llm() -> None:
    messages = _long_transcript(10)
    summary_text = "summary: user explored compactor, wrote tests"
    llm = _fake_llm(summary_text)

    result = compact_messages(messages, llm=llm, keep_last=4)

    assert summary_text in result.summary
    assert result.dropped_count == 6  # 10 total - 4 kept
    assert len(llm.calls) == 1
    call = llm.calls[0]
    # Summariser must hand the LLM the exact head block it's meant to
    # condense (not the tail, not the whole transcript).
    assert "messages" in call
    sent = call["messages"]
    head_contents = {m["content"] for m in messages[:6]}
    sent_contents = {m["content"] for m in sent if m["role"] != "system"}
    assert head_contents.issubset(sent_contents)


# ---- 3. SOUL / system preservation --------------------------------- #


def test_preserves_system_soul_messages() -> None:
    soul = {"role": "system", "content": "# SOUL\nYou are Lyra."}
    messages = [soul] + _long_transcript(10)
    llm = _fake_llm("summary: condensed 10 turns")

    result = compact_messages(messages, llm=llm, keep_last=4)

    # System/SOUL rides through unmodified and does NOT count against
    # keep_last (the 4 kept turns are still the last 4 user/assistant).
    # ``summarised_messages`` exposes the compacted transcript ready to
    # drop into the live context.
    compacted = result.summarised_messages
    assert compacted[0] == soul
    # Exactly one summary message (role=system) after SOUL.
    assert compacted[1]["role"] == "system"
    assert compacted[1]["content"].startswith("[compacted")
    assert compacted[-4:] == messages[-4:]


# ---- 4. dropped_count == number of messages folded in -------------- #


def test_returns_dropped_count_matches_summary_replacement() -> None:
    messages = _long_transcript(12)
    llm = _fake_llm("s")

    result = compact_messages(messages, llm=llm, keep_last=3)

    # 12 total, keep last 3 → 9 folded into the summary.
    assert result.dropped_count == 9
    compacted = result.summarised_messages
    assert len(compacted) == 1 + 3  # 1 summary + 3 kept raw


# ---- 5. summary_tokens counted via shared heuristic ---------------- #


def test_compactresult_tokens_are_counted() -> None:
    messages = _long_transcript(8)
    summary = "summary: x" * 50
    llm = _fake_llm(summary)

    result = compact_messages(messages, llm=llm, keep_last=2)

    # Must match the project-wide ``_tok_estimate`` heuristic so the
    # compactor composes with ``ContextItem.estimated_tokens`` and the
    # ``/context`` grid arithmetic.
    assert result.summary_tokens == _tok_estimate(result.summary)
    assert result.summary_tokens > 0


# ---- 6. empty / small transcripts become no-ops -------------------- #


def test_short_transcript_is_a_no_op() -> None:
    messages = _long_transcript(3)
    llm = _fake_llm("should never be called")

    result = compact_messages(messages, llm=llm, keep_last=4)

    # Fewer compactable messages than keep_last → nothing to summarise,
    # LLM must not be invoked, and ``summarised_messages`` equals input.
    assert result.dropped_count == 0
    assert result.summary == ""
    assert result.summary_tokens == 0
    assert result.summarised_messages == messages
    assert len(llm.calls) == 0


# ---- 7. max_summary_tokens is respected ---------------------------- #


def test_max_summary_tokens_passed_to_llm() -> None:
    messages = _long_transcript(10)
    llm = _fake_llm("s")

    compact_messages(messages, llm=llm, keep_last=2, max_summary_tokens=321)

    assert len(llm.calls) == 1
    call = llm.calls[0]
    # The summariser must surface the ceiling to the LLM so the model
    # can size its output. We accept either an explicit kwarg or a
    # system-prompt mention — the interface is the integer, the
    # delivery detail is implementation.
    flat = str(call)
    assert "321" in flat


# ---- 8. keep_last must be > 0 -------------------------------------- #


def test_keep_last_zero_raises() -> None:
    with pytest.raises(ValueError):
        compact_messages(_long_transcript(4), llm=_fake_llm("s"), keep_last=0)
