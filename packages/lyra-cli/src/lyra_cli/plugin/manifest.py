"""
Plugin Manifest — typed metadata for Lyra plugin packages.

Defines the manifest schema that every Lyra plugin must provide
(plugin.json or plugin.yaml at the plugin root).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class PluginKind(str, Enum):
    SKILL = "skill"
    AGENT = "agent"
    HOOK = "hook"
    MCP_SERVER = "mcp_server"
    LSP_SERVER = "lsp_server"
    MONITOR = "monitor"
    TOOL = "tool"
    THEME = "theme"
    SOUND_PACK = "sound_pack"
    BUNDLE = "bundle"


@dataclass
class PluginPermission:
    """A permission required by the plugin."""

    tool: str
    level: Literal["read", "write", "shell", "network"] = "read"
    reason: str = ""


@dataclass
class PluginDependency:
    """A dependency on another plugin or Python package."""

    name: str
    version: str = "*"
    optional: bool = False


@dataclass
class PluginManifest:
    """Metadata for a Lyra plugin.

    Every plugin directory must contain a ``plugin.json`` conforming
    to this schema. Lyra discovers plugins by scanning configured
    plugin directories and validating manifests.
    """

    name: str
    version: str
    kind: PluginKind | list[PluginKind]
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""

    # Entry points
    entry_point: str = ""
    commands: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)

    # Requirements
    requires_python: str = ">=3.10"
    dependencies: list[PluginDependency] = field(default_factory=list)
    permissions: list[PluginPermission] = field(default_factory=list)

    # Compatibility
    min_lyra_version: str = "0.1.0"
    max_lyra_version: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        kind_val = (
            self.kind.value if isinstance(self.kind, PluginKind) else [k.value for k in self.kind]
        )
        return {
            "name": self.name,
            "version": self.version,
            "kind": kind_val,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "entry_point": self.entry_point,
            "commands": self.commands,
            "skills": self.skills,
            "agents": self.agents,
            "requires_python": self.requires_python,
            "dependencies": [
                {"name": d.name, "version": d.version, "optional": d.optional}
                for d in self.dependencies
            ],
            "permissions": [
                {"tool": p.tool, "level": p.level, "reason": p.reason} for p in self.permissions
            ],
            "min_lyra_version": self.min_lyra_version,
            "max_lyra_version": self.max_lyra_version,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PluginManifest:
        kind_raw = data.get("kind", "skill")
        if isinstance(kind_raw, list):
            kind: PluginKind | list[PluginKind] = [PluginKind(k) for k in kind_raw]
        else:
            kind = PluginKind(kind_raw)

        return cls(
            name=data["name"],
            version=data["version"],
            kind=kind,
            description=data.get("description", ""),
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            entry_point=data.get("entry_point", ""),
            commands=data.get("commands", []),
            skills=data.get("skills", []),
            agents=data.get("agents", []),
            requires_python=data.get("requires_python", ">=3.10"),
            dependencies=[PluginDependency(**d) for d in data.get("dependencies", [])],
            permissions=[PluginPermission(**p) for p in data.get("permissions", [])],
            min_lyra_version=data.get("min_lyra_version", "0.1.0"),
            max_lyra_version=data.get("max_lyra_version"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_bundle(self) -> bool:
        if isinstance(self.kind, list):
            return PluginKind.BUNDLE in self.kind
        return self.kind == PluginKind.BUNDLE
