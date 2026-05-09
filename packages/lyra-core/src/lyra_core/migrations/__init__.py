"""Versioned on-disk migrations for the Lyra state directory.

The primitive ``migrate_state(old, new, *, marker_name=...)`` lives in
:mod:`lyra_core.migrations.state_v1`. The orchestrator below picks the
right legacy source automatically by walking ``layout.legacy_state_dirs``
(newest-first) and dispatches to the primitive with the correct marker.

Brand history covered:

- v1.7:   ``.open-harness``  → ``MIGRATED_FROM_OPEN_HARNESS``
- v1.6:   ``.opencoding``    → ``MIGRATED_FROM_OPENCODING``

lyra-legacy-aware: this module references the legacy directory names
by design — they are the migration sources.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .state_v1 import (
    MARKER_FROM_OPEN_HARNESS,
    MARKER_FROM_OPENCODING,
    migrate_state,
)

if TYPE_CHECKING:  # pragma: no cover
    from lyra_core.paths import RepoLayout

__all__ = [
    "MARKER_FROM_OPEN_HARNESS",
    "MARKER_FROM_OPENCODING",
    "migrate_legacy_state",
    "migrate_state",
]


_MARKER_FOR_DIR = {
    ".open-harness": MARKER_FROM_OPEN_HARNESS,
    ".opencoding": MARKER_FROM_OPENCODING,
}


def migrate_legacy_state(layout: "RepoLayout") -> tuple[bool, Path | None]:
    """Migrate the first legacy state dir found under ``layout``.

    Walks ``layout.legacy_state_dirs`` newest-first:

    1. If none of the legacy directories exist, returns ``(False, None)``
       and never creates the active ``state_dir``.
    2. Otherwise picks the first legacy dir that exists, dispatches to
       :func:`migrate_state` with the right marker, and returns
       ``(performed, source)`` where ``source`` is the legacy ``Path``
       that was used (even if the call was a no-op because ``state_dir``
       was already populated).

    Older legacy directories further down the list are *not* migrated
    or touched, matching the "newest wins" semantics users expect when
    they've upgraded repeatedly.
    """
    for legacy in layout.legacy_state_dirs:
        if not legacy.exists():
            continue
        marker = _MARKER_FOR_DIR.get(legacy.name, MARKER_FROM_OPENCODING)
        performed = migrate_state(legacy, layout.state_dir, marker_name=marker)
        if performed:
            return (True, legacy)
        # Legacy exists but the primitive refused (target already populated);
        # stop so we don't cascade into older legacy dirs.
        return (False, None)
    return (False, None)
