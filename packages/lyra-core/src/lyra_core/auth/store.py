"""Persist API keys to ``~/.lyra/auth.json`` with mode-0600 enforcement.

Backs the ``lyra connect`` Typer subcommand and the ``/connect`` REPL
slash. Both write here once preflight clears, so the next agent turn
can read the key without forcing the user to re-set an env var.

Resolution order at read time (in :mod:`llm_factory`):

1. ``os.environ`` — wins if set, so ``ANTHROPIC_API_KEY=foo lyra``
   continues to override a stored key.
2. Project-local ``.env`` (via :mod:`lyra_core.providers.dotenv`).
3. ``~/.lyra/auth.json`` (this module) — the long-lived store.

Mode-0600 enforcement is non-negotiable: the file holds raw API
secrets, so a leaked key would require either a deliberate ``chmod``
or shared-uid pwn. We re-chmod on every write so an old 0644 file
gets tightened automatically the next time the user runs ``lyra
connect``.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

__all__ = [
    "auth_path",
    "clear_budget",
    "get_api_key",
    "has_any_provider",
    "list_providers",
    "load",
    "load_budget",
    "lyra_home",
    "revoke",
    "save",
    "save_budget",
]


_DEFAULT_HOME_DIRNAME = ".lyra"
_AUTH_FILENAME = "auth.json"


def lyra_home() -> Path:
    """Resolve the directory that holds ``auth.json``.

    Honours ``$LYRA_HOME`` (lets the test suite redirect writes into
    a tmp dir) and falls back to ``~/.lyra``. Never expanded eagerly
    at import time so test fixtures that ``monkeypatch.setenv`` work
    correctly.
    """
    env = os.environ.get("LYRA_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / _DEFAULT_HOME_DIRNAME


def auth_path() -> Path:
    """Full path to the auth.json file (may not exist yet)."""
    return lyra_home() / _AUTH_FILENAME


def load() -> dict[str, Any]:
    """Return the parsed auth.json, or an empty skeleton if absent.

    Always returns a dict shaped ``{"providers": {...}}`` so callers
    can do ``data["providers"]["openai"]["api_key"]`` without
    defensive ``.get`` chains. Corrupt JSON is treated like a missing
    file rather than crashing the agent on startup.
    """
    path = auth_path()
    if not path.is_file():
        return {"providers": {}}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"providers": {}}
    if not isinstance(parsed, dict):
        return {"providers": {}}
    parsed.setdefault("providers", {})
    if not isinstance(parsed["providers"], dict):
        parsed["providers"] = {}
    return parsed


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via tempfile + rename.

    Avoids the half-written file failure mode where a crash between
    ``open`` and ``write`` leaves an empty ``auth.json`` and locks
    the user out of every previously-saved provider.
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".auth-", dir=str(parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        # Ensure tight perms before rename so there's never a moment
        # where the file is world-readable.
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def save(provider: str, api_key: str, *, model: str | None = None) -> None:
    """Persist ``api_key`` (and optional ``model``) for ``provider``.

    Re-chmods the file to 0600 on every write — even if the user
    accidentally relaxed perms with ``chmod 0644 ~/.lyra/auth.json``,
    the next ``lyra connect`` tightens them again.
    """
    data = load()
    entry: dict[str, Any] = {"api_key": api_key}
    if model:
        entry["model"] = model
    data["providers"][provider] = entry

    path = auth_path()
    _atomic_write(path, json.dumps(data, indent=2, sort_keys=True))
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def list_providers() -> list[str]:
    """Sorted list of provider names that have a saved key."""
    data = load()
    if not data.get("providers"):
        return []
    return sorted(data["providers"].keys())


def has_any_provider() -> bool:
    """``True`` iff at least one provider has been saved.

    Used by the REPL auto-trigger logic — we open the connect dialog
    on first launch when this returns ``False`` and no env-var key is
    set either.
    """
    return bool(list_providers())


def revoke(provider: str) -> None:
    """Remove ``provider`` from the store. No-op if not present."""
    data = load()
    if provider in data.get("providers", {}):
        del data["providers"][provider]
        path = auth_path()
        _atomic_write(path, json.dumps(data, indent=2, sort_keys=True))
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def get_api_key(provider: str) -> str | None:
    """Return the saved API key for ``provider`` or ``None``."""
    data = load()
    entry = data.get("providers", {}).get(provider)
    if isinstance(entry, dict):
        key = entry.get("api_key")
        if isinstance(key, str) and key:
            return key
    return None


# ---------------------------------------------------------------------------
# Budget persistence (v2.2.3)
#
# Sits next to the provider keys in ``auth.json`` so a single 0600 file
# holds everything that needs to survive REPL restarts. Schema lives
# under the top-level ``budget`` key so it never collides with provider
# names:
#
#     {
#       "providers": {...},
#       "budget": {
#         "cap_usd": 5.0,
#         "alert_pct": 80.0,
#         "auto_stop": true
#       }
#     }
#
# Every field is optional. ``cap_usd`` may be ``None`` to mean "no
# automatic cap" — the meter still tracks spend, it just doesn't
# refuse turns. The driver reads this on boot to seed
# ``session.budget_cap_usd``; the ``/budget save`` slash and the
# ``--budget`` CLI flag write here.
# ---------------------------------------------------------------------------


_DEFAULT_ALERT_PCT = 80.0


def load_budget() -> dict[str, Any]:
    """Return the persisted budget block, with defaults filled in.

    Always returns a dict with three keys (``cap_usd``, ``alert_pct``,
    ``auto_stop``) so callers can index without ``.get`` chains. A
    missing or corrupt file is treated as "no cap configured".
    """
    data = load()
    block = data.get("budget") if isinstance(data.get("budget"), dict) else {}
    cap = block.get("cap_usd")
    if cap is not None:
        try:
            cap = float(cap)
            if cap < 0:
                cap = None
        except (TypeError, ValueError):
            cap = None
    alert = block.get("alert_pct", _DEFAULT_ALERT_PCT)
    try:
        alert = float(alert)
        if alert <= 0 or alert > 100:
            alert = _DEFAULT_ALERT_PCT
    except (TypeError, ValueError):
        alert = _DEFAULT_ALERT_PCT
    auto_stop = bool(block.get("auto_stop", True))
    return {"cap_usd": cap, "alert_pct": alert, "auto_stop": auto_stop}


def save_budget(
    *,
    cap_usd: float | None,
    alert_pct: float | None = None,
    auto_stop: bool | None = None,
) -> None:
    """Persist budget settings into ``auth.json``.

    Only fields passed explicitly are mutated — ``alert_pct=None``
    means "leave the existing value alone", not "reset to default".
    Pass ``cap_usd=None`` to clear the persisted cap (the next
    session will boot uncapped).
    """
    data = load()
    block = data.get("budget") if isinstance(data.get("budget"), dict) else {}
    if cap_usd is None:
        block.pop("cap_usd", None)
    else:
        block["cap_usd"] = float(cap_usd)
    if alert_pct is not None:
        block["alert_pct"] = float(alert_pct)
    if auto_stop is not None:
        block["auto_stop"] = bool(auto_stop)
    data["budget"] = block

    path = auth_path()
    _atomic_write(path, json.dumps(data, indent=2, sort_keys=True))
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def clear_budget() -> None:
    """Remove the persisted budget block entirely."""
    data = load()
    if "budget" in data:
        del data["budget"]
        path = auth_path()
        _atomic_write(path, json.dumps(data, indent=2, sort_keys=True))
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
