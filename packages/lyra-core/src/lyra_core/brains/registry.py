"""Brain registry + installer.

The registry is intentionally tiny — every bundle is a frozen
dataclass; the installer writes ``SOUL.md`` + ``policy.yaml`` +
``.lyra/commands/*.md`` and reports what was written/skipped.
Idempotent unless ``force=True`` is passed.

Naming rules (mirrored from
:mod:`lyra_cli.interactive.user_commands`): bundle names are
``[a-z0-9][a-z0-9-]*``; command names follow the same pattern with
the ``.md`` suffix written by the installer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    from lyra_core.paths import RepoLayout


_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class BrainCommand:
    """One user-authored slash command shipped inside a brain bundle.

    The ``body`` is written verbatim to
    ``<repo>/.lyra/commands/<name>.md``; the markdown frontmatter (if
    any) is preserved so :mod:`lyra_cli.interactive.user_commands`
    picks it up on the next REPL boot.
    """

    name: str
    body: str

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ValueError(
                f"command name must match {_NAME_RE.pattern!r}, "
                f"got {self.name!r}"
            )


@dataclass(frozen=True)
class BrainBundle:
    """A curated, installable bundle of agent defaults.

    Fields are all serialisable strings/tuples so a bundle can be
    snapshotted to disk (``~/.lyra/brains/<name>/``) and round-tripped
    without losing fidelity.
    """

    name: str
    description: str
    soul_md: str
    policy_yaml: str | None = None
    toolset: str = "default"
    model_preference: str = "auto"
    tdd_gate_default: bool = False
    commands: tuple[BrainCommand, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ValueError(
                f"brain name must match {_NAME_RE.pattern!r}, "
                f"got {self.name!r}"
            )
        if not self.description.strip():
            raise ValueError("brain description cannot be empty")
        if not self.soul_md.strip():
            raise ValueError("brain soul_md cannot be empty")


@dataclass(frozen=True)
class InstallReport:
    """What :func:`install_brain` actually did on disk."""

    bundle: str
    written: tuple[str, ...]
    skipped: tuple[str, ...]
    repo_root: Path

    @property
    def changed(self) -> bool:
        return bool(self.written)


# --------------------------------------------------------------------- #
# Built-in bundles                                                      #
# --------------------------------------------------------------------- #

_DEFAULT_SOUL = """\
# SOUL.md — default brain

You are Lyra, a general-purpose CLI-native coding agent. You ship
working software fast, ask clarifying questions when intent is
ambiguous, and prefer small reversible edits over large ones.

Defaults:
- Toolset: default
- Model preference: auto (DeepSeek → Anthropic → OpenAI → ...)
- TDD plugin: off (opt-in via /tdd-gate on)
"""

_TDD_STRICT_SOUL = """\
# SOUL.md — tdd-strict brain

You are Lyra in TDD-strict mode. Every code change passes through
RED → GREEN → REFACTOR → SHIP. Refuse to write production code
before a failing test exists. The reviewer rubric is at default
strictness; do not relax it.

Defaults:
- Toolset: coding
- Model preference: auto (smart_model for reasoning)
- TDD plugin: on (enforced gate; do not disable mid-task)
- Reviewer: /ultrareview after every code-touching turn
"""

_RESEARCH_SOUL = """\
# SOUL.md — research brain

You are Lyra in research mode. You read, summarise, and reason; you
do not write code, run shells, or send messages. Outputs are
brief-mode by default: a 3–5 bullet executive answer followed by
optional details only when asked.

Defaults:
- Toolset: safe (read + web only; no Bash, no Edit, no Browser)
- Model preference: auto
- TDD plugin: off
- Persona: terse, evidence-first, link-citing
"""

_SHIP_FAST_SOUL = """\
# SOUL.md — ship-fast brain

You are Lyra in ship-fast mode. Bias toward the smallest change that
moves the project forward. Skip the planning round-trip on simple
asks. Reviewer is best-effort, not gating. Use this brain for
prototypes, glue code, and "just make it work" loops — not for
hardened production code paths.

Defaults:
- Toolset: coding
- Model preference: auto (fast_model for chat)
- TDD plugin: off
- Reviewer: /review on demand only
"""

_TDD_STRICT_POLICY = """\
# policy.yaml — tdd-strict brain
tdd_gate: on
reviewer:
  strictness: strict
permissions:
  default: ask
"""

_RESEARCH_POLICY = """\
# policy.yaml — research brain
toolset: safe
permissions:
  default: ask
  deny:
    - Bash
    - ExecuteCode
    - Edit
    - Write
    - Patch
    - apply_patch
    - send_message
    - Browser
"""

_SHIP_FAST_POLICY = """\
# policy.yaml — ship-fast brain
toolset: coding
reviewer:
  strictness: relaxed
"""

_BUILTIN_BUNDLES: tuple[BrainBundle, ...] = (
    BrainBundle(
        name="default",
        description=(
            "Generic coding agent (the v3.0.0 baseline). "
            "TDD off; default toolset; auto model selection."
        ),
        soul_md=_DEFAULT_SOUL,
        policy_yaml=None,
        toolset="default",
        model_preference="auto",
        tdd_gate_default=False,
    ),
    BrainBundle(
        name="tdd-strict",
        description=(
            "TDD plugin ON; strict reviewer rubric; coding toolset. "
            "Use when you want hard test gates."
        ),
        soul_md=_TDD_STRICT_SOUL,
        policy_yaml=_TDD_STRICT_POLICY,
        toolset="coding",
        model_preference="auto",
        tdd_gate_default=True,
    ),
    BrainBundle(
        name="research",
        description=(
            "Read-only safe toolset; brief-mode persona; "
            "no shells / edits / sends. Use for codebase exploration."
        ),
        soul_md=_RESEARCH_SOUL,
        policy_yaml=_RESEARCH_POLICY,
        toolset="safe",
        model_preference="auto",
        tdd_gate_default=False,
    ),
    BrainBundle(
        name="ship-fast",
        description=(
            "Coding toolset; relaxed reviewer; "
            "smallest-change bias. For prototypes and glue."
        ),
        soul_md=_SHIP_FAST_SOUL,
        policy_yaml=_SHIP_FAST_POLICY,
        toolset="coding",
        model_preference="auto",
        tdd_gate_default=False,
    ),
)


class BrainRegistry:
    """In-memory registry of named brain bundles."""

    def __init__(self, *, builtins: bool = True) -> None:
        self._bundles: dict[str, BrainBundle] = {}
        if builtins:
            for b in _BUILTIN_BUNDLES:
                self._bundles[b.name] = b

    def names(self) -> list[str]:
        return sorted(self._bundles.keys())

    def get(self, name: str) -> BrainBundle | None:
        return self._bundles.get(name)

    def register(self, bundle: BrainBundle) -> None:
        if bundle.name in self._bundles:
            raise ValueError(f"brain {bundle.name!r} already registered")
        self._bundles[bundle.name] = bundle

    def remove(self, name: str) -> None:
        self._bundles.pop(name, None)

    def replace(self, bundle: BrainBundle) -> None:
        """Register a bundle, overwriting any existing entry of the same name."""
        self._bundles[bundle.name] = bundle


_DEFAULT_SINGLETON: BrainRegistry | None = None


def default_registry() -> BrainRegistry:
    """Return a process-wide singleton populated with built-ins."""
    global _DEFAULT_SINGLETON
    if _DEFAULT_SINGLETON is None:
        _DEFAULT_SINGLETON = BrainRegistry(builtins=True)
    return _DEFAULT_SINGLETON


# --------------------------------------------------------------------- #
# Installer                                                             #
# --------------------------------------------------------------------- #


def install_brain(
    bundle: BrainBundle,
    layout: "RepoLayout",
    *,
    force: bool = False,
) -> InstallReport:
    """Write ``bundle`` into ``layout``'s repo.

    The installer always writes:

    * ``<repo>/SOUL.md``                   from ``bundle.soul_md``
    * ``<repo>/.lyra/policy.yaml``         from ``bundle.policy_yaml``
      (only when the bundle ships one)
    * ``<repo>/.lyra/commands/<n>.md``     for each ``BrainCommand``
    * ``<repo>/.lyra/brain.txt``           single-line marker recording
      the active brain name for ``lyra doctor`` etc.

    Existing files are preserved unless ``force=True``. The
    :class:`InstallReport` separates ``written`` from ``skipped`` so
    callers can render a diff.
    """
    layout.ensure()
    written: list[str] = []
    skipped: list[str] = []

    soul_target = layout.soul_md
    if soul_target.exists() and not force:
        skipped.append(str(soul_target.relative_to(layout.repo_root)))
    else:
        soul_target.write_text(bundle.soul_md)
        written.append(str(soul_target.relative_to(layout.repo_root)))

    if bundle.policy_yaml is not None:
        policy_target = layout.policy_yaml
        if policy_target.exists() and not force:
            skipped.append(str(policy_target.relative_to(layout.repo_root)))
        else:
            policy_target.write_text(bundle.policy_yaml)
            written.append(str(policy_target.relative_to(layout.repo_root)))

    if bundle.commands:
        commands_dir = layout.state_dir / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)
        for cmd in bundle.commands:
            cmd_target = commands_dir / f"{cmd.name}.md"
            if cmd_target.exists() and not force:
                skipped.append(str(cmd_target.relative_to(layout.repo_root)))
                continue
            cmd_target.write_text(cmd.body)
            written.append(str(cmd_target.relative_to(layout.repo_root)))

    marker = layout.state_dir / "brain.txt"
    marker.write_text(bundle.name + "\n")
    written.append(str(marker.relative_to(layout.repo_root)))

    return InstallReport(
        bundle=bundle.name,
        written=tuple(written),
        skipped=tuple(skipped),
        repo_root=layout.repo_root,
    )


__all__ = [
    "BrainBundle",
    "BrainCommand",
    "BrainRegistry",
    "InstallReport",
    "default_registry",
    "install_brain",
]
