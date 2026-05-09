"""Wave-D Task 3: user-defined subagent presets.

Drop a YAML or JSON file under ``~/.lyra/agents/<name>.yaml`` and Lyra
loads it as a preset that ``/spawn <name>`` (and the registry) can
reference. Built-ins (``explore``, ``general``, ``plan``) are always
present so a fresh install has at least one of each kind.

Why three built-ins?

* ``explore``     — leaf, read-only codebase search
  (Read / Glob / Grep). Mirrors claw-code's ``explore`` agent.
* ``general``     — leaf, multi-step specialist with the full tool
  belt. Mirrors hermes-agent's ``run_conversation`` default.
* ``plan``        — orchestrator, fans out to leaves and joins their
  reports. Mirrors opencode's ``planner`` workflow.

Loader contract:

* Returns a :class:`PresetBundle` (presets + errors).
* Never raises — a malformed file is recorded in ``errors`` and the
  rest of the directory continues loading.
* User files **shadow** built-ins by name (so a user can re-tune the
  built-in ``explore`` without forking the codebase).
* Aliases resolve via :meth:`PresetBundle.resolve`; primary names are
  always present in :attr:`PresetBundle.presets`.
* Role is normalised against ``{"leaf", "orchestrator"}`` — anything
  else falls back to ``"leaf"`` so a typo doesn't accidentally
  promote a sub-agent into an orchestrator.

Optional dependency: ``yaml``. We import it lazily inside
:func:`load_presets`. If it isn't installed we fall back to ``json``
parsing (so JSON presets always work, YAML presets degrade to a
``yaml not installed`` error in :attr:`PresetBundle.errors`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal


PresetRole = Literal["leaf", "orchestrator"]
_VALID_ROLES: frozenset[str] = frozenset({"leaf", "orchestrator"})


@dataclass
class SubagentPreset:
    """A single preset entry."""

    name: str
    description: str = ""
    model: str | None = None
    role: PresetRole = "leaf"
    tools: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    source: str = "builtin"  # "builtin" | "user" | "user-overrides-builtin"


@dataclass
class PresetBundle:
    """Result of loading the presets directory."""

    presets: dict[str, SubagentPreset] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def names(self) -> list[str]:
        return sorted(self.presets.keys())

    def resolve(self, name: str) -> SubagentPreset:
        """Return the preset matching ``name`` or any alias.

        Raises :class:`KeyError` when the name is unknown — callers
        that want graceful UX should ``in`` check ``presets`` first.
        """
        if name in self.presets:
            return self.presets[name]
        lname = name.strip().lower()
        for preset in self.presets.values():
            if any(a.strip().lower() == lname for a in preset.aliases):
                return preset
        raise KeyError(f"unknown preset {name!r}")


# ---------------------------------------------------------------------------
# Built-ins.
# ---------------------------------------------------------------------------


_BUILTINS: tuple[SubagentPreset, ...] = (
    SubagentPreset(
        name="explore",
        description=(
            "fast, read-only codebase exploration "
            "(Read/Glob/Grep, no Edit/Write)."
        ),
        model="haiku",
        role="leaf",
        tools=["Read", "Glob", "Grep"],
    ),
    SubagentPreset(
        name="general",
        description=(
            "multi-step specialist with the full tool belt — "
            "reach for this when the task crosses several files."
        ),
        model="sonnet",
        role="leaf",
        tools=["Read", "Glob", "Grep", "Edit", "Write", "Shell"],
    ),
    SubagentPreset(
        name="plan",
        description=(
            "orchestrator: builds a plan, fans out to leaf agents, "
            "joins their reports back into a single answer."
        ),
        model="opus",
        role="orchestrator",
        tools=["Task", "TodoWrite", "Read"],
    ),
)


def _builtins() -> dict[str, SubagentPreset]:
    """Fresh dict of built-ins so callers can mutate without leaking."""
    return {p.name: SubagentPreset(**p.__dict__) for p in _BUILTINS}


# ---------------------------------------------------------------------------
# Loader.
# ---------------------------------------------------------------------------


def _load_one(path: Path) -> dict:
    """Parse a single preset file. Always returns a dict.

    YAML preferred; falls back to JSON when ``yaml`` is missing or the
    file extension is ``.json``. Raises :class:`ValueError` (or any
    parser-specific error) on malformed input — :func:`load_presets`
    catches the exception and records it.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".json",):
        return json.loads(text)

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            f"yaml not installed; cannot read {path.name}"
        ) from exc
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(
            f"{path.name}: expected top-level mapping, got {type(data).__name__}"
        )
    return data


def _coerce_preset(name: str, raw: dict, *, source: str) -> SubagentPreset:
    role_raw = str(raw.get("role", "leaf")).strip().lower()
    role: PresetRole = "leaf"  # safe default
    if role_raw in _VALID_ROLES:
        role = role_raw  # type: ignore[assignment]
    tools = raw.get("tools") or []
    if not isinstance(tools, list):
        tools = []
    aliases = raw.get("aliases") or []
    if not isinstance(aliases, list):
        aliases = []
    return SubagentPreset(
        name=str(raw.get("name", name)).strip() or name,
        description=str(raw.get("description", "")).strip(),
        model=raw.get("model") or None,
        role=role,
        tools=[str(t) for t in tools],
        aliases=[str(a) for a in aliases],
        source=source,
    )


def load_presets(*, user_dir: Path | str) -> PresetBundle:
    """Load built-ins + every preset under ``user_dir``.

    Parameters
    ----------
    user_dir:
        The user-presets directory; conventionally
        ``~/.lyra/agents``. Missing or empty is fine — built-ins are
        always returned.

    Returns
    -------
    PresetBundle
        ``presets`` always contains the built-ins (possibly shadowed
        by user files). ``errors`` lists per-file failures by file
        name; the loader never raises.
    """
    bundle = PresetBundle(presets=_builtins())
    root = Path(user_dir)
    if not root.exists() or not root.is_dir():
        return bundle

    for child in sorted(root.iterdir()):
        if child.is_dir():
            continue
        if child.suffix.lower() not in (".yaml", ".yml", ".json"):
            continue
        name = child.stem
        try:
            raw = _load_one(child)
        except Exception as exc:  # malformed file — record + skip
            bundle.errors.append(f"{child.name}: {exc}")
            continue
        if not isinstance(raw, dict):
            bundle.errors.append(
                f"{child.name}: top-level value must be a mapping"
            )
            continue
        preset = _coerce_preset(name, raw, source="user")
        if preset.name in _builtins():
            preset.source = "user-overrides-builtin"
        bundle.presets[preset.name] = preset
    return bundle


def list_user_dirs(home: Path | str | None = None) -> Iterable[Path]:
    """Yield the conventional user preset locations.

    Today only ``$HOME/.lyra/agents`` is searched; the helper exists
    so a future Wave can layer in ``$LYRA_HOME/agents`` or per-repo
    ``.lyra/agents/`` without touching :func:`load_presets`.
    """
    base = Path(home) if home is not None else Path.home()
    yield base / ".lyra" / "agents"


__all__ = [
    "PresetBundle",
    "SubagentPreset",
    "PresetRole",
    "load_presets",
    "list_user_dirs",
]
