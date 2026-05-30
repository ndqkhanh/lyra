"""Plugin Manifest + Sandboxing — P1-B8 BREAKTHROUGH primitives.

Plugin lifecycle: install → configure → enable → disable → uninstall.
Sandbox: network-scoped, filesystem-scoped, shared read-only base environment.
"""
from __future__ import annotations

from lyra_harness_core.plugins.manifest import (
    DependencySpec,
    HookBinding,
    PluginInstance,
    PluginLifecycle,
    PluginManifest,
    SandboxConfig,
    SemVer,
    ToolDeclaration,
    check_version_constraint,
    load_manifest_from_yaml,
    parse_manifest,
)
from lyra_harness_core.plugins.sandbox import (
    PluginSandbox,
    SandboxResult,
    validate_domain,
    validate_path,
)

__all__ = [
    # Manifest
    "check_version_constraint",
    "DependencySpec",
    "HookBinding",
    "load_manifest_from_yaml",
    "parse_manifest",
    "PluginInstance",
    "PluginLifecycle",
    "PluginManifest",
    "SandboxConfig",
    "SemVer",
    "ToolDeclaration",
    # Sandbox
    "PluginSandbox",
    "SandboxResult",
    "validate_domain",
    "validate_path",
]
