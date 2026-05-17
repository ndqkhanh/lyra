"""Eager tools integration module."""
from lyra_cli.eager_tools.seal_detector import SealDetector, ToolBlock
from lyra_cli.eager_tools.executor_pool import EagerExecutorPool, ToolResult
from lyra_cli.eager_tools.metrics import MetricsCollector, SealMetrics

__all__ = [
    "SealDetector",
    "ToolBlock",
    "EagerExecutorPool",
    "ToolResult",
    "MetricsCollector",
    "SealMetrics",
]
