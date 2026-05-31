"""Plugin sandbox — restricts plugin access based on manifest permissions."""

from __future__ import annotations

from .manifest import PluginManifest, PluginPermission


class PluginSandbox:
    """
    Permission-gated sandbox for plugin execution.

    Each plugin declares its required permissions in its manifest.
    Before a plugin can use a tool or hook, the sandbox checks
    that the permission is granted.
    """

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest
        self._granted = set(manifest.permissions)

    def can_read_files(self) -> bool:
        return PluginPermission.READ_FILES in self._granted

    def can_write_files(self) -> bool:
        return PluginPermission.WRITE_FILES in self._granted

    def can_use_network(self) -> bool:
        return PluginPermission.NETWORK in self._granted

    def can_execute(self) -> bool:
        return PluginPermission.EXECUTE in self._granted

    def can_use_tool(self, tool_name: str) -> bool:
        if PluginPermission.TOOLS not in self._granted:
            return False
        return tool_name in self._manifest.tools or not self._manifest.tools

    def check(self, permission: PluginPermission) -> bool:
        return permission in self._granted

    @property
    def permissions(self) -> list[str]:
        return [p.value for p in self._granted]
