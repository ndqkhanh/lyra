"""Tool abstraction: base class, registry, typed-arg validation, schema export.

Includes tool annotations for permission gating per Claude Code tools-reference.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ValidationError

from .messages import ToolCall, ToolResult


class ToolError(Exception):
    """Raised by tools to signal a structured, model-visible failure."""


class RiskLevel(str, Enum):
    """Standard risk vocabulary for tool annotations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolCategory(str, Enum):
    """Categories for organizing the tool catalog."""

    FILE = "file"
    GIT = "git"
    SEARCH = "search"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    EXECUTION = "execution"
    COMMUNICATION = "communication"
    KNOWLEDGE = "knowledge"
    SYSTEM = "system"
    NETWORK = "network"


@dataclass(frozen=True)
class ToolAnnotation:
    """Annotations for a tool — drives permission gating and catalog display.

    Based on Claude Code tools-reference risk vocabulary.
    """

    read_only: bool = False
    requires_approval: bool = True
    sandboxed: bool = False
    network_access: bool = False
    mutates_filesystem: bool = False
    mutates_state: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    category: ToolCategory = ToolCategory.ANALYSIS
    tags: tuple[str, ...] = ()


class Tool(ABC):
    """Base class for a tool the agent may invoke.

    Subclasses override ``name``, ``description``, ``ArgsModel`` (pydantic), and
    ``run(args) -> str | dict``. The registry validates args before dispatch.
    """

    name: str = ""
    description: str = ""
    risk: str = "low"  # deprecated; use annotations.risk_level
    writes: bool = False  # deprecated; use annotations.mutates_filesystem
    annotations: ToolAnnotation = ToolAnnotation()

    class ArgsModel(BaseModel):  # override in subclasses
        pass

    @abstractmethod
    def run(self, args: Any) -> str:
        """Execute the tool and return stringified output."""
        raise NotImplementedError

    def to_schema(self) -> dict[str, Any]:
        """Emit an Anthropic-compatible tool schema with annotations."""
        schema = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.ArgsModel.model_json_schema(),
        }
        if self.annotations.risk_level != RiskLevel.LOW:
            schema["annotations"] = {
                "read_only": self.annotations.read_only,
                "requires_approval": self.annotations.requires_approval,
                "risk_level": self.annotations.risk_level.value,
            }
        return schema

    @property
    def is_read_only(self) -> bool:
        return self.annotations.read_only

    @property
    def is_destructive(self) -> bool:
        return self.annotations.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def needs_approval(self) -> bool:
        return self.annotations.requires_approval


@dataclass
class ToolPermissionGate:
    """Gate tool execution based on annotations and permission policy.

    Permission modes:
    - default: allow read-only, ask for writes, deny destructive
    - accept_edits: auto-approve non-destructive writes
    - plan: deny everything, just describe
    - bypass: allow everything (dangerous — use only in sandboxed contexts)
    """

    mode: str = "default"  # default | accept_edits | plan | bypass
    allow_network: bool = False
    allowed_paths: tuple[str, ...] = ()
    blocked_paths: tuple[str, ...] = ()

    def can_execute(self, tool: Tool) -> tuple[bool, str]:
        """Check if a tool can be executed under current policy.

        Returns (allowed, reason).
        """
        ann = tool.annotations

        if self.mode == "bypass":
            return True, "bypass mode"

        if self.mode == "plan":
            return False, f"plan mode: tool {tool.name!r} not executed"

        if ann.risk_level == RiskLevel.CRITICAL:
            return False, f"critical-risk tool {tool.name!r} blocked"

        if self.mode == "default":
            if ann.read_only:
                return True, "read-only tool allowed in default mode"
            if ann.risk_level == RiskLevel.LOW:
                return True, "low-risk tool allowed in default mode"
            return False, f"tool {tool.name!r} requires approval (risk={ann.risk_level.value})"

        if self.mode == "accept_edits":
            if ann.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                return False, f"destructive tool {tool.name!r} blocked in accept_edits"
            return True, "tool allowed in accept_edits mode"

        return False, f"unknown permission mode: {self.mode}"


class ToolRegistry:
    """Holds registered tools; dispatches ToolCall → ToolResult with validation."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError(f"Tool {type(tool).__name__} has empty .name")
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def names_by_category(self, category: ToolCategory) -> list[str]:
        return sorted(
            n for n, t in self._tools.items()
            if t.annotations.category == category
        )

    def names_by_risk(self, max_risk: RiskLevel = RiskLevel.LOW) -> list[str]:
        risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1,
                      RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        max_val = risk_order[max_risk]
        return sorted(
            n for n, t in self._tools.items()
            if risk_order[t.annotations.risk_level] <= max_val
        )

    def schemas(self, allowed: set[str] | None = None) -> list[dict[str, Any]]:
        """Emit schemas for all tools (or a subset by name)."""
        return [
            t.to_schema()
            for n, t in self._tools.items()
            if allowed is None or n in allowed
        ]

    def execute(self, call: ToolCall, permission_gate: ToolPermissionGate | None = None) -> ToolResult:
        """Validate args and dispatch to the tool; wrap errors into ToolResult.

        If permission_gate is provided, checks annotation-based permissions first.
        """
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                call_id=call.id,
                content=f"Unknown tool: {call.name!r}",
                is_error=True,
            )
        if permission_gate is not None:
            allowed, reason = permission_gate.can_execute(tool)
            if not allowed:
                return ToolResult(
                    call_id=call.id,
                    content=f"Permission denied: {reason}",
                    is_error=True,
                )
        try:
            args = tool.ArgsModel(**call.args)
        except ValidationError as e:
            return ToolResult(
                call_id=call.id,
                content=f"argument validation failed: {e.errors()}",
                is_error=True,
            )
        try:
            output = tool.run(args)
        except ToolError as e:
            return ToolResult(call_id=call.id, content=str(e), is_error=True)
        except Exception as e:  # noqa: BLE001 - intentional broad catch at tool boundary
            return ToolResult(
                call_id=call.id,
                content=f"unhandled tool error: {type(e).__name__}: {e}",
                is_error=True,
            )
        if not isinstance(output, str):
            output = str(output)
        return ToolResult(call_id=call.id, content=output, is_error=False)
