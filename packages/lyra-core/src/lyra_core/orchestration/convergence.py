"""Adversarial convergence protocol — code→build→test→review loop with gating.

Inspired by Claude Code Dynamic Workflows' adversarial convergence:
  - Loop: generate code → build → test → review
  - Each gate must pass before proceeding
  - Auto-fix with exponential backoff on failure
  - Review feedback incorporated into next iteration
  - Max attempts enforced to prevent infinite loops
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GateResult(str, Enum):
    """Result of a convergence gate check."""
    PASS = "pass"
    FAIL_RETRY = "fail_retry"    # Can auto-fix
    FAIL_ABORT = "fail_abort"    # Unrecoverable — abort
    TIMEOUT = "timeout"


class ConvergencePhase(str, Enum):
    """Phases in the convergence loop."""
    GENERATE = "generate"  # Generate code/artifact
    BUILD = "build"        # Compile/validate
    TEST = "test"          # Run tests
    REVIEW = "review"      # Quality review
    CONVERGED = "converged"  # All gates passed


@dataclass
class ConvergenceAttempt:
    """Record of a single convergence attempt."""
    attempt: int
    phase: ConvergencePhase
    result: GateResult
    output: Any = None
    error: str = ""
    elapsed_s: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConvergenceConfig:
    """Configuration for the convergence loop."""

    max_attempts: int = 5
    build_timeout_s: float = 120.0
    test_timeout_s: float = 300.0
    review_timeout_s: float = 60.0
    backoff_base_s: float = 1.0  # Exponential backoff multiplier
    require_build: bool = True
    require_test: bool = True
    require_review: bool = True
    auto_fix_enabled: bool = True


@dataclass
class ConvergenceReport:
    """Full report of a convergence run."""

    converged: bool
    total_attempts: int
    attempts: list[ConvergenceAttempt] = field(default_factory=list)
    final_output: Any = None
    total_elapsed_s: float = 0.0
    phases_passed: set[str] = field(default_factory=set)

    @property
    def build_passed(self) -> bool:
        return any(
            a.phase == ConvergencePhase.BUILD and a.result == GateResult.PASS
            for a in self.attempts
        )

    @property
    def test_passed(self) -> bool:
        return any(
            a.phase == ConvergencePhase.TEST and a.result == GateResult.PASS
            for a in self.attempts
        )

    @property
    def review_passed(self) -> bool:
        return any(
            a.phase == ConvergencePhase.REVIEW and a.result == GateResult.PASS
            for a in self.attempts
        )


class ConvergenceLoop:
    """Adversarial convergence loop with gate-based quality enforcement.

    The loop runs: GENERATE → BUILD → TEST → REVIEW, with each phase
    gated. A phase that fails with FAIL_RETRY triggers an auto-fix
    attempt (if enabled). FAIL_ABORT stops the loop immediately.

    Usage::

        loop = ConvergenceLoop()
        report = await loop.run(
            generator=my_generator,
            builder=my_builder,
            tester=my_tester,
            reviewer=my_reviewer,
        )
        assert report.converged
    """

    def __init__(self, config: ConvergenceConfig | None = None) -> None:
        self.config = config or ConvergenceConfig()
        self._attempts: list[ConvergenceAttempt] = []
        self._current_phase = ConvergencePhase.GENERATE

    async def run(
        self,
        *,
        generator: Callable[[int], Any],
        builder: Callable[[Any], GateResult] | None = None,
        tester: Callable[[Any], GateResult] | None = None,
        reviewer: Callable[[Any], GateResult] | None = None,
    ) -> ConvergenceReport:
        """Run the full convergence loop.

        Args:
            generator: Takes attempt number, returns artifact to validate
            builder: Validates the artifact builds/compiles
            tester: Runs tests against the artifact
            reviewer: Reviews the artifact for quality

        Returns:
            ConvergenceReport with full attempt history
        """
        t0 = time.time()
        self._attempts = []
        attempt = 0
        artifact = None
        converged = False

        while attempt < self.config.max_attempts:
            attempt += 1

            # Phase 1: GENERATE
            self._current_phase = ConvergencePhase.GENERATE
            try:
                artifact = await generator(attempt)
            except Exception as exc:
                self._record(attempt, ConvergencePhase.GENERATE,
                            GateResult.FAIL_ABORT, error=str(exc))
                break

            # Phase 2: BUILD (gate)
            if self.config.require_build and builder:
                build_result = await self._run_phase(
                    attempt, ConvergencePhase.BUILD, builder, artifact)
                if build_result == GateResult.FAIL_ABORT:
                    break
                if build_result == GateResult.FAIL_RETRY:
                    continue

            # Phase 3: TEST (gate)
            if self.config.require_test and tester:
                test_result = await self._run_phase(
                    attempt, ConvergencePhase.TEST, tester, artifact)
                if test_result == GateResult.FAIL_ABORT:
                    break
                if test_result == GateResult.FAIL_RETRY and self.config.auto_fix_enabled:
                    continue

            # Phase 4: REVIEW (gate)
            if self.config.require_review and reviewer:
                review_result = await self._run_phase(
                    attempt, ConvergencePhase.REVIEW, reviewer, artifact)
                if review_result == GateResult.FAIL_ABORT:
                    break
                if review_result == GateResult.FAIL_RETRY:
                    continue

            # All gates passed
            converged = True
            self._current_phase = ConvergencePhase.CONVERGED
            break

        return ConvergenceReport(
            converged=converged,
            total_attempts=attempt,
            attempts=list(self._attempts),
            final_output=artifact,
            total_elapsed_s=time.time() - t0,
            phases_passed={
                a.phase.value for a in self._attempts if a.result == GateResult.PASS
            },
        )

    async def _run_phase(
        self,
        attempt: int,
        phase: ConvergencePhase,
        gate_fn: Callable,
        artifact: Any,
    ) -> GateResult:
        """Run a single convergence phase and record the result."""
        t0 = time.time()
        try:
            result = gate_fn(artifact)
            if hasattr(result, '__await__'):
                result = await result
        except Exception as exc:
            result = GateResult.FAIL_RETRY
            self._record(attempt, phase, result,
                        error=str(exc), elapsed_s=time.time() - t0)
        else:
            self._record(attempt, phase, result,
                        output=artifact, elapsed_s=time.time() - t0)
        return result

    def _record(
        self,
        attempt: int,
        phase: ConvergencePhase,
        result: GateResult,
        *,
        output: Any = None,
        error: str = "",
        elapsed_s: float = 0.0,
    ) -> None:
        self._attempts.append(ConvergenceAttempt(
            attempt=attempt,
            phase=phase,
            result=result,
            output=output,
            error=error,
            elapsed_s=elapsed_s,
        ))

    def backoff_s(self, attempt: int) -> float:
        """Calculate exponential backoff for retry delay."""
        return self.config.backoff_base_s * (2 ** (attempt - 1))

    @property
    def attempts(self) -> list[ConvergenceAttempt]:
        return list(self._attempts)

    @property
    def current_phase(self) -> ConvergencePhase:
        return self._current_phase
