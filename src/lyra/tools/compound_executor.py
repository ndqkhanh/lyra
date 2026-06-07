"""
Compound Executor — multi-step tool chain execution.

Provides ``CompoundExecutor`` for executing tool chains (pipe, parallel,
conditional) with per-step and per-chain timeouts, error propagation, and
partial result preservation.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from lyra.tools.registry import ToolResult


# ---------------------------------------------------------------------------
# Enums & Dataclasses
# ---------------------------------------------------------------------------


class ChainType(str, Enum):
    """Type of tool chain."""

    PIPE = "pipe"  # Sequential, output feeds next input
    PARALLEL = "parallel"  # All steps run independently
    CONDITIONAL = "conditional"  # If-then-else based on predicate


@dataclass(frozen=True)
class ChainStep:
    """A single step in a tool chain.

    Attributes:
        tool_name: Registered name of the tool to execute.
        params: Explicit keyword arguments for this step.
        timeout: Per-step timeout in seconds (None = use chain default).
        label: Optional label for result indexing.
    """

    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class ToolChain:
    """A chain of tool steps to execute.

    Attributes:
        steps: Ordered list of chain steps.
        chain_type: How steps relate to each other.
        description: Optional human-readable description.
        chain_timeout: Overall chain timeout in seconds (None = no limit).
        step_timeout: Default per-step timeout in seconds (None = no limit).
        predicate: For CONDITIONAL chains — callable that receives context
            and returns True/False to select the then/else branch.
        then_branch: Steps to run when predicate returns True.
        else_branch: Steps to run when predicate returns False.
    """

    steps: List[ChainStep] = field(default_factory=list)
    chain_type: ChainType = ChainType.PIPE
    description: Optional[str] = None
    chain_timeout: Optional[float] = None
    step_timeout: Optional[float] = None
    predicate: Optional[Callable[[Dict[str, Any]], bool]] = None
    then_branch: List[ChainStep] = field(default_factory=list)
    else_branch: List[ChainStep] = field(default_factory=list)


@dataclass(frozen=True)
class ChainResult:
    """Result of a chain execution.

    Attributes:
        success: True if all steps completed successfully.
        step_results: Ordered list of ToolResult for each step.
        chain_type: The type of chain that was executed.
        error: Overall error message if the chain failed.
        execution_time_ms: Total wall-clock time for the chain.
        partial: True if some steps succeeded before a failure (pipe/conditional).
    """

    success: bool
    step_results: List[ToolResult]
    chain_type: ChainType
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    partial: bool = False


# ---------------------------------------------------------------------------
# Chain expression parser
# ---------------------------------------------------------------------------

# Regex for a single step: tool_name(param1=val1, param2="val2") OR just tool_name
_STEP_PATTERN = re.compile(
    r"(?P<name>[a-zA-Z_][a-zA-Z0-9_.]*)"  # tool name
    r"(?:\((?P<params>[^)]*)\))?",  # optional parenthesised params
)

# Split on "|" for pipe, "||" for parallel
_PIPE_SEP = re.compile(r"\s*\|\|\s*")
_PARALLEL_SEP = re.compile(r"\s*\|(?:\|)\s*")


def _parse_params(text: str) -> Dict[str, Any]:
    """Parse ``key=value[,key=value]`` into a dict.

    Supports integers, floats, booleans, quoted strings, and bare words.
    """
    params: Dict[str, Any] = {}
    if not text or not text.strip():
        return params

    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        key, _, raw_val = part.partition("=")
        key = key.strip()
        raw = raw_val.strip()

        # Parse value
        if raw.startswith('"') and raw.endswith('"'):
            val = raw[1:-1]
        elif raw.startswith("'") and raw.endswith("'"):
            val = raw[1:-1]
        elif raw.lower() in ("true", "yes"):
            val = True
        elif raw.lower() in ("false", "no"):
            val = False
        elif raw.lower() in ("none", "null"):
            val = None
        else:
            try:
                if "." in raw:
                    val = float(raw)
                else:
                    val = int(raw)
            except ValueError:
                val = raw  # bare word
        params[key] = val
    return params


def parse_chain(expression: str) -> ToolChain:
    """Parse a chain expression string into a ``ToolChain``.

    Syntax
    ------
    - ``tool1 | tool2 | tool3`` — pipe chain (output flows into next input)
    - ``tool1(x=1) | tool2 | tool3(y="abc")`` — pipe with explicit params
    - ``tool1 || tool2 || tool3`` — parallel chain

    Parameters
    ----------
    expression:
        Chain expression string.

    Returns
    -------
    ``ToolChain`` with appropriate chain type and parsed steps.

    Raises
    ------
    ``ValueError`` if the expression cannot be parsed.
    """
    expression = expression.strip()
    if not expression:
        raise ValueError("Empty chain expression")

    # Detect chain type
    is_parallel = "||" in expression
    is_pipe = "|" in expression and not is_parallel

    if is_parallel:
        # Split on "||" (parallel)
        raw_steps = [s.strip() for s in re.split(r"\s*\|\|\s*", expression)]
        chain_type = ChainType.PARALLEL
    elif is_pipe:
        # Split on "|" (pipe)
        raw_steps = [s.strip() for s in re.split(r"\s*\|\s*", expression)]
        chain_type = ChainType.PIPE
    else:
        # Single step
        raw_steps = [expression]
        chain_type = ChainType.PIPE

    steps: List[ChainStep] = []
    for raw in raw_steps:
        m = _STEP_PATTERN.fullmatch(raw)
        if not m:
            raise ValueError(f"Cannot parse step: '{raw}'")
        tool_name = m.group("name")
        params_text = m.group("params")
        params = _parse_params(params_text) if params_text else {}
        steps.append(
            ChainStep(
                tool_name=tool_name,
                params=params,
            )
        )

    return ToolChain(steps=steps, chain_type=chain_type)


# ---------------------------------------------------------------------------
# Compound Executor
# ---------------------------------------------------------------------------

StepRunner = Callable[..., "asyncio.Future[ToolResult]"]


class CompoundExecutor:
    """Executor for multi-step tool chains.

    Wraps a step runner function (typically ``ToolExecutor.execute``) and
    provides chain-aware execution with data flow, timeouts, and error
    propagation.

    Parameters
    ----------
    run_step:
        Async callable ``(tool_name, timeout, **params) -> ToolResult``.
        Typically ``ToolExecutor.execute`` or ``ToolRegistry.run``.
    """

    def __init__(self, run_step: StepRunner) -> None:
        self._run_step = run_step

    # ------------------------------------------------------------------
    # Execute chain
    # ------------------------------------------------------------------

    async def execute_chain(
        self,
        chain: ToolChain,
        context: Optional[Dict[str, Any]] = None,
    ) -> ChainResult:
        """Execute a tool chain.

        Parameters
        ----------
        chain:
            The tool chain to execute.
        context:
            Initial context dict passed to the first step (pipe) or all steps
            (parallel).  Also available to the predicate for conditional chains.

        Returns
        -------
        ``ChainResult`` with step-level results.
        """
        ctx = dict(context or {})
        start = time.monotonic()

        if chain.chain_type == ChainType.CONDITIONAL:
            result = await self._execute_conditional(chain, ctx)
        elif chain.chain_type == ChainType.PARALLEL:
            result = await self._execute_parallel(chain, ctx)
        else:
            result = await self._execute_pipe(chain, ctx)

        elapsed = (time.monotonic() - start) * 1000
        object.__setattr__(result, "execution_time_ms", elapsed)
        return result

    # ------------------------------------------------------------------
    # Pipe chain
    # ------------------------------------------------------------------

    async def _execute_pipe(
        self,
        chain: ToolChain,
        context: Dict[str, Any],
    ) -> ChainResult:
        """Execute a pipe chain: output flows as input to the next step."""
        if not chain.steps:
            return ChainResult(
                success=True,
                step_results=[],
                chain_type=ChainType.PIPE,
            )

        step_results: List[ToolResult] = []
        current_ctx = dict(context)

        async def _run_with_timeout(
            step: ChainStep,
            merged_params: Dict[str, Any],
        ) -> ToolResult:
            timeout = step.timeout or chain.step_timeout
            coro = self._run_step(step.tool_name, timeout=timeout, **merged_params)
            if chain.chain_timeout:
                return await asyncio.wait_for(coro, timeout=chain.chain_timeout)
            return await coro

        for idx, step in enumerate(chain.steps):
            merged_params = {**current_ctx, **step.params}

            try:
                result = await _run_with_timeout(step, merged_params)
            except asyncio.TimeoutError:
                elapsed = (time.monotonic() - (time.monotonic() - 0)) * 1000
                result = ToolResult(
                    success=False,
                    error=f"Chain timed out after {chain.chain_timeout}s at step {idx}",
                    execution_time_ms=elapsed,
                )
                step_results.append(result)
                return ChainResult(
                    success=False,
                    step_results=step_results,
                    chain_type=ChainType.PIPE,
                    error=f"Chain timeout at step '{step.tool_name}'",
                    partial=len(step_results) > 1,
                )

            step_results.append(result)

            if not result.success:
                return ChainResult(
                    success=False,
                    step_results=step_results,
                    chain_type=ChainType.PIPE,
                    error=f"Step '{step.tool_name}' failed: {result.error}",
                    partial=len(step_results) > 1,
                )

            # Pass output as input to the next step
            if result.output:
                current_ctx["input"] = result.output

        return ChainResult(
            success=True,
            step_results=step_results,
            chain_type=ChainType.PIPE,
        )

    # ------------------------------------------------------------------
    # Parallel chain
    # ------------------------------------------------------------------

    async def _execute_parallel(
        self,
        chain: ToolChain,
        context: Dict[str, Any],
    ) -> ChainResult:
        """Execute all steps in parallel with the same context."""
        if not chain.steps:
            return ChainResult(
                success=True,
                step_results=[],
                chain_type=ChainType.PARALLEL,
            )

        async def run_one(step: ChainStep) -> ToolResult:
            merged_params = {**context, **step.params}
            timeout = step.timeout or chain.step_timeout
            try:
                coro = self._run_step(step.tool_name, timeout=timeout, **merged_params)
                if chain.chain_timeout:
                    return await asyncio.wait_for(coro, timeout=chain.chain_timeout)
                return await coro
            except asyncio.TimeoutError:
                return ToolResult(
                    success=False,
                    error=f"Step '{step.tool_name}' timed out",
                )

        tasks = [run_one(step) for step in chain.steps]
        step_results: List[ToolResult] = await asyncio.gather(*tasks)

        # Parallel: report overall success (all steps pass)
        failures = [(i, r) for i, r in enumerate(step_results) if not r.success]
        if failures:
            failed_names = [chain.steps[i].tool_name for i, _ in failures]
            return ChainResult(
                success=False,
                step_results=step_results,
                chain_type=ChainType.PARALLEL,
                error=f"Steps failed: {', '.join(failed_names)}",
                partial=True,
            )

        return ChainResult(
            success=True,
            step_results=step_results,
            chain_type=ChainType.PARALLEL,
        )

    # ------------------------------------------------------------------
    # Conditional chain
    # ------------------------------------------------------------------

    async def _execute_conditional(
        self,
        chain: ToolChain,
        context: Dict[str, Any],
    ) -> ChainResult:
        """Execute a conditional chain (if-then-else).

        The ``chain.predicate`` must be set.  The predicate receives the
        context dict and returns True to execute ``then_branch``, or False
        to execute ``else_branch``.
        """
        if chain.predicate is None:
            return ChainResult(
                success=False,
                step_results=[],
                chain_type=ChainType.CONDITIONAL,
                error="Conditional chain has no predicate",
            )

        try:
            branch = chain.then_branch if chain.predicate(context) else chain.else_branch
        except Exception as exc:
            return ChainResult(
                success=False,
                step_results=[],
                chain_type=ChainType.CONDITIONAL,
                error=f"Predicate raised: {exc}",
            )

        if not branch:
            return ChainResult(
                success=True,
                step_results=[],
                chain_type=ChainType.CONDITIONAL,
            )

        # Execute the chosen branch as a sub-pipe chain
        sub_chain = ToolChain(
            steps=branch,
            chain_type=ChainType.PIPE,
            chain_timeout=chain.chain_timeout,
            step_timeout=chain.step_timeout,
        )
        sub_result = await self._execute_pipe(sub_chain, context)
        # Preserve the original chain_type on the result
        return ChainResult(
            success=sub_result.success,
            step_results=sub_result.step_results,
            chain_type=ChainType.CONDITIONAL,
            error=sub_result.error,
            execution_time_ms=sub_result.execution_time_ms,
            partial=sub_result.partial,
        )
