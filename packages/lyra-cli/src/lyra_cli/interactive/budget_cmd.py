"""Budget command + TUI bridge — track and visualize spending.

Ports the 324-line budget.py enforcement engine into a usable UX:
  • /budget — view current spend, set limits, get alerts
  • /budget set <usd> — set budget cap
  /budget reset — clear budget
  /budget status — show budget report
  • BudgetStatusWidget — TUI panel showing spend vs cap with bar

ECC reference: enterprise-controls.md emphasizes cost observability.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..commands.registry import CommandResult

# ── Budget config ──────────────────────────────────────────────────────

BUDGET_FILE = Path.home() / ".lyra" / "budget.json"


@dataclass
class BudgetState:
    """Persistent budget state."""

    limit_usd: float = 10.0
    spent_usd: float = 0.0
    alert_pct: float = 80.0
    last_reset: float = field(default_factory=time.time)
    session_spend: dict[str, float] = field(default_factory=dict)

    @property
    def pct(self) -> float:
        return (self.spent_usd / self.limit_usd * 100) if self.limit_usd > 0 else 0.0

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.limit_usd - self.spent_usd)

    @property
    def status(self) -> str:
        p = self.pct
        if p >= 100:
            return "exceeded"
        if p >= self.alert_pct:
            return "alert"
        return "ok"

    @property
    def status_glyph(self) -> str:
        return {"ok": "✓", "alert": "⚠", "exceeded": "✗"}[self.status]

    @property
    def status_color(self) -> str:
        return {"ok": "green", "alert": "yellow", "exceeded": "red"}[self.status]

    @property
    def bar(self, width: int = 15) -> str:
        f = int(self.pct / 100 * width)
        return "█" * f + "░" * (width - f)

    def to_dict(self) -> dict:
        return {
            "limit_usd": self.limit_usd,
            "spent_usd": self.spent_usd,
            "alert_pct": self.alert_pct,
            "last_reset": self.last_reset,
            "session_spend": self.session_spend,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BudgetState:
        return cls(
            limit_usd=d.get("limit_usd", 10.0),
            spent_usd=d.get("spent_usd", 0.0),
            alert_pct=d.get("alert_pct", 80.0),
            last_reset=d.get("last_reset", time.time()),
            session_spend=d.get("session_spend", {}),
        )

    def render(self) -> str:
        return (
            f"[{self.status_color}]{self.bar}[/]  "
            f"[{self.status_color}]{self.pct:.1f}%[/]  "
            f"[dim]${self.spent_usd:.4f} / ${self.limit_usd:.2f}[/]  "
            f"[dim]${self.remaining_usd:.4f} remaining[/]"
        )


# ── Persistence ────────────────────────────────────────────────────────


def _load_budget() -> BudgetState:
    if BUDGET_FILE.exists():
        try:
            return BudgetState.from_dict(json.loads(BUDGET_FILE.read_text()))
        except Exception:
            pass
    return BudgetState()


def _save_budget(state: BudgetState) -> None:
    BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    BUDGET_FILE.write_text(json.dumps(state.to_dict(), indent=2))


def _record_spend(amount_usd: float, session_id: str = "") -> BudgetState:
    state = _load_budget()
    state.spent_usd += amount_usd
    if session_id:
        state.session_spend[session_id] = state.session_spend.get(session_id, 0.0) + amount_usd
    _save_budget(state)
    return state


# ── Slash command ──────────────────────────────────────────────────────


def cmd_budget(session: Any, args: str) -> CommandResult:
    """Track and manage session spending.

    Usage:
      /budget              — show current budget status
      /budget set <usd>    — set budget cap
      /budget alert <pct>  — set alert percentage
      /budget reset        — reset spent counter
      /budget record <usd> — record spend (for agent loop)
    """
    parts = args.strip().split() if args.strip() else []
    subcmd = parts[0].lower() if parts else "show"

    state = _load_budget()

    if subcmd == "show" or not parts:
        lines = [
            "[bold]Budget[/]",
            f"  {state.render()}",
            f"  Status: [{state.status_color}]{state.status_glyph} {state.status}[/]",
            f"  Alert:  {state.alert_pct:.0f}% of cap",
        ]
        if state.session_spend:
            lines.append("")
            lines.append("[dim]By session:[/]")
            for sid, amt in sorted(state.session_spend.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  [dim]{sid[:20]}[/]  ${amt:.4f}")
        return CommandResult(
            output=(
                f"Budget: ${state.spent_usd:.4f} / ${state.limit_usd:.2f} ({state.pct:.1f}%) ["
                f"{state.status}]"
            ),
            renderable="\n".join(lines),
        )

    if subcmd == "set":
        if len(parts) < 2:
            return CommandResult(output="Usage: /budget set <usd>")
        try:
            new_limit = float(parts[1])
            if new_limit <= 0:
                return CommandResult(output="Budget limit must be positive")
            state.limit_usd = new_limit
            _save_budget(state)
            return CommandResult(output=f"✓ Budget cap set to ${new_limit:.2f}")
        except ValueError:
            return CommandResult(output="Usage: /budget set <usd>")

    if subcmd == "alert":
        if len(parts) < 2:
            return CommandResult(output="Usage: /budget alert <pct>")
        try:
            pct = float(parts[1])
            state.alert_pct = max(1.0, min(99.0, pct))
            _save_budget(state)
            return CommandResult(output=f"✓ Alert threshold set to {state.alert_pct:.0f}%")
        except ValueError:
            return CommandResult(output="Usage: /budget alert <pct>")

    if subcmd == "reset":
        state.spent_usd = 0.0
        state.session_spend = {}
        state.last_reset = time.time()
        _save_budget(state)
        return CommandResult(output="✓ Budget spent counter reset")

    if subcmd == "record":
        if len(parts) < 2:
            return CommandResult(output="Usage: /budget record <usd>")
        try:
            amount = float(parts[1])
            session_id = getattr(session, "session_id", "") if session else ""
            new_state = _record_spend(amount, session_id)
            return CommandResult(
                output=f"✓ Recorded ${amount:.4f} spend (total: ${new_state.spent_usd:.4f})"
            )
        except ValueError:
            return CommandResult(output="Usage: /budget record <usd>")

    return CommandResult(output="Usage: /budget [show|set|alert|reset|record]")


# ── TUI Widget ─────────────────────────────────────────────────────────


class BudgetStatusWidget(Widget):
    """Live budget tracker — spend vs cap with alert bar.

    Ctrl+Shift+B to toggle. Shows current spend, cap, alert threshold,
    and per-session breakdown.
    """

    DEFAULT_CSS = """
    BudgetStatusWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    BudgetStatusWidget.collapsed {
        height: 1;
        border: none;
    }

    BudgetStatusWidget #budget-header {
        height: 1;
        color: $text-muted;
    }

    BudgetStatusWidget #budget-content {
        height: auto;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+b", "toggle_budget", "Budget"),
    ]

    expanded: reactive[bool] = reactive(False)
    spent: reactive[float] = reactive(0.0)
    limit: reactive[float] = reactive(10.0)

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("", id="budget-header")
        yield Static("", id="budget-content")

    def on_mount(self) -> None:
        self._refresh()

    def _load(self) -> BudgetState:
        return _load_budget()

    def _refresh(self) -> None:
        state = self._load()
        self.spent = state.spent_usd
        self.limit = state.limit_usd
        self._render()

    def action_toggle_budget(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._refresh()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        state = self._load()
        try:
            hint = "[dim](ctrl+shift+b)[/]"
            if self.expanded:
                self.query_one("#budget-header", Static).update(
                    f"[bold]Budget[/]  [{state.status_color}]{state.status_glyph}[/]  {hint}"
                )
                lines = [f"  {state.render()}"]
                if state.session_spend:
                    lines.append("")
                    lines.append("[dim]By session:[/]")
                    for sid, amt in sorted(state.session_spend.items(), key=lambda x: -x[1])[:5]:
                        lines.append(f"  [dim]{sid[:20]}[/]  ${amt:.4f}")
                self.query_one("#budget-content", Static).update("\n".join(lines))
            else:
                self.query_one("#budget-header", Static).update(
                    f"[bold]Budget[/]  "
                    f"[{state.status_color}]{state.pct:.0f}%[/]  "
                    f"[dim]${state.spent_usd:.2f}/${state.limit_usd:.2f}[/]  {hint}"
                )
                self.query_one("#budget-content", Static).update("")
        except Exception:
            pass


__all__ = [
    "cmd_budget",
    "BudgetState",
    "BudgetStatusWidget",
    "_load_budget",
    "_save_budget",
    "_record_spend",
]
