"""Adaptive compression promotion — Phase L of the Lyra skill-curation plan.

Implements the "missing diagonal" from the compression spectrum:
  trace → episodic → skill → rule

Each level discards runtime-specific detail while retaining reusable structure.
Promotion is triggered by cross-context generalization evidence.
The "missing diagonal" is the direct promotion path (trace → rule) that activates
when generalization score is sufficiently high, skipping intermediate levels.

Grounded in:
- arXiv:2604.15877 — Adaptive Compression Promotion
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


__all__ = [
    "CompressionLevel",
    "CompressedArtifact",
    "CompressionConfig",
    "CompressionPromoter",
]


class CompressionLevel(IntEnum):
    """Ascending compression spectrum: higher = more abstract, less runtime detail."""

    TRACE = 0       # raw execution trace — every step, every tool call
    EPISODIC = 1    # episode summary — goals, key events, outcomes
    SKILL = 2       # reusable skill — abstract procedure, triggers, tools
    RULE = 3        # compact rule — transferable principle across domains


@dataclass
class CompressedArtifact:
    """An artifact at a specific compression level."""

    artifact_id: str
    source_id: str              # original trace/episode/skill ID
    level: CompressionLevel
    content: str
    context_tags: list[str] = field(default_factory=list)
    generalization_score: float = 0.0   # [0, 1]; high value triggers diagonal promotion


@dataclass(frozen=True)
class CompressionConfig:
    """Thresholds governing compression promotion."""

    episodic_min_contexts: int = 2       # contexts needed TRACE → EPISODIC
    skill_min_contexts: int = 3          # contexts needed EPISODIC → SKILL
    rule_min_contexts: int = 5           # contexts needed SKILL → RULE
    diagonal_threshold: float = 0.90    # generalization score for diagonal jump
    min_content_length: int = 10        # stub content is not promoted


class CompressionPromoter:
    """Manages promotion of artifacts through the compression spectrum.

    Normal promotion: TRACE → EPISODIC → SKILL → RULE (one level at a time).
    Diagonal promotion: jumps directly to RULE when generalization_score ≥
    diagonal_threshold and context count ≥ rule_min_contexts — the "missing
    diagonal" from arXiv:2604.15877.

    Usage::

        promoter = CompressionPromoter()
        a = CompressedArtifact("t1", "trace-abc", CompressionLevel.TRACE, "...content...")
        promoter.register(a)
        promoter.add_context("t1", "web")
        promoter.add_context("t1", "cli")
        new_level = promoter.promote("t1")   # → EPISODIC (2 contexts)
    """

    def __init__(self, config: Optional[CompressionConfig] = None) -> None:
        self._config = config or CompressionConfig()
        self._artifacts: dict[str, CompressedArtifact] = {}
        self._promoted: list[tuple[str, CompressionLevel, CompressionLevel]] = []

    def register(self, artifact: CompressedArtifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact

    def add_context(self, artifact_id: str, context_tag: str) -> None:
        """Record a new context in which the artifact succeeded; update generalization score."""
        a = self._artifacts[artifact_id]
        if context_tag not in a.context_tags:
            a.context_tags.append(context_tag)
            cfg = self._config
            a.generalization_score = min(
                1.0, len(a.context_tags) / cfg.rule_min_contexts
            )

    def _target_level(self, artifact: CompressedArtifact) -> Optional[CompressionLevel]:
        cfg = self._config
        current = artifact.level
        n = len(artifact.context_tags)
        score = artifact.generalization_score

        if current == CompressionLevel.RULE:
            return None

        # Diagonal promotion: skip directly to RULE when evidence is strong
        if score >= cfg.diagonal_threshold and n >= cfg.rule_min_contexts:
            return CompressionLevel.RULE

        # Incremental promotion
        if current == CompressionLevel.TRACE and n >= cfg.episodic_min_contexts:
            return CompressionLevel.EPISODIC
        if current == CompressionLevel.EPISODIC and n >= cfg.skill_min_contexts:
            return CompressionLevel.SKILL
        if current == CompressionLevel.SKILL and n >= cfg.rule_min_contexts:
            return CompressionLevel.RULE

        return None

    def promote(self, artifact_id: str) -> Optional[CompressionLevel]:
        """Attempt to promote one artifact; return new level or None if not ready."""
        artifact = self._artifacts[artifact_id]
        if len(artifact.content) < self._config.min_content_length:
            return None

        target = self._target_level(artifact)
        if target is None or target <= artifact.level:
            return None

        prev = artifact.level
        artifact.level = target
        self._promoted.append((artifact_id, prev, target))
        return target

    def promote_all(self) -> list[tuple[str, CompressionLevel, CompressionLevel]]:
        """Attempt promotion for all artifacts; return list of (id, from, to) tuples."""
        results = []
        for aid in list(self._artifacts):
            prev = self._artifacts[aid].level
            new_level = self.promote(aid)
            if new_level is not None:
                results.append((aid, prev, new_level))
        return results

    @property
    def promotion_log(self) -> list[tuple[str, CompressionLevel, CompressionLevel]]:
        return list(self._promoted)

    def artifact(self, artifact_id: str) -> Optional[CompressedArtifact]:
        return self._artifacts.get(artifact_id)

    def artifacts_at_level(self, level: CompressionLevel) -> list[CompressedArtifact]:
        return [a for a in self._artifacts.values() if a.level == level]
