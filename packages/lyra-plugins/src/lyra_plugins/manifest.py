"""Plugin manifest data models."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PluginPermission(str, Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    NETWORK = "network"
    EXECUTE = "execute"
    TOOLS = "tools"
    HOOKS = "hooks"


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    permissions: list[PluginPermission] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    provider_requirements: dict[str, Any] = field(default_factory=dict)
    entry_point: str = ""

    def validate(self) -> list[str]:
        errors = []
        if not self.name or not self.name.replace("-", "").replace("_", "").isalnum():
            errors.append(f"Invalid plugin name: {self.name}")
        if not self.version:
            errors.append("Version is required")
        if self.entry_point and not self.entry_point.endswith(".py"):
            errors.append(f"Entry point must be a .py file: {self.entry_point}")
        return errors
