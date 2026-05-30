"""Code-Execution-as-Tool-Primitive — batch tool calls into code blocks.

Inspired by the Anthropic Engineering Blog pattern: instead of N sequential
LLM round-trips for N tool calls, execute them as a batch within a single
code block. Each round-trip saves ~full context tokens.

Token savings: for a batch of N tool calls, only 1 round-trip instead of N.
With typical context sizes, this approaches 98.7% reduction in tool-call tokens.

Safety: executed code blocks are restricted to registered tool calls —
arbitrary Python is NOT evaluated. Tools still pass through annotation-based
permission gating.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .messages import ToolCall, ToolResult
from .tools import ToolPermissionGate, ToolRegistry


@dataclass
class BatchSpec:
    """A batch of tool calls to execute sequentially within a single code block.

    Each call references a registered tool by name with typed arguments.
    Execution stops on first error unless ``continue_on_error`` is True.
    """

    calls: list[ToolCall]
    continue_on_error: bool = False
    label: str = ""  # human-readable label for logging/debugging


@dataclass
class BatchResult:
    """Aggregated result from executing a batch of tool calls."""

    label: str = ""
    results: list[ToolResult] = field(default_factory=list)
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    tokens_saved: int = 0  # estimated context tokens saved by batching
    elapsed_ms: float = 0.0

    @property
    def all_succeeded(self) -> bool:
        return self.error_count == 0

    @property
    def combined_output(self) -> str:
        """Combined output suitable for returning to the LLM."""
        parts: list[str] = []
        for i, r in enumerate(self.results):
            status = "OK" if not r.is_error else "ERROR"
            parts.append(f"[{i}] {status}: {r.content}")
        return "\n".join(parts)


class BatchExecutor:
    """Executes batches of tool calls within a single code block context.

    Wraps a ToolRegistry with optional permission gating. Each batch
    executes all calls sequentially — no LLM round-trips between calls.

    Usage::

        executor = BatchExecutor(registry)
        batch = BatchSpec(calls=[
            ToolCall(id="c1", name="echo", args={"text": "hello"}),
            ToolCall(id="c2", name="calculator", args={"expression": "2+3"}),
        ])
        result = executor.execute(batch)
        # result.combined_output → "[0] OK: hello\\n[1] OK: 5"
    """

    def __init__(
        self,
        registry: ToolRegistry,
        permission_gate: ToolPermissionGate | None = None,
    ) -> None:
        self._registry = registry
        self._gate = permission_gate

    def execute(self, batch: BatchSpec) -> BatchResult:
        import time

        started = time.monotonic()
        results: list[ToolResult] = []
        success = 0
        errors = 0

        for call in batch.calls:
            result = self._registry.execute(call, permission_gate=self._gate)
            results.append(result)
            if result.is_error:
                errors += 1
                if not batch.continue_on_error:
                    # Stop on first error (default)
                    break
            else:
                success += 1

        elapsed = (time.monotonic() - started) * 1000

        # Token savings: N calls would be N round-trips, we use 1.
        # Each round-trip saves ~full context (conservatively estimate 2000 tokens)
        n = len(batch.calls)
        saved = (n - 1) * 2000 if n > 1 else 0

        return BatchResult(
            label=batch.label,
            results=results,
            total_calls=len(batch.calls),
            success_count=success,
            error_count=errors,
            tokens_saved=max(0, saved),
            elapsed_ms=round(elapsed, 2),
        )

    @property
    def registry(self) -> ToolRegistry:
        return self._registry


@dataclass
class CodeBlock:
    """Represents a code block submitted by the LLM for batched execution.

    The language determines how calls are parsed:
    - ``lyra-tools``: native JSON list of ToolCall specs
    - ``python``: reserved for future sandboxed Python support
    """

    language: str  # "lyra-tools" | "python" (reserved)
    code: str
    source: str = ""  # which model/agent submitted this block


def parse_batch_from_json(json_text: str, label: str = "") -> BatchSpec:
    """Parse a JSON array of tool call specs into a BatchSpec.

    Expected format::

        [
            {"id": "c1", "name": "echo", "args": {"text": "hello"}},
            {"id": "c2", "name": "calculator", "args": {"expression": "40+2"}}
        ]
    """
    import json as _json

    raw = _json.loads(json_text)
    if not isinstance(raw, list):
        raise ValueError("Batch JSON must be a list of tool call objects")

    calls: list[ToolCall] = []
    for i, item in enumerate(raw):
        calls.append(
            ToolCall(
                id=item.get("id", f"b{i}"),
                name=item["name"],
                args=item.get("args", {}),
            )
        )

    return BatchSpec(calls=calls, label=label)
