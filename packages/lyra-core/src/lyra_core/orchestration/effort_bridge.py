"""
Effort-Orchestration Bridge — wires the effort scale to auto-orchestration.

This thin integration layer connects Primitive 1 (effort scale) to Primitive 2
(auto-orchestration toggle) and Primitive 3 (dynamic workflow engine). When the
active effort level is ``ultracode`` (xhigh budget + orchestration toggle), user
tasks are evaluated for complexity and potentially auto-orchestrated into
dynamic workflows.

Design rationale: The effort scale and workflow engine are independently useful.
This bridge is the minimal glue that makes "ultracode" work — it reads the effort
level, evaluates task complexity, and dispatches to the workflow engine when
appropriate. No module in Lyra should import from this module directly; it is
used at the agent/conversation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from lyra_effort.models import EffortLevel
from lyra_workflow.engine import WorkflowScript
from lyra_workflow.orchestrator import (
    AutoOrchestrator,
    OrchestrationDecision,
    TaskComplexity,
)


@dataclass(frozen=True)
class EffortBridge:
    """
    Reads the active effort level and routes tasks through the orchestrator.

    When effort is ULTRACODE, tasks are evaluated for complexity. If the
    complexity exceeds the configured threshold, the orchestrator proposes
    a dynamic workflow instead of turn-by-turn execution.

    Usage::

        bridge = EffortBridge(effort_level=EffortLevel.ULTRACODE)
        decision = bridge.evaluate("Audit all payment endpoints for PCI")

        if decision.should_orchestrate:
            workflow = bridge.plan_workflow(decision)
            engine.start(workflow)
        else:
            agent.handle_turn_by_turn(prompt)
    """

    effort_level: EffortLevel
    orchestrator: AutoOrchestrator | None = None
    _orchestration_provider: str = ""  # Provider label for provider-aware degradation

    def __post_init__(self) -> None:
        if self.effort_level.orchestration_enabled and self.orchestrator is None:
            object.__setattr__(
                self, "orchestrator", AutoOrchestrator(threshold=TaskComplexity.MEDIUM)
            )

    def should_orchestrate(self, prompt: str) -> bool:
        """Check whether a task should be auto-orchestrated."""
        if not self.effort_level.orchestration_enabled:
            return False
        if self.orchestrator is None:
            return False
        provider = self._orchestration_provider or None
        return self.orchestrator.evaluate(prompt, provider=provider).should_orchestrate

    def evaluate(self, prompt: str) -> OrchestrationDecision:
        """Evaluate task complexity and decide whether to auto-orchestrate."""
        if not self.effort_level.orchestration_enabled:
            return OrchestrationDecision(
                should_orchestrate=False,
                complexity=TaskComplexity.TRIVIAL,
                reasoning="Orchestration disabled (effort={})".format(
                    self.effort_level.value
                ),
            )
        if self.orchestrator is None:
            return OrchestrationDecision(
                should_orchestrate=False,
                complexity=TaskComplexity.TRIVIAL,
                reasoning="No orchestrator configured",
            )
        provider = self._orchestration_provider or None
        return self.orchestrator.evaluate(prompt, provider=provider)

    def plan_workflow(
        self,
        decision: OrchestrationDecision,
    ) -> WorkflowScript:
        """Create a workflow script from an orchestration decision."""
        from lyra_workflow.engine import WorkflowPhase

        script = WorkflowScript(
            name="ultracode-workflow",
            providers={
                "explore": "deepseek-flash",   # Cheap, fast discovery
                "verify": "claude-sonnet",     # Reliable verification
                "synthesize": "claude-opus",   # Best quality synthesis
            },
        )

        if decision.estimated_phases >= 1:
            script.phases.append(WorkflowPhase(name="Discover"))
        if decision.estimated_phases >= 2:
            script.phases.append(WorkflowPhase(name="Verify"))
        if decision.estimated_phases >= 3:
            script.phases.append(WorkflowPhase(name="Report"))

        return script

    @staticmethod
    def from_config(effort_value: str) -> EffortBridge:
        """Create an EffortBridge from a string effort level."""
        try:
            level = EffortLevel(effort_value)
        except ValueError:
            level = EffortLevel.HIGH
        return EffortBridge(effort_level=level)
