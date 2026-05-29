"""Meta MCP — self-describing MCP server that aggregates all other MCPs.

Acts as a registry-of-registries: discovers MCP servers, aggregates their
tool/resource/prompt manifests, and exposes a unified meta-manifest for
clients to discover the full capability surface of the Lyra ecosystem.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class ToolCategory(StrEnum):
    FILE = "file"
    NETWORK = "network"
    CODE = "code"
    DATA = "data"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass(frozen=True)
class ToolManifest:
    name: str
    description: str
    category: ToolCategory
    server_id: str
    input_schema: dict | None = None
    version: str = "1.0.0"


@dataclass(frozen=True)
class ResourceManifest:
    uri: str
    name: str
    description: str
    mime_type: str
    server_id: str


@dataclass
class ServerInfo:
    server_id: str
    name: str
    version: str
    endpoint: str
    tools: list[ToolManifest] = field(default_factory=list)
    resources: list[ResourceManifest] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    healthy: bool = True


class MetaMcp:
    """Aggregate registry of all MCP servers in the ecosystem."""

    def __init__(self) -> None:
        self._servers: dict[str, ServerInfo] = {}
        self._tool_index: dict[str, ToolManifest] = {}
        self._resource_index: dict[str, ResourceManifest] = {}

    @property
    def server_count(self) -> int:
        return len(self._servers)

    @property
    def total_tools(self) -> int:
        return len(self._tool_index)

    @property
    def total_resources(self) -> int:
        return len(self._resource_index)

    def register_server(self, server_id: str, name: str, version: str, endpoint: str) -> ServerInfo:
        info = ServerInfo(server_id=server_id, name=name, version=version, endpoint=endpoint)
        self._servers[server_id] = info
        return info

    def deregister_server(self, server_id: str) -> None:
        info = self._servers.pop(server_id, None)
        if info is None:
            return
        for tool in info.tools:
            self._tool_index.pop(tool.name, None)
        for res in info.resources:
            self._resource_index.pop(res.uri, None)

    def register_tool(
        self,
        server_id: str,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.CUSTOM,
        input_schema: dict | None = None,
    ) -> ToolManifest | None:
        server = self._servers.get(server_id)
        if server is None:
            return None
        manifest = ToolManifest(
            name=name,
            description=description,
            category=category,
            server_id=server_id,
            input_schema=input_schema,
        )
        server.tools.append(manifest)
        self._tool_index[name] = manifest
        server.last_seen = time.time()
        return manifest

    def register_resource(
        self,
        server_id: str,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "application/json",
    ) -> ResourceManifest | None:
        server = self._servers.get(server_id)
        if server is None:
            return None
        manifest = ResourceManifest(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            server_id=server_id,
        )
        server.resources.append(manifest)
        self._resource_index[uri] = manifest
        server.last_seen = time.time()
        return manifest

    def find_tool(self, name: str) -> ToolManifest | None:
        return self._tool_index.get(name)

    def find_resource(self, uri: str) -> ResourceManifest | None:
        return self._resource_index.get(uri)

    def search_tools(self, query: str) -> list[ToolManifest]:
        q = query.lower()
        return [
            t
            for t in self._tool_index.values()
            if q in t.name.lower() or q in t.description.lower()
        ]

    def list_tools_by_category(self, category: ToolCategory) -> list[ToolManifest]:
        return [t for t in self._tool_index.values() if t.category == category]

    def get_meta_manifest(self) -> dict:
        """Return the aggregate manifest of all registered tools/resources."""
        return {
            "servers": self.server_count,
            "total_tools": self.total_tools,
            "total_resources": self.total_resources,
            "tools_by_server": {
                sid: [t.__dict__ for t in info.tools] for sid, info in self._servers.items()
            },
            "categories": {
                cat.value: len(self.list_tools_by_category(cat)) for cat in ToolCategory
            },
        }

    def prune_stale_servers(self, max_age_sec: float = 300.0) -> int:
        """Remove servers not seen within max_age_sec. Returns count pruned."""
        now = time.time()
        stale = [sid for sid, info in self._servers.items() if now - info.last_seen > max_age_sec]
        for sid in stale:
            self.deregister_server(sid)
        return len(stale)
