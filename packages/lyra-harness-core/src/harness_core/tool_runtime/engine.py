"""ToolEngine — guarded tool execution composing verifier + budget + cost + audit.

The engine wraps :class:`ToolRegistry` with optional pre-call gates and
post-call recording:

    1. **Verifier composer** (pre-call gate): if wired, builds an action dict
       from the tool call + caller-supplied ``action`` and runs the composer.
       A blocking verdict prevents the call.
    2. **Budget controller** (pre-call gate): reserves ``estimated_tokens``
       before the call. Reservation failure prevents the call.
    3. **Tool dispatch** with retry: ``ToolRegistry.execute`` is invoked; on
       error, the retry policy decides whether to try again.
    4. **Cost tracker** (post-call): records the call with computed or
       supplied ``cost_usd``.
    5. **Witness lattice** (post-call): emits VERIFIER_VERDICT (if a verdict
       was produced) and TOOL_RESULT witnesses, linking the latter to the
       former + caller-supplied ``parent_witnesses``.
    6. **Trace builder** (post-call): emits VERIFIER_VERDICT + TOOL_CALL
       events with matching event IDs.

Returns a :class:`ToolExecution` record capturing all of the above for audit.
All hooks are optional — a ``ToolEngine`` with only ``registry`` set behaves
like a thin pass-through over ``ToolRegistry.execute``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..cost import CostTracker
from ..evals import BudgetController, BudgetExhausted
from ..messages import ToolCall, ToolResult
from ..provenance import WitnessLattice
from ..replay import ReplayEventKind, TraceBuilder
from ..tools import ToolRegistry
from ..verifier import VerifierComposer
from .retry import NoRetry
from .types import RetryPolicy, ToolExecution


@dataclass
class ToolEngine:
    """Guarded tool dispatch hub. All hooks are optional.

    >>> from harness_core.tools import ToolRegistry
    >>> from harness_core.messages import ToolCall
    >>> engine = ToolEngine(registry=ToolRegistry())
    >>> exec = engine.execute(ToolCall(id="c1", name="missing", args={}))
    >>> exec.result.is_error
    True
    """

    registry: ToolRegistry
    verifier: Optional[VerifierComposer] = None
    budget: Optional[BudgetController] = None
    cost_tracker: Optional[CostTracker] = None
    lattice: Optional[WitnessLattice] = None
    trace: Optional[TraceBuilder] = None
    retry_policy: RetryPolicy = field(default_factory=NoRetry)
    project: str = "default"
    user_id: str = "anonymous"
    agent_id: str = "agent"
    sleep_fn: Any = field(default_factory=lambda: time.sleep)
    clock_fn: Any = field(default_factory=lambda: time.time)

    def execute(
        self,
        call: ToolCall,
        *,
        action: Optional[dict[str, Any]] = None,
        estimated_tokens: int = 0,
        cost_usd: Optional[float] = None,
        parent_witnesses: tuple[str, ...] = (),
    ) -> ToolExecution:
        """Run a guarded tool dispatch. See module docstring for the pipeline."""
        args_copy = dict(call.args)

        # 1. Verifier composer.
        verdict = None
        verdict_witness_id = ""
        if self.verifier is not None:
            verifier_action = {
                "op": call.name,
                "args": dict(call.args),
                **(action or {}),
            }
            verdict = self.verifier.verify(action=verifier_action)
            verdict_witness_id = self._record_verdict(
                verdict=verdict,
                parent_witnesses=parent_witnesses,
            )
            self._trace_verdict(
                verdict=verdict,
                event_id=verdict_witness_id,
                parent_event_ids=parent_witnesses,
            )
            if verdict.blocking:
                blocked_result = ToolResult(
                    call_id=call.id,
                    content=(
                        f"blocked by verifier: failed axes "
                        f"{[a.value for a in verdict.failed_axes()]}"
                    ),
                    is_error=True,
                )
                witness_id = self._record_tool_result(
                    call=call,
                    result=blocked_result,
                    parent_witnesses=self._link_parents(
                        parent_witnesses, verdict_witness_id,
                    ),
                )
                self._trace_tool_call(
                    call=call,
                    result=blocked_result,
                    event_id=witness_id,
                    parent_event_ids=self._link_parents(
                        parent_witnesses, verdict_witness_id,
                    ),
                )
                return ToolExecution(
                    call_id=call.id,
                    tool_name=call.name,
                    args=args_copy,
                    result=blocked_result,
                    verdict=verdict,
                    blocked_by_verdict=True,
                    witness_id=witness_id,
                    verdict_witness_id=verdict_witness_id,
                )

        # 2. Budget reservation.
        if self.budget is not None and estimated_tokens > 0:
            try:
                self.budget.consume(estimated_tokens, label=call.name)
            except BudgetExhausted as e:
                blocked_result = ToolResult(
                    call_id=call.id,
                    content=f"blocked by budget: {e}",
                    is_error=True,
                )
                witness_id = self._record_tool_result(
                    call=call,
                    result=blocked_result,
                    parent_witnesses=self._link_parents(
                        parent_witnesses, verdict_witness_id,
                    ),
                )
                self._trace_tool_call(
                    call=call,
                    result=blocked_result,
                    event_id=witness_id,
                    parent_event_ids=self._link_parents(
                        parent_witnesses, verdict_witness_id,
                    ),
                )
                return ToolExecution(
                    call_id=call.id,
                    tool_name=call.name,
                    args=args_copy,
                    result=blocked_result,
                    verdict=verdict,
                    blocked_by_budget=True,
                    witness_id=witness_id,
                    verdict_witness_id=verdict_witness_id,
                )

        # 3. Dispatch with retry.
        t_start = self.clock_fn()
        retried_errors: list[str] = []
        result: ToolResult
        attempt = 0
        while True:
            attempt += 1
            result = self.registry.execute(call)
            if not result.is_error:
                break
            if not self.retry_policy.should_retry(
                attempt=attempt, error=result.content,
            ):
                break
            retried_errors.append(result.content)
            delay = self.retry_policy.delay_seconds(attempt=attempt)
            if delay > 0:
                self.sleep_fn(delay)

        duration_ms = max(0.0, (self.clock_fn() - t_start) * 1000.0)

        # 4. Cost.
        recorded_cost = 0.0
        if self.cost_tracker is not None:
            entry = self.cost_tracker.record(
                operation=f"tool:{call.name}",
                project=self.project,
                user_id=self.user_id,
                input_tokens=estimated_tokens,
                output_tokens=0,
                cost_usd=cost_usd,
                tags=("tool_runtime",),
            )
            recorded_cost = entry.cost_usd

        # 5. Witness + 6. Trace.
        witness_id = self._record_tool_result(
            call=call,
            result=result,
            parent_witnesses=self._link_parents(
                parent_witnesses, verdict_witness_id,
            ),
        )
        self._trace_tool_call(
            call=call,
            result=result,
            event_id=witness_id,
            parent_event_ids=self._link_parents(
                parent_witnesses, verdict_witness_id,
            ),
        )

        return ToolExecution(
            call_id=call.id,
            tool_name=call.name,
            args=args_copy,
            result=result,
            verdict=verdict,
            cost_usd=recorded_cost,
            duration_ms=duration_ms,
            n_attempts=attempt,
            witness_id=witness_id,
            verdict_witness_id=verdict_witness_id,
            retried_errors=tuple(retried_errors),
        )

    # --- Audit helpers ---------------------------------------------------

    def _record_verdict(
        self,
        *,
        verdict,
        parent_witnesses: tuple[str, ...],
    ) -> str:
        if self.lattice is None:
            return ""
        w = self.lattice.record_verdict(
            verifier_name=f"{self.agent_id}:composer",
            passed=verdict.passed,
            severity=verdict.severity.value,
            axes={v.axis.value: v.passed for v in verdict.axis_verdicts},
            parent_witnesses=parent_witnesses,
        )
        return w.witness_id

    def _record_tool_result(
        self,
        *,
        call: ToolCall,
        result: ToolResult,
        parent_witnesses: tuple[str, ...],
    ) -> str:
        if self.lattice is None:
            return ""
        summary = result.content
        if len(summary) > 200:
            summary = summary[:197] + "..."
        w = self.lattice.record_tool_result(
            agent_id=self.agent_id,
            tool_name=call.name,
            args=dict(call.args),
            result_summary=summary,
            parent_witnesses=parent_witnesses,
        )
        return w.witness_id

    def _trace_verdict(
        self,
        *,
        verdict,
        event_id: str,
        parent_event_ids: tuple[str, ...],
    ) -> None:
        if self.trace is None:
            return
        eid = event_id or None
        self.trace.add_event(
            kind=ReplayEventKind.VERIFIER_VERDICT,
            issued_by=f"{self.agent_id}:composer",
            timestamp=self.clock_fn(),
            payload={
                "passed": verdict.passed,
                "blocking": verdict.blocking,
                "severity": verdict.severity.value,
                "axes": {v.axis.value: v.passed for v in verdict.axis_verdicts},
            },
            parent_event_ids=parent_event_ids,
            event_id=eid,
        )

    def _trace_tool_call(
        self,
        *,
        call: ToolCall,
        result: ToolResult,
        event_id: str,
        parent_event_ids: tuple[str, ...],
    ) -> None:
        if self.trace is None:
            return
        eid = event_id or None
        self.trace.add_event(
            kind=ReplayEventKind.TOOL_CALL,
            issued_by=self.agent_id,
            timestamp=self.clock_fn(),
            payload={
                "tool_name": call.name,
                "args": dict(call.args),
                "is_error": result.is_error,
                "content_preview": (
                    result.content[:200]
                    if len(result.content) > 200
                    else result.content
                ),
            },
            parent_event_ids=parent_event_ids,
            event_id=eid,
        )

    @staticmethod
    def _link_parents(
        external_parents: tuple[str, ...],
        verdict_id: str,
    ) -> tuple[str, ...]:
        """Append the verdict witness as a parent of the tool result, if present."""
        if verdict_id:
            return tuple(external_parents) + (verdict_id,)
        return tuple(external_parents)


__all__ = ["ToolEngine"]
