"""Phase E.1 — slash commands now ship honest behavior, not empty hints.

This module pins three deliberate behaviour upgrades made when E.1
demoted the "(stub)" tags from ``/compact``, ``/evals``, and friends:

1.  ``/compact`` actually compacts ``session._chat_history`` instead
    of just halving ``tokens_used`` for show. The most recent
    ``KEEP_RECENT`` messages survive verbatim and earlier turns are
    folded into one ``role="system"`` digest.
2.  ``/evals`` runs the bundled corpus inline via
    ``lyra_cli.commands.evals._run_bundled`` and renders a one-line
    summary, with ``--full`` for the JSON dump. The legacy
    "run lyra evals from a second shell" hint was useless inside
    the REPL.
3.  Stale ``(stub)`` / ``(planned)`` markers have been removed from
    ``/agents``, ``/map``, ``/blame``, ``/spawn``, ``/mcp``,
    ``/voice``, ``/observe``, ``/split``, ``/vote``, ``/ide``,
    ``/pair``, ``/wiki``, ``/team-onboarding``, ``/replay``,
    ``/phase``, ``/catch-up``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# /compact — heuristic prune of older chat history
# ---------------------------------------------------------------------------


def _make_session(tmp_path: Path):
    from lyra_cli.interactive.session import InteractiveSession

    return InteractiveSession(repo_root=tmp_path)


def test_compact_keeps_recent_and_digests_older_messages(tmp_path: Path) -> None:
    sess = _make_session(tmp_path)
    sess._chat_history = [
        {"role": "user", "content": f"old user msg {i}"}
        for i in range(10)
    ] + [
        {"role": "assistant", "content": f"recent reply {i}"}
        for i in range(8)
    ]
    sess.tokens_used = 12_000

    res = sess.dispatch("/compact")

    assert "compact" in res.output.lower()
    assert sess.tokens_used < 12_000
    assert len(sess._chat_history) == 7  # 1 digest + 6 KEEP_RECENT
    digest = sess._chat_history[0]
    assert digest["role"] == "system"
    assert "/compact digest" in digest["content"]
    assert "old user msg 0" in digest["content"]
    surviving_recents = sess._chat_history[1:]
    assert all(m.get("role") == "assistant" for m in surviving_recents)


def test_compact_falls_back_when_history_is_short(tmp_path: Path) -> None:
    sess = _make_session(tmp_path)
    sess._chat_history = [{"role": "user", "content": "hi"}]
    sess.tokens_used = 800

    res = sess.dispatch("/compact")

    assert sess.tokens_used == 400
    assert "no compactable history" in res.output


def test_compact_handles_missing_history_attr(tmp_path: Path) -> None:
    """Fresh sessions never had ``_chat_history`` written to. The
    slash must not raise — it must gracefully degrade to the
    halve-the-counter path."""
    sess = _make_session(tmp_path)
    sess.tokens_used = 2_000
    if hasattr(sess, "_chat_history"):
        delattr(sess, "_chat_history")

    res = sess.dispatch("/compact")

    assert sess.tokens_used == 1_000
    assert "compact" in res.output.lower()


# ---------------------------------------------------------------------------
# /evals — runs the bundled corpus inline
# ---------------------------------------------------------------------------


def test_evals_runs_inline_against_bundled_golden(tmp_path: Path) -> None:
    sess = _make_session(tmp_path)
    res = sess.dispatch("/evals")

    assert "/evals" in res.output
    assert "passed" in res.output
    assert "rate=" in res.output


def test_evals_full_dump_includes_json(tmp_path: Path) -> None:
    sess = _make_session(tmp_path)
    res = sess.dispatch("/evals --full")

    assert "/evals" in res.output
    assert "rate=" in res.output
    body = res.output.split("\n", 1)[1]
    parsed = json.loads(body)
    assert "total" in parsed
    assert "passed" in parsed
    assert isinstance(parsed.get("details"), list)


def test_evals_unknown_corpus_reports_error(tmp_path: Path) -> None:
    sess = _make_session(tmp_path)
    res = sess.dispatch("/evals nonsense-corpus")
    assert "/evals" in res.output
    assert "failed" in res.output.lower() or "unknown" in res.output.lower()


def test_evals_public_corpora_explain_the_external_step(tmp_path: Path) -> None:
    """``swe-bench-pro`` and ``loco-eval`` need a downloaded JSONL,
    so the slash must not pretend to run them inline."""
    sess = _make_session(tmp_path)
    res = sess.dispatch("/evals swe-bench-pro")
    assert "swe-bench-pro" in res.output
    assert "lyra evals" in res.output


# ---------------------------------------------------------------------------
# Description hygiene — stale (stub)/(planned)/(Wave-X) markers gone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "agents",
        "map",
        "blame",
        "spawn",
        "mcp",
        "voice",
        "observe",
        "split",
        "vote",
        "ide",
        "pair",
        "wiki",
        "team-onboarding",
        "replay",
        "phase",
        "catch-up",
    ],
)
def test_command_description_has_no_stale_marker(name: str) -> None:
    """Phase E.2: every advertised command must describe what it
    *actually* does today, not what was once planned. We block four
    well-known offending substrings — ``(stub)``, ``(planned)``,
    ``(Wave-E)``, ``(Wave-F)`` — across all the commands that were
    audited and either wired or relabelled in Phase D / E.
    """
    from lyra_cli.interactive.session import COMMAND_REGISTRY

    spec = next((c for c in COMMAND_REGISTRY if c.name == name), None)
    assert spec is not None, f"/{name} must remain registered"
    desc = spec.description
    forbidden = ("(stub)", "(planned)", "(Wave-E)", "(Wave-F)")
    for token in forbidden:
        assert token not in desc, (
            f"/{name} description still carries stale marker {token!r}: {desc!r}"
        )
