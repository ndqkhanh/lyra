"""Foreign-credential sniffer for missing-credential errors.

Generalises claw-code's ``anthropic_missing_credentials_hint`` across
every provider Lyra supports. The pattern is:

* User runs ``lyra run --llm anthropic``.
* ``ANTHROPIC_API_KEY`` is not set.
* But ``OPENAI_API_KEY`` *is* set.
* Lyra says: "I see OPENAI_API_KEY is set — if you meant the OpenAI
  provider, prefix your model with ``openai/`` or run
  ``lyra run --llm openai``."

This is dramatically better than a generic "missing credentials" wall
because the user's likely mistake is already diagnosed. Most common
case: OpenRouter users who set ``OPENAI_API_KEY=<or-key>`` and forget
the ``openai/`` prefix.

Empty env var values are treated as unset to prevent false positives
when users clear a stale export with ``KEY=``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ForeignCred:
    """Metadata for one provider we might sniff."""

    env_var: str
    provider_key: str
    label: str
    suggested_fix_prefix: str
    suggested_alias_hint: str


KNOWN_FOREIGN_CREDS: Tuple[ForeignCred, ...] = (
    ForeignCred(
        env_var="OPENAI_API_KEY",
        provider_key="openai",
        label="OpenAI",
        suggested_fix_prefix="openai/",
        suggested_alias_hint=(
            "prefix your model with `openai/` (e.g. `--model openai/gpt-4o`) "
            "or run `lyra run --llm openai`. If you're pointing at OpenRouter / "
            "Ollama / a local server, also set `OPENAI_BASE_URL`."
        ),
    ),
    ForeignCred(
        env_var="ANTHROPIC_API_KEY",
        provider_key="anthropic",
        label="Anthropic",
        suggested_fix_prefix="anthropic/",
        suggested_alias_hint=(
            "prefix your model with `anthropic/` (e.g. `--model anthropic/claude-opus-4.5`) "
            "or run `lyra run --llm anthropic`."
        ),
    ),
    ForeignCred(
        env_var="XAI_API_KEY",
        provider_key="xai",
        label="xAI",
        suggested_fix_prefix="grok",
        suggested_alias_hint=(
            "use an xAI alias (e.g. `--model grok` or `--model grok-mini`) "
            "or run `lyra run --llm xai`."
        ),
    ),
    ForeignCred(
        env_var="DEEPSEEK_API_KEY",
        provider_key="deepseek",
        label="DeepSeek",
        suggested_fix_prefix="deepseek/",
        suggested_alias_hint=(
            "prefix your model with `deepseek/` or run `lyra run --llm deepseek`."
        ),
    ),
    ForeignCred(
        env_var="GROQ_API_KEY",
        provider_key="groq",
        label="Groq",
        suggested_fix_prefix="groq/",
        suggested_alias_hint="run `lyra run --llm groq`.",
    ),
    ForeignCred(
        env_var="GEMINI_API_KEY",
        provider_key="gemini",
        label="Gemini",
        suggested_fix_prefix="gemini/",
        suggested_alias_hint=(
            "run `lyra run --llm gemini` (also honours `GOOGLE_API_KEY`)."
        ),
    ),
    ForeignCred(
        env_var="DASHSCOPE_API_KEY",
        provider_key="dashscope",
        label="Alibaba DashScope (Qwen / Kimi)",
        suggested_fix_prefix="qwen-",
        suggested_alias_hint=(
            "prefix your model with `qwen-` or `kimi-` (e.g. `--model qwen-plus` / "
            "`--model kimi-k2.5`) or run `lyra run --llm dashscope`."
        ),
    ),
    ForeignCred(
        env_var="OPENROUTER_API_KEY",
        provider_key="openrouter",
        label="OpenRouter",
        suggested_fix_prefix="openrouter/",
        suggested_alias_hint="run `lyra run --llm openrouter`.",
    ),
)


def _present(env_var: str) -> bool:
    """True iff env var is set AND non-empty (empty string == unset)."""
    v = os.environ.get(env_var, "")
    return bool(v.strip())


def missing_credential_hint(
    *,
    asking: str,
) -> Optional[str]:
    """Produce a fix-hint when the requested provider's creds are absent.

    *asking* is the provider name the user requested (lowercase).
    Returns ``None`` when either (a) no foreign creds are set, or (b) the
    requested provider is unknown. Otherwise returns a one-line hint
    naming the first set foreign cred and how to route to it.

    The "first match wins" rule keeps hints focused; listing three
    foreign creds at once is more confusing than helpful and the most
    common misroute pattern (OpenRouter users setting OPENAI_API_KEY)
    is already covered by the registry order.
    """
    asking_norm = asking.lower().strip()
    if not any(c.provider_key == asking_norm for c in KNOWN_FOREIGN_CREDS):
        return None

    for cred in KNOWN_FOREIGN_CREDS:
        if cred.provider_key == asking_norm:
            continue
        if _present(cred.env_var):
            return (
                f"I see {cred.env_var} is set — if you meant to use the "
                f"{cred.label} provider, {cred.suggested_alias_hint}"
            )
    return None


__all__ = ["ForeignCred", "KNOWN_FOREIGN_CREDS", "missing_credential_hint"]
