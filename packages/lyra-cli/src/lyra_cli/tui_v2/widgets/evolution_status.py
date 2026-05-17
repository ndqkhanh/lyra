"""Evolution status widget for TUI."""
from textual.reactive import reactive
from textual.widget import Widget
from rich.text import Text


class EvolutionStatusWidget(Widget):
    """Display meta-evolution progress."""

    round_current: reactive[int] = reactive(0)
    round_total: reactive[int] = reactive(0)
    segment_current: reactive[int] = reactive(0)
    segment_total: reactive[int] = reactive(0)
    best_score: reactive[float] = reactive(0.0)
    cost_spent: reactive[float] = reactive(0.0)
    cost_budget: reactive[float] = reactive(0.0)
    last_edit: reactive[str] = reactive("")
    active: reactive[bool] = reactive(False)

    def render(self) -> Text:
        """Render evolution status."""
        if not self.active:
            return Text("")

        lines = [
            "┌─ Meta-Evolution ─────────────────┐",
            f"│ Round: {self.round_current}/{self.round_total}                      │",
            f"│ Segment: {self.segment_current}/{self.segment_total}                     │",
            f"│ Best Score: {self.best_score:.2f}                 │",
            f"│ Cost: ${self.cost_spent:.2f} / ${self.cost_budget:.2f}             │",
            f"│ Last Edit: {self.last_edit[:20]:<20} │",
            "└──────────────────────────────────┘",
        ]
        return Text("\n".join(lines), style="cyan")
