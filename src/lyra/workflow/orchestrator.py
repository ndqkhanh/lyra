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
    provider_fallback: bool = False  # True when provider-specific fallback was applied
    ultrathink_triggered: bool = False  # True when "ultrathink" keyword was detected


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

    def evaluate(
        self,
        prompt: str,
        provider: str | None = None,
    ) -> OrchestrationDecision:
        """
        Estimate task complexity and decide whether to orchestrate.

        Args:
            prompt: The user's natural language task description.
            provider: The orchestration model's provider for provider-aware
                degradation. ``anthropic``/``openai`` → full auto-trigger,
                ``deepseek`` → auto-trigger + explicit prompt fallback,
                ``openweights`` → keyword-only (no auto-trigger).

        Returns:
            An OrchestrationDecision with the complexity estimate and
            whether a workflow should be triggered.
        """
        words = prompt.lower().split()
        word_count = len(words)

        # Complexity ordering for threshold comparison
        _complexity_order = {
            TaskComplexity.TRIVIAL: 0, TaskComplexity.LOW: 1,
            TaskComplexity.MEDIUM: 2, TaskComplexity.HIGH: 3,
        }

        # ── Ultrathink keyword detection ──────────────────────
        # "ultrathink" triggers one-off deep reasoning without changing
        # session effort. Flags the decision so callers can apply deep
        # reasoning to the prompt without escalating to a workflow.
        if "ultrathink" in prompt.lower():
            return OrchestrationDecision(
                should_orchestrate=False,
                complexity=TaskComplexity.LOW,
                reasoning="ultrathink keyword detected — one-off deep reasoning triggered",
                estimated_phases=1,
                estimated_agents=1,
                ultrathink_triggered=True,
            )

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
        should = _complexity_order[complexity] >= _complexity_order[self._threshold]

        # ── Provider-aware degradation ──────────────────────────
        # Different providers have different auto-trigger reliability.
        provider_fallback = False
        reasoning = (
            f"Complexity: {complexity.value} "
            f"(complex_kw={complex_matches}, medium_kw={medium_matches}, "
            f"words={word_count})"
        )
        if provider and not should:
            pass  # Already not orchestrating — no further action needed
        elif provider == "openweights":
            # Open-weights: keyword trigger only, no auto-trigger reliability
            if should:
                should = False
                provider_fallback = True
                reasoning += " | Provider fallback: open-weights auto-trigger unreliable, keyword-only"
        elif provider == "deepseek":
            # DeepSeek: less reliable auto-trigger → attach explicit prompt fallback
            if should:
                reasoning += " | Prompt fallback: 'This task may benefit from a workflow. Plan one?'"

        return OrchestrationDecision(
            should_orchestrate=should,
            complexity=complexity,
            reasoning=reasoning,
            estimated_phases=estimated_phases,
            estimated_agents=estimated_agents,
            provider_fallback=provider_fallback,
        )

    @property
    def threshold(self) -> TaskComplexity:
        return self._threshold
