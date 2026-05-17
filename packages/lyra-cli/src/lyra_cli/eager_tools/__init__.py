"""Eager Tools: Stream-parallel tool dispatch for 1.2×-1.5× speedup."""

from .types import StreamChunk, ToolSeal, ToolResult
from .seal_detector import SealDetector
from .executor import ExecutorPool
from .registry import ToolRegistry, ToolMetadata, tool

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
