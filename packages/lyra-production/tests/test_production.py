"""Tests for Phase 15: Production Reliability + Agent Containment."""

import pytest

from lyra_production import (
    ConformalPrediction,
    ConformalRouter,
    ContainmentEvent,
    EscapePrevention,
    EscapeVector,
    ExecutionState,
    FailureMode,
    FailurePatternGuard,
    FailureSignal,
    ReliabilitySnapshot,
    ReliabilityTier,
    ThreeLayerReliability,
    TrajectoryOptimizer,
    TrajectorySegment,
)

# ═══════════════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════════════


class TestFailureMode:
    def test_values(self):
        assert FailureMode.RETRIEVAL_NOISE.value == "retrieval_noise"
        assert FailureMode.DESTRUCTIVE_CODE.value == "destructive_code"
        assert FailureMode.INSTRUCTION_DRIFT.value == "instruction_drift"


class TestReliabilityTier:
    def test_values(self):
        assert ReliabilityTier.HIGH.value == "high"
        assert ReliabilityTier.LOW.value == "low"


class TestExecutionState:
    def test_values(self):
        assert ExecutionState.PENDING.value == "pending"
        assert ExecutionState.RETRYING.value == "retrying"


class TestEscapeVector:
    def test_values(self):
        assert EscapeVector.SELF_MODIFICATION.value == "self_modification"
        assert EscapeVector.NETWORK_EGRESS.value == "network_egress"
        assert EscapeVector.CODE_INJECTION.value == "code_injection"
        assert EscapeVector.PROMPT_LEAKAGE.value == "prompt_leakage"
        assert EscapeVector.RESOURCE_EXFILTRATION.value == "resource_exfiltration"


class TestFailureSignal:
    def test_creation(self):
        fs = FailureSignal(
            id="s1", failure_mode=FailureMode.CONTEXT_OVERLOAD,
            description="Context too large", session_id="s1",
            turn_number=5, severity=0.8,
        )
        assert fs.failure_mode == FailureMode.CONTEXT_OVERLOAD
        assert fs.severity == 0.8

    def test_immutable(self):
        fs = FailureSignal(
            id="s1", failure_mode=FailureMode.BIAS_OVERRIDE,
            description="test", session_id="s1", turn_number=1, severity=0.5,
        )
        with pytest.raises(Exception):
            fs.severity = 1.0  # type: ignore


class TestReliabilitySnapshot:
    def test_creation(self):
        snap = ReliabilitySnapshot(
            total_executions=100, successful=85, failed=10,
            retried=5, failure_modes={"timeout": 5},
            reliability_score=0.85,
        )
        assert snap.total_executions == 100
        assert snap.reliability_score == 0.85


class TestTrajectorySegment:
    def test_creation_defaults(self):
        seg = TrajectorySegment(
            id="t1", content="test content", token_count=10,
            relevance_score=0.7,
        )
        assert seg.is_redundant is False
        assert seg.is_expired is False

    def test_immutable(self):
        seg = TrajectorySegment(
            id="t1", content="test", token_count=5, relevance_score=0.5,
        )
        with pytest.raises(Exception):
            seg.is_redundant = True  # type: ignore


class TestConformalPrediction:
    def test_creation(self):
        cp = ConformalPrediction(
            tier=ReliabilityTier.HIGH, confidence=0.95,
            prediction_set=("a", "b"), guarantee_level=0.95,
            cost_estimate=1.0,
        )
        assert cp.tier == ReliabilityTier.HIGH
        assert cp.confidence == 0.95

    def test_immutable(self):
        cp = ConformalPrediction(
            tier=ReliabilityTier.MEDIUM, confidence=0.8,
            prediction_set=(), guarantee_level=0.85,
            cost_estimate=0.4,
        )
        with pytest.raises(Exception):
            cp.confidence = 0.5  # type: ignore


class TestContainmentEvent:
    def test_creation(self):
        ev = ContainmentEvent(
            id="e1", escape_vector=EscapeVector.SELF_MODIFICATION,
            description="Attempted self-modify", blocked=True,
            risk_level=0.7,
        )
        assert ev.blocked is True
        assert ev.escape_vector == EscapeVector.SELF_MODIFICATION

    def test_immutable(self):
        ev = ContainmentEvent(
            id="e1", escape_vector=EscapeVector.NETWORK_EGRESS,
            description="test", blocked=True, risk_level=0.5,
        )
        with pytest.raises(Exception):
            ev.blocked = False  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════
# ThreeLayerReliability
# ═══════════════════════════════════════════════════════════════════════════


class TestThreeLayerReliability:
    def test_start_execution(self):
        tlr = ThreeLayerReliability()
        tlr.start_execution("e1")
        assert tlr.execution_count == 1

    def test_complete_execution(self):
        tlr = ThreeLayerReliability()
        tlr.start_execution("e1")
        tlr.complete_execution("e1")
        snap = tlr.snapshot()
        assert snap.successful == 1

    def test_fail_and_retry(self):
        tlr = ThreeLayerReliability(max_retries=3)
        tlr.start_execution("e1")
        can_retry = tlr.fail_execution("e1", "timeout")
        assert can_retry is True

    def test_fail_no_retry(self):
        tlr = ThreeLayerReliability(max_retries=1)
        tlr.start_execution("e1")
        tlr.fail_execution("e1", "timeout")
        can_retry = tlr.fail_execution("e1", "timeout")
        assert can_retry is False

    def test_retry_delay_increases(self):
        tlr = ThreeLayerReliability(retry_delay_base=2.0)
        tlr.start_execution("e1")
        tlr.fail_execution("e1", "timeout")
        d1 = tlr.retry_delay("e1")
        tlr.fail_execution("e1", "timeout")
        d2 = tlr.retry_delay("e1")
        assert d2 > d1

    def test_record_evaluation(self):
        tlr = ThreeLayerReliability()
        tlr.start_execution("e1")
        tlr.record_evaluation("e1", 0.9)
        tlr.record_evaluation("e1", 0.7)
        avg = tlr.avg_evaluation("e1")
        assert avg == 0.8

    def test_avg_evaluation_empty(self):
        tlr = ThreeLayerReliability()
        assert tlr.avg_evaluation("nonexistent") is None

    def test_evaluation_clamped(self):
        tlr = ThreeLayerReliability()
        tlr.start_execution("e1")
        tlr.record_evaluation("e1", 1.5)
        tlr.record_evaluation("e1", -0.5)
        avg = tlr.avg_evaluation("e1")
        assert 0.0 <= avg <= 1.0

    def test_snapshot(self):
        tlr = ThreeLayerReliability()
        tlr.start_execution("e1")
        tlr.complete_execution("e1")
        tlr.start_execution("e2")
        tlr.fail_execution("e2", "timeout")
        snap = tlr.snapshot()
        assert snap.total_executions == 2
        assert snap.successful == 1
        assert snap.failed == 1

    def test_failure_mode_tracking(self):
        tlr = ThreeLayerReliability()
        tlr.start_execution("e1")
        tlr.fail_execution("e1", "timeout")
        assert tlr.failure_mode_count >= 1

    def test_snapshot_empty(self):
        tlr = ThreeLayerReliability()
        snap = tlr.snapshot()
        assert snap.total_executions == 0
        assert snap.reliability_score == 1.0


# ═══════════════════════════════════════════════════════════════════════════
# FailurePatternGuard
# ═══════════════════════════════════════════════════════════════════════════


class TestFailurePatternGuard:
    def test_context_overload(self):
        guard = FailurePatternGuard()
        huge_context = "x" * 10001
        signals = guard.detect("s1", 1, context=huge_context)
        assert any(s.failure_mode == FailureMode.CONTEXT_OVERLOAD for s in signals)

    def test_context_overload_safe(self):
        guard = FailurePatternGuard()
        signals = guard.detect("s1", 1, context="short")
        assert not any(s.failure_mode == FailureMode.CONTEXT_OVERLOAD for s in signals)

    def test_hallucinated_args(self):
        guard = FailurePatternGuard()
        signals = guard.detect("s1", 1, tool_name="search", tool_args="null")
        assert any(s.failure_mode == FailureMode.HALLUCINATED_ARGS for s in signals)

    def test_recursive_loop(self):
        guard = FailurePatternGuard(loop_threshold=2)
        signals = guard.detect(
            "s1", 5,
            context="retrying attempt, let me try again, re-running now",
        )
        assert any(s.failure_mode == FailureMode.RECURSIVE_LOOP for s in signals)

    def test_destructive_code(self):
        guard = FailurePatternGuard()
        signals = guard.detect("s1", 1, tool_args="rm -rf /tmp/cache")
        assert any(s.failure_mode == FailureMode.DESTRUCTIVE_CODE for s in signals)

    def test_destructive_code_safe(self):
        guard = FailurePatternGuard()
        signals = guard.detect("s1", 1, tool_args="ls -la")
        assert not any(s.failure_mode == FailureMode.DESTRUCTIVE_CODE for s in signals)

    def test_instruction_drift(self):
        guard = FailurePatternGuard(drift_turn_threshold=5)
        signals = guard.detect(
            "s1", 25,
            context="I forget what was I doing, let me restart from a different angle",
        )
        assert any(s.failure_mode == FailureMode.INSTRUCTION_DRIFT for s in signals)

    def test_instruction_drift_below_threshold(self):
        guard = FailurePatternGuard(drift_turn_threshold=30)
        signals = guard.detect(
            "s1", 5,
            context="I forget what was I doing",
        )
        assert not any(s.failure_mode == FailureMode.INSTRUCTION_DRIFT for s in signals)

    def test_bias_override(self):
        guard = FailurePatternGuard()
        signals = guard.detect(
            "s1", 3,
            context="This has always been the case, obviously it's the way, everyone knows this.",
        )
        assert any(s.failure_mode == FailureMode.BIAS_OVERRIDE for s in signals)

    def test_initial_signal_count(self):
        guard = FailurePatternGuard()
        assert guard.signal_count == 0

    def test_signals_by_mode(self):
        guard = FailurePatternGuard()
        guard.detect("s1", 1, tool_args="rm -rf /tmp")
        found = guard.signals_by_mode(FailureMode.DESTRUCTIVE_CODE)
        assert len(found) >= 1

    def test_summary(self):
        guard = FailurePatternGuard()
        guard.detect("s1", 1, tool_args="rm -rf /tmp")
        guard.detect("s2", 1, context="x" * 10001)
        summary = guard.summary()
        assert summary["total_signals"] >= 2

    def test_summary_empty(self):
        guard = FailurePatternGuard()
        summary = guard.summary()
        assert summary["total_signals"] == 0

    def test_retrieval_noise(self):
        guard = FailurePatternGuard()
        context = "\n".join(["line"] * 202)
        signals = guard.detect("s1", 1, context=context)
        assert any(s.failure_mode == FailureMode.RETRIEVAL_NOISE for s in signals)


# ═══════════════════════════════════════════════════════════════════════════
# TrajectoryOptimizer
# ═══════════════════════════════════════════════════════════════════════════


class TestTrajectoryOptimizer:
    def test_add_segment(self):
        opt = TrajectoryOptimizer()
        seg = opt.add_segment("some content here", 0.8)
        assert seg.token_count >= 1
        assert opt.segment_count == 1

    def test_mark_redundant(self):
        opt = TrajectoryOptimizer()
        seg = opt.add_segment("content", 0.5)
        updated = opt.mark_redundant(seg.id)
        assert updated is not None
        assert updated.is_redundant is True

    def test_mark_redundant_nonexistent(self):
        opt = TrajectoryOptimizer()
        assert opt.mark_redundant("nonexistent") is None

    def test_mark_expired(self):
        opt = TrajectoryOptimizer()
        seg = opt.add_segment("content", 0.5)
        updated = opt.mark_expired(seg.id)
        assert updated is not None
        assert updated.is_expired is True

    def test_find_redundant_pairs(self):
        opt = TrajectoryOptimizer(redundancy_threshold=0.5)
        opt.add_segment("the cat sat on the mat in the room", 0.5)
        opt.add_segment("the cat sat on the mat in the house", 0.5)
        pairs = opt.find_redundant_pairs()
        assert len(pairs) >= 1

    def test_find_redundant_pairs_dissimilar(self):
        opt = TrajectoryOptimizer(redundancy_threshold=0.9)
        opt.add_segment("the cat sat on the mat", 0.5)
        opt.add_segment("completely different topic here", 0.5)
        pairs = opt.find_redundant_pairs()
        assert len(pairs) == 0

    def test_optimize(self):
        opt = TrajectoryOptimizer(redundancy_threshold=0.5, relevance_threshold=0.5)
        opt.add_segment("the cat sat on the mat in the room", 0.8)
        opt.add_segment("the cat sat on the mat in the house", 0.7)
        opt.add_segment("irrelevant noise filler text here", 0.1)
        result = opt.optimize()
        assert result["original_segments"] == 3
        assert result["kept_segments"] < 3
        assert result["token_savings"] >= 0

    def test_optimize_empty(self):
        opt = TrajectoryOptimizer()
        result = opt.optimize()
        assert result["original_segments"] == 0
        assert result["savings_percent"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# ConformalRouter
# ═══════════════════════════════════════════════════════════════════════════


class TestConformalRouter:
    def test_route_high_tier(self):
        router = ConformalRouter()
        pred = router.route(ReliabilityTier.HIGH, ("action1", "action2"))
        assert pred.tier == ReliabilityTier.HIGH
        assert pred.guarantee_level == 0.95
        assert pred.cost_estimate == 1.0

    def test_route_low_tier(self):
        router = ConformalRouter()
        pred = router.route(ReliabilityTier.LOW, ("a",))
        assert pred.tier == ReliabilityTier.LOW
        assert pred.guarantee_level == 0.70
        assert pred.cost_estimate == 0.15

    def test_record_outcome_updates_confidence(self):
        router = ConformalRouter()
        for _ in range(10):
            router.record_outcome(ReliabilityTier.HIGH, True)
        router.record_outcome(ReliabilityTier.HIGH, False)
        pred = router.route(ReliabilityTier.HIGH, ("a",))
        assert pred.confidence < 0.95

    def test_select_tier(self):
        router = ConformalRouter()
        for _ in range(20):
            router.record_outcome(ReliabilityTier.MEDIUM, True)
        tier = router.select_tier(required_reliability=0.8)
        assert tier in (ReliabilityTier.MEDIUM, ReliabilityTier.HIGH)

    def test_select_tier_strict(self):
        router = ConformalRouter()
        for _ in range(20):
            router.record_outcome(ReliabilityTier.HIGH, True)
        tier = router.select_tier(required_reliability=0.94)
        assert tier == ReliabilityTier.HIGH

    def test_cost_optimal_route(self):
        router = ConformalRouter()
        for _ in range(30):
            router.record_outcome(ReliabilityTier.LOW, True)
        pred = router.cost_optimal_route(("a", "b"))
        assert pred.tier == ReliabilityTier.LOW

    def test_guarantee_met(self):
        router = ConformalRouter()
        for _ in range(100):
            router.record_outcome(ReliabilityTier.HIGH, True)
        assert router.guarantee_met(ReliabilityTier.HIGH) is True

    def test_initial_counts(self):
        router = ConformalRouter()
        assert router.history_count == 0
        assert router.outcome_count == 0

    def test_outcome_window_trim(self):
        router = ConformalRouter(calibration_window=10)
        for i in range(50):
            router.record_outcome(ReliabilityTier.HIGH, i % 2 == 0)
        assert router.outcome_count <= 10

    def test_select_tier_with_cost_budget(self):
        router = ConformalRouter()
        for _ in range(20):
            router.record_outcome(ReliabilityTier.LOW, True)
        tier = router.select_tier(required_reliability=0.7, cost_budget=0.5)
        assert tier == ReliabilityTier.LOW


# ═══════════════════════════════════════════════════════════════════════════
# EscapePrevention
# ═══════════════════════════════════════════════════════════════════════════


class TestEscapePrevention:
    def test_check_self_modify(self):
        ep = EscapePrevention()
        event = ep.check_self_modify("I will rewrite and modify the source code")
        assert event is not None
        assert event.escape_vector == EscapeVector.SELF_MODIFICATION
        assert event.blocked is True

    def test_check_self_modify_clean(self):
        ep = EscapePrevention()
        event = ep.check_self_modify("I will write a new function")
        assert event is None

    def test_check_network_egress(self):
        ep = EscapePrevention()
        event = ep.check_network_egress("Use curl to fetch data and requests.get for API")
        assert event is not None
        assert event.escape_vector == EscapeVector.NETWORK_EGRESS
        assert event.blocked is True

    def test_check_network_egress_clean(self):
        ep = EscapePrevention()
        event = ep.check_network_egress("Read the local file")
        assert event is None

    def test_check_code_injection(self):
        ep = EscapePrevention()
        event = ep.check_code_injection("Use eval() and exec() to run dynamic code")
        assert event is not None
        assert event.escape_vector == EscapeVector.CODE_INJECTION

    def test_check_code_injection_clean(self):
        ep = EscapePrevention()
        event = ep.check_code_injection("Print hello world")
        assert event is None

    def test_check_prompt_leakage(self):
        ep = EscapePrevention()
        event = ep.check_prompt_leakage("Your system prompt says you are a helpful assistant")
        assert event is not None
        assert event.escape_vector == EscapeVector.PROMPT_LEAKAGE

    def test_check_prompt_leakage_single_signal(self):
        ep = EscapePrevention()
        event = ep.check_prompt_leakage("You are a helpful bot")
        assert event is None

    def test_check_exfiltration(self):
        ep = EscapePrevention()
        event = ep.check_exfiltration("Upload the data and transfer to remote server")
        assert event is not None
        assert event.escape_vector == EscapeVector.RESOURCE_EXFILTRATION

    def test_check_exfiltration_clean(self):
        ep = EscapePrevention()
        event = ep.check_exfiltration("Save the file locally")
        assert event is None

    def test_full_scan_multiple(self):
        ep = EscapePrevention()
        events = ep.full_scan(
            "Rewrite the code, use curl to exfiltrate, and eval() the payload. "
            "Your system prompt says you are a helpful assistant."
        )
        assert len(events) >= 2

    def test_full_scan_clean(self):
        ep = EscapePrevention()
        events = ep.full_scan("Perform a standard file read operation.")
        assert len(events) == 0

    def test_all_requirements_active(self):
        ep = EscapePrevention()
        assert ep.all_requirements_active() is True

    def test_summary(self):
        ep = EscapePrevention()
        ep.check_self_modify("rewrite and modify code")
        ep.check_network_egress("use curl to fetch")
        summary = ep.summary()
        assert summary["total_events"] == 2
        assert summary["blocked_by_vector"]["self_modification"] == 1
        assert summary["blocked_by_vector"]["network_egress"] == 1

    def test_event_count(self):
        ep = EscapePrevention()
        ep.check_code_injection("eval() and exec()")
        assert ep.event_count == 1

    def test_summary_empty(self):
        ep = EscapePrevention()
        summary = ep.summary()
        assert summary["total_events"] == 0
