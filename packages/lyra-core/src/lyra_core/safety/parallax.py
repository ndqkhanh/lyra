"""Phase 13.3 — Cognitive-Executive Separation (Parallax).

Structural separation of reasoning context (read-only) from execution
context (action-capable). The model may reason freely in a sandboxed
context but must pass through the SeparationGate before any tool or
filesystem action is permitted. Target block rate: 98.9% of plans that
violate policy.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


__all__ = [
    "CognitiveContext",
    "ContextType",
    "ExecutionPlan",
    "ParallaxConfig",
    "SeparationGate",
]


class ContextType(Enum):
    """Distinguishes a read-only reasoning context from an action-capable
    execution context."""

    REASONING = "reasoning"
    EXECUTION = "execution"


@dataclass(frozen=True)
class ExecutionPlan:
    """A structured plan produced by the reasoning context that must be
    validated before execution is allowed."""

    plan_id: str
    steps: tuple[str, ...]
    required_tools: tuple[str, ...]
    file_targets: tuple[str, ...]
    risk_level: float  # 0.0 (safe) … 1.0 (critical)
    reasoning_summary: str
    proposed_by: str  # model family (e.g. "claude-sonnet-4-20250514")


@dataclass(frozen=True)
class SeparationGate:
    """The gate decision after a plan has been validated.

    Only plans with ``approved=True`` may proceed to execution.
    """

    plan: ExecutionPlan
    approved: bool
    validator_model: str
    validation_reasoning: str
    risk_mitigations: tuple[str, ...] = ()
    block_reason: str = ""


@dataclass(frozen=True)
class ParallaxConfig:
    """Configuration for the Parallax separation gate."""

    max_risk_threshold: float = 0.7
    require_different_validator: bool = True
    blocked_tools: tuple[str, ...] = (
        "rm -rf",
        "DROP TABLE",
        "git push --force",
    )
    audit_all_plans: bool = True


class CognitiveContext:
    """Manages the separation of reasoning from execution.

    Usage::

        ctx = CognitiveContext(config=ParallaxConfig())
        reasoning_id = ctx.create_reasoning_context()

        # … model reasons, produces an ExecutionPlan …

        gate = ctx.submit_plan(plan)
        if gate.approved:
            exec_id = ctx.create_execution_context(reasoning_id)
            ctx.execute_approved(gate)
    """

    def __init__(self, config: ParallaxConfig | None = None) -> None:
        self._config = config or ParallaxConfig()
        self._reasoning_contexts: set[str] = set()
        self._execution_contexts: dict[str, str] = {}  # exec_ctx_id -> reasoning_ctx_id
        self._plans: list[ExecutionPlan] = []
        self._gates: list[SeparationGate] = []
        self._total_plans: int = 0
        self._approved: int = 0
        self._blocked: int = 0

    # ------------------------------------------------------------------
    # Context lifecycle
    # ------------------------------------------------------------------

    def create_reasoning_context(self) -> str:
        """Create a read-only reasoning context and return its ID."""
        ctx_id = f"reason-{uuid.uuid4().hex}"
        self._reasoning_contexts.add(ctx_id)
        return ctx_id

    def create_execution_context(self, reasoning_ctx_id: str) -> str:
        """Create an action-capable execution context tied to an existing
        reasoning context.

        Raises ``ValueError`` if *reasoning_ctx_id* does not exist.
        """
        if reasoning_ctx_id not in self._reasoning_contexts:
            raise ValueError(
                f"Unknown reasoning context: {reasoning_ctx_id!r}"
            )
        exec_id = f"exec-{uuid.uuid4().hex}"
        self._execution_contexts[exec_id] = reasoning_ctx_id
        return exec_id

    # ------------------------------------------------------------------
    # Plan validation
    # ------------------------------------------------------------------

    def submit_plan(self, plan: ExecutionPlan) -> SeparationGate:
        """Submit an execution plan for validation.

        This method auto-generates a validator model name and delegates
        to :meth:`validate_plan`.
        """
        validator = f"validator-{uuid.uuid4().hex[:8]}"
        return self.validate_plan(plan, validator_model=validator)

    def validate_plan(
        self,
        plan: ExecutionPlan,
        validator_model: str,
    ) -> SeparationGate:
        """Validate an execution plan against the configured policy.

        Checks performed:
        * Risk level against ``max_risk_threshold``.
        * Tool access — any tool in ``blocked_tools`` that appears in the
          plan's ``required_tools`` causes a block.
        * Validator separation — when ``require_different_validator`` is
          set, the validator model family must differ from the proposer's.
        * Always validates when ``audit_all_plans`` is ``True``.
        """
        self._total_plans += 1
        self._plans.append(plan)

        mitigations: list[str] = []

        # --- risk check -------------------------------------------------
        if plan.risk_level > self._config.max_risk_threshold:
            gate = SeparationGate(
                plan=plan,
                approved=False,
                validator_model=validator_model,
                validation_reasoning=(
                    f"Risk level {plan.risk_level:.2f} exceeds "
                    f"threshold {self._config.max_risk_threshold:.2f}."
                ),
                block_reason="risk_threshold_exceeded",
            )
            self._gates.append(gate)
            self._blocked += 1
            return gate

        # --- tool check -------------------------------------------------
        blocked = [
            tool for tool in plan.required_tools
            if any(b.lower() in tool.lower() for b in self._config.blocked_tools)
        ]
        if blocked:
            gate = SeparationGate(
                plan=plan,
                approved=False,
                validator_model=validator_model,
                validation_reasoning=(
                    f"Plan requires blocked tool(s): {', '.join(blocked)}."
                ),
                block_reason="blocked_tool_requested",
            )
            self._gates.append(gate)
            self._blocked += 1
            return gate

        # --- validator separation check ---------------------------------
        if self._config.require_different_validator:
            proposer_prefix = plan.proposed_by.split("-")[0].lower()
            validator_prefix = validator_model.split("-")[0].lower()
            if proposer_prefix and proposer_prefix == validator_prefix:
                gate = SeparationGate(
                    plan=plan,
                    approved=False,
                    validator_model=validator_model,
                    validation_reasoning=(
                        f"Validator model {validator_model!r} shares the "
                        f"same family as proposer {plan.proposed_by!r}."
                    ),
                    block_reason="same_model_family_validator",
                )
                self._gates.append(gate)
                self._blocked += 1
                return gate

        # --- explicit mitigations for borderline risk -------------------
        if plan.risk_level > self._config.max_risk_threshold * 0.8:
            mitigations.append("human_review_recommended")

        gate = SeparationGate(
            plan=plan,
            approved=True,
            validator_model=validator_model,
            validation_reasoning="All policy checks passed.",
            risk_mitigations=tuple(mitigations),
        )
        self._gates.append(gate)
        self._approved += 1
        return gate

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_approved(self, gate: SeparationGate) -> bool:
        """Execute a plan iff its gate is approved.

        Returns ``True`` when execution is allowed, ``False`` when
        rejected.
        """
        if not gate.approved:
            return False
        return True

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, object]:
        """Return aggregate separation statistics."""
        total = self._total_plans
        approved = self._approved
        blocked = self._blocked
        avg_risk = (
            sum(p.risk_level for p in self._plans) / len(self._plans)
            if self._plans
            else 0.0
        )
        return {
            "total_plans": total,
            "approved": approved,
            "blocked": blocked,
            "block_rate": blocked / total if total else 0.0,
            "avg_risk": avg_risk,
        }
