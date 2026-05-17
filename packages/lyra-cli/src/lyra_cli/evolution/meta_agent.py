"""Meta-agent controller for evolution."""
from pathlib import Path
import json
from datetime import datetime

from lyra_cli.evolution.context import EvolutionContext, Observation
from lyra_cli.evolution.actions import EditAction, EditType


class MetaAgent:
    """Meta-controller that edits the evolver."""

    def __init__(self, evolution_dir: Path):
        self.evolution_dir = Path(evolution_dir)
        self.meta_edits_dir = self.evolution_dir / "archive" / "meta_edits"

    def observe(self, context: EvolutionContext) -> Observation:
        """Digest scores, traces, failures into observation."""
        if not context.scores:
            return Observation(
                best_score=0.0,
                worst_score=0.0,
                avg_score=0.0,
                num_candidates=0,
                num_failures=len(context.failures),
                recent_edits=context.meta_edits[-5:],
                summary="No candidates evaluated yet",
            )

        scores = [s.get("score", 0.0) for s in context.scores]
        return Observation(
            best_score=max(scores),
            worst_score=min(scores),
            avg_score=sum(scores) / len(scores),
            num_candidates=len(context.candidates),
            num_failures=len(context.failures),
            recent_edits=context.meta_edits[-5:],
            summary=f"{len(context.candidates)} candidates, best={max(scores):.2f}",
        )

    def plan_edit(self, obs: Observation) -> EditAction:
        """Propose edit to evolver (code or context)."""
        # Placeholder: real implementation would use LLM
        return EditAction(
            edit_type=EditType.AGENT_CONTEXT,
            target_path="skills.md",
            content="# Updated skills based on observation",
            rationale=f"Observed {obs.num_candidates} candidates with avg score {obs.avg_score:.2f}",
        )

    def apply_edit(self, action: EditAction) -> None:
        """Apply edit and log to meta_edits/."""
        timestamp = datetime.now().isoformat()
        edit_log = {
            "timestamp": timestamp,
            "edit_type": action.edit_type.value,
            "target_path": action.target_path,
            "rationale": action.rationale,
        }

        log_path = self.meta_edits_dir / f"edit_{timestamp.replace(':', '-')}.json"
        log_path.write_text(json.dumps(edit_log, indent=2))
