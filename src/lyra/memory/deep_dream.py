"""
Deep Dream — advanced dream analysis, persistent cross-session storage,
warm-up scheduling, and Conway-like memory life cycles.

Extends the base DreamEngine with:

    - DeepDreamObserver: Advanced dream analysis with quality metrics,
      anomaly detection, and trend tracking.
    - MemoryFilesIntegration: Persistent cross-session dream storage to
      the filesystem (JSON/YAML files on disk).
    - WarmUpScheduler: Schedule dreams during idle periods using an
      adaptive timer that learns from usage patterns.
    - ConwayCycle: Conway-like memory life cycle simulation where
      memories evolve through generations (birth, growth, reproduction,
      death).
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from lyra.memory.dream_engine import (
    DreamAction,
    DreamBank,
    DreamEngine,
    DreamEntry,
)
from lyra.memory.memory_store import Memory, MemoryType

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_DREAM_STORAGE_DIR: str = ".lyra/dreams"
DEFAULT_OBSERVER_WINDOW: int = 50        # entries in sliding window
DEFAULT_WARMUP_INTERVAL: float = 60.0    # seconds
DEFAULT_MAX_WARMUP_INTERVAL: float = 3600.0  # 1 hour
DEFAULT_CONWAY_GRID_SIZE: int = 10
DEFAULT_CONWAY_GENERATIONS: int = 100


# =============================================================================
# DeepDreamObserver
# =============================================================================


class DreamQuality(Enum):
    """Quality classification for a dream cycle."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FAILED = "failed"


@dataclass
class DreamObservation:
    """A single observation from analyzing a dream cycle.

    Attributes:
        observation_id: Unique identifier.
        dream_bank_id: ID of the analyzed DreamBank.
        quality: Overall quality classification.
        quality_score: Numeric quality score (0.0 - 1.0).
        anomaly_score: Anomaly detection score (0.0 = normal, 1.0 = anomalous).
        pattern_trends: List of detected trend descriptions.
        recommendations: List of recommended actions.
        timestamp: When this observation was made.
    """

    observation_id: str
    dream_bank_id: str
    quality: DreamQuality
    quality_score: float
    anomaly_score: float
    pattern_trends: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class DeepDreamObserver:
    """Advanced dream analysis with quality metrics and anomaly detection.

    Observes dream cycles and produces structured observations with
    quality scores, trend analysis, and actionable recommendations.

    Attributes:
        observation_window: Number of recent observations to track.
    """

    def __init__(self, observation_window: int = DEFAULT_OBSERVER_WINDOW) -> None:
        self.observation_window = observation_window
        self._observations: list[DreamObservation] = []
        self._listeners: list[Callable[[DreamObservation], None]] = []

    # ------------------------------------------------------------------
    # Observation lifecycle
    # ------------------------------------------------------------------

    def observe(self, bank: DreamBank) -> DreamObservation:
        """Analyze a DreamBank and produce an observation.

        Args:
            bank: The DreamBank to analyze.

        Returns:
            A DreamObservation with quality metrics.
        """
        obs_id = str(uuid.uuid4())
        now = time.time()

        # Compute quality score
        quality_score = self._compute_quality_score(bank)
        quality = self._classify_quality(quality_score)

        # Anomaly detection
        anomaly_score = self._detect_anomalies(bank)

        # Trend analysis
        trends = self._analyze_trends(bank)

        # Recommendations
        recommendations = self._generate_recommendations(bank, quality_score, anomaly_score)

        observation = DreamObservation(
            observation_id=obs_id,
            dream_bank_id=bank.bank_id,
            quality=quality,
            quality_score=quality_score,
            anomaly_score=anomaly_score,
            pattern_trends=trends,
            recommendations=recommendations,
            timestamp=now,
            metadata={
                "entry_count": len(bank.entries),
                "scanned_memories": bank.session_sources,
                "dream_cycle": bank.metadata.get("dream_cycle", -1),
            },
        )

        self._observations.append(observation)
        if len(self._observations) > self.observation_window:
            self._observations.pop(0)

        # Fire listeners
        for listener in self._listeners:
            try:
                listener(observation)
            except Exception as e:
                logger.warning("DeepDreamObserver: listener error: %s", e)

        logger.info(
            "DeepDreamObserver: bank=%s quality=%s score=%.2f anomaly=%.2f",
            bank.bank_id, quality.value, quality_score, anomaly_score,
        )

        return observation

    def on_observation(self, listener: Callable[[DreamObservation], None]) -> None:
        """Register a listener called when a new observation is made.

        Args:
            listener: Callable(observation).
        """
        self._listeners.append(listener)

    # ------------------------------------------------------------------
    # Quality computation
    # ------------------------------------------------------------------

    def _compute_quality_score(self, bank: DreamBank) -> float:
        """Compute an overall quality score for a dream bank.

        Factors:
            - Diversity of action types (more = better).
            - Number of entries relative to scanned sources.
            - Confidence scores of entries.
            - Entry importance distribution.

        Returns:
            Score from 0.0 (worst) to 1.0 (best).
        """
        if not bank.entries:
            return 0.0

        scores: list[float] = []

        # Factor 1: Action diversity (up to 0.3)
        action_types = set(e.action for e in bank.entries)
        diversity = len(action_types) / len(DreamAction)
        scores.append(diversity * 0.3)

        # Factor 2: Entry-to-source ratio (up to 0.2)
        if bank.session_sources > 0:
            ratio = min(1.0, len(bank.entries) / max(1, bank.session_sources))
            # Lower ratio with meaningful entries = better
            if ratio < 0.3:
                scores.append(0.2)  # efficient
            elif ratio < 0.6:
                scores.append(0.15)
            else:
                scores.append(0.05)
        else:
            scores.append(0.0)

        # Factor 3: Average confidence (up to 0.3)
        avg_confidence = sum(e.confidence for e in bank.entries) / len(bank.entries)
        scores.append(avg_confidence * 0.3)

        # Factor 4: Importance distribution (up to 0.2)
        high_imp = sum(1 for e in bank.entries if e.importance >= 0.7)
        imp_ratio = high_imp / len(bank.entries) if bank.entries else 0
        scores.append(imp_ratio * 0.2)

        return min(1.0, sum(scores))

    @staticmethod
    def _classify_quality(score: float) -> DreamQuality:
        """Classify a numeric score into a DreamQuality enum."""
        if score >= 0.85:
            return DreamQuality.EXCELLENT
        elif score >= 0.65:
            return DreamQuality.GOOD
        elif score >= 0.40:
            return DreamQuality.FAIR
        elif score >= 0.15:
            return DreamQuality.POOR
        return DreamQuality.FAILED

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------

    def _detect_anomalies(self, bank: DreamBank) -> float:
        """Detect anomalies in the dream bank.

        Anomaly signals:
            - Empty bank (no entries).
            - All entries are the same action type.
            - Extremely high or low importance variance.
            - Sudden change in entry count vs previous observations.

        Returns:
            Anomaly score from 0.0 (normal) to 1.0 (highly anomalous).
        """
        anomaly_signals: list[float] = []

        # Empty bank
        if not bank.entries:
            return 1.0

        # All same action type
        action_types = set(e.action for e in bank.entries)
        if len(action_types) == 1:
            anomaly_signals.append(0.5)

        # Importance variance
        if len(bank.entries) > 1:
            importances = [e.importance for e in bank.entries]
            variance = sum((x - sum(importances) / len(importances)) ** 2 for x in importances) / len(importances)
            if variance < 0.01:
                anomaly_signals.append(0.3)  # Too uniform

        # Sudden count change vs previous observations
        if self._observations:
            prev_entry_count = self._observations[-1].metadata.get("entry_count", 0)
            current_count = len(bank.entries)
            if prev_entry_count > 0 and current_count > 0:
                ratio = current_count / prev_entry_count
                if ratio > 3.0 or ratio < 0.33:
                    anomaly_signals.append(0.4)

        return min(1.0, sum(anomaly_signals) / max(1, len(anomaly_signals)))

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    def _analyze_trends(self, bank: DreamBank) -> list[str]:
        """Analyze trends from current and past observations.

        Returns:
            List of trend description strings.
        """
        trends: list[str] = []

        if not self._observations:
            return trends

        # Compare with previous observation
        if len(self._observations) >= 2:
            prev = self._observations[-2]

            if bank.metadata.get("dream_cycle", 0) > prev.metadata.get("dream_cycle", 0):
                if len(bank.entries) > len(self._observations[-1].metadata.get("entry_count", 0)):
                    trends.append("Dream entry count is increasing across cycles")
                elif len(bank.entries) < len(self._observations[-1].metadata.get("entry_count", 0)):
                    trends.append("Dream entry count is decreasing across cycles")

            if self._observations[-1].quality_score > prev.quality_score:
                trends.append("Dream quality is improving over time")

        # Entry type distribution
        action_counts: dict[str, int] = {}
        for entry in bank.entries:
            action_counts[entry.action.value] = action_counts.get(entry.action.value, 0) + 1

        dominant = max(action_counts, key=action_counts.get) if action_counts else "none"
        trends.append(f"Dominant dream action: {dominant} ({action_counts.get(dominant, 0)} entries)")

        return trends

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_recommendations(
        bank: DreamBank,
        quality_score: float,
        anomaly_score: float,
    ) -> list[str]:
        """Generate actionable recommendations based on analysis.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        if not bank.entries:
            recommendations.append("No entries produced; consider increasing session depth")
            return recommendations

        if quality_score < 0.4:
            recommendations.append("Dream quality is low; reduce dreaming frequency or increase scan depth")
        elif quality_score > 0.85:
            recommendations.append("Dream quality is excellent; current configuration is optimal")

        if anomaly_score > 0.6:
            recommendations.append("Anomalies detected; review dream parameters and memory health")

        # Action-specific recommendations
        action_counts: dict[str, int] = {}
        for entry in bank.entries:
            action_counts[entry.action.value] = action_counts.get(entry.action.value, 0) + 1

        if action_counts.get("pruned", 0) > len(bank.entries) * 0.5:
            recommendations.append("High pruning rate; consider adjusting min_importance threshold")
        if action_counts.get("contradiction", 0) > 5:
            recommendations.append("Multiple contradictions found; review memory ingestion sources")
        if action_counts.get("pattern", 0) == 0:
            recommendations.append("No cross-session patterns discovered; increase session_depth parameter")

        return recommendations

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_observations(self, limit: int = 10) -> list[DreamObservation]:
        """Return recent observations.

        Args:
            limit: Max observations to return.

        Returns:
            List of DreamObservation (most recent first).
        """
        return list(reversed(self._observations[-limit:]))

    def get_quality_history(self) -> list[dict[str, Any]]:
        """Return the quality score history for trend visualization.

        Returns:
            List of dicts with keys: timestamp, quality, score, entry_count.
        """
        return [
            {
                "timestamp": obs.timestamp,
                "quality": obs.quality.value,
                "score": obs.quality_score,
                "entry_count": obs.metadata.get("entry_count", 0),
            }
            for obs in self._observations
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Return observer statistics."""
        if not self._observations:
            return {"total_observations": 0}

        avg_quality = sum(o.quality_score for o in self._observations) / len(self._observations)
        avg_anomaly = sum(o.anomaly_score for o in self._observations) / len(self._observations)

        return {
            "total_observations": len(self._observations),
            "average_quality_score": round(avg_quality, 3),
            "average_anomaly_score": round(avg_anomaly, 3),
            "current_quality": self._observations[-1].quality.value,
            "observation_window": self.observation_window,
        }


# =============================================================================
# MemoryFilesIntegration
# =============================================================================


class MemoryFilesIntegration:
    """Persistent cross-session dream storage to the filesystem.

    Dream banks, observations, and metadata are written to JSON files
    in a configurable directory.  Supports loading dreams from previous
    sessions and exporting for analysis.

    Attributes:
        storage_dir: Directory for dream persistence files.
    """

    def __init__(self, storage_dir: str = DEFAULT_DREAM_STORAGE_DIR) -> None:
        self.storage_dir = Path(storage_dir)
        self._loaded_count: int = 0
        self._saved_count: int = 0

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_dream_bank(self, bank: DreamBank) -> str:
        """Save a DreamBank to the filesystem.

        Args:
            bank: The DreamBank to persist.

        Returns:
            The file path where the bank was saved.
        """
        self._ensure_dir()

        filepath = self._bank_path(bank.bank_id)
        data = self._serialize_bank(bank)

        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        self._saved_count += 1

        logger.debug("MemoryFilesIntegration: saved dream bank %s to %s", bank.bank_id, filepath)
        return str(filepath)

    def save_observation(self, observation: DreamObservation) -> str:
        """Save a DreamObservation to the filesystem.

        Args:
            observation: The observation to persist.

        Returns:
            The file path where the observation was saved.
        """
        self._ensure_dir()

        filepath = self._observation_path(observation.observation_id)
        data = {
            "observation_id": observation.observation_id,
            "dream_bank_id": observation.dream_bank_id,
            "quality": observation.quality.value,
            "quality_score": observation.quality_score,
            "anomaly_score": observation.anomaly_score,
            "pattern_trends": observation.pattern_trends,
            "recommendations": observation.recommendations,
            "timestamp": observation.timestamp,
            "metadata": observation.metadata,
        }

        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        self._saved_count += 1

        logger.debug("MemoryFilesIntegration: saved observation %s", observation.observation_id)
        return str(filepath)

    def save_session_manifest(self, manifest: dict[str, Any]) -> str:
        """Save a session manifest containing metadata about all dreams.

        Args:
            manifest: Session manifest dict.

        Returns:
            The file path where the manifest was saved.
        """
        self._ensure_dir()

        filepath = self.storage_dir / f"manifest_{int(time.time())}.json"
        filepath.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        self._saved_count += 1
        return str(filepath)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_dream_bank(self, bank_id: str) -> DreamBank | None:
        """Load a DreamBank from the filesystem.

        Args:
            bank_id: ID of the dream bank to load.

        Returns:
            The loaded DreamBank, or None if not found.
        """
        filepath = self._bank_path(bank_id)
        if not filepath.exists():
            logger.debug("MemoryFilesIntegration: dream bank %s not found", bank_id)
            return None

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            bank = self._deserialize_bank(data)
            self._loaded_count += 1
            return bank
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("MemoryFilesIntegration: failed to load %s: %s", bank_id, e)
            return None

    def list_saved_banks(self) -> list[dict[str, Any]]:
        """List all saved dream banks.

        Returns:
            List of dicts with keys: bank_id, timestamp, entry_count, filepath.
        """
        self._ensure_dir()
        banks: list[dict[str, Any]] = []

        for f in self.storage_dir.glob("dream_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                banks.append({
                    "bank_id": data.get("bank_id", ""),
                    "timestamp": data.get("timestamp", 0),
                    "entry_count": len(data.get("entries", [])),
                    "filepath": str(f),
                })
            except (json.JSONDecodeError, OSError):
                continue

        return sorted(banks, key=lambda b: b["timestamp"], reverse=True)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def prune_old_banks(self, max_age_days: float = 30.0) -> int:
        """Remove dream banks older than the specified age.

        Args:
            max_age_days: Maximum age in days.

        Returns:
            Number of pruned files.
        """
        self._ensure_dir()
        cutoff = time.time() - (max_age_days * 86400)
        pruned = 0

        for f in self.storage_dir.glob("dream_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ts = data.get("timestamp", 0)
                if ts < cutoff:
                    f.unlink()
                    pruned += 1
            except (json.JSONDecodeError, OSError):
                continue

        logger.info("MemoryFilesIntegration: pruned %d old dream banks", pruned)
        return pruned

    def clear_all(self) -> int:
        """Remove all saved dream files.

        Returns:
            Number of removed files.
        """
        self._ensure_dir()
        count = 0
        for f in self.storage_dir.glob("dream_*.json"):
            f.unlink()
            count += 1
        for f in self.storage_dir.glob("obs_*.json"):
            f.unlink()
            count += 1
        for f in self.storage_dir.glob("manifest_*.json"):
            f.unlink()
            count += 1
        logger.info("MemoryFilesIntegration: cleared %d files", count)
        return count

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Return storage statistics."""
        return {
            "storage_dir": str(self.storage_dir),
            "total_saved": self._saved_count,
            "total_loaded": self._loaded_count,
            "saved_banks": len(self.list_saved_banks()),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        """Ensure the storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _bank_path(self, bank_id: str) -> Path:
        return self.storage_dir / f"dream_{bank_id}.json"

    def _observation_path(self, obs_id: str) -> Path:
        return self.storage_dir / f"obs_{obs_id}.json"

    @staticmethod
    def _serialize_bank(bank: DreamBank) -> dict[str, Any]:
        return {
            "bank_id": bank.bank_id,
            "timestamp": bank.timestamp,
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "action": e.action.value,
                    "description": e.description,
                    "source_memory_ids": e.source_memory_ids,
                    "created_summary": e.created_summary,
                    "importance": e.importance,
                    "timestamp": e.timestamp,
                    "confidence": e.confidence,
                    "metadata": e.metadata,
                }
                for e in bank.entries
            ],
            "memory_bank_size": bank.memory_bank_size,
            "session_sources": bank.session_sources,
            "metadata": bank.metadata,
        }

    @staticmethod
    def _deserialize_bank(data: dict[str, Any]) -> DreamBank:
        entries = [
            DreamEntry(
                entry_id=e["entry_id"],
                action=DreamAction(e["action"]),
                description=e["description"],
                source_memory_ids=e["source_memory_ids"],
                created_summary=e.get("created_summary"),
                importance=e.get("importance", 0.5),
                timestamp=e.get("timestamp", 0),
                confidence=e.get("confidence", 1.0),
                metadata=e.get("metadata", {}),
            )
            for e in data.get("entries", [])
        ]
        return DreamBank(
            bank_id=data["bank_id"],
            timestamp=data["timestamp"],
            entries=entries,
            memory_bank_size=data.get("memory_bank_size", 0),
            session_sources=data.get("session_sources", 0),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# WarmUpScheduler
# =============================================================================


class WarmUpScheduler:
    """Schedule dreams during idle periods.

    Uses an adaptive interval that expands when the system is consistently
    idle and contracts when the user returns.  Learns from usage patterns
    to avoid running dreams when the user is likely to be active.

    Attributes:
        dream_engine: The DreamEngine to trigger.
        min_interval: Minimum seconds between warm-up dreams.
        max_interval: Maximum seconds between warm-up dreams.
        observer: Optional DeepDreamObserver for post-dream analysis.
    """

    def __init__(
        self,
        dream_engine: DreamEngine,
        min_interval: float = DEFAULT_WARMUP_INTERVAL,
        max_interval: float = DEFAULT_MAX_WARMUP_INTERVAL,
        observer: DeepDreamObserver | None = None,
    ) -> None:
        self.dream_engine = dream_engine
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.observer = observer

        self._current_interval: float = min_interval
        self._last_warmup: float = 0.0
        self._warmup_count: int = 0
        self._consecutive_idle: int = 0
        self._consecutive_active: int = 0
        self._warmup_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def should_warmup(self) -> bool:
        """Check if it is time to run a warm-up dream.

        Conditions:
            1. Dream engine is idle and should dream.
            2. Enough time has passed since the last warm-up.
            3. System has been consistently idle (adaptive).

        Returns:
            True if a warm-up dream should run.
        """
        if not self.dream_engine.is_idle():
            self._consecutive_active += 1
            self._consecutive_idle = 0
            return False

        self._consecutive_idle += 1
        self._consecutive_active = 0

        if not self.dream_engine.should_dream():
            return False

        elapsed = time.time() - self._last_warmup
        if elapsed < self._current_interval:
            return False

        # Require at least 3 consecutive idle checks before firing
        if self._consecutive_idle < 3:
            return False

        return True

    def run_warmup(self) -> DreamBank | None:
        """Execute one warm-up dream cycle.

        Returns:
            The DreamBank produced, or None if conditions are not met.
        """
        if not self.should_warmup():
            return None

        bank = self.dream_engine.dream()

        # Apply the dream (commit changes)
        self.dream_engine.apply_dream(bank)

        # Observe through DeepDreamObserver if available
        observation = None
        if self.observer is not None:
            observation = self.observer.observe(bank)

        # Update state
        self._last_warmup = time.time()
        self._warmup_count += 1
        self._adapt_interval()

        record: dict[str, Any] = {
            "warmup_id": self._warmup_count,
            "bank_id": bank.bank_id,
            "timestamp": self._last_warmup,
            "entry_count": len(bank.entries),
            "interval": self._current_interval,
            "observation_quality": observation.quality.value if observation else None,
        }
        self._warmup_history.append(record)

        logger.info(
            "WarmUpScheduler: run #%d (%d entries, interval=%.0fs)",
            self._warmup_count, len(bank.entries), self._current_interval,
        )

        return bank

    # ------------------------------------------------------------------
    # Adaptive interval
    # ------------------------------------------------------------------

    def _adapt_interval(self) -> None:
        """Adapt the warm-up interval based on idle patterns.

        - If consistently idle, expand interval (less frequent dreams).
        - If user returns frequently, contract interval (more responsive).
        """
        if self._consecutive_idle > 10:
            # Very idle: expand
            self._current_interval = min(
                self.max_interval,
                self._current_interval * 1.5,
            )
        elif self._consecutive_active > 5:
            # Active: contract
            self._current_interval = max(
                self.min_interval,
                self._current_interval / 1.5,
            )

    # ------------------------------------------------------------------
    # Manual control
    # ------------------------------------------------------------------

    def trigger_now(self) -> DreamBank | None:
        """Force an immediate warm-up dream regardless of interval.

        Returns:
            The DreamBank produced, or None if dreaming fails.
        """
        if not self.dream_engine.should_dream():
            return None
        # Bypass should_warmup checks for manual trigger
        bank = self.dream_engine.dream()
        self.dream_engine.apply_dream(bank)
        observation = None
        if self.observer is not None:
            observation = self.observer.observe(bank)
        self._last_warmup = time.time()
        self._warmup_count += 1
        record: dict[str, Any] = {
            "warmup_id": self._warmup_count,
            "bank_id": bank.bank_id,
            "timestamp": self._last_warmup,
            "entry_count": len(bank.entries),
            "interval": self._current_interval,
            "observation_quality": observation.quality.value if observation else None,
        }
        self._warmup_history.append(record)
        return bank

    def reset_interval(self) -> None:
        """Reset the warm-up interval to the minimum."""
        self._current_interval = self.min_interval
        logger.debug("WarmUpScheduler: interval reset to %.0fs", self.min_interval)

    def set_interval(self, interval: float) -> None:
        """Manually override the warm-up interval.

        Args:
            interval: New interval in seconds.
        """
        self._current_interval = max(self.min_interval, min(self.max_interval, interval))
        logger.debug("WarmUpScheduler: interval set to %.0fs", self._current_interval)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_warmup_history(self) -> list[dict[str, Any]]:
        """Return the warm-up execution history."""
        return list(self._warmup_history)

    def get_statistics(self) -> dict[str, Any]:
        """Return scheduler statistics."""
        return {
            "warmup_count": self._warmup_count,
            "current_interval": self._current_interval,
            "min_interval": self.min_interval,
            "max_interval": self.max_interval,
            "consecutive_idle": self._consecutive_idle,
            "consecutive_active": self._consecutive_active,
            "last_warmup": self._last_warmup,
        }


# =============================================================================
# ConwayCycle
# =============================================================================


class ConwayState(Enum):
    """State of a memory in the Conway life cycle."""

    BIRTH = "birth"              # Newly created memory
    GROWTH = "growth"            # Memory with increasing importance
    MATURE = "mature"            # Stable, high-importance memory
    REPRODUCTION = "reproduction"  # Spawning related memories
    DECAY = "decay"              # Declining importance
    DEATH = "death"              # Ready for pruning


@dataclass
class ConwayMemory:
    """A memory in the Conway cycle.

    Attributes:
        memory_id: Unique identifier linking to the original Memory.
        content: Memory content (copy for life-cycle processing).
        importance: Current importance (0.0 - 1.0).
        state: Current Conway state.
        generation: Generation number (birth = 0).
        neighbors: IDs of neighboring ConwayMemory instances.
        age_cycles: Number of life-cycle steps survived.
        metadata: Additional metadata.
    """

    memory_id: str
    content: str
    importance: float = 0.5
    state: ConwayState = ConwayState.BIRTH
    generation: int = 0
    neighbors: list[str] = field(default_factory=list)
    age_cycles: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ConwayCycle:
    """Conway-like memory life cycle simulation.

    Memories evolve through generations in a cellular-automaton-inspired
    process: birth, growth, maturity, reproduction, decay, and death.
    The cycle promotes high-quality, connected memories and prunes
    isolated or low-importance ones.

    Attributes:
        grid_size: Size of the cellular grid (grid_size x grid_size).
        max_generations: Max generations before auto-stabilization.
    """

    def __init__(
        self,
        grid_size: int = DEFAULT_CONWAY_GRID_SIZE,
        max_generations: int = DEFAULT_CONWAY_GENERATIONS,
    ) -> None:
        self.grid_size = grid_size
        self.max_generations = max_generations

        self._memories: dict[str, ConwayMemory] = {}
        self._grid: list[list[ConwayMemory | None]] = [
            [None for _ in range(grid_size)] for _ in range(grid_size)
        ]
        self._generation: int = 0
        self._history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------

    def populate(self, memories: list[Memory] | list[ConwayMemory]) -> int:
        """Populate the Conway grid from a list of memories.

        Each memory is placed on a random grid cell.  Existing memories
        are preserved; new ones are added to empty cells.

        Args:
            memories: List of Memory or ConwayMemory instances.

        Returns:
            Number of memories added.
        """
        added = 0

        for mem in memories:
            if isinstance(mem, Memory):
                cm = ConwayMemory(
                    memory_id=mem.memory_id,
                    content=mem.content,
                    importance=mem.importance,
                    state=ConwayState.BIRTH,
                )
            else:
                cm = mem

            if cm.memory_id in self._memories:
                continue

            self._memories[cm.memory_id] = cm

            # Place on grid
            placed = False
            for _ in range(100):  # max attempts
                x = random.randint(0, self.grid_size - 1)
                y = random.randint(0, self.grid_size - 1)
                if self._grid[x][y] is None:
                    self._grid[x][y] = cm
                    placed = True
                    break

            if not placed:
                # Fill first empty cell
                for x in range(self.grid_size):
                    for y in range(self.grid_size):
                        if self._grid[x][y] is None:
                            self._grid[x][y] = cm
                            placed = True
                            break
                    if placed:
                        break

            added += 1

        self._update_neighbors()
        logger.debug("ConwayCycle: populated %d memories (grid %dx%d)", added, self.grid_size, self.grid_size)
        return added

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------

    def evolve(self, steps: int = 1) -> list[dict[str, Any]]:
        """Evolve the memory population through one or more generations.

        Each generation applies Conway-inspired rules:
            1. BIRTH memories gain importance.
            2. GROWTH memories with sufficient importance → MATURE.
            3. MATURE memories may spawn REPRODUCTION.
            4. REPRODUCTION memories create BIRTH neighbors.
            5. Low-importance or isolated memories → DECAY.
            6. DECAY memories with zero importance → DEATH.

        Args:
            steps: Number of generations to simulate.

        Returns:
            List of change records for each generation.
        """
        changes: list[dict[str, Any]] = []

        for _ in range(steps):
            self._generation += 1
            if self._generation > self.max_generations:
                break

            gen_changes = self._step()
            changes.append({
                "generation": self._generation,
                "changes": gen_changes,
                "population": len(self._memories),
            })
            self._history.append(changes[-1])

            # Auto-stabilize if no changes
            if not gen_changes:
                logger.debug("ConwayCycle: stabilized at generation %d", self._generation)
                break

        return changes

    def _step(self) -> list[dict[str, Any]]:
        """Execute one Conway generation step.

        Returns:
            List of change dicts with keys: memory_id, from_state, to_state, reason.
        """
        gen_changes: list[dict[str, Any]] = []

        # Compute next states
        next_states: dict[str, ConwayState] = {}
        next_importances: dict[str, float] = {}

        for cm in self._memories.values():
            old_state = cm.state
            new_state, new_importance = self._apply_rules(cm)

            if new_state != old_state or new_importance != cm.importance:
                next_states[cm.memory_id] = new_state
                next_importances[cm.memory_id] = new_importance

                gen_changes.append({
                    "memory_id": cm.memory_id,
                    "from_state": old_state.value,
                    "to_state": new_state.value,
                    "old_importance": cm.importance,
                    "new_importance": new_importance,
                    "generation": self._generation,
                })

        # Apply changes
        for mid, state in next_states.items():
            cm = self._memories[mid]
            cm.state = state
            if mid in next_importances:
                cm.importance = next_importances[mid]
            cm.age_cycles += 1

        # Remove DEATH memories
        dead_ids = [mid for mid, cm in self._memories.items() if cm.state == ConwayState.DEATH]
        for mid in dead_ids:
            self._remove_memory(mid)

        return gen_changes

    def _apply_rules(
        self,
        cm: ConwayMemory,
    ) -> tuple[ConwayState, float]:
        """Apply Conway-inspired rules to a single memory.

        Args:
            cm: The ConwayMemory to evaluate.

        Returns:
            Tuple of (new_state, new_importance).
        """
        neighbor_count = len(cm.neighbors)
        avg_neighbor_importance = self._avg_neighbor_importance(cm)

        if cm.state == ConwayState.BIRTH:
            # Birth: gain importance based on neighbors
            imp = min(1.0, cm.importance + 0.1 + (avg_neighbor_importance * 0.05))
            if imp >= 0.3:
                return ConwayState.GROWTH, imp
            # Stay in birth if not enough neighbors
            if neighbor_count < 2:
                return ConwayState.DECAY, max(0.0, imp - 0.05)
            return ConwayState.BIRTH, imp

        if cm.state == ConwayState.GROWTH:
            imp = min(1.0, cm.importance + 0.05 + (avg_neighbor_importance * 0.02))
            if imp >= 0.6:
                return ConwayState.MATURE, imp
            if neighbor_count == 0:
                return ConwayState.DECAY, max(0.0, imp - 0.1)
            return ConwayState.GROWTH, imp

        if cm.state == ConwayState.MATURE:
            imp = min(1.0, cm.importance + 0.02)
            # Mature memories with many neighbors may reproduce
            if neighbor_count >= 3 and random.random() < 0.3:
                return ConwayState.REPRODUCTION, imp
            if neighbor_count == 0:
                return ConwayState.DECAY, max(0.0, imp - 0.15)
            return ConwayState.MATURE, imp

        if cm.state == ConwayState.REPRODUCTION:
            # Reproduction spawns new memories (handled separately via spawn events)
            imp = min(1.0, cm.importance + 0.01)
            return ConwayState.MATURE, imp  # Return to mature after one cycle

        if cm.state == ConwayState.DECAY:
            imp = max(0.0, cm.importance - 0.15 - (0.02 * (3 - neighbor_count)))
            if imp <= 0.0:
                return ConwayState.DEATH, 0.0
            if neighbor_count >= 2 and imp > 0.3:
                return ConwayState.GROWTH, imp  # Recovery possible
            return ConwayState.DECAY, imp

        return cm.state, cm.importance

    # ------------------------------------------------------------------
    # Reproduction
    # ------------------------------------------------------------------

    def spawn_offspring(
        self,
        parent_id: str,
        content_template: str = "",
    ) -> list[ConwayMemory]:
        """Spawn offspring memories from a parent in REPRODUCTION state.

        Args:
            parent_id: ID of the reproducing memory.
            content_template: Template string for offspring content.

        Returns:
            List of newly spawned ConwayMemory instances.
        """
        parent = self._memories.get(parent_id)
        if parent is None or parent.state != ConwayState.REPRODUCTION:
            return []

        # Place offspring in adjacent grid cells
        pos = self._find_position(parent_id)
        if pos is None:
            return []

        x, y = pos
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        random.shuffle(offsets)

        offspring: list[ConwayMemory] = []
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                if self._grid[nx][ny] is None:
                    child = ConwayMemory(
                        memory_id=str(uuid.uuid4()),
                        content=content_template or f"Offspring of {parent.content[:60]}",
                        importance=parent.importance * 0.5,
                        state=ConwayState.BIRTH,
                        generation=parent.generation + 1,
                        neighbors=[parent_id],
                    )
                    self._memories[child.memory_id] = child
                    self._grid[nx][ny] = child
                    offspring.append(child)

        if offspring:
            logger.debug("ConwayCycle: %s spawned %d offspring", parent_id, len(offspring))

        # Update neighbors
        self._update_neighbors()

        return offspring

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_memory(self, memory_id: str) -> ConwayMemory | None:
        """Get a ConwayMemory by ID."""
        return self._memories.get(memory_id)

    def get_by_state(self, state: ConwayState) -> list[ConwayMemory]:
        """Get all memories in a given state."""
        return [cm for cm in self._memories.values() if cm.state == state]

    def get_living(self) -> list[ConwayMemory]:
        """Get all memories that are not DEATH."""
        return [
            cm for cm in self._memories.values()
            if cm.state not in (ConwayState.DEATH, ConwayState.DECAY)
        ]

    def get_generation(self) -> int:
        """Get the current generation number."""
        return self._generation

    def population_count(self) -> int:
        """Get the current population count."""
        return len(self._memories)

    def get_statistics(self) -> dict[str, Any]:
        """Return Conway cycle statistics."""
        state_counts: dict[str, int] = {}
        for cm in self._memories.values():
            state_counts[cm.state.value] = state_counts.get(cm.state.value, 0) + 1

        return {
            "generation": self._generation,
            "max_generations": self.max_generations,
            "population": len(self._memories),
            "grid_size": self.grid_size,
            "states": state_counts,
            "history_length": len(self._history),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_neighbors(self) -> None:
        """Rebuild neighbor lists based on grid proximity."""
        # Clear all neighbor lists
        for cm in self._memories.values():
            cm.neighbors = []

        for x in range(self.grid_size):
            for y in range(self.grid_size):
                cm = self._grid[x][y]
                if cm is None:
                    continue
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                            neighbor = self._grid[nx][ny]
                            if neighbor is not None and neighbor.memory_id != cm.memory_id:
                                if neighbor.memory_id not in cm.neighbors:
                                    cm.neighbors.append(neighbor.memory_id)

    def _find_position(self, memory_id: str) -> tuple[int, int] | None:
        """Find the grid position of a memory."""
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                if self._grid[x][y] is not None and self._grid[x][y].memory_id == memory_id:
                    return x, y
        return None

    def _remove_memory(self, memory_id: str) -> None:
        """Remove a memory from the grid and the map."""
        self._memories.pop(memory_id, None)
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                if self._grid[x][y] is not None and self._grid[x][y].memory_id == memory_id:
                    self._grid[x][y] = None
        self._update_neighbors()

    def _avg_neighbor_importance(self, cm: ConwayMemory) -> float:
        """Compute average importance of a memory's neighbors."""
        if not cm.neighbors:
            return 0.0
        importances = [
            self._memories[n].importance
            for n in cm.neighbors
            if n in self._memories
        ]
        if not importances:
            return 0.0
        return sum(importances) / len(importances)
