"""harness_core.skill_auto — Voyager-line skill self-evolution from trajectories.

Per [docs/167-autoskill-experience-driven-lifelong-learning.md](../../../../../../research/harness-engineering/docs/167-autoskill-experience-driven-lifelong-learning.md),
[docs/168-evoskill-coding-agent-skill-discovery.md](../../../../../../research/harness-engineering/docs/168-evoskill-coding-agent-skill-discovery.md),
[docs/169-coevoskills-co-evolutionary-verification.md](../../../../../../research/harness-engineering/docs/169-coevoskills-co-evolutionary-verification.md),
[docs/170-skillrl-recursive-skill-augmented-rl.md](../../../../../../research/harness-engineering/docs/170-skillrl-recursive-skill-augmented-rl.md),
[docs/171-skill-self-evolution-2026-synthesis.md](../../../../../../research/harness-engineering/docs/171-skill-self-evolution-2026-synthesis.md),
[docs/197-argus-omega-vol-3-recursive-skills-curator.md](../../../../../../research/harness-engineering/docs/197-argus-omega-vol-3-recursive-skills-curator.md).

Three-step pipeline:

    1. **Extract** — scan a trajectory corpus, detect repeating successful
       action templates, emit :class:`SkillCandidate`s.
    2. **Verify** — run a *surrogate verifier* (info-isolated; the [169]
       co-evolutionary pattern that gives +30pp ablation lift) to check the
       candidate generalises beyond the source trajectories.
    3. **Promote** — gate by held-out eval score; emit a
       :class:`harness_core.marketplace.PromotedSkill` and record the
       promotion as a :class:`harness_core.provenance.Witness`.

Composes with:
    - :mod:`harness_core.forensic` — trajectory corpus.
    - :mod:`harness_core.verifier` — surrogate verifier as a one-axis composer.
    - :mod:`harness_core.provenance` — promotion witnesses cite source trajectories.
    - :mod:`harness_core.marketplace` — final ``PromotedSkill`` flows into argus.

Used by Mentat-Learn ([docs/210] Tier-0), Lyra V3.9 ([docs/208] Tier-1),
Polaris auto_creator ([docs/172] §2), Argus curator ([docs/197]).
"""
from __future__ import annotations

from .extractor import SkillExtractor
from .promoter import SkillPromoter
from .types import PromotionVerdict, SkillCandidate

__all__ = [
    "PromotionVerdict",
    "SkillCandidate",
    "SkillExtractor",
    "SkillPromoter",
]
