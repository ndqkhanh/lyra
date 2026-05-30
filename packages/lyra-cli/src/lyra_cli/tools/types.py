"""Tool type definitions — frozen DTOs for the extended tools system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ToolCategory(StrEnum):
    FILE = "file"
    WEB = "web"
    CODE = "code"
    SHELL = "shell"
    SEARCH = "search"
    TEXT = "text"
    DATA = "data"
    GIT = "git"
    MEDIA = "media"
    CUSTOM = "custom"


class ToolPermission(StrEnum):
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"


class ToolRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ToolParameter:
    name: str
    type_hint: str
    description: str = ""
    required: bool = True
    default: str | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    permissions: tuple[ToolPermission, ...] = ()
    risk_level: ToolRisk = ToolRisk.LOW
    parameters: tuple[ToolParameter, ...] = ()
    returns: str = "Any"
    idempotent: bool = False
    timeout_ms: int = 30000
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolResult:
    success: bool
    data: str = ""
    error: str = ""
    tool_name: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolExecution:
    execution_id: str
    tool: ToolDefinition
    inputs: dict[str, str]
    result: ToolResult | None = None
    status: str = "pending"
    started_at: float = 0.0
    completed_at: float = 0.0
