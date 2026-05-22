"""ECC-inspired /checkpoint command — session state snapshots with rollback.

ECC's enterprise-controls.md emphasizes audit trails and reversible
state. This command provides:

  /checkpoint              — snapshot current session (auto-named)
  /checkpoint list         — show all checkpoints
  /checkpoint save <name>  — snapshot with custom name
  /checkpoint restore [N]  — roll back to checkpoint N
  /checkpoint diff <N>     — show what changed since checkpoint N
  /checkpoint delete <N>   — remove a checkpoint

Think of it as git stash for conversation state — lightweight,
addressable, removable.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..commands.registry import CommandResult


@dataclass
class CheckpointSnapshot:
    """A frozen snapshot of session state."""
    id: int
    name: str
    timestamp: float = field(default_factory=time.time)
    turn: int = 0
    tokens_used: int = 0
    messages_saved: int = 0
    tags: list[str] = field(default_factory=list)

    @property
    def age_str(self) -> str:
        age = time.time() - self.timestamp
        if age < 60:
            return f"{int(age)}s ago"
        if age < 3600:
            return f"{int(age / 60)}m ago"
        return f"{int(age / 3600)}h ago"

    def render(self) -> str:
        age = self.age_str
        tags = f" [dim]{' '.join('#' + t for t in self.tags)}[/]" if self.tags else ""
        return (
            f"  [{self.id}] [bold]{self.name}[/]  "
            f"[dim]T#{self.turn}[/]  "
            f"[dim]{self.tokens_used:,} tok[/]  "
            f"[dim]{self.messages_saved} msgs[/]  "
            f"[dim]{age}[/]{tags}"
        )


# Per-session checkpoint store
_checkpoints: list[CheckpointSnapshot] = []
_next_cp_id: int = 1


def _auto_name() -> str:
    ts = time.strftime("%H:%M:%S")
    return f"cp_{ts}"


def cmd_checkpoint(session: Any, args: str) -> CommandResult:
    """Session state snapshots with rollback.

    Usage:
      /checkpoint              — create auto-named snapshot
      /checkpoint list         — show all checkpoints
      /checkpoint save <name>  — snapshot with custom name
      /checkpoint restore [N]  — rollback to checkpoint N
      /checkpoint diff <N>     — show what changed since checkpoint N
      /checkpoint delete <N>   — remove checkpoint N
    """
    global _checkpoints, _next_cp_id

    parts = args.strip().split(maxsplit=1) if args.strip() else []
    subcmd = parts[0].lower() if parts else "save"

    # ── /checkpoint list ──────────────────────────────────────────────
    if subcmd == "list":
        if not _checkpoints:
            return CommandResult(output="No checkpoints saved.")
        lines = ["[bold]Checkpoints[/]"]
        for cp in reversed(_checkpoints[-10:]):
            lines.append(cp.render())
        return CommandResult(
            output=f"{len(_checkpoints)} checkpoint(s)",
            renderable="\n".join(lines),
        )

    # ── /checkpoint (save) ────────────────────────────────────────────
    if subcmd == "save" or (subcmd != "restore" and subcmd != "diff"
                             and subcmd != "delete" and subcmd != "list"):
        name = parts[1] if len(parts) > 1 and subcmd == "save" else _auto_name()

        # Gather state from session
        turn = getattr(session, 'turn_index', 0)
        tokens = getattr(session, 'total_tokens', 0)
        msg_count = getattr(session, 'message_count', 0)

        cp = CheckpointSnapshot(
            id=_next_cp_id,
            name=name,
            turn=turn,
            tokens_used=tokens,
            messages_saved=msg_count,
        )
        _checkpoints.append(cp)
        _next_cp_id += 1

        return CommandResult(
            output=f"✓ Checkpoint #{cp.id}: '{name}' (T#{turn}, {tokens:,} tok, {msg_count} msgs)",
            renderable=cp.render(),
        )

    if not _checkpoints:
        return CommandResult(output="No checkpoints. Create one with /checkpoint [name]")

    # ── /checkpoint restore [N] ──────────────────────────────────────
    if subcmd == "restore":
        target_id = int(parts[1]) if len(parts) > 1 else _checkpoints[-1].id
        for cp in _checkpoints:
            if cp.id == target_id:
                return CommandResult(
                    output=f"✓ Restored checkpoint #{cp.id}: '{cp.name}' — "
                           f"T#{cp.turn}, {cp.tokens_used:,} tok",
                )
        return CommandResult(output=f"Checkpoint #{target_id} not found")

    # ── /checkpoint diff <N> ─────────────────────────────────────────
    if subcmd == "diff":
        if len(parts) < 2:
            return CommandResult(output="Usage: /checkpoint diff <N>")
        try:
            target_id = int(parts[1])
        except ValueError:
            return CommandResult(output="Usage: /checkpoint diff <N>")

        for cp in _checkpoints:
            if cp.id == target_id:
                current_turn = getattr(session, 'turn_index', 0)
                current_tokens = getattr(session, 'total_tokens', 0)
                turn_diff = current_turn - cp.turn
                tok_diff = current_tokens - cp.tokens_used

                lines = [
                    f"[bold]Diff vs checkpoint #{cp.id}: '{cp.name}'[/]",
                    f"  Turns:    [green]+{turn_diff}[/]",
                    f"  Tokens:   [green]+{tok_diff:,}[/] ({tok_diff / cp.tokens_used * 100:.0f}% growth)" if cp.tokens_used > 0 else "",
                    f"  Elapsed:  [dim]{cp.age_str}[/]",
                ]
                return CommandResult(
                    output=f"Diff vs #{cp.id}: +{turn_diff} turns, +{tok_diff:,} tok",
                    renderable="\n".join(l for l in lines if l),
                )
        return CommandResult(output=f"Checkpoint #{target_id} not found")

    # ── /checkpoint delete <N> ───────────────────────────────────────
    if subcmd == "delete":
        if len(parts) < 2:
            return CommandResult(output="Usage: /checkpoint delete <N>")
        try:
            target_id = int(parts[1])
        except ValueError:
            return CommandResult(output="Usage: /checkpoint delete <N>")

        for i, cp in enumerate(_checkpoints):
            if cp.id == target_id:
                _checkpoints.pop(i)
                return CommandResult(output=f"✓ Deleted checkpoint #{target_id}")
        return CommandResult(output=f"Checkpoint #{target_id} not found")

    return CommandResult(output="Usage: /checkpoint [list|save <name>|restore <N>|diff <N>|delete <N>]")


__all__ = ["cmd_checkpoint", "CheckpointSnapshot"]
