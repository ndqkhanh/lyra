"""Custom provider registry — extensibility for ``lyra build_llm`` (Phase N.8).

Power-users want to plug in *their own* :class:`LLMProvider`
implementations without forking Lyra. ``settings.json`` now carries
a ``providers`` dict that maps a slug to a Python import string:

.. code-block:: json

    {
      "config_version": 2,
      "providers": {
        "in-house": "mypkg.providers:InHouseLLM",
        "router-v2": "mypkg.providers:RouterFactory"
      }
    }

When ``--llm in-house`` is used, the CLI imports
``mypkg.providers``, looks up ``InHouseLLM``, and either
instantiates it (if it's a class) or calls it (if it's a factory
function). The result must implement
:class:`harness_core.models.LLMProvider`.

This file owns the *parsing* and *resolution*; integration with the
existing ``build_llm`` cascade lives at
:func:`lyra_cli.llm_factory._maybe_build_custom_provider`.
"""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .config_io import load_settings


_log = logging.getLogger(__name__)


# Schema version that introduced the ``providers`` dict. Older
# configs are migrated transparently when read. We only bump this
# when the meaning of an existing key changes — additive fields
# (new optional keys) keep the version stable.
LYRA_PROVIDERS_CONFIG_VERSION = 2


class CustomProviderError(RuntimeError):
    """Raised when a registered provider import string can't be resolved."""


@dataclass(frozen=True)
class CustomProviderEntry:
    """Parsed view of one ``providers`` mapping entry.

    Attributes:
        slug: User-chosen name (the value of ``--llm``).
        import_string: ``"package.module:Symbol"`` reference.
        module: ``package.module`` portion (the half before ``:``).
        symbol: ``Symbol`` portion (the half after ``:``).
    """

    slug: str
    import_string: str
    module: str
    symbol: str

    @classmethod
    def parse(cls, slug: str, import_string: str) -> "CustomProviderEntry":
        slug = (slug or "").strip()
        if not slug:
            raise CustomProviderError("provider slug must be a non-empty string")
        ref = (import_string or "").strip()
        if ":" not in ref:
            raise CustomProviderError(
                f"provider {slug!r}: import string {ref!r} must be of the form "
                "`package.module:Symbol`"
            )
        module, _, symbol = ref.partition(":")
        if not module or not symbol:
            raise CustomProviderError(
                f"provider {slug!r}: import string {ref!r} is missing module or symbol"
            )
        return cls(slug=slug, import_string=ref, module=module, symbol=symbol)


def parse_providers(settings: Mapping[str, Any]) -> list[CustomProviderEntry]:
    """Walk ``settings['providers']`` into a list of typed entries.

    Returns an empty list when no providers are declared, when the
    field is missing, or when the field isn't a dict (so a
    misformatted config doesn't crash the cascade — we log a warning
    instead).
    """
    raw = settings.get("providers")
    if raw is None:
        return []
    if not isinstance(raw, Mapping):
        _log.warning(
            "settings.providers must be an object; ignoring (got %s)",
            type(raw).__name__,
        )
        return []
    out: list[CustomProviderEntry] = []
    for slug, ref in raw.items():
        if not isinstance(ref, str):
            _log.warning(
                "provider %r: import string must be a string; skipping (got %s)",
                slug, type(ref).__name__,
            )
            continue
        try:
            out.append(CustomProviderEntry.parse(slug, ref))
        except CustomProviderError as exc:
            _log.warning("provider registry: %s", exc)
    return out


def resolve_entry(entry: CustomProviderEntry) -> Any:
    """Import the symbol referenced by *entry* and return it.

    Raises:
        CustomProviderError: when the module fails to import or the
            symbol is missing — wrapping the underlying error so
            callers can render a single, actionable message.
    """
    try:
        module = importlib.import_module(entry.module)
    except Exception as exc:
        raise CustomProviderError(
            f"provider {entry.slug!r}: failed to import {entry.module!r} ({exc})"
        ) from exc
    if not hasattr(module, entry.symbol):
        raise CustomProviderError(
            f"provider {entry.slug!r}: module {entry.module!r} has no attribute "
            f"{entry.symbol!r}"
        )
    return getattr(module, entry.symbol)


def build_provider(entry: CustomProviderEntry, **kwargs: Any) -> Any:
    """Instantiate / call the resolved symbol.

    The contract is intentionally permissive — both classes and
    plain factory functions are valid. The only requirement on the
    returned object is that it match :class:`LLMProvider` (a
    ``generate(messages)`` method); we don't enforce that here so
    callers can decide how strict to be.
    """
    target = resolve_entry(entry)
    if not callable(target):
        raise CustomProviderError(
            f"provider {entry.slug!r}: resolved symbol {entry.symbol!r} is not callable"
        )
    try:
        return target(**kwargs)
    except TypeError as exc:
        # Re-raise with a clearer message — the most common cause is
        # passing kwargs the factory doesn't accept.
        raise CustomProviderError(
            f"provider {entry.slug!r}: factory raised TypeError ({exc})"
        ) from exc


def load_registered_providers(settings_path: Path | str | None = None) -> dict[str, CustomProviderEntry]:
    """Read ``settings.json`` and return a slug → entry mapping.

    Used by :func:`build_llm` to discover whether a ``--llm <slug>``
    matches a registered custom provider. Cheap and side-effect-free.
    """
    if settings_path is None:
        # Default to the same path :mod:`config_io` uses.
        import os

        home = os.environ.get("LYRA_HOME")
        base = Path(home) if home else Path.home() / ".lyra"
        settings_path = base / "settings.json"
    settings = load_settings(settings_path)
    return {e.slug: e for e in parse_providers(settings)}


def known_custom_slugs(settings_path: Path | str | None = None) -> list[str]:
    """Return every registered slug — used by ``known_llm_names`` and CLI help."""
    return sorted(load_registered_providers(settings_path).keys())


__all__ = [
    "CustomProviderEntry",
    "CustomProviderError",
    "LYRA_PROVIDERS_CONFIG_VERSION",
    "build_provider",
    "known_custom_slugs",
    "load_registered_providers",
    "parse_providers",
    "resolve_entry",
]
