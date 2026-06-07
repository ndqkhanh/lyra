"""
Karpathy Auto-Research Loop — minimal viable autonomous experimentation.

Implements the Karpathy Loop (from karpathy/autoresearch, ~80k★):
  1. Agent proposes a change to the codebase/configuration
  2. Run a bounded evaluation (fixed time budget, one metric)
  3. Gate: keep if metric improves, discard otherwise
  4. Log everything in an experiment ledger (results.tsv equivalent)
  5. Auto-commit with descriptive messages
  6. Repeat until budget exhausted or N consecutive failures

This is THE minimal viable auto-research loop — proven with 93 automated
commits at Shopify (53% faster template rendering). Generalises beyond ML
to ANYTHING scoreable.

References
----------
- Karpathy/autoresearch: https://github.com/karpathy/autoresearch (~80k★)
- Darwin Gödel Machine (DGM-H): arXiv 2505.22954v3
- Lyra §4.15 Auto/Deep Research Plan: plans/4.15-auto-deep-research.md
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class ExperimentStatus(str, Enum):
    KEPT = "KEPT"
    DISCARDED = "DISCARDED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class ExperimentRecord:
    """A single row in the experiment ledger (analogous to results.tsv)."""

    iteration: int
    hypothesis: str
    change_description: str
    metric_before: float
    metric_after: float
    delta: float
    status: ExperimentStatus
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ExperimentLedger:
    """Append-only log of all experiments (the results.tsv equivalent).

    Persisted to disk as JSON Lines for durability across crashes.
    """

    records: list[ExperimentRecord] = field(default_factory=list)
    _path: Optional[Path] = None

    def append(self, record: ExperimentRecord) -> None:
        self.records.append(record)
        if self._path:
            self._flush()

    def best_record(self) -> Optional[ExperimentRecord]:
        kept = [r for r in self.records if r.status == ExperimentStatus.KEPT]
        if not kept:
            return None
        return max(kept, key=lambda r: r.delta)

    def best_metric(self) -> float:
        best = self.best_record()
        return best.metric_after if best else float("-inf")

    def total_kept(self) -> int:
        return sum(1 for r in self.records if r.status == ExperimentStatus.KEPT)

    def total_discarded(self) -> int:
        return sum(1 for r in self.records if r.status == ExperimentStatus.DISCARDED)

    def save(self, path: Path) -> None:
        self._path = path
        self._flush()

    def _flush(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps({
                "iteration": r.iteration,
                "hypothesis": r.hypothesis,
                "change_description": r.change_description,
                "metric_before": r.metric_before,
                "metric_after": r.metric_after,
                "delta": r.delta,
                "status": r.status.value,
                "duration_seconds": r.duration_seconds,
                "timestamp": r.timestamp,
            })
            for r in self.records
        ]
        with open(self._path, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    @classmethod
    def load(cls, path: Path) -> "ExperimentLedger":
        if not path.is_file():
            return cls(records=[], _path=path)

        records = []
        with open(path, "r") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                records.append(ExperimentRecord(
                    iteration=data["iteration"],
                    hypothesis=data["hypothesis"],
                    change_description=data["change_description"],
                    metric_before=data["metric_before"],
                    metric_after=data["metric_after"],
                    delta=data["delta"],
                    status=ExperimentStatus(data["status"]),
                    duration_seconds=data["duration_seconds"],
                    timestamp=data.get("timestamp", ""),
                ))
        return cls(records=records, _path=path)


# ---------------------------------------------------------------------------
# The Karpathy Loop
# ---------------------------------------------------------------------------


@dataclass
class AutoResearchLoop:
    """Minimal autonomous experimentation loop.

    Usage::

        loop = AutoResearchLoop(
            work_dir=Path("./my-project"),
            eval_command="python3 tests/benchmark.py --metric accuracy",
            max_iterations=100,
        )
        loop.set_proposer(my_proposer_fn)
        loop.set_gate(my_gate_fn)  # optional custom gate
        results = loop.run()
    """

    work_dir: Path
    eval_command: str  # Command that prints a single float to stdout
    max_iterations: int = 100
    max_consecutive_failures: int = 10
    eval_timeout_seconds: int = 300  # 5 min default (Karpathy's original)
    metric_name: str = "score"

    # Callbacks
    _proposer: Optional[Callable[[ExperimentLedger, Path], dict[str, Any]]] = None
    _gate: Optional[Callable[[float, float], bool]] = None
    _on_iteration: Optional[Callable[[int, ExperimentRecord], None]] = None

    # State
    ledger: ExperimentLedger = field(default_factory=ExperimentLedger)
    _best_metric: float = float("-inf")
    _consecutive_failures: int = 0

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_proposer(
        self,
        proposer: Callable[[ExperimentLedger, Path], dict[str, Any]],
    ) -> None:
        """Set the proposal function.

        The proposer receives the experiment ledger and working directory,
        and returns a dict with keys:
        - ``hypothesis``: one-line description of what's being tested
        - ``change_description``: detailed description of the change
        - ``patch`` or ``script``: the actual change to apply
        """
        self._proposer = proposer

    def set_gate(
        self,
        gate: Callable[[float, float], bool],
    ) -> None:
        """Set a custom gate function.

        Receives (metric_before, metric_after) and returns True to KEEP.
        Default: keep if metric_after > metric_before.
        """
        self._gate = gate

    def on_iteration(
        self,
        callback: Callable[[int, ExperimentRecord], None],
    ) -> None:
        """Register a callback invoked after each iteration."""
        self._on_iteration = callback

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self) -> ExperimentLedger:
        """Run the auto-research loop.

        Returns the experiment ledger with all records.

        Raises:
            RuntimeError: If no proposer is configured.
        """
        if self._proposer is None:
            raise RuntimeError(
                "No proposer configured. Call set_proposer() before run()."
            )

        for iteration in range(1, self.max_iterations + 1):
            if self._consecutive_failures >= self.max_consecutive_failures:
                break

            try:
                record = self._run_one_iteration(iteration)
                self.ledger.append(record)

                if record.status == ExperimentStatus.KEPT:
                    self._best_metric = record.metric_after
                    self._consecutive_failures = 0
                elif record.status == ExperimentStatus.DISCARDED:
                    self._consecutive_failures += 1

                if self._on_iteration:
                    self._on_iteration(iteration, record)

            except Exception as exc:
                self.ledger.append(ExperimentRecord(
                    iteration=iteration,
                    hypothesis=f"ERROR: {exc}",
                    change_description=str(exc),
                    metric_before=self._best_metric,
                    metric_after=self._best_metric,
                    delta=0.0,
                    status=ExperimentStatus.ERROR,
                    duration_seconds=0.0,
                ))
                self._consecutive_failures += 1

        return self.ledger

    def _run_one_iteration(self, iteration: int) -> ExperimentRecord:
        """Execute one iteration of the loop."""
        assert self._proposer is not None

        # 1. Measure baseline
        metric_before = self._get_current_metric()

        # 2. Propose a change
        proposal = self._proposer(self.ledger, self.work_dir)
        hypothesis = proposal.get("hypothesis", f"Iteration {iteration}")
        change_desc = proposal.get("change_description", hypothesis)
        patch = proposal.get("patch", "")
        script = proposal.get("script", "")

        # 3. Apply the change
        t0 = time.monotonic()
        if patch:
            self._apply_patch(patch)
        elif script:
            self._run_script(script)

        # 4. Evaluate
        metric_after = self._get_current_metric()
        elapsed = time.monotonic() - t0

        # 5. Gate: keep or discard
        delta = metric_after - metric_before
        if self._gate:
            keep = self._gate(metric_before, metric_after)
        else:
            keep = metric_after > metric_before  # Default: higher is better

        # 6. Revert if discarded
        if not keep and (patch or script):
            self._git_checkout()  # Revert changes

        # 7. Auto-commit if kept
        if keep and (patch or script):
            self._git_commit(hypothesis, metric_before, metric_after)

        return ExperimentRecord(
            iteration=iteration,
            hypothesis=hypothesis,
            change_description=change_desc,
            metric_before=metric_before,
            metric_after=metric_after,
            delta=delta,
            status=ExperimentStatus.KEPT if keep else ExperimentStatus.DISCARDED,
            duration_seconds=elapsed,
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _get_current_metric(self) -> float:
        """Run the eval command and parse its stdout as a float."""
        try:
            result = subprocess.run(
                self.eval_command,
                shell=True,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=self.eval_timeout_seconds,
            )
            return float(result.stdout.strip().split()[-1])
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            return self._best_metric  # Fall back to best known

    # ------------------------------------------------------------------
    # Git integration
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_patch(patch_text: str) -> None:
        subprocess.run(
            ["git", "apply"],
            input=patch_text,
            text=True,
            capture_output=True,
        )

    @staticmethod
    def _run_script(script: str) -> None:
        subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )

    def _git_commit(
        self,
        hypothesis: str,
        metric_before: float,
        metric_after: float,
    ) -> None:
        msg = (
            f"auto-research: {hypothesis}\n\n"
            f"  {self.metric_name}: {metric_before:.4f} → {metric_after:.4f} "
            f"(Δ {metric_after - metric_before:+.4f})"
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(self.work_dir),
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=str(self.work_dir),
            capture_output=True,
        )

    def _git_checkout(self) -> None:
        """Revert all uncommitted changes."""
        subprocess.run(
            ["git", "checkout", "--", "."],
            cwd=str(self.work_dir),
            capture_output=True,
        )
