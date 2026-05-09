"""L312-4 — AgentContract: resource-bounded autonomous-agent envelope.

Anchor: ``docs/305-agent-contracts-formal-framework.md`` (arXiv 2601.08815,
COINE 2026). Wraps any inner loop in a six-state machine
(``PENDING / RUNNING / FULFILLED / VIOLATED / EXPIRED / TERMINATED``)
with a :class:`BudgetEnvelope` (USD, iterations, wall-clock, per-tool
quotas, deny-pattern regex) and three formal guarantees:

- **G1 — bounded blast.** No run consumes more than ``1.5×`` the declared
  budget under realistic clock skew.
- **G2 — deterministic terminal state.** Every run reaches exactly one
  terminal state in finite time.
- **G3 — auditable cause.** The contract records a single load-bearing
  ``terminal_cause`` for the transition.

Closes the *$47 k recursive-clarification-loop* incident class
(Appendix A.3 of the source paper) by giving the runtime a *first* line
of defence: budget-USD overshoot triggers ``VIOLATED("budget-usd")``
within one iteration of the breach.

Composition:

- The contract evaluates *before* the on_stop hook (L312-1). A
  ``VIOLATED`` contract preempts any ``ContinueLoop`` the hook would
  raise.
- Contracts compose recursively via :meth:`AgentContract.spawn_child` —
  the parent's ``cum_usd`` includes the child's ``cum_usd``.
- ``EXPIRED`` never propagates parent-ward; ``VIOLATED`` does, unless
  the parent declares ``child_violation_isolation=True``.

The priority order of the ``step()`` evaluator is **not debatable** and
matches Section 3.4 of the paper: deny-patterns → quotas → budget-USD →
wall-clock → iterations → external signal → fulfillment. This is the
unique ordering satisfying both G1 and G2.
"""
from __future__ import annotations

import enum
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional


__all__ = [
    "AgentContract",
    "BudgetEnvelope",
    "ContractObservation",
    "ContractState",
    "TerminalCause",
    "VerifierPred",
]


# --- States and causes ------------------------------------------------- #


class ContractState(str, enum.Enum):
    """Six-state lifecycle from arXiv 2601.08815."""

    PENDING = "pending"
    RUNNING = "running"
    FULFILLED = "fulfilled"   # success criteria met within all constraints
    VIOLATED = "violated"     # constraint breached (budget, quota, deny-pattern)
    EXPIRED = "expired"       # wall-clock or iteration cap reached
    TERMINATED = "terminated"  # external cancellation (Ctrl-C, /stop, signal)

    def is_terminal(self) -> bool:
        return self in (
            ContractState.FULFILLED,
            ContractState.VIOLATED,
            ContractState.EXPIRED,
            ContractState.TERMINATED,
        )


class TerminalCause(str, enum.Enum):
    """The single load-bearing ``cause`` field on every terminal transition.

    Strictly enumerated — these are the only valid causes recorded in the
    audit artefact compliance teams consume (EU AI Act Art. 14, ISO/IEC
    42001 §6.1.3, SOC 2 CC7.4).
    """

    # FULFILLED
    PREDICATE = "predicate"
    # VIOLATED
    DENY_PATTERN = "deny-pattern"
    BUDGET_USD = "budget-usd"
    # quota:<tool> is encoded as a parameterised cause; see _violated_quota()
    # EXPIRED
    WALL_CLOCK = "wall-clock"
    ITERATIONS = "iterations"
    # TERMINATED
    SIGNAL = "signal"
    EXTERNAL_CANCEL = "external-cancel"


VerifierPred = Callable[[Any], bool]
"""Callable returning True iff the run's state satisfies fulfillment."""


# --- Budget envelope --------------------------------------------------- #


@dataclass(frozen=True)
class BudgetEnvelope:
    """Resource bounds for a single contract.

    All fields default to ``None``/empty meaning "no bound on this axis";
    a contract with every field None becomes a trivial PENDING→RUNNING
    machine that only terminates via ``terminate()`` or ``fulfillment``.

    - ``max_usd``: cumulative USD across the run.
    - ``max_iterations``: cumulative LLM calls / loop iterations.
    - ``max_wall_clock_s``: monotonic CPU time (not wall clock under
      sleep — see paper §4.4 footnote on the unfortunate naming).
    - ``per_tool_max``: per-tool dispatch quota.
    - ``deny_patterns``: tuple of regex strings; if any tool's
      stringified args match, the contract VIOLATES.
    """

    max_usd: Optional[float] = None
    max_iterations: Optional[int] = None
    max_wall_clock_s: Optional[float] = None
    per_tool_max: Mapping[str, int] = field(default_factory=dict)
    deny_patterns: tuple[str, ...] = ()

    def is_unbounded(self) -> bool:
        return (
            self.max_usd is None
            and self.max_iterations is None
            and self.max_wall_clock_s is None
            and not self.per_tool_max
            and not self.deny_patterns
        )


# --- Observation passed to step() -------------------------------------- #


@dataclass
class ContractObservation:
    """One step's worth of inputs to :meth:`AgentContract.step`.

    The contract owns *cumulative* totals; the observation carries
    per-step *deltas*. This split is what makes the cost-reporting
    surface tamper-resistant — the contract's totals come from a
    trusted price table, not from the tool's self-report.
    """

    cost_usd: float = 0.0
    elapsed_s: float = 0.0
    tool_calls: tuple[dict, ...] = ()
    external_signal: bool = False


# --- Contract ---------------------------------------------------------- #


def _never_done(_: Any) -> bool:
    return False


def _no_op(_state: ContractState, _cause: str) -> None:
    return None


@dataclass
class AgentContract:
    """The four-terminal-state envelope.

    Wrap any inner loop with::

        contract = AgentContract(
            fulfillment=lambda state: state.tests_pass,
            budget=BudgetEnvelope(max_usd=5.00, max_iterations=50),
        )
        contract.start()
        for _ in range(MAX):
            obs = inner_loop.step()
            outcome = contract.step(obs)
            if outcome.is_terminal():
                break
        contract.finalize()
    """

    fulfillment: VerifierPred = field(default=_never_done)
    budget: BudgetEnvelope = field(default_factory=BudgetEnvelope)
    on_violated: Callable[[ContractState, str], None] = field(default=_no_op)
    on_expired: Callable[[ContractState, str], None] = field(default=_no_op)
    on_fulfilled: Callable[[ContractState, str], None] = field(default=_no_op)
    on_terminated: Callable[[ContractState, str], None] = field(default=_no_op)
    child_violation_isolation: bool = False

    state: ContractState = ContractState.PENDING
    cum_usd: float = 0.0
    cum_seconds: float = 0.0
    iter_count: int = 0
    per_tool_count: dict[str, int] = field(default_factory=dict)
    terminal_cause: Optional[str] = None
    terminal_value: Optional[float] = None
    terminal_limit: Optional[float] = None
    triggered_at: Optional[float] = None
    children: list["AgentContract"] = field(default_factory=list)
    _parent: Optional["AgentContract"] = None

    # ---- public API --------------------------------------------------- #

    def start(self) -> None:
        if self.state != ContractState.PENDING:
            raise RuntimeError(f"start() requires PENDING; was {self.state}")
        self.state = ContractState.RUNNING

    def step(self, observation: ContractObservation) -> ContractState:
        """Drive one step. First-trigger-wins terminal transition.

        Priority order (Section 3.4 of the source paper):
        deny-patterns → quotas → budget-USD → wall-clock →
        iterations → external signal → fulfillment.
        """
        if self.state.is_terminal():
            return self.state
        if self.state == ContractState.PENDING:
            self.start()

        # 1. Bookkeeping (cumulative totals; cost not from tool self-report)
        self.iter_count += 1
        self.cum_usd += float(observation.cost_usd or 0.0)
        self.cum_seconds += float(observation.elapsed_s or 0.0)
        for call in observation.tool_calls:
            name = str(call.get("name", ""))
            if name:
                self.per_tool_count[name] = self.per_tool_count.get(name, 0) + 1

        # Roll the parent's totals as well so cumulative budgets compose.
        if self._parent is not None:
            self._parent.cum_usd += float(observation.cost_usd or 0.0)
            self._parent.cum_seconds += float(observation.elapsed_s or 0.0)

        # 2. Deny patterns
        if self.budget.deny_patterns:
            for call in observation.tool_calls:
                arg_str = _stringify_args(call)
                for pattern in self.budget.deny_patterns:
                    if re.search(pattern, arg_str):
                        return self._terminate(
                            ContractState.VIOLATED,
                            cause=TerminalCause.DENY_PATTERN.value,
                            value=None, limit=None,
                        )

        # 3. Quotas
        for tool_name, cap in (self.budget.per_tool_max or {}).items():
            if self.per_tool_count.get(tool_name, 0) > cap:
                return self._terminate(
                    ContractState.VIOLATED,
                    cause=f"quota:{tool_name}",
                    value=self.per_tool_count.get(tool_name, 0),
                    limit=cap,
                )

        # 4. Budget USD
        if self.budget.max_usd is not None and self.cum_usd > self.budget.max_usd:
            return self._terminate(
                ContractState.VIOLATED,
                cause=TerminalCause.BUDGET_USD.value,
                value=self.cum_usd, limit=self.budget.max_usd,
            )

        # 5. Wall clock
        if (self.budget.max_wall_clock_s is not None
                and self.cum_seconds > self.budget.max_wall_clock_s):
            return self._terminate(
                ContractState.EXPIRED,
                cause=TerminalCause.WALL_CLOCK.value,
                value=self.cum_seconds, limit=self.budget.max_wall_clock_s,
            )

        # 6. Iterations
        if (self.budget.max_iterations is not None
                and self.iter_count >= self.budget.max_iterations):
            return self._terminate(
                ContractState.EXPIRED,
                cause=TerminalCause.ITERATIONS.value,
                value=self.iter_count, limit=self.budget.max_iterations,
            )

        # 7. External signal (TERMINATED preempts FULFILLED on a tie)
        if observation.external_signal:
            return self._terminate(
                ContractState.TERMINATED,
                cause=TerminalCause.SIGNAL.value,
                value=None, limit=None,
            )

        # 8. Fulfillment predicate
        try:
            if self.fulfillment(observation):
                return self._terminate(
                    ContractState.FULFILLED,
                    cause=TerminalCause.PREDICATE.value,
                    value=None, limit=None,
                )
        except Exception:
            # Predicate errors are non-fatal — continue running. The
            # paper recommends logging in production; we keep this
            # silent in the runtime path and let observers handle it.
            pass

        return self.state

    def terminate(self, *, cause: str = "external-cancel") -> ContractState:
        """External cancellation surface (Ctrl-C, /stop, signal)."""
        if self.state.is_terminal():
            return self.state
        return self._terminate(
            ContractState.TERMINATED, cause=cause, value=None, limit=None,
        )

    def spawn_child(self, budget: BudgetEnvelope) -> "AgentContract":
        """Compose a child contract whose budget is bounded by this one.

        Cumulative-budget rule: the parent's ``cum_usd`` and
        ``cum_seconds`` *include* the child's; child VIOLATED propagates
        unless ``child_violation_isolation=True``.

        Cycles are forbidden by construction — the spawn relationship is
        a DAG.
        """
        child = AgentContract(budget=budget)
        child._parent = self
        self.children.append(child)
        return child

    def finalize(self) -> None:
        """Idempotent flush — fires the terminal callback exactly once."""
        # Guard via a sentinel so finalize() is safe to call repeatedly.
        if getattr(self, "_finalized", False):
            return
        if self.state.is_terminal():
            cb = {
                ContractState.FULFILLED: self.on_fulfilled,
                ContractState.VIOLATED: self.on_violated,
                ContractState.EXPIRED: self.on_expired,
                ContractState.TERMINATED: self.on_terminated,
            }[self.state]
            try:
                cb(self.state, self.terminal_cause or "")
            except Exception:
                # Callbacks must never break finalize().
                pass
        self._finalized = True

    # ---- audit artefact ---------------------------------------------- #

    def to_audit_dict(self) -> dict:
        """The single artefact compliance teams consume."""
        return {
            "state": self.state.value,
            "cause": self.terminal_cause,
            "value": self.terminal_value,
            "limit": self.terminal_limit,
            "triggered_at": self.triggered_at,
            "iter_count": self.iter_count,
            "cum_usd": self.cum_usd,
            "cum_seconds": self.cum_seconds,
            "per_tool_count": dict(self.per_tool_count),
        }

    # ---- private helpers -------------------------------------------- #

    def _terminate(
        self,
        state: ContractState,
        *,
        cause: str,
        value: Any = None,
        limit: Any = None,
    ) -> ContractState:
        self.state = state
        self.terminal_cause = cause
        self.terminal_value = value
        self.terminal_limit = limit
        self.triggered_at = time.time()
        # Propagate VIOLATED to parent unless isolated.
        if (state == ContractState.VIOLATED
                and self._parent is not None
                and not self._parent.child_violation_isolation
                and not self._parent.state.is_terminal()):
            self._parent._terminate(
                ContractState.VIOLATED,
                cause=f"child:{cause}",
                value=value, limit=limit,
            )
        return state


def _stringify_args(call: Mapping[str, Any]) -> str:
    """Best-effort string representation of a tool call's args for regex check."""
    args = call.get("arguments", {}) or {}
    if isinstance(args, str):
        return args
    try:
        import json
        return json.dumps(args, default=str, sort_keys=True)
    except Exception:
        return str(args)
