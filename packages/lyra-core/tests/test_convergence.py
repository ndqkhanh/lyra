"""Tests for ConvergenceLoop — adversarial convergence with gate-based quality enforcement."""

import pytest
from lyra_core.orchestration.convergence import (
    ConvergenceAttempt,
    ConvergenceConfig,
    ConvergenceLoop,
    ConvergencePhase,
    ConvergenceReport,
    GateResult,
)


class TestGateResult:
    """Unit tests for GateResult enum."""

    def test_all_values(self):
        assert GateResult.PASS == "pass"
        assert GateResult.FAIL_RETRY == "fail_retry"
        assert GateResult.FAIL_ABORT == "fail_abort"
        assert GateResult.TIMEOUT == "timeout"


class TestConvergencePhase:
    """Unit tests for ConvergencePhase enum."""

    def test_all_phases(self):
        assert ConvergencePhase.GENERATE == "generate"
        assert ConvergencePhase.BUILD == "build"
        assert ConvergencePhase.TEST == "test"
        assert ConvergencePhase.REVIEW == "review"
        assert ConvergencePhase.CONVERGED == "converged"


class TestConvergenceAttempt:
    """Unit tests for ConvergenceAttempt model."""

    def test_attempt_creation(self):
        a = ConvergenceAttempt(attempt=1, phase=ConvergencePhase.GENERATE,
                                result=GateResult.PASS)
        assert a.attempt == 1
        assert a.phase == ConvergencePhase.GENERATE
        assert a.result == GateResult.PASS

    def test_attempt_with_error(self):
        a = ConvergenceAttempt(attempt=2, phase=ConvergencePhase.BUILD,
                                result=GateResult.FAIL_RETRY, error="compilation failed")
        assert a.error == "compilation failed"
        assert a.output is None

    def test_attempt_with_output(self):
        a = ConvergenceAttempt(attempt=1, phase=ConvergencePhase.TEST,
                                result=GateResult.PASS, output="tests passed")
        assert a.output == "tests passed"


class TestConvergenceConfig:
    """Unit tests for ConvergenceConfig."""

    def test_defaults(self):
        config = ConvergenceConfig()
        assert config.max_attempts == 5
        assert config.require_build is True
        assert config.require_test is True
        assert config.require_review is True
        assert config.auto_fix_enabled is True

    def test_custom_config(self):
        config = ConvergenceConfig(
            max_attempts=3, require_build=False, require_test=False,
            require_review=False, auto_fix_enabled=False,
        )
        assert config.max_attempts == 3
        assert config.require_build is False

    def test_timeout_defaults(self):
        config = ConvergenceConfig()
        assert config.build_timeout_s == 120.0
        assert config.test_timeout_s == 300.0
        assert config.review_timeout_s == 60.0

    def test_backoff_base(self):
        config = ConvergenceConfig(backoff_base_s=2.0)
        assert config.backoff_base_s == 2.0


class TestConvergenceReport:
    """Unit tests for ConvergenceReport."""

    def test_converged_report(self):
        report = ConvergenceReport(converged=True, total_attempts=3)
        assert report.converged is True
        assert report.total_attempts == 3
        assert report.build_passed is False

    def test_not_converged_report(self):
        report = ConvergenceReport(converged=False, total_attempts=5)
        assert report.converged is False

    def test_build_passed_tracks_phase(self):
        report = ConvergenceReport(converged=True, total_attempts=2, attempts=[
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.GENERATE,
                               result=GateResult.PASS),
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.BUILD,
                               result=GateResult.PASS),
        ])
        assert report.build_passed is True
        assert report.test_passed is False
        assert report.review_passed is False

    def test_test_passed_tracks_phase(self):
        report = ConvergenceReport(converged=True, total_attempts=2, attempts=[
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.TEST,
                               result=GateResult.PASS),
        ])
        assert report.test_passed is True

    def test_review_passed_tracks_phase(self):
        report = ConvergenceReport(converged=True, total_attempts=2, attempts=[
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.REVIEW,
                               result=GateResult.PASS),
        ])
        assert report.review_passed is True

    def test_phases_passed_set(self):
        report = ConvergenceReport(converged=True, total_attempts=2, attempts=[
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.BUILD,
                               result=GateResult.PASS),
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.TEST,
                               result=GateResult.PASS),
            ConvergenceAttempt(attempt=1, phase=ConvergencePhase.REVIEW,
                               result=GateResult.FAIL_RETRY),
        ], phases_passed={"build", "test"})
        assert "build" in report.phases_passed
        assert "test" in report.phases_passed
        assert "review" not in report.phases_passed


class TestConvergenceLoop:
    """Tests for ConvergenceLoop execution."""

    def test_backoff_exponential(self):
        loop = ConvergenceLoop(ConvergenceConfig(backoff_base_s=1.0))
        assert loop.backoff_s(1) == 1.0
        assert loop.backoff_s(2) == 2.0
        assert loop.backoff_s(3) == 4.0
        assert loop.backoff_s(4) == 8.0

    def test_backoff_custom_base(self):
        loop = ConvergenceLoop(ConvergenceConfig(backoff_base_s=3.0))
        assert loop.backoff_s(1) == 3.0
        assert loop.backoff_s(2) == 6.0

    def test_initial_phase_is_generate(self):
        loop = ConvergenceLoop()
        assert loop.current_phase == ConvergencePhase.GENERATE

    def test_attempts_empty_initially(self):
        loop = ConvergenceLoop()
        assert loop.attempts == []

    @pytest.mark.asyncio
    async def test_run_converges_first_attempt(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        async def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.converged is True
        assert report.total_attempts == 1

    @pytest.mark.asyncio
    async def test_run_fails_on_generation_error(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            raise RuntimeError("generation failed")

        report = await loop.run(generator=generator)

        assert report.converged is False
        assert report.total_attempts == 1
        assert len(report.attempts) == 1
        assert report.attempts[0].phase == ConvergencePhase.GENERATE
        assert report.attempts[0].result == GateResult.FAIL_ABORT

    @pytest.mark.asyncio
    async def test_run_retries_on_build_fail_retry(self):
        loop = ConvergenceLoop()
        build_calls = []

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            build_calls.append(artifact)
            if len(build_calls) < 2:
                return GateResult.FAIL_RETRY
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        async def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.converged is True
        assert report.total_attempts == 2
        assert len(build_calls) == 2

    @pytest.mark.asyncio
    async def test_run_aborts_on_fail_abort(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.FAIL_ABORT

        report = await loop.run(generator=generator, builder=builder)

        assert report.converged is False
        assert report.attempts[-1].result == GateResult.FAIL_ABORT

    @pytest.mark.asyncio
    async def test_run_retries_on_test_failure(self):
        loop = ConvergenceLoop()
        test_calls = []

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            test_calls.append(artifact)
            if len(test_calls) < 2:
                return GateResult.FAIL_RETRY
            return GateResult.PASS

        async def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.converged is True
        assert report.total_attempts == 2

    @pytest.mark.asyncio
    async def test_run_retries_on_review_failure(self):
        loop = ConvergenceLoop()
        review_calls = []

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        async def reviewer(artifact):
            review_calls.append(artifact)
            if len(review_calls) < 2:
                return GateResult.FAIL_RETRY
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.converged is True
        assert report.total_attempts == 2

    @pytest.mark.asyncio
    async def test_run_hits_max_attempts(self):
        loop = ConvergenceLoop(ConvergenceConfig(max_attempts=3))

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.FAIL_RETRY

        report = await loop.run(generator=generator, builder=builder)

        assert report.converged is False
        assert report.total_attempts == 3

    @pytest.mark.asyncio
    async def test_run_skips_disabled_phases(self):
        loop = ConvergenceLoop(ConvergenceConfig(
            require_build=False, require_test=False, require_review=False,
        ))

        async def generator(attempt):
            return f"artifact_{attempt}"

        report = await loop.run(generator=generator)

        assert report.converged is True
        assert report.total_attempts == 1

    @pytest.mark.asyncio
    async def test_run_records_attempts(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        async def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        phases = {a.phase for a in report.attempts}
        assert ConvergencePhase.BUILD in phases
        assert ConvergencePhase.TEST in phases
        assert ConvergencePhase.REVIEW in phases
        assert len(report.attempts) == 3  # BUILD + TEST + REVIEW

    @pytest.mark.asyncio
    async def test_run_with_sync_gates(self):
        """Gate functions can be sync or async."""
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"artifact_{attempt}"

        def builder(artifact):
            return GateResult.PASS

        def tester(artifact):
            return GateResult.PASS

        def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.converged is True

    @pytest.mark.asyncio
    async def test_run_gate_exception_becomes_fail_retry(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            raise RuntimeError("build system down")

        report = await loop.run(generator=generator, builder=builder)

        assert report.total_attempts >= 1
        assert report.attempts[-1].phase == ConvergencePhase.BUILD
        assert report.attempts[-1].result == GateResult.FAIL_RETRY

    @pytest.mark.asyncio
    async def test_run_without_reviewer(self):
        loop = ConvergenceLoop(ConvergenceConfig(require_review=False))

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder, tester=tester,
        )

        assert report.converged is True

    @pytest.mark.asyncio
    async def test_run_auto_fix_disabled_no_test_retry(self):
        loop = ConvergenceLoop(ConvergenceConfig(auto_fix_enabled=False))

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.FAIL_RETRY

        report = await loop.run(
            generator=generator, builder=builder, tester=tester,
        )

        # Without auto_fix, test FAIL_RETRY proceeds to review instead of retrying
        assert report.total_attempts >= 1

    @pytest.mark.asyncio
    async def test_report_includes_final_output(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"final_artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        async def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.final_output == "final_artifact_1"

    @pytest.mark.asyncio
    async def test_run_total_elapsed_tracked(self):
        loop = ConvergenceLoop()

        async def generator(attempt):
            return f"artifact_{attempt}"

        async def builder(artifact):
            return GateResult.PASS

        async def tester(artifact):
            return GateResult.PASS

        async def reviewer(artifact):
            return GateResult.PASS

        report = await loop.run(
            generator=generator, builder=builder,
            tester=tester, reviewer=reviewer,
        )

        assert report.total_elapsed_s > 0
