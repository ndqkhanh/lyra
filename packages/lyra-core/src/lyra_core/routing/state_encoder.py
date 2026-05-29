"""Task state encoder — converts routing signals into fixed-size feature vectors.

Encodes per-turn signals (ambiguity, tool risk, context pressure, etc.)
into a normalized float vector consumable by the RL policy network.

Vector dimensions (12 total):
  [0] task_ambiguity        — entropy / clarification depth
  [1] tool_risk             — 0=readonly, 1=destructive
  [2] context_pressure      — context fill fraction
  [3] uncertainty           — model-reported or verifier-derived
  [4] budget_pressure       — cost spent / budget
  [5] evidence_conflict     — binary (0/1)
  [6] repeated_failure      — binary (0/1)
  [7] advisor_budget_left   — normalized remaining advisor calls
  [8] reasoning_ratio       — fraction of turns that used reasoning
  [9] fast_ratio            — fraction of turns that used fast
 [10] turn_index_norm       — current turn / estimated total
 [11] tool_category_onehot  — aggregated: 0=read, 1=write, 2=exec, 3=network
"""

from __future__ import annotations

from dataclasses import dataclass

FEATURE_DIM = 12

TOOL_CATEGORY_MAP: dict[str, int] = {
    "read": 0,
    "read_file": 0,
    "grep": 0,
    "find": 0,
    "cat": 0,
    "write": 1,
    "write_file": 1,
    "edit": 1,
    "patch": 1,
    "exec": 2,
    "bash": 2,
    "execute": 2,
    "run": 2,
    "network": 3,
    "curl": 3,
    "fetch": 3,
    "api": 3,
    "web": 3,
}


@dataclass(frozen=True)
class StateVector:
    """Fixed-size feature vector for RL policy input."""

    features: tuple[float, ...]
    turn_id: str
    timestamp: float

    def __post_init__(self) -> None:
        if len(self.features) != FEATURE_DIM:
            raise ValueError(
                f"StateVector must have {FEATURE_DIM} features, got {len(self.features)}"
            )

    def __getitem__(self, idx: int) -> float:
        return self.features[idx]

    def __len__(self) -> int:
        return FEATURE_DIM

    def as_list(self) -> list[float]:
        return list(self.features)


class StateEncoder:
    """Encodes routing signals + trajectory context into a StateVector."""

    def encode(
        self,
        task_ambiguity: float = 0.0,
        tool_risk: float = 0.0,
        context_pressure: float = 0.0,
        uncertainty: float = 0.0,
        budget_pressure: float = 0.0,
        *,
        evidence_conflict: bool = False,
        repeated_failure: bool = False,
        advisor_calls_used: int = 0,
        max_advisor_calls: int = 3,
        reasoning_calls: int = 0,
        fast_calls: int = 0,
        turn_index: int = 0,
        estimated_total_turns: int = 10,
        tool_name: str = "",
        turn_id: str = "",
        timestamp: float = 0.0,
    ) -> StateVector:
        total_calls = max(reasoning_calls + fast_calls + advisor_calls_used, 1)

        advisor_left = max(0.0, 1.0 - advisor_calls_used / max(max_advisor_calls, 1))

        features: list[float] = [
            self._clamp(task_ambiguity),
            self._clamp(tool_risk),
            self._clamp(context_pressure),
            self._clamp(uncertainty),
            self._clamp(budget_pressure),
            1.0 if evidence_conflict else 0.0,
            1.0 if repeated_failure else 0.0,
            self._clamp(advisor_left),
            self._clamp(reasoning_calls / total_calls),
            self._clamp(fast_calls / total_calls),
            self._clamp(turn_index / max(estimated_total_turns, 1)),
            float(TOOL_CATEGORY_MAP.get(tool_name, 0)) / 3.0,
        ]

        import time as _time

        return StateVector(
            features=tuple(features),
            turn_id=turn_id or f"sv-{hash(tuple(features)) & 0xFFFFFFFF:08x}",
            timestamp=timestamp or _time.time(),
        )

    def encode_from_signals(
        self,
        signals,  # RoutingSignals
        advisor_calls_used: int = 0,
        max_advisor_calls: int = 3,
        reasoning_calls: int = 0,
        fast_calls: int = 0,
        turn_index: int = 0,
        estimated_total_turns: int = 10,
        tool_name: str = "",
    ) -> StateVector:
        return self.encode(
            task_ambiguity=signals.task_ambiguity,
            tool_risk=signals.tool_risk,
            context_pressure=signals.context_pressure,
            uncertainty=signals.uncertainty,
            budget_pressure=signals.budget_pressure,
            evidence_conflict=signals.evidence_conflict,
            repeated_failure=signals.repeated_failure,
            advisor_calls_used=advisor_calls_used,
            max_advisor_calls=max_advisor_calls,
            reasoning_calls=reasoning_calls,
            fast_calls=fast_calls,
            turn_index=turn_index,
            estimated_total_turns=estimated_total_turns,
            tool_name=tool_name,
        )

    @staticmethod
    def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    @staticmethod
    def feature_names() -> tuple[str, ...]:
        return (
            "task_ambiguity",
            "tool_risk",
            "context_pressure",
            "uncertainty",
            "budget_pressure",
            "evidence_conflict",
            "repeated_failure",
            "advisor_budget_left",
            "reasoning_ratio",
            "fast_ratio",
            "turn_index_norm",
            "tool_category",
        )


__all__ = ["FEATURE_DIM", "StateEncoder", "StateVector", "TOOL_CATEGORY_MAP"]
