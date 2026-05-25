"""Symbolic compression — Tool execution logs to compact symbolic representations.

Uses a TencentDB-inspired pattern to transform verbose tool execution logs into
compact Mermaid-style diagram symbols with node_id references for drill-down,
targeting 10x compression of token budget.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from lyra_memory_stack.exceptions import CompressionError


@dataclass(frozen=True)
class ToolCall:
    """A single tool execution record to be compressed."""

    tool_name: str
    arguments: dict[str, Any]
    result: str | None = None
    duration_ms: float = 0.0
    status: str = "success"
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class CompressedSymbol:
    """A compressed symbolic representation of a tool call."""

    node_id: str
    symbol_type: str
    label: str
    summary: str
    raw_token_count: int
    compressed_token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


SYMBOL_TYPES: dict[str, str] = {
    "read": "RD",
    "write": "WR",
    "search": "SR",
    "execute": "EX",
    "think": "TH",
    "observe": "OB",
    "error": "ER",
    "tool_call": "TC",
    "tool_result": "TR",
    "branch": "BR",
    "merge": "MG",
    "condition": "CD",
    "loop": "LP",
    "subgraph": "SG",
}

# Reverse mapping
TYPE_FROM_SYMBOL: dict[str, str] = {v: k for k, v in SYMBOL_TYPES.items()}


def _infer_symbol_type(tool_name: str) -> str:
    """Infer the symbol type from a tool name."""
    tl = tool_name.lower()
    if any(x in tl for x in ("read", "get", "list", "fetch", "query")):
        return "read"
    if any(x in tl for x in ("write", "create", "update", "put", "post")):
        return "write"
    if any(x in tl for x in ("search", "find", "grep")):
        return "search"
    if any(x in tl for x in ("execute", "run", "bash", "shell")):
        return "execute"
    if any(x in tl for x in ("think", "reason", "analyze")):
        return "think"
    if any(x in tl for x in ("observe", "watch", "monitor")):
        return "observe"
    return "tool_call"


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, appending '...' if truncated."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token)."""
    return max(1, len(text) // 4)


def _make_node_id(tool_name: str, index: int) -> str:
    """Create a deterministic node ID for a tool call."""
    raw = f"{tool_name}:{index}:{time.time():.0f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


class SymbolicCompressor:
    """Compresses tool execution logs into compact symbolic representations."""

    _min_token_saving: int

    def __init__(self, min_token_saving: int = 10) -> None:
        self._min_token_saving = min_token_saving

    def compress_call(self, call: ToolCall, index: int = 0) -> CompressedSymbol:
        """Compress a single tool call into a symbolic representation."""
        node_id = _make_node_id(call.tool_name, index)
        symbol_type = _infer_symbol_type(call.tool_name)
        symbol_code = SYMBOL_TYPES.get(symbol_type, "TC")

        # Build compact label
        args_summary = _truncate(json.dumps(call.arguments, separators=(",", ":")), 80)
        label = f"{symbol_code}[{call.tool_name}]"
        summary = f"{label} {args_summary}"

        raw_tokens = _estimate_tokens(json.dumps({
            "tool": call.tool_name,
            "args": call.arguments,
            "result": call.result,
            "duration": call.duration_ms,
        }))

        compressed = _estimate_tokens(summary)

        if compressed >= raw_tokens - self._min_token_saving:
            summary = f"{label} {len(call.arguments)} args, {call.duration_ms:.0f}ms"

        compressed = _estimate_tokens(summary)

        return CompressedSymbol(
            node_id=node_id,
            symbol_type=symbol_type,
            label=label,
            summary=summary,
            raw_token_count=raw_tokens,
            compressed_token_count=compressed,
            metadata={
                "tool_name": call.tool_name,
                "duration_ms": call.duration_ms,
                "status": call.status,
                "timestamp": call.timestamp,
            },
        )

    def compress_calls(self, calls: list[ToolCall]) -> list[CompressedSymbol]:
        """Compress a sequence of tool calls."""
        return [self.compress_call(call, i) for i, call in enumerate(calls)]

    def build_mermaid_sequence(self, symbols: list[CompressedSymbol]) -> str:
        """Build a Mermaid sequence diagram from compressed symbols."""
        if not symbols:
            return "sequenceDiagram\n    note over Agent: No calls"

        lines: list[str] = ["sequenceDiagram"]
        last_type: str | None = None

        for sym in symbols:
            node_ref = f"[[{sym.node_id}]]"
            if sym.symbol_type == "error" or sym.metadata.get("status") == "error":
                label = f"Note over Agent: !! {sym.summary}"
            elif sym.symbol_type == "think":
                label = f"Note over Agent: {_truncate(sym.summary, 60)}"
            elif sym.symbol_type == "branch":
                label = f"Agent->>Branch: {sym.label} {node_ref}"
            elif last_type and sym.symbol_type != last_type:
                label = f"Agent->>Tool: {sym.label} {node_ref}"
            else:
                label = f"Agent->>Tool: {sym.label} {node_ref}"
            lines.append(f"    {label}")
            last_type = sym.symbol_type

        return "\n".join(lines)

    def build_mermaid_graph(self, symbols: list[CompressedSymbol]) -> str:
        """Build a Mermaid flow graph from compressed symbols."""
        if not symbols:
            return "flowchart TD\n    start[No calls]"

        lines: list[str] = ["flowchart TD"]
        for i, sym in enumerate(symbols):
            node_id = f"N{i}"
            safe_label = sym.summary.replace('"', "'")
            lines.append(f"    {node_id}[\"{safe_label}\"]")
            if i > 0:
                lines.append(f"    N{i - 1} --> {node_id}")

        return "\n".join(lines)

    def compression_ratio(self, symbols: list[CompressedSymbol]) -> float:
        """Compute the compression ratio (raw / compressed)."""
        raw_total = sum(s.raw_token_count for s in symbols)
        comp_total = sum(s.compressed_token_count for s in symbols)
        if comp_total == 0:
            return 0.0
        return round(raw_total / comp_total, 2)

    def expand_node(self, node_id: str, symbols: list[CompressedSymbol]) -> CompressedSymbol | None:
        """Retrieve the full compressed symbol for a node_id (drill-down)."""
        for sym in symbols:
            if sym.node_id == node_id:
                return sym
        return None

    def compress_logs(
        self,
        raw_logs: str,
        tool_name: str = "generic",
    ) -> CompressedSymbol:
        """Compress a raw log string into a single symbol entry."""
        if not raw_logs.strip():
            raise CompressionError(tool_name, "Empty log content")
        lines = raw_logs.strip().split("\n")
        call = ToolCall(
            tool_name=tool_name,
            arguments={"lines": len(lines)},
            result=_truncate(raw_logs, 200),
            status="success",
        )
        return self.compress_call(call, index=0)
