"""L312-2 — RalphRunner: drive a Ralph loop until COMPLETE / contract-terminal.

Composes :class:`AgentContract` (L312-4) + :class:`HumanDirective`
(L312-5) + :func:`parse_completion` (this package) + :class:`Prd` /
:class:`ProgressLog` (this package). The actual *agent* per iteration
is supplied by the caller as a callable so the runner is testable
without an LLM.

Refuses ``--dangerously-skip-permissions`` outright.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from lyra_core.contracts import (
    AgentContract,
    BudgetEnvelope,
    ContractObservation,
    ContractState,
)
from lyra_core.loops.directive import HumanDirective

from .completion import CompletionSignal, parse_completion
from .prd import Prd, UserStory, load_prd, save_prd
from .progress import ProgressLog


__all__ = [
    "RalphIterationResult",
    "RalphRunner",
    "DangerousFlagRefused",
]


class DangerousFlagRefused(RuntimeError):
    """Raised when the runner is asked to operate with permissions disabled.

    Lyra's L312-2 explicitly refuses `--dangerously-skip-permissions`
    (snarktank/frankbria) and `--dangerously-allow-all` (Amp). The
    runner relies on the permission bridge + path-quarantine +
    cost guard instead.
    """


@dataclass
class RalphIterationResult:
    """One iteration's outcome — fed to the contract + the runner state."""

    iteration: int
    story_id: str
    text_output: str = ""
    cost_usd: float = 0.0
    elapsed_s: float = 0.0
    did_work: bool = False                 # frankbria's pre-flight
    completion: CompletionSignal = field(default_factory=CompletionSignal)
    files_changed: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)


# --- Iteration driver protocol ---------------------------------------- #


IterationDriver = Callable[[Prd, UserStory, ProgressLog], RalphIterationResult]
"""Caller-supplied: given the PRD, the next pending story, and the
progress log, drive one iteration and return its outcome. The runner
does not own the model or the tool dispatch — the caller does."""


@dataclass
class RalphRunner:
    """Drive a Ralph loop until COMPLETE or contract-terminal.

    Files written under ``run_dir``::

        run_dir/
          prd.json            (working copy; ``passes`` flips True per story)
          progress.txt        (codebase patterns + iteration log)
          state.json          (iteration counter, last branch, last completion)
          HUMAN_DIRECTIVE.md  (async control file; user touches between iters)
          directives/         (consumed-directive archive)
          archive/            (auto-archived prior runs on branch change)

    Caller provides ``driver`` — a callable invoked once per iteration
    with the live PRD + the next story + the progress log. The driver
    returns a :class:`RalphIterationResult` describing what happened.
    """

    run_dir: Path
    driver: IterationDriver
    contract: AgentContract = field(default_factory=AgentContract)
    max_iterations: int = 50
    dangerous_skip_permissions: bool = False  # parameter exists only to refuse it

    # Set up by ``__post_init__``.
    prd_path: Path = field(init=False)
    progress_path: Path = field(init=False)
    state_path: Path = field(init=False)
    archive_dir: Path = field(init=False)
    directive_path: Path = field(init=False)
    progress: ProgressLog = field(init=False)
    directive: HumanDirective = field(init=False)

    def __post_init__(self) -> None:
        if self.dangerous_skip_permissions:
            raise DangerousFlagRefused(
                "lyra ralph refuses --dangerously-skip-permissions. "
                "Use the permission bridge + path quarantine + cost guard."
            )
        self.run_dir = Path(self.run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.prd_path = self.run_dir / "prd.json"
        self.progress_path = self.run_dir / "progress.txt"
        self.state_path = self.run_dir / "state.json"
        self.archive_dir = self.run_dir / "archive"
        self.directive_path = self.run_dir / "HUMAN_DIRECTIVE.md"
        self.progress = ProgressLog(self.progress_path)
        self.directive = HumanDirective(path=self.directive_path)
        if self.contract.state == ContractState.PENDING:
            self.contract.start()

    # ---- public API ------------------------------------------------- #

    def run(self) -> ContractState:
        """Drive iterations until terminal."""
        if not self.prd_path.exists():
            raise FileNotFoundError(f"prd.json missing at {self.prd_path}")
        prd = load_prd(self.prd_path)
        self._handle_branch_change(prd)
        self.progress.init_if_missing()

        for iteration in range(1, self.max_iterations + 1):
            if self.contract.state.is_terminal():
                break

            # L312-5 — async control. STOP terminates immediately.
            directive_text = self.directive.consume_if_changed()
            if directive_text is not None:
                if "STOP" in directive_text.upper().split():
                    self.contract.terminate(cause="human-directive-stop")
                    break

            story = prd.next_pending_story()
            if story is None:
                # Nothing pending — emit FULFILLED via the contract.
                self.contract.fulfillment = lambda *_: True  # type: ignore[assignment]
                self.contract.step(ContractObservation())
                break

            outcome = self.driver(prd, story, self.progress)
            self._record_iteration(prd, story, outcome)
            obs = ContractObservation(
                cost_usd=outcome.cost_usd,
                elapsed_s=outcome.elapsed_s,
                tool_calls=(),
            )
            state = self.contract.step(obs)
            if state.is_terminal():
                break

            if outcome.completion.found and outcome.did_work:
                # Tier 2 — string match + work-was-done check (frankbria).
                # If the PRD shows all stories passing, FULFILLED.
                if prd.all_passing():
                    self.contract.fulfillment = lambda *_: True  # type: ignore[assignment]
                    self.contract.step(ContractObservation())
                    break

        # If we exited the for-loop without a terminal contract, mark EXPIRED.
        if not self.contract.state.is_terminal():
            self.contract.terminate(cause="ralph-max-iter")
        self.contract.finalize()
        save_prd(prd, self.prd_path)
        return self.contract.state

    # ---- internal --------------------------------------------------- #

    def _record_iteration(
        self,
        prd: Prd,
        story: UserStory,
        outcome: RalphIterationResult,
    ) -> None:
        if outcome.did_work:
            try:
                prd.mark_pass(story.id)
            except KeyError:
                pass
            save_prd(prd, self.prd_path)
        what = (
            outcome.text_output.splitlines()[0]
            if outcome.text_output else f"worked on {story.id}"
        )
        self.progress.append_iteration(
            story_id=story.id,
            what_was_done=what,
            files_changed=outcome.files_changed,
            learnings=outcome.learnings,
        )

    def _handle_branch_change(self, prd: Prd) -> None:
        """Archive prior run if the PRD's branch changed since last run."""
        last_branch_file = self.run_dir / ".last-branch"
        if last_branch_file.exists():
            last_branch = last_branch_file.read_text(encoding="utf-8").strip()
            if last_branch and last_branch != prd.branchName:
                self._archive_run(last_branch)
                self.progress.reset()
        last_branch_file.write_text(prd.branchName or "", encoding="utf-8")

    def _archive_run(self, last_branch: str) -> None:
        from datetime import datetime, timezone
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_branch = last_branch.replace("/", "-")
        target = self.archive_dir / f"{date}-{safe_branch}"
        target.mkdir(parents=True, exist_ok=True)
        for f in (self.prd_path, self.progress_path):
            if f.exists():
                (target / f.name).write_text(
                    f.read_text(encoding="utf-8"), encoding="utf-8",
                )
