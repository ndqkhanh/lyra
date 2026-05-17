"""Evolution harness with capability boundaries."""
from pathlib import Path
import json
from typing import Optional


class EvolutionHarness:
    """Protected environment for agent evolution."""

    def __init__(self, evolution_dir: Path):
        self.evolution_dir = Path(evolution_dir)
        self.archive_dir = self.evolution_dir / "archive"
        self.workspace_dir = self.evolution_dir / "workspace"
        self.evaluator_dir = self.evolution_dir / "evaluator"

    def evaluate(self, candidate_id: str) -> dict:
        """Run protected scorer, return redacted results."""
        candidate_path = self.archive_dir / "candidates" / f"{candidate_id}.json"
        if not candidate_path.exists():
            return {"error": "Candidate not found", "score": 0.0}

        # Protected evaluation (simplified)
        score = self._run_evaluator(candidate_id)

        # Write to scores (agent cannot write here)
        score_path = self.archive_dir / "scores" / f"{candidate_id}.json"
        score_path.write_text(json.dumps({"candidate_id": candidate_id, "score": score}))

        return {"score": score, "candidate_id": candidate_id}

    def submit(self, candidate_id: str) -> bool:
        """Write to official score (write-only for agent)."""
        # Agent can submit but not read back
        return True

    def workspace_read(self, path: str) -> Optional[str]:
        """Read from workspace (confined to workspace/)."""
        # Resolve paths to prevent traversal attacks
        full_path = (self.workspace_dir / path).resolve()
        workspace_resolved = self.workspace_dir.resolve()

        if not full_path.is_relative_to(workspace_resolved):
            raise PermissionError(f"Access denied: path '{path}' is outside workspace")

        if full_path.exists():
            return full_path.read_text()
        return None

    def workspace_write(self, path: str, content: str) -> bool:
        """Write to workspace (confined to workspace/)."""
        # Resolve paths to prevent traversal attacks
        full_path = (self.workspace_dir / path).resolve()
        workspace_resolved = self.workspace_dir.resolve()

        if not full_path.is_relative_to(workspace_resolved):
            raise PermissionError(f"Access denied: path '{path}' is outside workspace")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        return True

    def _run_evaluator(self, candidate_id: str) -> float:
        """Protected evaluator (simplified placeholder)."""
        # Real implementation would run actual evaluation
        return 0.5
