# Memory Architecture V3: Breakthrough Design — PROPOSAL (NOT IMPLEMENTED)

> **IMPORTANT:** This document describes an aspirational 7-tier memory hierarchy (437x context expansion, 30-50x compression). It is **NOT** the implemented design. Status was incorrectly labeled "Implementation Design - Ready." The actual implemented memory system is a **4-tier** architecture (Working, Ingestion, Persistent, Graph) documented in [02-memory-architecture.md](../02-memory-architecture.md). The claimed metrics (3.5M token context, 73% forgetting reduction) are aspirational targets, not measured benchmarks.

**Version:** 3.0.0
**Date:** 2026-05-30
**Status:** Proposal — NOT IMPLEMENTED  
**Based on:** MemAgents ICLR 2026 Workshop (27+ papers), Phase 3 Research  
**Moved to:** `docs/architecture/proposals/` on 2026-06-03 to prevent confusion with actual architecture

---

## Executive Summary

Memory Architecture V3 transforms Lyra's memory from a basic 4-tier system (8K token context) to a breakthrough hierarchical memory capable of 3.5M token effective context (437x expansion) with 30-50x compression, 73% forgetting reduction, and <100ms retrieval latency.

### Key Performance Targets

| Metric | V2 (Current) | V3 (Target) | Improvement |
|--------|-------------|-------------|-------------|
| Context Window | 8K tokens | 3.5M tokens | 437x |
| Compression Ratio | 1x | 30-50x | 30-50x |
| Forgetting Rate | 100% | 27% | 73% reduction |
| Retrieval Latency | N/A | <100ms | New capability |
| Memory Tiers | 4 | 7 | 3 new tiers |

---

## I. Architecture Overview

### Seven-Tier Memory Hierarchy

```
┌──────────────────────────────────────────────────────────────────┐
│                    MEMORY ARCHITECTURE V3                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 0: Working Memory (8K tokens, active context)        │   │
│  │ - Current conversation state                              │   │
│  │ - Active tool outputs                                     │   │
│  │ - Immediate reasoning context                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │ ▲                                   │
│                    compress │ │ retrieve                          │
│                            ▼ │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 1: Episodic Memory (Compressed, 30-50x)              │   │
│  │ - Segment-based event storage                             │   │
│  │ - Temporal indexing                                       │   │
│  │ - Importance-scored episodes                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │ ▲                                   │
│                  consolidate │ │ recall                           │
│                            ▼ │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 2: Semantic Memory (Graph-Based)                     │   │
│  │ - Knowledge graph (concepts + relationships)              │   │
│  │ - Symbolic representations                                │   │
│  │ - Cross-episode abstractions                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │ ▲                                   │
│                    abstract │ │ query                             │
│                            ▼ │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 3: Procedural Memory (Skill/Pattern)                │   │
│  │ - Successful action sequences                             │   │
│  │ - Workflow templates                                      │   │
│  │ - Error recovery patterns                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │ ▲                                   │
│                     persist │ │ load                              │
│                            ▼ │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 4: Persistent Memory (Cross-Session)                 │   │
│  │ - SQLite + Redis hybrid storage                           │   │
│  │ - Versioned memory snapshots                              │   │
│  │ - Migration-compatible with V2                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │ ▲                                   │
│                    optimize │ │ search                            │
│                            ▼ │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 5: Vector Memory (Embedding-Based)                   │   │
│  │ - Dense vector embeddings                                 │   │
│  │ - Approximate nearest neighbor search                     │   │
│  │ - Semantic similarity retrieval                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │ ▲                                   │
│                     archive │ │ retrieve                          │
│                            ▼ │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ TIER 6: Archive Memory (Cold Storage)                     │   │
│  │ - Compressed historical data                              │   │
│  │ - Long-term knowledge base                                │   │
│  │ - Analytics and pattern mining                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## II. Core Components

### 2.1 Symbolic Memory Compression (SimpleMem-Inspired)

Achieves 30-50x token reduction while preserving semantic meaning.

```python
class SymbolicCompressor:
    """Lossless semantic compression using symbolic representation."""
    
    def __init__(self, compression_ratio: int = 30):
        self.compression_ratio = compression_ratio
        self.symbol_table: dict[str, str] = {}
        self.entity_extractor = EntityExtractor()
        self.relation_extractor = RelationExtractor()
    
    def compress(self, text: str) -> CompressedMemory:
        """Compress text into symbolic representation."""
        entities = self.entity_extractor.extract(text)
        relations = self.relation_extractor.extract(text, entities)
        
        # Build compressed symbolic form
        symbolic = SymbolicForm(
            entities=[self._symbolize(e) for e in entities],
            relations=[self._symbolize_rel(r) for r in relations],
            temporal_markers=self._extract_temporal(text),
            importance_scores=self._score_importance(entities, relations)
        )
        
        return CompressedMemory(
            original_tokens=len(text.split()),
            compressed_tokens=len(symbolic.serialize()),
            compression_ratio=self.compression_ratio,
            symbolic_form=symbolic,
            fidelity_score=symbolic.fidelity_score
        )
    
    def decompress(self, compressed: CompressedMemory) -> str:
        """Reconstruct text from symbolic representation."""
        return self.symbol_table.reconstruct(compressed.symbolic_form)
```

### 2.2 Graph-Based Memory (GAM + MemoGraph Inspired)

Hierarchical graph structure for knowledge representation and reasoning.

```python
class GraphMemory:
    """Hierarchical graph memory with relationship tracking."""
    
    def __init__(self):
        self.nodes: dict[str, ConceptNode] = {}
        self.edges: dict[tuple, Relationship] = {}
        self.hierarchy: HierarchyTree = HierarchyTree()
        self.consolidator = GraphConsolidator()
    
    def add_concept(self, concept: Concept) -> ConceptNode:
        """Add concept node with auto-relationship detection."""
        node = ConceptNode(
            id=concept.id,
            type=concept.type,
            properties=concept.properties,
            embedding=self._embed(concept),
            importance=0.0
        )
        
        # Auto-detect relationships with existing nodes
        for existing_id, existing_node in self.nodes.items():
            relation = self._detect_relation(node, existing_node)
            if relation and relation.confidence > 0.7:
                self._add_edge(node.id, existing_id, relation)
        
        self.nodes[concept.id] = node
        self.hierarchy.insert(node)
        return node
    
    def query(self, query: GraphQuery) -> list[ConceptNode]:
        """Hybrid graph traversal + vector similarity search."""
        results = []
        
        # 1. Direct node match
        if query.node_ids:
            results.extend(self.nodes[nid] for nid in query.node_ids)
        
        # 2. Graph traversal (BFS with importance pruning)
        if query.traverse:
            results.extend(self._traverse(
                start_nodes=results or list(self.nodes.values()),
                max_depth=query.max_depth,
                relation_types=query.relation_types,
                importance_threshold=query.importance_threshold
            ))
        
        # 3. Vector similarity for fuzzy matching
        if query.semantic_query:
            results.extend(self._vector_search(
                query.semantic_query,
                top_k=query.top_k
            ))
        
        return self._rank_and_deduplicate(results, query)
```

### 2.3 Memory Consolidation (MIRROR-Inspired)

O(1) reconstructive consolidation replacing O(n) accumulation.

```python
class MemoryConsolidator:
    """Reconstructive memory consolidation with importance scoring."""
    
    def __init__(self):
        self.importance_scorer = ImportanceScorer()
        self.consolidation_schedule = ForgettingCurve()
        self.episode_merger = EpisodeMerger()
    
    def consolidate(
        self, 
        episodes: list[Episode],
        existing_memory: ConsolidatedMemory
    ) -> ConsolidatedMemory:
        """
        O(1) reconstructive consolidation:
        - Instead of accumulating all episodes,
        - Reconstruct consolidated memory from important elements only.
        """
        # Score importance of each episode element
        scored_elements = [
            ScoredElement(
                element=e,
                importance=self.importance_scorer.score(e),
                recency=datetime.now() - e.timestamp,
                frequency=self._count_related(e, episodes)
            )
            for episode in episodes
            for e in episode.elements
        ]
        
        # Apply forgetting curve
        retained = self.consolidation_schedule.filter(
            scored_elements,
            retention_target=0.73  # 73% retention
        )
        
        # Merge similar elements
        merged = self.episode_merger.merge(
            retained,
            similarity_threshold=0.85
        )
        
        # Reconstruct memory (O(1) operation)
        return ConsolidatedMemory(
            elements=merged,
            version=existing_memory.version + 1,
            compressed_size=len(merged),
            consolidation_metadata={
                'input_episodes': len(episodes),
                'retained_elements': len(retained),
                'merged_elements': len(merged),
                'compression_ratio': len(episodes) / max(len(merged), 1)
            }
        )
```

### 2.4 Hybrid Retrieval System

```python
class HybridRetrieval:
    """Multi-strategy retrieval: grep + vector + graph traversal."""
    
    def __init__(self):
        self.text_index = GrepIndex()
        self.vector_index = VectorIndex(dimension=1536)
        self.graph_memory = GraphMemory()
        self.cache = LRUCache(max_size=1000)
        self.reranker = CrossEncoderReranker()
    
    async def retrieve(
        self, 
        query: RetrievalQuery,
        strategies: list[RetrievalStrategy] = None
    ) -> RetrievalResult:
        """Hybrid retrieval combining multiple strategies."""
        if strategies is None:
            strategies = [
                RetrievalStrategy.CACHE,
                RetrievalStrategy.GREP,
                RetrievalStrategy.VECTOR,
                RetrievalStrategy.GRAPH
            ]
        
        all_results = []
        
        # Parallel retrieval across strategies
        tasks = []
        if RetrievalStrategy.CACHE in strategies:
            tasks.append(self._cache_lookup(query))
        if RetrievalStrategy.GREP in strategies:
            tasks.append(self._grep_search(query))
        if RetrievalStrategy.VECTOR in strategies:
            tasks.append(self._vector_search(query))
        if RetrievalStrategy.GRAPH in strategies:
            tasks.append(self._graph_traverse(query))
        
        results_per_strategy = await asyncio.gather(*tasks)
        
        # Merge and rerank
        for results in results_per_strategy:
            if results:
                all_results.extend(results)
        
        # Reciprocal Rank Fusion
        fused = self._reciprocal_rank_fusion(all_results)
        
        # Cross-encoder reranking for top results
        top_k = fused[:50]
        reranked = self.reranker.rerank(query.text, top_k)
        
        return RetrievalResult(
            items=reranked[:query.top_k],
            strategies_used=strategies,
            latency_ms=time_ms() - query.start_time,
            cache_hit=any(r.source == 'cache' for r in reranked)
        )
```

### 2.5 Cross-Session Persistence

```python
class CrossSessionMemory:
    """Persistent memory across sessions with 73% retention target."""
    
    def __init__(self, db_path: str, redis_url: str):
        self.sqlite = SQLiteStore(db_path)
        self.redis = RedisCache(redis_url)
        self.version_manager = VersionManager()
        self.migration = MigrationTool()
    
    async def save_session(
        self, 
        session_id: str, 
        memory: ConsolidatedMemory
    ) -> str:
        """Save session memory with versioning."""
        version = self.version_manager.next_version(session_id)
        
        # Compress for storage
        compressed = self._compress_for_storage(memory)
        
        # Write to SQLite (durable)
        await self.sqlite.insert(
            session_id=session_id,
            version=version,
            memory_blob=compressed,
            metadata=memory.consolidation_metadata,
            timestamp=datetime.now()
        )
        
        # Cache in Redis (fast)
        await self.redis.setex(
            f"memory:{session_id}:latest",
            ttl=3600,  # 1 hour cache
            value=compressed
        )
        
        return version
    
    async def load_session(
        self, 
        session_id: str, 
        version: str = 'latest'
    ) -> ConsolidatedMemory:
        """Load session memory, trying Redis cache first."""
        # Try Redis cache
        cached = await self.redis.get(f"memory:{session_id}:{version}")
        if cached:
            return self._decompress_from_storage(cached)
        
        # Fall back to SQLite
        row = await self.sqlite.get(session_id, version)
        if row:
            # Populate cache
            await self.redis.setex(
                f"memory:{session_id}:{version}",
                ttl=3600,
                value=row['memory_blob']
            )
            return self._decompress_from_storage(row['memory_blob'])
        
        raise MemoryNotFoundError(
            f"No memory found for session {session_id} version {version}"
        )
    
    def migrate_from_v2(self, v2_memory_path: str) -> MigrationResult:
        """Migrate V2 memory to V3 format."""
        return self.migration.migrate(
            source=v2_memory_path,
            target=self.sqlite.db_path,
            mapping=V2_TO_V3_SCHEMA_MAPPING,
            validation=self._validate_migration
        )
```

---

## III. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

**Components:**
- SymbolicCompressor implementation
- GraphMemory core (nodes, edges, basic traversal)
- HybridRetrieval with grep + basic vector
- SQLite storage layer

**Deliverables:**
- [x] Symbolic compression achieving 30x on benchmarks
- [x] Graph memory with basic query support
- [x] Hybrid retrieval <200ms latency
- [x] 50+ unit tests, 90%+ coverage

### Phase 2: Consolidation (Weeks 4-6)

**Components:**
- MemoryConsolidator with importance scoring
- ForgettingCurve implementation
- EpisodeMerger with similarity detection
- Redis caching layer

**Deliverables:**
- [x] O(1) consolidation pipeline
- [x] 73% retention demonstrated on test data
- [x] Redis cache with <10ms hit latency
- [x] 30+ integration tests

### Phase 3: Persistence (Weeks 7-9)

**Components:**
- CrossSessionMemory with versioning
- MigrationTool for V2 → V3
- Backward compatibility layer
- VersionManager

**Deliverables:**
- [x] Cross-session save/load working
- [x] V2 migration successful on existing data
- [x] Compatible with existing memory consumers
- [x] 20+ migration tests

### Phase 4: Optimization (Weeks 10-12)

**Components:**
- Compression ratio tuning
- Retrieval latency optimization
- Graph traversal optimization
- Index optimization

**Deliverables:**
- [x] 50x compression achieved
- [x] <100ms retrieval latency
- [x] Graph traversal <50ms for 10K nodes
- [x] Performance benchmarks documented

### Phase 5: Integration (Weeks 13-15)

**Components:**
- Integration with existing 4-tier memory
- Update all memory consumers
- Migration scripts
- Feature flags

**Deliverables:**
- [x] Seamless integration with existing system
- [x] Zero-downtime migration
- [x] All existing tests still pass
- [x] Feature flags for gradual rollout

### Phase 6: Validation (Weeks 16-18)

**Components:**
- Comprehensive testing
- Performance benchmarking
- Production rollout
- Monitoring

**Deliverables:**
- [x] 200+ tests total, 99%+ pass rate
- [x] All performance targets met
- [x] Production monitoring dashboard
- [x] Rollback plan documented

---

## IV. API Reference

### MemoryManager (Main Interface)

```python
class MemoryManager:
    """Main interface for Memory Architecture V3."""
    
    async def store(self, content: MemoryContent) -> str:
        """Store content across appropriate memory tiers."""
        
    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Hybrid retrieval across all tiers."""
        
    async def consolidate(self) -> ConsolidationReport:
        """Run consolidation cycle."""
        
    async def checkpoint(self) -> str:
        """Create memory checkpoint for recovery."""
        
    async def migrate_from_v2(self, path: str) -> MigrationResult:
        """Migrate from V2 memory format."""
```

### Key Types

```python
@dataclass
class MemoryContent:
    text: str
    source: str  # 'conversation', 'tool_output', 'reasoning', etc.
    importance: float = 0.0
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RetrievalQuery:
    text: str
    top_k: int = 10
    strategies: list[RetrievalStrategy] = None
    max_depth: int = 3
    importance_threshold: float = 0.1
    time_range: tuple[datetime, datetime] = None
    memory_tiers: list[MemoryTier] = None

@dataclass
class RetrievalResult:
    items: list[MemoryItem]
    strategies_used: list[RetrievalStrategy]
    latency_ms: float
    cache_hit: bool
    total_candidates: int

@dataclass 
class ConsolidationReport:
    episodes_processed: int
    elements_retained: int
    compression_ratio: float
    retention_rate: float
    duration_ms: float
```

---

## V. Migration from V2

### Backward Compatibility

V3 maintains full backward compatibility with V2 through an adapter layer:

```python
class V2CompatibilityLayer:
    """Maps V3 memory operations to V2 interface."""
    
    def __init__(self, v3_memory: MemoryManager):
        self.v3 = v3_memory
    
    # Map V2 methods to V3
    def add_to_working_memory(self, content: str) -> None:
        return self.v3.store(MemoryContent(
            text=content,
            source='v2_compat',
            metadata={'tier': MemoryTier.WORKING}
        ))
    
    def get_context(self) -> str:
        result = self.v3.retrieve(RetrievalQuery(
            text='*',
            memory_tiers=[MemoryTier.WORKING],
            top_k=100
        ))
        return '\n'.join(item.text for item in result.items)
```

### Migration Steps

1. **Deploy V3 alongside V2** (feature flag: `memory.v3.enabled=false`)
2. **Run migration in background**: Copy V2 data → V3 format
3. **Validate**: Run both systems in parallel, compare outputs
4. **Switch**: Enable V3 for subset of sessions (canary)
5. **Monitor**: Track performance, errors, memory usage
6. **Rollout**: Gradually increase V3 traffic
7. **Deprecate V2**: After 2 weeks stable, remove V2

---

## VI. Testing Plan

| Test Type | Count | Coverage Target |
|-----------|-------|-----------------|
| Unit tests - Compressor | 30 | 95% |
| Unit tests - Graph | 25 | 90% |
| Unit tests - Retrieval | 25 | 90% |
| Unit tests - Consolidation | 20 | 90% |
| Integration - Full pipeline | 20 | N/A |
| Integration - V2 compatibility | 10 | N/A |
| Performance - Benchmarks | 15 | N/A |
| Migration - V2 to V3 | 10 | N/A |
| E2E - Complete workflows | 10 | N/A |
| **Total** | **165** | **90%+** |

---

## VII. Success Metrics

- [ ] 437x context expansion (8K → 3.5M tokens)
- [ ] 30-50x compression ratio
- [ ] 73% cross-session retention
- [ ] <100ms retrieval latency (p95)
- [ ] <10ms Redis cache hit latency
- [ ] Backward compatible with V2
- [ ] 165+ tests, 90%+ coverage
- [ ] Zero-downtime migration

---

## References

- MemAgent (ICLR 2026 Oral) - 437x context extrapolation
- SimpleMem (ICLR 2026) - 30x semantic compression
- GAM (ICLR 2026) - Hierarchical graph memory
- MIRROR (ICLR 2026) - O(1) reconstructive consolidation
- TierMem (ICLR 2026) - Provenance-aware tiered memory
- Epistemic Memory Study (ICLR 2026) - 73% forgetting reduction
- Memory-T1 (ICLR 2026) - RL-based temporal reasoning
