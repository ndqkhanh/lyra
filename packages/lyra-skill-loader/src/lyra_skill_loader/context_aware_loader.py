"""Context-Budget-Aware Loading — decide what to load, what to evict, and whether it fits."""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from lyra_skill_loader.tiered_loader import LoadedSkill, LoadTier, TieredLoader

if TYPE_CHECKING:
    from collections.abc import Sequence


class EvictionPolicy(Enum):
    """Policy used to select skills for eviction when budget is exceeded."""

    LRU = auto()
    LFU = auto()
    PRIORITY = auto()
    FIFO = auto()


@dataclass(frozen=True)
class ContextBudget:
    """Current context window budget state."""

    total_tokens: int
    used_tokens: int = 0
    available_tokens: int = field(init=False)
    reserved_for_skills: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "available_tokens",
            self.total_tokens - self.used_tokens,
        )

    @property
    def effective_skill_budget(self) -> int:
        """Tokens available for skills after reserving a portion."""
        return int(self.available_tokens * (1 - self.reserved_for_skills / 100.0))


@dataclass(frozen=True)
class LoadDecision:
    """Decision about whether to load a skill and at what tier."""

    skill_id: str
    load_tier: LoadTier
    estimated_tokens: int
    fits_in_budget: bool


@dataclass(frozen=True)
class BudgetConfig:
    """Configuration for context-aware loading decisions."""

    max_skill_tokens: int = 2000
    reserve_percent: float = 0.2
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU


@dataclass(frozen=True)
class LoadPlan:
    """Plan detailing what to load and evict to stay within budget."""

    to_load: tuple[LoadDecision, ...]
    to_evict: tuple[str, ...]
    estimated_tokens_after: int


class ContextAwareLoader:
    """Makes budget-aware loading and eviction decisions.

    Works in concert with :class:`TieredLoader` by deciding which skills
    should be loaded, at what tier, and which skills should be evicted
    when the context budget is exceeded.
    """

    def __init__(
        self,
        tiered_loader: TieredLoader,
        budget: ContextBudget | None = None,
        config: BudgetConfig | None = None,
    ) -> None:
        self._loader = tiered_loader
        self._budget = budget or ContextBudget(total_tokens=4096)
        self._config = config or BudgetConfig()
        # OrderedDict for LRU/FIFO tracking (insertion order)
        self._loaded_order: OrderedDict[str, float] = OrderedDict()

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    @property
    def budget(self) -> ContextBudget:
        return self._budget

    def set_budget(self, new_budget: ContextBudget) -> None:
        self._budget = new_budget

    def update_used_tokens(self, used: int) -> None:
        """Update the used token count in the budget."""
        total = self._budget.total_tokens
        reserved = self._budget.reserved_for_skills
        self._budget = ContextBudget(
            total_tokens=total,
            used_tokens=used,
            reserved_for_skills=reserved,
        )

    # ------------------------------------------------------------------
    # Feasibility checks
    # ------------------------------------------------------------------

    def can_load(self, skill_id: str, budget: ContextBudget | None = None) -> bool:
        """Check whether a skill fits in the given budget at any tier."""
        b = budget or self._budget
        available = b.effective_skill_budget
        entry = self._loader.get_entry(skill_id)
        if entry is None:
            return False
        return entry.metadata.estimated_tokens <= available

    def can_load_at_tier(
        self,
        skill_id: str,
        tier: LoadTier,
        budget: ContextBudget | None = None,
    ) -> bool:
        """Check whether a skill fits at a specific tier."""
        b = budget or self._budget
        available = b.effective_skill_budget
        return tier.estimated_tokens <= available

    # ------------------------------------------------------------------
    # Decision making
    # ------------------------------------------------------------------

    def decide_loading(
        self,
        matches: Sequence[tuple[str, float, LoadTier]],
        budget: ContextBudget | None = None,
    ) -> list[LoadDecision]:
        """Create an optimal loading plan from ranked matches.

        Args:
            matches: Sequence of ``(skill_id, score, suggested_tier)`` tuples,
                     typically from :meth:`TriggerMatcher.rank_matches`.
            budget: Optional budget override. Defaults to current budget.

        Returns:
            List of load decisions, one per match.
        """
        b = budget or self._budget
        available = b.effective_skill_budget
        decisions: list[LoadDecision] = []
        running_total = 0

        for skill_id, _score, suggested_tier in matches:
            if running_total >= available:
                decisions.append(
                    LoadDecision(
                        skill_id=skill_id,
                        load_tier=suggested_tier,
                        estimated_tokens=suggested_tier.estimated_tokens,
                        fits_in_budget=False,
                    )
                )
                continue

            tier = self._select_tier(skill_id, suggested_tier, available - running_total)
            tokens = tier.estimated_tokens
            fits = running_total + tokens <= available

            if fits:
                running_total += tokens

            decisions.append(
                LoadDecision(
                    skill_id=skill_id,
                    load_tier=tier,
                    estimated_tokens=tokens,
                    fits_in_budget=fits,
                )
            )

        return decisions

    def plan_loading(
        self,
        matches: Sequence[tuple[str, float, LoadTier]],
        budget: ContextBudget | None = None,
    ) -> LoadPlan:
        """Create a complete load plan with eviction recommendations."""
        b = budget or self._budget
        decisions = self.decide_loading(matches, b)

        to_load = tuple(d for d in decisions if d.fits_in_budget)
        token_needed = sum(d.estimated_tokens for d in decisions if not d.fits_in_budget)

        to_evict: tuple[str, ...] = ()
        if token_needed > 0:
            loaded_skills = self._get_currently_loaded()
            to_evict = self.evict_if_needed(
                loaded_skills, token_needed, self._config.eviction_policy
            )

        total_after = b.used_tokens + sum(d.estimated_tokens for d in to_load)
        total_after -= sum(self._loader.estimate_tokens(sid) for sid in to_evict)

        return LoadPlan(
            to_load=to_load,
            to_evict=to_evict,
            estimated_tokens_after=max(0, total_after),
        )

    # ------------------------------------------------------------------
    # Eviction
    # ------------------------------------------------------------------

    def evict_if_needed(
        self,
        loaded: Sequence[str],
        budget_needed: int,
        policy: EvictionPolicy = EvictionPolicy.LRU,
    ) -> tuple[str, ...]:
        """Return a list of skill ids to evict to free *budget_needed* tokens.

        Args:
            loaded: Currently loaded skill ids.
            budget_needed: Number of tokens to free up.
            policy: Eviction policy to use.

        Returns:
            Tuple of skill ids to evict.
        """
        if budget_needed <= 0 or not loaded:
            return ()

        scored: list[tuple[str, float]] = []

        for sid in loaded:
            if policy == EvictionPolicy.LRU:
                entry = self._loader.get_entry(sid)
                score = entry.last_access if entry and entry.last_access > 0 else 0.0
            elif policy == EvictionPolicy.LFU:
                entry = self._loader.get_entry(sid)
                score = float(entry.load_count) if entry else 0.0
            elif policy == EvictionPolicy.PRIORITY:
                entry = self._loader.get_entry(sid)
                score = float(entry.priority) if entry else 0.0
            elif policy == EvictionPolicy.FIFO:
                score = self._loaded_order.get(sid, 0.0)
            else:
                score = 0.0

            scored.append((sid, score))

        # Sort by policy: LRU/PRIORITY ascending (least recent/lowest first)
        # LFU ascending (least used first), FIFO ascending (oldest first)
        scored.sort(key=lambda x: x[1])

        evicted: list[str] = []
        freed = 0

        for sid, _score in scored:
            if freed >= budget_needed:
                break
            tokens = self._loader.estimate_tokens(sid)
            evicted.append(sid)
            freed += tokens

        return tuple(evicted)

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    def apply_plan(self, plan: LoadPlan) -> tuple[list[LoadedSkill], list[str]]:
        """Execute a load plan against the tiered loader.

        Returns:
            ``(loaded_skills, evicted_skill_ids)``
        """
        # Evict first
        for sid in plan.to_evict:
            if sid in self._loader.list_skills():
                self._loader.unload_to_tier1(sid)

        # Load
        loaded: list[LoadedSkill] = []
        for decision in plan.to_load:
            if not decision.fits_in_budget:
                continue
            ls = self._loader.load_at_tier(decision.skill_id, decision.load_tier)
            loaded.append(ls)

        return loaded, list(plan.to_evict)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_tier(
        self,
        skill_id: str,
        suggested: LoadTier,
        available_tokens: int,
    ) -> LoadTier:
        """Choose the highest feasible tier given available tokens."""
        entry = self._loader.get_entry(skill_id)
        if entry is None:
            return LoadTier.TIER1_METADATA

        tiers = [LoadTier.TIER3_REFERENCES, LoadTier.TIER2_CONTENT, LoadTier.TIER1_METADATA]
        for tier in tiers:
            if (
                tier.tier_number <= suggested.tier_number
                and tier.estimated_tokens <= available_tokens
            ):
                return tier

        return LoadTier.TIER1_METADATA

    def _get_currently_loaded(self) -> list[str]:
        """Return list of skill ids that are loaded above tier 1."""
        loaded: list[str] = []
        for sid in self._loader.list_skills():
            tier = self._loader.get_current_tier(sid)
            if tier and tier != LoadTier.TIER1_METADATA:
                loaded.append(sid)
        return loaded

    def track_load(self, skill_id: str) -> None:
        """Track a skill access for LRU-based eviction ordering."""
        self._loaded_order[skill_id] = time.time()
