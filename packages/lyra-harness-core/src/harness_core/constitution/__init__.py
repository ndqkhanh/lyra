"""harness_core.constitution — per-user 3-principle constitution.

Per [docs/206-collaborative-ai-canon-2026.md](../../../../../../research/harness-engineering/docs/206-collaborative-ai-canon-2026.md) §5,
ICAI (arXiv:2406.06560), C3AI (arXiv:2502.15861, ACM Web 2025).

A user's personal constitution is the cleanest serialisable form of "what
working with you should feel like" — far smaller than a full preference
dataset, far more interpretable than a reward model. Per-project apply plans:
[203] Polaris Tier-2, [208] Lyra Tier-2, [218] Atlas Tier-2, [219] Helix
Tier-2, [220] Orion Tier-2, [221] Aegis Tier-1 (per-operator), [210] Mentat
Tier-1.

Three core operations:
    - :meth:`Constitution.render` — produce system-prompt-ready text.
    - :meth:`Constitution.with_principle` — immutable update.
    - :meth:`ConstitutionRegistry.update_for_edit` — drift signal from
      PRELUDE/CIPHER (NeurIPS 2024) edit-as-preference pattern.
"""
from __future__ import annotations

from .constitution import (
    Constitution,
    ConstitutionRegistry,
    Principle,
    suggest_principle_from_edit,
)

__all__ = [
    "Constitution",
    "ConstitutionRegistry",
    "Principle",
    "suggest_principle_from_edit",
]
