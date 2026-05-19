"""
Compression Metrics - Track compression performance.

Features:
- Compression ratio tracking
- Information loss measurement
- Cost savings calculation
- A/B testing support
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CompressionMetric:
    """Single compression metric."""

    timestamp: datetime
    rule_name: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    information_loss: float
    processing_time_ms: float
    metadata: Dict[str, str] = field(default_factory=dict)


class MetricsTracker:
    """
    Track compression metrics.

    Features:
    - Per-rule statistics
    - Cost savings calculation
    - A/B testing support
    """

    def __init__(self, cost_per_1k_tokens: float = 0.03):
        """
        Initialize metrics tracker.

        Args:
            cost_per_1k_tokens: Cost per 1000 tokens (default: GPT-4 pricing)
        """
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.metrics: List[CompressionMetric] = []

    def record(
        self,
        rule_name: str,
        original_tokens: int,
        compressed_tokens: int,
        compression_ratio: float,
        information_loss: float,
        processing_time_ms: float,
        metadata: Optional[Dict[str, str]] = None,
    ):
        """
        Record compression metric.

        Args:
            rule_name: Name of compression rule
            original_tokens: Original token count
            compressed_tokens: Compressed token count
            compression_ratio: Compression ratio (0.0-1.0)
            information_loss: Information loss (0.0-1.0)
            processing_time_ms: Processing time in milliseconds
            metadata: Additional metadata
        """
        metric = CompressionMetric(
            timestamp=datetime.now(),
            rule_name=rule_name,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            information_loss=information_loss,
            processing_time_ms=processing_time_ms,
            metadata=metadata or {},
        )

        self.metrics.append(metric)

    def get_stats(self) -> Dict[str, float]:
        """
        Get overall statistics.

        Returns:
            Statistics dictionary
        """
        if not self.metrics:
            return {}

        total_original = sum(m.original_tokens for m in self.metrics)
        total_compressed = sum(m.compressed_tokens for m in self.metrics)
        avg_compression = sum(m.compression_ratio for m in self.metrics) / len(self.metrics)
        avg_info_loss = sum(m.information_loss for m in self.metrics) / len(self.metrics)
        avg_processing_time = sum(m.processing_time_ms for m in self.metrics) / len(self.metrics)

        # Calculate cost savings
        original_cost = (total_original / 1000) * self.cost_per_1k_tokens
        compressed_cost = (total_compressed / 1000) * self.cost_per_1k_tokens
        cost_savings = original_cost - compressed_cost
        cost_savings_pct = (cost_savings / original_cost * 100) if original_cost > 0 else 0

        return {
            "total_compressions": len(self.metrics),
            "total_original_tokens": total_original,
            "total_compressed_tokens": total_compressed,
            "tokens_saved": total_original - total_compressed,
            "avg_compression_ratio": avg_compression,
            "avg_information_loss": avg_info_loss,
            "avg_processing_time_ms": avg_processing_time,
            "original_cost_usd": original_cost,
            "compressed_cost_usd": compressed_cost,
            "cost_savings_usd": cost_savings,
            "cost_savings_pct": cost_savings_pct,
        }

    def get_stats_by_rule(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics per rule.

        Returns:
            Per-rule statistics
        """
        rules: Dict[str, List[CompressionMetric]] = {}

        for metric in self.metrics:
            if metric.rule_name not in rules:
                rules[metric.rule_name] = []
            rules[metric.rule_name].append(metric)

        stats = {}
        for rule_name, rule_metrics in rules.items():
            total_original = sum(m.original_tokens for m in rule_metrics)
            total_compressed = sum(m.compressed_tokens for m in rule_metrics)
            avg_compression = sum(m.compression_ratio for m in rule_metrics) / len(rule_metrics)
            avg_info_loss = sum(m.information_loss for m in rule_metrics) / len(rule_metrics)

            stats[rule_name] = {
                "count": len(rule_metrics),
                "total_original_tokens": total_original,
                "total_compressed_tokens": total_compressed,
                "avg_compression_ratio": avg_compression,
                "avg_information_loss": avg_info_loss,
            }

        return stats

    def get_dashboard_data(self) -> Dict:
        """
        Get data for dashboard visualization.

        Returns:
            Dashboard data
        """
        overall_stats = self.get_stats()
        per_rule_stats = self.get_stats_by_rule()

        # Recent metrics (last 100)
        recent_metrics = self.metrics[-100:]

        return {
            "overall": overall_stats,
            "by_rule": per_rule_stats,
            "recent_compressions": len(recent_metrics),
            "timestamp": datetime.now().isoformat(),
        }

    def clear(self):
        """Clear all metrics."""
        self.metrics.clear()
