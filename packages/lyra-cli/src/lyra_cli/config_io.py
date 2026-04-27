"""Read / write helpers for ``$LYRA_HOME/settings.json`` and ``.env``.

Phase N.4 introduces a versioned user-global config (the wizard
seeds it; future migrations bump :data:`LYRA_CONFIG_VERSION`).
Phase N.8 will hang the import-string provider registry off the
same file. Keep the surface tiny — load, save, env write — so
both layers reuse it without circular imports.

All writes go through ``os.replace`` so a crash mid-write leaves
the previous file intact instead of a half-truncated one.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping


# Bumped whenever the on-disk schema changes in a non-additive way.
#
# * v1 (Phase N.4) — seeded ``default_provider`` / ``default_model``.
# * v2 (Phase N.8) — adds the ``providers`` map for import-string
#   custom providers (``slug → "pkg.mod:Symbol"``). Pre-v2 configs
#   are migrated by :func:`_maybe_migrate` on read; old files
#   keep working without a manual edit.
LYRA_CONFIG_VERSION = 2


def load_settings(path: Path | str) -> dict[str, Any]:
    """Read *path* and return its JSON dict.

    Missing file ⇒ empty dict (the wizard treats that as "first
    run"). Malformed JSON ⇒ empty dict + the corrupt file is
    *renamed*, not deleted, so the user can see what went wrong.

    Returned dict is always mutable; callers update + pass back to
    :func:`save_settings`.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        return {}
    raw = p.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Move corrupt file aside so the wizard can write a clean
        # one without nuking the user's history.
        p.rename(p.with_suffix(p.suffix + ".corrupt"))
        return {}
    if not isinstance(data, dict):
        return {}
    return _maybe_migrate(data)


def save_settings(path: Path | str, settings: Mapping[str, Any]) -> Path:
    """Write *settings* to *path* atomically; chmod 600.

    Atomicity is via tempfile + ``os.replace``. Permissions are
    600 because ``settings.json`` may end up next to ``.env`` and
    we treat the whole config dir as sensitive.
    """
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(settings)
    payload.setdefault("config_version", LYRA_CONFIG_VERSION)
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    fd, tmp = tempfile.mkstemp(prefix=".settings.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, p)
    except Exception:
        # Clean up the temp file on failure so we don't litter the
        # config dir with .settings.<random> droppings.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


def write_env_file(path: Path | str, vars: Mapping[str, str]) -> Path:
    """Merge *vars* into a ``KEY=VALUE`` ``.env`` file at *path*.

    Existing variables in the file are *preserved* (we read, merge,
    then write) so a user who already has ``DATABASE_URL=...`` in
    ``$LYRA_HOME/.env`` doesn't lose it when we add an API key.
    Values are written verbatim — the file is meant to be sourced
    via ``set -a; source ... ; set +a`` so callers wanting full
    POSIX shell compatibility should escape special chars themselves.

    Permissions: 600 (the file holds API keys).
    """
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, str] = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, _, val = stripped.partition("=")
            if key:
                existing[key.strip()] = val
    existing.update(vars)
    body = "".join(f"{k}={v}\n" for k, v in existing.items())

    fd, tmp = tempfile.mkstemp(prefix=".env.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


def _maybe_migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Bump older config blobs to the current schema.

    Migrations are intentionally additive: we never drop user keys.
    The v1→v2 step seeds an empty ``providers`` dict so callers can
    rely on ``settings["providers"]`` being a dict without an
    explicit ``in`` check.

    Pre-v1 (no ``config_version`` at all) hand-crafted files get
    stamped at v1 first, then migrated forward.
    """
    data = dict(data)
    version = data.get("config_version")
    if version is None:
        version = 1
    if version < 2:
        data.setdefault("providers", {})
        version = 2
    data["config_version"] = version
    return data


__all__ = [
    "LYRA_CONFIG_VERSION",
    "load_settings",
    "save_settings",
    "write_env_file",
]
