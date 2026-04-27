"""tdd-gate hook (Phase 1 stub).

Phase 1 contract: block writes/edits to ``src/**`` when no RED proof is present.
Writes to ``tests/**`` are always allowed (they ARE the RED proof).

Full contract (Phase 4, see docs/tdd-discipline.md):
    - RED proof validation (the test genuinely fails, not syntax-error)
    - coverage regression detection on POST
    - focused-test run on POST
    - full suite on Stop
    - escape hatch ``--no-tdd`` with audit trail
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from harness_core.hooks import HookDecision
from harness_core.messages import ToolCall, ToolResult

WRITE_TOOL_NAMES = frozenset({"Write", "Edit", "MultiEdit"})


@dataclass
class TDDGateContext:
    """Context the gate needs at each invocation.

    Phase 1 keeps this simple; Phase 4 will replace ``red_proof_present`` with
    a validated structure (failing test path, last run result hash, coverage
    delta, timestamps).
    """

    repo_root: str
    red_proof_present: bool = False
    enabled: bool = True


def _is_test_path(path: str) -> bool:
    p = path.lstrip("./")
    return (
        p.startswith("tests/")
        or p.startswith("test/")
        or "/tests/" in p
        or p.endswith("_test.py")
        or p.split("/")[-1].startswith("test_")
    )


def _is_src_path(path: str) -> bool:
    p = path.lstrip("./")
    return (
        p.startswith("src/")
        or p.startswith("app/")
        or p.startswith("lib/")
        or p.startswith("packages/")
    )


def make_tdd_gate_hook(
    ctx: TDDGateContext,
    *,
    event: Literal["PRE", "POST"] = "PRE",
) -> Callable[[ToolCall, ToolResult | None], HookDecision]:
    """Return a hook handler closed over ``ctx``.

    PRE handler: block writes to src/** without red proof.
    POST handler: advisory only — annotates but does not block.
    """

    def _pre(call: ToolCall, _result: ToolResult | None) -> HookDecision:
        if call.name not in WRITE_TOOL_NAMES:
            return HookDecision(block=False)

        if not ctx.enabled:
            return HookDecision(
                block=False,
                annotation="tdd-gate: disabled via --no-tdd (skipped, audit-logged)",
            )

        path = call.args.get("path") or call.args.get("file_path") or ""
        if not isinstance(path, str) or not path:
            return HookDecision(
                block=True,
                reason="tdd-gate: write tool called without a path arg",
            )

        if _is_test_path(path):
            return HookDecision(
                block=False,
                annotation=f"tdd-gate: test edit to {path!r} allowed in any phase",
            )

        if _is_src_path(path):
            if not ctx.red_proof_present:
                return HookDecision(
                    block=True,
                    reason=(
                        f"tdd-gate: production write to {path!r} rejected; "
                        "no RED proof present (write a failing test first)"
                    ),
                )
            return HookDecision(
                block=False,
                annotation="tdd-gate: RED proof present; production edit allowed",
            )

        return HookDecision(block=False)

    def _post(call: ToolCall, _result: ToolResult | None) -> HookDecision:
        if call.name not in WRITE_TOOL_NAMES:
            return HookDecision(block=False)
        return HookDecision(
            block=False,
            annotation="tdd-gate post: Phase 1 stub (focused-test run arrives in Phase 4)",
        )

    return _pre if event == "PRE" else _post
