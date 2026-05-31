"""State-Machine Tool Gating per Workflow Phase — P1-X (HIGH, MED).

Define workflow phases as states, transitions between them, and gate
tool availability based on the current phase. Each phase has an explicit
allow-list of tools; transitions carry guards that must be satisfied.

See: plan-phase1-harness.md, statewright
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Workflow Phase
# ---------------------------------------------------------------------------


class WorkflowPhase(str, enum.Enum):
    """Standard agent workflow phases."""

    INIT = "init"
    PLANNING = "planning"
    RESEARCH = "research"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    REVIEW = "review"
    COMPLETE = "complete"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Transition Guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Transition:
    """A directed transition between two workflow phases."""

    name: str
    from_phase: WorkflowPhase
    to_phase: WorkflowPhase
    description: str = ""


GuardFn = Callable[["PhaseStateMachine", dict[str, Any]], bool]


# ---------------------------------------------------------------------------
# Phase Definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhaseDef:
    """Definition of a workflow phase including allowed tools."""

    phase: WorkflowPhase
    allowed_tools: frozenset[str] | None = None  # None = all allowed, empty = none allowed
    required_tools: frozenset[str] = frozenset()
    max_tool_calls: int = 0  # 0 = unlimited
    description: str = ""


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------


@dataclass
class PhaseStateMachine:
    """State machine that gates tool access based on workflow phase.

    Usage::

        sm = PhaseStateMachine()
        sm.add_phase(WorkflowPhase.PLANNING, allowed_tools={"read", "search"})
        sm.add_phase(WorkflowPhase.EXECUTION, allowed_tools={"read", "write", "bash"})
        sm.add_transition("plan_done", WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION)
        sm.start(WorkflowPhase.PLANNING)

        sm.can_use_tool("read")   # True
        sm.can_use_tool("write")  # False (planning phase)
        sm.transition("plan_done")
        sm.can_use_tool("write")  # True (execution phase)
    """

    _phases: dict[WorkflowPhase, PhaseDef] = field(default_factory=dict)
    _transitions: dict[WorkflowPhase, list[Transition]] = field(default_factory=dict)
    _guards: dict[str, GuardFn] = field(default_factory=dict)
    current_phase: WorkflowPhase = WorkflowPhase.INIT
    _phase_history: list[WorkflowPhase] = field(default_factory=list)
    _tool_call_count: int = field(default=0, init=False)
    _total_tool_calls: int = field(default=0, init=False)

    # --- Phase management -----------------------------------------------------

    def add_phase(
        self,
        phase: WorkflowPhase,
        *,
        allowed_tools: set[str] | None = None,
        required_tools: set[str] | None = None,
        max_tool_calls: int = 0,
        description: str = "",
    ) -> None:
        """Register a phase with its tool constraints."""
        self._phases[phase] = PhaseDef(
            phase=phase,
            allowed_tools=frozenset(allowed_tools) if allowed_tools is not None else None,
            required_tools=frozenset(required_tools or set()),
            max_tool_calls=max_tool_calls,
            description=description,
        )

    def get_phase_def(self, phase: WorkflowPhase) -> PhaseDef | None:
        """Get the definition for a phase."""
        return self._phases.get(phase)

    # --- Transition management ------------------------------------------------

    def add_transition(
        self,
        name: str,
        from_phase: WorkflowPhase,
        to_phase: WorkflowPhase,
        *,
        description: str = "",
        guard: GuardFn | None = None,
    ) -> None:
        """Register a transition between phases, optionally with a guard."""
        t = Transition(
            name=name,
            from_phase=from_phase,
            to_phase=to_phase,
            description=description,
        )
        if from_phase not in self._transitions:
            self._transitions[from_phase] = []
        self._transitions[from_phase].append(t)

        if guard is not None:
            self._guards[name] = guard

    def transition(self, name: str, context: dict[str, Any] | None = None) -> bool:
        """Attempt a named transition from the current phase.

        Returns True if the transition was successful.
        """
        ctx = context or {}
        transitions = self._transitions.get(self.current_phase, [])

        for t in transitions:
            if t.name == name:
                # Check guard if present
                guard = self._guards.get(name)
                if guard is not None and not guard(self, ctx):
                    return False

                self._phase_history.append(self.current_phase)
                self.current_phase = t.to_phase
                self._tool_call_count = 0  # reset per-phase counter
                return True

        return False

    def can_transition(self, name: str, context: dict[str, Any] | None = None) -> bool:
        """Check whether a named transition is possible from the current phase."""
        ctx = context or {}
        transitions = self._transitions.get(self.current_phase, [])
        for t in transitions:
            if t.name == name:
                guard = self._guards.get(name)
                if guard is not None:
                    return guard(self, ctx)
                return True
        return False

    def available_transitions(self) -> list[Transition]:
        """List all transitions available from the current phase."""
        return list(self._transitions.get(self.current_phase, []))

    def transition_names(self) -> list[str]:
        """List names of available transitions."""
        return [t.name for t in self.available_transitions()]

    # --- Tool gating ----------------------------------------------------------

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if a tool is allowed in the current phase."""
        phase_def = self._phases.get(self.current_phase)
        if phase_def is None:
            return False

        # None = no explicit allow-list = everything allowed
        if phase_def.allowed_tools is None:
            return True

        # Empty frozenset = explicit deny-all
        if not phase_def.allowed_tools:
            return False

        # Check max tool calls
        if phase_def.max_tool_calls > 0 and self._tool_call_count >= phase_def.max_tool_calls:
            return False

        return tool_name in phase_def.allowed_tools

    def record_tool_call(self, tool_name: str) -> bool:
        """Record a tool call. Returns True if the call was within limits."""
        if not self.can_use_tool(tool_name):
            return False
        self._tool_call_count += 1
        self._total_tool_calls += 1
        return True

    def allowed_tools(self) -> list[str]:
        """List all tools allowed in the current phase."""
        phase_def = self._phases.get(self.current_phase)
        if phase_def is None:
            return []
        if phase_def.allowed_tools is None:
            return []  # None = no explicit list = all tools
        if not phase_def.allowed_tools:
            return []  # empty = nothing allowed
        if phase_def.max_tool_calls > 0 and self._tool_call_count >= phase_def.max_tool_calls:
            return []
        return sorted(phase_def.allowed_tools)

    def required_tools(self) -> list[str]:
        """List required tools for the current phase."""
        phase_def = self._phases.get(self.current_phase)
        if phase_def is None:
            return []
        return sorted(phase_def.required_tools)

    def missing_required_tools(self) -> list[str]:
        """Required tools that haven't been called yet this phase."""
        phase_def = self._phases.get(self.current_phase)
        if phase_def is None:
            return []
        return sorted(phase_def.required_tools)  # tracking would need per-tool state

    # --- Lifecycle ------------------------------------------------------------

    def start(self, phase: WorkflowPhase) -> None:
        """Set the initial phase."""
        self.current_phase = phase
        self._phase_history.clear()
        self._tool_call_count = 0
        self._total_tool_calls = 0

    def reset(self) -> None:
        """Reset to INIT state."""
        self.start(WorkflowPhase.INIT)

    # --- Introspection --------------------------------------------------------

    @property
    def phase_count(self) -> int:
        return len(self._phases)

    @property
    def transition_count(self) -> int:
        return sum(len(ts) for ts in self._transitions.values())

    @property
    def phase_history(self) -> list[WorkflowPhase]:
        return list(self._phase_history)

    @property
    def tool_calls_this_phase(self) -> int:
        return self._tool_call_count

    @property
    def total_tool_calls(self) -> int:
        return self._total_tool_calls

    def phase_tool_summary(self) -> dict[str, Any]:
        """Summary of tools available per phase."""
        return {
            "current_phase": self.current_phase.value,
            "allowed_tools": self.allowed_tools(),
            "required_tools": self.required_tools(),
            "tool_calls_this_phase": self._tool_call_count,
            "available_transitions": self.transition_names(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_phase": self.current_phase.value,
            "phase_history": [p.value for p in self._phase_history],
            "phases": {
                p.value: {
                    "allowed_tools": sorted(pdef.allowed_tools),
                    "required_tools": sorted(pdef.required_tools),
                    "max_tool_calls": pdef.max_tool_calls,
                }
                for p, pdef in self._phases.items()
            },
            "transitions": {
                p.value: [
                    {"name": t.name, "to": t.to_phase.value}
                    for t in trans
                ]
                for p, trans in self._transitions.items()
            },
        }


# ---------------------------------------------------------------------------
# Pre-built State Machines
# ---------------------------------------------------------------------------


def build_standard_workflow() -> PhaseStateMachine:
    """Build a standard agent workflow state machine.

    Phases: INIT → PLANNING → RESEARCH → EXECUTION → VERIFICATION → REVIEW → COMPLETE
    """
    sm = PhaseStateMachine()

    # Define phases with tool constraints
    sm.add_phase(
        WorkflowPhase.INIT,
        allowed_tools={"read", "list_files"},
        description="Initial setup — minimal tools",
    )

    sm.add_phase(
        WorkflowPhase.PLANNING,
        allowed_tools={"read", "search", "list_files", "grep"},
        description="Planning phase — read-only tools",
    )

    sm.add_phase(
        WorkflowPhase.RESEARCH,
        allowed_tools={"read", "search", "web_search", "web_fetch", "grep", "list_files"},
        description="Research phase — read + search tools",
    )

    sm.add_phase(
        WorkflowPhase.EXECUTION,
        allowed_tools={"read", "write", "edit", "bash", "search", "grep", "list_files"},
        description="Execution phase — read + write + shell tools",
    )

    sm.add_phase(
        WorkflowPhase.VERIFICATION,
        allowed_tools={"read", "bash", "search", "grep", "list_files"},
        required_tools={"read"},
        description="Verification phase — read-only + test execution",
    )

    sm.add_phase(
        WorkflowPhase.REVIEW,
        allowed_tools={"read", "search", "grep", "list_files"},
        description="Review phase — read-only review tools",
    )

    sm.add_phase(
        WorkflowPhase.COMPLETE,
        allowed_tools=set(),  # no tools in complete phase
        description="Workflow complete",
    )

    sm.add_phase(
        WorkflowPhase.ERROR,
        allowed_tools={"read", "list_files"},
        description="Error recovery — minimal tools",
    )

    # Define transitions
    sm.add_transition("begin_planning", WorkflowPhase.INIT, WorkflowPhase.PLANNING)
    sm.add_transition("begin_research", WorkflowPhase.PLANNING, WorkflowPhase.RESEARCH)
    sm.add_transition("begin_execution", WorkflowPhase.RESEARCH, WorkflowPhase.EXECUTION)
    sm.add_transition("begin_execution", WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION)
    sm.add_transition("begin_verification", WorkflowPhase.EXECUTION, WorkflowPhase.VERIFICATION)
    sm.add_transition("begin_review", WorkflowPhase.VERIFICATION, WorkflowPhase.REVIEW)
    sm.add_transition("complete", WorkflowPhase.REVIEW, WorkflowPhase.COMPLETE)
    sm.add_transition("complete", WorkflowPhase.VERIFICATION, WorkflowPhase.COMPLETE)
    sm.add_transition("back_to_planning", WorkflowPhase.RESEARCH, WorkflowPhase.PLANNING)
    sm.add_transition("back_to_execution", WorkflowPhase.VERIFICATION, WorkflowPhase.EXECUTION)
    sm.add_transition("to_error", WorkflowPhase.EXECUTION, WorkflowPhase.ERROR)
    sm.add_transition("to_error", WorkflowPhase.VERIFICATION, WorkflowPhase.ERROR)
    sm.add_transition("recover", WorkflowPhase.ERROR, WorkflowPhase.PLANNING)

    return sm


def build_readonly_workflow() -> PhaseStateMachine:
    """Build a read-only workflow (no write/bash tools at any phase)."""
    sm = PhaseStateMachine()

    sm.add_phase(
        WorkflowPhase.PLANNING,
        allowed_tools={"read", "search", "grep", "list_files"},
    )
    sm.add_phase(
        WorkflowPhase.EXECUTION,
        allowed_tools={"read", "search", "grep", "list_files", "web_search", "web_fetch"},
    )
    sm.add_phase(
        WorkflowPhase.VERIFICATION,
        allowed_tools={"read", "grep", "list_files"},
    )

    sm.add_transition("plan", WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION)
    sm.add_transition("verify", WorkflowPhase.EXECUTION, WorkflowPhase.VERIFICATION)
    sm.add_transition("replan", WorkflowPhase.VERIFICATION, WorkflowPhase.PLANNING)
    sm.add_transition("complete", WorkflowPhase.VERIFICATION, WorkflowPhase.COMPLETE)

    return sm


__all__ = [
    "PhaseDef",
    "PhaseStateMachine",
    "Transition",
    "WorkflowPhase",
    "build_readonly_workflow",
    "build_standard_workflow",
]
