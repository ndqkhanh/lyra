"""
Human-in-the-Loop (HITL) Gate System

Implements AutoResearchClaw's 7-mode collaboration spectrum:
- Mode 0: Full Auto
- Mode 1: Gate Review (phase boundaries)
- Mode 2: Stage Approval (all 23 stages)
- Mode 3: Critical Gates (stages 5, 9, 15, 20)
- Mode 4: Experiment Only (stage 10)
- Mode 5: Writing Review (paper stages)
- Mode 6: Full Manual (every decision)

Based on: researchclaw/hitl/gate_orchestrator.py
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class HITLMode(Enum):
    """Human-in-the-loop collaboration mode"""
    FULL_AUTO = 0        # No human intervention
    GATE_REVIEW = 1      # Review at phase boundaries
    STAGE_APPROVAL = 2   # Approve each stage
    CRITICAL_GATES = 3   # Only critical decision points
    EXPERIMENT_ONLY = 4  # Only experiment execution
    WRITING_REVIEW = 5   # Only paper generation
    FULL_MANUAL = 6      # Every decision


class HITLPolicy(Enum):
    """Policy for human intervention at a gate"""
    NONE = "none"              # Auto-proceed
    REVIEW = "review"          # Show output, wait for approval
    EDIT = "edit"              # Allow human modification
    COLLABORATE = "collaborate"  # Interactive co-creation


@dataclass
class GatePoint:
    """Definition of a gate point in the pipeline"""
    stage_id: str
    stage_name: str
    description: str
    policy: HITLPolicy
    is_critical: bool = False


@dataclass
class GateDecision:
    """Human decision at a gate"""
    approved: bool
    modified_output: Any | None = None
    feedback: str | None = None
    skip_remaining: bool = False


class GateOrchestrator:
    """
    Orchestrates human-in-the-loop gates in research pipeline

    Implements AutoResearchClaw's gate system with configurable modes
    """

    # Critical gate stages (Mode 3)
    CRITICAL_STAGES = ["5", "9", "15", "20"]

    # Experiment stages (Mode 4)
    EXPERIMENT_STAGES = ["10", "11", "12", "13", "14"]

    # Writing stages (Mode 5)
    WRITING_STAGES = ["17", "18", "19", "20", "21"]

    def __init__(
        self,
        mode: HITLMode = HITLMode.CRITICAL_GATES,
        custom_gates: list[GatePoint] | None = None,
        approval_callback: Callable[[GatePoint, Any], GateDecision] | None = None,
    ):
        """
        Initialize gate orchestrator

        Args:
            mode: HITL collaboration mode
            custom_gates: Custom gate definitions (overrides mode)
            approval_callback: Function to get human approval
        """
        self.mode = mode
        self.custom_gates = custom_gates
        self.approval_callback = approval_callback or self._default_approval
        self.gate_history: list[dict[str, Any]] = []

    def should_gate(self, stage_id: str) -> bool:
        """
        Check if a gate should be applied at this stage

        Args:
            stage_id: Stage identifier

        Returns:
            True if gate should be applied
        """

        # Custom gates override mode
        if self.custom_gates:
            return any(gate.stage_id == stage_id for gate in self.custom_gates)

        # Mode-based gating
        if self.mode == HITLMode.FULL_AUTO:
            return False

        elif self.mode == HITLMode.FULL_MANUAL:
            return True

        elif self.mode == HITLMode.STAGE_APPROVAL:
            return True

        elif self.mode == HITLMode.CRITICAL_GATES:
            return stage_id in self.CRITICAL_STAGES

        elif self.mode == HITLMode.EXPERIMENT_ONLY:
            return stage_id in self.EXPERIMENT_STAGES

        elif self.mode == HITLMode.WRITING_REVIEW:
            return stage_id in self.WRITING_STAGES

        elif self.mode == HITLMode.GATE_REVIEW:
            # Phase boundaries (simplified - would map stages to phases)
            phase_boundaries = ["4", "8", "9", "14", "16", "21", "23"]
            return stage_id in phase_boundaries

        return False

    def get_gate_policy(self, stage_id: str) -> HITLPolicy:
        """
        Get policy for a gate

        Args:
            stage_id: Stage identifier

        Returns:
            HITLPolicy for this gate
        """

        # Custom gates
        if self.custom_gates:
            for gate in self.custom_gates:
                if gate.stage_id == stage_id:
                    return gate.policy

        # Default policies by mode
        if self.mode == HITLMode.FULL_MANUAL:
            return HITLPolicy.COLLABORATE

        elif self.mode == HITLMode.CRITICAL_GATES:
            return HITLPolicy.REVIEW

        elif self.mode == HITLMode.EXPERIMENT_ONLY:
            return HITLPolicy.EDIT

        elif self.mode == HITLMode.WRITING_REVIEW:
            return HITLPolicy.EDIT

        else:
            return HITLPolicy.REVIEW

    def process_gate(
        self,
        stage_id: str,
        stage_name: str,
        output: Any,
        context: dict[str, Any] | None = None,
    ) -> GateDecision:
        """
        Process a gate point

        Args:
            stage_id: Stage identifier
            stage_name: Human-readable stage name
            output: Output from the stage
            context: Additional context

        Returns:
            GateDecision with approval and optional modifications
        """

        # Check if gate should be applied
        if not self.should_gate(stage_id):
            return GateDecision(approved=True)

        # Get policy
        policy = self.get_gate_policy(stage_id)

        # Create gate point
        gate = GatePoint(
            stage_id=stage_id,
            stage_name=stage_name,
            description=f"Gate at {stage_name}",
            policy=policy,
            is_critical=stage_id in self.CRITICAL_STAGES,
        )

        # Get human decision
        decision = self.approval_callback(gate, output)

        # Record in history
        self.gate_history.append({
            "stage_id": stage_id,
            "stage_name": stage_name,
            "policy": policy.value,
            "approved": decision.approved,
            "modified": decision.modified_output is not None,
            "feedback": decision.feedback,
        })

        logger.info(
            f"Gate {stage_id} ({stage_name}): "
            f"{'APPROVED' if decision.approved else 'REJECTED'}"
        )

        return decision

    def _default_approval(self, gate: GatePoint, output: Any) -> GateDecision:
        """
        Default approval callback (auto-approve with logging)

        In production, this would prompt the user for input
        """

        logger.info(f"Gate: {gate.stage_name} ({gate.policy.value})")
        logger.info(f"Output preview: {str(output)[:200]}...")

        # Auto-approve in default implementation
        return GateDecision(approved=True)

    def get_statistics(self) -> dict[str, Any]:
        """Get gate statistics"""

        if not self.gate_history:
            return {
                "total_gates": 0,
                "approved": 0,
                "rejected": 0,
                "modified": 0,
            }

        return {
            "total_gates": len(self.gate_history),
            "approved": sum(1 for g in self.gate_history if g["approved"]),
            "rejected": sum(1 for g in self.gate_history if not g["approved"]),
            "modified": sum(1 for g in self.gate_history if g["modified"]),
            "by_stage": {
                g["stage_id"]: g["approved"]
                for g in self.gate_history
            },
        }


class InteractiveGateCallback:
    """
    Interactive callback for terminal-based approval

    Prompts user for approval in terminal
    """

    def __call__(self, gate: GatePoint, output: Any) -> GateDecision:
        """Prompt user for approval"""

        print("\n" + "=" * 60)
        print(f"GATE: {gate.stage_name}")
        print(f"Policy: {gate.policy.value}")
        if gate.is_critical:
            print("⚠️  CRITICAL GATE")
        print("=" * 60)

        # Show output preview
        output_str = str(output)
        if len(output_str) > 500:
            output_str = output_str[:500] + "..."
        print(f"\nOutput:\n{output_str}\n")

        # Get decision based on policy
        if gate.policy == HITLPolicy.REVIEW:
            response = input("Approve? (y/n/s=skip remaining): ").lower()

            if response == 's':
                return GateDecision(approved=True, skip_remaining=True)
            elif response == 'y':
                return GateDecision(approved=True)
            else:
                feedback = input("Feedback (optional): ")
                return GateDecision(approved=False, feedback=feedback or None)

        elif gate.policy == HITLPolicy.EDIT:
            response = input("Approve/Edit/Reject? (a/e/r): ").lower()

            if response == 'a':
                return GateDecision(approved=True)
            elif response == 'e':
                print("Enter modified output (Ctrl+D when done):")
                lines = []
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    pass
                modified = "\n".join(lines)
                return GateDecision(approved=True, modified_output=modified)
            else:
                feedback = input("Feedback (optional): ")
                return GateDecision(approved=False, feedback=feedback or None)

        elif gate.policy == HITLPolicy.COLLABORATE:
            print("Collaborative mode - iterative refinement")
            response = input("Continue/Modify/Stop? (c/m/s): ").lower()

            if response == 'c':
                return GateDecision(approved=True)
            elif response == 'm':
                print("Enter modifications (Ctrl+D when done):")
                lines = []
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    pass
                modified = "\n".join(lines)
                return GateDecision(approved=True, modified_output=modified)
            else:
                return GateDecision(approved=False)

        else:
            # NONE policy - auto-approve
            return GateDecision(approved=True)


def create_gate_config(
    mode: HITLMode = HITLMode.CRITICAL_GATES,
    custom_stages: list[str] | None = None,
    interactive: bool = False,
) -> GateOrchestrator:
    """
    Convenience function: Create gate orchestrator with common configurations

    Args:
        mode: HITL collaboration mode
        custom_stages: Custom stage IDs to gate (overrides mode)
        interactive: Use interactive terminal callback

    Returns:
        Configured GateOrchestrator
    """

    custom_gates = None
    if custom_stages:
        custom_gates = [
            GatePoint(
                stage_id=stage_id,
                stage_name=f"Stage {stage_id}",
                description=f"Custom gate at stage {stage_id}",
                policy=HITLPolicy.REVIEW,
            )
            for stage_id in custom_stages
        ]

    callback = InteractiveGateCallback() if interactive else None

    return GateOrchestrator(
        mode=mode,
        custom_gates=custom_gates,
        approval_callback=callback,
    )


# Goldilocks Zone Analysis
class GoldillocksAnalyzer:
    """
    Analyzes gate effectiveness to find optimal collaboration mode

    Based on AutoResearchClaw's finding that Mode 3 (Critical Gates)
    achieves 89% of full-manual quality at 23% of time cost
    """

    @staticmethod
    def analyze_mode_effectiveness(
        gate_history: list[dict[str, Any]],
        quality_score: float,
        time_cost: float,
    ) -> dict[str, Any]:
        """
        Analyze effectiveness of current mode

        Args:
            gate_history: History of gate decisions
            quality_score: Quality metric (0-1)
            time_cost: Time cost in seconds

        Returns:
            Analysis with recommendations
        """

        total_gates = len(gate_history)
        approved = sum(1 for g in gate_history if g["approved"])
        modified = sum(1 for g in gate_history if g["modified"])

        # Compute metrics
        approval_rate = approved / total_gates if total_gates > 0 else 1.0
        modification_rate = modified / total_gates if total_gates > 0 else 0.0

        # Heuristic recommendations
        recommendations = []

        if approval_rate > 0.95 and modification_rate < 0.05:
            recommendations.append(
                "High approval rate with few modifications - consider FULL_AUTO mode"
            )

        if modification_rate > 0.3:
            recommendations.append(
                "High modification rate - consider FULL_MANUAL or COLLABORATE mode"
            )

        if total_gates > 20:
            recommendations.append(
                "Many gates triggered - consider CRITICAL_GATES mode to reduce overhead"
            )

        return {
            "total_gates": total_gates,
            "approval_rate": approval_rate,
            "modification_rate": modification_rate,
            "quality_score": quality_score,
            "time_cost": time_cost,
            "efficiency": quality_score / (time_cost / 3600) if time_cost > 0 else 0,
            "recommendations": recommendations,
        }
