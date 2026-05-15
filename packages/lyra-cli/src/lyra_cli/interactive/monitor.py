"""Monitor commands — Wave G.

``/monitor`` and ``/aer`` slash handlers.

``/monitor`` — operator fleet view grouped by attention priority (doc 325).
``/aer``     — Agent Execution Record viewer derived from session message history.

Both follow the ``(session, args: str) -> CommandResult`` contract and never raise.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Result proxy
# ---------------------------------------------------------------------------

def _result_class() -> type:
    try:
        from .session import CommandResult  # type: ignore[attr-defined]
        return CommandResult
    except Exception:
        from lyra_cli.commands.registry import CommandResult as _R
        return _R


def _ok(text: str, renderable: Any = None) -> Any:
    cls = _result_class()
    if renderable is not None:
        return cls(output=text, renderable=renderable)
    return cls(output=text)


# ---------------------------------------------------------------------------
# Attention priority (doc 325)
# ---------------------------------------------------------------------------

# (priority_label, emoji, border_color, states)
_PRIORITY_GROUPS: list[tuple[str, str, str, frozenset[str]]] = [
    ("P0 Needs Attention",  "🔴", "#FF5370", frozenset({"needs_input", "failed"})),
    ("P1 Ready for Review", "🟡", "#FFC857", frozenset({"ready_for_review"})),
    ("P2 Working",          "🔵", "#00E5FF", frozenset({"working"})),
    ("P3 Completed",        "✅", "#7CFFB2", frozenset({"completed"})),
]


def _priority_for(state: str) -> str:
    for label, emoji, _, states in _PRIORITY_GROUPS:
        if state in states:
            return f"{emoji} {label}"
    return f"❓ {state}"


def _priority_sort_key(state: str) -> int:
    for idx, (_, _, _, states) in enumerate(_PRIORITY_GROUPS):
        if state in states:
            return idx
    return 99


# ---------------------------------------------------------------------------
# Session file reader
# ---------------------------------------------------------------------------

_SESSIONS_DIR = Path.home() / ".lyra" / "sessions"


def _read_session_files() -> list[dict[str, Any]]:
    """Read all ``*.json`` files under ``~/.lyra/sessions/``."""
    if not _SESSIONS_DIR.is_dir():
        return []
    sessions: list[dict[str, Any]] = []
    for f in sorted(_SESSIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                sessions.append(data)
        except Exception:
            pass
    return sessions


# ---------------------------------------------------------------------------
# /monitor
# ---------------------------------------------------------------------------

def cmd_monitor(session: Any, args: str) -> Any:
    """Operator fleet view — sessions grouped by attention priority."""
    try:
        from rich.box import ROUNDED, SIMPLE
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        _has_rich = True
    except ImportError:
        _has_rich = False

    all_sessions = _read_session_files()

    if not all_sessions:
        # Show current session stats
        sid = getattr(session, "session_id", "unknown")
        turn = getattr(session, "turn", 0)
        model = getattr(session, "model", "auto")
        cost = getattr(session, "cost_usd", 0.0)
        plain = (
            f"No other sessions tracked.\n"
            f"current session: {sid}\n"
            f"  model={model}  turns={turn}  cost=${cost:.4f}"
        )
        return _ok(plain)

    # Sort by priority then last_activity
    all_sessions.sort(
        key=lambda s: (
            _priority_sort_key(str(s.get("state", s.get("status", "")))),
            str(s.get("last_activity", s.get("updated_at", ""))),
        )
    )

    plain_lines = [f"fleet: {len(all_sessions)} session(s)"]
    plain_lines.append(
        f"  {'priority':<26}  {'session_id':<28}  {'model':<16}  "
        f"{'turns':>5}  {'cost':>8}  {'status':<16}  last_activity"
    )
    plain_lines.append("  " + "-" * 120)

    for s in all_sessions:
        state = str(s.get("state", s.get("status", "unknown")))
        plain_lines.append(
            f"  {_priority_for(state):<26}  "
            f"{str(s.get('session_id', '?'))[:28]:<28}  "
            f"{str(s.get('model', '?'))[:16]:<16}  "
            f"{s.get('turn', s.get('turns', '?'))!s:>5}  "
            f"${float(s.get('cost_usd', 0)):>7.4f}  "
            f"{state:<16}  "
            f"{s.get('last_activity', s.get('updated_at', ''))[:19]!s}"
        )
    plain = "\n".join(plain_lines)

    if not _has_rich:
        return _ok(plain)

    from rich.box import ROUNDED, SIMPLE
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    state_colors: dict[str, str] = {
        "needs_input":     "#FF5370",
        "failed":          "#FF5370",
        "ready_for_review": "#FFC857",
        "working":         "#00E5FF",
        "completed":       "#7CFFB2",
    }

    t = Table(box=SIMPLE, show_header=True, show_edge=False, pad_edge=False)
    t.add_column("priority",      style="bright_white",  no_wrap=True, width=26)
    t.add_column("session_id",    style="#00E5FF",        no_wrap=True, width=28)
    t.add_column("model",         style="#7CFFB2",        no_wrap=True, width=16)
    t.add_column("turns",         justify="right",        width=6)
    t.add_column("cost",          justify="right",        width=9)
    t.add_column("status",        no_wrap=True,           width=18)
    t.add_column("last_activity", style="#6B7280")

    for s in all_sessions:
        state = str(s.get("state", s.get("status", "unknown")))
        color = state_colors.get(state, "#6B7280")
        turns_val = str(s.get("turn", s.get("turns", "?")))
        cost_val = f"${float(s.get('cost_usd', 0)):.4f}"
        last_act = str(s.get("last_activity", s.get("updated_at", "")))[:19]
        t.add_row(
            _priority_for(state),
            str(s.get("session_id", "?"))[:28],
            str(s.get("model", "?"))[:16],
            turns_val,
            cost_val,
            Text(state, style=f"bold {color}"),
            last_act,
        )

    panel = Panel(
        t,
        box=ROUNDED,
        border_style="#7C4DFF",
        title="[bold #00E5FF]fleet monitor[/]",
        title_align="left",
        subtitle=f"[dim]{len(all_sessions)} session(s)[/]",
        subtitle_align="right",
    )
    return _ok(plain, panel)


# ---------------------------------------------------------------------------
# AER step-type classifier
# ---------------------------------------------------------------------------

_STEP_PATTERNS: list[tuple[str, list[str]]] = [
    ("intent_classification", ["intent", "classify", "understand", "goal", "what do you want"]),
    ("verification",          ["verify", "check", "assert", "test", "pass", "fail", "correct"]),
    ("tool_execution",        ["tool", "execute", "run", "bash", "file", "read", "write", "edit"]),
    ("synthesis",             ["summary", "synthesize", "combine", "result", "conclusion", "answer"]),
]


def _infer_step_type(content: str) -> str:
    low = content.lower()
    best = ("synthesis", 0)
    for step_type, keywords in _STEP_PATTERNS:
        hits = sum(1 for kw in keywords if kw in low)
        if hits > best[1]:
            best = (step_type, hits)
    return best[0]


# ---------------------------------------------------------------------------
# /aer
# ---------------------------------------------------------------------------

def cmd_aer(session: Any, args: str) -> Any:
    """Agent Execution Record viewer."""
    raw = (args or "").strip()
    timeline_mode = raw == "timeline"
    target_sid = "" if timeline_mode else raw

    # Resolve target session data
    current_sid = str(getattr(session, "session_id", "unknown"))
    use_current = not target_sid or target_sid == current_sid

    if use_current:
        # Derive from current session's chat history / history
        chat_history: list[Any] = getattr(session, "_chat_history", []) or getattr(session, "history", [])
    else:
        # Try to load from file
        candidate = _SESSIONS_DIR / f"{target_sid}.json"
        chat_history = []
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                chat_history = data.get("history", data.get("messages", []))
            except Exception:
                pass
        if not chat_history:
            return _ok(f"no AER data found for session {target_sid!r}")

    # Build turn records
    records: list[dict[str, Any]] = []
    turn_num = 0
    for item in chat_history:
        if isinstance(item, str):
            turn_num += 1
            records.append({
                "turn":      turn_num,
                "role":      "user",
                "step_type": "intent_classification",
                "snippet":   item[:80],
                "tokens":    len(item) // 4,
            })
        elif isinstance(item, dict):
            role = item.get("role", "unknown")
            content = item.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            if role == "user":
                turn_num += 1
            records.append({
                "turn":      turn_num,
                "role":      role,
                "step_type": _infer_step_type(content),
                "snippet":   content[:80],
                "tokens":    len(content) // 4,
            })

    if not records:
        return _ok(f"no message history found for session {current_sid if use_current else target_sid}")

    # Timeline mode — flat event list
    if timeline_mode:
        plain_lines = [f"AER timeline — {len(records)} event(s)"]
        for r in records:
            plain_lines.append(
                f"  [{r['turn']:>3}] {r['role']:<10}  {r['step_type']:<24}  "
                f"tokens={r['tokens']:<5}  {r['snippet']}"
            )
        return _ok("\n".join(plain_lines))

    # Table mode
    plain_lines = [f"AER — {len(records)} record(s)"]
    plain_lines.append(
        f"  {'turn':>4}  {'role':<12}  {'step_type':<24}  {'snippet':<56}  tokens"
    )
    plain_lines.append("  " + "-" * 110)
    for r in records:
        plain_lines.append(
            f"  {r['turn']:>4}  {r['role']:<12}  {r['step_type']:<24}  "
            f"{r['snippet']:<56}  {r['tokens']}"
        )
    plain = "\n".join(plain_lines)

    try:
        from rich.box import ROUNDED, SIMPLE
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        _has_rich = True
    except ImportError:
        _has_rich = False

    if not _has_rich:
        return _ok(plain)

    from rich.box import ROUNDED, SIMPLE
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    step_colors: dict[str, str] = {
        "intent_classification": "#FFC857",
        "tool_execution":        "#00E5FF",
        "synthesis":             "#7CFFB2",
        "verification":          "#FF2D95",
    }

    t = Table(box=SIMPLE, show_header=True, show_edge=False, pad_edge=False)
    t.add_column("turn",      style="#6B7280",     justify="right", width=5)
    t.add_column("role",      style="bold #00E5FF", no_wrap=True,   width=12)
    t.add_column("step_type", no_wrap=True,                         width=24)
    t.add_column("snippet",   style="bright_white")
    t.add_column("tokens",    justify="right",                      width=7)

    for r in records:
        color = step_colors.get(r["step_type"], "#6B7280")
        t.add_row(
            str(r["turn"]),
            r["role"],
            Text(r["step_type"], style=f"bold {color}"),
            r["snippet"],
            str(r["tokens"]),
        )

    sid_label = current_sid if use_current else target_sid
    panel = Panel(
        t,
        box=ROUNDED,
        border_style="#7C4DFF",
        title=f"[bold #00E5FF]AER[/]  [dim]{sid_label[:40]}[/]",
        title_align="left",
        subtitle=f"[dim]{len(records)} records[/]",
        subtitle_align="right",
    )
    return _ok(plain, panel)


__all__ = ["cmd_aer", "cmd_monitor"]
