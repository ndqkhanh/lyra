"""
Steering Engine — mid-run correction, undo, preference capture, trust calibration.

Per plan §4.22: When Lyra runs an autonomous ultracode workflow, users MUST be able to:
(1) see what's happening, (2) stop/pause individual agents, (3) correct wrong direction
mid-run, (4) undo agent actions, and (5) have Lyra learn from corrections.

Commands implemented:
  /steer focus on <topic>    — redirect workflow to prioritize specific area
  /steer ignore <topic>      — tell workflow to skip specific area
  /steer use <model>         — switch model for remaining tasks
  /steer budget <amount>     — change budget limit for remaining tasks
  /steer verify more/less    — adjust verification strictness
  /undo                      — undo last mutating action
  /undo <N>                  — undo last N mutating actions

Architecture: Steering commands capture user intent as structured preferences,
apply to current workflow AND store in TKG for future sessions. Trust calibration
adjusts autonomy level based on correction frequency.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class SteerAction(str, Enum):
    """Types of steering actions the user can take."""
    FOCUS = "focus"       # Prioritize a topic
    IGNORE = "ignore"     # Skip a topic
    USE_MODEL = "use"     # Switch model
    BUDGET = "budget"     # Change budget limit
    VERIFY = "verify"     # Adjust verification strictness
    UNDO = "undo"         # Rollback actions


class AutonomyLevel(str, Enum):
    """Autonomy level — adjusted by trust calibration."""
    SUPERVISED = "supervised"       # Ask before every mutating action
    COLLABORATIVE = "collaborative" # Proactive prompts on high-stakes decisions
    AUTONOMOUS = "autonomous"       # Full auto (with AVP gating)


@dataclass
class SteeringEvent:
    """A single steering action captured as a structured preference."""
    action: SteerAction
    target: str = ""           # topic, model, budget amount, etc.
    timestamp: float = field(default_factory=time.time)
    workflow_context: str = ""  # What was happening when the user steered
    outcome: str | None = None  # Updated after workflow completes
    learned_constraint: str = ""  # LLM-generalized version for future runs


@dataclass
class UndoEntry:
    """Record of a mutating action that can be undone."""
    action_id: str
    description: str
    git_ref: str = ""  # Git ref before the action (for rollback)
    timestamp: float = field(default_factory=time.time)
    undone: bool = False


# ---------------------------------------------------------------------------
# Steering Engine
# ---------------------------------------------------------------------------


class SteeringEngine:
    """Central steering engine for mid-run correction and preference learning.

    Integrates with:
    - WorkflowEngine (via callback) for pause/redirect
    - lyra-personalization (TKG) for preference storage
    - Git for undo/rollback
    - AVP (§4.16) for verification strictness adjustment
    - Router (§4.5) for model switching
    """

    def __init__(self) -> None:
        self._preferences: list[SteeringEvent] = []
        self._undo_stack: list[UndoEntry] = []
        self._corrections: list[SteeringEvent] = []
        self._total_decisions: int = 0
        self._active_workflow_id: str | None = None
        self._budget: float = 5.0  # Default $5
        self._model: str = "auto"
        self._verify_strictness: float = 0.5  # 0.0 = lenient, 1.0 = strict
        self._paused: bool = False

    # -- Steering commands --------------------------------------------------

    def steer(
        self,
        action: str,
        target: str = "",
        workflow_context: str = "",
    ) -> str:
        """Execute a steering command and return a human-readable response.

        Args:
            action: One of focus, ignore, use, budget, verify
            target: The topic/model/budget to steer toward
            workflow_context: Description of current workflow state

        Returns:
            Confirmation message for the user
        """
        try:
            steer_action = SteerAction(action.lower())
        except ValueError:
            return f"Unknown steer action: {action!r}. Valid: focus, ignore, use, budget, verify"

        event = SteeringEvent(
            action=steer_action,
            target=target,
            workflow_context=workflow_context,
        )
        self._preferences.append(event)

        if steer_action == SteerAction.FOCUS:
            self._corrections.append(event)
            self._total_decisions += 1
            return f"🎯 Focusing on: {target}. Remaining workflow will prioritize this area."

        elif steer_action == SteerAction.IGNORE:
            self._corrections.append(event)
            self._total_decisions += 1
            return f"🚫 Ignoring: {target}. Remaining workflow will skip this area."

        elif steer_action == SteerAction.USE_MODEL:
            self._model = target
            self._total_decisions += 1
            return f"🤖 Switched to model: {target} for remaining tasks."

        elif steer_action == SteerAction.BUDGET:
            try:
                self._budget = float(target)
            except ValueError:
                return f"Invalid budget: {target!r}. Use a number like '3.00'."
            self._total_decisions += 1
            return f"💰 Budget set to ${self._budget:.2f} for remaining tasks."

        elif steer_action == SteerAction.VERIFY:
            if target.lower() in ("more", "stricter", "++"):
                self._verify_strictness = min(1.0, self._verify_strictness + 0.25)
            elif target.lower() in ("less", "lenient", "--"):
                self._verify_strictness = max(0.0, self._verify_strictness - 0.25)
            else:
                return f"Unknown verify level: {target!r}. Use 'more' or 'less'."
            self._total_decisions += 1
            return f"🔍 Verification strictness: {self._verify_strictness:.0%}"

        return f"Unknown steering action: {action}"

    # -- Undo ---------------------------------------------------------------

    def record_action(
        self,
        action_id: str,
        description: str,
        capture_git_ref: bool = True,
    ) -> None:
        """Record a mutating action for potential undo."""
        git_ref = ""
        if capture_git_ref:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                git_ref = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        self._undo_stack.append(UndoEntry(
            action_id=action_id,
            description=description,
            git_ref=git_ref,
        ))

    def undo(self, count: int = 1) -> str:
        """Undo the last N mutating actions via git rollback.

        Returns a human-readable summary of what was undone.
        """
        if not self._undo_stack:
            return "Nothing to undo — no mutating actions recorded."

        count = min(count, len(self._undo_stack))
        undone: list[str] = []

        for _ in range(count):
            entry = self._undo_stack.pop()
            entry.undone = True

            if entry.git_ref:
                try:
                    # Reset files to state at git_ref for affected paths
                    subprocess.run(
                        ["git", "checkout", entry.git_ref, "--", "."],
                        capture_output=True, timeout=30,
                    )
                    undone.append(f"⏪ {entry.description} (git rollback to {entry.git_ref[:8]})")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    undone.append(f"⚠️  {entry.description} (git rollback failed — manual recovery needed)")
            else:
                undone.append(f"⚠️  {entry.description} (no git ref — manual undo needed)")

        summary = "\n".join(undone)
        summary += f"\n\n📋 Undid {count} action(s). {len(self._undo_stack)} remaining in undo stack."
        return summary

    def undo_last(self) -> str:
        """Undo exactly the last action."""
        return self.undo(count=1)

    # -- Trust calibration --------------------------------------------------

    def calibrate_trust(self) -> AutonomyLevel:
        """Calculate appropriate autonomy level based on correction history.

        Per plan §4.22:
        - correctionRate > 0.3 → supervised
        - correctionRate > 0.1 → collaborative
        - otherwise → autonomous
        """
        if self._total_decisions == 0:
            return AutonomyLevel.COLLABORATIVE

        correction_rate = len(self._corrections) / self._total_decisions

        if correction_rate > 0.3:
            return AutonomyLevel.SUPERVISED
        if correction_rate > 0.1:
            return AutonomyLevel.COLLABORATIVE
        return AutonomyLevel.AUTONOMOUS

    def should_ask_before_action(self) -> bool:
        """Check if the current autonomy level requires user approval."""
        level = self.calibrate_trust()
        return level == AutonomyLevel.SUPERVISED

    # -- Preference capture -------------------------------------------------

    def capture_preference(
        self,
        instruction: str,
        workflow_context: str,
        generalize_fn: Callable[[str, str], str] | None = None,
    ) -> SteeringEvent:
        """Capture a free-form steering instruction as a structured preference.

        The instruction is stored with workflow context and can be generalized
        by an LLM for application to future similar contexts.
        """
        event = SteeringEvent(
            action=SteerAction.FOCUS,  # default for free-form
            target=instruction,
            workflow_context=workflow_context,
        )
        self._preferences.append(event)
        self._corrections.append(event)
        self._total_decisions += 1

        if generalize_fn:
            event.learned_constraint = generalize_fn(instruction, workflow_context)

        return event

    # -- Properties ---------------------------------------------------------

    @property
    def budget(self) -> float:
        return self._budget

    @property
    def model(self) -> str:
        return self._model

    @property
    def verify_strictness(self) -> float:
        return self._verify_strictness

    @property
    def autonomy_level(self) -> AutonomyLevel:
        return self.calibrate_trust()

    @property
    def correction_rate(self) -> float:
        if self._total_decisions == 0:
            return 0.0
        return len(self._corrections) / self._total_decisions

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "preferences_captured": len(self._preferences),
            "undo_stack_depth": len(self._undo_stack),
            "corrections": len(self._corrections),
            "total_decisions": self._total_decisions,
            "correction_rate": round(self.correction_rate, 3),
            "autonomy_level": self.autonomy_level.value,
            "current_budget": self._budget,
            "current_model": self._model,
            "verify_strictness": self._verify_strictness,
            "paused": self._paused,
        }


# ---------------------------------------------------------------------------
# Interrupt Handler
# ---------------------------------------------------------------------------


class InterruptHandler:
    """Handles Ctrl+C and other interrupt signals for graceful barge-in.

    Per interruptible agents research (CHI/ACL): barge-in semantics require
    stopping the current action while preserving completed work. This handler
    provides the state machine for pause → redirect → resume.
    """

    def __init__(self, steering: SteeringEngine) -> None:
        self._steering = steering
        self._interrupt_count: int = 0
        self._last_interrupt: float = 0.0
        self._double_tap_window: float = 1.0  # seconds

    def handle_interrupt(self) -> str:
        """Handle a single interrupt signal (Ctrl+C).

        First press: pause workflow, prompt for redirection
        Second press within double_tap_window: stop entirely
        """
        now = time.time()
        self._interrupt_count += 1

        if now - self._last_interrupt <= self._double_tap_window:
            self._steering._paused = False
            self._last_interrupt = now
            return "🛑 Workflow stopped. All progress saved."

        self._steering._paused = True
        self._last_interrupt = now
        return (
            "⏸️  Workflow paused. What would you like to do?\n"
            "   /steer focus on <topic> — redirect focus\n"
            "   /steer ignore <topic> — skip an area\n"
            "   /resume — continue work\n"
            "   Ctrl+C again — stop entirely"
        )

    def resume(self) -> str:
        """Resume a paused workflow."""
        self._steering._paused = False
        return "▶️  Workflow resumed."

    @property
    def is_paused(self) -> bool:
        return self._steering._paused

    @property
    def interrupt_count(self) -> int:
        return self._interrupt_count
