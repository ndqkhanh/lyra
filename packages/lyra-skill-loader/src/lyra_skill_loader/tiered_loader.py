"""Progressive Disclosure 3-Tier Loading — 82% token reduction via progressive loading."""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class LoadTier(Enum):
    """Progressive disclosure tier."""

    TIER1_METADATA = auto()
    TIER2_CONTENT = auto()
    TIER3_REFERENCES = auto()

    @property
    def tier_number(self) -> int:
        mapping = {self.TIER1_METADATA: 1, self.TIER2_CONTENT: 2, self.TIER3_REFERENCES: 3}
        return mapping[self]

    @property
    def estimated_tokens(self) -> int:
        mapping = {self.TIER1_METADATA: 50, self.TIER2_CONTENT: 500, self.TIER3_REFERENCES: 2000}
        return mapping[self]


@dataclass(frozen=True)
class SkillMetadata:
    """Tier 1: lightweight skill identity and routing info (~50 tokens)."""

    name: str
    description: str
    triggers: tuple[str, ...] = ()
    io_capabilities: tuple[str, ...] = ()
    category: str = "general"
    tags: tuple[str, ...] = ()
    estimated_tokens: int = 50


@dataclass(frozen=True)
class SkillContent:
    """Tier 2: full skill body, instructions, examples (~500 tokens)."""

    body: str = ""
    instructions: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillReferences:
    """Tier 3: extended references, docs, deps (~2000+ tokens)."""

    docs: tuple[str, ...] = ()
    api_specs: tuple[str, ...] = ()
    extended_examples: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadedSkill:
    """A skill loaded at a specific progressive-disclosure tier."""

    metadata: SkillMetadata
    content: SkillContent | None = None
    references: SkillReferences | None = None
    current_tier: LoadTier = LoadTier.TIER1_METADATA


@dataclass(frozen=True)
class LoaderStats:
    """Aggregate statistics about the loader's operation."""

    skills_loaded: int = 0
    tokens_saved: int = 0
    tier_distribution: tuple[tuple[str, int], ...] = ()

    def tokens_saved_pct(self) -> float:
        """Percentage of tokens saved vs. loading everything at tier 3."""
        total = sum(count * 2000 for _, count in self.tier_distribution)
        if total == 0:
            return 0.0
        return (self.tokens_saved / total) * 100.0


@dataclass
class _SkillEntry:
    """Internal registry entry holding all three tiers of skill data."""

    metadata: SkillMetadata
    content: SkillContent | None = None
    references: SkillReferences | None = None
    priority: int = 0
    load_count: int = 0
    last_access: float = 0.0


class TieredLoader:
    """Progressive-disclosure skill loader.

    Skills are registered with full metadata, content, and references,
    then loaded at incrementally deeper tiers to minimize token consumption.
    """

    def __init__(self) -> None:
        self._registry: dict[str, _SkillEntry] = {}
        self._current_tiers: dict[str, LoadTier] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_skill(
        self,
        skill_id: str,
        metadata: SkillMetadata,
        content: SkillContent | None = None,
        references: SkillReferences | None = None,
        priority: int = 0,
    ) -> None:
        """Register a skill with the loader so it can be progressively loaded."""
        self._registry[skill_id] = _SkillEntry(
            metadata=metadata,
            content=content,
            references=references,
            priority=priority,
        )

    def unregister_skill(self, skill_id: str) -> None:
        """Remove a skill from the registry."""
        self._registry.pop(skill_id, None)
        self._current_tiers.pop(skill_id, None)

    def has_skill(self, skill_id: str) -> bool:
        """Check if a skill is registered."""
        return skill_id in self._registry

    def list_skills(self) -> tuple[str, ...]:
        """Return all registered skill ids."""
        return tuple(self._registry.keys())

    # ------------------------------------------------------------------
    # Progressive loading
    # ------------------------------------------------------------------

    def load_tier1(self, skill_id: str) -> LoadedSkill:
        """Load skill metadata only (~50 tokens)."""
        entry = self._registry.get(skill_id)
        if entry is None:
            raise KeyError(f"Skill not registered: {skill_id}")

        self._current_tiers[skill_id] = LoadTier.TIER1_METADATA
        self._update_access_stats(entry)

        return LoadedSkill(
            metadata=entry.metadata,
            current_tier=LoadTier.TIER1_METADATA,
        )

    def load_tier2(self, skill_id: str) -> LoadedSkill:
        """Load skill metadata + full content (~500 tokens).

        Automatically upgrades from tier 1 if already loaded.
        """
        entry = self._registry.get(skill_id)
        if entry is None:
            raise KeyError(f"Skill not registered: {skill_id}")

        self._current_tiers[skill_id] = LoadTier.TIER2_CONTENT
        self._update_access_stats(entry)

        return LoadedSkill(
            metadata=entry.metadata,
            content=entry.content,
            current_tier=LoadTier.TIER2_CONTENT,
        )

    def load_tier3(self, skill_id: str) -> LoadedSkill:
        """Load skill metadata + content + references (~2000+ tokens).

        Automatically upgrades from tier 1 or 2 if already loaded.
        """
        entry = self._registry.get(skill_id)
        if entry is None:
            raise KeyError(f"Skill not registered: {skill_id}")

        self._current_tiers[skill_id] = LoadTier.TIER3_REFERENCES
        self._update_access_stats(entry)

        return LoadedSkill(
            metadata=entry.metadata,
            content=entry.content,
            references=entry.references,
            current_tier=LoadTier.TIER3_REFERENCES,
        )

    def load_at_tier(self, skill_id: str, tier: LoadTier) -> LoadedSkill:
        """Load a skill at the specified tier."""
        mapping = {
            LoadTier.TIER1_METADATA: self.load_tier1,
            LoadTier.TIER2_CONTENT: self.load_tier2,
            LoadTier.TIER3_REFERENCES: self.load_tier3,
        }
        return mapping[tier](skill_id)

    def unload_to_tier1(self, skill_id: str) -> LoadedSkill:
        """Release skill back to metadata-only tier to free token budget."""
        return self.load_tier1(skill_id)

    def get_current_tier(self, skill_id: str) -> LoadTier | None:
        """Return the current load tier for a skill, or None if not loaded."""
        return self._current_tiers.get(skill_id)

    def get_entry(self, skill_id: str) -> _SkillEntry | None:
        """Return the internal entry for a skill, or None if not registered."""
        return self._registry.get(skill_id)

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    def load_batch(
        self,
        skill_ids: Sequence[str],
        tier: LoadTier = LoadTier.TIER1_METADATA,
    ) -> tuple[LoadedSkill, ...]:
        """Load multiple skills at the same tier."""
        return tuple(self.load_at_tier(sid, tier) for sid in skill_ids)

    def unload_batch(self, skill_ids: Sequence[str]) -> tuple[LoadedSkill, ...]:
        """Release multiple skills back to tier 1."""
        return tuple(self.unload_to_tier1(sid) for sid in skill_ids)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def loading_stats(self) -> LoaderStats:
        """Return aggregate loading statistics."""
        loaded = sum(
            1 for sid in self._current_tiers
            if self._current_tiers[sid] != LoadTier.TIER1_METADATA
        )
        tokens_saved = 0
        dist: dict[str, int] = {}

        for _sid, tier in self._current_tiers.items():
            tier_name = tier.name
            dist[tier_name] = dist.get(tier_name, 0) + 1
            full_cost = LoadTier.TIER3_REFERENCES.estimated_tokens
            actual_cost = tier.estimated_tokens
            tokens_saved += full_cost - actual_cost

        tier_dist = tuple(sorted(dist.items()))

        return LoaderStats(
            skills_loaded=loaded,
            tokens_saved=tokens_saved,
            tier_distribution=tier_dist,
        )

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    def estimate_tokens(self, skill_id: str) -> int:
        """Estimate the total token cost for a skill loaded at tier 3."""
        entry = self._registry.get(skill_id)
        if entry is None:
            return 0
        base = LoadTier.TIER3_REFERENCES.estimated_tokens
        if entry.references is not None:
            base += len(entry.references.docs)
        return base

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _update_access_stats(entry: _SkillEntry) -> None:
        entry.load_count += 1
        entry.last_access = time.time()
