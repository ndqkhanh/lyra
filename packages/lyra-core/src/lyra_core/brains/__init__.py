"""Brain bundles — curated, installable agent presets.

Inspired by `garrytan/gbrain` ("Garry's Opinionated OpenClaw/Hermes
Agent Brain"). A "brain" is a single named bundle of opinionated
defaults that the user can install into a repo with one command:

    $ lyra brain install ship-fast

The bundle drops a curated ``SOUL.md`` + optional ``policy.yaml`` +
optional ``.lyra/commands/*.md`` into the target repo. It does not
mutate the live session — the user re-enters ``lyra`` (or runs
``/init --force``) to pick up the new persona.

Public surface:

* :class:`BrainBundle` — frozen dataclass; one curated preset.
* :class:`BrainCommand` — one user-authored slash command shipped
  inside a bundle (``.lyra/commands/<name>.md``).
* :class:`BrainRegistry` — built-in + user-registered bundles.
* :func:`install_brain` — write a bundle into a :class:`RepoLayout`.
* :func:`default_registry` — singleton with the four built-ins.

The four built-ins:

* ``default``      — the v3.0.0 generic coding agent.
* ``tdd-strict``   — TDD plugin ON; strict reviewer rubric.
* ``research``     — read-only ``safe`` toolset; brief-mode persona.
* ``ship-fast``    — coding toolset; relaxed reviewer; GREEN-first.

User-defined bundles can be registered at runtime via
``BrainRegistry.register`` and round-trip through
``~/.lyra/brains/<name>/`` on disk.
"""
from __future__ import annotations

from .registry import (
    BrainBundle,
    BrainCommand,
    BrainRegistry,
    InstallReport,
    default_registry,
    install_brain,
)

__all__ = [
    "BrainBundle",
    "BrainCommand",
    "BrainRegistry",
    "InstallReport",
    "default_registry",
    "install_brain",
]
