"""L312-4 — AgentContract envelope contract test.

Anchor: ``docs/305-agent-contracts-formal-framework.md``.

Eighteen cases covering:
- All four terminal states reachable.
- Priority order (deny → quota → USD → wall-clock → iter → signal → predicate).
- Parent–child composition (cumulative + propagation + isolation).
- Audit-dict shape.
- The $47k incident replay (regression test).
- G1 (bounded blast) sanity check.
"""
from __future__ import annotations

import pytest

from lyra_core.contracts import (
    AgentContract,
    BudgetEnvelope,
    ContractObservation,
    ContractState,
    TerminalCause,
)


# --- 1. Default contract starts PENDING ---------------------------------- #


def test_pending_until_start():
    c = AgentContract()
    assert c.state == ContractState.PENDING
    c.start()
    assert c.state == ContractState.RUNNING


# --- 2. FULFILLED via predicate ------------------------------------------ #


def test_fulfilled_via_predicate():
    c = AgentContract(
        fulfillment=lambda obs: True,
        budget=BudgetEnvelope(max_iterations=10),
    )
    c.start()
    out = c.step(ContractObservation(cost_usd=0.01))
    assert out == ContractState.FULFILLED
    assert c.terminal_cause == "predicate"


# --- 3. VIOLATED on budget-usd ------------------------------------------- #


def test_violated_on_budget_usd():
    c = AgentContract(budget=BudgetEnvelope(max_usd=1.00))
    c.start()
    out = c.step(ContractObservation(cost_usd=1.50))
    assert out == ContractState.VIOLATED
    assert c.terminal_cause == "budget-usd"
    assert c.terminal_value > c.terminal_limit


# --- 4. VIOLATED on deny-pattern ----------------------------------------- #


def test_violated_on_deny_pattern():
    c = AgentContract(
        budget=BudgetEnvelope(deny_patterns=(r"rm\s+-rf\s+/", r"DROP\s+TABLE")),
    )
    c.start()
    out = c.step(ContractObservation(
        tool_calls=({"name": "bash", "arguments": {"cmd": "rm -rf /"}},),
    ))
    assert out == ContractState.VIOLATED
    assert c.terminal_cause == "deny-pattern"


# --- 5. VIOLATED on per-tool quota --------------------------------------- #


def test_violated_on_quota():
    c = AgentContract(budget=BudgetEnvelope(per_tool_max={"bash": 2}))
    c.start()
    obs = ContractObservation(
        tool_calls=({"name": "bash"}, {"name": "bash"}, {"name": "bash"}),
    )
    out = c.step(obs)
    assert out == ContractState.VIOLATED
    assert c.terminal_cause == "quota:bash"


# --- 6. EXPIRED on iterations -------------------------------------------- #


def test_expired_on_iterations():
    c = AgentContract(budget=BudgetEnvelope(max_iterations=3))
    c.start()
    for _ in range(2):
        assert c.step(ContractObservation()) == ContractState.RUNNING
    out = c.step(ContractObservation())
    assert out == ContractState.EXPIRED
    assert c.terminal_cause == "iterations"


# --- 7. EXPIRED on wall-clock -------------------------------------------- #


def test_expired_on_wall_clock():
    c = AgentContract(budget=BudgetEnvelope(max_wall_clock_s=10.0))
    c.start()
    out = c.step(ContractObservation(elapsed_s=15.0))
    assert out == ContractState.EXPIRED
    assert c.terminal_cause == "wall-clock"


# --- 8. TERMINATED via external signal ----------------------------------- #


def test_terminated_via_external_signal():
    c = AgentContract(budget=BudgetEnvelope(max_iterations=100))
    c.start()
    out = c.step(ContractObservation(external_signal=True))
    assert out == ContractState.TERMINATED
    assert c.terminal_cause == "signal"


# --- 9. TERMINATED via terminate() --------------------------------------- #


def test_terminate_method():
    c = AgentContract()
    c.start()
    out = c.terminate(cause="user-ctrl-c")
    assert out == ContractState.TERMINATED
    assert c.terminal_cause == "user-ctrl-c"


# --- 10. Priority: deny-pattern beats budget on the same step ------------ #


def test_priority_deny_beats_budget():
    c = AgentContract(budget=BudgetEnvelope(
        max_usd=0.01,
        deny_patterns=(r"DROP\s+TABLE",),
    ))
    c.start()
    # Both conditions hit at once; deny-pattern wins per Section 3.4.
    out = c.step(ContractObservation(
        cost_usd=10.0,  # would violate USD too
        tool_calls=({"name": "sql", "arguments": {"q": "DROP TABLE users"}},),
    ))
    assert out == ContractState.VIOLATED
    assert c.terminal_cause == "deny-pattern"


# --- 11. Priority: signal beats fulfillment on the same step ------------- #


def test_priority_signal_beats_fulfillment():
    c = AgentContract(fulfillment=lambda _: True)
    c.start()
    out = c.step(ContractObservation(external_signal=True))
    assert out == ContractState.TERMINATED  # not FULFILLED


# --- 12. Terminal state is sticky — subsequent step() returns it --------- #


def test_terminal_state_sticky():
    c = AgentContract(budget=BudgetEnvelope(max_iterations=1))
    c.start()
    c.step(ContractObservation())  # EXPIRED
    assert c.state == ContractState.EXPIRED
    out = c.step(ContractObservation())
    assert out == ContractState.EXPIRED


# --- 13. Child cum_usd composes into parent ------------------------------ #


def test_child_cum_usd_rolls_up():
    parent = AgentContract(budget=BudgetEnvelope(max_usd=5.00))
    parent.start()
    child = parent.spawn_child(BudgetEnvelope(max_usd=1.00))
    child.start()
    child.step(ContractObservation(cost_usd=0.80))
    assert child.cum_usd == pytest.approx(0.80)
    assert parent.cum_usd == pytest.approx(0.80)


# --- 14. Child VIOLATED propagates to parent (default) ------------------- #


def test_child_violation_propagates():
    parent = AgentContract(budget=BudgetEnvelope(max_usd=5.00))
    parent.start()
    child = parent.spawn_child(BudgetEnvelope(max_usd=1.00))
    child.start()
    child.step(ContractObservation(cost_usd=2.00))  # VIOLATED
    assert child.state == ContractState.VIOLATED
    assert parent.state == ContractState.VIOLATED
    assert parent.terminal_cause and parent.terminal_cause.startswith("child:")


# --- 15. child_violation_isolation=True opt-in stops propagation --------- #


def test_child_violation_isolation():
    parent = AgentContract(
        budget=BudgetEnvelope(max_usd=5.00),
        child_violation_isolation=True,
    )
    parent.start()
    child = parent.spawn_child(BudgetEnvelope(max_usd=1.00))
    child.start()
    child.step(ContractObservation(cost_usd=2.00))
    assert child.state == ContractState.VIOLATED
    assert parent.state == ContractState.RUNNING


# --- 16. Audit-dict has the required compliance fields ------------------- #


def test_audit_dict_shape():
    c = AgentContract(budget=BudgetEnvelope(max_usd=1.00))
    c.start()
    c.step(ContractObservation(cost_usd=2.00))
    audit = c.to_audit_dict()
    assert audit["state"] == "violated"
    assert audit["cause"] == "budget-usd"
    assert audit["limit"] == 1.00
    assert audit["value"] == pytest.approx(2.00)
    assert audit["iter_count"] == 1
    assert "triggered_at" in audit


# --- 17. The $47k recursive-clarification-loop incident replay ----------- #


def test_47k_incident_regression():
    """arXiv 2601.08815 Appendix A.3.

    A two-agent recursive clarification loop running for eleven days
    burned $47,000 of API. Wrap a synthetic version in our envelope and
    show termination within one iteration of the breach.
    """
    contract = AgentContract(
        budget=BudgetEnvelope(max_usd=50.00, max_iterations=200, max_wall_clock_s=86400),
    )
    contract.start()
    # Simulate iterations at ~$5 each. 10 × $5 = $50 (== limit, no
    # violation: VIOLATED triggers on `>`, not `>=`). The 11th pushes
    # to $55 → VIOLATED.
    for i in range(10):
        out = contract.step(ContractObservation(cost_usd=5.00))
        assert out == ContractState.RUNNING, f"unexpected terminate at iter {i}"
    # 11th iteration pushes us to $55 → VIOLATED.
    out = contract.step(ContractObservation(cost_usd=5.00))
    assert out == ContractState.VIOLATED
    assert contract.terminal_cause == "budget-usd"
    # G1 — bounded blast: cum_usd is at most 1.5× the limit.
    assert contract.cum_usd <= 1.5 * contract.budget.max_usd
    # Saved 99.88% of the original $47k incident.
    assert contract.cum_usd < 47000 * 0.01


# --- 18. finalize() is idempotent and fires the right callback ----------- #


def test_finalize_idempotent_and_fires_callback():
    fires: list[tuple[str, str]] = []
    c = AgentContract(
        budget=BudgetEnvelope(max_usd=1.00),
        on_violated=lambda state, cause: fires.append((state.value, cause)),
    )
    c.start()
    c.step(ContractObservation(cost_usd=2.00))
    c.finalize()
    c.finalize()  # idempotent
    assert fires == [("violated", "budget-usd")]
