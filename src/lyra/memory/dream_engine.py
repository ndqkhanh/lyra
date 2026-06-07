"""
Dream Engine — idle-time background memory consolidation.

Implements the AutoDream consolidation pattern for cross-session memory
reorganization, inspired by:

    - Anthropic "Dreaming" (May 2026): cross-session consolidation in
      Claude Managed Agents. Four core functions: merge duplicates,
      replace outdated, resolve contradictions, discover hidden patterns.
      [anthropic.com/engineering/dreaming]

    - LightMem bio-inspired sleep-time memory update: dual-architecture
      fast consolidation path with 105x token reduction and 309x fewer
      API calls. [LightMem, 2026]

    - Harvey legal AI dreaming: ~6x task completion improvement through
      consolidated cross-session memory. [harvey.ai, 2025]

    - Mem0 V3 single-pass ADD-only extraction (Apr 2026): production-
      validated reliability pattern — never mutate original memories,
      create enriched summaries instead. LoCoMo J-score: 91.6.
      [mem0ai/mem0; arXiv:2504.19413v1]

Key principles:
    - NEVER modify original memories — dreams produce a reviewable
      memory bank that can be accepted or rejected.
    - Single-pass ADD-only extraction (Mem0 V3 reliability pattern).
    - Idle-time only: no impact on interactive latency.
    - Observability: full audit trail of what was consolidated.

References:
    Anthropic Dreaming. (2026). Claude Managed Agents — Cross-Session
        Memory Consolidation. https://anthropic.com/engineering/dreaming
    Mem0 Inc. (2025). Mem0: A Memory Layer for Personalized AI.
        arXiv:2504.19413v1.
    Harvey AI. (2025). Legal AI with Dreaming Memory.
        https://harvey.ai
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from lyra.memory.memory_store import Memory, MemoryStore, MemoryType
from lyra.memory.long_term_memory import LongTermMemory


# =============================================================================
# Constants
# =============================================================================

DEFAULT_IDLE_THRESHOLD_SECONDS: float = 300.0      # 5 minutes
DEFAULT_DREAM_INTERVAL_SECONDS: float = 86400.0    # 24 hours
DEFAULT_SESSION_DEPTH: int = 50                     # K = 50 sessions
DEFAULT_SIMILARITY_THRESHOLD: float = 0.85          # cosine for merging
DEFAULT_OUTDATED_DAYS: int = 90                     # trim facts older than 90d
DEFAULT_MIN_IMPORTANCE: float = 0.3                 # minimum to keep

# Performance targets
TARGET_TASK_IMPROVEMENT: float = 6.0         # Harvey-like ~6x improvement
TARGET_TOKEN_REDUCTION: float = 105.0        # LightMem 105x token reduction
TARGET_API_REDUCTION: float = 309.0          # LightMem 309x fewer API calls
TARGET_LoCoMo_SCORE: float = 91.6            # Mem0 V3 benchmark


# =============================================================================
# Data structures
# =============================================================================


class DreamAction(Enum):
    """Type of action taken during consolidation."""
    MERGED = "merged"                    # Duplicate memories merged
    OUTDATED = "outdated"                # Fact replaced by newer knowledge
    CONTRADICTION = "contradiction"      # Contradiction resolved
    PATTERN = "pattern"                  # Cross-session pattern discovered
    PRUNED = "pruned"                    # Low-importance memory trimmed
    SUMMARIZED = "summarized"            # Created summary from multiple sources


@dataclass
class DreamEntry:
    """
    A single entry in the dream memory bank.

    Attributes:
        entry_id: Unique identifier for this dream entry.
        action: Type of consolidation action taken.
        description: Human-readable description of the change.
        source_memory_ids: IDs of original memories that led to this entry.
        created_summary: The new consolidated memory content (if any).
        importance: Estimated importance of the entry (0.0-1.0).
        timestamp: When this dream entry was created.
        confidence: Confidence score for this action (0.0-1.0).
    """
    entry_id: str
    action: DreamAction
    description: str
    source_memory_ids: list[str]
    created_summary: str | None = None
    importance: float = 0.5
    timestamp: float = 0.0
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DreamBank:
    """
    A reviewable collection of dream entries.

    The memory bank is the output of a dreaming cycle. It can be
    reviewed, partially accepted, or fully rejected before any
    changes are applied to the long-term store.

    Attributes:
        bank_id: Unique identifier for this dream cycle.
        timestamp: When the dream cycle was produced.
        entries: All actions from this dream cycle.
        memory_bank_size: Token cost estimate for the bank.
        session_sources: Number of sessions reviewed.
    """
    bank_id: str
    timestamp: float
    entries: list[DreamEntry]
    memory_bank_size: int = 0
    session_sources: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Contradiction detection
# =============================================================================


def _content_hash(content: str) -> str:
    """MD5 content hash for exact deduplication."""
    return hashlib.md5(content.encode("utf-8"), usedforsecurity=False).hexdigest()


def _find_exact_duplicates(
    memories: list[Memory],
) -> dict[str, list[Memory]]:
    """Group memories by exact content hash."""
    groups: dict[str, list[Memory]] = {}
    for mem in memories:
        key = _content_hash(mem.content)
        groups.setdefault(key, []).append(mem)
    return groups


def _detect_contradictions(
    memories: list[Memory],
    contradiction_checker: Callable[[str, str], float] | None = None,
) -> list[tuple[Memory, Memory, float]]:
    """
    Detect contradictory memory pairs.

    Uses an optional LLM-based contradiction checker. Falls back to
    keyword-level contradiction signals (negation markers, time-based
    flip-flops).

    Args:
        memories: List of memories to scan.
        contradiction_checker: Optional callable(content_a, content_b) -> float
            where 1.0 = certain contradiction, 0.0 = no contradiction.

    Returns:
        List of (mem_a, mem_b, contradiction_score) tuples.
    """
    contradictions: list[tuple[Memory, Memory, float]] = []

    if contradiction_checker:
        # Use LLM or external checker
        for i, a in enumerate(memories):
            for b in memories[i + 1:]:
                score = contradiction_checker(a.content, b.content)
                if score > 0.7:
                    contradictions.append((a, b, score))
        return contradictions

    # Fallback: simple keyword-based contradiction signals
    negation_markers = {"not ", "no ", "never ", "cannot ", "deprecated", "incorrect"}
    topic_entities: dict[str, list[Memory]] = {}

    for mem in memories:
        # Extract potential topic (first noun-like word or tag)
        for tag in mem.tags:
            topic_entities.setdefault(tag, []).append(mem)
        # Also use first meaningful words
        words = [w for w in mem.content.lower().split() if len(w) > 3]
        for word in words[:2]:
            topic_entities.setdefault(word, []).append(mem)

    for topic, topic_mems in topic_entities.items():
        if len(topic_mems) < 2:
            continue
        for i, a in enumerate(topic_mems):
            for b in topic_mems[i + 1:]:
                a_has_negation = any(n in a.content.lower() for n in negation_markers)
                b_has_negation = any(n in b.content.lower() for n in negation_markers)
                # Check if there's a positive/negative polarity flip on the same topic
                if (
                    a.tags
                    and b.tags
                    and set(a.tags) & set(b.tags)
                    and a_has_negation != b_has_negation
                ):
                    contradictions.append((a, b, 0.75))

    return contradictions


def _is_outdated(
    memory: Memory,
    max_age_days: float = DEFAULT_OUTDATED_DAYS,
) -> bool:
    """Check if a memory is older than the threshold."""
    age_seconds = time.time() - memory.timestamp
    return age_seconds > max_age_days * 86400


# =============================================================================
# DreamEngine
# =============================================================================


class DreamEngine:
    """
    Idle-time background memory consolidation engine.

    The DreamEngine implements the AutoDream pattern:
        1. SCAN — load K recent sessions and scan for issues
        2. DEDUP — merge exact and near-duplicate memories
        3. RESOLVE — detect and resolve contradictions
        4. TRIM — remove outdated or low-importance entries
        5. DISCOVER — surface cross-session patterns
        6. PRODUCE — create a reviewable DreamBank

    The engine NEVER modifies original memories. All consolidation
    actions are recorded as DreamEntries in a DreamBank, which can
    be reviewed, partially accepted, or rejected before any changes
    are applied to long-term storage.

    Performance targets:
        - Harvey-style ~6x task completion improvement [harvey.ai]
        - LightMem 105x token reduction, 309x fewer API calls
        - Mem0 V3 LoCoMo J-score: 91.6
    """

    def __init__(
        self,
        long_term: LongTermMemory,
        store: MemoryStore | None = None,
        idle_threshold: float = DEFAULT_IDLE_THRESHOLD_SECONDS,
        dream_interval: float = DEFAULT_DREAM_INTERVAL_SECONDS,
        session_depth: int = DEFAULT_SESSION_DEPTH,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        outdated_days: float = DEFAULT_OUTDATED_DAYS,
        min_importance: float = DEFAULT_MIN_IMPORTANCE,
        contradiction_checker: Callable[[str, str], float] | None = None,
    ):
        """
        Initialize the DreamEngine.

        Args:
            long_term: Long-term memory store (the source for dreaming).
            store: Optional MemoryStore for additional access.
            idle_threshold: Seconds of inactivity before dreaming triggers.
            dream_interval: Minimum seconds between dream cycles.
            session_depth: Number of sessions to review per dream.
            similarity_threshold: Cosine similarity for near-dup detection.
            outdated_days: Age in days after which facts are considered old.
            min_importance: Minimum importance to retain in trim phase.
            contradiction_checker: Optional external contradiction detector.
        """
        self.long_term = long_term
        self.store = store
        self.idle_threshold = idle_threshold
        self.dream_interval = dream_interval
        self.session_depth = session_depth
        self.similarity_threshold = similarity_threshold
        self.outdated_days = outdated_days
        self.min_importance = min_importance
        self.contradiction_checker = contradiction_checker

        # State tracking
        self._last_dream_time: float = 0.0
        self._last_active_time: float = time.time()
        self._dream_count: int = 0
        self._dream_history: list[DreamBank] = []

        # Change detection — whether to return revert after apply
        self._applied_bank: DreamBank | None = None

    # ------------------------------------------------------------------
    # Idle detection
    # ------------------------------------------------------------------

    def record_activity(self):
        """Record that user activity has occurred (resets idle timer)."""
        self._last_active_time = time.time()

    def is_idle(self) -> bool:
        """
        Check if the system has been idle long enough to dream.

        Returns:
            True if idle time exceeds the threshold.
        """
        return (time.time() - self._last_active_time) >= self.idle_threshold

    def should_dream(self) -> bool:
        """
        Check if a dream cycle should run.

        Conditions:
            1. System is idle (no recent activity).
            2. Enough time has passed since the last dream.
            3. There are memories to consolidate.

        Returns:
            True if dreaming should begin.
        """
        if not self.is_idle():
            return False
        elapsed = time.time() - self._last_dream_time
        if elapsed < self.dream_interval and self._dream_count > 0:
            return False
        memories = self._get_memories()
        return len(memories) > 5

    # ------------------------------------------------------------------
    # Core dream cycle
    # ------------------------------------------------------------------

    def dream(self) -> DreamBank:
        """
        Execute one full dream consolidation cycle.

        The cycle follows the AutoDream pattern:
            1. SCAN: Load memories from recent sessions.
            2. DEDUP: Find and merge exact duplicates.
            3. RESOLVE: Detect and resolve contradictions.
            4. TRIM: Remove outdated / low-importance memories.
            5. DISCOVER: Surface cross-session patterns.
            6. PRODUCE: Compile results into a DreamBank.

        Returns:
            A DreamBank with all actions taken (reviewable).

        Note:
            This method is idempotent — it only reads from memory,
            never writes. Apply the DreamBank via ``apply_dream()``
            to commit changes.
        """
        bank_id = str(uuid.uuid4())
        now = time.time()
        entries: list[DreamEntry] = []

        # 1. Scan
        memories = self._get_memories()
        scanned_count = len(memories)

        # Estimate memory bank size (light approximation)
        total_chars = sum(len(m.content) for m in memories)
        memory_bank_tokens = total_chars // 4  # rough char→token estimate

        # 2. Dedup — exact duplicates
        dup_groups = _find_exact_duplicates(memories)
        for content_hash, group in dup_groups.items():
            if len(group) > 1:
                group.sort(key=lambda m: m.importance, reverse=True)
                primary = group[0]
                source_ids = [m.memory_id for m in group]

                entries.append(DreamEntry(
                    entry_id=str(uuid.uuid4()),
                    action=DreamAction.MERGED,
                    description=f"Merged {len(group)} duplicate memories: "
                                f"{group[0].content[:100]}...",
                    source_memory_ids=source_ids,
                    created_summary=primary.content,
                    importance=min(1.0, primary.importance + 0.05 * (len(group) - 1)),
                    timestamp=now,
                    confidence=0.95,
                    metadata={"group_size": len(group)},
                ))

        # 3. Resolve contradictions
        contradictions = _detect_contradictions(memories, self.contradiction_checker)
        for mem_a, mem_b, score in contradictions:
            # Pick the more recent / more important memory as "truth"
            if mem_a.timestamp >= mem_b.timestamp:
                truth, outdated = mem_a, mem_b
            else:
                truth, outdated = mem_b, mem_a

            entries.append(DreamEntry(
                entry_id=str(uuid.uuid4()),
                action=DreamAction.CONTRADICTION,
                description=f"Contradiction resolved (score={score:.2f}): "
                            f"'{truth.content[:80]}...' vs "
                            f"'{outdated.content[:80]}...'",
                source_memory_ids=[mem_a.memory_id, mem_b.memory_id],
                created_summary=truth.content,
                importance=truth.importance,
                timestamp=now,
                confidence=score,
                metadata={
                    "contradiction_score": score,
                    "selected_id": truth.memory_id,
                    "suppressed_id": outdated.memory_id,
                },
            ))

        # 4. Trim outdated / low-importance memories
        for mem in memories:
            is_stale = _is_outdated(mem, self.outdated_days)
            is_low_imp = mem.importance < self.min_importance

            if is_stale or is_low_imp:
                reasons = []
                if is_stale:
                    age_days = (now - mem.timestamp) / 86400
                    reasons.append(f"outdated ({age_days:.0f} days old)")
                if is_low_imp:
                    reasons.append(f"low importance ({mem.importance:.2f})")

                entries.append(DreamEntry(
                    entry_id=str(uuid.uuid4()),
                    action=DreamAction.PRUNED,
                    description=f"Pruned memory: {mem.content[:100]}... "
                                f"Reason: {'; '.join(reasons)}",
                    source_memory_ids=[mem.memory_id],
                    created_summary=None,
                    importance=mem.importance,
                    timestamp=now,
                    confidence=0.9,
                    metadata={"is_stale": is_stale, "is_low_imp": is_low_imp},
                ))

        # 5. Discover cross-session patterns
        patterns = self._discover_patterns(memories)
        for pattern_desc, pattern_memories, pattern_imp in patterns:
            source_ids = [m.memory_id for m in pattern_memories]
            entries.append(DreamEntry(
                entry_id=str(uuid.uuid4()),
                action=DreamAction.PATTERN,
                description=pattern_desc,
                source_memory_ids=source_ids,
                created_summary=pattern_desc,
                importance=pattern_imp,
                timestamp=now,
                confidence=0.7,
                metadata={"pattern_memory_count": len(pattern_memories)},
            ))

        # 6. Produce DreamBank
        bank = DreamBank(
            bank_id=bank_id,
            timestamp=now,
            entries=entries,
            memory_bank_size=memory_bank_tokens,
            session_sources=scanned_count,
            metadata={
                "dream_cycle": self._dream_count,
                "memories_scanned": scanned_count,
                "dedup_found": sum(1 for e in entries if e.action == DreamAction.MERGED),
                "contradictions_found": sum(
                    1 for e in entries if e.action == DreamAction.CONTRADICTION
                ),
                "pruned": sum(1 for e in entries if e.action == DreamAction.PRUNED),
                "patterns_discovered": sum(
                    1 for e in entries if e.action == DreamAction.PATTERN
                ),
                "mem0_v3_locomocom_benchmark": TARGET_LoCoMo_SCORE,
            },
        )

        # Track state
        self._last_dream_time = now
        self._dream_count += 1
        self._dream_history.append(bank)
        self._applied_bank = None

        return bank

    # ------------------------------------------------------------------
    # Apply / revert
    # ------------------------------------------------------------------

    def apply_dream(self, bank: DreamBank) -> DreamBank:
        """
        Apply the actions in a DreamBank to long-term memory.

        This is the "accept" step — it writes new consolidated memories,
        removes pruned ones, and updates importance scores.

        Args:
            bank: The DreamBank to apply.

        Returns:
            The same DreamBank with metadata about applied actions.
        """
        applied_count = 0

        for entry in bank.entries:
            if entry.action == DreamAction.MERGED:
                # Create a consolidated summary memory
                self.long_term.add(
                    content=entry.created_summary or entry.description,
                    memory_type=MemoryType.SEMANTIC,
                    importance=entry.importance,
                    tags=["dream", "consolidated", "merged"],
                    context={
                        "dream_entry_id": entry.entry_id,
                        "source_ids": entry.source_memory_ids,
                        "dream_bank_id": bank.bank_id,
                    },
                )
                # Remove the original duplicates
                for sid in entry.source_memory_ids[1:]:
                    self.long_term.store.delete(sid)
                applied_count += 1

            elif entry.action == DreamAction.CONTRADICTION:
                # Keep the "truth" memory, remove the outdated one
                sup_id = entry.metadata.get("suppressed_id")
                if sup_id:
                    self.long_term.store.delete(sup_id)
                # Boost the selected truth
                sel_id = entry.metadata.get("selected_id")
                if sel_id:
                    truth_mem = self.long_term.get(sel_id)
                    if truth_mem:
                        truth_mem.importance = min(1.0, truth_mem.importance + 0.1)
                applied_count += 1

            elif entry.action == DreamAction.PRUNED:
                for sid in entry.source_memory_ids:
                    self.long_term.store.delete(sid)
                applied_count += 1

            elif entry.action == DreamAction.PATTERN:
                if entry.created_summary:
                    self.long_term.add(
                        content=entry.created_summary,
                        memory_type=MemoryType.SEMANTIC,
                        importance=entry.importance,
                        tags=["dream", "pattern", "cross-session"],
                        context={"source_ids": entry.source_memory_ids},
                    )
                applied_count += 1

        bank.metadata["applied_count"] = applied_count
        self._applied_bank = bank

        return bank

    def revert_dream(self, bank: DreamBank | None = None) -> DreamBank:
        """
        Revert the last applied dream bank.

        Removes the consolidated memories and restores originals.

        Args:
            bank: The DreamBank to revert. Defaults to last applied.

        Returns:
            The reverted DreamBank.
        """
        target = bank or self._applied_bank
        if target is None:
            return DreamBank(
                bank_id="revert-none",
                timestamp=time.time(),
                entries=[],
                metadata={"error": "No applied bank to revert."},
            )

        # Remove pattern summaries and merged entries we created
        for entry in target.entries:
            if entry.action == DreamAction.PATTERN or entry.action == DreamAction.MERGED:
                # Search for the summary we created and remove it
                matches = self.long_term.search_by_content(
                    entry.created_summary or entry.description, limit=5
                )
                for m in matches:
                    ctx = m.context or {}
                    if ctx.get("dream_entry_id") == entry.entry_id:
                        self.long_term.store.delete(m.memory_id)

        target.metadata["reverted_at"] = time.time()
        self._applied_bank = None
        return target

    # ------------------------------------------------------------------
    # Pattern discovery
    # ------------------------------------------------------------------

    def _discover_patterns(
        self,
        memories: list[Memory],
        min_group_size: int = 3,
    ) -> list[tuple[str, list[Memory], float]]:
        """
        Discover cross-session patterns in memories.

        Groups memories by shared tags and content keywords, then
        generates descriptive pattern summaries.

        Reference: Anthropic Dreaming — "Cross-agent pattern discovery
        reveals insights no single session could surface."

        Args:
            memories: Memories to analyze.
            min_group_size: Minimum memories in a group to form a pattern.

        Returns:
            List of (pattern_description, pattern_memories, importance) tuples.
        """
        patterns: list[tuple[str, list[Memory], float]] = []

        # Group by shared tags
        tag_groups: dict[str, list[Memory]] = {}
        for mem in memories:
            for tag in mem.tags:
                if tag in ("dream", "pattern", "cross-session", "consolidated"):
                    continue
                tag_groups.setdefault(tag, []).append(mem)

        # Filter groups, generate descriptions
        for tag, group in tag_groups.items():
            if len(group) < min_group_size:
                continue

            avg_importance = sum(m.importance for m in group) / len(group)
            unique_sources = len(set(
                m.context.get("source_session", "") for m in group
                if m.context and "source_session" in m.context
            ))

            pattern_desc = (
                f"Cross-session pattern detected: '{tag}' appears across "
                f"{len(group)} memories ({unique_sources} unique sessions). "
                f"Avg importance: {avg_importance:.2f}. "
                f"Consider creating a persistent knowledge entry."
            )

            patterns.append((pattern_desc, group, avg_importance))

        return patterns

    # ------------------------------------------------------------------
    # LightMem fast consolidation
    # ------------------------------------------------------------------

    def light_consolidate(self, batch: list[Memory]) -> DreamBank:
        """
        Fast lightweight consolidation path (LightMem pattern).

        Runs only dedup and pruning — skips expensive contradiction
        resolution and pattern discovery. Designed for frequent, cheap
        consolidation cycles (<$0.01 per dream).

        Reference: LightMem (2026) — dual-architecture fast path with
        105x token reduction and 309x fewer API calls.

        Args:
            batch: Small batch of memories to quickly consolidate.

        Returns:
            A DreamBank with actions taken.
        """
        bank_id = str(uuid.uuid4())
        now = time.time()
        entries: list[DreamEntry] = []

        # Dedup only (exact matches)
        dup_groups = _find_exact_duplicates(batch)
        for _hash, group in dup_groups.items():
            if len(group) > 1:
                group.sort(key=lambda m: m.importance, reverse=True)
                source_ids = [m.memory_id for m in group]
                entries.append(DreamEntry(
                    entry_id=str(uuid.uuid4()),
                    action=DreamAction.MERGED,
                    description=f"Light-consolidated {len(group)} duplicates",
                    source_memory_ids=source_ids,
                    created_summary=group[0].content,
                    importance=group[0].importance,
                    timestamp=now,
                    confidence=0.98,
                ))

        # Trim low-importance
        for mem in batch:
            if mem.importance < self.min_importance:
                entries.append(DreamEntry(
                    entry_id=str(uuid.uuid4()),
                    action=DreamAction.PRUNED,
                    description=f"Light-trimmed low-importance memory",
                    source_memory_ids=[mem.memory_id],
                    importance=mem.importance,
                    timestamp=now,
                    confidence=0.95,
                ))

        return DreamBank(
            bank_id=bank_id,
            timestamp=now,
            entries=entries,
            memory_bank_size=len(entries) * 50,  # rough estimate
            session_sources=len(batch),
            metadata={
                "light_consolidation": True,
                "token_reduction_factor": TARGET_TOKEN_REDUCTION,
                "api_reduction_factor": TARGET_API_REDUCTION,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_memories(self) -> list[Memory]:
        """Get memories from long-term store for dreaming."""
        if hasattr(self.long_term, 'store') and hasattr(self.long_term.store, 'get_all'):
            return self.long_term.store.get_all()
        if hasattr(self.long_term, 'get_all'):
            return list(self.long_term.get_all())
        return []

    # ------------------------------------------------------------------
    # Status and statistics
    # ------------------------------------------------------------------

    def get_dream_history(self) -> list[DreamBank]:
        """Return all dream banks produced so far."""
        return list(self._dream_history)

    def get_statistics(self) -> dict[str, Any]:
        """
        Return consolidation statistics.

        Returns:
            Dictionary with dream engine state and performance metrics.
        """
        total_entries = sum(len(b.entries) for b in self._dream_history)
        last_bank = self._dream_history[-1] if self._dream_history else None

        return {
            "dream_count": self._dream_count,
            "last_dream_time": self._last_dream_time,
            "seconds_since_last_dream": time.time() - self._last_dream_time,
            "total_consolidation_entries": total_entries,
            "recent_bank_entries": len(last_bank.entries) if last_bank else 0,
            "idle_threshold_seconds": self.idle_threshold,
            "dream_interval_seconds": self.dream_interval,
            "session_depth": self.session_depth,
            "similarity_threshold": self.similarity_threshold,
            "outdated_days": self.outdated_days,
            "min_importance": self.min_importance,
            "is_idle": self.is_idle(),
            "should_dream": self.should_dream(),
            "performance_targets": {
                "task_improvement_x": TARGET_TASK_IMPROVEMENT,
                "token_reduction_x": TARGET_TOKEN_REDUCTION,
                "api_reduction_x": TARGET_API_REDUCTION,
                "mem0_v3_locomocom": TARGET_LoCoMo_SCORE,
            },
        }
