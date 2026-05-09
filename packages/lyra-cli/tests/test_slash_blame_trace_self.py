"""Wave-C Task 4: ``/blame`` + ``/trace`` + ``/self``.

These slashes round out the "what just happened?" debugging surface.

* ``/blame [path]`` — git blame for the named (or current) file.
  Skip-on-no-git, same pattern as Wave-B's ``/diff``.
* ``/trace`` — last N events from the new
  :class:`lyra_core.hir.events.RingBuffer` (default cap 1024,
  drop-oldest). The ring buffer auto-subscribes to ``hir.events.emit``
  the first time it's instantiated so any code path that already
  emits HIR events is observable without changes.
* ``/self`` — render the live :class:`InteractiveSession` state as
  YAML-ish key/value pairs (no PyYAML dep — the format is keys-only).
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession
from lyra_core.hir import events as hir_events


# ---- ring buffer ------------------------------------------------------

def test_ring_buffer_captures_recent_emits() -> None:
    """A fresh RingBuffer hooks itself up and starts capturing emits."""
    rb = hir_events.RingBuffer(cap=4)
    try:
        hir_events.emit("provider.selected", name="anthropic")
        hir_events.emit("provider.selected", name="openai")
        hir_events.emit("provider.selected", name="ollama")

        snap = rb.snapshot()
        names = [e["name"] for e in snap]
        assert names == [
            "provider.selected",
            "provider.selected",
            "provider.selected",
        ]
        # Attributes round-trip:
        assert snap[-1]["attrs"]["name"] == "ollama"
    finally:
        rb.detach()


def test_ring_buffer_drops_oldest_past_cap() -> None:
    """RingBuffer(cap=2) keeps only the two most recent events."""
    rb = hir_events.RingBuffer(cap=2)
    try:
        for i in range(5):
            hir_events.emit("test.event", i=i)
        snap = rb.snapshot()
        assert [e["attrs"]["i"] for e in snap] == [3, 4]
    finally:
        rb.detach()


# ---- /trace -----------------------------------------------------------

def test_slash_trace_renders_recent_events(tmp_path: Path) -> None:
    """``/trace`` reads from the global ring buffer attached at import."""
    s = InteractiveSession(repo_root=tmp_path)
    # Emit a couple of events so the trace has content to print.
    hir_events.emit("session.dispatch", line="hello")
    hir_events.emit("session.dispatch", line="world")
    out = s._cmd_trace_text("")
    assert "session.dispatch" in out
    assert "hello" in out or "world" in out


# ---- /blame -----------------------------------------------------------

def test_slash_blame_friendly_outside_git(tmp_path: Path) -> None:
    """No git repo → friendly message, never a traceback."""
    s = InteractiveSession(repo_root=tmp_path)
    out = s._cmd_blame_text("README.md")
    assert "/blame" in out
    assert "git" in out.lower()


# ---- /self -----------------------------------------------------------

def test_slash_self_renders_session_state(tmp_path: Path) -> None:
    """``/self`` emits a key/value rendering of the live session fields."""
    s = InteractiveSession(repo_root=tmp_path, model="mock", mode="plan")
    s.dispatch("first thought")
    out = s._cmd_self_text("")
    # Heading + every salient field appears.
    assert "InteractiveSession" in out or "session:" in out
    for key in ("mode", "model", "turn", "session_id", "repo_root"):
        assert key in out


def test_slash_self_redacts_long_history(tmp_path: Path) -> None:
    """``/self`` truncates the history to keep the slash printable."""
    s = InteractiveSession(repo_root=tmp_path)
    for i in range(50):
        s.dispatch(f"line {i}")
    out = s._cmd_self_text("")
    # Should not blat all 50 history items into the rendering.
    assert out.count("line 0") <= 1
    # And it should call out that there's more than rendered.
    assert "history" in out.lower()
