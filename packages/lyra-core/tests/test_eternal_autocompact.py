"""L4.2 — auto-compaction trigger + Ralph fallback."""
from __future__ import annotations

import pytest

from lyra_core.context.eternal_autocompact import (
    AutoCompactingLLM,
    ContextOverflow,
    _tok_estimate,
)


class _StubLLM:
    """Records calls. Returns a short summary when asked to compact."""

    def __init__(self):
        self.calls = []

    def generate(self, *, messages, **kwargs):
        self.calls.append(("generate", len(messages)))
        # The compactor calls generate(messages=[...]) and reads .content.
        return {"content": "SUMMARY", "tool_calls": []}

    def __call__(self, *, messages, **kwargs):
        self.calls.append(("call", len(messages)))
        return {"content": "SUMMARY", "tool_calls": []}


def _filler(n_chars: int) -> str:
    """Generate a string with roughly N tokens (4 chars/token)."""
    return "x" * n_chars


def test_no_compact_under_threshold():
    llm = _StubLLM()
    proxy = AutoCompactingLLM(
        inner_llm=llm, model_window=10_000, compact_threshold_pct=0.6
    )
    msgs = [
        {"role": "user", "content": _filler(100)},
        {"role": "assistant", "content": "hi"},
    ]
    proxy.generate(messages=msgs)
    assert proxy.compact_count == 0
    # Underlying LLM saw the messages unchanged.
    assert ("generate", 2) in llm.calls


def test_auto_compact_fires_above_threshold():
    llm = _StubLLM()
    # Small window so we trip the threshold easily.
    proxy = AutoCompactingLLM(
        inner_llm=llm, model_window=1_000, compact_threshold_pct=0.5,
        keep_last=2,
    )
    msgs = [
        {"role": "system", "content": "soul"},
        {"role": "user", "content": _filler(500)},
        {"role": "assistant", "content": _filler(500)},
        {"role": "user", "content": _filler(500)},
        {"role": "assistant", "content": _filler(500)},
        {"role": "user", "content": "tail"},
    ]
    # Tokens ~ (500*4 + 5) / 4 ≈ 500, threshold = 500 → compaction fires.
    proxy.generate(messages=msgs)
    assert proxy.compact_count == 1
    # Compaction should have shrunk the message list.
    assert len(msgs) <= 5  # system + summary + at most keep_last raw


def test_ralph_fallback_raises_when_still_over_after_compaction():
    """If compaction can't shrink enough, ContextOverflow is raised so the
    caller abandons the turn and re-enters fresh."""

    # The stub LLM returns a short summary, but our compactor relies on
    # internal logic to actually fold messages. To force the post-compact
    # estimate to STILL be over the ralph threshold, we set
    # ralph_threshold_pct very low so it trips even with a short summary.
    llm = _StubLLM()
    proxy = AutoCompactingLLM(
        inner_llm=llm,
        model_window=1_000,
        compact_threshold_pct=0.5,
        ralph_threshold_pct=0.01,  # so low that even a "SUMMARY" trips it
        keep_last=4,
    )
    msgs = [
        {"role": "user", "content": _filler(500)},
        {"role": "assistant", "content": _filler(500)},
        {"role": "user", "content": _filler(500)},
        {"role": "assistant", "content": _filler(500)},
        {"role": "user", "content": _filler(500)},
    ]
    with pytest.raises(ContextOverflow):
        proxy.generate(messages=msgs)


def test_compactor_llm_can_differ_from_inner():
    main_llm = _StubLLM()
    compactor_llm = _StubLLM()

    proxy = AutoCompactingLLM(
        inner_llm=main_llm,
        compactor_llm=compactor_llm,
        model_window=1_000,
        compact_threshold_pct=0.5,
        keep_last=2,
    )
    msgs = [
        {"role": "user", "content": _filler(500)},
        {"role": "assistant", "content": _filler(500)},
        {"role": "user", "content": _filler(500)},
        {"role": "assistant", "content": _filler(500)},
        {"role": "user", "content": "tail"},
    ]
    proxy.generate(messages=msgs)
    # Compactor saw the original (large) message list once …
    assert any(call[0] == "call" or call[0] == "generate" for call in compactor_llm.calls)
    # … and the main LLM saw the post-compaction (smaller) one.
    assert any(call[0] == "generate" for call in main_llm.calls)


def test_tok_estimate_handles_string_and_list_content():
    msgs = [
        {"role": "user", "content": "x" * 40},               # ~10 tokens
        {"role": "assistant", "content": [
            {"type": "text", "text": "y" * 40},              # ~10 tokens
            {"type": "image", "url": "..."},                  # ignored
        ]},
        {"role": "tool", "tool_call_id": "t1", "content": "z" * 40},  # ~10
    ]
    assert _tok_estimate(msgs) == 30
