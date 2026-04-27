"""Phase 0 — RED for the v1.7.1 state-dir migration chain.

v1.7.1 introduces a second legacy source: ``.open-harness`` (from v1.7).
The migration chain must handle BOTH v1.6 (``.opencoding``) and v1.7
(``.open-harness``), preferring the newer one when both exist.

Contract:

- A new primitive ``migrate_state(old, new, *, marker_name=...)`` lives
  in ``lyra_core.migrations.state_v1``. It takes an optional
  ``marker_name`` so the same primitive can stamp different origin
  markers (``MIGRATED_FROM_OPENCODING`` or ``MIGRATED_FROM_OPEN_HARNESS``).
- A new orchestrator ``migrate_legacy_state(layout)`` lives in
  ``lyra_core.migrations`` and iterates ``layout.legacy_state_dirs``
  (newest-first: ``.open-harness`` before ``.opencoding``), migrating
  the first legacy dir it finds.
- Orchestrator is idempotent: once ``.lyra`` has content it returns
  ``(False, None)`` and never touches legacy dirs.
- Orchestrator never deletes the legacy directory — data stays
  recoverable.

lyra-legacy-aware: this file intentionally references legacy brand
tokens (``.open-harness``, ``.opencoding``) to exercise the migration.
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _import_primitive():
    try:
        from lyra_core.migrations.state_v1 import (
            MARKER_FROM_OPEN_HARNESS,
            MARKER_FROM_OPENCODING,
            migrate_state,
        )
    except ImportError as exc:
        pytest.fail(
            "lyra_core.migrations.state_v1 must expose migrate_state, "
            f"MARKER_FROM_OPENCODING, MARKER_FROM_OPEN_HARNESS ({exc})"
        )
    return migrate_state, MARKER_FROM_OPENCODING, MARKER_FROM_OPEN_HARNESS


def _import_orchestrator():
    try:
        from lyra_core.migrations import migrate_legacy_state
    except ImportError as exc:
        pytest.fail(
            f"lyra_core.migrations.migrate_legacy_state must exist ({exc})"
        )
    return migrate_legacy_state


def _import_layout():
    try:
        from lyra_core.paths import RepoLayout
    except ImportError as exc:
        pytest.fail(f"lyra_core.paths.RepoLayout must exist ({exc})")
    return RepoLayout


# ------------------------------------------------------------------ #
# Primitive: open-harness -> lyra                                    #
# ------------------------------------------------------------------ #
def test_primitive_migrates_open_harness_with_correct_marker(tmp_path: Path) -> None:
    migrate_state, _mark_oc, mark_oh = _import_primitive()
    old = tmp_path / ".open-harness"
    (old / "sessions").mkdir(parents=True)
    (old / "policy.yaml").write_text("version: 2\n")
    (old / "sessions" / "log.jsonl").write_text("{}\n")

    new = tmp_path / ".lyra"
    result = migrate_state(old, new, marker_name=mark_oh)
    assert result is True
    assert (new / "policy.yaml").read_text() == "version: 2\n"
    assert (new / "sessions" / "log.jsonl").read_text() == "{}\n"
    assert (new / mark_oh).is_file(), (
        f"missing v1.7 migration marker {mark_oh} in {new}"
    )
    # Old dir untouched.
    assert (old / "policy.yaml").is_file()


def test_primitive_marker_names_are_distinct() -> None:
    _mig, mark_oc, mark_oh = _import_primitive()
    assert mark_oc == "MIGRATED_FROM_OPENCODING"
    assert mark_oh == "MIGRATED_FROM_OPEN_HARNESS"
    assert mark_oc != mark_oh


# ------------------------------------------------------------------ #
# Orchestrator: auto-pick newest legacy                              #
# ------------------------------------------------------------------ #
def test_orchestrator_noop_when_no_legacy(tmp_path: Path) -> None:
    migrate_legacy_state = _import_orchestrator()
    RepoLayout = _import_layout()
    layout = RepoLayout(repo_root=tmp_path)
    performed, source = migrate_legacy_state(layout)
    assert performed is False
    assert source is None
    assert not layout.state_dir.exists(), (
        "orchestrator must not create .lyra when there is nothing to migrate"
    )


def test_orchestrator_migrates_open_harness_when_only_it_exists(tmp_path: Path) -> None:
    migrate_legacy_state = _import_orchestrator()
    RepoLayout = _import_layout()
    layout = RepoLayout(repo_root=tmp_path)

    oh_dir = tmp_path / ".open-harness"
    oh_dir.mkdir()
    (oh_dir / "policy.yaml").write_text("from-v1.7\n")

    performed, source = migrate_legacy_state(layout)
    assert performed is True
    assert source == oh_dir
    assert (layout.state_dir / "policy.yaml").read_text() == "from-v1.7\n"
    assert (layout.state_dir / "MIGRATED_FROM_OPEN_HARNESS").is_file()
    # opencoding marker must NOT be there.
    assert not (layout.state_dir / "MIGRATED_FROM_OPENCODING").is_file()


def test_orchestrator_migrates_opencoding_when_only_it_exists(tmp_path: Path) -> None:
    migrate_legacy_state = _import_orchestrator()
    RepoLayout = _import_layout()
    layout = RepoLayout(repo_root=tmp_path)

    oc_dir = tmp_path / ".opencoding"
    oc_dir.mkdir()
    (oc_dir / "policy.yaml").write_text("from-v1.6\n")

    performed, source = migrate_legacy_state(layout)
    assert performed is True
    assert source == oc_dir
    assert (layout.state_dir / "policy.yaml").read_text() == "from-v1.6\n"
    assert (layout.state_dir / "MIGRATED_FROM_OPENCODING").is_file()


def test_orchestrator_prefers_open_harness_when_both_legacy_exist(tmp_path: Path) -> None:
    """A user who went v1.6 -> v1.7 -> v1.7.1 has BOTH legacy dirs.
    The newer one wins; the older one is left untouched."""
    migrate_legacy_state = _import_orchestrator()
    RepoLayout = _import_layout()
    layout = RepoLayout(repo_root=tmp_path)

    oc_dir = tmp_path / ".opencoding"
    oc_dir.mkdir()
    (oc_dir / "policy.yaml").write_text("v1.6-content\n")

    oh_dir = tmp_path / ".open-harness"
    oh_dir.mkdir()
    (oh_dir / "policy.yaml").write_text("v1.7-content\n")

    performed, source = migrate_legacy_state(layout)
    assert performed is True
    assert source == oh_dir, "must prefer the newer legacy dir"
    assert (layout.state_dir / "policy.yaml").read_text() == "v1.7-content\n", (
        "content must come from .open-harness, not .opencoding"
    )
    assert (layout.state_dir / "MIGRATED_FROM_OPEN_HARNESS").is_file()
    assert not (layout.state_dir / "MIGRATED_FROM_OPENCODING").is_file()
    # Both legacy dirs preserved.
    assert (oc_dir / "policy.yaml").is_file()
    assert (oh_dir / "policy.yaml").is_file()


def test_orchestrator_is_idempotent(tmp_path: Path) -> None:
    migrate_legacy_state = _import_orchestrator()
    RepoLayout = _import_layout()
    layout = RepoLayout(repo_root=tmp_path)

    oh_dir = tmp_path / ".open-harness"
    oh_dir.mkdir()
    (oh_dir / "policy.yaml").write_text("initial\n")

    # First call migrates.
    performed1, _ = migrate_legacy_state(layout)
    assert performed1 is True

    # User edits the migrated state.
    (layout.state_dir / "policy.yaml").write_text("user-edited\n")

    # Second call must be a no-op.
    performed2, source2 = migrate_legacy_state(layout)
    assert performed2 is False
    assert source2 is None
    assert (layout.state_dir / "policy.yaml").read_text() == "user-edited\n"
