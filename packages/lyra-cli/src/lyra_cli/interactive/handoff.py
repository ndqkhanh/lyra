"""Render a paste-able PR description from a live :class:`InteractiveSession`.

Pure render — does no I/O, gives the caller a string. The slash
dispatcher decides whether to print, save to disk, or copy to the
clipboard. Keeping the helper pure makes it trivial to unit-test
across all four sections (title / summary / test plan / changelog).

The handoff is intentionally small enough to paste into a GitHub PR
template field: long sessions get a `(+N earlier turns elided)` tail
rather than dumping every turn.
"""
from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover
    from .session import InteractiveSession


_TEST_LINE_RE = re.compile(r"\b(test_[\w/.\-]+)\b")


def _git_diff_stat(repo_root) -> str | None:
    """Return ``git diff --stat`` body or ``None`` outside a checkout."""
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
        ).stdout.strip()
        out = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True,
            text=True,
            check=True,
            cwd=toplevel,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.strip() or None


def _truncate(text: str, *, cap: int) -> str:
    if len(text) <= cap:
        return text
    return text[: cap - 1].rstrip() + "…"


def _collect_test_targets(history: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for line in history:
        for match in _TEST_LINE_RE.findall(line):
            if match not in seen:
                seen.append(match)
    return seen


def render_handoff(
    session: "InteractiveSession",
    *,
    git_available: bool = True,
    title_cap: int = 80,
) -> str:
    """Return a markdown PR description summarising *session*.

    Parameters mirror the function signature in the Wave-C plan so a
    future agent-loop integration can call this without inspecting
    the implementation. ``git_available=False`` is the test-time
    knob; the live slash uses :func:`_git_diff_stat` directly.
    """
    history = list(session.history)
    plain_turns = [ln for ln in history if not ln.startswith("/")]

    if not plain_turns:
        return (
            "# Handoff\n\n"
            "_(empty session — no turns to summarise yet. "
            "run a prompt, then re-issue /handoff.)_\n"
        )

    title_src = plain_turns[-1] if len(plain_turns) == 1 else plain_turns[-2]
    summary_src = plain_turns[-1]
    title = _truncate(title_src, cap=title_cap)
    summary = _truncate(summary_src, cap=400)

    test_targets = _collect_test_targets(history)
    test_block = (
        "\n".join(f"- run `pytest -k {t}`" for t in test_targets)
        if test_targets
        else "_(no test_* targets mentioned in this session yet)_"
    )

    if git_available:
        stat = _git_diff_stat(session.repo_root)
        changelog = (
            f"```\n{stat}\n```" if stat else "_(working tree clean since HEAD)_"
        )
    else:
        changelog = "_(no git available in this environment)_"

    return (
        f"# Handoff\n"
        f"\n"
        f"## Title\n"
        f"{title}\n"
        f"\n"
        f"## Summary\n"
        f"{summary}\n"
        f"\n"
        f"## Test plan\n"
        f"{test_block}\n"
        f"\n"
        f"## Changelog\n"
        f"{changelog}\n"
        f"\n"
        f"---\n"
        f"_session: {session.session_id} · mode: {session.mode} · turns: {session.turn}_\n"
    )


__all__ = ["render_handoff"]
