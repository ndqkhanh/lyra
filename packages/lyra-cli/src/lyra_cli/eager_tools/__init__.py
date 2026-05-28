"""Eager Tools: Stream-parallel tool dispatch for 1.2×-1.5× speedup."""

from .executor import ExecutorPool
from .registry import ToolMetadata, ToolRegistry, tool
from .seal_detector import SealDetector
from .types import StreamChunk, ToolResult, ToolSeal

__all__ = [
    "StreamChunk",
    "ToolSeal",
    "ToolResult",
    "SealDetector",
    "ExecutorPool",
    "ToolRegistry",
    "ToolMetadata",
    "tool",
]
