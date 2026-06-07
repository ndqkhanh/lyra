"""
Deterministic tool-call gating for Lyra (Breakthrough #3).

Architecture
------------
``ToolGate`` intercepts every tool invocation via the PRE_TOOL_USE hook system
and enforces an LLM-generated least-privilege ``Policy`` with **pure
deterministic logic** — no LLM calls in the enforcement (validation) path.

Two-phase design
~~~~~~~~~~~~~~~~
1. **generate_policy(task_context) -> Policy**
   Calls an LLM (or returns a configured default) to produce a
   least-privilege permission set for the current task.  This is the *only*
   place an LLM is used.  Called infrequently (once per task).

2. **validate(tool_call, policy) -> GateDecision**
   Pure pattern/logic matching against the Policy.  Returns one of four
   gating levels: ALLOW, ALLOW_WITH_SANDBOX, ASK_USER, BLOCK.

Gating levels
~~~~~~~~~~~~~
* ALLOW — Tool call proceeds normally. No restrictions.
* ALLOW_WITH_SANDBOX — Tool call proceeds under sandboxed execution.
* ASK_USER — Tool call requires interactive user approval (deferred).
* BLOCK — Tool call is denied outright with a reason.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import Any, Dict, List, Optional

from src.hooks.hook import HookAction, HookContext, HookResult, HookType
from src.safety.policy import GateDecision, Policy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default least-privilege policy
# ---------------------------------------------------------------------------

_DEFAULT_POLICY = Policy(
    allowed_tools=[
        "Read",
        "Bash",
        "Write",
        "Edit",
        "WebSearch",
        "WebFetch",
    ],
    allowed_paths=["**"],
    allowed_domains=["*"],
    max_tokens_per_call=4096,
    requires_approval_for=["Bash"],
)

# Prefixes that trigger ALLOW_WITH_SANDBOX for Bash commands
_DANGEROUS_BASH_PREFIXES: tuple[str, ...] = (
    "rm ",
    "mkfs ",
    "dd ",
    "sudo ",
    "chmod ",
    "chown ",
)


# ---------------------------------------------------------------------------
# Builder helper for modified HookContext
# ---------------------------------------------------------------------------


def _with_metadata(context: HookContext, **extra: Any) -> HookContext:
    """Return a new ``HookContext`` with additional metadata entries."""
    return HookContext(
        hook_type=context.hook_type,
        tool_name=context.tool_name,
        tool_args=context.tool_args,
        tool_input=context.tool_input,
        tool_result=context.tool_result,
        model_request=context.model_request,
        model_response=context.model_response,
        agent_id=context.agent_id,
        session_id=context.session_id,
        timestamp=context.timestamp,
        metadata={**context.metadata, **extra},
    )


# ---------------------------------------------------------------------------
# ToolGate
# ---------------------------------------------------------------------------


class ToolGate:
    """Deterministic tool-call gating with LLM-generated policies.

    Usage::

        gate = ToolGate()
        decision = gate.validate({"name": "Bash", "args": {"command": "ls"}}, policy)

    Register with the hook engine::

        engine.register(
            HookType.PRE_TOOL_USE,
            gate,                       # __call__ method
            priority=2000,              # runs before all other hooks
            hook_id="tool_gate",
            description="Deterministic tool-call gating (P2)",
        )
    """

    def __init__(self, policy: Optional[Policy] = None) -> None:
        """Initialize ToolGate with an optional custom policy.

        Args:
            policy: A ``Policy`` to use as the default.  If ``None``, a
                permissive default (covering common tools) is used.
        """
        self._policy = policy or _DEFAULT_POLICY

    # ------------------------------------------------------------------
    # Phase 1: Policy generation (LLM-backed)
    # ------------------------------------------------------------------

    def generate_policy(self, task_context: str) -> Policy:
        """Generate a least-privilege policy from a textual task description.

        This method is the **only** path that uses an LLM.  The returned
        ``Policy`` is then enforced deterministically by ``validate()``.

        Args:
            task_context: A textual description of the task, including
                relevant constraints (e.g., workspace, allowed domains).

        Returns:
            A ``Policy`` dataclass with the least-privilege permission set.
        """
        # TODO (P2+): Integrate with an actual LLM call to generate a
        # context-specific least-privilege policy.  For now, return the
        # configured default.
        #
        # Example future implementation:
        #
        #   prompt = f"""Given this task context, generate a least-privilege
        #   tool policy as JSON:
        #
        #   Task: {task_context}
        #
        #   Respond with ONLY a JSON object matching the Policy schema."""
        #
        #   response = await llm.complete(prompt)
        #   return Policy(**json.loads(response.content))
        #
        return self._policy

    # ------------------------------------------------------------------
    # Phase 2: Deterministic enforcement (NO LLM)
    # ------------------------------------------------------------------

    def validate(
        self,
        tool_call: Dict[str, Any],
        policy: Policy,
    ) -> GateDecision:
        """Deterministically validate a tool call against a policy.

        **No LLM is called in this path.**  This is pure deterministic
        enforcement — pattern matching, string comparison, and simple
        logic only.

        Args:
            tool_call: A dictionary representing the tool invocation.
                Expected keys:
                - ``name`` (str): The tool name (e.g. ``"Bash"``).
                - ``args`` (dict, optional): Tool arguments.
            policy: The ``Policy`` to enforce against.

        Returns:
            A ``GateDecision``: ALLOW, ALLOW_WITH_SANDBOX, ASK_USER,
            or BLOCK.
        """
        tool_name: str = tool_call.get("name", "")
        tool_args: Dict[str, Any] = tool_call.get("args", {}) or tool_call.get(
            "arguments", {}
        )
        if not isinstance(tool_args, dict):
            tool_args = {}

        # --------------------------------------------------------------
        # Check 1: Tool allowlist
        # --------------------------------------------------------------
        if tool_name not in policy.allowed_tools:
            logger.warning("ToolGate: BLOCK — '%s' not in allowed_tools", tool_name)
            return GateDecision.BLOCK

        # --------------------------------------------------------------
        # Check 2: User-approval requirement
        # --------------------------------------------------------------
        if tool_name in policy.requires_approval_for:
            logger.info("ToolGate: ASK_USER — '%s' requires approval", tool_name)
            return GateDecision.ASK_USER

        # --------------------------------------------------------------
        # Check 3: Path allowlist (Read / Write / Edit)
        # --------------------------------------------------------------
        if tool_name in ("Read", "Write", "Edit") and policy.allowed_paths:
            file_path: str = tool_args.get("file_path", "")
            if file_path:
                allowed = any(
                    fnmatch.fnmatch(file_path, pat) for pat in policy.allowed_paths
                )
                if not allowed:
                    logger.warning(
                        "ToolGate: BLOCK — path '%s' not in allowed_paths",
                        file_path,
                    )
                    return GateDecision.BLOCK

        # --------------------------------------------------------------
        # Check 4: Bash command safety (sandbox for dangerous commands)
        # --------------------------------------------------------------
        if tool_name == "Bash":
            command: str = (
                tool_args.get("command")
                or tool_args.get("cmd")
                or tool_args.get("script", "")
            )
            if command and command.strip().startswith(_DANGEROUS_BASH_PREFIXES):
                logger.info(
                    "ToolGate: ALLOW_WITH_SANDBOX — dangerous command in '%s'",
                    tool_name,
                )
                return GateDecision.ALLOW_WITH_SANDBOX

        # --------------------------------------------------------------
        # Check 5: Domain allowlist (WebSearch / WebFetch)
        #          Future enhancement — not enforced in this iteration.
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # Fallthrough: ALLOW
        # --------------------------------------------------------------
        return GateDecision.ALLOW

    # ------------------------------------------------------------------
    # Hook handler entry point
    # ------------------------------------------------------------------

    def __call__(self, context: HookContext) -> HookResult:
        """Handle PRE_TOOL_USE hook events.

        Registered as a PRE_TOOL_USE hook so it fires before every tool
        invocation.  Returns a ``HookResult`` that maps the GateDecision
        to the appropriate hook action (ALLOW, MODIFY, ASK_USER, BLOCK).

        Args:
            context: The hook context describing the tool call.

        Returns:
            A ``HookResult`` that controls the interceptor pipeline.
        """
        if context.hook_type != HookType.PRE_TOOL_USE:
            return HookResult.allow(hook_name="ToolGate")

        tool_call: Dict[str, Any] = {
            "name": context.tool_name or "",
            "args": context.tool_input or context.tool_args or {},
        }

        policy = self.generate_policy(task_context="")
        decision = self.validate(tool_call, policy)

        # Map GateDecision -> HookResult
        if decision == GateDecision.BLOCK:
            return HookResult.block(
                reason=f"ToolGate: '{context.tool_name}' blocked per policy",
                hook_name="ToolGate",
            )

        if decision == GateDecision.ASK_USER:
            return HookResult.ask_user(
                reason=(
                    f"ToolGate: '{context.tool_name}' "
                    f"requires user approval"
                ),
                hook_name="ToolGate",
            )

        if decision == GateDecision.ALLOW_WITH_SANDBOX:
            return HookResult.modify(
                context=_with_metadata(context, sandbox_required=True),
                hook_name="ToolGate",
                reason="ToolGate: sandbox required for this tool call",
            )

        # ALLOW
        return HookResult.allow(hook_name="ToolGate")
