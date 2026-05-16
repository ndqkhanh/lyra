"""
ReasoningBank-style Experience Memory with Conservative Retrieval.

Learns from successful strategies and avoids negative transfer.
Implements CoPS-style conservative retrieval for high precision.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json


@dataclass
class Strategy:
    """A learned strategy from past experience."""

    strategy_id: str
    description: str
    context: Dict[str, Any]  # When this strategy applies
    actions: List[str]  # What actions to take
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Neutral prior
        return self.success_count / total

    def update_confidence(self):
        """Update confidence based on success rate and sample size."""
        success_rate = self.get_success_rate()
        total = self.success_count + self.failure_count

        # Confidence increases with more samples
        # Use Wilson score interval for confidence
        if total == 0:
            self.confidence = 0.5
        else:
            # Simple confidence: success_rate weighted by sample size
            # More samples = higher confidence
            sample_weight = min(total / 10.0, 1.0)  # Cap at 10 samples
            self.confidence = success_rate * sample_weight + 0.5 * (1 - sample_weight)


@dataclass
class ExperienceRecord:
    """A record of a past experience."""

    record_id: str
    task_description: str
    context: Dict[str, Any]
    strategy_used: str
    outcome: str  # "success" or "failure"
    evidence: List[str]  # Evidence supporting the outcome
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ExperienceMemory:
    """
    ReasoningBank-style experience memory with conservative retrieval.

    Features:
    - Strategy learning from successful experiences
    - Conservative retrieval (CoPS-style) to avoid negative transfer
    - Confidence-based strategy selection
    - Evidence-backed experience records
    """

    def __init__(self, data_dir: str = "./data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.strategies: Dict[str, Strategy] = {}
        self.experiences: List[ExperienceRecord] = []

        # Statistics
        self.stats = {
            "total_experiences": 0,
            "successful_experiences": 0,
            "failed_experiences": 0,
            "strategies_learned": 0,
            "strategies_reused": 0,
        }

        self._load_state()

    def _load_state(self):
        """Load experience memory from disk."""
        state_file = self.data_dir / "experience_memory.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                data = json.load(f)

                # Load strategies
                self.strategies = {
                    sid: Strategy(**sdata)
                    for sid, sdata in data.get("strategies", {}).items()
                }

                # Load experiences
                self.experiences = [
                    ExperienceRecord(**edata)
                    for edata in data.get("experiences", [])
                ]

                # Load stats
                self.stats = data.get("stats", self.stats)

    def _save_state(self):
        """Save experience memory to disk."""
        data = {
            "strategies": {
                sid: {
                    "strategy_id": s.strategy_id,
                    "description": s.description,
                    "context": s.context,
                    "actions": s.actions,
                    "success_count": s.success_count,
                    "failure_count": s.failure_count,
                    "confidence": s.confidence,
                    "created_at": s.created_at,
                    "last_used": s.last_used,
                }
                for sid, s in self.strategies.items()
            },
            "experiences": [
                {
                    "record_id": e.record_id,
                    "task_description": e.task_description,
                    "context": e.context,
                    "strategy_used": e.strategy_used,
                    "outcome": e.outcome,
                    "evidence": e.evidence,
                    "timestamp": e.timestamp,
                }
                for e in self.experiences
            ],
            "stats": self.stats,
        }

        with open(self.data_dir / "experience_memory.json", "w") as f:
            json.dump(data, f, indent=2)

    def add_experience(
        self,
        task_description: str,
        context: Dict[str, Any],
        strategy_used: str,
        outcome: str,
        evidence: List[str]
    ) -> str:
        """
        Add a new experience record.

        Args:
            task_description: Description of the task
            context: Context in which the task was performed
            strategy_used: Strategy ID that was used
            outcome: "success" or "failure"
            evidence: Evidence supporting the outcome

        Returns:
            Record ID
        """
        record = ExperienceRecord(
            record_id=f"exp_{len(self.experiences):06d}",
            task_description=task_description,
            context=context,
            strategy_used=strategy_used,
            outcome=outcome,
            evidence=evidence,
        )

        self.experiences.append(record)

        # Update statistics
        self.stats["total_experiences"] += 1
        if outcome == "success":
            self.stats["successful_experiences"] += 1
        else:
            self.stats["failed_experiences"] += 1

        # Update strategy success/failure counts
        if strategy_used in self.strategies:
            strategy = self.strategies[strategy_used]
            if outcome == "success":
                strategy.success_count += 1
            else:
                strategy.failure_count += 1
            strategy.update_confidence()
            strategy.last_used = datetime.now().isoformat()

        self._save_state()

        return record.record_id

    def learn_strategy(
        self,
        description: str,
        context: Dict[str, Any],
        actions: List[str]
    ) -> str:
        """
        Learn a new strategy from successful experience.

        Args:
            description: Description of the strategy
            context: Context in which this strategy applies
            actions: Actions to take

        Returns:
            Strategy ID
        """
        strategy = Strategy(
            strategy_id=f"strategy_{len(self.strategies):06d}",
            description=description,
            context=context,
            actions=actions,
        )

        self.strategies[strategy.strategy_id] = strategy
        self.stats["strategies_learned"] += 1

        self._save_state()

        return strategy.strategy_id

    def retrieve_strategies(
        self,
        context: Dict[str, Any],
        min_confidence: float = 0.7,
        top_k: int = 3
    ) -> List[Strategy]:
        """
        Conservative retrieval of strategies (CoPS-style).

        Only retrieves high-confidence strategies to avoid negative transfer.

        Args:
            context: Current context
            min_confidence: Minimum confidence threshold (default: 0.7)
            top_k: Maximum number of strategies to return

        Returns:
            List of relevant high-confidence strategies
        """
        # Filter by confidence first (conservative)
        candidates = [
            s for s in self.strategies.values()
            if s.confidence >= min_confidence
        ]

        # Score by context similarity
        scored = []
        for strategy in candidates:
            score = self._compute_context_similarity(context, strategy.context)
            scored.append((score, strategy))

        # Sort by score and take top_k
        scored.sort(reverse=True, key=lambda x: x[0])

        # Update reuse stats
        if scored:
            self.stats["strategies_reused"] += 1
            self._save_state()

        return [s for _, s in scored[:top_k]]

    def _compute_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """
        Compute similarity between two contexts.

        Returns score between 0.0 and 1.0.
        """
        if not context1 or not context2:
            return 0.0

        # Simple keyword-based similarity
        keys1 = set(context1.keys())
        keys2 = set(context2.keys())

        if not keys1 or not keys2:
            return 0.0

        # Jaccard similarity on keys
        intersection = len(keys1 & keys2)
        union = len(keys1 | keys2)

        if union == 0:
            return 0.0

        return intersection / union

    def get_stats(self) -> Dict[str, Any]:
        """Get experience memory statistics."""
        success_rate = (
            self.stats["successful_experiences"] / self.stats["total_experiences"]
            if self.stats["total_experiences"] > 0
            else 0.0
        )

        return {
            **self.stats,
            "success_rate": success_rate,
            "num_strategies": len(self.strategies),
            "num_experiences": len(self.experiences),
        }
