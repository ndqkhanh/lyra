"""
Lyra TokenJuice - Token compression system.

This package provides:
- 80% token reduction
- <5% information loss
- Cyber-specific compression rules
- Cost savings tracking
"""

from lyra_tokenjuice.compressor import CompressionResult, TokenCompressor
from lyra_tokenjuice.cyber_rules import CyberCompressor
from lyra_tokenjuice.metrics import CompressionMetric, MetricsTracker

__version__ = "0.1.0"

__all__ = [
    # Compressor
    "TokenCompressor",
    "CompressionResult",
    # Cyber rules
    "CyberCompressor",
    # Metrics
    "MetricsTracker",
    "CompressionMetric",
]
