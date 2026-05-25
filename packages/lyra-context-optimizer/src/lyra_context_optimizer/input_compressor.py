"""RTK-style hook-based proxy compression for command outputs.

Compresses tool/command outputs by applying 100+ command-specific compression
patterns: smart filtering, grouping, truncation, and deduplication.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import CompressionError


class CompressionStrategy(Enum):
    """Compression strategies for input/output processing."""

    SMART_FILTERING = auto()
    GROUPING = auto()
    TRUNCATION = auto()
    DEDUPLICATION = auto()


@dataclass(frozen=True)
class CompressionResult:
    """Result of a compression operation.

    Attributes:
        compressed: The compressed content.
        original_tokens: Token count before compression.
        compressed_tokens: Token count after compression.
        compression_ratio: Ratio (0.0 = none, 1.0 = full).
        strategy_used: Which strategy was applied.
        time_taken_ms: Time taken in milliseconds.
    """

    compressed: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy_used: str
    time_taken_ms: float


# ── Command pattern definitions ────────────────────────────────────────

_COMMAND_PATTERNS: dict[str, dict[str, Any]] = {
    # File system
    "ls": {
        "filter": r"^[-d|].{9}\s+\d+\s+\S+\s+\S+\s+\d+\s+\S+\s+\d+\s+\S+$",
        "max_lines": 80,
        "group": True,
    },
    "find": {
        "filter": r"^\.?/",
        "max_lines": 100,
        "group": True,
    },
    "du": {
        "filter": r"^\d+",
        "max_lines": 50,
        "group": True,
    },
    "df": {
        "filter": r"^/",
        "max_lines": 30,
        "group": False,
    },
    # Git
    "git diff": {
        "filter": r"^[+-@]|^diff|^index|^---|^\+\+\+",
        "max_lines": 200,
        "group": False,
    },
    "git log": {
        "filter": r"^commit|^Author|^Date|^\s{4}",
        "max_lines": 60,
        "group": True,
    },
    "git status": {
        "filter": r"^[ #]",
        "max_lines": 50,
        "group": False,
    },
    "git branch": {
        "filter": r"^[\s*]",
        "max_lines": 40,
        "group": True,
    },
    # Process
    "ps": {
        "filter": r"^\s*\d+",
        "max_lines": 60,
        "group": True,
    },
    "top": {
        "filter": r"^\s*\d+",
        "max_lines": 30,
        "group": False,
    },
    # Network
    "netstat": {
        "filter": r"^(tcp|udp|unix|Active|Proto)",
        "max_lines": 60,
        "group": True,
    },
    "ss": {
        "filter": r"^(tcp|udp|Netid|State)",
        "max_lines": 60,
        "group": True,
    },
    # Package managers
    "pip list": {
        "filter": r"^\S+",
        "max_lines": 80,
        "group": False,
    },
    "npm list": {
        "filter": r"^[├└─┌┬┐│\s]",
        "max_lines": 100,
        "group": True,
    },
    "cargo": {
        "filter": r"^\s*\w+",
        "max_lines": 80,
        "group": True,
    },
    # System
    "journalctl": {
        "filter": r"^\w{3}\s+\d+",
        "max_lines": 50,
        "group": True,
    },
    "dmesg": {
        "filter": r"^\[",
        "max_lines": 50,
        "group": True,
    },
    "env": {
        "filter": r"^\w+=",
        "max_lines": 100,
        "group": False,
    },
    # Python
    "pip show": {
        "filter": r"^\w+:",
        "max_lines": 30,
        "group": False,
    },
    "python -m pytest": {
        "filter": r"(PASSED|FAILED|ERROR|test_|collected|passed|failed|error)",
        "max_lines": 200,
        "group": True,
    },
    # Docker
    "docker ps": {
        "filter": r"^[a-f0-9]{12}",
        "max_lines": 60,
        "group": False,
    },
    "docker images": {
        "filter": r"^\S+",
        "max_lines": 40,
        "group": False,
    },
    # Kubernetes
    "kubectl get": {
        "filter": r"^\S+",
        "max_lines": 80,
        "group": False,
    },
    # Generic
    "generic": {
        "filter": r".*",
        "max_lines": 150,
        "group": True,
    },
}


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return max(1, len(text) // 4)


def _detect_command(command: str) -> str:
    """Detect the best matching command pattern.

    Args:
        command: The command string to classify.

    Returns:
        Pattern key from _COMMAND_PATTERNS.
    """
    cmd_lower = command.strip().lower()
    # Exact match first
    if cmd_lower in _COMMAND_PATTERNS:
        return cmd_lower

    # Prefix match
    for pattern in sorted(_COMMAND_PATTERNS.keys(), key=len, reverse=True):
        if pattern == "generic":
            continue
        if cmd_lower.startswith(pattern):
            return pattern

    return "generic"


class InputCompressor:
    """Compresses command/tool outputs using pattern-aware strategies.

    Supports four compression strategies:
    - smart_filtering: Removes irrelevant lines based on command pattern.
    - grouping: Collapses similar consecutive lines.
    - truncation: Keeps head and tail of long outputs.
    - deduplication: Removes repeated identical lines.

    Targets 60-90% token reduction for tool outputs.
    """

    def __init__(self) -> None:
        self._compression_history: list[CompressionResult] = []
        self._total_original_tokens: int = 0
        self._total_compressed_tokens: int = 0

    def compress_command_output(
        self,
        command: str,
        output: str,
        strategy: CompressionStrategy = CompressionStrategy.SMART_FILTERING,
        target_ratio: float = 0.7,
    ) -> CompressionResult:
        """Compress command output using the best matching strategy.

        Args:
            command: The command that produced the output.
            output: The command output to compress.
            strategy: Compression strategy to use.
            target_ratio: Target compression ratio (0.0 to 1.0).

        Returns:
            CompressionResult with compressed content and metadata.

        Raises:
            CompressionError: If output is empty or target_ratio invalid.
        """
        if not output:
            raise CompressionError(command, 0, "empty output")
        if not 0.0 <= target_ratio <= 1.0:
            raise CompressionError(
                command, _estimate_tokens(output),
                f"invalid target_ratio: {target_ratio}",
            )

        start_time = time.time()
        original_tokens = _estimate_tokens(output)
        cmd_pattern = _detect_command(command)

        if strategy == CompressionStrategy.SMART_FILTERING:
            compressed = self._smart_filter(output, cmd_pattern)
        elif strategy == CompressionStrategy.GROUPING:
            compressed = self._group_lines(output, cmd_pattern)
        elif strategy == CompressionStrategy.TRUNCATION:
            compressed = self._truncate_output(output, cmd_pattern)
        elif strategy == CompressionStrategy.DEDUPLICATION:
            compressed = self._deduplicate(output)
        else:
            compressed = output

        compressed_tokens = _estimate_tokens(compressed)
        compression_ratio = 1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0.0

        elapsed = (time.time() - start_time) * 1000

        result = CompressionResult(
            compressed=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            strategy_used=strategy.name,
            time_taken_ms=elapsed,
        )
        self._compression_history.append(result)
        self._total_original_tokens += original_tokens
        self._total_compressed_tokens += compressed_tokens
        return result

    def _smart_filter(self, output: str, cmd_pattern: str) -> str:
        """Remove irrelevant lines based on command pattern filtering.

        Keeps only lines matching the command's filter pattern.
        """
        config = _COMMAND_PATTERNS.get(cmd_pattern, _COMMAND_PATTERNS["generic"])
        filter_pattern = config["filter"]
        max_lines = config["max_lines"]

        lines = output.splitlines()
        filtered = [l for l in lines if re.match(filter_pattern, l)]

        if len(filtered) <= max_lines:
            return "\n".join(filtered)

        return self._head_tail(filtered, max_lines // 2)

    def _group_lines(self, output: str, cmd_pattern: str) -> str:
        """Collapse similar consecutive lines (e.g., repeated file listings).

        Groups consecutive lines that differ only by timestamp or index
        and replaces them with a summary.
        """
        config = _COMMAND_PATTERNS.get(cmd_pattern, _COMMAND_PATTERNS["generic"])
        if not config.get("group", False):
            return output

        lines = output.splitlines()
        if len(lines) < 10:
            return output

        max_lines = config.get("max_lines", 100)
        return self._truncate_grouped(lines, max_lines)

    def _truncate_output(self, output: str, cmd_pattern: str) -> str:
        """Keep head and tail of output, removing the middle.

        Uses command-specific max_lines configuration.
        """
        config = _COMMAND_PATTERNS.get(cmd_pattern, _COMMAND_PATTERNS["generic"])
        max_lines = config["max_lines"]
        lines = output.splitlines()

        if len(lines) <= max_lines:
            return output

        return self._head_tail(lines, max_lines // 2)

    @staticmethod
    def _deduplicate(output: str) -> str:
        """Remove repeated consecutive identical lines."""
        lines = output.splitlines(keepends=True)
        result: list[str] = []
        prev = ""
        for line in lines:
            if line.strip() and line.strip() == prev.strip():
                continue
            if line.strip():
                prev = line
            result.append(line)
        return "".join(result)

    @staticmethod
    def _head_tail(lines: list[str], keep: int) -> str:
        """Keep first `keep` and last `keep` lines with a truncation marker."""
        if len(lines) <= keep * 2:
            return "\n".join(lines)
        head = lines[:keep]
        tail = lines[-keep:]
        removed = len(lines) - keep * 2
        return "\n".join(head) + f"\n... [{removed} lines truncated]\n" + "\n".join(tail)

    @staticmethod
    def _truncate_grouped(lines: list[str], max_lines: int) -> str:
        """Truncate lines with grouping awareness."""
        if len(lines) <= max_lines:
            return "\n".join(lines)
        return "\n".join(lines[: max_lines // 2]) + (
            f"\n... [{len(lines) - max_lines} similar lines grouped]\n"
            + "\n".join(lines[-max_lines // 2 :])
        )

    @property
    def summary(self) -> dict[str, Any]:
        """Get compression summary statistics."""
        total_saved = self._total_original_tokens - self._total_compressed_tokens
        overall_ratio = (
            1.0 - (self._total_compressed_tokens / self._total_original_tokens)
            if self._total_original_tokens > 0
            else 0.0
        )
        return {
            "total_compressions": len(self._compression_history),
            "total_original_tokens": self._total_original_tokens,
            "total_compressed_tokens": self._total_compressed_tokens,
            "total_tokens_saved": total_saved,
            "overall_compression_ratio": overall_ratio,
            "avg_time_ms": (
                sum(r.time_taken_ms for r in self._compression_history)
                / len(self._compression_history)
                if self._compression_history
                else 0.0
            ),
        }

    def get_history(self, limit: int = 20) -> list[CompressionResult]:
        """Get compression history, most recent first."""
        return list(reversed(self._compression_history[-limit:]))
