"""L312-3 — LoopSession contract tests.

Ten cases covering interval validation, self-paced termination,
contract integration, until_pred, max_iter, directive STOP, and
keyboard-interrupt clean handling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from lyra_core.contracts import (
    AgentContract,
    BudgetEnvelope,
    ContractState,
)
from lyra_core.loops import (
    HumanDirective,
    InvalidInterval,
    LoopSession,
    validate_interval,
)


# --- 1. Interval validation: 270 fine, 300 rejected, 1200 fine ---------- #


def test_validate_interval_cache_warm():
    assert validate_interval(270) == 270.0


def test_validate_interval_300_rejected_worst_of_both():
    with pytest.raises(InvalidInterval) as ei:
        validate_interval(300)
    assert "worst-of-both" in str(ei.value)


def test_validate_interval_1200_fine():
    assert validate_interval(1200) == 1200.0


def test_validate_interval_below_floor_rejected():
    with pytest.raises(InvalidInterval):
        validate_interval(30)


def test_validate_interval_above_ceiling_rejected():
    with pytest.raises(InvalidInterval):
        validate_interval(7200)


# --- 2. Self-paced loop terminates when until_pred returns True --------- #


def test_self_paced_terminates_on_until_pred():
    iters = [0]

    def driver(prompt: str) -> dict:
        iters[0] += 1
        return {"content": f"iter-{iters[0]}", "cost_usd": 0.01, "tests_pass": iters[0] >= 3}

    sess = LoopSession(
        prompt="work",
        driver=driver,
        until_pred=lambda obs: bool(obs.get("tests_pass")),
        max_iter=10,
    )
    state = sess.run()
    assert state == ContractState.TERMINATED
    assert iters[0] == 3


# --- 3. Contract violation preempts until_pred -------------------------- #


def test_contract_violation_preempts_until_pred():
    def driver(prompt: str) -> dict:
        return {"cost_usd": 5.00, "tests_pass": True}

    sess = LoopSession(
        prompt="x",
        driver=driver,
        contract=AgentContract(budget=BudgetEnvelope(max_usd=1.00)),
        until_pred=lambda obs: True,  # would terminate but contract wins
        max_iter=5,
    )
    state = sess.run()
    assert state == ContractState.VIOLATED
    assert sess.contract.terminal_cause == "budget-usd"


# --- 4. max_iter triggers TERMINATED with loop-max-iter cause ----------- #


def test_max_iter_terminates_via_contract():
    def driver(_):
        return {"cost_usd": 0.01}

    sess = LoopSession(prompt="x", driver=driver, max_iter=3)
    state = sess.run()
    assert state == ContractState.TERMINATED
    assert sess.contract.terminal_cause == "loop-max-iter"
    assert sess.state.iteration == 3


# --- 5. KeyboardInterrupt → TERMINATED with external-cancel ------------- #


def test_keyboard_interrupt_terminates_cleanly():
    def driver(_):
        raise KeyboardInterrupt()

    sess = LoopSession(prompt="x", driver=driver, max_iter=5)
    state = sess.run()
    assert state == ContractState.TERMINATED
    assert sess.contract.terminal_cause == "external-cancel"


# --- 6. HUMAN_DIRECTIVE.md "STOP" → TERMINATED ------------------------- #


def test_directive_stop_terminates(tmp_path: Path):
    directive_file = tmp_path / "HUMAN_DIRECTIVE.md"
    directive_file.write_text("STOP after current story")
    directive = HumanDirective(path=directive_file)

    iters = [0]

    def driver(_):
        iters[0] += 1
        return {"cost_usd": 0.01}

    sess = LoopSession(
        prompt="work", driver=driver, directive=directive, max_iter=10,
    )
    state = sess.run()
    assert state == ContractState.TERMINATED
    assert sess.contract.terminal_cause == "human-directive-stop"
    # Driver was never called because the directive stopped before it.
    assert iters[0] == 0


# --- 7. HUMAN_DIRECTIVE redirect — non-STOP appended to next prompt ----- #


def test_directive_non_stop_injects_into_next_prompt(tmp_path: Path):
    directive_file = tmp_path / "HUMAN_DIRECTIVE.md"
    directive_file.write_text("Focus on US-007 first")
    directive = HumanDirective(path=directive_file)

    seen_prompts: list[str] = []

    def driver(prompt: str) -> dict:
        seen_prompts.append(prompt)
        return {"cost_usd": 0.01, "tests_pass": True}

    sess = LoopSession(
        prompt="general work",
        driver=driver,
        directive=directive,
        until_pred=lambda obs: bool(obs.get("tests_pass")),
        max_iter=3,
    )
    sess.run()
    assert any("US-007" in p for p in seen_prompts)
    assert any("<directive" in p for p in seen_prompts)


# --- 8. Sleep is invoked between iterations when interval set ---------- #


def test_sleep_invoked_when_interval_set():
    sleeps: list[float] = []

    def driver(_):
        return {"cost_usd": 0.01}

    sess = LoopSession(
        prompt="x", driver=driver, interval_s=270, max_iter=3,
        sleep_fn=lambda s: sleeps.append(s),
    )
    sess.run()
    # 3 iterations → 3 sleeps in the for-loop (one per iter).
    assert len(sleeps) == 3
    assert all(s == 270 for s in sleeps)


# --- 9. step() is callable independently of run() --------------------- #


def test_step_called_directly_advances_one_iteration():
    iters = [0]

    def driver(_):
        iters[0] += 1
        return {"cost_usd": 0.01}

    sess = LoopSession(prompt="x", driver=driver, max_iter=10)
    state = sess.step()
    assert iters[0] == 1
    assert state == ContractState.RUNNING


# --- 10. Terminal state is sticky on subsequent step() calls ----------- #


def test_terminal_state_sticky_across_step():
    sess = LoopSession(
        prompt="x",
        driver=lambda _: {"cost_usd": 5.0},
        contract=AgentContract(budget=BudgetEnvelope(max_usd=1.0)),
        max_iter=5,
    )
    sess.step()
    assert sess.contract.state == ContractState.VIOLATED
    sess.step()  # no-op
    assert sess.contract.state == ContractState.VIOLATED
