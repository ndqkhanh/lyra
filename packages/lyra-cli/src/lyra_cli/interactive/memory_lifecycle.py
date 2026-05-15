"""Lifecycle sub-commands for ``/memory``.

Implements:
  consolidate — promote recent episodes to stable semantic summaries
  distill     — extract reusable strategy lessons from session history
  audit       — Rich table view of all stored memory files
  evolve      — Zettelkasten enrichment of an existing note (A-Mem pattern)
  promote     — promote a verified episodic pattern into a skill file

Public surface: :func:`cmd_memory_lifecycle`.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MEMORY_ROOT = Path.home() / ".lyra" / "memory"
_STRATEGIES_DIR = _MEMORY_ROOT / "strategies"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40]


def _extract_text_messages(messages: list[Any], last_n: int = 20) -> list[dict[str, str]]:
    """Return the last *last_n* messages as plain {role, text} dicts."""
    result: list[dict[str, str]] = []
    for msg in messages[-last_n:]:
        try:
            role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else "unknown")
            if isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = getattr(msg, "content", "")
            if isinstance(content, list):
                text = " ".join(
                    (c.get("text", "") if isinstance(c, dict) else str(c))
                    for c in content
                )
            else:
                text = str(content) if content else ""
            result.append({"role": str(role), "text": text[:300]})
        except Exception:
            continue
    return result


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def _consolidate(session: Any) -> Any:
    """Show what would be consolidated from recent turns and write a summary file."""
    from rich.panel import Panel

    msgs = _extract_text_messages(getattr(session, "messages", []), last_n=20)
    if not msgs:
        return Panel(
            "[yellow]No messages in current session to consolidate.[/yellow]",
            title="[bold cyan]Memory: Consolidate[/bold cyan]",
        )

    lines: list[str] = []
    for m in msgs:
        role_tag = "[bold green]user[/bold green]" if m["role"] == "user" else "[dim]assistant[/dim]"
        snippet = m["text"][:120].replace("[", "\\[")
        lines.append(f"  {role_tag}: {snippet}")

    summary_text = "\n".join(
        f"{m['role']}: {m['text'][:120]}" for m in msgs
    )

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    turn = getattr(session, "turn", 0)
    out_path = _ensure_dir(_MEMORY_ROOT) / f"consolidation-{ts}.md"
    try:
        out_path.write_text(
            f"# Consolidation — {ts}\n\nturn: {turn}\n\n## Last {len(msgs)} messages\n\n{summary_text}\n",
            encoding="utf-8",
        )
        footer = f"[dim]Written → {out_path}[/dim]"
    except Exception as exc:
        footer = f"[red]Write failed: {exc}[/red]"

    body = "\n".join(lines) + f"\n\n{footer}"
    return Panel(
        body,
        title=f"[bold cyan]Memory: Consolidate[/bold cyan] [dim]({len(msgs)} messages)[/dim]",
        border_style="cyan",
    )


def _distill(session: Any) -> Any:
    """Extract reusable strategy lessons and write to strategies dir."""
    from rich.panel import Panel

    msgs = _extract_text_messages(getattr(session, "messages", []), last_n=20)
    if not msgs:
        return Panel(
            "[yellow]No messages to distill.[/yellow]",
            title="[bold magenta]Memory: Distill[/bold magenta]",
        )

    # Build a naive lesson summary from assistant messages
    assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
    lessons: list[str] = []
    for i, m in enumerate(assistant_msgs[:5], 1):
        snippet = m["text"][:200].replace("[", "\\[")
        lessons.append(f"  {i}. {snippet}")

    lesson_text = "\n".join(f"{i+1}. {m['text'][:200]}" for i, m in enumerate(assistant_msgs[:5]))
    model = getattr(session, "model", "unknown")
    turn = getattr(session, "turn", 0)
    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(f"session-turn-{turn}")
    out_path = _ensure_dir(_STRATEGIES_DIR) / f"{ts}-{slug}.md"

    try:
        out_path.write_text(
            f"# Strategy Lessons — {ts}\n\nmodel: {model}\nturn: {turn}\n\n## Lessons\n\n{lesson_text}\n",
            encoding="utf-8",
        )
        footer = f"[dim]Written → {out_path}[/dim]"
    except Exception as exc:
        footer = f"[red]Write failed: {exc}[/red]"

    body = "\n".join(lessons) if lessons else "  [dim](no assistant messages found)[/dim]"
    body += f"\n\n{footer}"
    return Panel(
        body,
        title=f"[bold magenta]Memory: Distill[/bold magenta] [dim]({len(assistant_msgs)} assistant turns)[/dim]",
        border_style="magenta",
    )


def _audit() -> Any:
    """Scan ~/.lyra/memory for .md files and display in a Rich Table."""
    from rich.table import Table

    table = Table(title="Memory Audit", show_lines=True, border_style="blue")
    table.add_column("id", style="dim", no_wrap=True)
    table.add_column("type", style="cyan")
    table.add_column("scope", style="green")
    table.add_column("path", style="dim", overflow="fold")
    table.add_column("size", justify="right")
    table.add_column("modified", style="yellow")

    root = _MEMORY_ROOT
    if not root.exists():
        table.add_row("-", "-", "-", str(root), "-", "[dim]directory absent[/dim]")
        return table

    files = sorted(root.rglob("*.md"))
    if not files:
        table.add_row("-", "-", "-", str(root), "-", "[dim]no .md files found[/dim]")
        return table

    for idx, fpath in enumerate(files):
        try:
            stat = fpath.stat()
            size_str = f"{stat.st_size:,}"
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        except Exception:
            size_str = "?"
            mtime = "?"

        rel = str(fpath.relative_to(root.parent)) if fpath.is_relative_to(root.parent) else str(fpath)
        parts = fpath.relative_to(root).parts
        mem_type = parts[0] if len(parts) > 1 else "general"
        scope = "session" if "session" in rel else "global"

        table.add_row(str(idx), mem_type, scope, rel, size_str, mtime)

    return table


def _evolve(note_id: str, session: Any) -> Any:
    """Zettelkasten update: enrich an existing note with new evidence links."""
    from rich.panel import Panel

    root = _MEMORY_ROOT
    if not root.exists():
        return Panel(
            f"[red]Memory root {root} does not exist.[/red]",
            title="[bold yellow]Memory: Evolve[/bold yellow]",
        )

    matches = list(root.rglob("*.md"))
    target: Path | None = None
    for f in matches:
        if note_id in f.stem or note_id in f.name:
            target = f
            break

    if target is None:
        names = [str(f.relative_to(root)) for f in matches[:10]]
        hint = "\n".join(f"  {n}" for n in names) if names else "  (none)"
        return Panel(
            f"[red]Note not found: {note_id!r}[/red]\n\nAvailable notes:\n{hint}",
            title="[bold yellow]Memory: Evolve[/bold yellow]",
            border_style="yellow",
        )

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    turn = getattr(session, "turn", 0)
    msgs = _extract_text_messages(getattr(session, "messages", []), last_n=5)
    evidence = "\n".join(f"- (turn {turn}) {m['role']}: {m['text'][:120]}" for m in msgs)

    try:
        existing = target.read_text(encoding="utf-8")
        link_block = f"\n\n## Evidence links ({ts})\n\n{evidence}\n"
        target.write_text(existing + link_block, encoding="utf-8")
        status = f"[green]Appended evidence links to {target.name}[/green]"
    except Exception as exc:
        status = f"[red]Failed to update {target}: {exc}[/red]"

    return Panel(
        f"Note: [bold]{target}[/bold]\n\n{status}\n\nLinks added:\n{evidence.replace('[', chr(91))}",
        title="[bold yellow]Memory: Evolve[/bold yellow]",
        border_style="yellow",
    )


def _promote(note_id: str, session: Any) -> Any:
    """Promote a verified episodic pattern into a skill file."""
    from rich.panel import Panel

    root = _MEMORY_ROOT
    matches = list(root.rglob("*.md")) if root.exists() else []
    target: Path | None = None
    for f in matches:
        if note_id in f.stem or note_id in f.name:
            target = f
            break

    repo_root: Path | None = getattr(session, "repo_root", None)
    skills_base = (repo_root / ".lyra" / "skills") if repo_root else (Path.home() / ".lyra" / "skills")
    _ensure_dir(skills_base)

    slug = _slugify(note_id)
    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    skill_path = skills_base / f"{slug}.md"

    if target is not None:
        try:
            note_content = target.read_text(encoding="utf-8")
        except Exception:
            note_content = f"# {note_id}\n\n(source note unreadable)"
    else:
        note_content = f"# {note_id}\n\n(source note not found in {root})"

    verifier_block = (
        f"\n\n---\n\n"
        f"## Verifier\n\n"
        f"promoted: {ts}\n"
        f"source: {target or 'unknown'}\n"
        f"model: {getattr(session, 'model', 'unknown')}\n"
        f"turn: {getattr(session, 'turn', 0)}\n"
    )

    try:
        skill_path.write_text(note_content + verifier_block, encoding="utf-8")
        status = f"[green]Skill written → {skill_path}[/green]"
    except Exception as exc:
        status = f"[red]Failed to write skill: {exc}[/red]"

    return Panel(
        f"Note: [bold]{target or note_id}[/bold]\nSkill: [bold]{skill_path}[/bold]\n\n{status}",
        title="[bold green]Memory: Promote[/bold green]",
        border_style="green",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def cmd_memory_lifecycle(session: Any, args: str) -> Any:
    """Dispatch lifecycle sub-commands for ``/memory``.

    Sub-commands:
      consolidate           — promote recent episodes to semantic summaries
      distill               — extract strategy lessons from session history
      audit                 — show lifecycle view of all stored memories
      evolve <note-id>      — enrich an existing note with new evidence links
      promote <note-id>     — promote a pattern into a skill file
    """
    from .session import CommandResult

    parts = (args or "").strip().split(None, 1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    try:
        if sub == "consolidate":
            renderable = _consolidate(session)
            return CommandResult(output="consolidate: see panel above.", renderable=renderable)

        if sub == "distill":
            renderable = _distill(session)
            return CommandResult(output="distill: see panel above.", renderable=renderable)

        if sub == "audit":
            renderable = _audit()
            return CommandResult(output="audit: see table above.", renderable=renderable)

        if sub == "evolve":
            if not rest:
                return CommandResult(output="usage: /memory lifecycle evolve <note-id>")
            renderable = _evolve(rest, session)
            return CommandResult(output=f"evolve {rest!r}: see panel above.", renderable=renderable)

        if sub == "promote":
            if not rest:
                return CommandResult(output="usage: /memory lifecycle promote <note-id>")
            renderable = _promote(rest, session)
            return CommandResult(output=f"promote {rest!r}: see panel above.", renderable=renderable)

        usage = (
            "memory lifecycle sub-commands:\n"
            "  consolidate           promote recent episodes to semantic summaries\n"
            "  distill               extract strategy lessons from session history\n"
            "  audit                 show lifecycle view of all stored memories\n"
            "  evolve <note-id>      enrich an existing note with new evidence links\n"
            "  promote <note-id>     promote a pattern into a skill file"
        )
        return CommandResult(output=usage)

    except Exception as exc:
        return CommandResult(output=f"error: {exc}")
