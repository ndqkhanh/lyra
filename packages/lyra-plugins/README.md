# lyra-plugins — Plugin System

Marketplace-style plugin discovery, manifest validation, and sandboxed loading.

| Component | Purpose |
|-----------|---------|
| `PluginManifest` | Standardized metadata (name, version, permissions, tools, hooks) |
| `PluginDiscovery` | Auto-discover from `.lyra/plugins/` directory |
| `PluginLoader` | Import-based loading with error handling |
| `PluginSandbox` | Permission-gated access control |

[Plan: plans/06-plugins.md](../../lyra-upgrade/plans/06-plugins.md)
