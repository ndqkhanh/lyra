"""Phase B (v2.4.0) — chat-mode tool loop.

These tests exercise the new chat-tool loop in
:func:`lyra_cli.interactive.chat_tools.run_chat_tool_loop` as well as
its integration into :func:`lyra_cli.interactive.session._chat_with_llm`
via :func:`_chat_with_tool_loop`. The loop must:

* dispatch every ``tool_call`` the LLM proposes through the registry,
* feed the tool results back to the LLM as a follow-up turn,
* terminate cleanly when the model emits a no-tool-calls reply,
* honour ``ToolApprovalCache`` decisions (yolo / strict / cached
  allow / cached deny / first-time prompt),
* bail out at ``max_steps`` rather than looping forever,
* bill *every* LLM hop, not just the first or last,
* never crash the REPL if the registry refuses a path or the model
  emits a malformed call.

Tests use a pure-Python ``ToolingFakeLLM`` that scripts a sequence of
replies; no network, no real LLM. The chat tools themselves (Read,
Glob, Grep, Edit, Write from ``lyra_core.tools.builtin``) are
exercised end-to-end since they're tiny and stdlib-only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------


class ToolingFakeLLM:
    """Scripted LLM that emits pre-baked ``Message`` replies in order.

    Mirrors the contract of ``LLMProvider``: ``generate(messages,
    tools=…)`` returns a :class:`harness_core.messages.Message`.
    Records every call so the test can assert on which tool spec was
    forwarded, what tool results came back, etc.

    Each script entry is either:

    * a plain string — interpreted as an assistant text reply with
      no tool calls (terminates the loop);
    * a list of ``(tool_name, args)`` tuples — interpreted as a
      :class:`Message.assistant` with that many ``tool_calls``.
    """

    def __init__(
        self,
        script: list[Any],
        *,
        usage: dict[str, int] | None = None,
        model: str = "test-model-x",
    ) -> None:
        self.script = list(script)
        self.calls: list[tuple[list[Any], list[dict[str, Any]] | None]] = []
        self.last_usage: dict[str, int] = (
            dict(usage) if usage is not None else {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        )
        self.model = model
        self.provider_name = "test"

    def generate(
        self,
        messages: list[Any],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> Any:
        from harness_core.messages import Message, StopReason, ToolCall

        self.calls.append((list(messages), list(tools or [])))
        if not self.script:
            return Message.assistant(content="done", stop_reason=StopReason.END_TURN)

        entry = self.script.pop(0)
        if isinstance(entry, str):
            return Message.assistant(content=entry, stop_reason=StopReason.END_TURN)

        # Tool-call entry. Build a deterministic call id from the index
        # in the conversation so test assertions are stable across
        # runs without random suffixes.
        tool_calls = [
            ToolCall(id=f"call_{i}", name=name, args=dict(args))
            for i, (name, args) in enumerate(entry)
        ]
        return Message.assistant(
            content="",
            tool_calls=tool_calls,
            stop_reason=StopReason.TOOL_USE,
        )


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Empty workspace with one sample file the tools can read."""
    (tmp_path / "sample.txt").write_text("hello world\nline two\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def add(a, b):\n    return a + b\n")
    return tmp_path


# ---------------------------------------------------------------------------
# Pure-loop tests (no session, no driver)
# ---------------------------------------------------------------------------


def test_no_tool_calls_returns_text_immediately(repo_root: Path) -> None:
    """A reply with no ``tool_calls`` ends the loop in one hop."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )

    fake = ToolingFakeLLM(["hi there"])
    registry = build_chat_tool_registry(repo_root)

    report = run_chat_tool_loop(
        fake,
        [Message.user("say hi")],
        registry,
    )

    assert report.final_text == "hi there"
    assert report.tool_calls == 0
    assert report.steps == 1
    assert not report.hit_max_steps
    assert len(fake.calls) == 1


def test_one_tool_call_dispatches_and_continues(repo_root: Path) -> None:
    """Tool call → registry execution → result back to LLM → final text."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )

    fake = ToolingFakeLLM(
        [
            [("Read", {"path": "sample.txt"})],
            "the file says: hello world",
        ]
    )
    registry = build_chat_tool_registry(repo_root)

    report = run_chat_tool_loop(
        fake,
        [Message.user("read sample.txt")],
        registry,
    )

    assert report.tool_calls == 1
    assert report.steps == 2
    assert report.final_text == "the file says: hello world"
    # Hop 2's transcript must contain the tool-result message so the
    # LLM had context to continue.
    second_messages, _ = fake.calls[1]
    assert any(getattr(m, "role", "") == "tool" for m in second_messages), (
        "second hop must include a role='tool' message with tool_results"
    )


def test_multi_tool_call_in_single_hop(repo_root: Path) -> None:
    """Multiple tool calls per hop are dispatched in order."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )

    fake = ToolingFakeLLM(
        [
            [
                ("Read", {"path": "sample.txt"}),
                ("Read", {"path": "src/main.py"}),
            ],
            "I read both files.",
        ]
    )
    registry = build_chat_tool_registry(repo_root)
    report = run_chat_tool_loop(
        fake,
        [Message.user("read both")],
        registry,
    )

    assert report.tool_calls == 2
    # The second hop's tool message should bundle BOTH results so the
    # LLM sees them atomically (matches OpenAI tool-message contract).
    _, _ = fake.calls[0]
    second_messages, _ = fake.calls[1]
    tool_msg = [m for m in second_messages if getattr(m, "role", "") == "tool"]
    assert tool_msg
    assert len(tool_msg[-1].tool_results) == 2


def test_max_steps_caps_runaway_loop(repo_root: Path) -> None:
    """Infinite tool calls hit ``max_steps`` and surface a clear flag."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )

    # Always emit one tool call → loop never terminates without a cap.
    fake = ToolingFakeLLM(
        [[("Read", {"path": "sample.txt"})] for _ in range(50)]
    )
    registry = build_chat_tool_registry(repo_root)

    report = run_chat_tool_loop(
        fake,
        [Message.user("loop forever")],
        registry,
        max_steps=3,
    )

    assert report.hit_max_steps
    assert report.steps == 3
    assert report.tool_calls == 3


def test_renderer_emits_call_and_result_events(repo_root: Path) -> None:
    """The render callback fires once per call and once per result."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        ToolEvent,
        build_chat_tool_registry,
        run_chat_tool_loop,
    )

    fake = ToolingFakeLLM(
        [
            [("Glob", {"pattern": "*.txt"})],
            "found one txt file",
        ]
    )
    registry = build_chat_tool_registry(repo_root)
    seen: list[ToolEvent] = []
    run_chat_tool_loop(
        fake,
        [Message.user("find txt files")],
        registry,
        render=seen.append,
    )

    kinds = [e.kind for e in seen]
    assert kinds == ["call", "result"], kinds
    assert seen[0].tool_name == "Glob"
    assert seen[1].is_error is False


def test_approval_deny_blocks_tool(repo_root: Path) -> None:
    """``approve`` returning False short-circuits dispatch."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    fake = ToolingFakeLLM(
        [
            [("Write", {"path": "evil.txt", "content": "x"})],
            "ok i won't",
        ]
    )
    registry = build_chat_tool_registry(repo_root)
    cache = ToolApprovalCache(mode="normal")

    report = run_chat_tool_loop(
        fake,
        [Message.user("write evil.txt")],
        registry,
        approval_cache=cache,
        approve=lambda _name, _args: False,  # deny
    )

    assert report.blocked_calls == 1
    assert report.tool_calls == 1
    # The Write tool must NOT have run — file should not exist.
    assert not (repo_root / "evil.txt").exists()


def test_yolo_mode_skips_approval(repo_root: Path) -> None:
    """``yolo`` mode auto-allows; the approve callback never fires."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    fake = ToolingFakeLLM(
        [
            [("Write", {"path": "yolo.txt", "content": "y"})],
            "wrote it",
        ]
    )
    registry = build_chat_tool_registry(repo_root)
    cache = ToolApprovalCache(mode="yolo")
    approve_calls: list[str] = []

    run_chat_tool_loop(
        fake,
        [Message.user("write yolo.txt")],
        registry,
        approval_cache=cache,
        approve=lambda name, _args: approve_calls.append(name) or True,
    )

    assert approve_calls == [], "yolo must skip approve()"
    assert (repo_root / "yolo.txt").exists()


def test_billing_callback_runs_per_hop(repo_root: Path) -> None:
    """``on_usage`` fires once per ``generate`` call, not just the last."""
    from harness_core.messages import Message
    from lyra_cli.interactive.chat_tools import (
        build_chat_tool_registry,
        run_chat_tool_loop,
    )

    fake = ToolingFakeLLM(
        [
            [("Read", {"path": "sample.txt"})],
            [("Glob", {"pattern": "*.py"})],
            "summary",
        ]
    )
    registry = build_chat_tool_registry(repo_root)
    hops: list[Any] = []

    run_chat_tool_loop(
        fake,
        [Message.user("read and glob")],
        registry,
        on_usage=hops.append,
    )

    assert len(hops) == 3, f"expected 3 billing hooks, got {len(hops)}"


# ---------------------------------------------------------------------------
# End-to-end: chat handler routes through the loop
# ---------------------------------------------------------------------------


def test_session_chat_runs_tool_loop_by_default(repo_root: Path) -> None:
    """``session.dispatch`` plain text must engage the loop and bill."""
    from lyra_cli.interactive.session import InteractiveSession

    fake = ToolingFakeLLM(
        [
            [("Read", {"path": "sample.txt"})],
            "the file starts with hello",
        ]
    )

    session = InteractiveSession(repo_root=repo_root)
    session.mode = "ask"  # plain-text read-only mode (v3.2.0)

    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("what's in sample.txt?")

    # The reply text reaches the user.
    assert "the file starts with hello" in (result.output or "")
    # The loop hopped twice.
    assert len(fake.calls) == 2
    # Billing fired (last_usage was 10/5/15, mocked default).
    assert session.tokens_used > 0


def test_session_chat_tools_can_be_disabled(repo_root: Path) -> None:
    """``chat_tools_enabled = False`` falls back to single-shot generate."""
    from lyra_cli.interactive.session import InteractiveSession

    fake = ToolingFakeLLM(["hi"])
    session = InteractiveSession(repo_root=repo_root)
    session.mode = "ask"
    session.chat_tools_enabled = False

    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("hi")

    assert "hi" in (result.output or "")
    # Without tools, the loop never runs — exactly one ``generate``.
    assert len(fake.calls) == 1


def test_session_chat_skips_loop_for_mock_provider(repo_root: Path) -> None:
    """The harness_core ``MockLLM`` is *not* routed through the loop.

    MockLLM's scripted outputs have no tool support. Routing them
    through the loop wastes a hop; the gate must recognise them by
    class name.
    """
    from harness_core.models import MockLLM

    from lyra_cli.interactive.session import InteractiveSession

    fake = MockLLM(scripted_outputs=["canned reply"])
    session = InteractiveSession(repo_root=repo_root)
    session.mode = "ask"

    with patch("lyra_cli.llm_factory.build_llm", return_value=fake):
        result = session.dispatch("hi")

    assert "canned reply" in (result.output or "")
