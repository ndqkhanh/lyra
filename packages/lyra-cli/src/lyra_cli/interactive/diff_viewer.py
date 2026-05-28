"""Interactive diff viewer — Phase C Gap 4.

Prompt_toolkit-based diff browser with:
  - Left pane: file list (changed files)
  - Right pane: diff content for selected file
  - Left/right arrows: switch between git-diff and per-turn diffs
  - Up/down arrows: browse files
  - q / Esc: dismiss

Call ``run_diff_viewer(session)`` from ``_cmd_diff`` when no args are given.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

_STYLE = Style.from_dict({
    "left-pane": "bg:#1a1a2e #ffffff",
    "right-pane": "bg:#16213e #e0e0e0",
    "header": "bg:#0f3460 #00E5FF bold",
    "file-selected": "bg:#533483 #7CFFB2 bold",
    "file-normal": "#a0a0a0",
    "addition": "#7CFFB2",
    "deletion": "#FF5370",
    "hunk-header": "#00E5FF bold",
    "context-line": "#6B7280",
    "mode-indicator": "bg:#0f3460 #FFC857 bold",
    "help-bar": "bg:#0f3460 #6B7280 italic",
})


def _get_git_diff(repo_root: Path) -> list[tuple[str, str]]:
    """Return list of (filename, diff_content) pairs from git diff."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10, cwd=str(repo_root),
        )
        stat = result.stdout.strip()
        if not stat:
            return []
    except Exception:
        return []

    # Parse stat output for file list
    files: list[str] = []
    for line in stat.split("\n"):
        if "|" in line:
            fname = line.split("|")[0].strip()
            if fname:
                files.append(fname)

    # Get individual diffs for each file
    results: list[tuple[str, str]] = []
    for fname in files:
        try:
            result = subprocess.run(
                ["git", "diff", "--", fname],
                capture_output=True, text=True, timeout=10, cwd=str(repo_root),
            )
            diff_text = result.stdout.strip()
            if diff_text:
                results.append((fname, diff_text))
        except Exception:
            results.append((fname, "(error reading diff)"))
    return results


def _get_turn_diffs(session: Any) -> list[tuple[str, str]]:
    """Return list of (turn_label, change_description) from session turn snapshots."""
    turns_log = getattr(session, "_turns_log", [])
    if not turns_log:
        return []

    results: list[tuple[str, str]] = []
    for snap in turns_log:
        label = f"turn {snap.turn} [{snap.mode}]"
        lo = snap.line[:150].replace("\n", " ") if snap.line else "(empty prompt)"
        detail = f"prompt: {lo}"
        if getattr(snap, "cost_delta_usd", None):
            detail += f"\ncost: ${snap.cost_delta_usd:.4f}"
        if getattr(snap, "tokens_in", None):
            detail += f"\ntokens: {snap.tokens_in}→{snap.tokens_out}"
        if getattr(snap, "latency_ms", None):
            detail += f"\nlatency: {snap.latency_ms:.0f}ms"
        results.append((label, detail))
    return results


def _colorize_diff(diff_text: str) -> list[tuple[str, str]]:
    """Tokenize a unified diff into (style_key, line) pairs for Rich/prompt_toolkit."""
    tokens: list[tuple[str, str]] = []
    for line in diff_text.split("\n"):
        if line.startswith("+++") or line.startswith("---"):
            tokens.append(("class:hunk-header", line))
        elif line.startswith("@@"):
            tokens.append(("class:hunk-header", line))
        elif line.startswith("+"):
            tokens.append(("class:addition", line))
        elif line.startswith("-"):
            tokens.append(("class:deletion", line))
        else:
            tokens.append(("class:context-line", line))
    return tokens


def _build_help_text(mode: str, selected_idx: int, total: int) -> str:
    return (
        f" mode: [{mode}]  |  ←→ toggle mode  |  ↑↓ browse ({selected_idx + 1}/{total})  "
        f" |  q/Esc dismiss"
    )


class _DiffState:
    """Mutable state for the diff viewer application."""
    def __init__(self, git_diffs: list[tuple[str, str]], turn_diffs: list[tuple[str, str]]):
        self.git_diffs = git_diffs
        self.turn_diffs = turn_diffs
        self.current_mode = "git"  # "git" or "turn"
        self.selected_idx = 0

    @property
    def current_diffs(self) -> list[tuple[str, str]]:
        return self.git_diffs if self.current_mode == "git" else self.turn_diffs

    @property
    def selected_diff(self) -> tuple[str, str] | None:
        diffs = self.current_diffs
        if not diffs:
            return None
        self.selected_idx = max(0, min(self.selected_idx, len(diffs) - 1))
        return diffs[self.selected_idx]


def run_diff_viewer(session: Any, repo_root: Path) -> None:
    """Launch the interactive diff viewer fullscreen application.

    Blocks until the user dismisses with q/Esc.
    """
    git_diffs = _get_git_diff(repo_root)
    turn_diffs = _get_turn_diffs(session)
    state = _DiffState(git_diffs, turn_diffs)

    # ── left pane: file list ──────────────────────────
    def _left_pane_text() -> FormattedText:
        lines: list[tuple[str, str]] = [("class:header", "files\n")]
        diffs = state.current_diffs
        if not diffs:
            lines.append(("", "\n(no changes)"))
            return FormattedText(lines)

        for i, (name, _) in enumerate(diffs):
            style = "class:file-selected" if i == state.selected_idx else "class:file-normal"
            display = name[:45]
            lines.append((style, f"{display}\n"))
        return FormattedText(lines)

    left_control = FormattedTextControl(_left_pane_text)
    left_window = Window(left_control, style="class:left-pane", width=50)

    # ── right pane: diff content ──────────────────────
    def _right_pane_text() -> FormattedText:
        lines: list[tuple[str, str]] = [("class:header", "diff\n")]
        sel = state.selected_diff
        if sel is None:
            lines.append(("", "\n(no changes to display)"))
            return FormattedText(lines)
        _, content = sel
        for token in _colorize_diff(content):
            lines.append(token)
            lines.append(("", "\n"))
        return FormattedText(lines)

    right_control = FormattedTextControl(_right_pane_text)
    right_window = Window(right_control, style="class:right-pane", wrap_lines=True)

    # ── mode indicator ────────────────────────────────
    def _mode_text() -> FormattedText:
        return FormattedText([
            ("class:mode-indicator",
             f" {state.current_mode.upper()} DIFF "),
        ])

    mode_window = Window(
        FormattedTextControl(_mode_text),
        height=1, style="class:header",
    )

    # ── help bar ──────────────────────────────────────
    def _help_text() -> FormattedText:
        total = len(state.current_diffs)
        return FormattedText([
            ("class:help-bar",
             _build_help_text(state.current_mode, state.selected_idx, total)),
        ])

    help_window = Window(
        FormattedTextControl(_help_text),
        height=1, style="class:help-bar",
    )

    # ── key bindings ──────────────────────────────────
    kb = KeyBindings()

    @kb.add("q")
    @kb.add("escape")
    def _dismiss(event: Any) -> None:
        event.app.exit()

    @kb.add("up")
    def _move_up(event: Any) -> None:
        if state.current_diffs:
            state.selected_idx = max(0, state.selected_idx - 1)

    @kb.add("down")
    def _move_down(event: Any) -> None:
        if state.current_diffs:
            state.selected_idx = min(
                len(state.current_diffs) - 1, state.selected_idx + 1
            )

    @kb.add("left")
    def _mode_left(event: Any) -> None:
        state.current_mode = "git" if state.current_mode == "turn" else "turn"
        state.selected_idx = 0

    @kb.add("right")
    def _mode_right(event: Any) -> None:
        state.current_mode = "git" if state.current_mode == "turn" else "turn"
        state.selected_idx = 0

    # ── layout ────────────────────────────────────────
    body = VSplit([left_window, Window(width=1, char="│"), right_window])
    root = HSplit([
        mode_window,
        body,
        help_window,
    ])

    layout = Layout(root)
    app = Application(
        layout=layout,
        key_bindings=kb,
        style=_STYLE,
        full_screen=True,
    )
    app.run()
