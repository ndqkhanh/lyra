"""Background task panel like Claude Code."""
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class BackgroundTask:
    """Status of a background task."""
    description: str
    agent_type: str
    start_time: float = field(default_factory=time.time)
    tokens: int = 0
    status: str = "running"  # running, completed, error


class BackgroundTaskPanel:
    """Shows background tasks with status.

    Example:
    ⏵⏵ bypass permissions on · 5 background tasks · esc to interrupt · ctrl+t

      ⏺ main                                           ↑/↓ to select · Enter to view
      ◯ general-purpose  Deep research: Kilo, Hermes…  3m 4s · ↓ 63.6k tokens
      ◯ general-purpose  Verify model diversity…       3m 3s · ↓ 102.2k tokens
    """

    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.selected_index = 0
        self.visible = False

    def add_task(self, task_id: str, description: str, agent_type: str) -> None:
        """Add background task."""
        self.tasks[task_id] = BackgroundTask(
            description=description,
            agent_type=agent_type,
        )

    def update_task(
        self,
        task_id: str,
        tokens: Optional[int] = None,
        status: Optional[str] = None,
    ) -> None:
        """Update task status."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        if tokens is not None:
            task.tokens = tokens
        if status is not None:
            task.status = status

    def remove_task(self, task_id: str) -> None:
        """Remove completed task."""
        self.tasks.pop(task_id, None)

    def toggle_visibility(self) -> None:
        """Toggle panel visibility."""
        self.visible = not self.visible

    def select_next(self) -> None:
        """Select next task."""
        if self.tasks:
            self.selected_index = (self.selected_index + 1) % len(self.tasks)

    def select_previous(self) -> None:
        """Select previous task."""
        if self.tasks:
            self.selected_index = (self.selected_index - 1) % len(self.tasks)

    def render(self) -> str:
        """Render background task panel."""
        if not self.visible or not self.tasks:
            return ""

        lines = []

        # Header
        task_count = len(self.tasks)
        header = f"⏵⏵ bypass permissions on · {task_count} background tasks · "
        header += "esc to interrupt · ctrl+t to hide"
        lines.append(header)
        lines.append("")

        # Main task indicator
        lines.append("  ⏺ main                                           ↑/↓ to select · Enter to view")

        # Task list
        task_items = list(self.tasks.items())
        for i, (task_id, task) in enumerate(task_items):
            selected = "⏺" if i == self.selected_index else "◯"

            # Duration
            elapsed = time.time() - task.start_time
            if elapsed < 60:
                duration_str = f"{int(elapsed)}s"
            else:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                duration_str = f"{minutes}m {seconds}s"

            # Tokens
            tokens_str = f"↓ {task.tokens/1000:.1f}k tokens"

            # Truncate description
            desc = task.description
            if len(desc) > 40:
                desc = desc[:37] + "…"

            line = f"  {selected} {task.agent_type}  {desc}  "
            line += f"{duration_str} · {tokens_str}"
            lines.append(line)

        return "\n".join(lines)

    def get_summary(self) -> str:
        """Get one-line summary for status bar."""
        if not self.tasks:
            return ""

        running = sum(1 for t in self.tasks.values() if t.status == "running")
        return f"{running} background tasks"
