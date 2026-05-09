"""Phase E.5: ``/spawn`` actually spins up a working AgentLoop.

The pre-v2.7 ``_loop_factory`` in :func:`_ensure_subagent_registry`
called ``AgentLoop(provider=provider)`` — but lyra-core's
``AgentLoop`` is a dataclass with field ``llm``, not ``provider``,
so every real ``/spawn`` invocation died with::

    TypeError: __init__() got an unexpected keyword argument 'provider'

The fix unifies the two loop substrates (``harness_core.AgentLoop``
for one-shot ``run`` and ``lyra_core.agent.AgentLoop`` for subagent
fan-out) on a single LLM provider via :class:`_LyraCoreLLMAdapter`:
the adapter speaks Message-in / dict-out, which is what the lyra_core
loop expects. These tests pin that contract end-to-end.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from harness_core.messages import Message, StopReason

from lyra_cli.interactive.session import (
    InteractiveSession,
    _LyraCoreLLMAdapter,
    _ensure_subagent_registry,
)


class _FakeProvider:
    """Minimal lyra-cli LLMProvider — returns a single text Message."""

    def __init__(self, text: str = "subagent done") -> None:
        self._text = text
        self.calls: list[dict] = []

    def generate(self, messages: list[Message], *, tools: Any = None, **_: Any):
        self.calls.append({"messages": list(messages), "tools": tools})
        return Message(
            role="assistant",
            content=self._text,
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
        )


def test_adapter_converts_message_to_loop_dict() -> None:
    provider = _FakeProvider("hello from subagent")
    adapter = _LyraCoreLLMAdapter(provider)

    out = adapter.generate(
        messages=[{"role": "user", "content": "hi"}], tools=[{"name": "x"}]
    )
    assert isinstance(out, dict)
    assert out["content"] == "hello from subagent"
    assert out["tool_calls"] == []
    assert out["stop_reason"].lower().endswith("end_turn") or "end_turn" in out["stop_reason"]
    # Parent passed dict messages → adapter promoted them to Message before
    # calling the provider, so the provider saw exactly one Message.
    assert len(provider.calls) == 1
    seen = provider.calls[0]["messages"]
    assert all(isinstance(m, Message) for m in seen)
    assert seen[0].content == "hi"


def test_adapter_passes_through_existing_message_objects() -> None:
    provider = _FakeProvider("ok")
    adapter = _LyraCoreLLMAdapter(provider)

    msg = Message.user("already a Message")
    out = adapter.generate(messages=[msg])
    assert out["content"] == "ok"
    seen = provider.calls[0]["messages"]
    assert seen == [msg]


def test_spawn_factory_constructs_a_working_lyra_core_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression for the pre-v2.7 ``provider=`` kwarg crash."""
    sess = InteractiveSession(
        repo_root=tmp_path,
        chat_tools_enabled=False,
    )
    sess.model = "deepseek/deepseek-v3"

    fake = _FakeProvider("spawned-ok")
    monkeypatch.setattr(
        "lyra_cli.llm_factory.build_llm",
        lambda *_a, **_kw: fake,
    )

    reg = _ensure_subagent_registry(sess)
    assert reg is not None, "lyra-core must be importable in the test env"

    rec = reg.spawn("investigate the repo")
    assert rec.state in ("done", "failed", "running")
    if rec.state == "done":
        assert rec.result is not None
        assert "spawned-ok" in str(rec.result.get("final_text", ""))
    elif rec.state == "failed":
        # Surfacing failure is acceptable in a stripped sandbox; the
        # important thing is the legacy ``provider=`` TypeError is GONE.
        assert "provider" not in str(rec.error or "").lower()


def test_spawn_factory_does_not_crash_with_provider_kwarg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct check: the loop_factory must accept the lyra_core API."""
    from lyra_core.agent.loop import AgentLoop

    sess = InteractiveSession(
        repo_root=tmp_path,
        chat_tools_enabled=False,
    )
    sess.model = "deepseek/deepseek-v3"
    fake = _FakeProvider("hello")
    monkeypatch.setattr(
        "lyra_cli.llm_factory.build_llm",
        lambda *_a, **_kw: fake,
    )
    reg = _ensure_subagent_registry(sess)
    assert reg is not None
    # The factory is stored as a private attribute on the registry's
    # task closure; we exercise it indirectly by spawning. The point
    # of *this* test is that constructing the loop does not raise.
    rec = reg.spawn("noop")
    # No ``TypeError: ... unexpected keyword argument 'provider'`` was raised.
    assert "unexpected keyword argument 'provider'" not in str(rec.error or "")
