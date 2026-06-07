"""Plugin Manifest — schema, validation, and lifecycle management.

Implements the lyra-plugin.yaml manifest format with semver constraints,
hook bindings, tool declarations, and sandbox configuration. Provides
the full plugin lifecycle: install → configure → enable → disable → uninstall.

See: plan-phase1-harness.md §P1-B8, plan-phase5-master-plan.md §Week 2
"""
from __future__ import annotations

import enum
import functools
import re
from dataclasses import dataclass, field

from lyra.harness_core.tools import RiskLevel, ToolAnnotation, ToolCategory


# --- Semver parsing -----------------------------------------------------------


_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

_VERSION_CONSTRAINT_RE = re.compile(
    r"^(>=|<=|!=|==|>|<|~>)\s*"
    r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)


@functools.total_ordering
@dataclass(frozen=True)
class SemVer:
    """Semantic version (major.minor.patch[-pre][+build])."""

    major: int
    minor: int
    patch: int
    pre: str = ""
    build: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre:
            base += f"-{self.pre}"
        if self.build:
            base += f"+{self.build}"
        return base

    @classmethod
    def parse(cls, raw: str) -> SemVer:
        m = _SEMVER_RE.match(raw.strip())
        if not m:
            raise ValueError(f"invalid semver: {raw!r}")
        return cls(
            major=int(m.group("major")),
            minor=int(m.group("minor")),
            patch=int(m.group("patch")),
            pre=m.group("pre") or "",
            build=m.group("build") or "",
        )

    def __lt__(self, other: SemVer) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)


def check_version_constraint(version: SemVer, constraint: str) -> bool:
    """Check if a SemVer satisfies a version constraint string.

    Supports: >=, <=, !=, ==, >, <, ~> (pessimistic/pessimistic operator).
    """
    m = _VERSION_CONSTRAINT_RE.match(constraint.strip())
    if not m:
        raise ValueError(f"invalid version constraint: {constraint!r}")

    op = m.group(1)
    target = SemVer(
        major=int(m.group("major")),
        minor=int(m.group("minor")),
        patch=int(m.group("patch")),
    )

    if op == "==":
        return version == target
    elif op == "!=":
        return version != target
    elif op == ">":
        return version > target
    elif op == ">=":
        return version >= target
    elif op == "<":
        return version < target
    elif op == "<=":
        return version <= target
    elif op == "~>":
        # Pessimistic: >= target, < next significant digit
        next_major = SemVer(major=target.major + 1, minor=0, patch=0)
        next_minor = SemVer(major=target.major, minor=target.minor + 1, patch=0)
        upper = next_major if target.major > 0 else next_minor
        return version >= target and version < upper
    return False


# --- Plugin manifest data types -----------------------------------------------


class PluginLifecycle(str, enum.Enum):
    """Plugin lifecycle states."""

    INSTALLED = "installed"
    CONFIGURED = "configured"
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNINSTALLED = "uninstalled"
    ERROR = "error"


@dataclass(frozen=True)
class HookBinding:
    """A hook event-to-handler binding declared in the plugin manifest."""

    event: str          # HookEvent value, e.g. "session.start"
    handler: str        # fully qualified handler, e.g. "research.init_session"


@dataclass(frozen=True)
class ToolDeclaration:
    """A tool definition declared in the plugin manifest."""

    name: str
    annotations: ToolAnnotation = field(default_factory=ToolAnnotation)


@dataclass(frozen=True)
class DependencySpec:
    """A Python package dependency with version constraint."""

    package: str        # e.g. "arxiv"
    constraint: str = ""  # e.g. ">=2.0"


@dataclass(frozen=True)
class SandboxConfig:
    """Network and filesystem scoping for plugin execution.

    If empty, the plugin runs with default sandbox restrictions.
    The shared base environment is read-only; only allowlisted paths
    are writable.
    """

    network_allowlist: tuple[str, ...] = ()   # allowed domains
    filesystem_allowlist: tuple[str, ...] = ()  # allowed writable paths
    read_only_base: bool = True  # shared base environment is read-only


@dataclass
class PluginManifest:
    """Full parsed plugin manifest (lyra-plugin.yaml).

    Carries all metadata, hook bindings, tool declarations, dependencies,
    and sandbox configuration declared by a plugin.
    """

    name: str
    version: SemVer
    lyra_version: str = ">=7.2.0"  # constraint string
    author: str = ""
    license: str = "MIT"
    description: str = ""
    hooks: tuple[HookBinding, ...] = ()
    tools: tuple[ToolDeclaration, ...] = ()
    dependencies: tuple[DependencySpec, ...] = ()
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    lifecycle: PluginLifecycle = PluginLifecycle.INSTALLED

    @property
    def display_name(self) -> str:
        return f"{self.name} v{self.version}"

    def validate_lyra_version(self, lyra_semver: SemVer) -> bool:
        """Check that the running Lyra version satisfies the manifest constraint."""
        return check_version_constraint(lyra_semver, self.lyra_version)


# --- Manifest loader ----------------------------------------------------------


def _parse_tool_annotation(raw: dict) -> ToolAnnotation:
    """Parse a tool annotation from a manifest dict."""
    risk_map = {r.value: r for r in RiskLevel}
    category_map = {c.value: c for c in ToolCategory}

    risk = risk_map.get(raw.get("risk_level", "low"), RiskLevel.LOW)
    category = category_map.get(raw.get("category", "analysis"), ToolCategory.ANALYSIS)

    return ToolAnnotation(
        read_only=raw.get("read_only", True),
        requires_approval=raw.get("requires_approval", False),
        sandboxed=raw.get("sandboxed", True),
        network_access=raw.get("network_access", False),
        mutates_filesystem=raw.get("mutates_filesystem", False),
        mutates_state=raw.get("mutates_state", False),
        risk_level=risk,
        category=category,
        tags=tuple(raw.get("tags", [])),
    )


def parse_manifest(raw: dict) -> PluginManifest:
    """Parse a raw dict (from YAML) into a validated PluginManifest.

    Args:
        raw: The parsed YAML dict from lyra-plugin.yaml.

    Returns:
        A validated PluginManifest instance.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if "name" not in raw:
        raise ValueError("plugin manifest missing required field: 'name'")
    if "version" not in raw:
        raise ValueError("plugin manifest missing required field: 'version'")

    version = SemVer.parse(raw["version"])

    hooks = tuple(
        HookBinding(event=h["event"], handler=h["handler"])
        for h in raw.get("hooks", [])
    )

    tools = tuple(
        ToolDeclaration(
            name=t["name"],
            annotations=_parse_tool_annotation(t.get("annotations", {})) if "annotations" in t else ToolAnnotation(),
        )
        for t in raw.get("tools", [])
    )

    deps = tuple(
        DependencySpec(package=d["package"], constraint=d.get("constraint", ""))
        if isinstance(d, dict)
        else DependencySpec(package=str(d))
        for d in raw.get("dependencies", [])
    )

    sandbox_raw = raw.get("sandbox", {})
    sandbox = SandboxConfig(
        network_allowlist=tuple(sandbox_raw.get("network", [])),
        filesystem_allowlist=tuple(sandbox_raw.get("filesystem", [])),
        read_only_base=sandbox_raw.get("read_only_base", True),
    )

    return PluginManifest(
        name=raw["name"],
        version=version,
        lyra_version=raw.get("lyra_version", ">=7.2.0"),
        author=raw.get("author", ""),
        license=raw.get("license", "MIT"),
        description=raw.get("description", ""),
        hooks=hooks,
        tools=tools,
        dependencies=deps,
        sandbox=sandbox,
    )


def load_manifest_from_yaml(yaml_text: str) -> PluginManifest:
    """Parse a plugin manifest from YAML text.

    Args:
        yaml_text: Raw YAML content of a lyra-plugin.yaml file.

    Returns:
        A validated PluginManifest instance.
    """
    try:
        import yaml as _yaml  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "PyYAML is required to parse plugin manifests. Install with: pip install pyyaml"
        )

    raw = _yaml.safe_load(yaml_text)
    if not isinstance(raw, dict):
        raise ValueError("plugin manifest YAML must be a mapping")
    return parse_manifest(raw)


# --- Plugin lifecycle manager -------------------------------------------------


@dataclass
class PluginInstance:
    """Runtime instance of a loaded plugin.

    Tracks the plugin manifest and its current lifecycle state.
    Hooks and tools are activated/deactivated as the lifecycle transitions.
    """

    manifest: PluginManifest
    install_path: str = ""

    def transition_to(self, target: PluginLifecycle) -> None:
        """Transition the plugin to a new lifecycle state.

        Valid transitions:
          INSTALLED → CONFIGURED → ENABLED → DISABLED → ENABLED (re-enable)
          Any state → UNINSTALLED
          Any state → ERROR
        """
        valid = self._valid_transitions()
        if target not in valid:
            raise ValueError(
                f"invalid lifecycle transition for {self.manifest.display_name}: "
                f"{self.manifest.lifecycle.value} → {target.value}"
            )
        self.manifest.lifecycle = target

    def _valid_transitions(self) -> set[PluginLifecycle]:
        current = self.manifest.lifecycle
        always_allowed = {PluginLifecycle.UNINSTALLED, PluginLifecycle.ERROR}

        transitions: dict[PluginLifecycle, set[PluginLifecycle]] = {
            PluginLifecycle.INSTALLED: {PluginLifecycle.CONFIGURED, PluginLifecycle.UNINSTALLED},
            PluginLifecycle.CONFIGURED: {PluginLifecycle.ENABLED, PluginLifecycle.DISABLED, PluginLifecycle.UNINSTALLED},
            PluginLifecycle.ENABLED: {PluginLifecycle.DISABLED, PluginLifecycle.UNINSTALLED},
            PluginLifecycle.DISABLED: {PluginLifecycle.ENABLED, PluginLifecycle.UNINSTALLED},
            PluginLifecycle.UNINSTALLED: set(),
            PluginLifecycle.ERROR: {PluginLifecycle.DISABLED, PluginLifecycle.UNINSTALLED},
        }

        return transitions.get(current, set()) | always_allowed


__all__ = [
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
]
