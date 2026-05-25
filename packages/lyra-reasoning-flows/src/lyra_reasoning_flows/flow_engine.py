from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .exceptions import FlowCompositionError


class FlowPattern(str, Enum):
    SEQUENTIAL = "sequential"
    BRANCHING = "branching"
    REFLECTIVE = "reflective"
    META = "meta"


@dataclass(frozen=True)
class FlowStep:
    step_type: str
    action: str
    next_steps: tuple[str, ...] = ()
    condition: str | None = None


@dataclass(frozen=True)
class FlowDefinition:
    steps: tuple[FlowStep, ...]
    pattern: FlowPattern
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FlowResult:
    outputs: dict[str, Any]
    trace: tuple[dict[str, Any], ...] = ()
    metrics: dict[str, float] = field(default_factory=dict)


async def _noop_step(action: str, context: dict[str, Any]) -> dict[str, Any]:
    """Default step handler that records the action."""
    return {
        "step": action,
        "status": "completed",
        "output": f"Executed {action}",
    }


class FlowEngine:
    """Composable reasoning flows engine supporting four flow families.

    Flow families:
      SEQUENTIAL: Plan -> Execute -> Verify -> Reflect
      BRANCHING:  Plan -> [Branch A, B, C] -> Merge -> Conclude
      REFLECTIVE: Generate -> Self-Critique -> Revise -> Finalize
      META:       Observe reasoning -> Identify patterns -> Update strategies
    """

    def __init__(self) -> None:
        self._step_handlers: dict[
            str, Callable[[str, dict[str, Any]], dict[str, Any]]
        ] = {}
        self._composition_cache: dict[str, FlowDefinition] = {}

    def register_step_handler(
        self,
        step_type: str,
        handler: Callable[[str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._step_handlers[step_type] = handler

    async def execute_flow(
        self,
        flow_def: FlowDefinition,
        context: dict[str, Any] | None = None,
    ) -> FlowResult:
        ctx = context or {}
        outputs: dict[str, Any] = {}
        trace: list[dict[str, Any]] = []
        start = time.time()

        if flow_def.pattern == FlowPattern.SEQUENTIAL:
            outputs = await self._execute_sequential(flow_def, ctx, trace)
        elif flow_def.pattern == FlowPattern.BRANCHING:
            outputs = await self._execute_branching(flow_def, ctx, trace)
        elif flow_def.pattern == FlowPattern.REFLECTIVE:
            outputs = await self._execute_reflective(flow_def, ctx, trace)
        elif flow_def.pattern == FlowPattern.META:
            outputs = await self._execute_meta(flow_def, ctx, trace)
        else:
            raise FlowCompositionError(f"Unknown flow pattern: {flow_def.pattern}")

        elapsed = time.time() - start
        metrics: dict[str, float] = {
            "duration_seconds": elapsed,
            "num_steps": float(len(flow_def.steps)),
            "num_executed": float(len(trace)),
        }

        return FlowResult(outputs=outputs, trace=tuple(trace), metrics=metrics)

    def compose(
        self,
        capabilities_needed: list[str],
        context: dict[str, Any] | None = None,
    ) -> FlowDefinition:
        ctx = context or {}
        cache_key = str(sorted(capabilities_needed))

        if cache_key in self._composition_cache:
            return self._composition_cache[cache_key]

        pattern = self._select_pattern(capabilities_needed, ctx)
        steps = self._build_steps(capabilities_needed, pattern)
        flow = FlowDefinition(steps=steps, pattern=pattern)
        self._composition_cache[cache_key] = flow
        return flow

    async def _execute_sequential(
        self,
        flow_def: FlowDefinition,
        ctx: dict[str, Any],
        trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        for step in flow_def.steps:
            result = await self._run_step(step, ctx)
            outputs[step.step_type] = result
            trace.append({"step": step.step_type, "action": step.action, "result": result})
        return outputs

    async def _execute_branching(
        self,
        flow_def: FlowDefinition,
        ctx: dict[str, Any],
        trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        branches: dict[str, list[dict[str, Any]]] = {}

        for step in flow_def.steps:
            if step.step_type == "merge":
                # Merge phase: aggregate branch outputs.
                merged: dict[str, Any] = {}
                for branch_name, branch_outputs in branches.items():
                    merged[branch_name] = branch_outputs
                outputs["merged"] = merged
                result = await self._run_step(step, ctx)
                outputs["conclusion"] = result
                trace.append({"step": "merge", "action": step.action, "result": result})
            elif step.step_type == "branch":
                branches[step.action] = []
                result = await self._run_step(step, ctx)
                branches[step.action].append(result)
            else:
                result = await self._run_step(step, ctx)
                outputs[step.step_type] = result
                trace.append({"step": step.step_type, "action": step.action, "result": result})

        return outputs

    async def _execute_reflective(
        self,
        flow_def: FlowDefinition,
        ctx: dict[str, Any],
        trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        max_iterations = ctx.get("max_reflections", 3)
        iteration = 0
        current_output: dict[str, Any] = {}

        for step in flow_def.steps:
            if step.step_type == "revise":
                # Revise in a loop with critique feedback.
                last_critique = outputs.get("critique", "")
                while iteration < max_iterations:
                    result = await self._run_step(step, ctx)
                    current_output[step.action] = result
                    trace.append(
                        {"step": f"revise_{iteration}", "action": step.action, "result": result}
                    )
                    iteration += 1
                    if last_critique and "reject" not in str(last_critique):
                        break
                outputs[step.step_type] = current_output
            else:
                result = await self._run_step(step, ctx)
                outputs[step.step_type] = result
                trace.append({"step": step.step_type, "action": step.action, "result": result})

        return outputs

    async def _execute_meta(
        self,
        flow_def: FlowDefinition,
        ctx: dict[str, Any],
        trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        for step in flow_def.steps:
            result = await self._run_step(step, ctx)
            step_type = step.step_type
            if step_type not in outputs:
                outputs[step_type] = []
            if isinstance(outputs[step_type], list):
                outputs[step_type].append(result)
            trace.append({"step": step.step_type, "action": step.action, "result": result})

        # Summarize strategies.
        if "identify_patterns" in outputs:
            outputs["summary"] = {
                "patterns_identified": len(outputs.get("identify_patterns", [])),
                "strategies_updated": len(outputs.get("update_strategies", [])),
            }

        return outputs

    async def _run_step(
        self, step: FlowStep, ctx: dict[str, Any]
    ) -> dict[str, Any]:
        handler = self._step_handlers.get(step.step_type, _noop_step)
        return await _run_handler(handler, step.action, ctx)

    def _select_pattern(
        self, capabilities: list[str], ctx: dict[str, Any]
    ) -> FlowPattern:
        if "reflect" in capabilities or "critique" in capabilities:
            return FlowPattern.REFLECTIVE
        if "branch" in capabilities or "parallel" in capabilities:
            return FlowPattern.BRANCHING
        if "monitor" in capabilities or "observe" in capabilities:
            return FlowPattern.META
        return FlowPattern.SEQUENTIAL

    def _build_steps(
        self, capabilities: list[str], pattern: FlowPattern
    ) -> tuple[FlowStep, ...]:
        if pattern == FlowPattern.REFLECTIVE:
            return (
                FlowStep(step_type="generate", action="generate_answer"),
                FlowStep(step_type="critique", action="self_critique", next_steps=("revise",)),
                FlowStep(step_type="revise", action="revise_answer", condition="critique_score < 0.8"),
                FlowStep(step_type="finalize", action="finalize_answer"),
            )

        if pattern == FlowPattern.BRANCHING:
            branches: tuple[FlowStep, ...] = ()
            for cap in capabilities:
                if cap not in ("branch", "parallel", "merge"):
                    branches += (FlowStep(step_type="branch", action=f"branch_{cap}"),)
            return branches + (
                FlowStep(step_type="merge", action="merge_branches"),
                FlowStep(step_type="conclude", action="conclude"),
            )

        if pattern == FlowPattern.META:
            return (
                FlowStep(step_type="observe", action="observe_reasoning"),
                FlowStep(step_type="identify_patterns", action="identify_patterns"),
                FlowStep(step_type="update_strategies", action="update_strategies"),
            )

        # SEQUENTIAL default.
        return (
            FlowStep(step_type="plan", action="create_plan"),
            FlowStep(step_type="execute", action="execute_plan"),
            FlowStep(step_type="verify", action="verify_result"),
            FlowStep(step_type="reflect", action="reflect_on_result"),
        )


async def _run_handler(
    handler: Callable[[str, dict[str, Any]], dict[str, Any]],
    action: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Wrapper to handle both sync and async handlers."""
    result = handler(action, context)
    if hasattr(result, "__await__"):
        return await result
    return result
