"""Iterative workspace reconstruction — the evolving report M_t pattern from IterResearch.

Implements Markovian state compression: at each step, update a compressed
workspace report M_t. Future decisions condition on (question, M_t, last_interaction)
only — constant O(1) workspace vs O(t) growth.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkspaceReport:
    """Compressed workspace state that replaces raw history.

    Based on IterResearch (2511.07327v2, ICLR 2026) and Tongyi DeepResearch
    (2510.24701v3) — five independent groups converged on this pattern.
    """

    summary: str = ""
    key_findings: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    token_estimate: int = 0

    def update(self, new_observation: str, action_outcome: str):
        """Synthesize new M_{t+1} from (M_t, observation, outcome)."""
        if new_observation:
            self.key_findings.append(new_observation)
        if action_outcome:
            self.decisions_made.append(action_outcome)
        # Prune old findings to keep workspace compact
        if len(self.key_findings) > 20:
            self.key_findings = self.key_findings[-15:]
        if len(self.decisions_made) > 20:
            self.decisions_made = self.decisions_made[-15:]

    def to_prompt_context(self) -> str:
        """Render the workspace as a compact context block."""
        parts = []
        if self.summary:
            parts.append(f"## Current State\n{self.summary}")
        if self.key_findings:
            parts.append("## Key Findings\n" + "\n".join(f"- {f}" for f in self.key_findings[-10:]))
        if self.open_questions:
            parts.append("## Open Questions\n" + "\n".join(f"- {q}" for q in self.open_questions))
        if self.next_steps:
            parts.append("## Next Steps\n" + "\n".join(f"- {s}" for s in self.next_steps))
        return "\n\n".join(parts)

    def estimate_tokens(self) -> int:
        """Rough token estimate for budget tracking."""
        full_text = self.to_prompt_context()
        return len(full_text.split()) * 2  # ~2 tokens per word
