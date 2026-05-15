"""Context profile — a single env-readable knob that flips the
context-engine's aggressiveness together.

Three named profiles (steal: ECC's ``ECC_HOOK_PROFILE``):

* ``minimal``  — low-context, hot-path-friendly. Compact early, recall
  little, trim MCP descriptions, no SessionStart preamble.
* ``standard`` — balanced default; mirrors the historical hard-coded
  numbers in the rest of ``lyra_core.context``.
* ``strict``   — generous context budget for high-stakes work; large
  keep-window, longer summaries, broader recall.

Resolution order: explicit ``name`` argument → ``LYRA_CONTEXT_PROFILE``
env var → ``"standard"``. Unknown names raise so a typo can't silently
demote a strict session.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ContextProfile:
    """Frozen knob-set that callers thread through context operations.

    Every field is a coherent slice of the same axis: how aggressively
    the engine reclaims tokens. Higher ``autocompact_pct`` means we
    let the dynamic layer grow further before compacting.
    """

    name: str
    autocompact_pct: float
    keep_last: int
    max_summary_tokens: int
    reduction_cap_kb: int
    mcp_descriptions: str  # "full" | "trimmed" | "off"
    session_start_context_bytes: int  # 0 = off
    reasoning_bank_k: int

    def __post_init__(self) -> None:  # validate at construction
        if not 0.0 < self.autocompact_pct <= 1.0:
            raise ValueError(
                f"autocompact_pct must be in (0, 1], got {self.autocompact_pct}"
            )
        if self.keep_last <= 0:
            raise ValueError(f"keep_last must be > 0, got {self.keep_last}")
        if self.max_summary_tokens <= 0:
            raise ValueError(
                f"max_summary_tokens must be > 0, got {self.max_summary_tokens}"
            )
        if self.reduction_cap_kb <= 0:
            raise ValueError(
                f"reduction_cap_kb must be > 0, got {self.reduction_cap_kb}"
            )
        if self.mcp_descriptions not in {"full", "trimmed", "off"}:
            raise ValueError(
                "mcp_descriptions must be one of full|trimmed|off, "
                f"got {self.mcp_descriptions!r}"
            )
        if self.session_start_context_bytes < 0:
            raise ValueError(
                "session_start_context_bytes must be >= 0, "
                f"got {self.session_start_context_bytes}"
            )
        if self.reasoning_bank_k < 0:
            raise ValueError(
                f"reasoning_bank_k must be >= 0, got {self.reasoning_bank_k}"
            )


MINIMAL = ContextProfile(
    name="minimal",
    autocompact_pct=0.50,
    keep_last=4,
    max_summary_tokens=400,
    reduction_cap_kb=2,
    mcp_descriptions="trimmed",
    session_start_context_bytes=0,
    reasoning_bank_k=2,
)

STANDARD = ContextProfile(
    name="standard",
    autocompact_pct=0.85,
    keep_last=8,
    max_summary_tokens=800,
    reduction_cap_kb=4,
    mcp_descriptions="full",
    session_start_context_bytes=8000,
    reasoning_bank_k=4,
)

STRICT = ContextProfile(
    name="strict",
    autocompact_pct=0.80,
    keep_last=12,
    max_summary_tokens=1200,
    reduction_cap_kb=4,
    mcp_descriptions="full",
    session_start_context_bytes=8000,
    reasoning_bank_k=6,
)

_PROFILES: dict[str, ContextProfile] = {
    p.name: p for p in (MINIMAL, STANDARD, STRICT)
}


def resolve_profile(
    name: str | None = None, *, env: dict[str, str] | None = None
) -> ContextProfile:
    """Pick a :class:`ContextProfile` from explicit name, env, or default.

    Args:
        name: Explicit profile name; takes precedence over env.
        env: Override the env mapping (tests pass an empty dict to
            isolate from the real environment).

    Raises:
        ValueError: If the requested name isn't a registered profile.
    """
    env_map = env if env is not None else os.environ
    chosen = name if name is not None else env_map.get("LYRA_CONTEXT_PROFILE")
    if chosen is None or chosen == "":
        return STANDARD
    key = chosen.strip().lower()
    if key not in _PROFILES:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(
            f"unknown context profile {chosen!r}; expected one of: {known}"
        )
    return _PROFILES[key]


def list_profiles() -> list[ContextProfile]:
    """Return all registered profiles in canonical order."""
    return [MINIMAL, STANDARD, STRICT]


__all__ = [
    "ContextProfile",
    "MINIMAL",
    "STANDARD",
    "STRICT",
    "list_profiles",
    "resolve_profile",
]
