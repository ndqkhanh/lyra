"""Tests for the RL routing state encoder."""
from __future__ import annotations

import pytest

from lyra_core.routing.policy import RoutingSignals
from lyra_core.routing.state_encoder import (
    FEATURE_DIM,
    TOOL_CATEGORY_MAP,
    StateEncoder,
    StateVector,
)


class TestStateVector:
    def test_creates_with_correct_dimension(self):
        features = tuple(float(i) for i in range(FEATURE_DIM))
        sv = StateVector(features=features, turn_id="test", timestamp=100.0)
        assert len(sv) == FEATURE_DIM

    def test_rejects_wrong_dimension(self):
        with pytest.raises(ValueError, match="must have 12"):
            StateVector(features=(0.0, 0.5), turn_id="test", timestamp=100.0)

    def test_getitem(self):
        features = tuple(float(i) for i in range(FEATURE_DIM))
        sv = StateVector(features=features, turn_id="test", timestamp=100.0)
        assert sv[0] == 0.0
        assert sv[11] == 11.0

    def test_as_list(self):
        features = tuple(float(i) for i in range(FEATURE_DIM))
        sv = StateVector(features=features, turn_id="test", timestamp=100.0)
        result = sv.as_list()
        assert isinstance(result, list)
        assert result == list(features)

    def test_frozen(self):
        features = tuple(float(i) for i in range(FEATURE_DIM))
        sv = StateVector(features=features, turn_id="test", timestamp=100.0)
        with pytest.raises(Exception):
            sv.features = (0.0,) * FEATURE_DIM  # type: ignore[misc]


class TestStateEncoder:
    def test_encode_defaults(self):
        encoder = StateEncoder()
        sv = encoder.encode()
        assert len(sv) == FEATURE_DIM
        assert all(0.0 <= v <= 1.0 for v in sv.features)

    def test_clamping(self):
        encoder = StateEncoder()
        sv = encoder.encode(
            task_ambiguity=1.5,
            tool_risk=-0.5,
        )
        assert sv[0] == 1.0
        assert sv[1] == 0.0

    def test_evidence_conflict_encoded_as_binary(self):
        encoder = StateEncoder()
        sv_t = encoder.encode(evidence_conflict=True)
        sv_f = encoder.encode(evidence_conflict=False)
        assert sv_t[5] == 1.0
        assert sv_f[5] == 0.0

    def test_repeated_failure_encoded_as_binary(self):
        encoder = StateEncoder()
        sv_t = encoder.encode(repeated_failure=True)
        sv_f = encoder.encode(repeated_failure=False)
        assert sv_t[6] == 1.0
        assert sv_f[6] == 0.0

    def test_advisor_budget_left(self):
        encoder = StateEncoder()
        sv = encoder.encode(advisor_calls_used=2, max_advisor_calls=4)
        assert sv[7] == 0.5

    def test_turn_index_normalized(self):
        encoder = StateEncoder()
        sv = encoder.encode(turn_index=4, estimated_total_turns=8)
        assert sv[10] == 0.5

    def test_tool_category_mapped(self):
        encoder = StateEncoder()
        sv_read = encoder.encode(tool_name="read_file")
        sv_write = encoder.encode(tool_name="write_file")
        sv_exec = encoder.encode(tool_name="bash")
        sv_network = encoder.encode(tool_name="curl")
        assert sv_read[11] == 0.0
        assert sv_write[11] > 0.0
        assert sv_exec[11] > 0.0
        assert sv_network[11] == 1.0

    def test_unknown_tool_defaults_zero(self):
        encoder = StateEncoder()
        sv = encoder.encode(tool_name="unknown_tool_xyz")
        assert sv[11] == 0.0

    def test_encode_from_signals(self):
        encoder = StateEncoder()
        signals = RoutingSignals(
            task_ambiguity=0.3,
            evidence_conflict=True,
            tool_risk=0.5,
            context_pressure=0.7,
            uncertainty=0.2,
            repeated_failure=False,
            budget_pressure=0.4,
        )
        sv = encoder.encode_from_signals(signals, turn_index=1)
        assert sv[0] == 0.3
        assert sv[1] == 0.5
        assert sv[2] == 0.7
        assert sv[3] == 0.2
        assert sv[4] == 0.4
        assert sv[5] == 1.0
        assert sv[6] == 0.0

    def test_unique_turn_ids(self):
        encoder = StateEncoder()
        sv1 = encoder.encode(turn_index=0)
        sv2 = encoder.encode(turn_index=1)
        assert sv1.turn_id != sv2.turn_id

    def test_feature_names(self):
        names = StateEncoder.feature_names()
        assert len(names) == FEATURE_DIM
        assert names[0] == "task_ambiguity"
        assert names[11] == "tool_category"


class TestToolCategoryMap:
    def test_all_known_tools_have_category(self):
        for tool, cat in TOOL_CATEGORY_MAP.items():
            assert 0 <= cat <= 3


class TestFeatureDim:
    def test_feature_dim_is_12(self):
        assert FEATURE_DIM == 12
