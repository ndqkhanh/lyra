"""Backward-compatible env-var lookups for the Lyra rename (v3.5+).

This module is intentionally lyra-legacy-aware: it owns the deprecation
shim from old HARNESS_* / OPEN_HARNESS_* environment variables to the
new LYRA_* names, and therefore must mention the legacy tokens by name.
The brand-identity guardrail in ``test_brand_identity.py`` honors the
``lyra-legacy-aware`` marker above so this file is allowed.

History
-------
Lyra was previously named **open-coding** (v1.6) and then **open-harness**
(v1.7). Many environment variables still carry those legacy prefixes:

- ``HARNESS_LLM_MODEL`` (the canonical model selector read by `build_llm`)
- ``HARNESS_REASONING_EFFORT``, ``HARNESS_MAX_OUTPUT_TOKENS``
- ``OPEN_HARNESS_<PROVIDER>_MODEL`` (per-provider overrides)
- ``OPEN_HARNESS_MODE``, ``OPEN_HARNESS_MODEL`` (status-source defaults)

Deployments and user `~/.zshrc` files in the wild are full of these. We
**do not** rip them out in v3.5 — that would silently break every user
who upgraded. Instead this module provides one canonical lookup helper
that:

1. Reads the new ``LYRA_*`` name first.
2. Falls back to the matching ``HARNESS_*`` / ``OPEN_HARNESS_*`` legacy
   name(s).
3. Emits a one-shot deprecation warning the first time a legacy name
   wins (rate-limited per name to avoid log spam).

New code should import :func:`lookup_env` (or the convenience
:func:`get_lyra_model`) from this module rather than reading
``os.environ`` directly. Existing call sites continue to work — they
just stay on the legacy names until a focused migration PR sweeps them
to the new helper.

Migration path
--------------
- v3.5: this shim ships; new readers prefer ``LYRA_*`` names.
- v3.6: focused PR migrates ~50 legacy reads in `llm_factory.py`,
  `session.py`, `providers/openai_compatible.py` to use this shim.
- v4.0 (≥ 6 months after v3.5): legacy names removed. Users who still
  set them get a hard error pointing to the migration doc.

The deprecation telemetry (which legacy names are still in use) is
exposed via :func:`legacy_hits` so `lyra doctor` can report which env
vars in the user's environment are still on the old names.
"""

from __future__ import annotations

import os
import warnings
from collections import Counter
from collections.abc import Iterable

# Static mapping of new → legacy alternatives, in priority order. The
# first hit wins; later names are tried only if all earlier ones are
# unset or empty. Anchor names that already start with ``LYRA_`` map
# to themselves (no compat lookup needed) so callers can use one helper
# for everything.
_LEGACY_MAP: dict[str, tuple[str, ...]] = {
    "LYRA_LLM_MODEL": ("HARNESS_LLM_MODEL",),
    "LYRA_REASONING_EFFORT": ("HARNESS_REASONING_EFFORT",),
    "LYRA_MAX_OUTPUT_TOKENS": ("HARNESS_MAX_OUTPUT_TOKENS",),
    "LYRA_MODE": ("OPEN_HARNESS_MODE",),
    "LYRA_MODEL": ("OPEN_HARNESS_MODEL", "HARNESS_LLM_MODEL"),
    "LYRA_DEEPSEEK_MODEL": ("OPEN_HARNESS_DEEPSEEK_MODEL", "DEEPSEEK_MODEL"),
    "LYRA_OPENAI_MODEL": ("OPEN_HARNESS_OPENAI_MODEL", "OPENAI_MODEL"),
    "LYRA_OPENAI_REASONING_MODEL": ("OPEN_HARNESS_OPENAI_REASONING_MODEL",),
    "LYRA_XAI_MODEL": ("OPEN_HARNESS_XAI_MODEL", "XAI_MODEL"),
    "LYRA_GROQ_MODEL": ("OPEN_HARNESS_GROQ_MODEL", "GROQ_MODEL"),
    "LYRA_CEREBRAS_MODEL": ("OPEN_HARNESS_CEREBRAS_MODEL", "CEREBRAS_MODEL"),
    "LYRA_MISTRAL_MODEL": ("OPEN_HARNESS_MISTRAL_MODEL", "MISTRAL_MODEL"),
    "LYRA_OPENROUTER_MODEL": ("OPEN_HARNESS_OPENROUTER_MODEL", "OPENROUTER_MODEL"),
    "LYRA_DASHSCOPE_MODEL": ("OPEN_HARNESS_DASHSCOPE_MODEL", "DASHSCOPE_MODEL"),
    "LYRA_QWEN_MODEL": ("OPEN_HARNESS_QWEN_MODEL", "QWEN_MODEL"),
    "LYRA_GEMINI_MODEL": ("OPEN_HARNESS_GEMINI_MODEL", "GEMINI_MODEL"),
    "LYRA_LOCAL_MODEL": ("OPEN_HARNESS_LOCAL_MODEL", "OLLAMA_MODEL"),
    "LYRA_LMSTUDIO_MODEL": ("OPEN_HARNESS_LMSTUDIO_MODEL",),
    "LYRA_VLLM_MODEL": ("OPEN_HARNESS_VLLM_MODEL", "VLLM_MODEL"),
    "LYRA_TGI_MODEL": ("OPEN_HARNESS_TGI_MODEL", "TGI_MODEL"),
    "LYRA_LLAMA_SERVER_MODEL": ("OPEN_HARNESS_LLAMA_SERVER_MODEL",),
    "LYRA_LLAMAFILE_MODEL": ("OPEN_HARNESS_LLAMAFILE_MODEL",),
    "LYRA_MLX_MODEL": ("OPEN_HARNESS_MLX_MODEL", "MLX_MODEL"),
    "LYRA_MLX_BASE_URL": ("OPEN_HARNESS_MLX_BASE_URL",),
}

# Counter of (legacy_name → hits). Used by `lyra doctor --json` to show
# the user which env vars in their environment are still on legacy
# names so they can update their dotfiles before v4.0.
_LEGACY_HITS: Counter[str] = Counter()
_WARNED: set[str] = set()


def lookup_env(canonical: str, default: str = "", *, warn_on_legacy: bool = True) -> str:
    """Return the value of ``canonical``, falling back to its legacy aliases.

    Parameters
    ----------
    canonical
        The new ``LYRA_*`` env-var name. If unknown to the compat map,
        we just read it directly with no fallback (so this helper is a
        safe drop-in for ``os.environ.get``).
    default
        Returned when neither the canonical nor any legacy name is set
        (or all are set to empty strings).
    warn_on_legacy
        Emit a one-shot ``DeprecationWarning`` per legacy name on the
        first hit. Set ``False`` for hot paths that read repeatedly
        (the ``_LEGACY_HITS`` counter still increments).

    Notes
    -----
    Empty-string values are treated as unset, matching the historical
    behaviour of ``os.environ.get(name, default).strip()`` patterns
    scattered across `llm_factory.py`.
    """
    primary = os.environ.get(canonical, "").strip()
    if primary:
        return primary

    for legacy in _LEGACY_MAP.get(canonical, ()):
        value = os.environ.get(legacy, "").strip()
        if value:
            _LEGACY_HITS[legacy] += 1
            if warn_on_legacy and legacy not in _WARNED:
                _WARNED.add(legacy)
                warnings.warn(
                    f"env var {legacy!r} is deprecated; rename to "
                    f"{canonical!r}. Both names are read in v3.5 — "
                    f"only {canonical!r} will be read in v4.0.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            return value

    return default


def get_lyra_model(default: str = "claude-3-5-sonnet-latest") -> str:
    """Convenience for the most-used reader: ``LYRA_LLM_MODEL``."""
    return lookup_env("LYRA_LLM_MODEL", default)


def legacy_hits() -> dict[str, int]:
    """Return a snapshot of which legacy env names have been read.

    Used by ``lyra doctor --json`` (in a future PR) to surface which
    user env vars are still on legacy names. Returns a plain dict so
    consumers can serialise it directly.
    """
    return dict(_LEGACY_HITS)


def reset_compat_state() -> None:
    """Clear the deprecation-warning + hit-counter caches.

    Test-only helper. Production never calls this.
    """
    _LEGACY_HITS.clear()
    _WARNED.clear()


def known_canonical_names() -> Iterable[str]:
    """Iterate every ``LYRA_*`` name this shim knows about."""
    return _LEGACY_MAP.keys()


__all__ = [
    "get_lyra_model",
    "known_canonical_names",
    "legacy_hits",
    "lookup_env",
    "reset_compat_state",
]
