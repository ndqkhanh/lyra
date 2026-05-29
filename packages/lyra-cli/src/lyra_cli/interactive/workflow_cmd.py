"""ECC-inspired structured workflow command for the Lyra REPL.

Implements the ECC feature-development pattern as a slash command:
  /workflow <name> [--step N] [--list] [--status]

Provides structured multi-step task scaffolding with:
  • Built-in workflow templates (feature, bugfix, research, migration, review)
  • Step-by-step guided execution
  • Visual status tracking per step
  • Auto-generation of plan artifacts

ECC reference: everything-claude-code feature-development.md +
database-migration.md + add-language-rules.md structured workflows.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..commands.registry import CommandResult

# ── Workflow Definitions ───────────────────────────────────────────────

WORKFLOW_STEPS: dict[str, list[dict[str, str]]] = {
    "feature": [
        {
            "step": "1",
            "name": "Specification",
            "prompt": "Define requirements & acceptance criteria",
        },
        {"step": "2", "name": "Design", "prompt": "Architecture & interface design"},
        {"step": "3", "name": "Implementation", "prompt": "Write the implementation"},
        {"step": "4", "name": "Testing", "prompt": "Write & run tests"},
        {"step": "5", "name": "Review", "prompt": "Self-review & polish"},
        {"step": "6", "name": "Documentation", "prompt": "Update docs & changelog"},
    ],
    "bugfix": [
        {"step": "1", "name": "Reproduce", "prompt": "Create minimal reproduction"},
        {"step": "2", "name": "Root Cause", "prompt": "Identify the root cause"},
        {"step": "3", "name": "Fix", "prompt": "Implement the fix"},
        {"step": "4", "name": "Verify", "prompt": "Verify fix & add regression test"},
        {"step": "5", "name": "Review", "prompt": "Review for side-effects"},
    ],
    "research": [
        {"step": "1", "name": "Scope", "prompt": "Define research questions & sources"},
        {"step": "2", "name": "Discovery", "prompt": "Gather information from sources"},
        {"step": "3", "name": "Analysis", "prompt": "Analyze & cross-reference findings"},
        {"step": "4", "name": "Synthesis", "prompt": "Synthesize into conclusions"},
        {"step": "5", "name": "Report", "prompt": "Write research brief"},
    ],
    "migration": [
        {"step": "1", "name": "Audit", "prompt": "Audit current state & dependencies"},
        {"step": "2", "name": "Plan", "prompt": "Design migration plan with rollback"},
        {"step": "3", "name": "Execute", "prompt": "Execute migration"},
        {"step": "4", "name": "Verify", "prompt": "Verify data integrity & behavior"},
        {"step": "5", "name": "Cleanup", "prompt": "Remove deprecated paths"},
    ],
    "review": [
        {"step": "1", "name": "Understand", "prompt": "Understand the change context"},
        {"step": "2", "name": "Logic", "prompt": "Review correctness & edge cases"},
        {"step": "3", "name": "Style", "prompt": "Review code style & conventions"},
        {"step": "4", "name": "Security", "prompt": "Review security implications"},
        {"step": "5", "name": "Performance", "prompt": "Review performance impact"},
    ],
}

WORKFLOW_DESCRIPTIONS = {
    "feature": "Standard feature implementation",
    "bugfix": "Bug reproduction & fix workflow",
    "research": "Multi-source research investigation",
    "migration": "Database / config / code migration",
    "review": "Code review checklist",
}


@dataclass
class WorkflowState:
    """Persistent state for an active workflow."""

    name: str
    started_at: float = field(default_factory=time.time)
    current_step: int = 0
    completed_steps: list[int] = field(default_factory=list)
    notes: dict[str, str] = field(default_factory=dict)

    def progress_str(self) -> str:
        total = len(WORKFLOW_STEPS.get(self.name, []))
        done = len(self.completed_steps)
        bar = "█" * done + "░" * (total - done)
        return f"{bar}  {done}/{total} steps"

    def status_line(self) -> str:
        steps = WORKFLOW_STEPS.get(self.name, [])
        if not steps:
            return "[dim]no steps[/]"
        lines = [f"[bold]Workflow: {self.name}[/]  {self.progress_str()}"]
        for s in steps:
            idx = int(s["step"]) - 1
            completed = idx in self.completed_steps
            active = idx == self.current_step
            if completed:
                glyph = "✓"
            elif active:
                glyph = "⏺"
            else:
                glyph = "◻"
            marker = (
                f"[green]{glyph}"
                if completed
                else (f"[cyan]{glyph}" if active else f"[dim]{glyph}")
            )
            lines.append(f"  {marker}[/] {s['name']}  [dim]— {s['prompt']}[/]")
        for note_key, note_val in self.notes.items():
            if note_key.startswith("step_"):
                lines.append(f"    [dim]⎿ note: {note_val[:60]}[/]")
        return "\n".join(lines)


# In-memory workflow state (per-session; could be persisted)
_active_workflow: WorkflowState | None = None


# ── Command Handler ────────────────────────────────────────────────────


def cmd_workflow(session: Any, args: str) -> CommandResult:
    """Manage structured multi-step workflows.

    Usage:
      /workflow list                     — list available templates
      /workflow start <name>             — start a new workflow
      /workflow status                   — show current workflow progress
      /workflow step [N]                 — advance to or show step N
      /workflow next                     — advance to next step
      /workflow note <text>              — add note to current step
      /workflow done                     — mark current step complete
      /workflow cancel                   — cancel active workflow
    """
    global _active_workflow

    parts = args.strip().split(maxsplit=2) if args.strip() else []
    subcmd = parts[0].lower() if parts else "list"

    # ── /workflow list ─────────────────────────────────────────────────
    if subcmd == "list" or subcmd == "ls":
        lines = ["[bold]Available Workflows[/]"]
        for name, desc in sorted(WORKFLOW_DESCRIPTIONS.items()):
            steps = len(WORKFLOW_STEPS.get(name, []))
            lines.append(f"  [cyan]{name:<12}[/] {desc}  [dim]({steps} steps)[/]")
        return CommandResult(
            output="Available workflows: " + ", ".join(WORKFLOW_DESCRIPTIONS),
            renderable="\n".join(lines) if _rich_available() else None,
        )

    # ── /workflow start <name> ─────────────────────────────────────────
    if subcmd == "start":
        wf_name = parts[1].lower() if len(parts) > 1 else ""
        if wf_name not in WORKFLOW_STEPS:
            valid = ", ".join(WORKFLOW_DESCRIPTIONS)
            return CommandResult(
                output=f"Unknown workflow '{wf_name}'. Available: {valid}",
            )
        _active_workflow = WorkflowState(name=wf_name)
        return CommandResult(
            output=f"Started workflow '{wf_name}' — type /workflow next to begin",
            renderable=_active_workflow.status_line(),
        )

    # ── Guard: active workflow required ────────────────────────────────
    if _active_workflow is None:
        return CommandResult(
            output="No active workflow. Start one with /workflow start <name>",
        )

    wf = _active_workflow
    steps = WORKFLOW_STEPS.get(wf.name, [])

    # ── /workflow status ───────────────────────────────────────────────
    if subcmd == "status":
        return CommandResult(
            output=f"Workflow '{wf.name}': step {wf.current_step + 1}/{len(steps)}",
            renderable=wf.status_line(),
        )

    # ── /workflow next ─────────────────────────────────────────────────
    if subcmd == "next":
        wf.current_step = min(wf.current_step + 1, len(steps) - 1)
        if wf.current_step not in wf.completed_steps and wf.current_step > 0:
            wf.completed_steps.append(wf.current_step - 1)
        step = steps[wf.current_step] if wf.current_step < len(steps) else None
        if step:
            return CommandResult(
                output=f"Step {step['step']}: {step['name']} — {step['prompt']}",
                renderable=wf.status_line(),
            )
        return CommandResult(
            output="Workflow complete! Run /workflow cancel to finish.",
            renderable=wf.status_line(),
        )

    # ── /workflow step [N] ─────────────────────────────────────────────
    if subcmd == "step":
        if len(parts) > 1:
            try:
                target = int(parts[1]) - 1
                if 0 <= target < len(steps):
                    wf.current_step = target
                else:
                    return CommandResult(output=f"Step must be 1–{len(steps)}")
            except ValueError:
                return CommandResult(output="Usage: /workflow step <N>")
        step = steps[wf.current_step] if wf.current_step < len(steps) else None
        if step:
            return CommandResult(
                output=f"Current: Step {step['step']}: {step['name']}",
                renderable=wf.status_line(),
            )

    # ── /workflow done ─────────────────────────────────────────────────
    if subcmd == "done":
        if wf.current_step not in wf.completed_steps:
            wf.completed_steps.append(wf.current_step)
        if wf.current_step < len(steps) - 1:
            wf.current_step += 1
            next_step = steps[wf.current_step]
            return CommandResult(
                output=f"✓ Step marked done. Now on: Step {next_step['step']}: {next_step['name']}",
                renderable=wf.status_line(),
            )
        else:
            return CommandResult(
                output="✓ All steps complete! Run /workflow cancel to finish.",
                renderable=wf.status_line(),
            )

    # ── /workflow note <text> ──────────────────────────────────────────
    if subcmd == "note":
        note_text = parts[2] if len(parts) > 2 else ""
        if note_text:
            wf.notes[f"step_{wf.current_step}_{int(time.time())}"] = note_text
            return CommandResult(output=f"Note saved for step {wf.current_step + 1}")

    # ── /workflow cancel ───────────────────────────────────────────────
    if subcmd == "cancel":
        name = _active_workflow.name
        _active_workflow = None
        return CommandResult(output=f"Workflow '{name}' cancelled.")

    return CommandResult(
        output=(
            "Unknown subcommand. Usage: /workflow [list|start|status|next|step|done|note|cancel]"
        ),
    )


def _rich_available() -> bool:
    try:
        from rich.console import Console  # noqa: F401

        return True
    except ImportError:
        return False


__all__ = ["cmd_workflow", "WORKFLOW_STEPS", "WORKFLOW_DESCRIPTIONS", "WorkflowState"]
