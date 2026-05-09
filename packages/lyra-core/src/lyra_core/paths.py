"""Filesystem layout for a repo initialised with Lyra.

Canonical location (``lyra_core.paths``) so both the CLI package and the
migration helpers can reach a single source of truth.

The ``state_dir`` attribute is the active state directory for a given
repo (``.lyra``). The ``legacy_state_dirs`` attribute lists historical
state-directory names in priority order (newest-first) so the migration
orchestrator in :mod:`lyra_core.migrations` can detect a legacy install
and copy it across without touching the originals.

Brand history (most-recent first):

- v1.7.1+: ``.lyra``
- v1.7:    ``.open-harness`` (now legacy)
- v1.6:    ``.opencoding`` (now legacy)

lyra-legacy-aware: this module references the two legacy directory names
(``.open-harness`` and ``.opencoding``) by design — they are migration
sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoLayout:
    repo_root: Path

    # ------------------------------------------------------------------ #
    # Canonical state-dir accessors                                      #
    # ------------------------------------------------------------------ #
    @property
    def state_dir(self) -> Path:
        """The active state directory for this repo (``.lyra``)."""
        return self.repo_root / ".lyra"

    @property
    def legacy_state_dirs(self) -> list[Path]:
        """Historical state directories, newest-first.

        The migration orchestrator iterates this list in order: the first
        one that exists wins. That means a user who went v1.6 → v1.7 →
        v1.7.1 and has BOTH ``.opencoding`` and ``.open-harness`` on
        disk gets their ``.open-harness`` (more recent) migrated.
        """
        return [
            self.repo_root / ".open-harness",
            self.repo_root / ".opencoding",
        ]

    # Back-compat aliases for code still using the old accessor names.
    @property
    def legacy_state_dir(self) -> Path:  # pragma: no cover - alias
        """Deprecated: first legacy dir. Prefer :attr:`legacy_state_dirs`."""
        return self.legacy_state_dirs[0]

    @property
    def open_harness_dir(self) -> Path:  # pragma: no cover - alias
        return self.state_dir

    # ------------------------------------------------------------------ #
    # Derived paths                                                      #
    # ------------------------------------------------------------------ #
    @property
    def soul_md(self) -> Path:
        return self.repo_root / "SOUL.md"

    @property
    def policy_yaml(self) -> Path:
        return self.state_dir / "policy.yaml"

    @property
    def plans_dir(self) -> Path:
        return self.state_dir / "plans"

    @property
    def sessions_dir(self) -> Path:
        return self.state_dir / "sessions"

    @property
    def hir_log(self) -> Path:
        return self.state_dir / "hir.jsonl"

    def ensure(self) -> None:
        """Create all directories this layout expects. Idempotent."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["RepoLayout"]
