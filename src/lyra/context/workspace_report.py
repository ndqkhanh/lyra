"""
Workspace Report - Evolving compressed workspace representation M_t.

Implements Iterative Workspace Reconstruction (Breakthrough #1):
- O(1) memory per step instead of O(t) growth
- M_{t+1} = synthesize(M_t, latest_observations, action_outcome)
- Configurable compression (AGGRESSIVE | BALANCED | VERBOSE)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from lyra.context.compaction import CompactionStrategy, COMPACTION_PROMPTS

SynthesizeFn = Callable[[str], str] | None

_TOKEN_ESTIMATE_RATIO = 0.75  # Rough word-to-token ratio


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text (rough heuristic)."""
    return int(len(text.split()) / _TOKEN_ESTIMATE_RATIO)


def _now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def _default_compress(
    old_report: str | None,
    new_observations: str,
    action_outcome: str,
    strategy: CompactionStrategy,
) -> str:
    """Fallback synthesizer when no LLM function is provided.

    Produces a simple merged report by combining existing context with new
    observations.  Does not achieve O(1) memory on its own; the LLM-powered
    :param:`synthesize_fn` is required for true bounded growth.
    """
    prefix = ""
    if old_report:
        prefix = old_report.rstrip() + "\n\n"
    return (
        f"{prefix}--- Step ---\n"
        f"Observations: {new_observations}\n"
        f"Outcome: {action_outcome}"
    )


@dataclass
class WorkspaceReport:
    """Evolving compressed workspace report that replaces linear context accumulation.

    Attributes:
        report_text: The current synthesised markdown report.
        key_findings: Extracted key findings discovered so far.
        step_count: Number of update cycles applied.
        total_tokens_saved: Cumulative tokens saved vs. naive concatenation.
        created_at: Timestamp of first creation.
        updated_at: Timestamp of most recent update.
    """

    report_text: str
    key_findings: list[str] = field(default_factory=list)
    step_count: int = 0
    total_tokens_saved: int = 0
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    # --- Public API ---------------------------------------------------------

    def update(
        self,
        new_observations: str,
        action_outcome: str,
        strategy: CompactionStrategy = CompactionStrategy.BALANCED,
        synthesize_fn: SynthesizeFn = None,
    ) -> "WorkspaceReport":
        """Synthesise a new compressed report M_{t+1}.

        Uses the provided LLM :param:`synthesize_fn` (or a fallback merge) to
        produce a compact representation of prior context combined with the
        latest step's observations and outcome.

        Args:
            new_observations: Raw observations from the latest step.
            action_outcome: Outcome of the action taken.
            strategy: Compression aggressiveness.
            synthesize_fn: Callable that takes a prompt and returns
                synthesised text.  When ``None`` a simple text merge is used
                (does **not** achieve bounded growth).

        Returns:
            A new ``WorkspaceReport`` instance with the updated state.
        """
        raw_tokens = _estimate_tokens(
            self.report_text
            + new_observations
            + action_outcome
        )

        if synthesize_fn is not None:
            prompt = _build_synthesis_prompt(
                current_report=self.report_text,
                new_observations=new_observations,
                action_outcome=action_outcome,
                key_findings=self.key_findings,
                strategy=strategy,
                step_count=self.step_count,
            )
            synthesized = synthesize_fn(prompt)
            new_key_findings = self.key_findings[:]
            step_count = self.step_count + 1
        else:
            synthesized = _default_compress(
                old_report=self.report_text,
                new_observations=new_observations,
                action_outcome=action_outcome,
                strategy=strategy,
            )
            new_key_findings = self.key_findings[:]
            step_count = self.step_count + 1

        synthesized_tokens = _estimate_tokens(synthesized)
        tokens_saved_this_step = max(0, raw_tokens - synthesized_tokens)

        return WorkspaceReport(
            report_text=synthesized,
            key_findings=new_key_findings,
            step_count=step_count,
            total_tokens_saved=self.total_tokens_saved + tokens_saved_this_step,
            created_at=self.created_at,
            updated_at=_now(),
        )

    def to_prompt_context(self) -> str:
        """Format the report for injection into an LLM system message.

        Returns a concise markdown string describing the workspace state
        discovered so far.
        """
        lines = [
            "<workspace_context>",
            f"Steps completed: {self.step_count}",
            f"Tokens saved: {self.total_tokens_saved}",
            "",
            "### Workspace Report",
            self.report_text,
            "",
            "### Key Findings",
        ]

        if self.key_findings:
            for i, finding in enumerate(self.key_findings, 1):
                lines.append(f"{i}. {finding}")
        else:
            lines.append("_(no findings extracted yet)_")

        lines.append("</workspace_context>")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_synthesis_prompt(
    current_report: str,
    new_observations: str,
    action_outcome: str,
    key_findings: list[str],
    strategy: CompactionStrategy,
    step_count: int,
) -> str:
    """Build the prompt sent to the LLM synthesizer."""
    prompt_template = COMPACTION_PROMPTS[strategy]
    key_findings_str = "\n".join(f"- {f}" for f in key_findings) if key_findings else "_(none yet)_"

    return prompt_template.format(
        current_report=current_report,
        new_observations=new_observations,
        action_outcome=action_outcome,
        key_findings=key_findings_str,
        step_count=step_count,
    )
