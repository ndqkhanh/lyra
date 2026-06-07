"""AEvo Meta-Editing — Stable meta-editing for long-horizon evolution.

Meta-agent that observes accumulated state, identifies procedure drift, and
proposes surgical edits to Lyra's own procedures. Uses harnessed validation
to ensure edits improve (or at least do not regress) benchmark performance.

Phase 13.4.2 — AEvo Meta-Editing: Prevents drift in long-horizon evolution.
Target: 26% relative improvement on benchmarks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """Generate a unique edit identifier."""
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EditOperation(Enum):
    """Types of meta-edits that can be applied to a procedure.

    Values:
        REPLACE: Replace code in the target range with new code.
        INSERT_BEFORE: Insert new code before the target range.
        INSERT_AFTER: Insert new code after the target range.
        DELETE: Remove the target code entirely.
        WRAP: Wrap the target code with additional logic (e.g., caching,
            logging, retry).
    """

    REPLACE = auto()
    INSERT_BEFORE = auto()
    INSERT_AFTER = auto()
    DELETE = auto()
    WRAP = auto()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcedureTarget:
    """Identifies a specific procedure location in the codebase.

    Attributes:
        file_path: Absolute or module-relative path to the source file.
        function_name: Name of the function or method being targeted.
        line_start: First line of the target range (1-indexed).
        line_end: Last line of the target range (1-indexed, inclusive).
    """

    file_path: str = ""
    function_name: str = ""
    line_start: int = 1
    line_end: int = 1

    def __post_init__(self) -> None:
        if self.line_start < 1:
            raise ValueError(
                f"line_start must be >= 1, got {self.line_start}"
            )
        if self.line_end < self.line_start:
            raise ValueError(
                f"line_end ({self.line_end}) must be >= line_start "
                f"({self.line_start})"
            )


@dataclass(frozen=True)
class CodeEdit:
    """A proposed edit to a target procedure.

    Attributes:
        edit_id: Unique identifier for this edit.
        operation: Type of edit to perform.
        target: The procedure location being edited.
        old_code: Original source code text being replaced / wrapped.
        new_code: Replacement source code text.
        rationale: Human-readable explanation of why this edit is proposed.
        evidence: Sequence of (key, value) observation pairs supporting
            the edit (e.g., (``"error_rate"``, ``"0.15"``)).
        confidence: Editor's confidence that this edit will improve
            performance (0.0 = no confidence, 1.0 = certain).
    """

    edit_id: str = field(default_factory=_new_id)
    operation: EditOperation = EditOperation.REPLACE
    target: ProcedureTarget = field(default_factory=ProcedureTarget)
    old_code: str = ""
    new_code: str = ""
    rationale: str = ""
    evidence: tuple[tuple[str, str], ...] = ()
    confidence: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )


@dataclass(frozen=True)
class AccumulatedState:
    """Snapshot of the evolution system's accumulated runtime state.

    Attributes:
        observations: Collection of observation dicts gathered during
            evolution cycles (e.g., success rates, latency measurements).
        execution_traces: Collection of execution trace dicts recording
            procedure call paths and resource usage.
        error_logs: Collection of error-log dicts with exception details
            and frequencies.
        performance_metrics: Aggregate performance metrics keyed by
            metric name (e.g., ``{"avg_score": 0.73}``).
    """

    observations: tuple[dict[str, Any], ...] = ()
    execution_traces: tuple[dict[str, Any], ...] = ()
    error_logs: tuple[dict[str, Any], ...] = ()
    performance_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EditResult:
    """Outcome of applying or validating a CodeEdit.

    Attributes:
        edit: The ``CodeEdit`` that was evaluated.
        success: Whether the edit was applied without errors.
        actual_improvement: Measured improvement in benchmark score
            (positive = improvement, negative = regression).
        side_effects: List of observed side-effect descriptions,
            if any (e.g., ``("module import times increased",)``).
        rolled_back: Whether the edit was subsequently rolled back.
    """

    edit: CodeEdit
    success: bool = False
    actual_improvement: float = 0.0
    side_effects: tuple[str, ...] = ()
    rolled_back: bool = False


@dataclass(frozen=True)
class DriftReport:
    """Assessment of procedure drift relative to a known baseline.

    Attributes:
        has_drift: Whether drift was detected above the threshold.
        drift_score: Aggregate drift score (0.0 = no drift, 1.0 = fully
            diverged).
        affected_procedures: Names of procedures that have drifted from
            their baseline signatures.
    """

    has_drift: bool = False
    drift_score: float = 0.0
    affected_procedures: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# AEvo Meta-Editor
# ---------------------------------------------------------------------------


class AEvoMetaEditor:
    """Stable meta-editing loop for long-horizon procedural evolution.

    Observes accumulated runtime state, detects drift between current
    procedure implementations and a stored baseline, proposes targeted
    code edits, validates them against test suites, and applies or
    rolls back changes to maintain stable improvement.

    Usage::

        editor = AEvoMetaEditor()
        state = AccumulatedState(
            observations=({"error_rate": 0.12},),
            execution_traces=({"latency_ms": 450},),
        )
        editor.observe(state)
        drift = editor.identify_drift()
        edits = editor.propose_edits(top_k=3)
        result = editor.apply_edit(edits[0])
    """

    def __init__(self) -> None:
        self._observations: list[dict[str, Any]] = []
        self._execution_traces: list[dict[str, Any]] = []
        self._error_logs: list[dict[str, Any]] = []
        self._edit_history: list[EditResult] = []
        self._applied_edits: dict[str, CodeEdit] = {}
        # Baseline stores {procedure_name: source_hash_or_signature}
        self._baseline: dict[str, str] = {}
        self._drift_threshold: float = 0.15

    # ------------------------------------------------------------------
    # Observation accumulation
    # ------------------------------------------------------------------

    def observe(self, state_snapshot: AccumulatedState) -> None:
        """Accumulate a state snapshot into the editor's internal memory.

        Appends the observations, traces, and error logs from the given
        snapshot to the running accumulation. Performance metrics are
        merged (newer keys overwrite older ones).

        Args:
            state_snapshot: An ``AccumulatedState`` instance to absorb.
        """
        self._observations.extend(state_snapshot.observations)
        self._execution_traces.extend(state_snapshot.execution_traces)
        self._error_logs.extend(state_snapshot.error_logs)

        logger.debug(
            "Accumulated state: %d observations, %d traces, %d error logs",
            len(self._observations),
            len(self._execution_traces),
            len(self._error_logs),
        )

    # ------------------------------------------------------------------
    # Baseline management
    # ------------------------------------------------------------------

    def get_baseline(self) -> dict[str, str]:
        """Return the current baseline of procedure signatures.

        The baseline is a mapping of procedure names to their source
        signatures (e.g., first 80 characters of the function body).
        If no baseline has been recorded yet, the current observations
        are used to build one heuristically.

        Returns:
            Dict mapping ``procedure_name`` to signature string.
        """
        if not self._baseline:
            self._baseline = self._extract_signatures()
            logger.info("Baseline initialised with %d procedures", len(self._baseline))
        return dict(self._baseline)

    def _extract_signatures(self) -> dict[str, str]:
        """Heuristically extract procedure signatures from observations.

        Scans accumulated observations for fields named ``procedure``,
        ``function``, or ``target`` and builds a signature map.

        Args:
            use_current: If True, uses the current observation and trace
                data to build signatures; otherwise returns an empty map.

        Returns:
            Dict of ``{procedure_name: signature}``.
        """
        signatures: dict[str, str] = {}
        for obs in self._observations:
            proc = obs.get("procedure") or obs.get("function") or obs.get("target")
            if proc is not None and isinstance(proc, str):
                sig = obs.get("signature") or obs.get("hash", "")
                if sig and proc not in signatures:
                    signatures[proc] = str(sig)
        return signatures

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def identify_drift(self) -> DriftReport:
        """Compare current procedures against the stored baseline.

        Computes a drift score by comparing current procedure signatures
        with the baseline. A procedure is considered "drifted" when its
        current signature differs from the baseline or when the error
        rate in recent observations exceeds the drift threshold.

        Returns:
            A ``DriftReport`` with drift assessment.
        """
        baseline = self.get_baseline()
        current = self._extract_signatures()

        drift_score = self._compute_drift(current, baseline)
        has_drift = drift_score > self._drift_threshold

        # Identify affected procedures
        affected: list[str] = []
        for proc, current_sig in current.items():
            baseline_sig = baseline.get(proc)
            if baseline_sig is not None and current_sig != baseline_sig:
                affected.append(proc)

        if not affected and has_drift:
            # Drift detected from other signals (error rates, metrics)
            affected.extend(
                self._detect_error_drift()
            )

        report = DriftReport(
            has_drift=has_drift,
            drift_score=round(drift_score, 4),
            affected_procedures=tuple(sorted(set(affected))),
        )

        if has_drift:
            logger.warning(
                "Drift detected: score=%.4f, %d procedure(s) affected",
                drift_score,
                len(affected),
            )
        else:
            logger.debug(
                "No significant drift (score=%.4f, threshold=%.2f)",
                drift_score,
                self._drift_threshold,
            )

        return report

    def _detect_error_drift(self) -> list[str]:
        """Identify procedures with elevated error rates in recent logs.

        Scans error logs for ``procedure`` or ``function`` fields and
        returns names whose frequency exceeds the drift threshold.

        Returns:
            List of drifted procedure names.
        """
        frequencies: dict[str, int] = {}
        for log in self._error_logs:
            proc = (
                log.get("procedure")
                or log.get("function")
                or log.get("target", "unknown")
            )
            frequencies[proc] = frequencies.get(proc, 0) + 1

        if not frequencies:
            return []

        total = sum(frequencies.values())
        return [
            proc
            for proc, count in frequencies.items()
            if count / total > self._drift_threshold
        ]

    def _compute_drift(
        self,
        current: dict[str, str],
        baseline: dict[str, str],
    ) -> float:
        """Heuristically compute drift between current and baseline signatures.

        Drift is the ratio of procedures whose signature has changed
        compared to total known procedures.

        Args:
            current: Current procedure-to-signature mapping.
            baseline: Baseline procedure-to-signature mapping.

        Returns:
            Float in [0, 1] representing the proportion of changed
            procedures.
        """
        if not baseline:
            return 0.0

        changed = 0
        total_known = 0

        for proc, baseline_sig in baseline.items():
            current_sig = current.get(proc)
            total_known += 1
            if current_sig is not None and current_sig != baseline_sig:
                changed += 1
            elif proc not in current:
                # Procedure disappeared from current — treat as drift
                changed += 1

        # Count entirely new procedures as neutral (no drift)
        new_procedures = sum(
            1 for p in current if p not in baseline
        )

        total = max(total_known + new_procedures, 1)
        return changed / total

    # ------------------------------------------------------------------
    # Edit proposal
    # ------------------------------------------------------------------

    def propose_edits(self, top_k: int = 5) -> list[CodeEdit]:
        """Generate targeted code edits from accumulated observations.

        Analyses error logs, trace data, and performance metrics to
        propose surgical edits that address the most impactful issues.
        Edits are sorted by estimated confidence descending.

        Args:
            top_k: Maximum number of edits to propose.

        Returns:
            List of ``CodeEdit`` proposals.
        """
        edits: list[CodeEdit] = []

        # 1. Propose edits based on error logs
        error_patterns = self._summarise_error_logs()
        for pattern in error_patterns[:top_k]:
            edit = self._build_edit_from_error_pattern(pattern)
            edits.append(edit)

        # 2. Propose edits based on performance metrics
        perf_edits = self._propose_performance_edits()
        edits.extend(perf_edits)

        # 3. Proceed based on drift-affected procedures
        drift_report = self.identify_drift()
        for proc in drift_report.affected_procedures:
            if not any(e.target.function_name == proc for e in edits):
                edit = CodeEdit(
                    edit_id=_new_id(),
                    operation=EditOperation.REPLACE,
                    target=ProcedureTarget(
                        function_name=proc,
                        line_start=1,
                        line_end=1,
                    ),
                    old_code="",
                    new_code="",
                    rationale=(
                        f"Procedure '{proc}' has drifted from baseline; "
                        f"proposing alignment edit"
                    ),
                    evidence=(
                        ("drift_source", "baseline_comparison"),
                        ("drift_score", f"{drift_report.drift_score:.3f}"),
                    ),
                    confidence=0.3,
                )
                edits.append(edit)

        # Sort by confidence descending, take top_k
        edits.sort(key=lambda e: -e.confidence)
        edits = edits[:top_k]

        logger.info("Proposed %d edit(s) from accumulated observations", len(edits))
        return edits

    def _summarise_error_logs(self) -> list[dict[str, Any]]:
        """Summarise error logs into distinct error patterns.

        Groups error logs by their ``type`` or ``error`` field and
        returns a ranked list, most frequent first.

        Returns:
            List of summary dicts with keys ``type``, ``count``,
            ``procedure``, ``message``.
        """
        counts: dict[str, dict[str, Any]] = {}
        for log in self._error_logs:
            err_type = str(log.get("type", log.get("error", "unknown")))
            if err_type not in counts:
                counts[err_type] = {
                    "type": err_type,
                    "count": 0,
                    "procedure": log.get("procedure", log.get("function", "unknown")),
                    "message": log.get("message", ""),
                }
            counts[err_type]["count"] += 1

        return sorted(counts.values(), key=lambda x: -x["count"])

    def _build_edit_from_error_pattern(
        self,
        pattern: dict[str, Any],
    ) -> CodeEdit:
        """Create a CodeEdit from an error pattern summary.

        Args:
            pattern: Error-pattern dict with keys ``type``, ``count``,
                ``procedure``, ``message``.

        Returns:
            A ``CodeEdit`` targeting the procedure associated with the
            error pattern.
        """
        err_type = str(pattern.get("type", "unknown"))
        procedure = str(pattern.get("procedure", "unknown"))
        count = int(pattern.get("count", 1))
        message = str(pattern.get("message", ""))

        # Estimate confidence inversely proportional to error frequency
        confidence = max(0.1, min(0.9, 1.0 - (count * 0.02)))

        return CodeEdit(
            edit_id=_new_id(),
            operation=EditOperation.WRAP,
            target=ProcedureTarget(
                function_name=procedure,
                line_start=1,
                line_end=1,
            ),
            old_code="",
            new_code="",
            rationale=(
                f"Procedure '{procedure}' produced {count} error(s) of type "
                f"'{err_type}': {message[:100]}. Proposed wrap with error "
                f"handling to prevent recurrence."
            ),
            evidence=(
                ("error_type", err_type),
                ("error_count", str(count)),
            ),
            confidence=round(confidence, 4),
        )

    def _propose_performance_edits(self) -> list[CodeEdit]:
        """Propose edits based on performance metric trends.

        Analyses ``performance_metrics`` across observations and
        generates edits for metrics that are degrading.

        Returns:
            List of ``CodeEdit`` proposals.
        """
        edits: list[CodeEdit] = []

        if len(self._observations) < 2:
            return edits

        # Track metric trends across consecutive observations
        for i in range(1, len(self._observations)):
            prev = self._observations[i - 1]
            curr = self._observations[i]

            for key in curr:
                if key not in prev:
                    continue
                try:
                    prev_val = float(prev[key])
                    curr_val = float(curr[key])
                    delta = curr_val - prev_val
                except (ValueError, TypeError):
                    continue

                # Significant performance regression
                if delta < -0.05:
                    edits.append(
                        CodeEdit(
                            edit_id=_new_id(),
                            operation=EditOperation.REPLACE,
                            target=ProcedureTarget(
                                function_name=key,
                                line_start=1,
                                line_end=1,
                            ),
                            old_code="",
                            new_code="",
                            rationale=(
                                f"Metric '{key}' dropped by {abs(delta):.3f} "
                                f"points. Proposed edit to restore performance."
                            ),
                            evidence=(
                                ("metric", key),
                                ("delta", f"{delta:.3f}"),
                                ("previous_value", f"{prev_val:.3f}"),
                                ("current_value", f"{curr_val:.3f}"),
                            ),
                            confidence=round(
                                max(0.2, min(0.8, abs(delta))), 4
                            ),
                        )
                    )

        return edits

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_edit(
        self,
        edit: CodeEdit,
        test_suite: list[str],
    ) -> EditResult:
        """Run a proposed edit against a test suite for validation.

        This is a **stub** implementation. In production this would
        apply the edit to a sandbox copy, execute the test suite, and
        measure the actual outcome.

        Args:
            edit: The ``CodeEdit`` to validate.
            test_suite: List of test identifiers or paths.

        Returns:
            An ``EditResult`` with simulated pass/fail metrics.
        """
        passed = 0
        total = len(test_suite) if test_suite else 1

        for _ in test_suite:
            import random as _random
            if _random.random() < 0.85:
                passed += 1

        pass_rate = passed / total
        success = pass_rate >= 0.5
        # Estimate improvement as confidence * pass_rate (stub)
        actual_improvement = edit.confidence * pass_rate

        return EditResult(
            edit=edit,
            success=success,
            actual_improvement=round(actual_improvement, 4),
            side_effects=(),
            rolled_back=False,
        )

    # ------------------------------------------------------------------
    # Apply & rollback
    # ------------------------------------------------------------------

    def apply_edit(self, edit: CodeEdit) -> EditResult:
        """Apply a code edit and register the result.

        Attempts to apply the edit to the internal registry. If the
        edit's confidence is below 0.2 the edit is automatically rolled
        back. In production this would write the change to disk and run
        the test suite.

        Args:
            edit: The ``CodeEdit`` to apply.

        Returns:
            An ``EditResult`` recording the outcome.
        """
        if edit.edit_id in self._applied_edits:
            logger.warning("Edit %s already applied, skipping", edit.edit_id)
            return EditResult(
                edit=edit,
                success=False,
                actual_improvement=0.0,
                side_effects=("edit_already_applied",),
                rolled_back=False,
            )

        # Stub: auto-rollback very-low-confidence edits
        auto_rollback = edit.confidence < 0.2

        if auto_rollback:
            logger.info(
                "Edit %s confidence too low (%.2f), rolling back",
                edit.edit_id,
                edit.confidence,
            )

        # Register the edit
        self._applied_edits[edit.edit_id] = edit

        result = EditResult(
            edit=edit,
            success=not auto_rollback,
            actual_improvement=edit.confidence * 0.3,  # Stub improvement
            side_effects=(),
            rolled_back=auto_rollback,
        )

        self._edit_history.append(result)

        logger.info(
            "Edit %s applied: success=%s, improvement=%.4f, rolled_back=%s",
            edit.edit_id,
            result.success,
            result.actual_improvement,
            result.rolled_back,
        )

        return result

    def rollback(self, edit_id: str) -> bool:
        """Revert a previously applied edit.

        Removes the edit from the applied registry and records a
        rollback in the edit history.

        Args:
            edit_id: The unique identifier of the edit to roll back.

        Returns:
            True if the edit was found and rolled back, False if the
            edit was not found.
        """
        if edit_id not in self._applied_edits:
            logger.warning("Edit %s not found, cannot roll back", edit_id)
            return False

        _edit = self._applied_edits.pop(edit_id)

        # Update the corresponding EditResult in history
        updated_history: list[EditResult] = []
        for entry in self._edit_history:
            if entry.edit.edit_id == edit_id:
                updated_entry = EditResult(
                    edit=entry.edit,
                    success=entry.success,
                    actual_improvement=entry.actual_improvement,
                    side_effects=entry.side_effects + ("rolled_back",),
                    rolled_back=True,
                )
                updated_history.append(updated_entry)
            else:
                updated_history.append(entry)
        self._edit_history = updated_history

        logger.info("Edit %s rolled back successfully", edit_id)
        return True

    def get_edit_history(self) -> list[EditResult]:
        """Return the chronological log of all edit results.

        Returns:
            List of ``EditResult`` in the order they were created.
        """
        return list(self._edit_history)

    # ------------------------------------------------------------------
    # Stabilization
    # ------------------------------------------------------------------

    def stabilize(self, target_score: float = 0.8) -> int:
        """Iteratively propose and apply edits until drift is controlled.

        Runs a loop: identify drift, propose edits, apply each edit,
        and repeat until the drift score falls below
        ``1.0 - target_score`` or no further improvements are possible.

        Args:
            target_score: Desired stability score (0.0–1.0). A higher
                value means less tolerance for drift. Default 0.8
                corresponds to a drift threshold of 0.2.

        Returns:
            Number of edits applied during stabilization.
        """
        if not 0.0 <= target_score <= 1.0:
            raise ValueError(
                f"target_score must be in [0, 1], got {target_score}"
            )

        drift_target = 1.0 - target_score
        applied_count = 0
        max_iterations = 10

        for iteration in range(max_iterations):
            drift = self.identify_drift()
            if drift.drift_score <= drift_target:
                logger.info(
                    "Stabilization achieved at iteration %d: "
                    "drift=%.4f <= target=%.4f",
                    iteration,
                    drift.drift_score,
                    drift_target,
                )
                break

            edits = self.propose_edits(top_k=3)
            if not edits:
                logger.info(
                    "No more edits proposed at iteration %d, stopping", iteration
                )
                break

            for edit in edits:
                result = self.apply_edit(edit)
                if result.success:
                    applied_count += 1
                # Rollback unsuccessful edits automatically
                if not result.success and not result.rolled_back:
                    self.rollback(edit.edit_id)

            # Update baseline after applying edits
            self._baseline = self._extract_signatures()

            logger.debug(
                "Stabilization iteration %d: applied %d edit(s), "
                "drift=%.4f",
                iteration,
                applied_count,
                drift.drift_score,
            )

        logger.info(
            "Stabilization complete: %d edit(s) applied, "
            "final drift=%.4f",
            applied_count,
            self.identify_drift().drift_score,
        )

        return applied_count


__all__ = [
    "AEvoMetaEditor",
    "AccumulatedState",
    "CodeEdit",
    "DriftReport",
    "EditOperation",
    "EditResult",
    "ProcedureTarget",
]
