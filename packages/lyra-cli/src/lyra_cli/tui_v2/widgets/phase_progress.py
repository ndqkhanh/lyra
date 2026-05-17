"""Phase/step progress tracking."""
from typing import List
from dataclasses import dataclass


@dataclass
class Phase:
    """A phase in a multi-phase task."""
    name: str
    status: str = "pending"  # pending, in_progress, completed, error


class PhaseProgress:
    """Track multi-phase task progress.

    Example:
    ✶ Galloping… (32s · ↓ 20 tokens)
      ⎿  ◻ Phase 9: Production Readiness
         ◻ Phase 3: Implement Research Pipeline
         ◻ Phase 6: Interactive UI & Themes
         ◻ Phase 5: Memory Systems
         ◻ Phase 2: Integrate Real Agent Loop
          … +3 pending
    """

    def __init__(self):
        self.phases: List[Phase] = []

    def add_phase(self, name: str, status: str = "pending") -> None:
        """Add a phase to track."""
        self.phases.append(Phase(name=name, status=status))

    def update_phase(self, name: str, status: str) -> None:
        """Update phase status."""
        for phase in self.phases:
            if phase.name == name:
                phase.status = status
                break

    def get_phase(self, name: str) -> Phase | None:
        """Get phase by name."""
        for phase in self.phases:
            if phase.name == name:
                return phase
        return None

    def render(self, max_visible: int = 5) -> str:
        """Render phase progress.

        Args:
            max_visible: Maximum number of phases to show

        Returns:
            Formatted phase progress string
        """
        if not self.phases:
            return ""

        lines = []
        visible_phases = self.phases[:max_visible]

        for phase in visible_phases:
            # Status icon
            if phase.status == "completed":
                icon = "✓"
            elif phase.status == "in_progress":
                icon = "⏺"
            elif phase.status == "error":
                icon = "✗"
            else:
                icon = "◻"

            lines.append(f"     {icon} {phase.name}")

        # Show remaining count
        remaining = len(self.phases) - max_visible
        if remaining > 0:
            lines.append(f"      … +{remaining} pending")

        return "\n".join(lines)

    def get_summary(self) -> str:
        """Get one-line summary of progress."""
        if not self.phases:
            return ""

        completed = sum(1 for p in self.phases if p.status == "completed")
        total = len(self.phases)

        return f"{completed}/{total} phases complete"

    def clear(self) -> None:
        """Clear all phases."""
        self.phases.clear()
