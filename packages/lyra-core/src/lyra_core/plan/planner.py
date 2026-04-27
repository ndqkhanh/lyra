"""Planner sub-loop: runs a read-only agent turn to produce a Plan artifact.

The Planner installs an aggressive pre-tool-use hook so *any* attempt to call
a write/edit tool is blocked with a loud error. This is Lyra's
``PermissionMode.PLAN`` contract enforced at the harness-core layer.

The Planner:
    - Uses a provided ``ToolRegistry`` (expected to include the read-only
      built-ins: Read / Glob / Grep).
    - Runs ``harness_core.AgentLoop`` with a Plan-Mode system prompt.
    - Scans the final transcript for the first plan artifact (``---\\n`` fence +
      ``# Plan: ...`` header), parses it, lints it, and returns it.

Failure paths are non-fatal: the caller inspects ``PlannerResult.plan`` is
``None`` and reads ``parse_error`` / ``lint_error`` to decide next steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from harness_core.hooks import Hook, HookDecision, HookEvent, HookRegistry
from harness_core.loop import AgentLoop
from harness_core.messages import Message, ToolCall, ToolResult
from harness_core.models import LLMProvider
from harness_core.observability import Tracer
from harness_core.permissions import PermissionMode
from harness_core.tools import ToolRegistry

from .artifact import Plan, PlanValidationError, load_plan

_PLANNER_SYSTEM_PROMPT = """You are the Planner for Lyra.

Produce a single plan artifact for the user's task. You have read-only tools
only; do not attempt to write, edit, or run mutating commands.

CRITICAL FORMAT REQUIREMENT
The first three characters of your response MUST be the literal "---".
Do not prepend ANY prose, quotation marks, code-fences, or explanation
before the frontmatter. The output is parsed by a strict-first cascade
that reads from byte zero — anything before the fence is dropped.

Output format (Markdown with YAML frontmatter), exactly:

---
session_id: <ulid>
created_at: <ISO-8601>
planner_model: <model-id>
estimated_cost_usd: <float>
goal_hash: sha256:<hex>
---

# Plan: <one-line title>

## Acceptance tests
- <test reference>

## Expected files
- <path>

## Forbidden files
- <path>

## Feature items
1. **(skill)** <description>

## Open questions
- <question>

## Notes
<free text>

Rules:
- Every feature item names an atomic skill (edit, test_gen, review, etc.).
- If acceptance_tests is empty, include a test_gen feature item.
- Be concise. Ask a question only if truly ambiguous.
- Never wrap the plan in a Markdown code-fence (no ``` lines).
- Never return JSON. The schema is Markdown + YAML frontmatter.
- Lyra's parser is tolerant of mistakes (prose prefix, code-fenced YAML,
  missing frontmatter, JSON, pure prose) but every recovery surface
  emits a `planner.format_drift` event the user can audit. Aim for
  the strict shape so your run shows up clean in `lyra doctor`.
"""

# Tool names considered "write" (block during plan mode).
_WRITE_TOOLS = {"Write", "Edit", "EditTool", "WriteTool", "Bash", "Shell"}


def _plan_mode_write_guard() -> Hook:
    """Pre-tool-use hook that denies any write/edit tool call."""

    def handler(call: ToolCall, _result: ToolResult | None) -> HookDecision:
        if call.name in _WRITE_TOOLS:
            return HookDecision(
                block=True,
                reason=(
                    f"Plan Mode denies write tool {call.name!r}; "
                    "Planner must remain read-only"
                ),
            )
        return HookDecision(block=False)

    return Hook(
        name="plan-mode-write-guard",
        event=HookEvent.PRE_TOOL_USE,
        matcher="*",
        handler=handler,
    )


@dataclass
class PlannerResult:
    plan: Plan | None = None
    transcript: list[Message] = field(default_factory=list)
    steps: int = 0
    cost_usd: float = 0.0
    blocked_write_attempts: int = 0
    parse_error: str | None = None
    lint_error: str | None = None


def _count_blocked_writes(transcript: list[Message]) -> int:
    n = 0
    for m in transcript:
        if m.role != "tool":
            continue
        for r in m.tool_results:
            if r.is_error and "Plan Mode denies write tool" in r.content:
                n += 1
    return n


def run_planner(
    task: str,
    *,
    llm: LLMProvider,
    tools: ToolRegistry,
    repo_root: Path,
    session_id: str,
    max_steps: int = 10,
    hooks: HookRegistry | None = None,
    tracer: Tracer | None = None,
) -> PlannerResult:
    """Run one Planner pass and return the produced plan (or failure diagnostics)."""
    hook_registry = hooks or HookRegistry()
    hook_registry.register(_plan_mode_write_guard())

    loop = AgentLoop(
        llm=llm,
        tools=tools,
        hooks=hook_registry,
        permission_mode=PermissionMode.DEFAULT,
        tracer=tracer or Tracer(),
        max_steps=max_steps,
        system_prompt=_PLANNER_SYSTEM_PROMPT,
    )

    outcome = loop.run(task)
    transcript = outcome.transcript
    blocked = _count_blocked_writes(transcript)

    final_assistant_texts: list[str] = [
        m.content for m in transcript if m.role == "assistant" and m.content
    ]
    candidate = "\n\n".join(final_assistant_texts)

    parse_error: str | None = None
    lint_error: str | None = None
    plan: Plan | None = None
    if not candidate.strip():
        parse_error = "planner produced no assistant text"
    else:
        try:
            plan = load_plan(candidate)
        except PlanValidationError as e:
            parse_error = str(e)
        else:
            try:
                plan.lint()
            except PlanValidationError as e:
                lint_error = str(e)
                plan = None

    return PlannerResult(
        plan=plan,
        transcript=transcript,
        steps=outcome.steps,
        cost_usd=0.0,  # cost integration lands in Phase 3 budgeter
        blocked_write_attempts=blocked,
        parse_error=parse_error,
        lint_error=lint_error,
    )
