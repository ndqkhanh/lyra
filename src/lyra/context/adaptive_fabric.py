"""
Adaptive Context Fabric — ACON-style context optimization for Lyra.

The AdaptiveContextFabric evolves context composition per task type using
ACE-style typed experience units. It provides:

- ``compress(messages, target_ratio)``: Compresses a conversation history to
  a target token ratio by selectively removing or summarizing low-value turns.
- ``evolve_context(task_type, feedback)``: Learns the optimal compaction
  strategy per task type through reinforcement from usage feedback.
- ``speculate(tool_name, tool_input)``: Pre-computes likely next context
  segments during tool-waiting periods (IdleSpec-style).
- ``ContextPolicy``: A dataclass capturing the learned compaction policy
  (strategy, keep_recent, protect_system, target_ratio).

Enhancements in v8.1
--------------------
- ``TaskTypeProfile``: Pre-configured profiles per task type — code, chat,
  research — that control compaction behaviour (structure protection,
  summarization aggressiveness, citation preservation).
- ``TaskTypeProfiles``: Registry of named profiles.
- Full ACON integration: the feedback loop learns optimal compaction strategy
  per task type, updates task type profiles dynamically, and tracks
  cost-per-token per strategy.
- ``CostPerTokenTracker``: Records token cost per compaction strategy.

References
----------
- ACON (Adaptive Context Optimization): evolves context composition per task
  type by treating context as typed experience units.
- ACE (Adaptive Context Engine): evolving contexts where each unit type
  captures a different dimension of agent experience.
- IdleSpec: speculative planning that pre-computes likely next context during
  tool-waiting periods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from statistics import mean
from typing import Any

from lyra.context.compaction import CompactionStrategy
from lyra.context.experience_units import (
    ExperienceUnitType,
    TypedExperienceUnit,
    UnitLibrary,
)

# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

Message = dict[str, str]  # {"role": "...", "content": "..."}


@dataclass
class ContextPolicy:
    """Learned policy for optimal context compaction on a given task type.

    Attributes:
        compaction_strategy: Which CompactionStrategy to prefer.
        keep_recent:         Number of most recent turns to always preserve.
        protect_system:      Whether the system message must be kept verbatim.
        target_ratio:        Target compression ratio (0.0 = compress everything,
                             1.0 = keep everything).
    """

    compaction_strategy: CompactionStrategy = CompactionStrategy.BALANCED
    keep_recent: int = 5
    protect_system: bool = True
    target_ratio: float = 0.6

    def to_dict(self) -> dict[str, Any]:
        return {
            "compaction_strategy": self.compaction_strategy.value,
            "keep_recent": self.keep_recent,
            "protect_system": self.protect_system,
            "target_ratio": self.target_ratio,
        }


# ---------------------------------------------------------------------------
# TaskTypeProfile — ACON integration
# ---------------------------------------------------------------------------


class ProfileType(str, Enum):
    """Named task type profiles that control compaction behaviour."""

    CODE = "code"
    CHAT = "chat"
    RESEARCH = "research"
    GENERAL = "general"


@dataclass
class TaskTypeProfile:
    """Pre-configured compaction behaviour for a task type category.

    Attributes:
        profile_type:        Which profile this represents.
        protect_code:        Whether code blocks must never be compacted.
        summarization_aggressiveness: 0.0 (none) to 1.0 (max).
        keep_citations:      Whether citation / reference patterns must be
                             preserved (important for research tasks).
        default_target_ratio: Fallback target ratio.
        description:         Human-readable description.
    """

    profile_type: ProfileType
    protect_code: bool = False
    summarization_aggressiveness: float = 0.5
    keep_citations: bool = False
    default_target_ratio: float = 0.6
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_type": self.profile_type.value,
            "protect_code": self.protect_code,
            "summarization_aggressiveness": self.summarization_aggressiveness,
            "keep_citations": self.keep_citations,
            "default_target_ratio": self.default_target_ratio,
            "description": self.description,
        }


class TaskTypeProfiles:
    """Registry of named :class:`TaskTypeProfile` instances.

    Provides factory methods and a registry that maps ``ProfileType`` and
    string-based task type keys to profiles.
    """

    _DEFAULT_PROFILES: dict[ProfileType, TaskTypeProfile] = {
        ProfileType.CODE: TaskTypeProfile(
            profile_type=ProfileType.CODE,
            protect_code=True,
            summarization_aggressiveness=0.4,
            keep_citations=False,
            default_target_ratio=0.7,
            description="Protect code structure; moderate summarization; retain more context.",
        ),
        ProfileType.CHAT: TaskTypeProfile(
            profile_type=ProfileType.CHAT,
            protect_code=False,
            summarization_aggressiveness=0.8,
            keep_citations=False,
            default_target_ratio=0.3,
            description="Aggressive summarization; no code protection needed.",
        ),
        ProfileType.RESEARCH: TaskTypeProfile(
            profile_type=ProfileType.RESEARCH,
            protect_code=False,
            summarization_aggressiveness=0.3,
            keep_citations=True,
            default_target_ratio=0.6,
            description="Preserve citations; light summarization to keep evidence.",
        ),
        ProfileType.GENERAL: TaskTypeProfile(
            profile_type=ProfileType.GENERAL,
            protect_code=False,
            summarization_aggressiveness=0.5,
            keep_citations=False,
            default_target_ratio=0.6,
            description="Default balanced profile.",
        ),
    }

    # Heuristic mapping from task type string to profile type
    _TASK_TYPE_MAP: dict[str, ProfileType] = {
        "code_generation": ProfileType.CODE,
        "code_review": ProfileType.CODE,
        "debugging": ProfileType.CODE,
        "refactoring": ProfileType.CODE,
        "chat": ProfileType.CHAT,
        "conversation": ProfileType.CHAT,
        "research": ProfileType.RESEARCH,
        "analysis": ProfileType.RESEARCH,
        "investigation": ProfileType.RESEARCH,
    }

    def __init__(self) -> None:
        self._profiles: dict[ProfileType, TaskTypeProfile] = {
            k: v for k, v in self._DEFAULT_PROFILES.items()
        }

    def get_by_task_type(self, task_type: str) -> TaskTypeProfile:
        """Return the profile best matching a task type string.

        Args:
            task_type: The task type key (e.g. ``"code_review"``).

        Returns:
            The matching profile, falling back to ``GENERAL``.
        """
        pt = self._TASK_TYPE_MAP.get(task_type, ProfileType.GENERAL)
        return self._profiles.get(pt, self._profiles[ProfileType.GENERAL])

    def get_by_profile_type(self, pt: ProfileType) -> TaskTypeProfile:
        """Return profile by :class:`ProfileType`.

        Args:
            pt: The profile type enum value.

        Returns:
            The matching profile, falling back to ``GENERAL``.
        """
        return self._profiles.get(pt, self._profiles[ProfileType.GENERAL])

    @property
    def all_profiles(self) -> dict[ProfileType, TaskTypeProfile]:
        return dict(self._profiles)

    def update_profile(self, profile: TaskTypeProfile) -> None:
        """Update a profile in the registry (for ACON learning).

        Args:
            profile: The profile to upsert.
        """
        self._profiles[profile.profile_type] = profile


# ---------------------------------------------------------------------------
# CostPerToken tracking
# ---------------------------------------------------------------------------


@dataclass
class CostPerTokenRecord:
    """Cost tracking record for a single compaction operation.

    Attributes:
        strategy:       The compaction strategy used.
        tokens_before:  Token count before compaction.
        tokens_after:   Token count after compaction.
        estimated_cost: Estimated USD cost of the compaction operation.
        task_type:      The task type this compaction was for.
        timestamp:      ISO-formatted timestamp.
    """

    strategy: CompactionStrategy
    tokens_before: int
    tokens_after: int
    estimated_cost: float
    task_type: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


@dataclass
class CostPerTokenTracker:
    """Tracks token cost per compaction strategy across task types.

    Maintains a history of compaction operations and provides summary
    statistics: average compression ratio, average cost per token saved,
    and average cost per operation for each strategy.
    """

    records: list[CostPerTokenRecord] = field(default_factory=list)

    def record(
        self,
        strategy: CompactionStrategy,
        tokens_before: int,
        tokens_after: int,
        estimated_cost: float,
        task_type: str,
    ) -> None:
        """Record a compaction operation.

        Args:
            strategy:      The compaction strategy used.
            tokens_before: Token count before.
            tokens_after:  Token count after.
            estimated_cost: Estimated USD cost of the operation.
            task_type:     The task type.
        """
        self.records.append(CostPerTokenRecord(
            strategy=strategy,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            estimated_cost=estimated_cost,
            task_type=task_type,
        ))

    def stats_by_strategy(
        self,
        strategy: CompactionStrategy | None = None,
    ) -> dict[str, Any]:
        """Return summary statistics, optionally filtered by strategy.

        Args:
            strategy: If set, only records for this strategy are included.

        Returns:
            Dict with ``total_ops``, ``avg_compression_ratio``,
            ``avg_cost_per_op``, ``avg_cost_per_token_saved``.
        """
        recs = (
            [r for r in self.records if r.strategy == strategy]
            if strategy is not None
            else self.records[:]
        )
        if not recs:
            return {
                "total_ops": 0,
                "avg_compression_ratio": 0.0,
                "avg_cost_per_op": 0.0,
                "avg_cost_per_token_saved": 0.0,
            }

        ratios = [
            (r.tokens_before - r.tokens_after) / max(r.tokens_before, 1)
            for r in recs
        ]
        costs_per_token_saved = []
        for r in recs:
            saved = r.tokens_before - r.tokens_after
            if saved > 0:
                costs_per_token_saved.append(r.estimated_cost / saved)

        return {
            "total_ops": len(recs),
            "avg_compression_ratio": mean(ratios) if ratios else 0.0,
            "avg_cost_per_op": mean(r.estimated_cost for r in recs) if recs else 0.0,
            "avg_cost_per_token_saved": mean(costs_per_token_saved)
            if costs_per_token_saved
            else 0.0,
        }

    def best_strategy_by_cost_efficiency(self) -> tuple[str, float]:
        """Return the strategy name and its cost-per-token-saved that is
        most cost-efficient (lowest cost per token saved).

        Returns:
            Tuple of ``(strategy_name, avg_cost_per_token_saved)``.
        """
        best = None
        best_cost = float("inf")
        for s in CompactionStrategy:
            stats = self.stats_by_strategy(s)
            if stats["total_ops"] > 0:
                cpt = stats["avg_cost_per_token_saved"]
                if cpt < best_cost:
                    best_cost = cpt
                    best = s.value
        return (best or "unknown", best_cost if best_cost != float("inf") else 0.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRUNCATION_MARKER = "[...truncated by Lyra Adaptive Fabric...]"


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: 1 token per 4 characters."""
    return max(1, len(text) // 4)


def _compute_message_weight(msg: Message) -> float:
    """Compute a weight for a message that indicates its relative value.

    Lower weights mean the message is a better candidate for removal.
    Uses heuristic rules:
    - System messages get high weight (protected).
    - Assistant messages with short content get medium weight.
    - User messages with long content get low weight (good truncation targets).
    - Tool result messages get low weight (bulky, often redundant).
    """
    role = msg.get("role", "")
    content = msg.get("content", "")
    length = len(content)

    if role == "system":
        return 2.0
    elif role == "assistant" and length < 500:
        return 1.5
    elif role == "assistant":
        return 1.0
    elif role == "tool" or role == "tool_result":
        return 0.3
    elif role == "user" and length < 200:
        return 0.8
    else:  # user or unknown with long content
        return 0.5


# ---------------------------------------------------------------------------
# Adaptive Context Fabric
# ---------------------------------------------------------------------------


@dataclass
class AdaptiveContextFabric:
    """Adaptive context compression and evolution engine.

    The fabric maintains per-task-type policies that are learned and refined
    through feedback. It also supports speculative context pre-computation
    for IdleSpec-style optimization.

    Usage::

        fabric = AdaptiveContextFabric()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Find all Python files."},
            {"role": "assistant", "content": "I found 42 Python files."},
        ]

        # Compress to 50% of original size
        compressed = fabric.compress(messages, target_ratio=0.5)

        # Evolve policy based on feedback
        policy = fabric.evolve_context(
            task_type="code_search",
            feedback={"success": True, "latency_reduction": 0.3},
        )

        # Speculate next context
        next_turns = fabric.speculate(
            tool_name="grep_search",
            tool_input={"pattern": "def test_"},
        )
    """

    # Per-task-type policies
    policies: dict[str, ContextPolicy] = field(default_factory=dict)
    # Shared experience library (or a dedicated one per task type)
    unit_library: UnitLibrary = field(default_factory=UnitLibrary)

    # --- ACON v8.1 additions ---

    # Task type profiles registry — controls per-category compaction behaviour
    task_type_profiles: TaskTypeProfiles = field(default_factory=TaskTypeProfiles)

    # Cost-per-token tracker — records compaction cost efficiency
    cost_tracker: CostPerTokenTracker = field(default_factory=CostPerTokenTracker)

    # Estimated cost to run a cheap compaction model (USD per token)
    _compaction_model_cost_per_token: float = 0.000_001

    # ---

    # Speculation cache: tool_name -> list of predicted messages
    _speculation_cache: dict[str, list[Message]] = field(default_factory=dict)
    # Speculation hit counter for cache stats
    _speculation_hits: int = 0
    _speculation_misses: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress(
        self,
        messages: list[Message],
        target_ratio: float | None = None,
        task_type: str | None = None,
    ) -> list[Message]:
        """Compress a conversation history to a target token ratio.

        Strategy:
        1. Protect the system message (if configured).
        2. Always keep the ``keep_recent`` most recent non-system turns.
        3. Score remaining messages by estimated value weight.
        4. Remove or truncate the lowest-weight messages until the target
           ratio is met.

        **ACON integration (v8.1):** When ``task_type`` is provided, the
        method also looks up the :class:`TaskTypeProfile` for that task
        type. If the profile says ``protect_code``, messages containing
        code blocks are given a higher weight. If the profile says
        ``keep_citations``, messages with citation patterns are protected.
        Cost-per-token is recorded via the ``cost_tracker``.

        Args:
            messages:     List of conversation turns.
            target_ratio: Desired ratio of output tokens to input tokens
                          (0.0 to 1.0). Falls back to the policy for the
                          given task_type, then to 0.6.
            task_type:    Optional task type to look up the policy and profile.

        Returns:
            Compressed message list.
        """
        if not messages:
            return messages

        # Resolve target ratio
        if target_ratio is None and task_type is not None:
            policy = self._get_policy(task_type)
            target_ratio = policy.target_ratio
        elif target_ratio is None:
            target_ratio = 0.6

        policy = (
            self._get_policy(task_type)
            if task_type
            else ContextPolicy()
        )

        # --- ACON v8.1: look up task type profile ---
        profile: TaskTypeProfile | None = None
        if task_type is not None:
            profile = self.task_type_profiles.get_by_task_type(task_type)

        # Estimate tokens before compression
        total_tokens_before = sum(
            _estimate_tokens(m.get("content", "")) for m in messages
        )

        # Phase 1: identify protected messages
        protected_indices: set[int] = set()
        system_idx: int | None = None

        for i, msg in enumerate(messages):
            if msg.get("role") == "system" and policy.protect_system:
                protected_indices.add(i)
                system_idx = i
                break  # only one system message expected

        # Phase 2: protect recent turns
        non_system = [
            i for i in range(len(messages))
            if i not in protected_indices
        ]
        recent_count = min(policy.keep_recent, len(non_system))
        for idx in non_system[-recent_count:]:
            protected_indices.add(idx)

        # Phase 2.5 (ACON): protect code blocks and citations from profile
        if profile is not None:
            for i, msg in enumerate(messages):
                if i in protected_indices:
                    continue
                content = msg.get("content", "")
                if profile.protect_code and "```" in content:
                    protected_indices.add(i)
                    continue
                if profile.keep_citations and self._has_citation(content):
                    protected_indices.add(i)

        # Phase 3: score and trim unprotected messages
        unprotected = [
            i for i in range(len(messages))
            if i not in protected_indices
        ]

        # Estimate current token count
        total_tokens = sum(_estimate_tokens(m.get("content", "")) for m in messages)
        target_tokens = max(1, int(total_tokens * target_ratio))

        # Score unprotected messages (lower = better to remove/truncate)
        scored: list[tuple[int, float]] = [
            (i, _compute_message_weight(messages[i]))
            for i in unprotected
        ]
        scored.sort(key=lambda x: x[1])  # lowest weight first

        # Compute tokens from protected messages
        protected_tokens = sum(
            _estimate_tokens(messages[i].get("content", ""))
            for i in protected_indices
        )

        # Budget for unprotected content
        budget = target_tokens - protected_tokens

        result = {i: messages[i] for i in protected_indices}

        # Greedy: keep highest-weight unprotected messages that fit in budget
        # Process scored in reverse (highest weight first for keep decisions)
        for idx, weight in reversed(scored):
            msg_tokens = _estimate_tokens(result.get(idx, messages[idx]).get("content", ""))
            if budget >= msg_tokens:
                result[idx] = messages[idx]
                budget -= msg_tokens
            elif weight < 0.5:
                # Low-value message: drop entirely
                continue
            else:
                # Medium value: truncate
                content = messages[idx].get("content", "")
                truncated = self._truncate_content(content, budget)
                result[idx] = {**messages[idx], "content": truncated}
                budget = 0

        # Reconstruct in original order
        compressed = [result[i] for i in range(len(messages)) if i in result]

        # --- ACON v8.1: record cost per token ---
        total_tokens_after = sum(
            _estimate_tokens(m.get("content", "")) for m in compressed
        )
        estimated_op_cost = (
            total_tokens_before * self._compaction_model_cost_per_token
        )
        self.cost_tracker.record(
            strategy=policy.compaction_strategy,
            tokens_before=total_tokens_before,
            tokens_after=total_tokens_after,
            estimated_cost=estimated_op_cost,
            task_type=task_type or "unknown",
        )

        return compressed

    def evolve_context(
        self,
        task_type: str,
        feedback: dict[str, Any],
    ) -> ContextPolicy:
        """Learn and refine the optimal compaction policy for a task type.

        Feedback keys:
        - ``success`` (bool): Whether the compressed context led to a
          successful outcome.
        - ``latency_reduction`` (float): Measured latency improvement from
          0.0 (none) to 1.0 (maximum).
        - ``accuracy_loss`` (float): Estimated loss in output quality from
          0.0 (none) to 1.0 (total).

        Policy adjustments:
        - On success with good latency -> increase target_ratio (compress more).
        - On failure or accuracy loss -> decrease target_ratio (keep more),
          lower keep_recent.
        - Repeated success -> shift compaction_strategy toward more aggressive.

        **ACON integration (v8.1):** The method also updates the
        :class:`TaskTypeProfile` for the given task type. A high-quality
        compaction score (``feedback.get("compaction_quality", 0.0)``)
        reinforces the current profile settings; a low score triggers a
        profile adjustment (e.g. reducing summarization aggressiveness).

        Args:
            task_type: The task category to evolve the policy for.
            feedback:  Dict with success, latency_reduction, accuracy_loss
                       and optionally ``compaction_quality`` (0.0-1.0).

        Returns:
            The updated ContextPolicy for this task type.
        """
        policy = self._get_policy(task_type)
        success = feedback.get("success", True)
        latency = feedback.get("latency_reduction", 0.0)
        accuracy_loss = feedback.get("accuracy_loss", 0.0)

        if success and latency > 0.3 and accuracy_loss < 0.1:
            # Good outcome: we can compress more aggressively
            policy.target_ratio = max(0.2, policy.target_ratio - 0.05)
            policy.keep_recent = max(2, policy.keep_recent - 1)

            # Eventually shift strategy
            if policy.target_ratio < 0.4:
                policy.compaction_strategy = CompactionStrategy.AGGRESSIVE
            elif policy.target_ratio < 0.55:
                policy.compaction_strategy = CompactionStrategy.BALANCED

        elif not success or accuracy_loss > 0.2:
            # Bad outcome: be more conservative
            policy.target_ratio = min(1.0, policy.target_ratio + 0.1)
            policy.keep_recent = min(10, policy.keep_recent + 2)

            if policy.target_ratio > 0.7:
                policy.compaction_strategy = CompactionStrategy.VERBOSE

        # Record as an experience unit for future reference
        unit = TypedExperienceUnit(
            unit_id=f"policy-{task_type}-{datetime.now(timezone.utc).isoformat()}",
            unit_type=ExperienceUnitType.STRATEGY,
            content=f"policy={policy.to_dict()} | feedback={feedback}",
            source="evolution",
            task_type=task_type,
            score=1.0 if success else 0.0,
        )
        self.unit_library.add(unit)

        # Store the updated policy
        self.policies[task_type] = policy

        # --- ACON v8.1: update task type profile based on feedback ---
        self._update_task_type_profile(task_type, feedback)

        return policy

    # ------------------------------------------------------------------
    # ACON v8.1 — Task type profile learning
    # ------------------------------------------------------------------

    def get_compaction_quality_scores(
        self,
        task_type: str,
    ) -> list[float]:
        """Return historical compaction quality scores for a task type.

        Scans the unit library for strategy units of the given task type
        and extracts their scores (1.0 = perfect compaction).

        Args:
            task_type: The task type key.

        Returns:
            List of quality scores.
        """
        units = self.unit_library.find_by_task(task_type)
        return [u.score for u in units if u is not None]

    def learn_profile_from_feedback(
        self,
        task_type: str,
        feedback: dict[str, Any],
    ) -> TaskTypeProfile:
        """Learn and update the task type profile for *task_type* using
        compaction quality feedback.

        If the feedback indicates good compaction quality, the profile's
        summarization aggressiveness is increased. If quality is poor,
        it is decreased and code protection may be enabled.

        Args:
            task_type: The task type key (e.g. ``"code_review"``).
            feedback:  Dict with at least ``compaction_quality`` (0.0-1.0).

        Returns:
            The updated (or new) TaskTypeProfile.
        """
        profile = self.task_type_profiles.get_by_task_type(task_type)
        quality = feedback.get("compaction_quality", 0.5)

        # Adjust summarization aggressiveness based on quality feedback
        if quality >= 0.8:
            # Good compaction: can increase aggressiveness
            new_agg = min(1.0, profile.summarization_aggressiveness + 0.05)
        elif quality >= 0.5:
            new_agg = profile.summarization_aggressiveness
        else:
            # Poor compaction: reduce aggressiveness
            new_agg = max(0.0, profile.summarization_aggressiveness - 0.1)

        # For code tasks with poor quality, enable code protection
        base_pt = self.task_type_profiles._TASK_TYPE_MAP.get(
            task_type, ProfileType.GENERAL,
        )
        protect_code = profile.protect_code
        if base_pt == ProfileType.CODE and quality < 0.4:
            protect_code = True

        updated = TaskTypeProfile(
            profile_type=profile.profile_type,
            protect_code=protect_code,
            summarization_aggressiveness=new_agg,
            keep_citations=profile.keep_citations,
            default_target_ratio=profile.default_target_ratio,
            description=profile.description,
        )
        self.task_type_profiles.update_profile(updated)
        return updated

    # ------------------------------------------------------------------
    # ACON helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _has_citation(content: str) -> bool:
        """Check if content contains citation-like patterns.

        Matches patterns like ``[1]``, ``[Author, 2023]``, ``(Author, 2023)``,
        ``https://doi.org/...``.
        """
        import re
        return bool(
            re.search(r"\[\d+\]", content)
            or re.search(r"\[.*?\d{4}\]", content)
            or re.search(r"\(.*?\d{4}\)", content)
            or "doi.org" in content
            or "arxiv" in content.lower()
        )

    # ------------------------------------------------------------------

    def speculate(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> list[Message]:
        """Pre-compute likely next context segments for a tool call.

        Uses the speculation cache to return predicted next turns without
        recomputing. On cache miss, generates a best-guess prediction.

        Args:
            tool_name:  The tool being called.
            tool_input: The input arguments for the tool.

        Returns:
            Predicted next messages (typically an assistant thought turn or
            a user request turn).
        """
        cache_key = f"{tool_name}:{sorted(tool_input.items())[:3]}"

        cached = self._speculation_cache.get(cache_key)
        if cached is not None:
            self._speculation_hits += 1
            return cached

        self._speculation_misses += 1

        # Generate speculative context based on tool name
        predicted = self._build_prediction(tool_name, tool_input)
        self._speculation_cache[cache_key] = predicted

        # Limit cache size to avoid unbounded growth
        if len(self._speculation_cache) > 200:
            # Evict oldest entry
            oldest = next(iter(self._speculation_cache))
            del self._speculation_cache[oldest]

        return predicted

    def speculation_stats(self) -> dict[str, Any]:
        """Return hit/miss statistics for the speculation cache.

        Returns:
            Dict with hits, misses, hit_rate, cache_size.
        """
        total = self._speculation_hits + self._speculation_misses
        hit_rate = (
            round(self._speculation_hits / total, 3)
            if total > 0
            else 0.0
        )
        return {
            "hits": self._speculation_hits,
            "misses": self._speculation_misses,
            "hit_rate": hit_rate,
            "cache_size": len(self._speculation_cache),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_policy(self, task_type: str | None) -> ContextPolicy:
        """Retrieve the policy for a task type, creating a default if needed.

        Args:
            task_type: The task type key.

        Returns:
            The ContextPolicy for that task type.
        """
        if task_type is None:
            return ContextPolicy()
        if task_type not in self.policies:
            self.policies[task_type] = ContextPolicy()
        return self.policies[task_type]

    def _update_task_type_profile(
        self,
        task_type: str,
        feedback: dict[str, Any],
    ) -> None:
        """Update the task type profile based on feedback.

        Uses the ``compaction_quality`` key from feedback (if present) to
        adjust the profile. Falls back to the ``success`` key.

        Args:
            task_type: The task type key.
            feedback:  Feedback dict from ``evolve_context``.
        """
        if "compaction_quality" not in feedback and "success" not in feedback:
            return  # nothing to learn from

        # Derive quality from feedback
        if "compaction_quality" in feedback:
            quality = feedback["compaction_quality"]
        else:
            quality = 1.0 if feedback.get("success", True) else 0.0

        quality_feedback = {"compaction_quality": quality}
        self.learn_profile_from_feedback(task_type, quality_feedback)

    @staticmethod
    def _truncate_content(content: str, budget_tokens: int) -> str:
        """Truncate content to fit within a token budget.

        Keeps the beginning and end of the content, removing the middle,
        to preserve context framing.

        Args:
            content:       Original content string.
            budget_tokens: Maximum allowed tokens.

        Returns:
            Truncated content string.
        """
        current_tokens = _estimate_tokens(content)
        if current_tokens <= budget_tokens:
            return content

        # Target character count
        budget_chars = budget_tokens * 4
        if budget_chars >= len(content):
            return content

        # Keep the first 1/3 and last 1/3 of the budget, drop the middle
        first_part_end = max(1, budget_chars // 3)
        last_part_start = len(content) - max(1, budget_chars // 3)

        if first_part_end >= last_part_start:
            # Very short budget: just take the beginning
            return content[:budget_chars] + f"\n{_TRUNCATION_MARKER}\n"

        truncated = (
            content[:first_part_end]
            + f"\n{_TRUNCATION_MARKER}\n"
            + content[last_part_start:]
        )
        return truncated

    def _build_prediction(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> list[Message]:
        """Build a speculative next-turn prediction for a tool call.

        Args:
            tool_name:  The tool being called.
            tool_input: The input arguments.

        Returns:
            Predicted assistant messages for the likely next turns.
        """
        # Map tool names to likely next patterns
        prediction_map: dict[str, str] = {
            "grep_search": "Search results received. Synthesizing findings.",
            "read_file": "File content read. Extracting relevant sections.",
            "web_search": "Web search results received. Compiling information.",
            "bash": "Command executed. Analyzing output.",
            "write_file": "File written successfully. Verifying correctness.",
            "edit_file": "File edited. Validating changes.",
        }

        thought = prediction_map.get(
            tool_name,
            f"Tool {tool_name} completed. Processing results.",
        )

        return [
            {
                "role": "assistant",
                "content": thought,
            },
        ]


__all__ = [
    "AdaptiveContextFabric",
    "ContextPolicy",
    "CostPerTokenRecord",
    "CostPerTokenTracker",
    "ProfileType",
    "TaskTypeProfile",
    "TaskTypeProfiles",
]
