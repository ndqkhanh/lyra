"""
Context Visualization - Context window usage visualization and management.

Features:
- Token usage breakdown
- Context ring visualization
- Component-level tracking
- Context management tools
"""

from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class ContextComponent(Enum):
    """Context component types."""

    SYSTEM_PROMPT = "system_prompt"
    CONVERSATION = "conversation"
    TOOL_RESULTS = "tool_results"
    CODE_CONTEXT = "code_context"
    MEMORY = "memory"
    OTHER = "other"


@dataclass
class ContextUsage:
    """Context usage data."""

    component: ContextComponent
    tokens: int
    percentage: float
    description: str


class ContextTracker:
    """
    Context window tracker.

    Features:
    - Component-level tracking
    - Token counting
    - Usage breakdown
    """

    def __init__(self, total_tokens: int = 200000):
        """
        Initialize context tracker.

        Args:
            total_tokens: Total context window size
        """
        self.total_tokens = total_tokens
        self.components: dict[ContextComponent, int] = dict.fromkeys(ContextComponent, 0)

    def add_tokens(self, component: ContextComponent, tokens: int):
        """
        Add tokens to component.

        Args:
            component: Context component
            tokens: Number of tokens
        """
        self.components[component] += tokens

    def set_tokens(self, component: ContextComponent, tokens: int):
        """
        Set tokens for component.

        Args:
            component: Context component
            tokens: Number of tokens
        """
        self.components[component] = tokens

    def get_tokens(self, component: ContextComponent) -> int:
        """
        Get tokens for component.

        Args:
            component: Context component

        Returns:
            Token count
        """
        return self.components.get(component, 0)

    def get_total_used(self) -> int:
        """
        Get total tokens used.

        Returns:
            Total tokens
        """
        return sum(self.components.values())

    def get_percentage(self, component: ContextComponent) -> float:
        """
        Get percentage for component.

        Args:
            component: Context component

        Returns:
            Percentage (0-100)
        """
        total = self.get_total_used()
        if total == 0:
            return 0.0
        return (self.components[component] / total) * 100

    def get_total_percentage(self) -> float:
        """
        Get total usage percentage.

        Returns:
            Percentage (0-100)
        """
        return (self.get_total_used() / self.total_tokens) * 100

    def get_breakdown(self) -> list[ContextUsage]:
        """
        Get usage breakdown.

        Returns:
            List of context usage data
        """
        breakdown = []
        for component in ContextComponent:
            tokens = self.get_tokens(component)
            if tokens > 0:
                breakdown.append(
                    ContextUsage(
                        component=component,
                        tokens=tokens,
                        percentage=self.get_percentage(component),
                        description=component.value.replace("_", " ").title(),
                    )
                )
        return breakdown

    def clear_component(self, component: ContextComponent):
        """
        Clear component tokens.

        Args:
            component: Context component
        """
        self.components[component] = 0

    def clear_all(self):
        """Clear all tokens."""
        for component in ContextComponent:
            self.components[component] = 0


class ContextRingVisualizer:
    """
    Context ring visualizer.

    Features:
    - Ring chart visualization
    - Color-coded segments
    - Percentage display
    """

    def __init__(self, console: Console | None = None):
        """Initialize context ring visualizer."""
        self.console = console or Console()

    def render_ring(self, tracker: ContextTracker) -> str:
        """
        Render context ring.

        Args:
            tracker: Context tracker

        Returns:
            Rendered ring
        """
        total_percentage = tracker.get_total_percentage()

        # Color coding
        if total_percentage < 50:
            color = "green"
        elif total_percentage < 80:
            color = "yellow"
        else:
            color = "red"

        # Simple text-based ring
        bar_width = 30
        filled = int((total_percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        used = tracker.get_total_used()
        total = tracker.total_tokens

        return f"[{color}]{bar}[/{color}] {used:,} / {total:,} ({total_percentage:.1f}%)"

    def render_breakdown(self, tracker: ContextTracker) -> Table:
        """
        Render breakdown table.

        Args:
            tracker: Context tracker

        Returns:
            Rich table
        """
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Tokens", style="yellow", justify="right")
        table.add_column("Percentage", style="green", justify="right")

        breakdown = tracker.get_breakdown()
        for usage in breakdown:
            table.add_row(
                usage.description,
                f"{usage.tokens:,}",
                f"{usage.percentage:.1f}%",
            )

        # Add total row
        total_used = tracker.get_total_used()
        total_percentage = tracker.get_total_percentage()
        table.add_row(
            "[bold]Total[/bold]",
            f"[bold]{total_used:,}[/bold]",
            f"[bold]{total_percentage:.1f}%[/bold]",
        )

        return table

    def display(self, tracker: ContextTracker):
        """
        Display context visualization.

        Args:
            tracker: Context tracker
        """
        # Ring
        ring = self.render_ring(tracker)
        self.console.print(Panel(ring, title="Context Usage", border_style="blue"))

        # Breakdown
        table = self.render_breakdown(tracker)
        self.console.print(table)


class ContextManager:
    """
    Context management tools.

    Features:
    - Context export
    - Context import
    - Context pruning
    """

    def __init__(self, tracker: ContextTracker):
        """
        Initialize context manager.

        Args:
            tracker: Context tracker
        """
        self.tracker = tracker

    def export_context(self) -> dict[str, int]:
        """
        Export context data.

        Returns:
            Context data dictionary
        """
        return {
            component.value: self.tracker.get_tokens(component) for component in ContextComponent
        }

    def import_context(self, data: dict[str, int]):
        """
        Import context data.

        Args:
            data: Context data dictionary
        """
        for component_name, tokens in data.items():
            try:
                component = ContextComponent(component_name)
                self.tracker.set_tokens(component, tokens)
            except ValueError:
                pass  # Skip unknown components

    def prune_component(self, component: ContextComponent, target_tokens: int):
        """
        Prune component to target size.

        Args:
            component: Context component
            target_tokens: Target token count
        """
        current = self.tracker.get_tokens(component)
        if current > target_tokens:
            self.tracker.set_tokens(component, target_tokens)

    def get_recommendations(self) -> list[str]:
        """
        Get optimization recommendations.

        Returns:
            List of recommendations
        """
        recommendations = []
        total_percentage = self.tracker.get_total_percentage()

        if total_percentage > 80:
            recommendations.append("⚠️  Context usage is high (>80%). Consider compaction.")

        breakdown = self.tracker.get_breakdown()
        for usage in breakdown:
            if usage.percentage > 40:
                recommendations.append(

                        f"⚠️  {usage.description} uses {usage.percentage:.1f}"
                        f"% of context. Consider pruning."

                )

        if not recommendations:
            recommendations.append("✓ Context usage is healthy.")

        return recommendations
