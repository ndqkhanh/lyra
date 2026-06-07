"""
Tests for ErrorProbe failure attribution.
"""

from datetime import datetime

import pytest

from src.verification.error_probe import (
    AnomalyDetector,
    BackwardTracer,
    ErrorProbe,
    ExecutionStep,
    FailureType,
    ValidationTeam,
    VerifiedMemoryGate,
)


class TestAnomalyDetector:
    """Test anomaly detection."""

    def test_detect_repeated_errors(self):
        """Test repeated error detection."""
        detector = AnomalyDetector()

        steps = [
            ExecutionStep(
                step_id=f"step-{i}",
                timestamp=datetime.now(),
                action="tool_call",
                input_data={},
                output_data={},
                success=False,
                error=f"Error {i}",
            )
            for i in range(5)
        ]

        anomalies = detector.detect(steps)

        # Should detect repeated errors
        assert len(anomalies) > 0
        assert any(a.anomaly_type == "repeated_errors" for a in anomalies)

    def test_detect_circular_reasoning(self):
        """Test circular reasoning detection."""
        detector = AnomalyDetector()

        steps = [
            ExecutionStep(
                step_id="step-1",
                timestamp=datetime.now(),
                action="reason",
                input_data={"query": "test"},
                output_data={},
                success=True,
            ),
            ExecutionStep(
                step_id="step-2",
                timestamp=datetime.now(),
                action="reason",
                input_data={"query": "test"},
                output_data={},
                success=True,
            ),
        ]

        anomalies = detector.detect(steps)

        # Should detect circular reasoning
        assert any(a.anomaly_type == "circular_reasoning" for a in anomalies)

    def test_detect_memory_inconsistency(self):
        """Test memory inconsistency detection."""
        detector = AnomalyDetector()

        steps = [
            ExecutionStep(
                step_id="step-1",
                timestamp=datetime.now(),
                action="memory_write",
                input_data={"key": "user_id", "value": "123"},
                output_data={},
                success=True,
            ),
            ExecutionStep(
                step_id="step-2",
                timestamp=datetime.now(),
                action="memory_write",
                input_data={"key": "user_id", "value": "456"},
                output_data={},
                success=True,
            ),
        ]

        anomalies = detector.detect(steps)

        # Should detect inconsistency
        assert any(a.anomaly_type == "memory_inconsistency" for a in anomalies)

    def test_detect_tool_failure_cascade(self):
        """Test tool failure cascade detection."""
        detector = AnomalyDetector()

        steps = [
            ExecutionStep(
                step_id=f"step-{i}",
                timestamp=datetime.now(),
                action="tool_call",
                input_data={"tool_name": "bash"},
                output_data={},
                success=False,
                error="Command failed",
            )
            for i in range(3)
        ]

        anomalies = detector.detect(steps)

        # Should detect cascade
        assert any(a.anomaly_type == "tool_failure_cascade" for a in anomalies)


class TestBackwardTracer:
    """Test backward tracing."""

    def test_trace_from_failure(self):
        """Test tracing backward from failure."""
        tracer = BackwardTracer()

        steps = [
            ExecutionStep(
                step_id="step-1",
                timestamp=datetime.now(),
                action="read_file",
                input_data={"path": "test.txt"},
                output_data={"content": "data"},
                success=True,
            ),
            ExecutionStep(
                step_id="step-2",
                timestamp=datetime.now(),
                action="process",
                input_data={"data": "data"},
                output_data={},
                success=False,
                error="Processing failed",
            ),
            ExecutionStep(
                step_id="step-3",
                timestamp=datetime.now(),
                action="write_file",
                input_data={},
                output_data={},
                success=False,
                error="Write failed",
            ),
        ]

        symptoms = tracer.trace(steps, "step-3")

        # Should find step-2 as contributing
        assert len(symptoms) > 0
        assert any("step-2" in s.step_id for s in symptoms)


class TestValidationTeam:
    """Test multi-agent validation."""

    @pytest.mark.asyncio
    async def test_validate_reasoning_error(self):
        """Test validation identifies reasoning errors."""
        team = ValidationTeam()

        steps = []
        anomalies = [
            type(
                "Anomaly",
                (),
                {
                    "anomaly_type": "circular_reasoning",
                    "step_id": "step-1",
                    "confidence": 0.8,
                },
            )()
        ]
        symptoms = []

        attribution = await team.validate(steps, anomalies, symptoms)

        assert attribution.failure_type == FailureType.REASONING_ERROR

    @pytest.mark.asyncio
    async def test_validate_tool_error(self):
        """Test validation identifies tool errors."""
        team = ValidationTeam()

        steps = []
        anomalies = [
            type(
                "Anomaly",
                (),
                {
                    "anomaly_type": "tool_failure_cascade",
                    "step_id": "step-1",
                    "confidence": 0.9,
                },
            )()
        ]
        symptoms = []

        attribution = await team.validate(steps, anomalies, symptoms)

        assert attribution.failure_type == FailureType.TOOL_ERROR


class TestVerifiedMemoryGate:
    """Test verified-before-write memory gate."""

    def test_stage_and_commit(self):
        """Test staging and committing writes."""
        gate = VerifiedMemoryGate()

        # Stage writes
        gate.stage_write("key1", "value1", "step-1")
        gate.stage_write("key2", "value2", "step-2")

        # Verify one
        gate.verify_write("key1", True)
        gate.verify_write("key2", False)

        # Mock memory store
        class MockStore:
            def __init__(self):
                self.data = {}

            def set(self, key, value):
                self.data[key] = value

        store = MockStore()
        committed = gate.commit_writes(store)

        # Only verified write should be committed
        assert committed == 1
        assert "key1" in store.data
        assert "key2" not in store.data

    def test_pending_writes_cleared(self):
        """Test pending writes are cleared after commit."""
        gate = VerifiedMemoryGate()

        gate.stage_write("key1", "value1", "step-1")
        gate.verify_write("key1", True)

        class MockStore:
            def set(self, key, value):
                pass

        store = MockStore()
        gate.commit_writes(store)

        # Pending should be empty
        assert len(gate.pending_writes) == 0


class TestErrorProbe:
    """Test ErrorProbe integration."""

    @pytest.mark.asyncio
    async def test_diagnose_failure(self):
        """Test full failure diagnosis."""
        probe = ErrorProbe()

        steps = [
            ExecutionStep(
                step_id="step-1",
                timestamp=datetime.now(),
                action="tool_call",
                input_data={"tool_name": "bash"},
                output_data={},
                success=False,
                error="Command failed",
            ),
            ExecutionStep(
                step_id="step-2",
                timestamp=datetime.now(),
                action="tool_call",
                input_data={"tool_name": "bash"},
                output_data={},
                success=False,
                error="Command failed again",
            ),
        ]

        attribution = await probe.diagnose(steps)

        assert attribution is not None
        assert attribution.failure_type in [ft for ft in FailureType]
        assert len(attribution.recommendations) > 0

    @pytest.mark.asyncio
    async def test_auto_detect_failure(self):
        """Test auto-detection of failure step."""
        probe = ErrorProbe()

        steps = [
            ExecutionStep(
                step_id="step-1",
                timestamp=datetime.now(),
                action="tool_call",
                input_data={},
                output_data={},
                success=True,
            ),
            ExecutionStep(
                step_id="step-2",
                timestamp=datetime.now(),
                action="tool_call",
                input_data={},
                output_data={},
                success=False,
                error="Failed",
            ),
        ]

        attribution = await probe.diagnose(steps, failure_step=None)

        # Should auto-detect step-2 as failure
        assert attribution.root_cause_step == "step-2" or len(attribution.contributing_steps) > 0

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        probe = ErrorProbe()

        attribution = type(
            "Attribution", (), {"failure_type": FailureType.TOOL_ERROR}
        )()

        recommendations = probe._generate_recommendations(attribution)

        assert len(recommendations) > 0
        assert any("retry" in r.lower() for r in recommendations)
