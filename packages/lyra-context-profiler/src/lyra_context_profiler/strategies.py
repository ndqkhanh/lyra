"""Compaction Strategies — Configurable strategies for context window management.

Provides Aggressive, Conservative, Balanced, and Adaptive strategies,
each with tunable parameters. Includes strategy registry and performance
tracking.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Enums ───────────────────────────────────────────────────────────────────────


class CompactionStrategy(Enum):
    """Compaction strategy enum."""

    AGGRESSIVE = auto()    # Maximize free space
    CONSERVATIVE = auto()  # Minimize information loss
    BALANCED = auto()      # Optimize for task completion
    ADAPTIVE = auto()      # Learn from past decisions


# ── Strategy Parameters ─────────────────────────────────────────────────────────


@dataclass
class StrategyParameters:
    """Configurable parameters for a compaction strategy.

    Each parameter controls a specific aspect of compaction behavior.
    """

    # Retention thresholds (importance score below which elements may be removed)
    drop_threshold: float = 0.15       # Below this: candidate for dropping
    compact_threshold: float = 0.50    # Below this: candidate for compaction
    keep_threshold: float = 0.70       # Above this: always keep

    # Compaction ratios
    compression_target: float = 0.60   # Target fraction of content to retain
    max_single_element_reduction: float = 0.80  # Max % reduction for one element

    # Duplicate handling
    dedup_similarity_threshold: float = 0.85  # Similarity threshold for dup detection
    enable_fuzzy_dedup: bool = True

    # Summarization levels
    high_importance_summary_level: int = 0  # 0=full, 1=detailed, 2=overview, 3=minimal
    medium_importance_summary_level: int = 1
    low_importance_summary_level: int = 2

    # Progressive disclosure
    enable_progressive_disclosure: bool = True
    disclosure_trigger_utilization: float = 0.75  # Utilization % to trigger disclosure

    # Cache warming
    enable_cache_warming: bool = True
    max_preload_tokens: int = 6000

    # Safety
    max_quality_loss: float = 0.30     # Maximum acceptable information loss
    min_retained_elements: int = 3     # Minimum elements to always retain

    # Adaptive learning
    learning_rate: float = 0.05        # How fast to adapt parameters
    window_size: int = 100             # History window for adaptation

    def to_dict(self) -> dict[str, Any]:
        """Export parameters as a dictionary."""
        return {
            "drop_threshold": self.drop_threshold,
            "compact_threshold": self.compact_threshold,
            "keep_threshold": self.keep_threshold,
            "compression_target": self.compression_target,
            "max_single_element_reduction": self.max_single_element_reduction,
            "dedup_similarity_threshold": self.dedup_similarity_threshold,
            "enable_fuzzy_dedup": self.enable_fuzzy_dedup,
            "high_importance_summary_level": self.high_importance_summary_level,
            "medium_importance_summary_level": self.medium_importance_summary_level,
            "low_importance_summary_level": self.low_importance_summary_level,
            "enable_progressive_disclosure": self.enable_progressive_disclosure,
            "disclosure_trigger_utilization": self.disclosure_trigger_utilization,
            "enable_cache_warming": self.enable_cache_warming,
            "max_preload_tokens": self.max_preload_tokens,
            "max_quality_loss": self.max_quality_loss,
            "min_retained_elements": self.min_retained_elements,
            "learning_rate": self.learning_rate,
            "window_size": self.window_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StrategyParameters:
        """Create parameters from a dictionary."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# ── Strategy Presets ────────────────────────────────────────────────────────────


class StrategyPresets:
    """Factory for pre-configured strategy parameter sets."""

    @staticmethod
    def aggressive() -> StrategyParameters:
        """Aggressive: maximize free space, accept higher quality loss."""
        return StrategyParameters(
            drop_threshold=0.25,
            compact_threshold=0.60,
            keep_threshold=0.80,
            compression_target=0.30,
            max_single_element_reduction=0.90,
            dedup_similarity_threshold=0.75,
            enable_fuzzy_dedup=True,
            high_importance_summary_level=1,
            medium_importance_summary_level=2,
            low_importance_summary_level=3,
            enable_progressive_disclosure=True,
            disclosure_trigger_utilization=0.65,
            enable_cache_warming=True,
            max_preload_tokens=8000,
            max_quality_loss=0.40,
            min_retained_elements=2,
            learning_rate=0.08,
        )

    @staticmethod
    def conservative() -> StrategyParameters:
        """Conservative: minimize information loss, accept less space freed."""
        return StrategyParameters(
            drop_threshold=0.05,
            compact_threshold=0.30,
            keep_threshold=0.50,
            compression_target=0.80,
            max_single_element_reduction=0.40,
            dedup_similarity_threshold=0.95,
            enable_fuzzy_dedup=False,
            high_importance_summary_level=0,
            medium_importance_summary_level=1,
            low_importance_summary_level=2,
            enable_progressive_disclosure=True,
            disclosure_trigger_utilization=0.85,
            enable_cache_warming=True,
            max_preload_tokens=4000,
            max_quality_loss=0.10,
            min_retained_elements=5,
            learning_rate=0.02,
        )

    @staticmethod
    def balanced() -> StrategyParameters:
        """Balanced: optimize for task completion with moderate trade-offs."""
        return StrategyParameters(
            drop_threshold=0.15,
            compact_threshold=0.50,
            keep_threshold=0.70,
            compression_target=0.55,
            max_single_element_reduction=0.70,
            dedup_similarity_threshold=0.85,
            enable_fuzzy_dedup=True,
            high_importance_summary_level=0,
            medium_importance_summary_level=1,
            low_importance_summary_level=3,
            enable_progressive_disclosure=True,
            disclosure_trigger_utilization=0.75,
            enable_cache_warming=True,
            max_preload_tokens=6000,
            max_quality_loss=0.25,
            min_retained_elements=3,
            learning_rate=0.05,
        )

    @staticmethod
    def adaptive() -> StrategyParameters:
        """Adaptive: learn from past compaction decisions."""
        return StrategyParameters(
            drop_threshold=0.12,
            compact_threshold=0.45,
            keep_threshold=0.65,
            compression_target=0.50,
            max_single_element_reduction=0.75,
            dedup_similarity_threshold=0.85,
            enable_fuzzy_dedup=True,
            high_importance_summary_level=0,
            medium_importance_summary_level=1,
            low_importance_summary_level=2,
            enable_progressive_disclosure=True,
            disclosure_trigger_utilization=0.75,
            enable_cache_warming=True,
            max_preload_tokens=6000,
            max_quality_loss=0.20,
            min_retained_elements=3,
            learning_rate=0.10,  # Higher learning rate for faster adaptation
        )


# ── Strategy Registry ───────────────────────────────────────────────────────────


@dataclass
class StrategyRecord:
    """Performance record for a single strategy application."""

    strategy: CompactionStrategy
    tokens_freed: int
    quality_loss: float
    task_success: bool
    user_satisfaction: float  # 0.0 to 1.0
    duration_ms: float
    context_before_utilization: float
    context_after_utilization: float


class StrategyRegistry:
    """Registry for managing compaction strategies and their performance history.

    Tracks which strategies perform best under different conditions and
    supports adaptive strategy selection.

    Usage::

        registry = StrategyRegistry()
        registry.configure(CompactionStrategy.BALANCED, StrategyPresets.balanced())

        # After each compaction:
        registry.record_result(strategy, record)

        # Get best strategy for current conditions:
        best = registry.best_strategy_for(utilization_pct=0.82)
    """

    def __init__(self):
        self._parameters: dict[CompactionStrategy, StrategyParameters] = {
            CompactionStrategy.AGGRESSIVE: StrategyPresets.aggressive(),
            CompactionStrategy.CONSERVATIVE: StrategyPresets.conservative(),
            CompactionStrategy.BALANCED: StrategyPresets.balanced(),
            CompactionStrategy.ADAPTIVE: StrategyPresets.adaptive(),
        }

        self._history: dict[CompactionStrategy, list[StrategyRecord]] = defaultdict(list)
        self._success_rates: dict[CompactionStrategy, float] = {}
        self._avg_quality_loss: dict[CompactionStrategy, float] = {}

    def configure(
        self,
        strategy: CompactionStrategy,
        parameters: StrategyParameters,
    ) -> None:
        """Set or update parameters for a strategy."""
        self._parameters[strategy] = parameters
        logger.info("Configured %s strategy with drop_threshold=%.2f", strategy.name, parameters.drop_threshold)

    def get_parameters(self, strategy: CompactionStrategy) -> StrategyParameters:
        """Get the current parameters for a strategy."""
        return self._parameters[strategy]

    def record_result(
        self,
        strategy: CompactionStrategy,
        record: StrategyRecord,
    ) -> None:
        """Record the outcome of a strategy application."""
        self._history[strategy].append(record)

        # Keep history bounded
        max_history = self._parameters[strategy].window_size
        if len(self._history[strategy]) > max_history:
            self._history[strategy] = self._history[strategy][-max_history:]

        # Update statistics
        records = self._history[strategy]
        self._success_rates[strategy] = sum(1 for r in records if r.task_success) / len(records)
        self._avg_quality_loss[strategy] = sum(r.quality_loss for r in records) / len(records)

    def best_strategy_for(
        self,
        utilization_pct: float,
        prioritize_quality: bool = False,
    ) -> CompactionStrategy:
        """Select the best strategy for current context conditions.

        Args:
            utilization_pct: Current context utilization percentage (0-100).
            prioritize_quality: If True, favor lower quality loss over more space.

        Returns:
            The best CompactionStrategy for the conditions.
        """
        # If no history, use heuristic selection
        if not any(self._history.values()):
            return self._heuristic_select(utilization_pct, prioritize_quality)

        candidates = list(self._history.keys())

        if prioritize_quality:
            # Best = lowest average quality loss
            best = min(
                candidates,
                key=lambda s: self._avg_quality_loss.get(s, 0.5),
            )
        else:
            # Best = highest success rate * token efficiency
            def score(s: CompactionStrategy) -> float:
                sr = self._success_rates.get(s, 0.5)
                avg_freed = sum(r.tokens_freed for r in self._history[s]) / max(len(self._history[s]), 1)
                norm_freed = min(avg_freed / 10000, 1.0)  # Normalize to 10k tokens
                return sr * 0.6 + norm_freed * 0.4

            best = max(candidates, key=score)

        logger.debug(
            "Best strategy for %.1f%% utilization: %s (quality_priority=%s)",
            utilization_pct, best.name, prioritize_quality,
        )
        return best

    def get_strategy_stats(self) -> dict[str, dict[str, Any]]:
        """Get performance statistics for all strategies."""
        stats: dict[str, dict[str, Any]] = {}
        for strategy in CompactionStrategy:
            records = self._history[strategy]
            if not records:
                stats[strategy.name] = {
                    "applications": 0,
                    "success_rate": None,
                    "avg_quality_loss": None,
                    "avg_tokens_freed": None,
                }
                continue

            stats[strategy.name] = {
                "applications": len(records),
                "success_rate": self._success_rates.get(strategy, 0.0),
                "avg_quality_loss": self._avg_quality_loss.get(strategy, 0.0),
                "avg_tokens_freed": sum(r.tokens_freed for r in records) / len(records),
                "avg_duration_ms": sum(r.duration_ms for r in records) / len(records),
            }

        return stats

    def adapt_parameters(
        self,
        strategy: CompactionStrategy,
        recent_results: list[StrategyRecord],
    ) -> StrategyParameters:
        """Adapt strategy parameters based on recent results.

        Only applies to the ADAPTIVE strategy by default, but can be used
        for any strategy.
        """
        if not recent_results:
            return self._parameters[strategy]

        params = self._parameters[strategy]
        lr = params.learning_rate

        avg_loss = sum(r.quality_loss for r in recent_results) / len(recent_results)
        avg_freed = sum(r.tokens_freed for r in recent_results) / len(recent_results)

        # Adapt thresholds based on outcomes
        new_params = StrategyParameters(
            **{f.name: getattr(params, f.name) for f in params.__dataclass_fields__.values()}
        )

        # If quality loss is too high, raise thresholds (be more conservative)
        if avg_loss > params.max_quality_loss:
            new_params.drop_threshold = min(
                params.drop_threshold + lr,
                params.compact_threshold - 0.05,
            )
            new_params.compact_threshold = min(
                params.compact_threshold + lr,
                params.keep_threshold - 0.05,
            )

        # If we freed too little, lower thresholds (be more aggressive)
        target_freed_ratio = 0.15  # Aim for 15% freeable
        if avg_freed / 10000 < target_freed_ratio and avg_loss < params.max_quality_loss * 0.7:
            new_params.drop_threshold = max(params.drop_threshold - lr, 0.02)
            new_params.compact_threshold = max(params.compact_threshold - lr, params.drop_threshold + 0.05)

        self._parameters[strategy] = new_params
        logger.debug(
            "Adapted %s: drop=%.2f compact=%.2f (loss=%.3f, freed=%d)",
            strategy.name, new_params.drop_threshold, new_params.compact_threshold, avg_loss, int(avg_freed),
        )

        return new_params

    @staticmethod
    def _heuristic_select(
        utilization_pct: float,
        prioritize_quality: bool,
    ) -> CompactionStrategy:
        """Heuristic strategy selection when no history is available."""
        if prioritize_quality:
            if utilization_pct > 90:
                return CompactionStrategy.BALANCED  # Can't be too conservative at high util
            return CompactionStrategy.CONSERVATIVE
        else:
            if utilization_pct > 90:
                return CompactionStrategy.AGGRESSIVE
            elif utilization_pct > 70:
                return CompactionStrategy.BALANCED
            elif utilization_pct > 50:
                return CompactionStrategy.ADAPTIVE
            return CompactionStrategy.CONSERVATIVE

    def clear_history(self) -> None:
        """Clear all strategy performance history."""
        self._history.clear()
        self._success_rates.clear()
        self._avg_quality_loss.clear()

    @property
    def total_applications(self) -> int:
        return sum(len(records) for records in self._history.values())
