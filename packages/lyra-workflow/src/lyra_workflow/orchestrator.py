"""
Auto-Orchestration Trigger — effort-driven workflow auto-detection.

Implements Primitive 2 of the ultracode replication plan: when auto-orchestration
is enabled (ultracode mode), Lyra decides on its own whether a task warrants a
workflow instead of waiting to be asked.

The trigger uses a lightweight complexity estimator (<50ms) that checks:
- Word count of the user prompt
- Keyword matches against complex-task indicators
- File/system scope indicators (codebase, all files, every)

If complexity >= the configured auto-trigger threshold, Lyra proposes a
dynamic workflow instead of working turn-by-turn.

Design rationale: This is the "ultracode decision" — the thin layer that
converts a user prompt into a workflow plan. It must be fast (<50ms) and
never block the user. The actual decision of WHAT workflow to create is
delegated to the LLM (via the workflow script authoring step).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskComplexity(str, Enum):
    """Estimated complexity of a user task for workflow triggering."""

    TRIVIAL = "trivial"  # Greetings, simple questions, 1-step commands
    LOW = "low"          # Single-file changes, simple lookups
    MEDIUM = "medium"    # Multi-step tasks, moderate coding
    HIGH = "high"        # Architecture, refactoring, auditing, research


@dataclass(frozen=True)
class OrchestrationDecision:
    """Result of the auto-orchestration decision."""

    should_orchestrate: bool
    complexity: TaskComplexity
    reasoning: str
    estimated_phases: int = 1
    estimated_agents: int = 1


class AutoOrchestrator:
    """
    Effort-driven auto-orchestration trigger.

    Estimates task complexity from the user prompt and decides whether
    to auto-trigger a dynamic workflow. Fast (<50ms), never blocks.

    Usage::

        orchestrator = AutoOrchestrator(threshold=TaskComplexity.MEDIUM)
        decision = orchestrator.evaluate("Audit all auth endpoints for PCI compliance")
        if decision.should_orchestrate:
            engine.start(plan_workflow(decision))
    """

    # Keywords that signal high complexity (3+ matches → HIGH)
    _COMPLEX_KEYWORDS: frozenset[str] = frozenset({
        "audit", "migrate", "refactor", "research", "investigate",
        "across", "all files", "every", "codebase", "benchmark", "evaluate",
        "architecture", "system design", "implement a complete",
        "deploy", "orchestrate", "full pipeline", "end-to-end",
        "security review", "compliance", "enterprise",
    })

    # Keywords that signal medium complexity
    _MEDIUM_KEYWORDS: frozenset[str] = frozenset({
        "multiple", "several", "analyze", "review", "optimize",
        "create a", "build a", "add", "integrate", "configure",
        "setup", "debug", "test", "document", "generate",
    })

    def __init__(self, threshold: TaskComplexity = TaskComplexity.MEDIUM) -> None:
        """
        Args:
            threshold: Minimum complexity to auto-trigger a workflow.
                ``MEDIUM`` (default) matches Claude Code's behavior.
                ``HIGH`` is more conservative (fewer workflows, lower cost).
                ``LOW`` triggers workflows more aggressively.
        """
        self._threshold = threshold

    def evaluate(self, prompt: str) -> OrchestrationDecision:
        """
        Estimate task complexity and decide whether to orchestrate.

        Args:
            prompt: The user's natural language task description.

        Returns:
            An OrchestrationDecision with the complexity estimate and
            whether a workflow should be triggered.
        """
        words = prompt.lower().split()
        word_count = len(words)

        # Trivial: very short prompts
        if word_count < 5:
            return OrchestrationDecision(
                should_orchestrate=False,
                complexity=TaskComplexity.TRIVIAL,
                reasoning=f"Very short prompt ({word_count} words)",
            )

        # Count keyword matches
        complex_matches = sum(
            1 for kw in self._COMPLEX_KEYWORDS if kw in prompt.lower()
        )
        medium_matches = sum(
            1 for kw in self._MEDIUM_KEYWORDS if kw in prompt.lower()
        )

        # Classify complexity
        if complex_matches >= 3 or (complex_matches >= 2 and word_count > 50):
            complexity = TaskComplexity.HIGH
        elif complex_matches >= 1 or medium_matches >= 3:
            complexity = TaskComplexity.MEDIUM
        elif medium_matches >= 1 or word_count > 30:
            complexity = TaskComplexity.LOW
        else:
            complexity = TaskComplexity.TRIVIAL

        # Estimate phases and agents
        if complexity == TaskComplexity.HIGH:
            estimated_phases = 3  # Discover → Verify → Report
            estimated_agents = min(complex_matches * 4, 50)
        elif complexity == TaskComplexity.MEDIUM:
            estimated_phases = 2
            estimated_agents = min(medium_matches * 2, 16)
        else:
            estimated_phases = 1
            estimated_agents = 1

        # Decision: orchestrate if complexity >= threshold
        complexity_order = {
            TaskComplexity.TRIVIAL: 0, TaskComplexity.LOW: 1,
            TaskComplexity.MEDIUM: 2, TaskComplexity.HIGH: 3,
        }
        should = complexity_order[complexity] >= complexity_order[self._threshold]

        return OrchestrationDecision(
            should_orchestrate=should,
            complexity=complexity,
            reasoning=(
                f"Complexity: {complexity.value} "
                f"(complex_kw={complex_matches}, medium_kw={medium_matches}, "
                f"words={word_count})"
            ),
            estimated_phases=estimated_phases,
            estimated_agents=estimated_agents,
        )

    @property
    def threshold(self) -> TaskComplexity:
        return self._threshold
