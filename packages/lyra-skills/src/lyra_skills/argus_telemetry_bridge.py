"""Mirror Lyra :class:`~lyra_core.skills.registry.SkillRegistry` events into Argus.

Lyra already keeps per-skill ``success_count`` / ``miss_count`` in
:class:`SkillRegistry`. The Argus telemetry ledger consumes
:class:`~harness_skill_router.EventKind.SKILL_EXECUTED` and
:class:`~harness_skill_router.EventKind.SKILL_REJECTED` events to drive
its drift detector, telemetry-aware re-ranker, and observability
surfaces (O1–O6).

:func:`mirror_registry_into_cascade` wraps the registry in-place so
every ``record_success`` / ``record_miss`` call also lands in the Argus
ledger. The wrapping is reversible — keep the returned :class:`Restore`
handle and call it to detach the bridge.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lyra_core.skills.registry import Skill as LyraSkill, SkillRegistry

from .argus_cascade import LyraArgusCascade


Restore = Callable[[], None]


@dataclass
class _Patches:
    original_success: Callable[[str], LyraSkill]
    original_miss: Callable[[str], LyraSkill]


def mirror_registry_into_cascade(
    registry: SkillRegistry,
    cascade: LyraArgusCascade,
) -> Restore:
    """Wrap *registry* so success/miss events also reach Argus's ledger.

    Returns a callable that restores the original methods. Calling the
    callable twice is harmless; the bridge is idempotent.
    """
    if getattr(registry, "_argus_bridge_attached", False):
        return _make_noop_restore()

    patches = _Patches(
        original_success=registry.record_success,
        original_miss=registry.record_miss,
    )

    def record_success(skill_id: str) -> LyraSkill:
        skill = patches.original_success(skill_id)
        cascade.record_outcome(
            skill_id, success=True,
            detail=f"registry.success_count={skill.success_count}",
        )
        return skill

    def record_miss(skill_id: str) -> LyraSkill:
        skill = patches.original_miss(skill_id)
        cascade.record_outcome(
            skill_id, success=False,
            detail=f"registry.miss_count={skill.miss_count}",
        )
        return skill

    registry.record_success = record_success  # type: ignore[method-assign]
    registry.record_miss = record_miss        # type: ignore[method-assign]
    registry._argus_bridge_attached = True    # type: ignore[attr-defined]

    def restore() -> None:
        if not getattr(registry, "_argus_bridge_attached", False):
            return
        registry.record_success = patches.original_success  # type: ignore[method-assign]
        registry.record_miss = patches.original_miss        # type: ignore[method-assign]
        registry._argus_bridge_attached = False             # type: ignore[attr-defined]

    return restore


def _make_noop_restore() -> Restore:
    def _noop() -> None:
        return None

    return _noop


__all__ = [
    "Restore",
    "mirror_registry_into_cascade",
]
