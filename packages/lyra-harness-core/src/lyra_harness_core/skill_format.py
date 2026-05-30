"""Cross-Platform Skill Format — P3-B2 (HIGH, LOW — BREAKTHROUGH).

Standardized YAML/Markdown schema for skills compatible with Microsoft Skills
Framework. Supports SKILL.md with YAML frontmatter and standalone .yaml files.

See: plan-phase3-skills-routing.md §Skill Schema
Ref: https://github.com/microsoft/skills
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Skill Input / Output Specs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillInput:
    """Input parameter for a skill."""

    name: str
    type: str = "string"  # string, integer, float, boolean, array
    required: bool = False
    default: Any = None
    choices: list[Any] | None = None
    description: str = ""


@dataclass(frozen=True)
class SkillOutput:
    """Output specification for a skill."""

    name: str
    type: str = "string"  # markdown, json, text, etc.
    description: str = ""


# ---------------------------------------------------------------------------
# Skill Trigger
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillTrigger:
    """Conditions that trigger a skill."""

    keywords: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Skill Retry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillRetry:
    """Retry configuration for a skill."""

    max_attempts: int = 1
    backoff: str = "exponential"  # exponential, linear, fixed


# ---------------------------------------------------------------------------
# Skill Manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillManifest:
    """A complete skill definition in the cross-platform format.

    Compatible with Microsoft Skills Framework schema.
    """

    name: str
    version: str = "1.0.0"
    description: str = ""
    triggers: SkillTrigger = field(default_factory=SkillTrigger)
    allowed_tools: list[str] = field(default_factory=list)
    model: str = ""  # Default model tier: haiku, sonnet, opus
    inputs: list[SkillInput] = field(default_factory=list)
    outputs: list[SkillOutput] = field(default_factory=list)
    timeout: int = 300  # seconds
    retry: SkillRetry = field(default_factory=SkillRetry)
    source: str = ""  # path to the SKILL.md or .yaml file
    body: str = ""    # Markdown body after frontmatter


# ---------------------------------------------------------------------------
# YAML Frontmatter Parsing
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter and body from SKILL.md text.

    Returns (frontmatter_dict, body_text).
    """
    try:
        import yaml as _yaml  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("no YAML frontmatter found (expected --- ... ---)")

    raw = _yaml.safe_load(m.group(1))
    if not isinstance(raw, dict):
        raise ValueError("frontmatter must be a YAML mapping")

    body = m.group(2).strip()
    return raw, body


# ---------------------------------------------------------------------------
# Loading Skills
# ---------------------------------------------------------------------------


def _parse_triggers(raw: dict[str, Any]) -> SkillTrigger:
    triggers_raw = raw.get("triggers", {}) or {}
    return SkillTrigger(
        keywords=list(triggers_raw.get("keywords", []) or []),
        contexts=list(triggers_raw.get("contexts", []) or []),
    )


def _parse_inputs(raw: dict[str, Any]) -> list[SkillInput]:
    inputs_raw = raw.get("inputs", {}) or {}
    if isinstance(inputs_raw, list):
        # list-of-dicts alternative format
        result: list[SkillInput] = []
        for item in inputs_raw:
            result.append(SkillInput(
                name=item["name"],
                type=item.get("type", "string"),
                required=item.get("required", False),
                default=item.get("default"),
                choices=item.get("choices"),
                description=item.get("description", ""),
            ))
        return result
    result = []
    for name, spec in inputs_raw.items():
        if not isinstance(spec, dict):
            continue
        result.append(SkillInput(
            name=name,
            type=spec.get("type", "string"),
            required=spec.get("required", False),
            default=spec.get("default"),
            choices=spec.get("choices"),
            description=spec.get("description", ""),
        ))
    return result


def _parse_outputs(raw: dict[str, Any]) -> list[SkillOutput]:
    outputs_raw = raw.get("outputs", {}) or {}
    if isinstance(outputs_raw, list):
        result: list[SkillOutput] = []
        for item in outputs_raw:
            result.append(SkillOutput(
                name=item["name"],
                type=item.get("type", "string"),
                description=item.get("description", ""),
            ))
        return result
    result = []
    for name, spec in outputs_raw.items():
        if not isinstance(spec, dict):
            continue
        result.append(SkillOutput(
            name=name,
            type=spec.get("type", "string"),
            description=spec.get("description", ""),
        ))
    return result


def _parse_retry(raw: dict[str, Any]) -> SkillRetry:
    retry_raw = raw.get("retry", {}) or {}
    return SkillRetry(
        max_attempts=retry_raw.get("max_attempts", 1),
        backoff=retry_raw.get("backoff", "exponential"),
    )


def _build_manifest(raw: dict[str, Any], body: str, source: str) -> SkillManifest:
    return SkillManifest(
        name=raw["name"],
        version=str(raw.get("version", "1.0.0")),
        description=raw.get("description", ""),
        triggers=_parse_triggers(raw),
        allowed_tools=list(raw.get("allowed_tools", []) or []),
        model=raw.get("model", ""),
        inputs=_parse_inputs(raw),
        outputs=_parse_outputs(raw),
        timeout=int(raw.get("timeout", 300)),
        retry=_parse_retry(raw),
        source=source,
        body=body,
    )


def load_skill_from_markdown(path: str | Path) -> SkillManifest:
    """Load a skill from a SKILL.md file with YAML frontmatter.

    Expected format::

        ---
        name: my-skill
        version: 1.0.0
        description: "Does something useful"
        triggers:
          keywords: ["research", "analyze"]
        allowed_tools:
          - WebSearch
          - Read
        model: sonnet
        inputs:
          query:
            type: string
            required: true
        outputs:
          report:
            type: markdown
        timeout: 300
        retry:
          max_attempts: 3
          backoff: exponential
        ---
        # Skill body (markdown implementation details)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"skill file not found: {path}")

    text = path.read_text()
    raw, body = _parse_frontmatter(text)
    return _build_manifest(raw, body, str(path))


def load_skill_from_yaml(path: str | Path) -> SkillManifest:
    """Load a skill from a standalone .yaml skill definition file."""
    try:
        import yaml as _yaml  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"skill file not found: {path}")

    with open(path, "r") as f:
        raw = _yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"skill YAML root must be a mapping, got: {type(raw).__name__}")

    return _build_manifest(raw, "", str(path))


def load_skill(path: str | Path) -> SkillManifest:
    """Auto-detect format and load a skill from a file.

    - ``.md`` files → SKILL.md with YAML frontmatter
    - ``.yaml`` / ``.yml`` files → standalone YAML definition
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".md":
        return load_skill_from_markdown(path)
    if suffix in (".yaml", ".yml"):
        return load_skill_from_yaml(path)
    # Try frontmatter first, fall back to YAML
    try:
        return load_skill_from_markdown(path)
    except ValueError:
        return load_skill_from_yaml(path)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillValidationResult:
    """Result of validating a skill manifest."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_skill_manifest(manifest: SkillManifest) -> SkillValidationResult:
    """Validate a skill manifest for correctness and completeness."""
    errors: list[str] = []
    warnings: list[str] = []

    if not manifest.name or not manifest.name.strip():
        errors.append("name is required and must be non-empty")

    if not manifest.version:
        errors.append("version is required")
    else:
        parts = manifest.version.split(".")
        if len(parts) < 2 or len(parts) > 4:
            errors.append(f"version '{manifest.version}' is not valid semver")
        elif not all(p.isdigit() for p in parts):
            errors.append(f"version '{manifest.version}' contains non-numeric segments")

    if manifest.timeout <= 0:
        errors.append(f"timeout must be positive, got {manifest.timeout}")

    if manifest.retry.max_attempts < 1:
        errors.append("retry.max_attempts must be >= 1")

    if manifest.retry.backoff not in ("exponential", "linear", "fixed"):
        warnings.append(f"unknown retry backoff: '{manifest.retry.backoff}'")

    if manifest.model and manifest.model not in ("haiku", "sonnet", "opus"):
        warnings.append(f"unknown model tier: '{manifest.model}'")

    # Check input/output name uniqueness
    input_names = [i.name for i in manifest.inputs]
    if len(input_names) != len(set(input_names)):
        errors.append("duplicate input names detected")

    output_names = [o.name for o in manifest.outputs]
    if len(output_names) != len(set(output_names)):
        errors.append("duplicate output names detected")

    return SkillValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Cross-Platform Skill Registry
# ---------------------------------------------------------------------------


@dataclass
class SkillManifestRegistry:
    """A registry of skill manifests with cross-platform lookup."""

    skills: dict[str, SkillManifest] = field(default_factory=dict)

    def register(self, manifest: SkillManifest) -> None:
        """Register a skill manifest."""
        self.skills[manifest.name] = manifest

    def unregister(self, name: str) -> bool:
        """Remove a skill. Returns True if it existed."""
        return self.skills.pop(name, None) is not None

    def get(self, name: str) -> SkillManifest | None:
        """Get a skill by exact name."""
        return self.skills.get(name)

    def find_by_keyword(self, keyword: str) -> list[SkillManifest]:
        """Find skills whose triggers include the given keyword."""
        kw = keyword.lower()
        return [
            s for s in self.skills.values()
            if kw in (k.lower() for k in s.triggers.keywords)
        ]

    def find_by_context(self, context: str) -> list[SkillManifest]:
        """Find skills applicable to a given context."""
        ctx = context.lower()
        return [
            s for s in self.skills.values()
            if ctx in (c.lower() for c in s.triggers.contexts)
        ]

    def find_by_tool(self, tool: str) -> list[SkillManifest]:
        """Find skills that use the given tool."""
        t = tool.lower()
        return [
            s for s in self.skills.values()
            if any(t == allowed.lower() or allowed.lower().startswith(t + "(")
                   for allowed in s.allowed_tools)
        ]

    def list_names(self) -> list[str]:
        return sorted(self.skills)

    def __len__(self) -> int:
        return len(self.skills)

    def __contains__(self, name: str) -> bool:
        return name in self.skills


__all__ = [
    "SkillInput",
    "SkillManifest",
    "SkillManifestRegistry",
    "SkillOutput",
    "SkillRetry",
    "SkillTrigger",
    "SkillValidationResult",
    "load_skill",
    "load_skill_from_markdown",
    "load_skill_from_yaml",
    "validate_skill_manifest",
]
