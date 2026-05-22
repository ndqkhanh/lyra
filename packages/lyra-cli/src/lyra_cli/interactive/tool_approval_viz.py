"""Tool approval visual — Rich approval panel with context preview.

Rewrites the bare ``ToolApprovalCache`` from tool_approval.py
into a full Rich-rendered UX panel, inspired by ECC's agent-shield
audit trails and Claude Code's tool permission dialogs.

Features:
  • Rich Panel showing tool name, args, risk level, and context
  • Color-coded risk badges (low=green, medium=yellow, high=red)
  • Keyboard-driven approval flow (y=allow, n=deny, a=always, s=strict)
  • Approval cache visualization ("allowed for this session")
  • Risk-based auto-approval for low-risk tools (configurable)
"""
from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ── Risk levels ─────────────────────────────────────────────────────────

LOW_RISK_TOOLS = {
    "Read", "Grep", "Glob", "ListFiles", "Bash", "WebSearch",
    "WebFetch", "AgentMemory", "SkillLookup", "Probe", "LSP",
    "SemanticSearch",
}

MEDIUM_RISK_TOOLS = {
    "Write", "Edit", "ApplyPatch", "Rename", "Delete",
    "CreateDirectory", "ImageGeneration", "Voice",
}

HIGH_RISK_TOOLS = {
    "Bash", "Subprocess", "Deploy", "Execute", "Kubernetes",
    "Terraform", "DatabaseQuery", "NetworkRequest",
    "ServiceWrite", "Webhook",
}


@dataclass
class ApprovalRequest:
    """Context for a tool approval prompt."""
    tool_name: str
    args_preview: str = ""
    risk_level: str = "unknown"
    mode: str = "normal"
    call_id: str = ""
    cache_status: str = "new"

    @property
    def risk_color(self) -> str:
        return {"low": "green", "medium": "yellow", "high": "red"}.get(self.risk_level, "dim")

    @classmethod
    def from_tool_call(cls, tool_name: str, args: dict, mode: str = "normal") -> "ApprovalRequest":
        if tool_name in LOW_RISK_TOOLS:
            risk = "low"
        elif tool_name in MEDIUM_RISK_TOOLS:
            risk = "medium"
        elif tool_name in HIGH_RISK_TOOLS:
            risk = "high"
        else:
            risk = "medium"

        # Build args preview (truncated)
        args_preview = ""
        if args:
            parts = []
            for k, v in list(args.items())[:4]:
                v_str = str(v)
                if len(v_str) > 60:
                    v_str = v_str[:57] + "..."
                parts.append(f"{k}={v_str}")
            args_preview = " ".join(parts)

        return cls(
            tool_name=tool_name,
            args_preview=args_preview,
            risk_level=risk,
            mode=mode,
        )


# ── Renderers ───────────────────────────────────────────────────────────

def render_approval_panel(req: ApprovalRequest) -> Panel:
    """Render a tool approval request as a Rich Panel.

    Shows: tool name, risk badge, args preview, mode status, and
    approval hint.
    """
    # Risk badge
    risk_label = {
        "low": "🟢 Low Risk",
        "medium": "🟡 Medium Risk",
        "high": "🔴 High Risk",
    }.get(req.risk_level, "⚪ Unknown")

    # Args table
    grid = Table.grid(padding=(0, 1))
    grid.add_row("[bold]Tool[/]", req.tool_name)
    grid.add_row("[dim]Risk[/]", f"[{req.risk_color}]{risk_label}[/]")

    if req.args_preview:
        grid.add_row("[dim]Args[/]", req.args_preview[:80])

    # Mode badge
    mode_badge = {
        "normal": "[dim]normal[/]",
        "strict": "[yellow]strict[/]",
        "yolo": "[green]yolo[/]",
    }.get(req.mode, "[dim]normal[/]")
    grid.add_row("[dim]Mode[/]", mode_badge)

    if req.cache_status == "cached":
        grid.add_row("[dim]Cache[/]", "[green]already approved[/]")

    # Footer with key hints
    footer = ""
    if req.risk_level == "high":
        footer = "\n[yellow]⚠ High-risk tool[/] — type [bold]y[/] allow · [bold]n[/] deny · [bold]a[/] always allow"
    elif req.risk_level == "medium":
        footer = "\n[dim]Approve?[/] [bold]y[/] yes · [bold]n[/] no · [bold]a[/] always for session"
    else:
        footer = "\n[dim](low-risk — auto-approved)[/]"

    return Panel(
        grid,
        title=f"🔧 {req.tool_name}",
        border_style=req.risk_color,
        subtitle=footer.strip() if footer else None,
    )


def render_approval_summary(cache: dict[str, str]) -> Panel:
    """Render the full approval cache as a summary table.

    Shows which tools are allowed/denied for the current session.
    """
    if not cache:
        return Panel(
            "[dim]No tools have been approved or denied yet.[/]",
            title="🔧 Tool Approvals",
            border_style="dim",
        )

    grid = Table.grid(padding=(0, 1))
    grid.add_column()
    grid.add_column()

    for tool_name, verdict in sorted(cache.items()):
        if verdict == "allow":
            glyph = "[green]✓[/]"
        elif verdict == "deny":
            glyph = "[red]✗[/]"
        else:
            glyph = "[dim]?[/]"
        grid.add_row(glyph, tool_name)

    allowed = sum(1 for v in cache.values() if v == "allow")
    denied = sum(1 for v in cache.values() if v == "deny")

    return Panel(
        grid,
        title=f"🔧 Tool Approvals ({allowed} allowed · {denied} denied)",
        border_style="green" if allowed > denied else "yellow",
    )


def classify_risk(tool_name: str) -> str:
    """Classify a tool's risk level by name."""
    if tool_name in LOW_RISK_TOOLS:
        return "low"
    if tool_name in MEDIUM_RISK_TOOLS:
        return "medium"
    if tool_name in HIGH_RISK_TOOLS:
        return "high"
    return "medium"


__all__ = [
    "ApprovalRequest", "render_approval_panel", "render_approval_summary",
    "classify_risk", "LOW_RISK_TOOLS", "MEDIUM_RISK_TOOLS", "HIGH_RISK_TOOLS",
]
