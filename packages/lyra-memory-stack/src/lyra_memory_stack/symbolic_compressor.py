"""Symbolic compressor — tool logs to lightweight symbols (TencentDB pattern).

Replaces verbose tool output with symbolic Mermaid-canvas-like
representations. Detailed logs remain queryable on demand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolicCanvas:
    """A compressed symbolic representation of tool output.

    Attributes:
        canvas_id: Unique identifier.
        summary: Human-readable summary.
        symbols: Key-value symbolic mappings.
        stats: Aggregated statistics.
        raw_ref: Reference to retrieve full raw output.
    """

    canvas_id: str
    summary: str
    symbols: tuple[tuple[str, str], ...]
    stats: dict[str, float]
    raw_ref: str


class SymbolicCompressor:
    """Compresses verbose tool outputs into symbolic canvases.

    Follows the TencentDB-Agent-Memory pattern: keep lightweight symbols
    in context, allow drill-down to full logs on demand.
    """

    def __init__(self) -> None:
        self._raw_store: dict[str, str] = {}
        self._counter = 0

    async def compress(self, tool_name: str, raw_output: str) -> SymbolicCanvas:
        """Compress tool output into a symbolic canvas.

        Args:
            tool_name: Name of the tool that produced the output.
            raw_output: The full raw output text.

        Returns:
            A SymbolicCanvas with extracted symbols and stats.
        """
        self._counter += 1
        canvas_id = f"canvas-{self._counter}"
        raw_ref = f"raw-{self._counter}"
        self._raw_store[raw_ref] = raw_output

        lines = raw_output.strip().split("\n")
        line_count = len(lines)
        char_count = len(raw_output)

        symbols: list[tuple[str, str]] = []
        symbols.append(("tool", tool_name))
        symbols.append(("lines", str(line_count)))
        symbols.append(("chars", str(char_count)))

        error_count = len(re.findall(r"(?i)error|exception|traceback|failed", raw_output))
        warning_count = len(re.findall(r"(?i)warning|warn|deprecat", raw_output))

        file_matches = re.findall(r"(?:^|\s)([/\w.-]+\.\w{1,6})", raw_output)
        if file_matches:
            symbols.append(("files_touched", ",".join(file_matches[:5])))

        summary_parts = [f"[{tool_name}] {line_count} lines, {char_count} chars"]
        if error_count > 0:
            summary_parts.append(f"{error_count} errors")
        if warning_count > 0:
            summary_parts.append(f"{warning_count} warnings")

        summary = " — ".join(summary_parts)

        stats = {
            "line_count": float(line_count),
            "char_count": float(char_count),
            "error_count": float(error_count),
            "warning_count": float(warning_count),
            "compression_ratio": (
                len(summary) / max(char_count, 1)
            ),
        }

        return SymbolicCanvas(
            canvas_id=canvas_id,
            summary=summary,
            symbols=tuple(symbols),
            stats=stats,
            raw_ref=raw_ref,
        )

    async def get_raw(self, raw_ref: str) -> str:
        """Retrieve the full raw output for a canvas reference.

        Args:
            raw_ref: The raw reference string.

        Returns:
            The original uncompressed output.
        """
        if raw_ref not in self._raw_store:
            raise KeyError(f"Raw output not found: {raw_ref}")
        return self._raw_store[raw_ref]

    async def compress_multi(
        self, outputs: tuple[tuple[str, str], ...]
    ) -> tuple[SymbolicCanvas, ...]:
        """Compress multiple tool outputs at once.

        Args:
            outputs: Tuple of (tool_name, raw_output) pairs.

        Returns:
            SymbolicCanvas for each input.
        """
        results = []
        for tool_name, raw_output in outputs:
            canvas = await self.compress(tool_name, raw_output)
            results.append(canvas)
        return tuple(results)

    @property
    def stored_raw_count(self) -> int:
        return len(self._raw_store)
