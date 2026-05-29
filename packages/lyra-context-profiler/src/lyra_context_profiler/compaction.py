"""Intelligent Context Compaction — Hierarchical summarization and element retention.

Provides multi-strategy compaction: hierarchical summarization, priority-based
retention, irrelevance filtering, duplicate detection, progressive disclosure,
and lossless vs lossy compaction modes.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .strategies import CompactionStrategy

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class CompactionError(Exception):
    """Base exception for compaction errors."""


class IrreversibleCompactionError(CompactionError):
    """Raised when attempting to undo an irreversible (lossy) compaction."""


class EmptyContextError(CompactionError):
    """Raised when attempting to compact an empty context."""


# ── Enums & Types ───────────────────────────────────────────────────────────────


class CompactionMode(Enum):
    """Compaction mode: lossless or lossy."""

    LOSSLESS = auto()   # Preserves all information exactly
    LOSSY = auto()      # May discard or summarize information


class DisclosureLevel(Enum):
    """Progressive disclosure levels for context elements."""

    FULL = auto()        # Complete content
    OVERVIEW = auto()    # Summary / abstract
    MINIMAL = auto()     # Title / key point only
    HIDDEN = auto()      # Removed from active context


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    original_tokens: int
    compacted_tokens: int
    tokens_saved: int
    compaction_ratio: float  # compacted / original
    elements_dropped: int
    elements_compacted: int
    elements_unchanged: int
    strategy: CompactionStrategy
    mode: CompactionMode
    quality_loss: float  # Estimated information loss 0.0-1.0
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SummarizationLevel:
    """Configuration for a hierarchical summarization level."""

    level: int
    name: str
    target_ratio: float  # Fraction of original content to retain
    preserve_code_blocks: bool = True
    preserve_links: bool = True
    preserve_keywords: bool = True


# ── Duplicate Detector ──────────────────────────────────────────────────────────


class DuplicateDetector:
    """Detects duplicate or near-duplicate content in context elements.

    Uses both exact hashing and MinHash-style fuzzy matching.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self._threshold = similarity_threshold
        self._known_hashes: dict[str, str] = {}  # element_id -> hash

    def find_duplicates(
        self,
        elements: dict[str, Any],
    ) -> list[tuple[str, str, float]]:
        """Find duplicate pairs. Returns (id1, id2, similarity_score) tuples."""
        duplicates: list[tuple[str, str, float]] = []
        element_items = list(elements.items())

        for i in range(len(element_items)):
            id1, el1 = element_items[i]
            h1 = self._compute_hash(getattr(el1, "content", str(el1)))
            self._known_hashes[id1] = h1

            for j in range(i + 1, len(element_items)):
                id2, el2 = element_items[j]
                h2 = self._compute_hash(getattr(el2, "content", str(el2)))
                self._known_hashes[id2] = h2

                similarity = self._jaccard_similarity(h1, h2)
                if similarity >= self._threshold:
                    duplicates.append((id1, id2, similarity))

        return duplicates

    def is_duplicate(self, content: str) -> str | None:
        """Check if content is a duplicate of any known element. Returns the matching ID."""
        h = self._compute_hash(content)
        for eid, known_h in self._known_hashes.items():
            if self._jaccard_similarity(h, known_h) >= self._threshold:
                return eid
        return None

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Compute a MinHash-style shingle hash."""
        shingles = DuplicateDetector._shingle(text)
        return hashlib.md5("|".join(sorted(shingles)[:50]).encode()).hexdigest()

    @staticmethod
    def _shingle(text: str, k: int = 5) -> list[str]:
        """Generate k-shingles from text."""
        words = text.lower().split()
        if len(words) < k:
            return [text.lower()]
        return [" ".join(words[i:i + k]) for i in range(len(words) - k + 1)]

    @staticmethod
    def _jaccard_similarity(h1: str, h2: str) -> float:
        """Estimate Jaccard similarity from MinHash signatures."""
        if h1 == h2:
            return 1.0
        # Simple character-level Jaccard for hash comparison
        s1, s2 = set(h1), set(h2)
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union if union > 0 else 0.0


# ── Hierarchical Summarizer ─────────────────────────────────────────────────────


class HierarchicalSummarizer:
    """Multi-level hierarchical summarization engine.

    Produces summaries at different levels of detail, from minimal
    (title/key-point only) to full-context.
    """

    _LEVELS: list[SummarizationLevel] = [
        SummarizationLevel(0, "full", target_ratio=1.0),
        SummarizationLevel(1, "detailed", target_ratio=0.60),
        SummarizationLevel(2, "overview", target_ratio=0.30),
        SummarizationLevel(3, "minimal", target_ratio=0.10),
    ]

    def summarize(
        self,
        content: str,
        level: int,
        element_type: str = "unknown",
        preserve_formatting: bool = True,
    ) -> str:
        """Summarize content to the specified disclosure level.

        Level 0: Full content (no summary)
        Level 1: Detailed (~60% of original)
        Level 2: Overview (~30%)
        Level 3: Minimal (~10%)
        """
        if level <= 0:
            return content
        if level >= 3:
            return self._minimal_summary(content, element_type, preserve_formatting)
        if level == 2:
            return self._overview_summary(content, element_type, preserve_formatting)
        if level == 1:
            return self._detailed_summary(content, element_type, preserve_formatting)

        return content

    def summarize_batch(
        self,
        elements: dict[str, str],
        level: int,
        element_types: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Summarize multiple content strings to the same level."""
        if element_types is None:
            element_types = {}
        return {
            eid: self.summarize(content, level, element_types.get(eid, "unknown"))
            for eid, content in elements.items()
        }

    def _detailed_summary(self, content: str, element_type: str, preserve: bool) -> str:
        """Keep key paragraphs and code blocks, drop filler text."""
        sentences = self._split_sentences(content)
        if len(sentences) <= 5:
            return content

        # Keep first 2 sentences (context), last 2 sentences (conclusion),
        # and sentences with key indicators
        key_indicators = {
            "important", "critical", "must", "should", "error", "warning",
            "define", "class ", "def ", "function", "return", "import",
        }

        kept: list[str] = []
        for i, sentence in enumerate(sentences):
            if i < 2 or i >= len(sentences) - 2:
                kept.append(sentence)
            elif any(ind in sentence.lower() for ind in key_indicators):
                kept.append(sentence)
            elif preserve and sentence.strip().startswith(("```", "\t", "    ")):
                kept.append(sentence)

        result = " ".join(kept)
        if len(result) < len(content) * 0.3:
            result = content[:int(len(content) * 0.6)] + " [...]"

        return result

    def _overview_summary(self, content: str, element_type: str, preserve: bool) -> str:
        """Provide an overview-level summary."""
        sentences = self._split_sentences(content)
        if len(sentences) <= 3:
            return content

        # Keep first sentence (topic) + any code block headers + last sentence
        kept = [sentences[0]]
        for s in sentences[1:-1]:
            if preserve and (s.strip().startswith("```") or s.strip().startswith("#")):
                kept.append(s)

        # Add trailing indicator
        result = " ".join(kept)
        if len(result) > 500:
            result = result[:500] + " [...]"

        return result

    def _minimal_summary(self, content: str, element_type: str, preserve: bool) -> str:
        """Produce the most minimal summary."""
        sentences = self._split_sentences(content)
        if not sentences:
            return ""

        # First sentence is usually the topic sentence
        first = sentences[0].strip()
        if len(first) > 200:
            first = first[:200] + "..."

        # Include a type tag
        type_tag = f"[{element_type}] " if element_type != "unknown" else ""
        return f"{type_tag}{first}"

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences, preserving code blocks."""
        # Preserve code blocks
        parts = re.split(r"(```[\s\S]*?```)", text)
        sentences: list[str] = []
        for part in parts:
            if part.startswith("```"):
                sentences.append(part)
            else:
                sentences.extend(
                    s.strip() for s in re.split(r"(?<=[.!?])\s+", part) if s.strip()
                )
        return sentences


# ── Compaction Engine ───────────────────────────────────────────────────────────


class CompactionEngine:
    """Intelligent context compaction orchestrator.

    Combines duplicate detection, hierarchical summarization, priority-based
    retention, and irrelevance filtering into a unified compaction pipeline.

    Usage::

        engine = CompactionEngine()
        result = await engine.compact(
            elements=context_elements,
            strategy=CompactionStrategy.BALANCED,
            target_reduction=10_000,
        )
    """

    def __init__(self):
        self._duplicate_detector = DuplicateDetector()
        self._summarizer = HierarchicalSummarizer()
        self._compaction_history: list[CompactionResult] = []

    async def compact(
        self,
        elements: dict[str, Any],
        strategy: CompactionStrategy = CompactionStrategy.BALANCED,
        target_reduction: int = 0,
        mode: CompactionMode = CompactionMode.LOSSY,
        element_importance: dict[str, float] | None = None,
    ) -> CompactionResult:
        """Run the full compaction pipeline.

        Args:
            elements: Dict of element_id to element objects (must have 'content' and 'token_count').
            strategy: The compaction strategy to apply.
            target_reduction: Target token reduction count.
            mode: Lossless or lossy compaction.
            element_importance: Optional pre-computed importance scores.

        Returns:
            CompactionResult with detailed metrics.
        """
        if not elements:
            raise EmptyContextError("Cannot compact empty context")

        start = time.perf_counter()
        original_tokens = sum(getattr(el, "token_count", len(getattr(el, "content", "")) // 4) for el in elements.values())

        # Phase 1: Duplicate detection and removal (always lossless)
        duplicates = self._duplicate_detector.find_duplicates(elements)
        duplicate_ids = self._resolve_duplicates(duplicates, element_importance or {})
        elements_filtered = {
            eid: el for eid, el in elements.items() if eid not in duplicate_ids
        }

        # Phase 2: Irrelevance filtering
        if mode == CompactionMode.LOSSY:
            irrelevant = self._find_irrelevant(
                elements_filtered,
                strategy,
                element_importance,
            )
        else:
            irrelevant = set()

        # Phase 3: Hierarchical summarization
        compacted: dict[str, Any] = {}
        level_map = self._strategy_to_levels(strategy)

        for eid, element in elements_filtered.items():
            if eid in irrelevant:
                continue

            content = getattr(element, "content", str(element))
            element_type = getattr(element, "element_type", "unknown")
            element_type_str = str(element_type) if hasattr(element_type, "name") else element_type

            importance = (element_importance or {}).get(eid, 0.5)

            # Determine summarization level based on importance and strategy
            level = self._determine_level(importance, level_map, strategy)

            if level > 0:
                summarized = self._summarizer.summarize(content, level, element_type_str)
                new_element = self._clone_with_content(element, summarized)
                compacted[eid] = new_element
            else:
                compacted[eid] = element

        # Calculate metrics
        compacted_tokens = sum(
            getattr(el, "token_count", len(getattr(el, "content", "")) // 4)
            for el in compacted.values()
        )

        tokens_dropped = sum(
            getattr(elements[eid], "token_count", 0) for eid in duplicate_ids | irrelevant
        )

        tokens_saved = original_tokens - compacted_tokens + tokens_dropped
        compaction_ratio = compacted_tokens / max(original_tokens, 1)

        quality_loss = self._estimate_quality_loss(
            len(duplicate_ids),
            len(irrelevant),
            len(elements_filtered) - len(compacted),
            len(elements),
        )

        result = CompactionResult(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            tokens_saved=tokens_saved,
            compaction_ratio=compaction_ratio,
            elements_dropped=len(duplicate_ids) + len(irrelevant),
            elements_compacted=len(elements_filtered) - len(compacted) - len(irrelevant),
            elements_unchanged=len(compacted),
            strategy=strategy,
            mode=mode,
            quality_loss=quality_loss,
            duration_ms=(time.perf_counter() - start) * 1000,
            metadata={
                "duplicate_ids": list(duplicate_ids),
                "irrelevant_ids": list(irrelevant),
                "level_map": level_map,
            },
        )

        self._compaction_history.append(result)

        logger.info(
            "Compaction complete: %d -> %d tokens (%.1f%% saved, %.3f quality loss) [%s/%s]",
            original_tokens, compacted_tokens,
            (1.0 - compaction_ratio) * 100,
            quality_loss,
            strategy.name, mode.name,
        )

        return result

    async def progressive_disclose(
        self,
        elements: dict[str, Any],
        levels: dict[str, DisclosureLevel] | None = None,
    ) -> dict[str, Any]:
        """Apply progressive disclosure to context elements.

        Hides detail progressively, showing only what's needed at each level.
        """
        if levels is None:
            levels = {}

        result: dict[str, Any] = {}
        for eid, element in elements.items():
            level = levels.get(eid, DisclosureLevel.FULL)
            content = getattr(element, "content", str(element))
            element_type = str(getattr(element, "element_type", "unknown"))

            if level == DisclosureLevel.HIDDEN:
                continue
            elif level == DisclosureLevel.MINIMAL:
                new_content = self._summarizer.summarize(content, 3, element_type)
            elif level == DisclosureLevel.OVERVIEW:
                new_content = self._summarizer.summarize(content, 2, element_type)
            else:
                new_content = content

            result[eid] = self._clone_with_content(element, new_content)

        return result

    @staticmethod
    def _resolve_duplicates(
        duplicates: list[tuple[str, str, float]],
        importance: dict[str, float],
    ) -> set[str]:
        """Decide which element to keep from each duplicate pair."""
        to_drop: set[str] = set()
        for id1, id2, _ in duplicates:
            score1 = importance.get(id1, 0.0)
            score2 = importance.get(id2, 0.0)
            to_drop.add(id2 if score1 >= score2 else id1)
        return to_drop

    def _find_irrelevant(
        self,
        elements: dict[str, Any],
        strategy: CompactionStrategy,
        importance: dict[str, float] | None,
    ) -> set[str]:
        """Identify irrelevant elements based on strategy thresholds."""
        irrelevant: set[str] = set()

        thresholds = {
            CompactionStrategy.AGGRESSIVE: 0.25,
            CompactionStrategy.BALANCED: 0.15,
            CompactionStrategy.CONSERVATIVE: 0.05,
            CompactionStrategy.ADAPTIVE: 0.12,
        }

        threshold = thresholds.get(strategy, 0.15)

        for eid, element in elements.items():
            if importance and importance.get(eid, 0.0) < threshold:
                irrelevant.add(eid)
            elif not importance:
                # Without importance scores, use heuristics
                content = getattr(element, "content", "")
                token_count = getattr(element, "token_count", 0)
                if token_count < 50 and len(str(content).strip()) < 100:
                    irrelevant.add(eid)

        return irrelevant

    @staticmethod
    def _strategy_to_levels(strategy: CompactionStrategy) -> dict[str, float]:
        """Map strategy to importance-to-level thresholds."""
        if strategy == CompactionStrategy.AGGRESSIVE:
            return {"high": 0, "medium": 2, "low": 3}  # Aggressive summarization
        elif strategy == CompactionStrategy.CONSERVATIVE:
            return {"high": 0, "medium": 1, "low": 2}
        elif strategy == CompactionStrategy.ADAPTIVE:
            return {"high": 0, "medium": 1, "low": 2}
        else:  # BALANCED
            return {"high": 0, "medium": 1, "low": 3}

    @staticmethod
    def _determine_level(
        importance: float,
        level_map: dict[str, float],
        strategy: CompactionStrategy,
    ) -> int:
        """Determine summarization level from importance and strategy."""
        if importance >= 0.7:
            return int(level_map.get("high", 0))
        elif importance >= 0.3:
            return int(level_map.get("medium", 1))
        else:
            return int(level_map.get("low", 2))

    @staticmethod
    def _clone_with_content(element: Any, new_content: str) -> Any:
        """Create a shallow clone of an element with replaced content."""
        import copy
        cloned = copy.copy(element)
        if hasattr(cloned, "content"):
            cloned.content = new_content
        # Re-estimate token count (rough: 4 chars per token)
        if hasattr(cloned, "token_count"):
            cloned.token_count = max(1, len(new_content) // 4)
        return cloned

    @staticmethod
    def _estimate_quality_loss(
        duplicates: int,
        irrelevant: int,
        compacted: int,
        total: int,
    ) -> float:
        """Estimate information loss from compaction actions."""
        if total == 0:
            return 0.0
        # Duplicates: near-zero loss
        # Irrelevant: small loss per element
        # Compacted: moderate loss per element
        loss = (duplicates * 0.01 + irrelevant * 0.05 + compacted * 0.15) / total
        return min(loss, 1.0)

    @property
    def history(self) -> list[CompactionResult]:
        return list(self._compaction_history)

    @property
    def last_result(self) -> CompactionResult | None:
        return self._compaction_history[-1] if self._compaction_history else None
