"""v1 state-directory migration primitive.

Abstracts the tree-copy operation from the *source brand* by taking a
``marker_name`` keyword argument. The orchestrator in
:mod:`lyra_core.migrations` picks the right marker for the detected
legacy source:

- ``.opencoding`` (v1.6) → ``MIGRATED_FROM_OPENCODING``
- ``.open-harness`` (v1.7) → ``MIGRATED_FROM_OPEN_HARNESS``

lyra-legacy-aware: this module references ``.opencoding`` and
``.open-harness`` directory names by design — they are the legitimate
migration sources.

Contract (see tests in ``test_state_dir_migration.py`` and
``test_state_dir_migration_v2.py``):

- No-op when ``old`` does not exist. Returns ``False`` and does *not*
  create anything at ``new``.
- Copies the tree recursively when ``old`` exists. Writes the chosen
  marker file into ``new`` for auditing. Returns ``True``.
- Idempotent: if ``new`` already exists with content, we treat it as
  *already migrated* and leave both sides alone — returning ``False``.
- The old directory is *never* deleted; users keep their data
  recoverable even after migration.
"""
from __future__ import annotations

import shutil
from pathlib import Path

__all__ = [
    "MARKER_FROM_OPENCODING",
    "MARKER_FROM_OPEN_HARNESS",
    "MARKER_NAME",
    "migrate_state",
]

MARKER_FROM_OPENCODING = "MIGRATED_FROM_OPENCODING"
MARKER_FROM_OPEN_HARNESS = "MIGRATED_FROM_OPEN_HARNESS"

# Back-compat alias for callers that used the pre-v1.7.1 single-marker API.
MARKER_NAME = MARKER_FROM_OPENCODING


def _is_effectively_empty(path: Path) -> bool:
    """Treat a directory as 'nothing to preserve' only when it's genuinely empty."""
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    return not any(path.iterdir())


def _marker_body(marker_name: str) -> str:
    if marker_name == MARKER_FROM_OPEN_HARNESS:
        source = ".open-harness"
    elif marker_name == MARKER_FROM_OPENCODING:
        source = ".opencoding"
    else:
        source = "a legacy Lyra state directory"
    return (
        f"This directory was migrated from {source}. "
        "Safe to delete once you have verified your state.\n"
    )


def migrate_state(
    old: Path,
    new: Path,
    *,
    marker_name: str = MARKER_FROM_OPENCODING,
) -> bool:
    """Copy ``old`` -> ``new`` once, idempotently.

    Returns ``True`` iff this call performed the migration. Any other
    state (nothing to migrate; already migrated) returns ``False``.

    The written marker file tells apart fresh installs from migrated
    ones and encodes which legacy brand the data came from.
    """
    # Nothing to migrate.
    if not old.exists():
        return False

    # Already migrated (destination has any content).
    if new.exists() and not _is_effectively_empty(new):
        return False

    # Fresh migration: recursively copy the tree.
    new.mkdir(parents=True, exist_ok=True)
    for entry in old.iterdir():
        dest = new / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dest, dirs_exist_ok=False)
        else:
            shutil.copy2(entry, dest)

    # Leave a marker so we can tell migrated data apart from a fresh install.
    (new / marker_name).write_text(_marker_body(marker_name), encoding="utf-8")
    return True
