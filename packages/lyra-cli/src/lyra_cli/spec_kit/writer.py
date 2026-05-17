"""Disk write operations for spec-kit artifacts."""

from __future__ import annotations
from pathlib import Path
from typing import Any

from .events import SpecFilesWritten


class Writer:
    """Writes spec artifacts to disk after approval."""

    def __init__(self, event_bus: Any = None):
        self.event_bus = event_bus
        self.specs_dir = Path(".specify")
        self.features_dir = Path("specs")

    async def write_artifacts(
        self,
        feature_id: str,
        spec: str,
        plan: str,
        tasks: str
    ) -> list[str]:
        """Write spec/plan/tasks to disk."""
        # Create feature directory
        feature_dir = self.features_dir / feature_id
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Write files
        paths = []

        spec_path = feature_dir / "spec.md"
        spec_path.write_text(spec)
        paths.append(str(spec_path))

        plan_path = feature_dir / "plan.md"
        plan_path.write_text(plan)
        paths.append(str(plan_path))

        tasks_path = feature_dir / "tasks.md"
        tasks_path.write_text(tasks)
        paths.append(str(tasks_path))

        # Emit event
        if self.event_bus:
            event = SpecFilesWritten(feature_id=feature_id, paths=paths)
            # Would emit to event bus here

        return paths

    def generate_feature_id(self, prompt: str) -> str:
        """Generate feature ID from prompt."""
        # Get next number
        existing = list(self.features_dir.glob("*-*"))
        numbers = [int(p.name.split("-")[0]) for p in existing if p.name.split("-")[0].isdigit()]
        next_num = max(numbers, default=0) + 1

        # Generate slug from prompt (first 4 words)
        words = prompt.lower().split()[:4]
        slug = "-".join(w for w in words if w.isalnum())

        return f"{next_num:03d}-{slug}"
