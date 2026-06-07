"""
Built-in hook handlers for Hook Engine v2.

These handlers are registered with the HookEngine v2 by default at
construction time, ordered by priority:

  - p0 (1000): SecretsScanner                -- security
  - p1 (900):  CommandGuard                  -- validation
  - p2 (800):  CostTracker                    -- observability
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from .hook import HookAction, HookContext, HookResult, HookType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SecretsScanner (priority 1000)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    # Generic API / bearer tokens
    re.compile(
        r"(?i)(?:api[_-]?key|apikey|secret|token|bearer)"
        r"['\"]?\s*[:=]\s*['\"]([a-z0-9_\-]{16,})['\"]",
    ),
    # AWS access key
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    # GitHub personal access token
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{36}"),
    # OpenAI key
    re.compile(r"(?i)sk-[a-zA-Z0-9]{32,}"),
    # Anthropic key
    re.compile(r"(?i)sk-ant-[a-z0-9]{32,}"),
    # Private / EC2 SSH keys (inline)
    re.compile(r"-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----"),
    # Generic password / credential assignment
    re.compile(
        r"(?i)(?:password|passwd|pwd|credential)"
        r"['\"]?\s*[:=]\s*['\"]([^'\"]{8,})['\"]",
    ),
]


class SecretsScanner:
    """p0 security handler: blocks detected secrets in tool output.

    Scans tool result and model response text for common secret patterns.
    If a secret is found, the hook returns BLOCK so the secret is never
    exposed to the agent or persisted.
    """

    def __init__(self) -> None:
        self._patterns = _SECRET_PATTERNS

    def __call__(self, context: HookContext) -> HookResult:
        """Inspect context for secret-like content."""
        if context.hook_type in (HookType.POST_TOOL_USE, HookType.POST_MODEL_CALL):
            payloads = []

            if context.tool_result is not None:
                payloads.append(str(context.tool_result))

            if context.model_response is not None:
                try:
                    payloads.append(str(context.model_response.content))
                except AttributeError:
                    payloads.append(str(context.model_response))

            for payload in payloads:
                matches = self._scan(payload)
                if matches:
                    logger.warning("SecretsScanner blocked %d secret pattern(s)", len(matches))
                    return HookResult.block(
                        reason=f"SecretsScanner blocked output containing possible secret "
                        f"(matched pattern{'s' if len(matches)>1 else ''}: "
                        f"{', '.join(matches[:3])})",
                        hook_name="SecretsScanner",
                    )

        return HookResult.allow(hook_name="SecretsScanner")

    def _scan(self, text: str) -> list[str]:
        """Return list of matched pattern names for *text*."""
        found: list[str] = []
        for pat in self._patterns:
            if pat.search(text):
                found.append(pat.pattern[:60])
        return found


# ---------------------------------------------------------------------------
# CommandGuard (priority 900)
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\s+/\s*$", re.MULTILINE),       # rm -rf /
    re.compile(r"\brm\s+-rf\s+~\s*$", re.MULTILINE),        # rm -rf ~
    re.compile(r"\bchmod\s+-R\s+777\s+/", re.MULTILINE),    # chmod -R 777 /
    re.compile(r"\bdd\s+if=.*\s+of=/dev/sd", re.MULTILINE),  # destructive dd
    re.compile(r"\b>:?\s*/dev/sd", re.MULTILINE),            # direct device write
    re.compile(r"\b:wq!\s*/etc/", re.MULTILINE),             # vi force-write system file
    re.compile(r"\bmkfs\.\w+\s+/dev/sd", re.MULTILINE),      # filesystem creation
    re.compile(r"\bcurl\s+.*\s*\|\s*bash\b", re.MULTILINE),  # pipe-to-bash
    re.compile(r"\bsudo\s+rm\s+-rf\s+--no-preserve-root\b", re.MULTILINE),
    re.compile(r"\bmv\s+/dev/null\s+/", re.MULTILINE),       # dangerous mv
]


class CommandGuard:
    """p1 validation handler: blocks dangerous bash commands.

    Scans tool input for known destructive command patterns and prevents
    execution by returning BLOCK.
    """

    def __init__(self, additional_patterns: list[re.Pattern[str]] | None = None) -> None:
        self._patterns = _DANGEROUS_PATTERNS
        if additional_patterns:
            self._patterns = self._patterns + additional_patterns

    def __call__(self, context: HookContext) -> HookResult:
        """Check tool arguments for dangerous shell commands."""
        if context.hook_type != HookType.PRE_TOOL_USE:
            return HookResult.allow(hook_name="CommandGuard")

        # Only inspect Bash tool calls
        if context.tool_name != "Bash":
            return HookResult.allow(hook_name="CommandGuard")

        command = self._get_command(context)
        if command is None:
            return HookResult.allow(hook_name="CommandGuard")

        for pat in self._patterns:
            if pat.search(command):
                logger.warning("CommandGuard blocked dangerous command matching: %s", pat.pattern)
                return HookResult.block(
                    reason=f"CommandGuard blocked potentially dangerous command: "
                    f"pattern /{pat.pattern[:50]}/ detected",
                    hook_name="CommandGuard",
                )

        return HookResult.allow(hook_name="CommandGuard")

    @staticmethod
    def _get_command(context: HookContext) -> str | None:
        """Extract the command string from the hook context."""
        args = context.tool_args or context.tool_input
        if args is None:
            return None
        cmd = args.get("command") or args.get("cmd") or args.get("script")
        return str(cmd) if cmd is not None else None


# ---------------------------------------------------------------------------
# CostTracker (priority 800)
# ---------------------------------------------------------------------------


class CostTracker:
    """p2 observability handler: logs token usage for model calls.

    Accumulates per-session token counts and costs (if model metadata
    is available).  Metrics can be retrieved with ``get_metrics()``.
    """

    def __init__(self) -> None:
        self._session_stats: dict[str, dict[str, Any]] = {}

    def __call__(self, context: HookContext) -> HookResult:
        """Record model response usage statistics."""
        if context.hook_type not in (
            HookType.POST_MODEL_CALL,
            HookType.POST_TOOL_USE,
        ):
            return HookResult.allow(hook_name="CostTracker")

        response = context.model_response
        usage = getattr(response, "usage", None) if response is not None else None

        if usage is None:
            return HookResult.allow(hook_name="CostTracker")

        sid = context.session_id or "_default"

        if sid not in self._session_stats:
            self._session_stats[sid] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "total_calls": 0,
            }

        stats = self._session_stats[sid]
        stats["input_tokens"] += getattr(usage, "input_tokens", 0)
        stats["output_tokens"] += getattr(usage, "output_tokens", 0)
        stats["cache_read_tokens"] += getattr(usage, "cache_read_tokens", 0)
        stats["cache_write_tokens"] += getattr(usage, "cache_write_tokens", 0)
        stats["total_calls"] += 1

        logger.debug(
            "CostTracker[%s]: +%d in / +%d out (total: %d in / %d out / %d calls)",
            sid,
            getattr(usage, "input_tokens", 0),
            getattr(usage, "output_tokens", 0),
            stats["input_tokens"],
            stats["output_tokens"],
            stats["total_calls"],
        )

        return HookResult.allow(hook_name="CostTracker")

    def get_metrics(self, session_id: str | None = None) -> dict[str, Any]:
        """Return metrics for one or all sessions."""
        if session_id is not None:
            return dict(self._session_stats.get(session_id, {}))
        return {sid: dict(stats) for sid, stats in self._session_stats.items()}

    def reset(self, session_id: str | None = None) -> None:
        """Reset metrics for one or all sessions."""
        if session_id is not None:
            self._session_stats.pop(session_id, None)
        else:
            self._session_stats.clear()
