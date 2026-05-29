"""ECC-inspired /verify command — structured verification checklist for the REPL.

ECC's feature-development.md mandates verifiable acceptance criteria.
This command scaffolds a verification checklist and tracks pass/fail:

  /verify              — show current verification status
  /verify add <desc>   — add a new check
  /verify pass [N]     — mark check N as passed
  /verify fail [N]     — mark check N as failed
  /verify all          — run all checks (placeholder)
  /verify clear        — clear all checks

Renders as a formatted checklist with pass/fail/pending indicators.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..commands.registry import CommandResult


@dataclass
class VerificationCheck:
    """One verifiable check item."""

    id: int
    description: str
    status: str = "pending"  # pending | pass | fail
    notes: str = ""
    timestamp: float = field(default_factory=time.time)


# Per-session verification store
_checks: list[VerificationCheck] = []
_next_id: int = 1


def cmd_verify(session: Any, args: str) -> CommandResult:
    """Verification checklist — ECC-structured acceptance testing.

    Usage:
      /verify              — show all checks with status
      /verify add <desc>   — add a new verification check
      /verify pass [N]     — mark check N as passed
      /verify fail [N]     — mark check N as failed
      /verify note <N> <text> — add note to check N
      /verify clear        — clear all checks
    """
    global _checks, _next_id

    parts = args.strip().split(maxsplit=2) if args.strip() else []
    subcmd = parts[0].lower() if parts else "show"

    # ── /verify (show) ────────────────────────────────────────────────
    if subcmd == "show" or not parts:
        if not _checks:
            return CommandResult(
                output="No verification checks. Add one with /verify add <description>"
            )

        lines = ["[bold]Verification Checklist[/]"]
        passed = sum(1 for c in _checks if c.status == "pass")
        failed = sum(1 for c in _checks if c.status == "fail")
        total = len(_checks)

        bar_w = 20
        f_passed = int(passed / total * bar_w) if total > 0 else 0
        f_failed = int(failed / total * bar_w) if total > 0 else 0
        bar = "[green]" + "█" * f_passed + "[/]"
        bar += "[red]" + "█" * f_failed + "[/]"
        bar += "[dim]" + "░" * (bar_w - f_passed - f_failed) + "[/]"

        lines.append(

                f"  {bar}  [green]{passed}[/]/{total} passed  [green]"
                f"{passed/total*100 if total else 0:.0f}%[/]"

        )
        lines.append("")

        for check in _checks:
            if check.status == "pass":
                glyph = "[green]✓[/]"
            elif check.status == "fail":
                glyph = "[red]✗[/]"
            else:
                glyph = "[dim]◻[/]"

            desc = check.description[:60]
            note = f"  [dim]⎿ {check.notes[:50]}[/]" if check.notes else ""
            lines.append(f"  [{check.id}] {glyph} {desc}{note}")

        return CommandResult(
            output=f"{passed}/{total} verification checks passed",
            renderable="\n".join(lines),
        )

    # ── /verify add <desc> ────────────────────────────────────────────
    if subcmd == "add":
        if len(parts) < 2:
            return CommandResult(output="Usage: /verify add <description>")
        desc = " ".join(parts[1:])
        _checks.append(VerificationCheck(id=_next_id, description=desc))
        _next_id += 1
        return CommandResult(output=f"✓ Added check #{_next_id - 1}: {desc}")

    # ── /verify pass [N] ──────────────────────────────────────────────
    if subcmd == "pass":
        target_id = (
            int(parts[1])
            if len(parts) > 1 and parts[1].isdigit()
            else (_checks[-1].id if _checks else None)
        )
        for check in _checks:
            if check.id == target_id:
                check.status = "pass"
                return CommandResult(
                    output=f"✓ Check #{check.id} marked passed: {check.description[:50]}"
                )
        return CommandResult(output=f"Check #{target_id} not found")

    # ── /verify fail [N] ──────────────────────────────────────────────
    if subcmd == "fail":
        target_id = (
            int(parts[1])
            if len(parts) > 1 and parts[1].isdigit()
            else (_checks[-1].id if _checks else None)
        )
        reason = " ".join(parts[2:]) if len(parts) > 2 else "failed"
        for check in _checks:
            if check.id == target_id:
                check.status = "fail"
                check.notes = reason
                return CommandResult(output=f"✗ Check #{check.id} marked failed: {reason}")
        return CommandResult(output=f"Check #{target_id} not found")

    # ── /verify note <N> <text> ───────────────────────────────────────
    if subcmd == "note":
        if len(parts) < 3:
            return CommandResult(output="Usage: /verify note <N> <text>")
        try:
            target_id = int(parts[1])
        except ValueError:
            return CommandResult(output="Usage: /verify note <N> <text>")
        note_text = parts[2]
        for check in _checks:
            if check.id == target_id:
                check.notes = note_text
                return CommandResult(output=f"✓ Note saved for check #{target_id}")
        return CommandResult(output=f"Check #{target_id} not found")

    # ── /verify clear ────────────────────────────────────────────────
    if subcmd == "clear":
        _checks.clear()
        _next_id = 1
        return CommandResult(output="✓ Cleared all verification checks")

    return CommandResult(output="Usage: /verify [show|add|pass|fail|note|clear]")


__all__ = ["cmd_verify", "VerificationCheck"]
