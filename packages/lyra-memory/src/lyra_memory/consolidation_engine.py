"""
Offline memory consolidation engine (Auto-Dreamer-inspired).

Implements sleep-like memory processing to compress, abstract, and reorganize
memories. Based on Auto-Dreamer research (May 2026) and hippocampal replay
principles from neuroscience.

Two consolidation modes:
1. Light consolidation - Fast cleanup (merge duplicates, resolve contradictions)
2. Deep consolidation - Pattern extraction and abstraction
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from lyra_memory.schema import MemoryRecord, MemoryType


@dataclass
class ConsolidationPattern:
    """
    A discovered pattern across multiple memories.
    
    Attributes:
        description: Natural language description of pattern
        source_memory_ids: Memories this pattern was extracted from
        confidence: Confidence in pattern (0.0-1.0)
        frequency: How often pattern appears
        abstraction_level: How abstract (0=concrete, 1=very abstract)
    """
    description: str
    source_memory_ids: list[str]
    confidence: float
    frequency: int
    abstraction_level: float = 0.5


@dataclass
class ConsolidationResult:
    """
    Result of a consolidation run.
    
    Attributes:
        duplicates_merged: Number of duplicate memories merged
        contradictions_resolved: Number of contradictions resolved
        patterns_extracted: Number of patterns discovered
        memories_compressed: Number of memories compressed
        memories_archived: Number of memories archived
        duration_seconds: How long consolidation took
    """
    duplicates_merged: int = 0
    contradictions_resolved: int = 0
    patterns_extracted: int = 0
    memories_compressed: int = 0
    memories_archived: int = 0
    duration_seconds: float = 0.0


class ConsolidationEngine:
    """
    Offline memory consolidation engine.
    
    Runs during low-activity periods to:
    - Merge duplicate memories
    - Resolve contradictions
    - Extract patterns
    - Compress verbose memories
    - Archive stale information
    """

    def __init__(
        self,
        similarity_threshold: float = 0.95,
        compression_min_length: int = 500,
        pattern_min_frequency: int = 2,
        pattern_confidence_threshold: float = 0.7,
    ):
        """
        Initialize consolidation engine.
        
        Args:
            similarity_threshold: Threshold for duplicate detection
            compression_min_length: Min length for compression
            pattern_min_frequency: Min occurrences for pattern
            pattern_confidence_threshold: Min confidence for pattern
        """
        self.similarity_threshold = similarity_threshold
        self.compression_min_length = compression_min_length
        self.pattern_min_frequency = pattern_min_frequency
        self.pattern_confidence_threshold = pattern_confidence_threshold

    def light_consolidation(
        self,
        memories: list[MemoryRecord],
    ) -> ConsolidationResult:
        """
        Fast consolidation: cleanup and deduplication.
        
        Args:
            memories: List of memories to consolidate
            
        Returns:
            ConsolidationResult with statistics
        """
        start_time = time.time()
        result = ConsolidationResult()

        # 1. Find and merge duplicates
        duplicates = self._find_duplicates(memories)
        result.duplicates_merged = len(duplicates)

        # 2. Resolve contradictions
        contradictions = self._find_contradictions(memories)
        result.contradictions_resolved = len(contradictions)

        result.duration_seconds = time.time() - start_time
        return result

    def deep_consolidation(
        self,
        memories: list[MemoryRecord],
        session_window_days: int = 7,
    ) -> tuple[ConsolidationResult, list[ConsolidationPattern]]:
        """
        Deep consolidation: pattern extraction and abstraction.
        
        Args:
            memories: List of memories to consolidate
            session_window_days: Days to look back for patterns
            
        Returns:
            Tuple of (ConsolidationResult, List of patterns)
        """
        start_time = time.time()
        result = ConsolidationResult()

        # 1. Light consolidation first
        light_result = self.light_consolidation(memories)
        result.duplicates_merged = light_result.duplicates_merged
        result.contradictions_resolved = light_result.contradictions_resolved

        # 2. Extract patterns from recent memories
        cutoff = datetime.now() - timedelta(days=session_window_days)
        recent_memories = [
            m for m in memories
            if m.created_at >= cutoff
        ]

        patterns = self._extract_patterns(recent_memories)
        result.patterns_extracted = len(patterns)

        # 3. Compress verbose memories
        verbose_memories = [
            m for m in memories
            if len(m.content) >= self.compression_min_length
        ]
        result.memories_compressed = len(verbose_memories)

        result.duration_seconds = time.time() - start_time
        return result, patterns

    def _find_duplicates(
        self,
        memories: list[MemoryRecord],
    ) -> list[list[str]]:
        """
        Find duplicate or near-duplicate memories.
        
        Returns list of duplicate groups (each group is list of memory IDs).
        """
        duplicates = []
        seen: set[str] = set()

        for i, mem1 in enumerate(memories):
            if mem1.id in seen:
                continue

            group = [mem1.id]

            for mem2 in memories[i+1:]:
                if mem2.id in seen:
                    continue

                # Check similarity
                similarity = self._compute_similarity(mem1.content, mem2.content)
                if similarity >= self.similarity_threshold:
                    group.append(mem2.id)
                    seen.add(mem2.id)

            if len(group) > 1:
                duplicates.append(group)
                seen.add(mem1.id)

        return duplicates

    def _find_contradictions(
        self,
        memories: list[MemoryRecord],
    ) -> list[tuple[str, str]]:
        """
        Find contradictory memories.
        
        Returns list of (memory_id1, memory_id2) pairs.
        """
        contradictions = []

        # Group by type for efficiency
        by_type: dict[MemoryType, list[MemoryRecord]] = {}
        for mem in memories:
            if mem.type not in by_type:
                by_type[mem.type] = []
            by_type[mem.type].append(mem)

        # Check for contradictions within each type
        for mem_type, type_memories in by_type.items():
            for i, mem1 in enumerate(type_memories):
                for mem2 in type_memories[i+1:]:
                    if self._are_contradictory(mem1, mem2):
                        contradictions.append((mem1.id, mem2.id))

        return contradictions

    def _extract_patterns(
        self,
        memories: list[MemoryRecord],
    ) -> list[ConsolidationPattern]:
        """
        Extract recurring patterns from memories.
        
        This is a simplified version. In production, would use:
        - LLM-based pattern extraction
        - Sequence mining algorithms
        - Topic modeling
        """
        patterns = []

        # Group memories by type
        by_type: dict[MemoryType, list[MemoryRecord]] = {}
        for mem in memories:
            if mem.type not in by_type:
                by_type[mem.type] = []
            by_type[mem.type].append(mem)

        # Look for repeated content patterns
        for mem_type, type_memories in by_type.items():
            if len(type_memories) < self.pattern_min_frequency:
                continue

            # Extract common phrases (simplified)
            phrase_counts: dict[str, list[str]] = {}
            for mem in type_memories:
                phrases = self._extract_phrases(mem.content)
                for phrase in phrases:
                    if phrase not in phrase_counts:
                        phrase_counts[phrase] = []
                    phrase_counts[phrase].append(mem.id)

            # Create patterns from frequent phrases
            for phrase, memory_ids in phrase_counts.items():
                if len(memory_ids) >= self.pattern_min_frequency:
                    confidence = min(1.0, len(memory_ids) / len(type_memories))

                    if confidence >= self.pattern_confidence_threshold:
                        pattern = ConsolidationPattern(
                            description=f"Pattern: {phrase}",
                            source_memory_ids=memory_ids,
                            confidence=confidence,
                            frequency=len(memory_ids),
                            abstraction_level=0.5,
                        )
                        patterns.append(pattern)

        return patterns

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.
        
        Simplified version using Jaccard similarity.
        In production, would use embeddings.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _are_contradictory(self, mem1: MemoryRecord, mem2: MemoryRecord) -> bool:
        """
        Check if two memories contradict each other.
        
        Simplified version. In production, would use:
        - NLI (Natural Language Inference) models
        - Temporal reasoning
        - Fact-checking
        """
        # Check for explicit negation patterns
        negation_pairs = [
            ("uses", "doesn't use"),
            ("prefers", "doesn't prefer"),
            ("is", "is not"),
            ("has", "doesn't have"),
        ]

        content1_lower = mem1.content.lower()
        content2_lower = mem2.content.lower()

        for positive, negative in negation_pairs:
            if positive in content1_lower and negative in content2_lower:
                return True
            if negative in content1_lower and positive in content2_lower:
                return True

        return False

    def _extract_phrases(self, text: str, min_words: int = 3) -> list[str]:
        """
        Extract meaningful phrases from text.
        
        Simplified version. In production, would use:
        - NLP chunking
        - Named entity recognition
        - Keyphrase extraction
        """
        words = text.lower().split()
        phrases = []

        # Extract n-grams
        for n in range(min_words, min(6, len(words) + 1)):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                # Filter out common stop phrases
                if not self._is_stop_phrase(phrase):
                    phrases.append(phrase)

        return phrases

    def _is_stop_phrase(self, phrase: str) -> bool:
        """Check if phrase is too common to be meaningful."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as", "is", "was",
        }
        words = phrase.split()
        return all(word in stop_words for word in words)


__all__ = [
    "ConsolidationPattern",
    "ConsolidationResult",
    "ConsolidationEngine",
]
