"""L312-2 — RalphRunner contract tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.contracts import (
    AgentContract,
    BudgetEnvelope,
    ContractState,
)
from lyra_core.ralph import (
    Prd,
    UserStory,
    save_prd,
    load_prd,
    parse_completion,
)
from lyra_core.ralph.completion import CompletionSignal
from lyra_core.ralph.runner import (
    DangerousFlagRefused,
    RalphIterationResult,
    RalphRunner,
)


def _seed_prd(run_dir: Path, *stories: UserStory, branch: str = "ralph/test") -> Prd:
    prd = Prd(
        project="test",
        branchName=branch,
        description="desc",
        userStories=list(stories),
    )
    save_prd(prd, run_dir / "prd.json")
    return prd


def _success_driver(content: str, *, did_work: bool = True, cost: float = 0.05):
    """Driver that always emits the same content + does work."""
    def driver(prd, story, progress):
        return RalphIterationResult(
            iteration=0,
            story_id=story.id,
            text_output=content,
            cost_usd=cost,
            did_work=did_work,
            completion=parse_completion(content),
            learnings=[f"completed {story.id}"],
        )
    return driver


# --- 1. PRD round-trip --------------------------------------------------- #


def test_prd_round_trip(tmp_path: Path):
    prd = Prd(
        project="P", branchName="ralph/x", description="d",
        userStories=[UserStory(id="US-001", title="t", priority=1, passes=False)],
    )
    save_prd(prd, tmp_path / "prd.json")
    loaded = load_prd(tmp_path / "prd.json")
    assert loaded.project == "P"
    assert loaded.userStories[0].id == "US-001"
    assert loaded.userStories[0].passes is False


# --- 2. next_pending_story by priority ----------------------------------- #


def test_next_pending_story_lowest_priority_int():
    prd = Prd(userStories=[
        UserStory(id="A", priority=2, passes=False),
        UserStory(id="B", priority=1, passes=False),
        UserStory(id="C", priority=0, passes=True),
    ])
    next_story = prd.next_pending_story()
    assert next_story is not None
    assert next_story.id == "B"


# --- 3. all_passing reflects state -------------------------------------- #


def test_all_passing():
    prd = Prd(userStories=[UserStory(id="A", passes=True), UserStory(id="B", passes=True)])
    assert prd.all_passing()
    prd.userStories[0].passes = False
    assert not prd.all_passing()


# --- 4. Runner refuses --dangerously-skip-permissions ------------------- #


def test_refuses_dangerous_flag(tmp_path: Path):
    save_prd(Prd(branchName="r/x"), tmp_path / "prd.json")
    with pytest.raises(DangerousFlagRefused):
        RalphRunner(
            run_dir=tmp_path,
            driver=_success_driver("done"),
            dangerous_skip_permissions=True,
        )


# --- 5. Runner walks PRD until COMPLETE --------------------------------- #


def test_runner_completes_full_prd(tmp_path: Path):
    _seed_prd(
        tmp_path,
        UserStory(id="US-001", title="one", priority=1),
        UserStory(id="US-002", title="two", priority=2),
    )
    # On the second story (US-002), emit the COMPLETE token.
    iteration = [0]

    def driver(prd, story, progress):
        iteration[0] += 1
        text = ("<promise>COMPLETE</promise>" if story.id == "US-002" else "did work")
        return RalphIterationResult(
            iteration=iteration[0], story_id=story.id, text_output=text,
            cost_usd=0.05, did_work=True, completion=parse_completion(text),
        )

    runner = RalphRunner(
        run_dir=tmp_path, driver=driver,
        contract=AgentContract(budget=BudgetEnvelope(max_usd=10.0)),
        max_iterations=10,
    )
    state = runner.run()
    assert state == ContractState.FULFILLED
    final = load_prd(tmp_path / "prd.json")
    assert final.all_passing()


# --- 6. Contract preempts COMPLETE on budget breach --------------------- #


def test_contract_preempts_completion_on_budget(tmp_path: Path):
    _seed_prd(
        tmp_path,
        UserStory(id="US-001", priority=1),
        UserStory(id="US-002", priority=2),
    )
    runner = RalphRunner(
        run_dir=tmp_path,
        driver=_success_driver("<promise>COMPLETE</promise>", cost=2.0),
        contract=AgentContract(budget=BudgetEnvelope(max_usd=1.0)),
        max_iterations=10,
    )
    state = runner.run()
    assert state == ContractState.VIOLATED
    assert runner.contract.terminal_cause == "budget-usd"


# --- 7. HUMAN_DIRECTIVE STOP terminates immediately --------------------- #


def test_directive_stop_terminates_runner(tmp_path: Path):
    _seed_prd(tmp_path, UserStory(id="US-001", priority=1))
    (tmp_path / "HUMAN_DIRECTIVE.md").write_text("STOP this run")

    runner = RalphRunner(
        run_dir=tmp_path,
        driver=_success_driver("done"),
        max_iterations=10,
    )
    state = runner.run()
    assert state == ContractState.TERMINATED
    assert runner.contract.terminal_cause == "human-directive-stop"


# --- 8. Branch change archives prior run + resets progress ------------- #


def test_branch_change_archives_and_resets(tmp_path: Path):
    _seed_prd(tmp_path, UserStory(id="US-001", priority=1), branch="ralph/old")
    (tmp_path / "progress.txt").write_text("# Ralph Progress Log\nold content\n")
    (tmp_path / ".last-branch").write_text("ralph/old")

    # Now switch the PRD branch.
    prd = load_prd(tmp_path / "prd.json")
    prd.branchName = "ralph/new"
    save_prd(prd, tmp_path / "prd.json")

    runner = RalphRunner(
        run_dir=tmp_path,
        driver=_success_driver("<promise>COMPLETE</promise>"),
        max_iterations=3,
    )
    runner.run()
    archive_dirs = list((tmp_path / "archive").glob("*"))
    assert archive_dirs, "branch change should produce an archive directory"


# --- 9. max_iterations triggers ralph-max-iter ------------------------- #


def test_max_iterations_terminates_with_ralph_cause(tmp_path: Path):
    _seed_prd(tmp_path, UserStory(id="US-001", priority=1))

    # Driver that never emits COMPLETE and never advances PRD.
    def driver(prd, story, progress):
        return RalphIterationResult(
            iteration=0, story_id=story.id, text_output="not done",
            cost_usd=0.01, did_work=False, completion=CompletionSignal(),
        )

    runner = RalphRunner(
        run_dir=tmp_path, driver=driver, max_iterations=3,
    )
    state = runner.run()
    assert state == ContractState.TERMINATED
    assert runner.contract.terminal_cause == "ralph-max-iter"


# --- 10. progress.txt written every iteration -------------------------- #


def test_progress_log_written(tmp_path: Path):
    _seed_prd(tmp_path,
              UserStory(id="US-001", priority=1),
              UserStory(id="US-002", priority=2))
    runner = RalphRunner(
        run_dir=tmp_path,
        driver=_success_driver("<promise>COMPLETE</promise>"),
        max_iterations=5,
    )
    runner.run()
    body = (tmp_path / "progress.txt").read_text(encoding="utf-8")
    assert "US-001" in body
    # All iterations recorded.
    assert body.count("##") >= 2  # one for patterns + at least one iteration


# --- 11. Missing prd.json → FileNotFoundError -------------------------- #


def test_missing_prd_raises(tmp_path: Path):
    runner = RalphRunner(
        run_dir=tmp_path, driver=_success_driver("done"), max_iterations=2,
    )
    with pytest.raises(FileNotFoundError):
        runner.run()
