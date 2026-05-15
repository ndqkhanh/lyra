"""Central API-key store — ``~/.lyra/credentials.json``.

Single source of truth for all provider credentials across sessions.
Keys are stored in the OS keyring when available (macOS Keychain,
Secret Service, Windows Credential Manager) and fall back to a
``chmod 600`` JSON file only when ``keyring`` is not installed.

File format (api_key omitted when keyring holds it)::

    {
      "providers": {
        "anthropic": {"keyring": "true", "base_url": "https://api.anthropic.com"},
        "openai":    {"api_key": "sk-..."},   <- keyring unavailable
        "deepseek":  {"api_key": "sk-..."}
      }
    }

On session boot :meth:`hydrate_env` injects all stored keys into
``os.environ`` (current process only — never shell rc files) so every
downstream component picks them up without extra wiring.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_LYRA_DIR = Path.home() / ".lyra"
_CREDS_FILE = _LYRA_DIR / "credentials.json"
_KEYRING_SERVICE = "lyra-cli"

# Provider → env-var that LLM clients read.  Kept in sync with
# llm_factory._AUTHJSON_PROVIDER_TO_ENV — duplicated here so this
# module is importable without pulling in the full factory.
PROVIDER_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "copilot": "GITHUB_TOKEN",
    "cohere": "COHERE_API_KEY",
    "together": "TOGETHER_API_KEY",
    "perplexity": "PPLX_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
}

# Provider → custom base-URL env var (optional, only set when non-default).
PROVIDER_BASE_URL_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_BASE_URL",
    "openai": "OPENAI_BASE_URL",
    "deepseek": "DEEPSEEK_BASE_URL",
}


# ---------------------------------------------------------------------------
# OS keyring helpers (best-effort, never raise)
# ---------------------------------------------------------------------------


def _kr_set(provider: str, api_key: str) -> bool:
    """Store *api_key* in the OS keyring. Returns True on success."""
    try:
        import keyring as _kr  # type: ignore[import-not-found]
        _kr.set_password(_KEYRING_SERVICE, provider, api_key)
        return True
    except Exception:
        return False


def _kr_get(provider: str) -> str | None:
    """Retrieve a key from the OS keyring, or None."""
    try:
        import keyring as _kr  # type: ignore[import-not-found]
        return _kr.get_password(_KEYRING_SERVICE, provider) or None
    except Exception:
        return None


def _kr_delete(provider: str) -> None:
    """Remove a key from the OS keyring (best-effort)."""
    try:
        import keyring as _kr  # type: ignore[import-not-found]
        _kr.delete_password(_KEYRING_SERVICE, provider)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# KeyStore
# ---------------------------------------------------------------------------


class KeyStore:
    """Read/write credentials and hydrate env vars.

    Storage priority:
    1. OS keyring (``keyring`` package) — raw key never written to disk.
    2. ``~/.lyra/credentials.json`` (``chmod 600``) — fallback when
       ``keyring`` is not installed.

    Callers only use :meth:`set` / :meth:`get` / :meth:`remove` /
    :meth:`list_all` / :meth:`hydrate_env`.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _CREDS_FILE

    # ---- persistence -------------------------------------------------------

    def _load_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"providers": {}}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"providers": {}}
            if "providers" not in data:
                data["providers"] = {}
            return data
        except Exception:
            return {"providers": {}}

    def _save_raw(self, data: dict[str, Any]) -> None:
        parent = self._path.parent
        parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.rename(self._path)
        self._path.chmod(0o600)

    # ---- public API --------------------------------------------------------

    def set(self, provider: str, api_key: str, base_url: str | None = None) -> None:
        """Save *api_key* for *provider*, stamp the process env immediately.

        Uses the OS keyring when available so the raw key is never written
        to the JSON file.  The file always stores metadata (base_url, the
        ``keyring`` marker) so :meth:`list_all` works without the keyring.
        """
        kr_ok = _kr_set(provider, api_key)
        data = self._load_raw()
        entry: dict[str, str] = {}
        if kr_ok:
            entry["keyring"] = "true"  # marker — raw key is in OS keyring
        else:
            entry["api_key"] = api_key  # plaintext fallback
        if base_url:
            entry["base_url"] = base_url
        data["providers"][provider] = entry
        self._save_raw(data)
        self._stamp_env(provider, {"api_key": api_key, **({"base_url": base_url} if base_url else {})})

    def get(self, provider: str) -> dict[str, str] | None:
        """Return the stored entry including the live api_key, or ``None``."""
        providers = self._load_raw().get("providers", {})
        entry = providers.get(provider)
        if not isinstance(entry, dict):
            return None
        entry = dict(entry)
        if entry.get("keyring") == "true":
            key = _kr_get(provider)
            if key:
                entry["api_key"] = key
            else:
                entry.pop("keyring", None)  # keyring gone — entry is degraded
        return entry if entry else None

    def remove(self, provider: str) -> bool:
        """Delete *provider*'s entry from both keyring and file."""
        data = self._load_raw()
        existed = provider in data["providers"]
        data["providers"].pop(provider, None)
        self._save_raw(data)
        _kr_delete(provider)
        return existed

    def list_all(self) -> dict[str, dict[str, str]]:
        """Return a snapshot of all stored entries with live api_keys resolved."""
        providers = self._load_raw().get("providers", {})
        result: dict[str, dict[str, str]] = {}
        for k, v in providers.items():
            if not isinstance(v, dict):
                continue
            entry = dict(v)
            if entry.get("keyring") == "true":
                key = _kr_get(k)
                if key:
                    entry["api_key"] = key
                else:
                    entry.pop("keyring", None)
            result[k] = entry
        return result

    def hydrate_env(self) -> None:
        """Stamp env vars for every stored key — skips slots already set.

        Only mutates ``os.environ`` of the current process; never writes
        shell rc files or exports to child shells.
        """
        for provider, entry in self.list_all().items():
            self._stamp_env(provider, entry, skip_if_set=True)

    # ---- helpers -----------------------------------------------------------

    def _stamp_env(
        self,
        provider: str,
        entry: dict[str, str],
        *,
        skip_if_set: bool = False,
    ) -> None:
        env_var = PROVIDER_ENV_VARS.get(provider)
        api_key = entry.get("api_key", "")
        if env_var and api_key:
            if not skip_if_set or not os.environ.get(env_var):
                os.environ[env_var] = api_key

        base_url_var = PROVIDER_BASE_URL_VARS.get(provider)
        base_url = entry.get("base_url", "")
        if base_url_var and base_url:
            if not skip_if_set or not os.environ.get(base_url_var):
                os.environ[base_url_var] = base_url


def mask_key(key: str) -> str:
    """Show only last 4 chars to avoid leaking prefix patterns: ``****ab12``."""
    if len(key) <= 4:
        return "****"
    return "****" + key[-4:]


# Keep old name as alias for callers that import _mask.
_mask = mask_key


__all__ = ["PROVIDER_ENV_VARS", "KeyStore", "_mask", "mask_key"]
