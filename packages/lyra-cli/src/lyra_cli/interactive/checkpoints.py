"""Checkpoint commands — Wave F.

``/checkpoint``, ``/rollback``, and ``/verify`` slash handlers.

All handlers follow the ``(session, args: str) -> CommandResult`` contract
from :mod:`lyra_cli.interactive.session` and never raise.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Result-class proxy — lazy so this module can be imported independently.
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
# Helpers
# ---------------------------------------------------------------------------

def _checkpoints_dir(session: Any) -> Path:
    sid = getattr(session, "session_id", "unknown")
    return Path.home() / ".lyra" / "checkpoints" / str(sid)


def _last_user_message(session: Any) -> str:
    history: list[str] = getattr(session, "history", [])
    for item in reversed(history):
        if isinstance(item, str):
            return item[:200]
    return ""


def _checkpoint_data(session: Any, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "session_id": str(getattr(session, "session_id", "unknown")),
        "turn": getattr(session, "turn", 0),
        "model": getattr(session, "model", "auto"),
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "message_count": len(getattr(session, "history", [])),
        "last_user_message": _last_user_message(session),
        "cost_usd": round(getattr(session, "cost_usd", 0.0), 6),
        "mode": getattr(session, "mode", "edit_automatically"),
        "pending_task": getattr(session, "pending_task", None),
    }


# ---------------------------------------------------------------------------
# /checkpoint
# ---------------------------------------------------------------------------

def cmd_checkpoint(session: Any, args: str) -> Any:
    """Save current agent state to ``~/.lyra/checkpoints/<session_id>/<label>.json``."""
    try:
        import rich as _rich  # noqa: F401 — presence check only
        _has_rich = True
    except ImportError:
        _has_rich = False

    label = args.strip() or f"turn-{getattr(session, 'turn', 0)}"
    data = _checkpoint_data(session, label)

    try:
        cp_dir = _checkpoints_dir(session)
        cp_dir.mkdir(parents=True, exist_ok=True)
        cp_file = cp_dir / f"{label}.json"
        cp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        return _ok(f"checkpoint save failed: {exc}")

    plain = (
        f"checkpoint saved: {label}\n"
        f"  file:  {cp_file}\n"
        f"  turn:  {data['turn']}\n"
        f"  model: {data['model']}\n"
        f"  cost:  ${data['cost_usd']:.4f}"
    )

    if not _has_rich:
        return _ok(plain)

    from rich.box import ROUNDED
    from rich.panel import Panel
    from rich.table import Table

    t = Table(box=None, show_header=False, show_edge=False, pad_edge=False, padding=(0, 2))
    t.add_column(style="bold #00E5FF", no_wrap=True)
    t.add_column(style="bright_white")
    t.add_row("label",   label)
    t.add_row("file",    str(cp_file))
    t.add_row("turn",    str(data["turn"]))
    t.add_row("model",   data["model"])
    t.add_row("cost",    f"${data['cost_usd']:.4f}")
    t.add_row("mode",    data["mode"])
    if data["pending_task"]:
        t.add_row("task", data["pending_task"][:80])

    panel = Panel(
        t,
        box=ROUNDED,
        border_style="#7C4DFF",
        title="[bold #7CFFB2]checkpoint saved[/]",
        title_align="left",
    )
    return _ok(plain, panel)


# ---------------------------------------------------------------------------
# /rollback
# ---------------------------------------------------------------------------

def cmd_rollback(session: Any, args: str) -> Any:
    """Restore session config from a prior checkpoint, or list all checkpoints."""
    cp_dir = _checkpoints_dir(session)
    label = args.strip()

    # --- no args: list all checkpoints ---
    if not label:
        if not cp_dir.is_dir():
            return _ok("no checkpoints found for this session")

        files = sorted(cp_dir.glob("*.json"))
        if not files:
            return _ok("no checkpoints found for this session")

        rows: list[tuple[str, str, str, str]] = []
        for f in files:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                rows.append((
                    d.get("label", f.stem),
                    str(d.get("turn", "?")),
                    d.get("timestamp", "")[:19].replace("T", " "),
                    d.get("model", "?"),
                ))
            except Exception:
                rows.append((f.stem, "?", "?", "?"))

        plain_lines = ["checkpoints:"]
        for r in rows:
            plain_lines.append(f"  {r[0]:<24}  turn={r[1]:<6}  {r[2]}  {r[3]}")
        plain = "\n".join(plain_lines)

        try:
            from rich.box import ROUNDED, SIMPLE
            from rich.panel import Panel
            from rich.table import Table
            t = Table(box=SIMPLE, show_header=True, show_edge=False, pad_edge=False)
            t.add_column("label",     style="bold #00E5FF")
            t.add_column("turn",      style="bright_white", justify="right")
            t.add_column("timestamp", style="#6B7280")
            t.add_column("model",     style="#7CFFB2")
            for r in rows:
                t.add_row(*r)
            panel = Panel(
                t,
                box=ROUNDED,
                border_style="#7C4DFF",
                title="[bold #00E5FF]checkpoints[/]",
                title_align="left",
            )
            return _ok(plain, panel)
        except Exception:
            return _ok(plain)

    # --- args given: load a checkpoint ---
    cp_file = cp_dir / f"{label}.json"
    if not cp_file.exists():
        # try stem match without .json
        candidates = list(cp_dir.glob(f"{label}*.json")) if cp_dir.is_dir() else []
        if len(candidates) == 1:
            cp_file = candidates[0]
        elif len(candidates) > 1:
            names = ", ".join(c.stem for c in candidates)
            return _ok(f"ambiguous label {label!r}: matches {names}")
        else:
            return _ok(f"checkpoint not found: {label!r}")

    try:
        data = json.loads(cp_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return _ok(f"failed to read checkpoint: {exc}")

    # Restore config fields
    for attr in ("model", "mode", "pending_task"):
        if attr in data:
            try:
                setattr(session, attr, data[attr])
            except Exception:
                pass

    note = "Note: message history rollback requires session restart. Config fields restored to session."
    plain = (
        f"rollback preview — {data.get('label', label)}\n"
        f"  turn:         {data.get('turn', '?')}\n"
        f"  model:        {data.get('model', '?')}\n"
        f"  mode:         {data.get('mode', '?')}\n"
        f"  cost_usd:     ${data.get('cost_usd', 0):.4f}\n"
        f"  pending_task: {data.get('pending_task') or '—'}\n"
        f"  timestamp:    {data.get('timestamp', '?')[:19].replace('T', ' ')}\n"
        f"\n{note}"
    )

    try:
        from rich.box import ROUNDED
        from rich.console import Group
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        t = Table(box=None, show_header=False, show_edge=False, pad_edge=False, padding=(0, 2))
        t.add_column(style="bold #00E5FF", no_wrap=True)
        t.add_column(style="bright_white")
        t.add_row("label",        data.get("label", label))
        t.add_row("turn",         str(data.get("turn", "?")))
        t.add_row("model",        data.get("model", "?"))
        t.add_row("mode",         data.get("mode", "?"))
        t.add_row("cost_usd",     f"${data.get('cost_usd', 0):.4f}")
        t.add_row("pending_task", data.get("pending_task") or "—")
        t.add_row("timestamp",    str(data.get("timestamp", "?"))[:19].replace("T", " "))
        note_text = Text(note, style="italic #6B7280")
        panel = Panel(
            Group(t, note_text),
            box=ROUNDED,
            border_style="#FFC857",
            title=f"[bold #FFC857]rollback: {data.get('label', label)}[/]",
            title_align="left",
        )
        return _ok(plain, panel)
    except Exception:
        return _ok(plain)


# ---------------------------------------------------------------------------
# /verify
# ---------------------------------------------------------------------------

def _parse_verify_args(args: str) -> tuple[str | None, str | None, str]:
    """Parse ``--spec <file>``, ``--rubric "..."`` or bare text.

    Returns ``(spec_path_str, rubric_inline, bare_rest)``.
    """
    import shlex
    try:
        tokens = shlex.split(args)
    except ValueError:
        tokens = args.split()

    spec_path: str | None = None
    rubric: str | None = None
    bare_parts: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "--spec" and i + 1 < len(tokens):
            spec_path = tokens[i + 1]
            i += 2
        elif tok == "--rubric" and i + 1 < len(tokens):
            rubric = tokens[i + 1]
            i += 2
        else:
            bare_parts.append(tok)
            i += 1
    return spec_path, rubric, " ".join(bare_parts)


def _split_criteria(text: str) -> list[str]:
    """Split a criteria string into testable sub-criteria."""
    lines = [ln.strip().lstrip("-•*").strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if len(ln) > 3]
    if not lines:
        lines = [s.strip() for s in text.split(".") if len(s.strip()) > 3]
    if not lines:
        lines = [text.strip()]
    return lines


def _score_criterion(criterion: str, content: str) -> tuple[str, int]:
    """Return (pass|partial|fail, score 0/50/100) for one criterion."""
    crit_lower = criterion.lower()
    content_lower = content.lower()

    keywords = [w for w in crit_lower.split() if len(w) > 3]
    if not keywords:
        return "partial", 50

    matches = sum(1 for kw in keywords if kw in content_lower)
    ratio = matches / len(keywords)

    if ratio >= 0.7:
        return "pass", 100
    if ratio >= 0.3:
        return "partial", 50
    return "fail", 0


def cmd_verify(session: Any, args: str) -> Any:
    """Rubric-based evaluator — scores last assistant output against acceptance criteria."""
    try:
        from rich.box import ROUNDED, SIMPLE
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        _has_rich = True
    except ImportError:
        _has_rich = False

    spec_path_str, rubric_inline, bare = _parse_verify_args(args)

    # Resolve criteria text
    criteria_text: str = ""
    if spec_path_str:
        try:
            criteria_text = Path(spec_path_str).read_text(encoding="utf-8")
        except Exception as exc:
            return _ok(f"could not read spec file: {exc}")
    elif rubric_inline:
        criteria_text = rubric_inline
    elif bare:
        criteria_text = bare
    else:
        # Fall back to session.pending_task
        criteria_text = getattr(session, "pending_task", None) or ""

    if not criteria_text.strip():
        return _ok(
            "no criteria supplied; pass --spec <file>, --rubric \"...\", "
            "or set a pending_task on the session"
        )

    # Resolve last assistant message from history
    history: list[Any] = getattr(session, "history", [])
    last_assistant = ""
    for item in reversed(history):
        if isinstance(item, str):
            last_assistant = item
            break
        if isinstance(item, dict) and item.get("role") == "assistant":
            content = item.get("content", "")
            last_assistant = content if isinstance(content, str) else str(content)
            break

    if not last_assistant:
        # Also check _chat_history if present
        chat_history: list[Any] = getattr(session, "_chat_history", [])
        for item in reversed(chat_history):
            if isinstance(item, dict) and item.get("role") == "assistant":
                content = item.get("content", "")
                last_assistant = content if isinstance(content, str) else str(content)
                break

    criteria_list = _split_criteria(criteria_text)
    results: list[tuple[str, str, int]] = []
    for crit in criteria_list:
        verdict, score = _score_criterion(crit, last_assistant)
        results.append((crit, verdict, score))

    total = sum(s for _, _, s in results)
    overall = round(total / len(results)) if results else 0

    status_map = {"pass": "PASS", "partial": "PARTIAL", "fail": "FAIL"}
    plain_lines = [f"verify score: {overall}/100"]
    for crit, verdict, _score in results:
        plain_lines.append(f"  [{status_map[verdict]}]  {crit[:72]}")
    plain = "\n".join(plain_lines)

    if not _has_rich:
        return _ok(plain)

    from rich.box import ROUNDED, SIMPLE
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    verdict_styles = {"pass": "#7CFFB2", "partial": "#FFC857", "fail": "#FF5370"}

    t = Table(box=SIMPLE, show_header=True, show_edge=False, pad_edge=False)
    t.add_column("#",         style="#6B7280", justify="right", width=3)
    t.add_column("criterion", style="bright_white")
    t.add_column("result",    justify="center", no_wrap=True, width=9)
    t.add_column("score",     justify="right",  width=6)

    for idx, (crit, verdict, score) in enumerate(results, 1):
        vstyle = verdict_styles.get(verdict, "#6B7280")
        t.add_row(
            str(idx),
            crit[:72],
            Text(status_map[verdict], style=f"bold {vstyle}"),
            Text(str(score), style=vstyle),
        )

    score_color = "#7CFFB2" if overall >= 70 else "#FFC857" if overall >= 40 else "#FF5370"
    panel = Panel(
        t,
        box=ROUNDED,
        border_style="#7C4DFF",
        title=f"[bold #00E5FF]verify[/]  score [bold {score_color}]{overall}/100[/]",
        title_align="left",
        subtitle=f"[dim]{len(criteria_list)} criteria[/]",
        subtitle_align="right",
    )
    return _ok(plain, panel)


__all__ = [
    "cmd_checkpoint",
    "cmd_rollback",
    "cmd_verify",
]
