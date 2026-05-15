"""Extended lifecycle sub-commands for ``/context``.

Implements:
  checkpoint [label]                    — CORAL pattern: write compact task-progress block
  prune [--last N]                      — FocusAgent: highlight goal-relevant vs noise spans
  playbook [list|set <k> <v>|append <t>|clear]  — ACE evolving playbook
  inject [<filepath>]                   — load AGENTS.md / CLAUDE.md / custom file into context

Public surface: :func:`cmd_context_extended`.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CHECKPOINTS_ROOT = Path.home() / ".lyra" / "checkpoints"
_PLAYBOOK_PATH = Path.home() / ".lyra" / "playbook.md"

_AGENTS_NAMES = ("AGENTS.md", "CLAUDE.md")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_id(session: Any) -> str:
    return str(getattr(session, "session_id", "default"))


def _last_user_message(session: Any) -> str:
    messages = getattr(session, "messages", [])
    for msg in reversed(messages):
        try:
            role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
            if role != "user":
                continue
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if isinstance(content, list):
                text = " ".join(
                    (c.get("text", "") if isinstance(c, dict) else str(c))
                    for c in content
                )
            else:
                text = str(content) if content else ""
            if text.strip():
                return text[:400]
        except Exception:
            continue
    return ""


def _tool_output_spans(session: Any, last_n: int) -> list[dict[str, Any]]:
    """Return the last *last_n* tool-result message spans."""
    messages = getattr(session, "messages", [])
    tool_msgs: list[dict[str, Any]] = []
    for msg in messages:
        try:
            role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
            if role != "tool":
                continue
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if isinstance(content, list):
                text = " ".join(
                    (c.get("text", "") if isinstance(c, dict) else str(c))
                    for c in content
                )
            else:
                text = str(content) if content else ""
            tool_name = (
                msg.get("name", "tool") if isinstance(msg, dict) else getattr(msg, "name", "tool")
            )
            tool_msgs.append({"name": str(tool_name), "text": text})
        except Exception:
            continue
    return tool_msgs[-last_n:]


# ---------------------------------------------------------------------------
# Sub-command: checkpoint
# ---------------------------------------------------------------------------


def _checkpoint(label: str, session: Any) -> Any:
    """Write a compact task-progress block to checkpoints dir."""
    from rich.panel import Panel

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    turn = getattr(session, "turn", 0)
    model = getattr(session, "model", "unknown")
    sid = _session_id(session)
    last_user = _last_user_message(session)

    # Minimal file-diffs summary from session if available
    file_diffs: str = ""
    try:
        history: list[str] = getattr(session, "history", [])
        if history:
            file_diffs = "; ".join(h[:80] for h in history[-5:])
    except Exception:
        file_diffs = ""

    payload: dict[str, Any] = {
        "label": label,
        "timestamp": ts,
        "turn": turn,
        "model": model,
        "last_user_message": last_user,
        "file_diffs_summary": file_diffs,
    }

    out_dir = _ensure_dir(_CHECKPOINTS_ROOT / sid)
    safe_label = label.replace("/", "-").replace(" ", "_") or "checkpoint"
    out_path = out_dir / f"{safe_label}.json"

    try:
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        status = f"[green]Checkpoint saved → {out_path}[/green]"
    except Exception as exc:
        status = f"[red]Write failed: {exc}[/red]"

    lines = [
        f"[bold]label[/bold]:   {label or '(unnamed)'}",
        f"[bold]turn[/bold]:    {turn}",
        f"[bold]model[/bold]:   {model}",
        f"[bold]session[/bold]: {sid}",
        "",
        status,
    ]
    return Panel(
        "\n".join(lines),
        title="[bold cyan]Context: Checkpoint[/bold cyan]",
        border_style="cyan",
    )


# ---------------------------------------------------------------------------
# Sub-command: prune
# ---------------------------------------------------------------------------


def _prune(last_n: int, session: Any) -> Any:
    """Show last N tool outputs and indicate goal-relevant vs noise spans."""
    from rich.panel import Panel
    from rich.table import Table

    spans = _tool_output_spans(session, last_n)
    if not spans:
        return Panel(
            "[yellow]No tool outputs found in current session.[/yellow]",
            title="[bold yellow]Context: Prune[/bold yellow]",
        )

    # Heuristic: spans with short text or generic names are "noise"
    _NOISE_NAMES = {"echo", "noop", "print", "log"}

    table = Table(show_lines=True, border_style="yellow")
    table.add_column("#", style="dim", width=3)
    table.add_column("tool", style="cyan", no_wrap=True)
    table.add_column("relevance", style="bold", width=12)
    table.add_column("snippet", overflow="fold")

    for i, span in enumerate(spans):
        name = span["name"]
        text = span["text"]
        is_noise = (
            name.lower() in _NOISE_NAMES
            or len(text.strip()) < 20
        )
        relevance = "[red]noise[/red]" if is_noise else "[green]relevant[/green]"
        snippet = text[:120].replace("[", "\\[")
        table.add_row(str(i), name, relevance, snippet)

    noise_count = sum(
        1 for s in spans
        if s["name"].lower() in _NOISE_NAMES or len(s["text"].strip()) < 20
    )
    summary = f"{len(spans)} spans shown — {noise_count} noise, {len(spans) - noise_count} relevant."
    return Panel(
        table,
        title=f"[bold yellow]Context: Prune[/bold yellow] [dim](last {last_n})[/dim]",
        subtitle=f"[dim]{summary}[/dim]",
        border_style="yellow",
    )


# ---------------------------------------------------------------------------
# Sub-command: playbook
# ---------------------------------------------------------------------------


def _playbook_list() -> Any:
    from rich.panel import Panel

    if not _PLAYBOOK_PATH.exists():
        return Panel(
            "[dim]Playbook is empty. Use `playbook append <text>` to add lessons.[/dim]",
            title="[bold blue]Context: Playbook[/bold blue]",
            border_style="blue",
        )
    try:
        content = _PLAYBOOK_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        return Panel(f"[red]Read failed: {exc}[/red]", title="[bold blue]Context: Playbook[/bold blue]")
    return Panel(
        content or "[dim](empty)[/dim]",
        title="[bold blue]Context: Playbook[/bold blue]",
        border_style="blue",
    )


def _playbook_append(text: str) -> Any:
    from rich.panel import Panel

    _ensure_dir(_PLAYBOOK_PATH.parent)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with _PLAYBOOK_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"\n- [{ts}] {text}\n")
        status = f"[green]Appended lesson to {_PLAYBOOK_PATH}[/green]"
    except Exception as exc:
        status = f"[red]Write failed: {exc}[/red]"
    return Panel(status, title="[bold blue]Context: Playbook[/bold blue]", border_style="blue")


def _playbook_set(key: str, value: str) -> Any:
    from rich.panel import Panel

    _ensure_dir(_PLAYBOOK_PATH.parent)
    try:
        existing = _PLAYBOOK_PATH.read_text(encoding="utf-8") if _PLAYBOOK_PATH.exists() else ""
    except Exception:
        existing = ""

    # Replace or append the key: value line
    new_line = f"{key}: {value}"
    pattern_lines = existing.splitlines()
    replaced = False
    out_lines: list[str] = []
    for line in pattern_lines:
        if line.startswith(f"{key}:"):
            out_lines.append(new_line)
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        out_lines.append(new_line)

    try:
        _PLAYBOOK_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        status = f"[green]Set {key!r} = {value!r} in playbook.[/green]"
    except Exception as exc:
        status = f"[red]Write failed: {exc}[/red]"
    return Panel(status, title="[bold blue]Context: Playbook[/bold blue]", border_style="blue")


def _playbook_clear() -> Any:
    from rich.panel import Panel

    try:
        _PLAYBOOK_PATH.write_text("", encoding="utf-8")
        status = "[green]Playbook cleared.[/green]"
    except Exception as exc:
        status = f"[red]Clear failed: {exc}[/red]"
    return Panel(status, title="[bold blue]Context: Playbook[/bold blue]", border_style="blue")


def _playbook(sub: str, rest: str) -> Any:
    from rich.panel import Panel

    if not sub or sub == "list":
        return _playbook_list()
    if sub == "append":
        if not rest:
            return Panel(
                "[red]usage: /context extended playbook append <text>[/red]",
                title="[bold blue]Context: Playbook[/bold blue]",
            )
        return _playbook_append(rest)
    if sub == "set":
        kv = rest.split(None, 1)
        if len(kv) < 2:
            return Panel(
                "[red]usage: /context extended playbook set <key> <value>[/red]",
                title="[bold blue]Context: Playbook[/bold blue]",
            )
        return _playbook_set(kv[0], kv[1])
    if sub == "clear":
        return _playbook_clear()
    return Panel(
        f"[red]Unknown playbook sub-command: {sub!r}[/red]\n"
        "  list | set <key> <value> | append <text> | clear",
        title="[bold blue]Context: Playbook[/bold blue]",
    )


# ---------------------------------------------------------------------------
# Sub-command: inject
# ---------------------------------------------------------------------------


def _inject(filepath: str, session: Any) -> Any:
    from rich.panel import Panel

    target: Path | None = None

    if filepath:
        candidate = Path(filepath).expanduser()
        if not candidate.is_absolute():
            repo_root: Path | None = getattr(session, "repo_root", None)
            if repo_root:
                candidate = repo_root / candidate
        if candidate.exists():
            target = candidate
        else:
            return Panel(
                f"[red]File not found: {candidate}[/red]",
                title="[bold green]Context: Inject[/bold green]",
                border_style="green",
            )
    else:
        repo_root = getattr(session, "repo_root", None)
        search_roots: list[Path] = []
        if repo_root:
            search_roots.append(Path(repo_root))
        search_roots.append(Path.cwd())
        for root in search_roots:
            for name in _AGENTS_NAMES:
                candidate = root / name
                if candidate.exists():
                    target = candidate
                    break
            if target is not None:
                break

        if target is None:
            return Panel(
                "[yellow]No AGENTS.md or CLAUDE.md found. Provide a filepath explicitly.[/yellow]",
                title="[bold green]Context: Inject[/bold green]",
                border_style="green",
            )

    try:
        content = target.read_text(encoding="utf-8")
    except Exception as exc:
        return Panel(
            f"[red]Failed to read {target}: {exc}[/red]",
            title="[bold green]Context: Inject[/bold green]",
        )

    # Attach to session.system_extras
    extras: list[str] = getattr(session, "system_extras", None) or []
    extras.append(content)
    session.system_extras = extras

    # Track injected files
    injected: list[str] = getattr(session, "injected_context_files", None) or []
    injected.append(str(target))
    session.injected_context_files = injected

    preview = content[:300].replace("[", "\\[")
    return Panel(
        f"[green]Injected[/green] [bold]{target.name}[/bold] ({len(content):,} chars)\n\n"
        f"[dim]{preview}{'…' if len(content) > 300 else ''}[/dim]",
        title="[bold green]Context: Inject[/bold green]",
        border_style="green",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def cmd_context_extended(session: Any, args: str) -> Any:
    """Dispatch extended lifecycle sub-commands for ``/context``.

    Sub-commands:
      checkpoint [label]                         write compact task-progress block
      prune [--last N]                           highlight goal-relevant vs noise spans
      playbook [list|set <k> <v>|append <t>|clear]  manage evolving playbook
      inject [<filepath>]                        inject AGENTS.md / CLAUDE.md / file into context
    """
    from .session import CommandResult

    parts = (args or "").strip().split(None, 1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    try:
        if sub == "checkpoint":
            renderable = _checkpoint(rest, session)
            return CommandResult(output="checkpoint: see panel above.", renderable=renderable)

        if sub == "prune":
            last_n = 5
            if rest.startswith("--last"):
                token = rest[len("--last"):].strip().split()[0] if rest[len("--last"):].strip() else "5"
                try:
                    last_n = int(token)
                except ValueError:
                    last_n = 5
            renderable = _prune(last_n, session)
            return CommandResult(output="prune: see panel above.", renderable=renderable)

        if sub == "playbook":
            pb_parts = rest.split(None, 1)
            pb_sub = pb_parts[0].lower() if pb_parts else "list"
            pb_rest = pb_parts[1].strip() if len(pb_parts) > 1 else ""
            renderable = _playbook(pb_sub, pb_rest)
            return CommandResult(output="playbook: see panel above.", renderable=renderable)

        if sub == "inject":
            renderable = _inject(rest, session)
            return CommandResult(output="inject: see panel above.", renderable=renderable)

        usage = (
            "context extended sub-commands:\n"
            "  checkpoint [label]                     write compact task-progress block\n"
            "  prune [--last N]                       show goal-relevant vs noise spans (default N=5)\n"
            "  playbook [list|set <k> <v>|append <t>|clear]  manage evolving playbook\n"
            "  inject [<filepath>]                    inject AGENTS.md/CLAUDE.md/file into context"
        )
        return CommandResult(output=usage)

    except Exception as exc:
        return CommandResult(output=f"error: {exc}")
