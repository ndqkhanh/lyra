"""Contract tests for the real ``/search`` slash UI (v1.7.3).

The `session_search` tool already exists for LLM callers; this pass
wires it into a real **interactive** slash command so users can recall
history on demand::

    > /search ripgrep perf

The command must:

- Return the current session's :class:`CommandResult` with ranked hits
  formatted as plain text (one line per hit).
- Respect a ``--k=<n>`` flag for the number of results (default 5,
  capped to 50).
- Surface a clean "(no matches)" message when the store returns
  nothing.
- Surface a helpful error if no :class:`SessionStore` is attached to
  the session (e.g. running off-disk in a test harness).
- Be discoverable via ``/help`` → ``session`` category.

We **do not** depend on a live SQLite database here; the
:class:`InteractiveSession` takes an injectable ``search_fn`` so the
test can pass a list of fake hits.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _make_session(tmp_path: Path, search_fn=None):
    from lyra_cli.interactive.session import InteractiveSession

    sess = InteractiveSession(repo_root=tmp_path)
    if search_fn is not None:
        # The feature adds an attribute the command looks up.
        sess.search_fn = search_fn  # type: ignore[attr-defined]
    return sess


def test_search_command_is_registered_in_session_category(tmp_path: Path) -> None:
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    spec = next((c for c in COMMAND_REGISTRY if c.name == "search"), None)
    assert spec is not None, "/search must be registered"
    assert spec.category == "session"


def test_search_renders_hits_from_injected_search_fn(tmp_path: Path) -> None:
    hits = [
        {"session_id": "sess-a", "role": "user", "content": "fix ripgrep perf"},
        {"session_id": "sess-b", "role": "assistant", "content": "use rg --json"},
    ]

    def fake(query: str, *, k: int):
        assert query == "ripgrep"
        assert k == 5  # default
        return hits

    sess = _make_session(tmp_path, search_fn=fake)
    res = sess.dispatch("/search ripgrep")

    assert "sess-a" in res.output
    assert "ripgrep perf" in res.output
    assert "sess-b" in res.output


def test_search_respects_k_flag(tmp_path: Path) -> None:
    calls: list[int] = []

    def fake(query: str, *, k: int):
        calls.append(k)
        return []

    sess = _make_session(tmp_path, search_fn=fake)
    sess.dispatch("/search --k=3 bm25")
    assert calls == [3]


def test_search_no_matches_message(tmp_path: Path) -> None:
    sess = _make_session(tmp_path, search_fn=lambda q, *, k: [])
    res = sess.dispatch("/search nothing-here")
    assert "no matches" in res.output.lower()


def test_search_without_search_fn_lazy_boots_default_store(tmp_path: Path) -> None:
    """As of v2.6.0 (Phase D.6) the slash command lazy-boots a default
    FTS5 :class:`SessionStore` at ``<repo>/.lyra/sessions.sqlite`` so
    ``/search`` works out-of-the-box without an injected fn.

    The empty repo case (no chat history) must therefore surface the
    "no matches" message — *not* "unavailable" — and silently
    materialise the default store on the session.
    """
    sess = _make_session(tmp_path, search_fn=None)
    res = sess.dispatch("/search anything")
    low = res.output.lower()
    assert "no matches" in low or "(no matches" in low
    # The lazy default should now be installed on the session so
    # subsequent calls reuse the same store rather than re-bootstrapping.
    assert getattr(sess, "search_fn", None) is not None
    assert getattr(sess, "_session_store", None) is not None


def test_search_requires_query(tmp_path: Path) -> None:
    sess = _make_session(tmp_path, search_fn=lambda q, *, k: [])
    res = sess.dispatch("/search   ")
    assert "usage" in res.output.lower() or "query" in res.output.lower()


def test_search_caps_k_at_50(tmp_path: Path) -> None:
    calls: list[int] = []

    def fake(query: str, *, k: int):
        calls.append(k)
        return []

    sess = _make_session(tmp_path, search_fn=fake)
    sess.dispatch("/search --k=999 rg")
    assert calls == [50]
