"""Per-skill enable/disable overrides driven by the ``/skills`` picker.

Every skill discovered on disk is *advertised by default*; this module
records the user's deviations from that default in a small JSON file
alongside ``skill_ledger.json``. The inject layer
(:func:`lyra_cli.interactive.skills_inject.render_skill_block`)
consults the state to drop disabled skills before the activation block
is built.

State semantics
---------------
* ``enabled`` is a forward-compat slot — today it's a no-op because
  every discovered skill is on by default. It exists so the picker
  can record an explicit opt-in once we ship default-off skills.
* ``disabled`` is the meaningful set. A skill id in this set is
  filtered out of the system-prompt block.
* ``locked`` skills (packaged packs that ship with Lyra) are ignored
  even if they appear in ``disabled`` — uninstalling them is a
  separate operation (``lyra skill remove``).

Persistence mirrors :mod:`lyra_skills.ledger`: tempfile + ``os.replace``
so a crash mid-write leaves the previous file intact, and a malformed
JSON is renamed with a ``.corrupt`` suffix so the user can post-mortem.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = [
    "SkillsState",
    "default_state_path",
    "is_active",
    "load_state",
    "save_state",
    "with_toggled",
]


@dataclass(frozen=True)
class SkillsState:
    """Immutable view of the user's per-skill overrides."""

    enabled: frozenset[str] = field(default_factory=frozenset)
    disabled: frozenset[str] = field(default_factory=frozenset)


# ── activation logic ─────────────────────────────────────────────


def is_active(skill_id: str, *, locked: bool, state: SkillsState) -> bool:
    """Return True when *skill_id* should be advertised this turn.

    Rules (in order):

    1. Locked skills are always active — the picker hides the toggle
       and the state file is ignored for them.
    2. A skill in ``disabled`` is off.
    3. Otherwise on (Lyra's default-on policy).
    """
    if locked:
        return True
    if skill_id in state.disabled:
        return False
    return True


def with_toggled(
    state: SkillsState,
    skill_id: str,
    *,
    currently_active: bool,
) -> SkillsState:
    """Return a new state with *skill_id*'s active-bit flipped.

    Caller passes the *current* active flag (from
    :func:`is_active`) so the function knows whether to add or
    remove the id from ``disabled``.
    """
    if currently_active:
        return SkillsState(
            enabled=state.enabled - {skill_id},
            disabled=state.disabled | {skill_id},
        )
    return SkillsState(
        enabled=state.enabled - {skill_id},
        disabled=state.disabled - {skill_id},
    )


# ── persistence ──────────────────────────────────────────────────


def default_state_path() -> Path:
    """``$LYRA_HOME/skills_state.json`` (or ``~/.lyra/skills_state.json``).

    Mirrors :func:`lyra_skills.ledger.default_ledger_path` so all
    per-user state lives under one root.
    """
    home_env = os.environ.get("LYRA_HOME")
    if home_env:
        return Path(home_env).expanduser() / "skills_state.json"
    return (
        Path(os.environ.get("HOME", ".")).expanduser()
        / ".lyra"
        / "skills_state.json"
    )


def _resolve(path: Path | str | None) -> Path:
    return Path(path).expanduser() if path is not None else default_state_path()


def load_state(path: Path | str | None = None) -> SkillsState:
    """Read overrides from *path* (or the default).

    Missing file ⇒ empty state. Malformed JSON ⇒ empty state and
    the corrupt file is renamed with a ``.corrupt`` suffix.
    """
    p = _resolve(path)
    if not p.is_file():
        return SkillsState()
    raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            p.rename(p.with_suffix(p.suffix + ".corrupt"))
        except OSError:
            pass
        return SkillsState()
    if not isinstance(data, dict):
        return SkillsState()
    enabled = data.get("enabled") or []
    disabled = data.get("disabled") or []
    if not isinstance(enabled, list):
        enabled = []
    if not isinstance(disabled, list):
        disabled = []
    return SkillsState(
        enabled=frozenset(str(x) for x in enabled),
        disabled=frozenset(str(x) for x in disabled),
    )


def save_state(
    state: SkillsState,
    path: Path | str | None = None,
) -> Path:
    """Atomically persist *state* to *path*.

    Tempfile + ``os.replace`` keeps the previous state file intact on
    crash. Sets are serialised as sorted JSON arrays so the file is
    diff-friendly and saves of equal state hash identically.
    """
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = (
        json.dumps(
            {
                "enabled": sorted(state.enabled),
                "disabled": sorted(state.disabled),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    fd, tmp = tempfile.mkstemp(prefix=".skills_state.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


# Optional: typed re-export for downstream callers that don't want
# to import `Optional` themselves.
StatePathLike = Optional[Path | str]
