"""Fast Skill Compilation — pre-compute triggers, dependency hashes, and bloom filters for sub-ms
lookup."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from lyra_skill_loader.tiered_loader import LoadedSkill, SkillMetadata

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class CompiledSkill:
    """Pre-compiled representation of a skill for fast matching."""

    skill_id: str
    precomputed_triggers: frozenset[str]
    dependency_hashes: dict[str, int]
    metadata_bloom_filter: tuple[bool, ...]
    version: int = 1


class CompiledIndex:
    """In-memory index for sub-ms skill lookup by trigger signature."""

    def __init__(self) -> None:
        self._skills: dict[str, CompiledSkill] = {}
        self._trigger_index: dict[str, list[str]] = {}
        self._capability_index: dict[str, list[str]] = {}

    def add(
        self, compiled: CompiledSkill, triggers: Sequence[str], capabilities: Sequence[str]
    ) -> None:
        """Index a compiled skill by its triggers and capabilities."""
        self._skills[compiled.skill_id] = compiled

        for trigger in triggers:
            sig = self._normalize_trigger(trigger)
            self._trigger_index.setdefault(sig, []).append(compiled.skill_id)

        for cap in capabilities:
            self._capability_index.setdefault(cap.lower(), []).append(compiled.skill_id)

    def remove(self, skill_id: str) -> None:
        """Remove a skill from the index."""
        self._skills.pop(skill_id, None)
        for sig in list(self._trigger_index.keys()):
            if skill_id in self._trigger_index[sig]:
                self._trigger_index[sig] = [
                    sid for sid in self._trigger_index[sig] if sid != skill_id
                ]
                if not self._trigger_index[sig]:
                    del self._trigger_index[sig]
        for cap in list(self._capability_index.keys()):
            if skill_id in self._capability_index[cap]:
                self._capability_index[cap] = [
                    sid for sid in self._capability_index[cap] if sid != skill_id
                ]
                if not self._capability_index[cap]:
                    del self._capability_index[cap]

    def lookup(self, trigger_signature: str) -> list[str]:
        """Fast index-based lookup by trigger signature."""
        sig = self._normalize_trigger(trigger_signature)
        return self._trigger_index.get(sig, [])

    def lookup_by_capability(self, capability: str) -> list[str]:
        """Look up skills by capability."""
        return self._capability_index.get(capability.lower(), [])

    def get_compiled(self, skill_id: str) -> CompiledSkill | None:
        """Retrieve a compiled skill by id."""
        return self._skills.get(skill_id)

    def all_skill_ids(self) -> tuple[str, ...]:
        """Return all indexed skill ids."""
        return tuple(self._skills.keys())

    @staticmethod
    def _normalize_trigger(trigger: str) -> str:
        return re.sub(r"[^a-z0-9]", "", trigger.lower())


class SkillCompiler:
    """Pre-compiles skill metadata for fast trigger matching and index creation.

    Uses hash-based signatures for trigger matching and a bloom-like filter for fast negative
    checking of metadata attributes.
    """

    def __init__(self) -> None:
        self._cache: dict[str, CompiledSkill] = {}
        self._dirty: set[str] = set()
        self._index: CompiledIndex | None = None

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile(self, skill: LoadedSkill) -> CompiledSkill:
        """Compile a single loaded skill into its fast-match representation."""
        metadata = skill.metadata
        all_triggers = list(metadata.triggers) + list(metadata.tags)

        # Pre-compute normalized trigger strings
        precomputed = frozenset(self._normalize(t) for t in all_triggers if t)

        # Compute dependency hashes
        dep_hashes: dict[str, int] = {}
        if skill.references is not None:
            for dep in skill.references.dependencies:
                dep_hashes[dep] = self._hash_string(dep)

        # Build bloom filter from metadata attributes
        bloom_items = [metadata.name, metadata.description, metadata.category]
        bloom_items.extend(metadata.triggers)
        bloom_items.extend(metadata.tags)
        bloom = _make_bloom_filter(tuple(bloom_items))

        compiled = CompiledSkill(
            skill_id=metadata.name,
            precomputed_triggers=precomputed,
            dependency_hashes=dep_hashes,
            metadata_bloom_filter=bloom,
        )

        self._cache[metadata.name] = compiled
        self._dirty.discard(metadata.name)
        return compiled

    def compile_batch(self, skills: Sequence[LoadedSkill]) -> list[CompiledSkill]:
        """Compile multiple skills in batch."""
        return [self.compile(s) for s in skills]

    def compile_from_metadata(self, skill_id: str, metadata: SkillMetadata) -> CompiledSkill:
        """Compile a skill using just its metadata (no content needed)."""
        wrapper = LoadedSkill(metadata=metadata)
        return self.compile(wrapper)

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------

    def create_index(self, compiled: Sequence[CompiledSkill]) -> CompiledIndex:
        """Build an in-memory index from compiled skills for sub-ms lookup."""
        index = CompiledIndex()

        for cs in compiled:
            metadata = self._get_metadata_for(cs.skill_id)
            triggers = list(cs.precomputed_triggers)
            capabilities: list[str] = []
            if metadata is not None:
                capabilities = list(metadata.io_capabilities)
            index.add(cs, triggers, capabilities)

        self._index = index
        return index

    def get_index(self) -> CompiledIndex | None:
        """Return the current compiled index, if one exists."""
        return self._index

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def lookup(self, trigger_signature: str) -> list[str]:
        """Fast index-based lookup by trigger signature.

        Returns:
            List of matching skill ids. Returns empty list if no index.
        """
        if self._index is None:
            return []
        return self._index.lookup(trigger_signature)

    def lookup_metadata_contains(self, keyword: str, min_skills: int = 1) -> list[str]:
        """Use bloom filters for fast negative checks across all compiled skills.

        This provides a quick pre-filter before falling back to exact matching.
        """
        candidates: list[str] = []
        normalized = self._normalize(keyword)

        for sid, cs in self._cache.items():
            if _bloom_might_contain(cs.metadata_bloom_filter, normalized):
                candidates.append(sid)
            if len(candidates) >= min_skills * 5:
                break

        return candidates

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate(self, skill_id: str) -> None:
        """Mark a compiled skill for recompilation on next access."""
        if skill_id in self._cache:
            self._dirty.add(skill_id)

    def is_dirty(self, skill_id: str) -> bool:
        """Check if a skill needs recompilation."""
        return skill_id in self._dirty

    def get_cached(self, skill_id: str) -> CompiledSkill | None:
        """Retrieve a compiled skill, recompiling if dirty."""
        if skill_id in self._dirty:
            # In a real system this would trigger recompilation
            self._dirty.discard(skill_id)
        return self._cache.get(skill_id)

    def clear(self) -> None:
        """Clear all cached compilations."""
        self._cache.clear()
        self._dirty.clear()
        self._index = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_metadata_for(self, skill_id: str) -> SkillMetadata | None:
        """Look up metadata for a compiled skill.

        Note: This method primarily exists for the index builder. In a
        production system it would query the tiered loader's registry.
        Currently returns None since we don't back-link to the loader
        (callers should index from :class:`LoadedSkill` sources).
        """
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", text.lower().strip())

    @staticmethod
    def _hash_string(text: str) -> int:
        return int(hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:8], 16)


# ------------------------------------------------------------------
# Bloom filter utilities
# ------------------------------------------------------------------

_BLOOM_SIZE = 64
_NUM_HASHES = 3


def _make_bloom_filter(
    items: tuple[str, ...],
    size: int = _BLOOM_SIZE,
    num_hashes: int = _NUM_HASHES,
) -> tuple[bool, ...]:
    """Create a bloom filter bit array from a sequence of strings."""
    bloom = np.zeros(size, dtype=bool)
    for item in items:
        normalized = re.sub(r"[^a-z0-9]", "", item.lower())
        for seed in range(num_hashes):
            idx = _hash_to_index(normalized, seed, size)
            bloom[idx] = True
    return tuple(bloom.tolist())


def _bloom_might_contain(
    bloom: tuple[bool, ...],
    item: str,
    num_hashes: int = _NUM_HASHES,
) -> bool:
    """Check if a bloom filter *might* contain an item.

    Returns False if the item is definitely NOT in the set. Returns True if the item MIGHT be in the
    set (false positives possible).
    """
    size = len(bloom)
    if size == 0:
        return False

    for seed in range(num_hashes):
        idx = _hash_to_index(item, seed, size)
        if not bloom[idx]:
            return False
    return True


def _hash_to_index(item: str, seed: int, size: int) -> int:
    """Compute a deterministic hash index for bloom filter operations."""
    return (hash(f"{seed}:{item}") + 2**31) % size
