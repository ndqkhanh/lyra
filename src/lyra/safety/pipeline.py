"""
Defense-in-depth safety pipeline for Lyra (P3).

Architecture
------------
SafetyPipeline orchestrates 5 layers of defense:

1. LexicalGate — fast regex scan for known-dangerous patterns (19ms target)
2. ToolCallGate — delegates to P2's deterministic ToolGate
3. AlignmentCheck — separate LLM call to verify task alignment (sampling)
4. DataFlowTracker — track untrusted data propagation
5. ContinuousEval — stub for self-evolving safety evaluation

Each layer returns a LayerResult (PASS, BLOCK, ESCALATE).
The pipeline stops at the first BLOCK and logs all decisions.

Usage::

    pipeline = SafetyPipeline()
    context = SafetyContext(
        tool_name="Bash",
        tool_args={"command": "ls -la"},
        task_description="List files",
    )
    decision = pipeline.evaluate(context)
    # decision.result == LayerResult.PASS
    # pipeline.decision_log contains all 5 layer decisions
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from lyra.safety.policy import GateDecision, Policy
from lyra.safety.tool_gate import ToolGate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


class LayerResult(str, Enum):
    """Result of a single safety layer evaluation.

    Three possible outcomes:
    * ``PASS`` — Layer found no issues. Pipeline continues.
    * ``BLOCK`` — Layer found a definitive violation. Pipeline stops.
    * ``ESCALATE`` — Layer found a potential issue requiring human review.
        Pipeline continues (non-blocking alert).
    """

    PASS = "pass"
    BLOCK = "block"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class LayerDecision:
    """Decision returned by a single safety layer evaluation.

    Attributes:
        result: The outcome (PASS, BLOCK, or ESCALATE).
        layer_name: Machine-readable name of the layer (e.g. "lexical_gate").
        reason: Human-readable explanation of the decision.
        details: Optional structured data (matched pattern, tainted values).
    """

    result: LayerResult
    layer_name: str
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SafetyContext:
    """Context passed through the safety pipeline for each tool call.

    Attributes:
        tool_name: Name of the tool being invoked.
        tool_args: Arguments to the tool.
        agent_id: Identifier for the calling agent.
        session_id: Session identifier for the current conversation.
        task_description: High-level description of the overall task, used
            by AlignmentCheck to verify tool-call alignment.
        untrusted_inputs: Substrings that originate from untrusted sources
            (user input, web content, file reads) for data-flow tracking.
        call_number: Sequential call number, used by AlignmentCheck to
            implement its sampling schedule.
        metadata: Additional contextual metadata for future extensibility.
    """

    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    session_id: str = ""
    task_description: str = ""
    untrusted_inputs: Tuple[str, ...] = ()
    call_number: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Layer 1: LexicalGate
# ---------------------------------------------------------------------------

# Pre-compiled dangerous patterns for fast regex scanning.
# Each entry: (compiled_pattern, category_name, human_description)
# Categories are used in log messages and decision details.
_DANGEROUS_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"`[^`]*`"),
        "shell_backtick",
        "Shell command substitution via backtick",
    ),
    (
        re.compile(r"\$\([^)]*\)"),
        "shell_subshell",
        "Shell command substitution via $()",
    ),
    (
        re.compile(
            r"[|;]\s*(?:rm|sudo|dd|mkfs|chmod|chown|shutdown|reboot)\b"
        ),
        "shell_dangerous_cmd",
        "Shell dangerous command via pipe or semicolon",
    ),
    (
        re.compile(r"\beval\s*\("),
        "eval_call",
        "eval() function call",
    ),
    (
        re.compile(r"\bexec\s*\("),
        "exec_call",
        "exec() function call",
    ),
    (
        re.compile(r"(?:^|[\s\"'/\\])\.\.[\\/]"),
        "path_traversal",
        "Path traversal (../)",
    ),
    (
        re.compile(r"/etc/(?:passwd|shadow|sudoers)\b"),
        "sensitive_file",
        "Access to sensitive system file",
    ),
    (
        re.compile(r"/root/"),
        "root_path",
        "Access to /root directory",
    ),
    (
        re.compile(r"__import__\s*\("),
        "dynamic_import",
        "Dynamic import via __import__()",
    ),
    (
        re.compile(r"os\.system\s*\("),
        "os_system",
        "os.system() call",
    ),
    (
        re.compile(r"subprocess\.(?:call|Popen|run|check_call)\s*\("),
        "subprocess_call",
        "subprocess module call",
    ),
]


class LexicalGate:
    """Layer 1: Fast regex scan for known-dangerous patterns.

    Uses pre-compiled regex patterns for maximum throughput (target:
    19ms per evaluation).  Operates on all string values extracted
    from the tool-call context (tool name + all arguments flattened).

    This is the first line of defense — fast and aggressive.  False
    positives are acceptable here because subsequent layers provide
    deeper analysis.
    """

    __slots__ = ()

    def evaluate(self, context: SafetyContext) -> LayerDecision:
        """Scan the tool call context for dangerous lexical patterns.

        Args:
            context: Safety context for the current tool call.

        Returns:
            BLOCK if a dangerous pattern is found; PASS otherwise.
        """
        strings_to_scan = self._extract_strings(context.tool_name)
        strings_to_scan.extend(self._extract_strings(context.tool_args))

        for string_val in strings_to_scan:
            for pattern, category, description in _DANGEROUS_PATTERNS:
                match = pattern.search(string_val)
                if match:
                    logger.warning(
                        "LexicalGate: BLOCK — pattern '%s' matched '%s'",
                        category,
                        match.group()[:80],
                    )
                    return LayerDecision(
                        result=LayerResult.BLOCK,
                        layer_name="lexical_gate",
                        reason=(
                            f"Dangerous pattern detected: "
                            f"{category} ({description})"
                        ),
                        details={
                            "pattern_category": category,
                            "matched_string": match.group()[:200],
                            "source": string_val[:200],
                        },
                    )

        return LayerDecision(
            result=LayerResult.PASS,
            layer_name="lexical_gate",
            reason="No dangerous patterns detected",
        )

    @staticmethod
    def _extract_strings(obj: Any) -> List[str]:
        """Recursively extract all string values from a nested structure.

        Handles dicts, lists, tuples, and primitive types.  Non-string
        primitives are converted for scanning.

        Args:
            obj: The value to extract strings from.

        Returns:
            A flat list of all string representations found.
        """
        strings: List[str] = []
        if isinstance(obj, str):
            strings.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                strings.extend(LexicalGate._extract_strings(v))
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                strings.extend(LexicalGate._extract_strings(item))
        elif obj is not None:
            strings.append(str(obj))
        return strings


# ---------------------------------------------------------------------------
# Layer 2: ToolCallGate
# ---------------------------------------------------------------------------

_GATE_DECISION_MAP: Dict[GateDecision, LayerResult] = {
    GateDecision.ALLOW: LayerResult.PASS,
    GateDecision.ALLOW_WITH_SANDBOX: LayerResult.PASS,
    GateDecision.ASK_USER: LayerResult.ESCALATE,
    GateDecision.BLOCK: LayerResult.BLOCK,
}


class ToolCallGateLayer:
    """Layer 2: Delegates to P2's deterministic ToolGate.

    Wraps ``ToolGate.validate()`` and maps the resulting ``GateDecision``
    to the P3 ``LayerResult`` vocabulary:

    * ALLOW / ALLOW_WITH_SANDBOX -> PASS
    * ASK_USER -> ESCALATE
    * BLOCK -> BLOCK
    """

    __slots__ = ("_gate", "_policy")

    def __init__(
        self,
        tool_gate: Optional[ToolGate] = None,
        policy: Optional[Policy] = None,
    ) -> None:
        """Initialize the layer.

        Args:
            tool_gate: An existing ToolGate instance. Created with the
                default permissive policy if not provided.
            policy: A Policy to pass to validate(). If not provided,
                uses the ToolGate's current policy.
        """
        self._gate = tool_gate or ToolGate(policy=policy)
        self._policy = policy

    def evaluate(self, context: SafetyContext) -> LayerDecision:
        """Evaluate the tool call against P2's ToolGate.

        Args:
            context: Safety context for the current tool call.

        Returns:
            LayerDecision mapped from GateDecision.
        """
        tool_call: Dict[str, Any] = {
            "name": context.tool_name,
            "args": dict(context.tool_args),
        }
        policy = self._policy if self._policy is not None else self._gate.generate_policy("")
        gate_decision = self._gate.validate(tool_call, policy)
        result = _GATE_DECISION_MAP.get(gate_decision, LayerResult.ESCALATE)

        reason: str
        if gate_decision == GateDecision.ALLOW:
            reason = f"ToolGate: '{context.tool_name}' allowed"
        elif gate_decision == GateDecision.ALLOW_WITH_SANDBOX:
            reason = f"ToolGate: '{context.tool_name}' allowed with sandbox"
        elif gate_decision == GateDecision.ASK_USER:
            reason = f"ToolGate: '{context.tool_name}' requires user approval"
        elif gate_decision == GateDecision.BLOCK:
            reason = f"ToolGate: '{context.tool_name}' blocked by policy"
        else:
            reason = f"ToolGate: unexpected gate decision '{gate_decision}'"

        return LayerDecision(
            result=result,
            layer_name="tool_call_gate",
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Layer 3: AlignmentCheck
# ---------------------------------------------------------------------------

AlignmentFn = Callable[[str, str, Dict[str, Any]], LayerDecision]
"""Signature for alignment-check callables.

Args:
    task_description: The overall task description.
    tool_name: Name of the tool being called.
    tool_args: Arguments to the tool.

Returns:
    LayerDecision: PASS, BLOCK, or ESCALATE.
"""

# Tools that warrant more frequent alignment sampling
_HIGH_RISK_TOOLS: Tuple[str, ...] = ("Bash", "Write", "Edit", "Exec")


class AlignmentCheck:
    """Layer 3: Separate LLM call to verify task alignment.

    Uses a sampling schedule to limit LLM calls — alignment checks are
    expensive and should only run periodically.  High-risk tools are
    sampled more frequently than low-risk ones.

    The alignment function can be injected for testing or wired to an
    actual LLM call in production.  The default stub always returns
    PASS.

    Sampling schedule:
    - Normal tools: check every ``sample_interval`` calls (default 5).
    - High-risk tools (Bash, Write, Edit, Exec): check every
      ``high_risk_interval`` calls (default 2).
    """

    __slots__ = ("_sample_interval", "_high_risk_interval", "_alignment_fn")

    def __init__(
        self,
        sample_interval: int = 5,
        high_risk_interval: int = 2,
        alignment_fn: Optional[AlignmentFn] = None,
    ) -> None:
        """Initialize AlignmentCheck.

        Args:
            sample_interval: Check alignment every N calls for normal tools.
                Must be >= 1.  Default 5.
            high_risk_interval: Check alignment every N calls for high-risk
                tools.  Must be >= 1.  Default 2.
            alignment_fn: Function to perform the alignment check.  If
                None, a stub that always returns PASS is used.
        """
        self._sample_interval = max(1, sample_interval)
        self._high_risk_interval = max(1, high_risk_interval)
        self._alignment_fn = alignment_fn or self._default_alignment

    @staticmethod
    def _default_alignment(
        task_description: str,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> LayerDecision:
        """Default stub — always PASS until an LLM is wired in."""
        return LayerDecision(
            result=LayerResult.PASS,
            layer_name="alignment_check",
            reason="Default alignment stub (no LLM configured) — always passes",
        )

    def evaluate(self, context: SafetyContext) -> LayerDecision:
        """Evaluate task alignment for the current tool call.

        Only performs the LLM call if the sampling schedule indicates
        it is time for one.

        Args:
            context: Safety context for the current tool call.

        Returns:
            PASS if aligned (or sampled skipped),
            BLOCK if misaligned,
            ESCALATE if uncertain.
        """
        interval = (
            self._high_risk_interval
            if context.tool_name in _HIGH_RISK_TOOLS
            else self._sample_interval
        )

        # call_number is 1-based; check on every `interval`-th call
        if context.call_number % interval != 0:
            return LayerDecision(
                result=LayerResult.PASS,
                layer_name="alignment_check",
                reason=(
                    f"Alignment check skipped (call #{context.call_number}, "
                    f"interval={interval})"
                ),
            )

        logger.info(
            "AlignmentCheck: checking call #%d for tool '%s' (interval=%d)",
            context.call_number,
            context.tool_name,
            interval,
        )
        return self._alignment_fn(
            context.task_description,
            context.tool_name,
            context.tool_args,
        )


# ---------------------------------------------------------------------------
# Layer 4: DataFlowTracker
# ---------------------------------------------------------------------------


class DataFlowTracker:
    """Layer 4: Track untrusted data propagation through tool calls.

    Checks whether untrusted inputs (user-supplied strings, web content,
    file reads) appear in the arguments of the current tool call.

    * If untrusted data flows to a **sensitive sink** (Bash, Write, Edit)
      the call is **BLOCKED**.
    * If untrusted data flows elsewhere it is **ESCALATED** for review.
    * If no untrusted data is detected the call **PASSES**.

    Untrusted inputs are provided via ``SafetyContext.untrusted_inputs``.
    The pipeline caller is responsible for populating this field by
    observing outputs of Read, WebFetch, WebSearch, and other
    data-ingesting tools.
    """

    __slots__ = ()

    SENSITIVE_SINKS: Tuple[str, ...] = ("Bash", "Write", "Edit")

    def evaluate(self, context: SafetyContext) -> LayerDecision:
        """Check for untrusted data propagation in the tool call.

        Args:
            context: Safety context for the current tool call.

        Returns:
            LayerDecision: BLOCK for untrusted data in sensitive sinks,
                ESCALATE for untrusted data elsewhere,
                PASS if no untrusted data detected.
        """
        if not context.untrusted_inputs:
            return LayerDecision(
                result=LayerResult.PASS,
                layer_name="data_flow_tracker",
                reason="No untrusted inputs to track",
            )

        # Serialize args to a flat string for efficient substring matching.
        args_str = json.dumps(context.tool_args, ensure_ascii=False, default=str)

        tainted_hits = [
            u for u in context.untrusted_inputs if u in args_str
        ]

        if not tainted_hits:
            return LayerDecision(
                result=LayerResult.PASS,
                layer_name="data_flow_tracker",
                reason="No untrusted data detected in tool args",
            )

        logger.warning(
            "DataFlowTracker: tainted data in '%s' call: %r",
            context.tool_name,
            tainted_hits[:3],
        )

        if context.tool_name in self.SENSITIVE_SINKS:
            return LayerDecision(
                result=LayerResult.BLOCK,
                layer_name="data_flow_tracker",
                reason=(
                    f"Untrusted data flowing to sensitive sink "
                    f"'{context.tool_name}'"
                ),
                details={
                    "sensitive_sink": context.tool_name,
                    "tainted_matches": tainted_hits[:5],
                },
            )

        return LayerDecision(
            result=LayerResult.ESCALATE,
            layer_name="data_flow_tracker",
            reason=(
                f"Tainted data in tool args (not a sensitive sink): "
                f"{', '.join(tainted_hits[:3])}"
            ),
            details={
                "tool_name": context.tool_name,
                "tainted_matches": tainted_hits[:5],
            },
        )


# ---------------------------------------------------------------------------
# Layer 5: ContinuousEval
# ---------------------------------------------------------------------------


class ContinuousEval:
    """Layer 5: Stub for self-evolving safety evaluation.

    Placeholder for future continuous safety evaluation that will:
    * Collect safety events and outcomes.
    * Evolve the dangerous-pattern list.
    * Adjust sampling schedules based on observed risk.
    * Re-weight layer priorities dynamically.

    Currently always returns PASS.  Logs each evaluation call for
    observability.
    """

    __slots__ = ()

    def evaluate(self, context: SafetyContext) -> LayerDecision:
        """Stub evaluation — always passes.

        Args:
            context: Safety context for the current tool call (unused).

        Returns:
            Always PASS.
        """
        logger.debug(
            "ContinuousEval: call #%d for tool '%s' (stub — always passes)",
            context.call_number,
            context.tool_name,
        )
        return LayerDecision(
            result=LayerResult.PASS,
            layer_name="continuous_eval",
            reason="ContinuousEval stub — always passes",
        )


# ---------------------------------------------------------------------------
# SafetyPipeline: Orchestrator
# ---------------------------------------------------------------------------


class SafetyPipeline:
    """Defense-in-depth safety pipeline orchestrating 5 layers.

    Runs layers sequentially:

    1. LexicalGate — fast regex scan
    2. ToolCallGate — delegates to P2 deterministic ToolGate
    3. AlignmentCheck — LLM-based alignment verification (sampled)
    4. DataFlowTracker — untrusted data propagation tracking
    5. ContinuousEval — self-evolving evaluation stub

    Short-circuits at the first ``BLOCK`` result and logs all layer
    decisions to ``self.decision_log`` for post-hoc audit.

    The pipeline is re-entrant: each ``evaluate()`` call resets the
    log.

    Usage::

        pipeline = SafetyPipeline()
        ctx = SafetyContext(
            tool_name="Bash",
            tool_args={"command": "ls"},
            task_description="List directory",
        )
        final = pipeline.evaluate(ctx)
        for d in pipeline.decision_log:
            print(d.layer_name, d.result, d.reason)
    """

    __slots__ = ("_layers", "decision_log")

    def __init__(self, layers: Optional[List[Any]] = None) -> None:
        """Initialize the pipeline with the default 5-layer stack.

        Args:
            layers: Optional list of layer instances. If ``None``, the
                default 5-layer stack is constructed.
        """
        self._layers = layers or [
            LexicalGate(),
            ToolCallGateLayer(),
            AlignmentCheck(),
            DataFlowTracker(),
            ContinuousEval(),
        ]
        self.decision_log: List[LayerDecision] = []

    def evaluate(self, context: SafetyContext) -> LayerDecision:
        """Run all layers against the given safety context.

        Stops at the first BLOCK.  All layer decisions are appended to
        ``self.decision_log``.

        Args:
            context: Safety context describing the tool call to evaluate.

        Returns:
            The final ``LayerDecision`` — either a BLOCK from the
            halting layer, or a PASS if all layers cleared.
        """
        self.decision_log.clear()

        for layer in self._layers:
            decision = layer.evaluate(context)
            self.decision_log.append(decision)

            logger.info(
                "SafetyPipeline: layer='%s' result=%s reason='%s'",
                decision.layer_name,
                decision.result,
                decision.reason,
            )

            if decision.result == LayerResult.BLOCK:
                logger.warning(
                    "SafetyPipeline: BLOCK at layer '%s': %s",
                    decision.layer_name,
                    decision.reason,
                )
                return decision

        return LayerDecision(
            result=LayerResult.PASS,
            layer_name="safety_pipeline",
            reason="All 5 safety layers passed",
        )
