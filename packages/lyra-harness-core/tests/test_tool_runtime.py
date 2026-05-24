"""Tests for harness_core.tool_runtime — ToolEngine + retry policies."""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from harness_core.cost import CostTracker, PricingTable
from harness_core.evals import BudgetController
from harness_core.messages import ToolCall
from harness_core.provenance import WitnessLattice
from harness_core.replay import ReplayEventKind, TraceBuilder
from harness_core.tool_runtime import (
    ExponentialBackoff,
    NoRetry,
    ToolEngine,
    ToolExecution,
)
from harness_core.tools import Tool, ToolError, ToolRegistry
from harness_core.verifier import (
    Severity,
    StubPolicyVerifier,
    VerifierAxis,
    VerifierComposer,
)


# --- Stub tools -------------------------------------------------------


class _EchoTool(Tool):
    name = "echo"
    description = "echo back the message"

    class ArgsModel(BaseModel):
        msg: str

    def run(self, args: Any) -> str:
        return f"echo: {args.msg}"


class _FlakyTool(Tool):
    """Fails N times with a transient error, then succeeds."""

    name = "flaky"
    description = "fail-then-succeed"

    def __init__(self, fail_n: int, error: str = "upstream timeout"):
        self.fail_n = fail_n
        self.error = error
        self.calls = 0

    class ArgsModel(BaseModel):
        x: int = 0

    def run(self, args: Any) -> str:
        self.calls += 1
        if self.calls <= self.fail_n:
            raise ToolError(self.error)
        return f"ok after {self.calls} attempts"


class _DeterministicFailTool(Tool):
    name = "broken"
    description = "always fails with a non-retriable error"

    class ArgsModel(BaseModel):
        pass

    def run(self, args: Any) -> str:
        raise ToolError("invalid argument: payload too large")


# --- Helpers ----------------------------------------------------------


def _make_registry(*tools: Tool) -> ToolRegistry:
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


# --- Bare-engine tests ------------------------------------------------


class TestBareEngine:
    """Engine with only a registry — pass-through behaviour."""

    def test_successful_call(self):
        engine = ToolEngine(registry=_make_registry(_EchoTool()))
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "hi"}))
        assert isinstance(result, ToolExecution)
        assert result.succeeded
        assert not result.blocked
        assert "echo: hi" in result.result.content
        assert result.n_attempts == 1
        assert result.cost_usd == 0.0
        assert result.witness_id == ""  # no lattice wired

    def test_unknown_tool(self):
        engine = ToolEngine(registry=ToolRegistry())
        result = engine.execute(ToolCall(id="c1", name="missing", args={}))
        assert not result.succeeded
        assert result.result.is_error

    def test_returns_tool_error(self):
        engine = ToolEngine(registry=_make_registry(_DeterministicFailTool()))
        result = engine.execute(ToolCall(id="c1", name="broken", args={}))
        assert not result.succeeded
        assert result.result.is_error
        assert "invalid argument" in result.result.content


# --- Verifier integration --------------------------------------------


class TestVerifierGate:
    def test_verifier_passes_then_runs(self):
        composer = VerifierComposer(
            verifiers=[StubPolicyVerifier(forbidden_ops=frozenset({"delete"}))],
        )
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
        )
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "ok"}))
        assert result.succeeded
        assert result.verdict is not None
        assert result.verdict.passed
        assert not result.blocked_by_verdict

    def test_verifier_blocks_critical_op(self):
        composer = VerifierComposer(
            verifiers=[StubPolicyVerifier(forbidden_ops=frozenset({"echo"}))],
        )
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
        )
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        assert result.blocked_by_verdict
        assert result.blocked
        assert not result.succeeded
        assert result.result.is_error
        assert "blocked by verifier" in result.result.content
        assert result.n_attempts == 1  # never dispatched

    def test_verifier_action_includes_op_and_args(self):
        """The action dict the verifier sees uses tool name as op, plus args."""

        seen: dict = {}

        class _Capture:
            axis = VerifierAxis.CUSTOM

            def verify(self, *, action):
                seen.update(action)
                from harness_core.verifier import AxisVerdict
                return AxisVerdict(axis=self.axis, passed=True, severity=Severity.INFO)

        composer = VerifierComposer(verifiers=[_Capture()])
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
        )
        engine.execute(ToolCall(id="c1", name="echo", args={"msg": "z"}))
        assert seen["op"] == "echo"
        assert seen["args"] == {"msg": "z"}


# --- Budget integration -----------------------------------------------


class TestBudgetGate:
    def test_within_budget_runs(self):
        budget = BudgetController(budget_tokens=1000)
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            budget=budget,
        )
        result = engine.execute(
            ToolCall(id="c1", name="echo", args={"msg": "x"}),
            estimated_tokens=100,
        )
        assert result.succeeded
        assert budget.consumed_tokens == 100

    def test_over_budget_blocks(self):
        budget = BudgetController(budget_tokens=50)
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            budget=budget,
        )
        result = engine.execute(
            ToolCall(id="c1", name="echo", args={"msg": "x"}),
            estimated_tokens=100,
        )
        assert result.blocked_by_budget
        assert "blocked by budget" in result.result.content
        assert result.n_attempts == 1
        # Budget was *not* consumed because reservation failed.
        assert budget.consumed_tokens == 0

    def test_zero_estimated_tokens_skips_check(self):
        budget = BudgetController(budget_tokens=0)
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            budget=budget,
        )
        # Even though budget is 0, estimated_tokens=0 → no check.
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        assert result.succeeded


# --- Cost tracking ----------------------------------------------------


class TestCostTracking:
    def test_records_cost_with_explicit_amount(self):
        tracker = CostTracker()
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            cost_tracker=tracker,
            project="orion-code",
            user_id="alice",
        )
        result = engine.execute(
            ToolCall(id="c1", name="echo", args={"msg": "x"}),
            cost_usd=0.05,
        )
        assert result.cost_usd == 0.05
        entries = tracker.all_entries()
        assert len(entries) == 1
        assert entries[0].cost_usd == 0.05
        assert entries[0].operation == "tool:echo"
        assert entries[0].project == "orion-code"
        assert entries[0].user_id == "alice"

    def test_records_cost_from_pricing_table(self):
        pricing = PricingTable(prices={
            "tool:echo": {"input_per_M": 1.0, "output_per_M": 0.0},
        })
        tracker = CostTracker(pricing=pricing)
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            cost_tracker=tracker,
        )
        result = engine.execute(
            ToolCall(id="c1", name="echo", args={"msg": "x"}),
            estimated_tokens=1_000_000,
        )
        # 1M input tokens × $1.00 / M = $1.00.
        assert result.cost_usd == pytest.approx(1.0)

    def test_no_tracker_no_record(self):
        engine = ToolEngine(registry=_make_registry(_EchoTool()))
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        assert result.cost_usd == 0.0


# --- Retry policy -----------------------------------------------------


class TestRetryPolicy:
    def test_no_retry_default(self):
        flaky = _FlakyTool(fail_n=2)
        engine = ToolEngine(registry=_make_registry(flaky))
        result = engine.execute(ToolCall(id="c1", name="flaky", args={}))
        assert not result.succeeded
        assert result.n_attempts == 1
        assert flaky.calls == 1
        assert result.retried_errors == ()

    def test_exponential_backoff_recovers(self):
        flaky = _FlakyTool(fail_n=2, error="upstream timeout")
        engine = ToolEngine(
            registry=_make_registry(flaky),
            retry_policy=ExponentialBackoff(max_attempts=5, base_delay=0.0),
            sleep_fn=lambda _: None,  # no real sleeps
        )
        result = engine.execute(ToolCall(id="c1", name="flaky", args={}))
        assert result.succeeded
        assert result.n_attempts == 3  # 2 fails + 1 success
        assert len(result.retried_errors) == 2
        assert "timeout" in result.retried_errors[0].lower()

    def test_exponential_backoff_gives_up(self):
        flaky = _FlakyTool(fail_n=10, error="upstream timeout")
        engine = ToolEngine(
            registry=_make_registry(flaky),
            retry_policy=ExponentialBackoff(max_attempts=3, base_delay=0.0),
            sleep_fn=lambda _: None,
        )
        result = engine.execute(ToolCall(id="c1", name="flaky", args={}))
        assert not result.succeeded
        assert result.n_attempts == 3

    def test_non_retriable_error_no_retry(self):
        engine = ToolEngine(
            registry=_make_registry(_DeterministicFailTool()),
            retry_policy=ExponentialBackoff(max_attempts=5, base_delay=0.0),
            sleep_fn=lambda _: None,
        )
        result = engine.execute(ToolCall(id="c1", name="broken", args={}))
        assert not result.succeeded
        assert result.n_attempts == 1  # "invalid argument" not retriable
        assert result.retried_errors == ()

    def test_sleep_is_called_with_increasing_delays(self):
        delays: list[float] = []
        flaky = _FlakyTool(fail_n=10, error="rate limit exceeded")
        engine = ToolEngine(
            registry=_make_registry(flaky),
            retry_policy=ExponentialBackoff(
                max_attempts=4, base_delay=0.1, multiplier=2.0,
            ),
            sleep_fn=delays.append,
        )
        engine.execute(ToolCall(id="c1", name="flaky", args={}))
        # 4 attempts → 3 sleeps after attempts 1, 2, 3.
        assert len(delays) == 3
        assert delays[0] == pytest.approx(0.1)
        assert delays[1] == pytest.approx(0.2)
        assert delays[2] == pytest.approx(0.4)


class TestRetryPolicyDirect:
    def test_no_retry_never_retries(self):
        p = NoRetry()
        assert p.max_attempts == 1
        assert p.should_retry(attempt=1, error="anything") is False
        assert p.delay_seconds(attempt=1) == 0.0

    def test_exponential_backoff_substring_match(self):
        p = ExponentialBackoff(max_attempts=3)
        assert p.should_retry(attempt=1, error="UPSTREAM TIMEOUT")  # case-insensitive
        assert p.should_retry(attempt=1, error="HTTP 503 backend")
        assert not p.should_retry(attempt=1, error="schema validation failed")

    def test_exponential_backoff_attempt_cap(self):
        p = ExponentialBackoff(max_attempts=3)
        assert p.should_retry(attempt=2, error="timeout")
        assert not p.should_retry(attempt=3, error="timeout")  # at cap


# --- Provenance + Trace audit ----------------------------------------


class TestAudit:
    def test_witness_records_verdict_and_result(self):
        lattice = WitnessLattice()
        composer = VerifierComposer(verifiers=[StubPolicyVerifier()])
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
            lattice=lattice,
            agent_id="orion-agent",
        )
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        assert result.witness_id != ""
        assert result.verdict_witness_id != ""
        assert result.witness_id != result.verdict_witness_id

        # Tool-result witness should cite the verdict witness as a parent.
        tr = lattice.ledger.get(result.witness_id)
        assert tr is not None
        assert result.verdict_witness_id in tr.parent_witnesses

    def test_no_lattice_no_witnesses(self):
        engine = ToolEngine(registry=_make_registry(_EchoTool()))
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        assert result.witness_id == ""
        assert result.verdict_witness_id == ""

    def test_trace_records_verdict_and_call(self):
        trace_builder = TraceBuilder(trace_id="t1")
        composer = VerifierComposer(verifiers=[StubPolicyVerifier()])
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
            trace=trace_builder,
        )
        engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        trace = trace_builder.build()
        kinds = [e.kind for e in trace.events]
        assert ReplayEventKind.VERIFIER_VERDICT in kinds
        assert ReplayEventKind.TOOL_CALL in kinds

    def test_blocked_call_still_records_witness(self):
        lattice = WitnessLattice()
        composer = VerifierComposer(
            verifiers=[StubPolicyVerifier(forbidden_ops=frozenset({"echo"}))],
        )
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
            lattice=lattice,
        )
        result = engine.execute(ToolCall(id="c1", name="echo", args={"msg": "x"}))
        assert result.blocked_by_verdict
        # Both verdict + tool-result witnesses recorded for the audit trail.
        assert result.verdict_witness_id != ""
        assert result.witness_id != ""

    def test_parent_witnesses_chain_through(self):
        lattice = WitnessLattice()
        # Pre-existing context witness — e.g., the agent decision that led here.
        decision = lattice.record_decision(
            agent_id="planner",
            action="invoke_echo",
        )
        composer = VerifierComposer(verifiers=[StubPolicyVerifier()])
        engine = ToolEngine(
            registry=_make_registry(_EchoTool()),
            verifier=composer,
            lattice=lattice,
        )
        result = engine.execute(
            ToolCall(id="c1", name="echo", args={"msg": "x"}),
            parent_witnesses=(decision.witness_id,),
        )
        # The verdict cites the upstream decision.
        verdict_w = lattice.ledger.get(result.verdict_witness_id)
        assert decision.witness_id in verdict_w.parent_witnesses
        # The tool-result cites both the upstream decision + the verdict.
        tr = lattice.ledger.get(result.witness_id)
        assert decision.witness_id in tr.parent_witnesses
        assert result.verdict_witness_id in tr.parent_witnesses


# --- End-to-end composition ------------------------------------------


class TestEndToEndComposition:
    """All hooks wired together — Orion-Code-style guarded dispatch."""

    def test_full_stack(self):
        registry = _make_registry(_EchoTool())
        composer = VerifierComposer(verifiers=[StubPolicyVerifier()])
        budget = BudgetController(budget_tokens=10_000)
        tracker = CostTracker()
        lattice = WitnessLattice()
        trace_builder = TraceBuilder(trace_id="orion-incident-2026-05-09")

        engine = ToolEngine(
            registry=registry,
            verifier=composer,
            budget=budget,
            cost_tracker=tracker,
            lattice=lattice,
            trace=trace_builder,
            project="orion-code",
            user_id="alice",
            agent_id="research-agent",
        )

        for i in range(3):
            engine.execute(
                ToolCall(id=f"c{i}", name="echo", args={"msg": f"call-{i}"}),
                estimated_tokens=100,
                cost_usd=0.01,
            )

        # 3 calls × verdict + tool_result = 6 witnesses.
        assert lattice.ledger.stats()["total"] == 6
        # 3 verdict events + 3 tool_call events = 6 trace events.
        trace = trace_builder.build()
        assert len(trace.events) == 6
        # 3 calls × 100 tokens = 300 consumed.
        assert budget.consumed_tokens == 300
        # 3 calls × $0.01 = $0.03.
        assert tracker.total(project="orion-code") == pytest.approx(0.03)
        assert len(tracker.all_entries()) == 3
