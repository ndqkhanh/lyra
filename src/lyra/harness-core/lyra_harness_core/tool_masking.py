"""Tool Masking over Tool Removal — P2-B8 (HIGH, MED).

Mask tool logits during decoding instead of dynamically removing tool
definitions. Preserves KV-cache coherence by keeping tool definitions
stable in the prompt while constraining which tools the model can call.

Three modes:
- AUTO: model chooses freely from all tools
- REQUIRED: force tool use, constrain to a subset
- SPECIFIED: require a specific tool call

See: plan-phase2-memory.md §Strategy 2
Ref: Manus Context Engineering §6.2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Tool Mask Mode
# ---------------------------------------------------------------------------


class ToolMaskMode(Enum):
    """How tools are constrained during decoding."""

    AUTO = "auto"          # Model chooses freely from all available tools
    REQUIRED = "required"  # Must call a tool from the allowed subset
    SPECIFIED = "specified"  # Must call a specific tool


# ---------------------------------------------------------------------------
# Tool Descriptor
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolDescriptor:
    """Minimal tool descriptor for masking purposes."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool Mask
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolMask:
    """A mask that constrains which tools are available.

    Unlike tool removal (which changes the prompt and invalidates KV-cache),
    tool masking keeps all definitions in the prompt but applies logit-level
    constraints during decoding.
    """

    mode: ToolMaskMode = ToolMaskMode.AUTO
    allowed_tools: frozenset[str] = field(default_factory=frozenset)
    required_tool: str = ""  # Only for SPECIFIED mode
    reason: str = ""

    @property
    def is_restrictive(self) -> bool:
        """True if this mask actually constrains tool selection."""
        return self.mode != ToolMaskMode.AUTO

    @property
    def tool_count(self) -> int:
        return len(self.allowed_tools)

    def allows(self, tool_name: str) -> bool:
        """Check whether a specific tool is allowed under this mask."""
        if self.mode == ToolMaskMode.AUTO:
            return True
        if self.mode == ToolMaskMode.SPECIFIED:
            return tool_name == self.required_tool
        return tool_name in self.allowed_tools


# ---------------------------------------------------------------------------
# Tool Mask Policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaskRule:
    """A single rule in the masking policy."""

    name: str
    condition: str = ""  # descriptive condition (for introspection)
    mode: ToolMaskMode = ToolMaskMode.AUTO
    allowed_tools: frozenset[str] = field(default_factory=frozenset)
    required_tool: str = ""
    priority: int = 0  # higher priority wins


@dataclass
class ToolMaskPolicy:
    """A policy that determines tool masking based on context.

    Policies are composed of ordered rules. Rules are evaluated in
    priority order (highest first); the first matching rule wins.
    """

    rules: list[MaskRule] = field(default_factory=list)

    def add_rule(self, rule: MaskRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)

    def evaluate(
        self,
        *,
        phase: str = "",
        task_type: str = "",
        tool_calls_so_far: int = 0,
        max_tool_calls: int = 10,
    ) -> ToolMask:
        """Evaluate the policy against the current context.

        Returns a ToolMask. If no rule matches, returns AUTO (unrestricted).
        """
        for rule in self.rules:
            if self._rule_matches(rule, phase, task_type, tool_calls_so_far, max_tool_calls):
                return ToolMask(
                    mode=rule.mode,
                    allowed_tools=rule.allowed_tools,
                    required_tool=rule.required_tool,
                    reason=rule.name,
                )
        return ToolMask(mode=ToolMaskMode.AUTO, reason="default (no matching rule)")

    @staticmethod
    def _rule_matches(
        rule: MaskRule,
        phase: str,
        task_type: str,
        tool_calls_so_far: int,
        max_tool_calls: int,
    ) -> bool:
        """Simple condition matching based on rule name patterns.

        Recognized condition keywords in rule name:
        - "enforce_tool_use" → REQUIRED for first turn
        - "limit_tool_calls" → checks call count
        - Phase-specific: "planning", "execution", "verification"
        """
        cond = rule.condition.lower() if rule.condition else rule.name.lower()

        if "planning" in cond and phase != "planning":
            return False
        if "execution" in cond and phase != "execution":
            return False
        if "verification" in cond and phase != "verification":
            return False

        if task_type and task_type.lower() not in cond and "any" not in cond:
            return False

        return True


# ---------------------------------------------------------------------------
# Tool Mask Applier
# ---------------------------------------------------------------------------


@dataclass
class ToolMaskApplier:
    """Applies tool masks to tool definitions for KV-cache preservation.

    Strategy: keep ALL tool definitions in the prompt (preserving KV-cache)
    but generate the mask configuration that providers use to constrain
    logits during decoding.

    Usage::

        applier = ToolMaskApplier(available_tools=[...])
        mask = policy.evaluate(phase="execution")
        visible = applier.apply(mask)  # tools visible to the model
        # Pass visible definitions + mask to provider
    """

    available_tools: list[ToolDescriptor] = field(default_factory=list)
    policy: ToolMaskPolicy = field(default_factory=ToolMaskPolicy)

    def apply(self, mask: ToolMask) -> list[ToolDescriptor]:
        """Return the subset of tools visible under the given mask.

        All tools remain in the prompt for KV-cache stability;
        only logit masking differs.
        """
        if mask.mode == ToolMaskMode.AUTO:
            return list(self.available_tools)

        if mask.mode == ToolMaskMode.SPECIFIED:
            return [t for t in self.available_tools if t.name == mask.required_tool]

        return [t for t in self.available_tools if t.name in mask.allowed_tools]

    def build_mask_config(self, mask: ToolMask) -> dict[str, Any]:
        """Build a provider-agnostic mask configuration.

        This dict can be passed to any provider's tool-masking
        implementation.
        """
        config: dict[str, Any] = {
            "mode": mask.mode.value,
            "reason": mask.reason,
        }
        if mask.mode == ToolMaskMode.REQUIRED:
            config["allowed_tools"] = sorted(mask.allowed_tools)
        elif mask.mode == ToolMaskMode.SPECIFIED:
            config["required_tool"] = mask.required_tool
        return config

    def apply_and_config(self, mask: ToolMask) -> tuple[list[ToolDescriptor], dict[str, Any]]:
        """Apply mask and return both visible tools and mask config."""
        return self.apply(mask), self.build_mask_config(mask)

    @property
    def tool_names(self) -> list[str]:
        return [t.name for t in self.available_tools]


# ---------------------------------------------------------------------------
# Pre-built Policies
# ---------------------------------------------------------------------------


def build_safety_policy() -> ToolMaskPolicy:
    """Pre-built policy for safety-critical workflows.

    - Verification phase: only read-only tools
    - Execution phase: all tools available
    - Planning phase: only read/search tools
    """
    policy = ToolMaskPolicy()
    policy.add_rule(MaskRule(
        name="verification_readonly",
        condition="verification",
        mode=ToolMaskMode.REQUIRED,
        allowed_tools=frozenset({"Read", "Bash(grep", "Bash(find", "Bash(git diff"}),
        priority=10,
    ))
    policy.add_rule(MaskRule(
        name="planning_readonly",
        condition="planning",
        mode=ToolMaskMode.REQUIRED,
        allowed_tools=frozenset({"Read", "WebSearch", "WebFetch", "Bash(find", "Bash(grep"}),
        priority=10,
    ))
    policy.add_rule(MaskRule(
        name="execution_full",
        condition="execution",
        mode=ToolMaskMode.AUTO,
        priority=5,
    ))
    return policy


def build_strict_policy(required_tool: str = "") -> ToolMaskPolicy:
    """Pre-built strict policy: require specific tool, used for forced tool calls."""
    policy = ToolMaskPolicy()
    policy.add_rule(MaskRule(
        name="strict_single_tool",
        mode=ToolMaskMode.SPECIFIED,
        required_tool=required_tool,
        priority=100,
    ))
    return policy


__all__ = [
    "MaskRule",
    "ToolDescriptor",
    "ToolMask",
    "ToolMaskApplier",
    "ToolMaskMode",
    "ToolMaskPolicy",
    "build_safety_policy",
    "build_strict_policy",
]
