"""Permission modes and rule-based decision resolver.

Precedence (per resolve_decision call):
  1. hard `deny` rule match -> DENY
  2. hard `ask` rule match -> ASK
  3. hard `allow` rule match -> ALLOW
  4. mode default (per tool.writes and mode)
"""
from __future__ import annotations

import enum
import fnmatch
from dataclasses import dataclass, field
from typing import Optional

from .messages import ToolCall


class PermissionMode(str, enum.Enum):
    PLAN = "plan"
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypass"


class Decision(str, enum.Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PermissionDecision:
    decision: Decision
    reason: str = ""
    matched_rule: Optional[str] = None


@dataclass
class PermissionPolicy:
    """Declarative policy: lists of glob patterns per decision class.

    Patterns match against ``"{tool_name}({arg_summary})"`` where ``arg_summary``
    is the tool's ``args`` rendered as ``key=value,...`` in sorted order. Callers
    may register custom rule functions for non-trivial checks.
    """

    allow: list[str] = field(default_factory=list)
    ask: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)

    def _signature(self, call: ToolCall) -> str:
        args = ",".join(f"{k}={v}" for k, v in sorted(call.args.items()))
        return f"{call.name}({args})"

    def _match(self, call: ToolCall, patterns: list[str]) -> Optional[str]:
        sig = self._signature(call)
        for pat in patterns:
            if fnmatch.fnmatchcase(sig, pat) or fnmatch.fnmatchcase(call.name, pat):
                return pat
        return None


def resolve_decision(
    call: ToolCall,
    *,
    mode: PermissionMode,
    policy: Optional[PermissionPolicy] = None,
    tool_writes: bool = False,
    tool_risk: str = "low",
) -> PermissionDecision:
    """Compute the authoritative decision for a proposed tool call."""
    policy = policy or PermissionPolicy()

    # 1. hard deny wins always
    matched = policy._match(call, policy.deny)
    if matched:
        return PermissionDecision(Decision.DENY, f"blocked by deny rule {matched!r}", matched)

    # 2. bypass mode (post-deny check): anything allowed
    if mode == PermissionMode.BYPASS:
        return PermissionDecision(Decision.ALLOW, "bypass mode", None)

    # 3. plan mode: only read-only tools allowed
    if mode == PermissionMode.PLAN:
        if tool_writes or tool_risk == "destructive":
            return PermissionDecision(
                Decision.DENY,
                f"plan mode does not permit {call.name!r} (writes={tool_writes})",
                None,
            )

    # 4. hard ask rule forces ask
    matched = policy._match(call, policy.ask)
    if matched:
        return PermissionDecision(Decision.ASK, f"matched ask rule {matched!r}", matched)

    # 5. hard allow rule short-circuits to allow
    matched = policy._match(call, policy.allow)
    if matched:
        return PermissionDecision(Decision.ALLOW, f"matched allow rule {matched!r}", matched)

    # 6. mode defaults
    if mode == PermissionMode.ACCEPT_EDITS:
        # edits auto-run; everything else asks
        if tool_risk == "destructive":
            return PermissionDecision(Decision.ASK, "destructive tool under acceptEdits", None)
        return PermissionDecision(Decision.ALLOW, "acceptEdits default", None)

    # DEFAULT: writes ask; reads allow
    if tool_writes or tool_risk in ("high", "destructive"):
        return PermissionDecision(Decision.ASK, "default mode: write requires ask", None)

    return PermissionDecision(Decision.ALLOW, "default mode: read auto-allowed", None)
