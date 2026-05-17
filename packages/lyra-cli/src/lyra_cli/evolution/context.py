"""Evolution context and observation types."""
from dataclasses import dataclass, field


@dataclass
class EvolutionContext:
    """Context for meta-agent observation."""
    candidates: list[dict] = field(default_factory=list)
    scores: list[dict] = field(default_factory=list)
    meta_edits: list[dict] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def append_candidate(self, candidate: dict, score: dict):
        """Add candidate and score to context."""
        self.candidates.append(candidate)
        self.scores.append(score)

    def append_edit(self, edit: dict):
        """Add meta-edit to context."""
        self.meta_edits.append(edit)

    def append_failure(self, failure: str):
        """Add failure message to context."""
        self.failures.append(failure)


@dataclass
class Observation:
    """Digested observation from evolution context."""
    best_score: float
    worst_score: float
    avg_score: float
    num_candidates: int
    num_failures: int
    recent_edits: list[dict]
    summary: str
