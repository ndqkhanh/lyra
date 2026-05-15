"""Adapter between Lyra's :class:`SkillManifest` and Argus's :class:`Skill`.

Lyra ships a description-overlap router (``lyra_skills.router.SkillRouter``)
that operates directly on :class:`SkillManifest`. The Argus integration
phase (V3.8 Theme A) wraps that primitive with Argus's five-tier router
cascade, governance ledgers, and refinement loop. The bridge in this
module is the bidirectional translator the wrapper depends on.

The mapping follows the agentskills.io convention Argus already targets,
with Lyra-specific fields tucked into :attr:`Skill.extra` so they survive
round-trips:

============================  =========================================
Lyra ``SkillManifest``         Argus ``Skill``
============================  =========================================
``id``                         ``name``
``name``                       ``extra["display_name"]``
``description``                ``description``
``body``                       ``body``
``keywords`` (list)            ``when_to_use`` (newline-joined)
``applies_to``                 ``paths``
``requires``                   ``extra["requires"]``
``progressive``                ``extra["progressive"]``
``version``                    ``extra["version"]``
``path``                       ``source_url``
``extras`` (free-form dict)    merged into ``extra``
============================  =========================================

The reverse direction (``argus_skill_to_manifest``) is provided for
symmetry — useful when Argus marketplace adapters introduce new skills
that the rest of Lyra still wants to see as :class:`SkillManifest`.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from harness_skill_router import Skill, SkillSource, TrustTier
from harness_skill_router.catalog import default_tier_for_source

from .loader import SkillManifest


_LYRA_RESERVED_KEYS = frozenset({
    "display_name",
    "version",
    "requires",
    "progressive",
    "lyra_keywords",
})


def manifest_to_argus_skill(
    manifest: SkillManifest,
    *,
    source: SkillSource = SkillSource.LOCAL_AUTHORED,
    trust_tier: TrustTier | None = None,
) -> Skill:
    """Project one :class:`SkillManifest` into an Argus :class:`Skill`.

    The default ``source`` is ``LOCAL_AUTHORED`` because Lyra ships its
    skills as repo-checked-in directories — the same provenance Argus
    treats as :class:`TrustTier.T_REVIEWED`. Marketplace fetches should
    pass an explicit ``source`` so the trust-tier defaults match
    Argus's :func:`default_tier_for_source`.
    """
    tier = trust_tier if trust_tier is not None else default_tier_for_source(source)
    when_to_use = "\n".join(k for k in manifest.keywords if k.strip())
    extra: dict[str, Any] = {
        "display_name": manifest.name,
        "version": manifest.version,
        "requires": list(manifest.requires),
        "progressive": manifest.progressive,
        "lyra_keywords": list(manifest.keywords),
    }
    for key, value in manifest.extras.items():
        if key in _LYRA_RESERVED_KEYS:
            continue
        extra[key] = value
    return Skill(
        name=manifest.id,
        description=manifest.description,
        body=manifest.body,
        when_to_use=when_to_use,
        paths=tuple(manifest.applies_to),
        source=source,
        source_url=manifest.path,
        trust_tier=tier,
        extra=extra,
    )


def argus_skill_to_manifest(skill: Skill) -> SkillManifest:
    """Reverse projection — Argus :class:`Skill` → Lyra :class:`SkillManifest`.

    The Lyra-specific fields are restored from ``Skill.extra`` when present.
    """
    extra = dict(skill.extra or {})
    keywords = list(extra.pop("lyra_keywords", None) or [])
    if not keywords and skill.when_to_use:
        keywords = [line for line in skill.when_to_use.splitlines() if line.strip()]
    display_name = str(extra.pop("display_name", skill.name) or skill.name)
    version = str(extra.pop("version", "") or "")
    requires = list(extra.pop("requires", None) or [])
    progressive = bool(extra.pop("progressive", False))
    return SkillManifest(
        id=skill.name,
        name=display_name,
        description=skill.description,
        body=skill.body,
        path=skill.source_url,
        version=version,
        keywords=keywords,
        applies_to=list(skill.paths),
        requires=requires,
        progressive=progressive,
        extras=extra,
    )


def manifests_to_skills(
    manifests: Iterable[SkillManifest],
    *,
    source: SkillSource = SkillSource.LOCAL_AUTHORED,
    trust_tier: TrustTier | None = None,
) -> list[Skill]:
    """Bulk-project a stream of manifests, preserving order."""
    return [
        manifest_to_argus_skill(m, source=source, trust_tier=trust_tier)
        for m in manifests
    ]


__all__ = [
    "argus_skill_to_manifest",
    "manifest_to_argus_skill",
    "manifests_to_skills",
]
