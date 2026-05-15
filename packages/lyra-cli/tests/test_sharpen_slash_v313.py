"""v3.13 P0-6 — ``/sharpen`` slash test suite.

Covers the imperative→declarative task sharpener stolen from
``forrestchang/andrej-karpathy-skills`` principle 4. The slash
queues a rewrite meta-prompt on ``session.pending_task`` for the
next agent turn to dispatch.

Test isolation mirrors :mod:`test_autonomy_slashes_v313`: a
:class:`_S` stub session carrying only ``session_id`` and
``pending_task``, so this file doesn't drag in the heavyweight
:class:`InteractiveSession` bring-up.
"""
from __future__ import annotations

from pathlib import Path


def _make_session(session_id: str = "s-test"):
    """Minimal InteractiveSession-shaped stub. ``/sharpen`` only
    touches ``pending_task``; nothing else needs to be wired."""

    class _S:
        pass

    s = _S()
    s.session_id = session_id
    s.pending_task = None
    return s


class TestCmdSharpenEmptyArgs:
    def test_empty_args_returns_usage_hint(self) -> None:
        from lyra_cli.interactive.session import _cmd_sharpen

        s = _make_session()
        res = _cmd_sharpen(s, "")
        assert "pass the task to rewrite" in res.output
        assert s.pending_task is None  # no queue without input

    def test_whitespace_only_returns_usage_hint(self) -> None:
        from lyra_cli.interactive.session import _cmd_sharpen

        s = _make_session()
        res = _cmd_sharpen(s, "   \t  ")
        assert "pass the task to rewrite" in res.output
        assert s.pending_task is None


class TestCmdSharpenQueue:
    def test_queues_rewrite_meta_prompt(self) -> None:
        from lyra_cli.interactive.session import _cmd_sharpen

        s = _make_session()
        res = _cmd_sharpen(s, "add input validation to login")

        assert s.pending_task is not None
        # The queued prompt must literally embed the original task
        # so the rewrite is grounded in the user's words.
        assert "add input validation to login" in s.pending_task
        # And it must steer the agent toward the declarative form.
        assert "verifiable goals" in s.pending_task
        assert "Invariants to verify" in s.pending_task
        assert "Failing tests to write FIRST" in s.pending_task
        assert "Minimal implementation" in s.pending_task
        # Crucially: it must tell the agent NOT to start editing.
        assert "Do NOT start editing" in s.pending_task

        # User-facing echo confirms the queue.
        assert "queued" in res.output
        assert "add input validation to login" in res.output

    def test_refuses_overwrite_of_pending_task(self) -> None:
        from lyra_cli.interactive.session import _cmd_sharpen

        s = _make_session()
        s.pending_task = "something else"
        res = _cmd_sharpen(s, "new task")

        assert "already queued" in res.output
        assert s.pending_task == "something else"  # unchanged


class TestRegistry:
    def test_sharpen_is_registered(self) -> None:
        from lyra_cli.interactive.session import COMMAND_REGISTRY

        names = {c.name for c in COMMAND_REGISTRY}
        assert "sharpen" in names

    def test_sharpen_has_args_hint_and_category(self) -> None:
        from lyra_cli.interactive.session import COMMAND_REGISTRY

        by_name = {c.name: c for c in COMMAND_REGISTRY}
        spec = by_name["sharpen"]
        assert spec.args_hint, "/sharpen missing args_hint"
        assert spec.category == "tools-agents"
        # Description names the rewrite pattern so users find it
        # via /help completion.
        assert "verifiable" in spec.description.lower()
