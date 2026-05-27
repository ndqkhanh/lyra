"""Two-Circuit Architecture Bridge (Plan 33).

Separates Lyra into:
- Hot Path (latency-critical): current agent loop with auto-fanout,
  stagnation-stop, canary token checks. Synchronous, real-time.
- Cold Path (improvement-critical): AlphaEvolve loop, SkillOpt,
  AEvo meta-editing, cross-model review. Async, batch, high-latency.

The TwoCircuitBridge manages validated skill documents flowing from
Cold Path → Hot Path at next session start.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class CircuitMode(Enum):
    HOT = auto()
    COLD = auto()
    BRIDGE = auto()


class ImprovementStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"


@dataclass
class ColdPathResult:
    """Result of a Cold Path improvement run."""

    improvement_id: str
    skill_name: str
    original_text: str
    improved_text: str
    score_delta: float
    review_rounds: int
    status: ImprovementStatus = ImprovementStatus.PENDING
    validation_notes: str = ""


@dataclass
class HotPathConfig:
    """Configuration loaded by the Hot Path at session start."""

    system_prompt: str = ""
    canary_token: str = ""
    skill_overrides: dict[str, str] = field(default_factory=dict)
    stagnation_threshold: int = 3
    fanout_max: int = 5
    approved_improvements: list[str] = field(default_factory=list)


class TwoCircuitBridge:
    """Bridge between Hot Path (production) and Cold Path (evolution).

    Cold Path writes validated improvements → Bridge gates them →
    Hot Path loads them at next session start.

    The bridge enforces that only cross-model-reviewed improvements
    flow from Cold→Hot, preventing regressions.
    """

    def __init__(self, review_required: bool = True, max_review_rounds: int = 3) -> None:
        self.review_required = review_required
        self.max_review_rounds = max_review_rounds
        self._pending: dict[str, ColdPathResult] = {}
        self._approved: dict[str, ColdPathResult] = {}
        self._rejected: dict[str, ColdPathResult] = {}
        self._deployed: dict[str, ColdPathResult] = {}

    def submit_cold_path_result(self, result: ColdPathResult) -> str:
        """Submit a Cold Path improvement for review."""
        self._pending[result.improvement_id] = result
        result.status = ImprovementStatus.PENDING
        logger.info("Cold Path improvement submitted: %s (Δ=%.2f)", result.improvement_id, result.score_delta)
        return result.improvement_id

    async def review(
        self,
        result_id: str,
        review_fn,  # async callable(ColdPathResult) -> tuple[bool, str]
    ) -> ImprovementStatus:
        """Gate a pending improvement through cross-model review.

        Returns the final status after review (max self.max_review_rounds rounds).
        """
        result = self._pending.get(result_id)
        if result is None:
            raise KeyError(f"Unknown improvement: {result_id}")

        if not self.review_required:
            self._approved[result_id] = result
            result.status = ImprovementStatus.APPROVED
            del self._pending[result_id]
            return ImprovementStatus.APPROVED

        result.status = ImprovementStatus.IN_REVIEW

        for round_num in range(self.max_review_rounds):
            approved, notes = await review_fn(result)
            result.validation_notes = notes
            result.review_rounds = round_num + 1

            if approved:
                self._approved[result_id] = result
                result.status = ImprovementStatus.APPROVED
                del self._pending[result_id]
                logger.info("Improvement %s approved after %d rounds", result_id, round_num + 1)
                return ImprovementStatus.APPROVED

        self._rejected[result_id] = result
        result.status = ImprovementStatus.REJECTED
        del self._pending[result_id]
        logger.warning("Improvement %s rejected after %d rounds", result_id, self.max_review_rounds)
        return ImprovementStatus.REJECTED

    def get_hot_path_config(self) -> HotPathConfig:
        """Build Hot Path configuration from all approved improvements."""
        skill_overrides: dict[str, str] = {}
        approved_ids: list[str] = []

        for imp_id, result in self._approved.items():
            skill_overrides[result.skill_name] = result.improved_text
            approved_ids.append(imp_id)

        return HotPathConfig(
            skill_overrides=skill_overrides,
            approved_improvements=approved_ids,
        )

    def deploy_approved(self) -> list[str]:
        """Move all approved improvements to deployed state."""
        deployed_ids: list[str] = []
        for imp_id, result in list(self._approved.items()):
            self._deployed[imp_id] = result
            result.status = ImprovementStatus.DEPLOYED
            deployed_ids.append(imp_id)
            del self._approved[imp_id]
        logger.info("Deployed %d improvements to Hot Path", len(deployed_ids))
        return deployed_ids

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def approved_count(self) -> int:
        return len(self._approved)

    @property
    def rejected_count(self) -> int:
        return len(self._rejected)

    @property
    def deployed_count(self) -> int:
        return len(self._deployed)

    def summary(self) -> dict[str, int]:
        return {
            "pending": self.pending_count,
            "approved": self.approved_count,
            "rejected": self.rejected_count,
            "deployed": self.deployed_count,
        }
