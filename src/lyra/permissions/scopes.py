"""Permission scopes — fine-grained access control for tools and resources."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionLevel(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PermissionScope:
    """A named scope of permissions for tools and resources."""

    name: str
    level: PermissionLevel = PermissionLevel.ASK
    tools: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    env_vars: list[str] = field(default_factory=list)
    network_hosts: list[str] = field(default_factory=list)

    def covers_tool(self, tool_name: str) -> bool:
        """Check if this scope covers a specific tool."""
        if not self.tools:
            return True  # Empty means "all tools"
        return any(t in tool_name for t in self.tools)

    def covers_path(self, path: str) -> bool:
        """Check if this scope covers a filesystem path."""
        if not self.paths:
            return True
        return any(p in path for p in self.paths)


@dataclass
class ScopeManager:
    """Manage multiple permission scopes with deny-first evaluation."""

    scopes: dict[str, PermissionScope] = field(default_factory=dict)
    default_level: PermissionLevel = PermissionLevel.ASK

    def add_scope(self, scope: PermissionScope):
        self.scopes[scope.name] = scope

    def evaluate_tool(self, tool_name: str) -> PermissionLevel:
        """Evaluate permission for a tool across all scopes. DENY wins."""
        result = self.default_level
        for scope in self.scopes.values():
            if scope.covers_tool(tool_name):
                if scope.level == PermissionLevel.DENY:
                    return PermissionLevel.DENY
                if scope.level == PermissionLevel.ALLOW:
                    result = PermissionLevel.ALLOW
        return result

    def evaluate_path(self, path: str) -> PermissionLevel:
        """Evaluate permission for a filesystem path. DENY wins."""
        result = self.default_level
        for scope in self.scopes.values():
            if scope.covers_path(path):
                if scope.level == PermissionLevel.DENY:
                    return PermissionLevel.DENY
                if scope.level == PermissionLevel.ALLOW:
                    result = PermissionLevel.ALLOW
        return result

    def to_policy(self) -> dict[str, Any]:
        """Export scopes as a serializable policy."""
        return {
            "scopes": {
                name: {"level": s.level.value, "tools": s.tools, "paths": s.paths}
                for name, s in self.scopes.items()
            },
            "default": self.default_level.value,
        }
