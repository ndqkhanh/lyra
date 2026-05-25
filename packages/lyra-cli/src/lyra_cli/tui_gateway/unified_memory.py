"""Unified memory orchestrator — wires L0-L3 tiers, UltraMemory, KG, and token index.

L0 (Working) → L1 (Episodic) → L2 (Semantic) → L3 (Procedural + KG)
With UltraMemory consolidation, ACT-R decay, and dream cycles.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Aggregated stats across all memory tiers."""

    working_entries: int = 0
    working_tokens: int = 0
    episodic_events: int = 0
    semantic_facts: int = 0
    procedural_count: int = 0
    kg_nodes: int = 0
    kg_edges: int = 0
    token_index_docs: int = 0
    token_index_bytes: int = 0
    total_memories: int = 0
    active_memories: int = 0
    dormant_memories: int = 0
    last_consolidation: float = 0.0
    budget_status: str = "unknown"


@dataclass
class MemoryQueryResult:
    """Unified result from cross-tier memory query."""

    tier: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedMemoryOrchestrator:
    """Orchestrates all memory tiers with automatic consolidation and retrieval.

    Provides a single API across:
      - Working memory (L0) — transient, high-priority, limited capacity
      - Episodic memory (L1) — session-based event recording
      - Semantic memory (L2) — facts, knowledge, embeddings
      - Procedural memory (L3) — procedures, skills, KG entries
      - UltraMemory — ACT-R activation/decay, budget, consolidation
      - Knowledge Graph — entity/relation graph
      - Token-Native Index — lightweight no-embedding retrieval
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = Path(db_path) if db_path != ":memory:" else Path(":memory:")
        self._lock = threading.Lock()
        self._initialized = False
        self._wm = None
        self._em = None
        self._sm = None
        self._pm = None
        self._ultra = None
        self._kg = None
        self._token_index = None
        self._query_count: int = 0
        self._write_count: int = 0

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> None:
        """Lazy-init all memory subsystems. Idempotent."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            from lyra_memory_stack.working_memory import WorkingMemory
            from lyra_memory_stack.episodic_memory import EpisodicMemory
            from lyra_memory_stack.semantic_memory import SemanticMemory
            from lyra_memory_stack.procedural_memory import ProceduralMemory

            self._wm = WorkingMemory()
            self._em = EpisodicMemory(
                db_path=str(self._db_path / "episodic.db")
                if self._db_path != Path(":memory:")
                else ":memory:"
            )
            self._sm = SemanticMemory()
            self._pm = ProceduralMemory()

            try:
                from lyra_memory.ultra_system import UltraMemorySystem
                self._ultra = UltraMemorySystem(self._db_path)
            except Exception:
                logger.warning("UltraMemorySystem not available, using L0-L3 only")

            try:
                from lyra_knowledge_graph.graph_builder import GraphBuilder
                self._kg = GraphBuilder()
            except Exception:
                logger.warning("KnowledgeGraph not available")

            try:
                from lyra_memory_token import TokenNativeIndex
                self._token_index = TokenNativeIndex()
            except Exception:
                logger.warning("TokenNativeIndex not available")

            self._initialized = True

    def _ensure_init(self) -> None:
        if not self._initialized:
            self.initialize()

    # ── Write APIs ─────────────────────────────────────────────────

    def write_working(self, content: str, priority: float = 1.0) -> str:
        """Store in L0 working memory (synchronous wrapper)."""
        self._ensure_init()
        return asyncio.run(self._wm.add(content, priority=priority))

    def write_episodic(
        self, session_id: str, event_type: str, content: str, tags: tuple[str, ...] = ()
    ) -> int:
        self._ensure_init()
        return asyncio.run(
            self._em.record_event(session_id, event_type, content, tags=tags)
        )

    def write_semantic(
        self,
        content: str,
        category: str = "knowledge",
        confidence: float = 1.0,
        source: str = "unknown",
    ) -> str:
        self._ensure_init()
        import numpy as np

        embedding = np.random.randn(384).astype(np.float32)  # placeholder
        return asyncio.run(
            self._sm.store(
                content,
                embedding,
                category=category,
                confidence=confidence,
                source=source,
            )
        )

    def write_procedural(
        self,
        name: str,
        description: str,
        steps: list[str],
        triggers: tuple[str, ...] = (),
    ) -> str:
        self._ensure_init()
        return asyncio.run(
            self._pm.register_procedure(
                name, description, steps, triggers=triggers
            )
        )

    def write_kg_node(
        self, node_id: str, label: str, node_type: str = "concept", confidence: float = 1.0
    ) -> None:
        self._ensure_init()
        if self._kg:
            asyncio.run(
                self._kg.add_node(node_id, label, node_type=node_type, confidence=confidence)
            )

    def write_kg_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str = "relates_to",
        confidence: float = 1.0,
    ) -> None:
        self._ensure_init()
        if self._kg:
            asyncio.run(
                self._kg.add_edge(source_id, target_id, relation=relation, confidence=confidence)
            )

    def write_ultra(
        self, content: str, scope: str = "session", memory_type: str = "fact"
    ) -> Any:
        self._ensure_init()
        if self._ultra:
            from lyra_memory.ultra_system import MemoryScope, MemoryType

            scope_map = {
                "session": MemoryScope.SESSION,
                "project": MemoryScope.PROJECT,
                "global": MemoryScope.GLOBAL,
            }
            type_map = {
                "fact": MemoryType.FACT,
                "procedure": MemoryType.PROCEDURE,
                "episode": MemoryType.EPISODE,
                "insight": MemoryType.INSIGHT,
            }
            return self._ultra.write(
                content,
                scope=scope_map.get(scope, MemoryScope.SESSION),
                type=type_map.get(memory_type, MemoryType.FACT),
            )
        return None

    def index_document(self, doc_id: str, text: str) -> None:
        self._ensure_init()
        if self._token_index:
            self._token_index.index(doc_id, text)

    # ── Read APIs ─────────────────────────────────────────────────

    def query(
        self,
        query: str,
        *,
        top_k: int = 10,
        tiers: tuple[str, ...] = ("working", "episodic", "semantic", "token"),
    ) -> list[MemoryQueryResult]:
        """Cross-tier query returning unified results."""
        self._ensure_init()
        results: list[MemoryQueryResult] = []
        self._query_count += 1

        if "working" in tiers and self._wm:
            try:
                entries = asyncio.run(self._wm.get_all())
                for e in entries[:top_k]:
                    if query.lower() in e.content.lower():
                        results.append(
                            MemoryQueryResult(
                                tier="L0_working",
                                content=e.content,
                                score=e.priority,
                            )
                        )
            except Exception:
                pass

        if "episodic" in tiers and self._em:
            try:
                events = asyncio.run(self._em.search(query, limit=top_k))
                for ev in events[:top_k]:
                    results.append(
                        MemoryQueryResult(
                            tier="L1_episodic",
                            content=ev.content,
                            score=0.8,
                            metadata={"event_type": ev.event_type},
                        )
                    )
            except Exception:
                pass

        if "semantic" in tiers and self._sm:
            try:
                import numpy as np

                q_embedding = np.random.randn(384).astype(np.float32)
                hits = asyncio.run(
                    self._sm.search(q_embedding, query_text=query, top_k=top_k)
                )
                for h in hits[:top_k]:
                    results.append(
                        MemoryQueryResult(
                            tier="L2_semantic",
                            content=h.fact.content if hasattr(h, "fact") else str(h),
                            score=float(h.similarity) if hasattr(h, "similarity") else 0.7,
                        )
                    )
            except Exception:
                pass

        if "token" in tiers and self._token_index:
            try:
                token_results = self._token_index.retrieve(query, top_k=top_k)
                for doc_id, score in token_results[:top_k]:
                    doc = self._token_index.get_document(doc_id)
                    if doc:
                        results.append(
                            MemoryQueryResult(
                                tier="token_index",
                                content=doc,
                                score=score,
                                metadata={"doc_id": doc_id},
                            )
                        )
            except Exception:
                pass

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def query_kg(
        self, node_type: str | None = None, label_contains: str | None = None
    ) -> list[dict[str, Any]]:
        self._ensure_init()
        if not self._kg:
            return []
        nodes = asyncio.run(
            self._kg.query_nodes(
                node_type=node_type, label=label_contains
            )
        )
        return [
            {"id": n.node_id, "label": n.label, "type": n.node_type, "confidence": n.confidence}
            for n in nodes[:20]
        ]

    # ── Consolidation ──────────────────────────────────────────────

    def consolidate(self, deep: bool = False) -> dict[str, Any]:
        """Run consolidation across all tiers."""
        self._ensure_init()
        result: dict[str, Any] = {"deep": deep, "actions": []}

        if self._ultra:
            try:
                cr = self._ultra.consolidate(deep=deep)
                result["ultra"] = {
                    "consolidated": cr.consolidated_count
                    if hasattr(cr, "consolidated_count")
                    else 0,
                    "pruned": cr.pruned_count if hasattr(cr, "pruned_count") else 0,
                }
                result["actions"].append("ultra_consolidation")
            except Exception as exc:
                result["ultra_error"] = str(exc)

        return result

    def dream_cycle(self) -> dict[str, Any]:
        """Run one dream cycle — offline enrichment and pruning."""
        self._ensure_init()
        result: dict[str, Any] = {}
        try:
            from lyra_knowledge_graph.dream_cycle import KGDreamCycle

            if self._kg:
                dream = KGDreamCycle(self._kg)
                asyncio.run(dream.run_cycle())
                result["kg_dream"] = "completed"
        except Exception as exc:
            result["kg_dream_error"] = str(exc)

        try:
            from lyra_memory_stack.dream_cycle import DreamCycle

            if self._wm and self._sm:
                dc = DreamCycle(self._wm, self._sm)
                asyncio.run(dc.run())
                result["memory_dream"] = "completed"
        except Exception as exc:
            result["memory_dream_error"] = str(exc)

        return result

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> MemoryStats:
        """Aggregated statistics across all memory tiers."""
        self._ensure_init()
        s = MemoryStats()

        if self._wm:
            try:
                s.working_entries = self._wm.size
                s.working_tokens = asyncio.run(self._wm.estimate_tokens())
            except Exception:
                pass

        if self._em:
            try:
                s.episodic_events = asyncio.run(self._em.count())
            except Exception:
                pass

        if self._sm:
            s.semantic_facts = self._sm.size

        if self._pm:
            s.procedural_count = self._pm.procedure_count
            s.kg_nodes = self._pm.kg_node_count

        if self._kg:
            try:
                summary = asyncio.run(
                    self._kg.query_nodes()
                ) if hasattr(self._kg, "query_nodes") else []
                s.kg_nodes = len(summary) if isinstance(summary, list) else 0
            except Exception:
                pass

        if self._token_index:
            try:
                s.token_index_docs = len(self._token_index.stats)
                s.token_index_bytes = self._token_index.memory_footprint_bytes
            except Exception:
                pass

        if self._ultra:
            try:
                ms = self._ultra.get_stats()
                s.total_memories = ms.total_memories
                s.active_memories = ms.active_memories
                s.dormant_memories = ms.dormant_memories
                s.last_consolidation = ms.last_consolidation
                s.budget_status = ms.budget_status
            except Exception:
                pass

        return s

    def snapshot(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "db_path": str(self._db_path),
            "queries": self._query_count,
            "writes": self._write_count,
            "stats": self.stats(),
        }

    def close(self) -> None:
        if self._ultra:
            try:
                self._ultra.close()
            except Exception:
                pass
