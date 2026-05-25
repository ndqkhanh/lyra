"""3-layer progressive disclosure retrieval (Claude-Mem pattern).

Layer1: Compact index (~50-100 tokens per result) — id, title, type, date
Layer2: Timeline context (~200-500 tokens) — summary + surrounding context
Layer3: Full observation detail (full content)

RetrievalManager orchestrates across all memory layers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from lyra_memory_stack.episodic_memory import EpisodicMemory, EpisodeEvent, SearchResult
from lyra_memory_stack.semantic_memory import SemanticMemory, Fact, FactQueryResult
from lyra_memory_stack.procedural_memory import ProceduralMemory, Skill, WorkflowTemplate
from lyra_memory_stack.working_memory import WorkingMemory, ContextItem


@dataclass(frozen=True)
class Layer1Index:
    """Compact index entry (~50-100 tokens)."""

    entry_id: str
    title: str
    entry_type: str  # "episodic", "semantic", "procedural", "working"
    date: float
    summary: str = ""
    relevance_score: float = 0.0


@dataclass(frozen=True)
class Layer2Timeline:
    """Timeline context entry (~200-500 tokens)."""

    entry_id: str
    title: str
    entry_type: str
    context_summary: str
    surrounding_entries: tuple[Layer1Index, ...] = ()
    timestamp: float = 0.0
    agent_id: str = ""


@dataclass(frozen=True)
class Layer3Detail:
    """Full observation detail."""

    entry_id: str
    entry_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    full_record: Any = None  # The original record object


class RetrievalManager:
    """Orchestrates progressive disclosure retrieval across memory layers.

    Provides a three-layer retrieval pipeline:
    1. Search returns compact indices (Layer1)
    2. Expand an index entry into timeline context (Layer2)
    3. Drill down into full detail (Layer3)
    """

    _working_memory: WorkingMemory | None
    _episodic_memory: EpisodicMemory | None
    _semantic_memory: SemanticMemory | None
    _procedural_memory: ProceduralMemory | None

    def __init__(
        self,
        working_memory: WorkingMemory | None = None,
        episodic_memory: EpisodicMemory | None = None,
        semantic_memory: SemanticMemory | None = None,
        procedural_memory: ProceduralMemory | None = None,
    ) -> None:
        self._working_memory = working_memory
        self._episodic_memory = episodic_memory
        self._semantic_memory = semantic_memory
        self._procedural_memory = procedural_memory

    # ── Layer 1: Compact Index ──────────────────────────────────────────

    def search_index(
        self,
        query: str,
        include_types: tuple[str, ...] = ("episodic", "semantic", "procedural", "working"),
        limit_per_type: int = 5,
    ) -> list[Layer1Index]:
        """Layer 1: Search across all memory layers and return compact indices."""
        results: list[Layer1Index] = []

        if "working" in include_types and self._working_memory is not None:
            wm_results = self._search_working_index(query, limit_per_type)
            results.extend(wm_results)

        if "episodic" in include_types and self._episodic_memory is not None:
            ep_results = self._search_episodic_index(query, limit_per_type)
            results.extend(ep_results)

        if "semantic" in include_types and self._semantic_memory is not None:
            sem_results = self._search_semantic_index(query, limit_per_type)
            results.extend(sem_results)

        if "procedural" in include_types and self._procedural_memory is not None:
            proc_results = self._search_procedural_index(query, limit_per_type)
            results.extend(proc_results)

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    def _search_working_index(self, query: str, limit: int) -> list[Layer1Index]:
        assert self._working_memory is not None
        query_lower = query.lower()
        results: list[Layer1Index] = []
        for item in self._working_memory.items():
            score = 0.5 if query_lower in item.content.lower() else 0.0
            results.append(Layer1Index(
                entry_id=item.item_id,
                title=item.content[:60],
                entry_type="working",
                date=item.timestamp,
                summary=item.content[:100],
                relevance_score=score,
            ))
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def _search_episodic_index(self, query: str, limit: int) -> list[Layer1Index]:
        assert self._episodic_memory is not None
        search_results = self._episodic_memory.search(query, limit=limit)
        return [
            Layer1Index(
                entry_id=r.event.event_id,
                title=f"[{r.event.event_type}] {r.event.content[:60]}",
                entry_type="episodic",
                date=r.event.timestamp,
                summary=r.snippet,
                relevance_score=r.rank,
            )
            for r in search_results
        ]

    def _search_semantic_index(self, query: str, limit: int) -> list[Layer1Index]:
        assert self._semantic_memory is not None
        query_results = self._semantic_memory.query_facts(query, limit=limit)
        return [
            Layer1Index(
                entry_id=r.fact.fact_id,
                title=r.fact.statement[:60],
                entry_type="semantic",
                date=r.fact.timestamp,
                summary=f"[{r.fact.domain}] {r.fact.statement[:100]}",
                relevance_score=r.score,
            )
            for r in query_results
        ]

    def _search_procedural_index(self, query: str, limit: int) -> list[Layer1Index]:
        assert self._procedural_memory is not None
        query_lower = query.lower()
        results: list[Layer1Index] = []

        for skill in self._procedural_memory.list_skills():
            score = 0.4 if query_lower in skill.name.lower() or query_lower in skill.description.lower() else 0.0
            results.append(Layer1Index(
                entry_id=skill.skill_id,
                title=skill.name,
                entry_type="procedural",
                date=skill.timestamp,
                summary=skill.description[:100],
                relevance_score=score,
            ))

        for wf in self._procedural_memory.list_workflows():
            score = 0.4 if query_lower in wf.name.lower() or query_lower in wf.description.lower() else 0.0
            results.append(Layer1Index(
                entry_id=wf.workflow_id,
                title=wf.name,
                entry_type="procedural",
                date=wf.timestamp,
                summary=wf.description[:100],
                relevance_score=score,
            ))

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    # ── Layer 2: Timeline Context ───────────────────────────────────────

    def get_timeline(self, entry_id: str, entry_type: str = "", depth: int = 3) -> Layer2Timeline | None:
        """Layer 2: Expand an index entry into its timeline context."""
        if entry_type in ("", "episodic") and self._episodic_memory is not None:
            return self._build_episodic_timeline(entry_id, depth)
        if entry_type in ("", "semantic") and self._semantic_memory is not None:
            return self._build_semantic_timeline(entry_id, depth)
        if entry_type in ("", "procedural") and self._procedural_memory is not None:
            return self._build_procedural_timeline(entry_id, depth)
        if entry_type in ("", "working") and self._working_memory is not None:
            return self._build_working_timeline(entry_id, depth)
        return None

    def _build_episodic_timeline(self, event_id: str, depth: int) -> Layer2Timeline | None:
        assert self._episodic_memory is not None
        try:
            event = self._episodic_memory.retrieve(event_id)
        except Exception:
            return None

        surrounding: list[Layer1Index] = []
        nearby = self._episodic_memory.query_by_time_range(
            event.timestamp - 10, event.timestamp + 10, limit=depth * 2
        )
        for e in nearby:
            if e.event_id != event_id:
                surrounding.append(Layer1Index(
                    entry_id=e.event_id,
                    title=e.content[:60],
                    entry_type="episodic",
                    date=e.timestamp,
                    relevance_score=0.5,
                ))

        return Layer2Timeline(
            entry_id=event.event_id,
            title=f"[{event.event_type}] {event.content[:60]}",
            entry_type="episodic",
            context_summary=f"Agent '{event.agent_id}' at {event.timestamp}: {event.content[:200]}",
            surrounding_entries=tuple(surrounding[:depth]),
            timestamp=event.timestamp,
            agent_id=event.agent_id,
        )

    def _build_semantic_timeline(self, fact_id: str, depth: int) -> Layer2Timeline | None:
        assert self._semantic_memory is not None
        try:
            fact = self._semantic_memory.get_fact(fact_id)
        except Exception:
            return None

        surrounding: list[Layer1Index] = []
        related = self._semantic_memory.query_facts(fact.statement[:20], limit=depth * 2)
        for r in related:
            if r.fact.fact_id != fact_id:
                surrounding.append(Layer1Index(
                    entry_id=r.fact.fact_id,
                    title=r.fact.statement[:60],
                    entry_type="semantic",
                    date=r.fact.timestamp,
                    summary=f"[{r.fact.domain}] {r.fact.statement[:100]}",
                    relevance_score=r.score,
                ))

        return Layer2Timeline(
            entry_id=fact.fact_id,
            title=fact.statement[:60],
            entry_type="semantic",
            context_summary=f"Domain '{fact.domain}', confidence {fact.confidence:.2f}: {fact.statement[:200]}",
            surrounding_entries=tuple(surrounding[:depth]),
            timestamp=fact.timestamp,
        )

    def _build_procedural_timeline(self, skill_id: str, depth: int) -> Layer2Timeline | None:
        assert self._procedural_memory is not None
        try:
            if skill_id in self._procedural_memory.list_skills():
                skill = self._procedural_memory.load_skill(skill_id)
                return Layer2Timeline(
                    entry_id=skill.skill_id,
                    title=skill.name,
                    entry_type="procedural",
                    context_summary=f"Skill v{skill.version}: {skill.description[:200]}",
                    timestamp=skill.timestamp,
                )
            wf = self._procedural_memory.load_workflow(skill_id)
            return Layer2Timeline(
                entry_id=wf.workflow_id,
                title=wf.name,
                entry_type="procedural",
                context_summary=f"Workflow v{wf.version}: {wf.description[:200]} with {len(wf.steps)} steps",
                timestamp=wf.timestamp,
            )
        except Exception:
            return None

    def _build_working_timeline(self, item_id: str, depth: int) -> Layer2Timeline | None:
        assert self._working_memory is not None
        item = self._working_memory.peek(item_id)
        if item is None:
            return None

        surrounding: list[Layer1Index] = []
        for other in self._working_memory.items()[:depth * 2]:
            if other.item_id != item_id:
                surrounding.append(Layer1Index(
                    entry_id=other.item_id,
                    title=other.content[:60],
                    entry_type="working",
                    date=other.timestamp,
                    relevance_score=other.priority / 10.0,
                ))

        return Layer2Timeline(
            entry_id=item.item_id,
            title=item.content[:60],
            entry_type="working",
            context_summary=f"Priority {item.priority}: {item.content[:200]}",
            surrounding_entries=tuple(surrounding[:depth]),
            timestamp=item.timestamp,
        )

    # ── Layer 3: Full Detail ────────────────────────────────────────────

    def get_detail(self, entry_id: str, entry_type: str = "") -> Layer3Detail | None:
        """Layer 3: Retrieve the full detail for an entry."""
        if entry_type in ("", "episodic") and self._episodic_memory is not None:
            return self._get_episodic_detail(entry_id)
        if entry_type in ("", "semantic") and self._semantic_memory is not None:
            return self._get_semantic_detail(entry_id)
        if entry_type in ("", "procedural") and self._procedural_memory is not None:
            return self._get_procedural_detail(entry_id)
        if entry_type in ("", "working") and self._working_memory is not None:
            return self._get_working_detail(entry_id)
        return None

    def _get_episodic_detail(self, event_id: str) -> Layer3Detail | None:
        assert self._episodic_memory is not None
        try:
            event = self._episodic_memory.retrieve(event_id)
            return Layer3Detail(
                entry_id=event.event_id,
                entry_type="episodic",
                content=event.content,
                metadata={
                    "agent_id": event.agent_id,
                    "event_type": event.event_type,
                    "session_id": event.session_id,
                    "timestamp": event.timestamp,
                    **event.metadata,
                },
                full_record=event,
            )
        except Exception:
            return None

    def _get_semantic_detail(self, fact_id: str) -> Layer3Detail | None:
        assert self._semantic_memory is not None
        try:
            fact = self._semantic_memory.get_fact(fact_id)
            return Layer3Detail(
                entry_id=fact.fact_id,
                entry_type="semantic",
                content=fact.statement,
                metadata={
                    "domain": fact.domain,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "tier": fact.tier.name,
                    "tags": list(fact.tags),
                    "timestamp": fact.timestamp,
                    **fact.metadata,
                },
                full_record=fact,
            )
        except Exception:
            return None

    def _get_procedural_detail(self, entry_id: str) -> Layer3Detail | None:
        assert self._procedural_memory is not None
        try:
            try:
                skill = self._procedural_memory.load_skill(entry_id)
                return Layer3Detail(
                    entry_id=skill.skill_id,
                    entry_type="procedural",
                    content=skill.content,
                    metadata={
                        "name": skill.name,
                        "version": skill.version,
                        "domain": skill.domain,
                        "triggers": list(skill.triggers),
                        "timestamp": skill.timestamp,
                        **skill.metadata,
                    },
                    full_record=skill,
                )
            except MemoryNotFoundError:
                pass
            try:
                wf = self._procedural_memory.load_workflow(entry_id)
                return Layer3Detail(
                    entry_id=wf.workflow_id,
                    entry_type="procedural",
                    content=f"{wf.name}: {wf.description} ({len(wf.steps)} steps)",
                    metadata={
                        "name": wf.name,
                        "version": wf.version,
                        "domain": wf.domain,
                        "steps": len(wf.steps),
                        "timestamp": wf.timestamp,
                    },
                    full_record=wf,
                )
            except MemoryNotFoundError:
                return None
        except Exception:
            return None

    def _get_working_detail(self, item_id: str) -> Layer3Detail | None:
        assert self._working_memory is not None
        item = self._working_memory.peek(item_id)
        if item is None:
            return None
        return Layer3Detail(
            entry_id=item.item_id,
            entry_type="working",
            content=item.content,
            metadata={
                "priority": item.priority,
                "source": item.source,
                "timestamp": item.timestamp,
                "token_estimate": item.token_estimate,
                **item.metadata,
            },
            full_record=item,
        )

    # ── Stats ───────────────────────────────────────────────────────────

    def get_memory_stats(self) -> dict[str, Any]:
        """Get aggregated statistics across all memory layers."""
        stats: dict[str, Any] = {}

        if self._working_memory is not None:
            stats["working"] = self._working_memory.summary()
        if self._episodic_memory is not None:
            stats["episodic"] = {"total_events": self._episodic_memory.count(), "db_path": self._episodic_memory.db_path}
        if self._semantic_memory is not None:
            stats["semantic"] = self._semantic_memory.summary()
        if self._procedural_memory is not None:
            stats["procedural"] = self._procedural_memory.summary()

        return stats
