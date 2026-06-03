# Memory System Architecture Tradeoffs

## Core Design Decisions

### 1. Hybrid Search: SQLite FTS5 + Chroma Vector DB

#### Decision
Use **both** keyword search (FTS5) and semantic search (Chroma), fusing results with Reciprocal Rank Fusion (RRF).

#### Alternatives Considered

**Option A: FTS5 Only**
- ✅ Pros: Simple, fast, deterministic, zero dependencies
- ❌ Cons: Misses semantic matches ("auth bug" won't match "authentication failure")
- ❌ Cons: Requires exact keyword overlap

**Option B: Chroma Only**
- ✅ Pros: Semantic understanding, handles synonyms
- ❌ Cons: Slower (embedding + vector search), non-deterministic
- ❌ Cons: Poor on exact keyword matches ("PostgreSQL 17" vs "Postgres 16")
- ❌ Cons: Requires embedding model

**Option C: Elasticsearch**
- ✅ Pros: Battle-tested, hybrid search built-in, scales horizontally
- ❌ Cons: Heavy infra (JVM, separate process), overkill for single-user
- ❌ Cons: Poor local-first story

**Option D: LanceDB / Qdrant**
- ✅ Pros: Modern vector DBs, good hybrid support
- ❌ Cons: Less mature, Chroma has better Python ecosystem
- ❌ Cons: LanceDB lacks FTS (2023)

#### Why Hybrid Won

| Scenario | FTS5 | Chroma | Hybrid |
|----------|------|--------|--------|
| Exact keyword ("pytest") | ✅ | ⚠️ | ✅ |
| Semantic match ("test framework") | ❌ | ✅ | ✅ |
| Mixed query ("python auth bug") | ⚠️ | ⚠️ | ✅ |
| Determinism | ✅ | ❌ | ⚠️ |
| Latency (cold) | 10ms | 80ms | 90ms |
| Latency (warm) | 5ms | 30ms | 35ms |

**Outcome**: Hybrid covers both strengths, RRF fusion is parameter-free and resilient.

### 2. SQLite as Source of Truth (not Chroma)

#### Decision
**SQLite** is the authoritative store; Chroma is a best-effort index.

#### Rationale
- **Atomicity**: SQLite transactions are ACID; Chroma writes can fail
- **Consistency**: FTS5 trigger keeps keyword index in perfect sync
- **Durability**: SQLite WAL mode prevents corruption
- **Repairability**: Can rebuild Chroma from SQLite at any time

#### Cost
- **Write amplification**: Every write goes to SQLite + Chroma
- **Reconciliation overhead**: Daily drift checker

#### Mitigation
- Async Chroma writes (don't block agent)
- Write-ahead log inspection on startup
- `lyra mem reembed` command for full rebuild

### 3. Three-Tier Partitioning (Procedural/Episodic/Semantic)

#### Decision
Separate knowledge by **how it's used**, not by storage backend.

#### Alternatives Considered

**Option A: Flat Storage (All in SQLite)**
- ✅ Pros: Simple schema, single source of truth
- ❌ Cons: Skills mixed with observations, hard to query efficiently
- ❌ Cons: No semantic separation (procedures ≠ facts ≠ events)

**Option B: Separate Databases**
- ✅ Pros: Complete isolation, independent scaling
- ❌ Cons: Cross-tier joins impossible, complex multi-DB transactions
- ❌ Cons: No unified search

**Option C: Two Tiers (Short-term / Long-term)**
- ✅ Pros: Simpler mental model
- ❌ Cons: Doesn't distinguish episodic vs semantic vs procedural
- ❌ Cons: All long-term knowledge competes for same context budget

#### Why Three Tiers Won

| Tier | Access Pattern | Update Frequency | Lifespan |
|------|---------------|------------------|----------|
| Procedural | Low-frequency, high-value | Manual refinement | Permanent |
| Episodic | High-frequency, temporal | Every session | 365 days |
| Semantic | Medium-frequency, durable | Agentic wiki | 90 days (TTL) |

Different access patterns demand different indexing, pruning, and caching strategies.

### 4. Local Embedding (BGE-small-en-v1.5) vs Cloud APIs

#### Decision
**Default to local** CPU embedding; cloud is opt-in.

#### Alternatives Considered

**Option A: OpenAI `text-embedding-3-small`**
- ✅ Pros: Better quality, 1536-dim, faster (GPU)
- ❌ Cons: API cost ($0.02/1M tokens), privacy leak, requires internet
- ❌ Cons: Vendor lock-in

**Option B: Cohere / Voyage**
- ✅ Pros: High quality, specialized models
- ❌ Cons: Same privacy/cost concerns

**Option C: Larger local model (BGE-large, 335M params)**
- ✅ Pros: Better quality
- ❌ Cons: 10x slower on CPU, requires GPU for real-time

#### Why BGE-small-en-v1.5 Won

| Metric | BGE-small | text-embedding-3-small | BGE-large |
|--------|-----------|------------------------|-----------|
| Params | 33M | ? (closed) | 335M |
| Dimensions | 384 | 1536 | 1024 |
| Throughput (CPU) | ~100 docs/s | - | ~10 docs/s |
| Quality (MTEB) | 58.4 | ~62 | 63.2 |
| Privacy | ✅ Local | ❌ Cloud | ✅ Local |
| Cost | Free | $0.02/1M tok | Free |

**Outcome**: Good-enough quality, fast CPU inference, zero privacy leak, zero cost.

### 5. Reciprocal Rank Fusion (RRF) with k=60

#### Decision
Fuse FTS5 + Chroma results with RRF, not weighted linear combination.

#### Alternatives Considered

**Option A: Weighted Linear Combination**
```python
score = alpha * fts_score + (1-alpha) * chroma_score
```
- ✅ Pros: Simple, tunable
- ❌ Cons: Requires normalization (FTS scores ≠ Chroma scores)
- ❌ Cons: Hyperparameter `alpha` needs per-query tuning

**Option B: Rank-based Voting (Borda Count)**
- ✅ Pros: Aggregates ranks, not scores
- ❌ Cons: Ties are common, needs tiebreaker

**Option C: Learning-to-Rank (LambdaMART)**
- ✅ Pros: Optimal fusion with training data
- ❌ Cons: Requires labeled relevance data (don't have)
- ❌ Cons: Complex, slow inference

#### Why RRF Won

**Formula**:
```python
score(item) = sum over engines of 1 / (k + rank_in_that_engine)
```

| Property | RRF | Weighted | LTR |
|----------|-----|----------|-----|
| Hyperparameters | 1 (k) | 1 (alpha) | Many |
| Score normalization | ❌ Not needed | ✅ Required | ✅ Required |
| Robustness to garbage | ✅ High | ⚠️ Medium | ⚠️ Medium |
| Training data | ❌ None | ❌ None | ✅ Required |

**Outcome**: k=60 is standard in IR literature; works well without tuning.

### 6. Progressive Disclosure (3-tool MCP surface)

#### Decision
Force agent to **search → get snippet → fetch full** instead of preloading memory.

#### Alternatives Considered

**Option A: Preload Top-K at Session Start**
- ✅ Pros: Agent has context immediately
- ❌ Cons: Wastes tokens on irrelevant memories
- ❌ Cons: Context budget exhausted before user prompt

**Option B: Auto-inject Memory on Every Turn**
- ✅ Pros: Agent always has relevant context
- ❌ Cons: Context pollution (agent sees outdated info)
- ❌ Cons: High token cost

**Option C: Single `memory.query` Tool (no get)**
- ✅ Pros: Simpler API
- ❌ Cons: Must return full content → wastes tokens on false positives

#### Why Progressive Disclosure Won

| Approach | Tokens per turn | Agent control | False positive cost |
|----------|----------------|---------------|---------------------|
| Preload top-10 | 5000+ | ❌ None | High |
| Auto-inject | 2000+ | ❌ None | High |
| Single query tool | 1000+ | ⚠️ Limited | Medium |
| 3-tool progressive | 200-500 | ✅ Full | Low |

**Outcome**: Agent decides what to fetch; snippets act as preview; tokens saved.

### 7. Pruner as Background Job (not LRU cache)

#### Decision
Run **tiered pruner** every N sessions (default 15) instead of LRU eviction.

#### Alternatives Considered

**Option A: LRU Cache (Fixed Capacity)**
- ✅ Pros: Simple, automatic
- ❌ Cons: Important but old memories evicted
- ❌ Cons: No user control

**Option B: Manual Pruning Only**
- ✅ Pros: User has full control
- ❌ Cons: Users forget; DB grows unbounded
- ❌ Cons: Performance degrades silently

**Option C: TTL on Every Memory**
- ✅ Pros: Automatic expiration
- ❌ Cons: All memories decay equally (wrong for important facts)
- ❌ Cons: Hard to predict when critical knowledge disappears

#### Why Tiered Pruner Won

**Tiers**:
1. **Keep**: High utility, recent (importance ≥ 0.7, accessed < 30d)
2. **Watch**: Lower utility (importance 0.3-0.7)
3. **Archive**: Stale, low utility (importance < 0.3, accessed > 180d)
4. **Delete**: Garbage / superseded

| Approach | Granularity | Control | Predictability |
|----------|-------------|---------|----------------|
| LRU | None | ❌ | ❌ |
| Manual | Full | ✅ | ⚠️ |
| TTL | Per-memory | ⚠️ | ⚠️ |
| Tiered | Per-tier + per-memory | ✅ | ✅ |

**Outcome**: First run is dry-run; user reviews before applying; gradual decay.

### 8. Immutability: Copy-on-Write vs In-Place Updates

#### Decision
**In-place updates** for memory objects (mutate `importance`, `tags`).

#### Rationale
- **Memory is NOT code**: Immutability is critical for code (avoid side effects), less so for data
- **Decay requires mutation**: Importance decay happens frequently (daily)
- **Conflict resolution**: In-place updates simplify concurrency (single-writer SQLite)

#### Cost
- **Harder to audit**: Can't see history of importance changes
- **Concurrency risk**: Multi-threaded access needs locks

#### Mitigation
- **Trace events**: Every write emits a `memory.write` span (audit log)
- **SQLite is single-writer**: No multi-writer concurrency
- **Snapshot before pruning**: Dry-run shows what will change

### 9. Schema Evolution: Migrations vs Rebuild

#### Decision
**Explicit migrations** with version tracking (not rebuild-from-scratch).

#### Alternatives Considered

**Option A: Rebuild on Schema Change**
- ✅ Pros: Simple (just delete DB)
- ❌ Cons: Lose all user memories
- ❌ Cons: Unacceptable for production

**Option B: Schema-on-Read (NoSQL style)**
- ✅ Pros: Flexible, no migrations
- ❌ Cons: Consistency issues, hard to query
- ❌ Cons: FTS5 requires fixed schema

#### Why Migrations Won

**Approach**:
```sql
CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
-- On startup: check version, run migrations
```

| Approach | Data loss | Consistency | Complexity |
|----------|-----------|-------------|------------|
| Rebuild | ❌ Total | ✅ | ✅ Low |
| Schema-on-read | ❌ None | ❌ | ⚠️ High |
| Migrations | ❌ None | ✅ | ⚠️ Medium |

**Outcome**: Alembic-style versioned migrations; never lose data.

### 10. Privacy: Opt-in vs Opt-out

#### Decision
Privacy is **opt-in per observation** (`is_private=True`).

#### Alternatives Considered

**Option A: All Private by Default**
- ✅ Pros: Maximum privacy
- ❌ Cons: Agent can't learn from past sessions (defeats purpose)
- ❌ Cons: User must whitelist everything

**Option B: User-level Toggle**
- ✅ Pros: Simple
- ❌ Cons: All-or-nothing (can't mark specific secrets)

#### Why Per-Observation Won

| Approach | Granularity | Friction | Auditability |
|----------|-------------|----------|--------------|
| All private | None | High | Low |
| User toggle | Session | Medium | Medium |
| Per-observation | Observation | Low | High |

**Outcome**: `<private>` tag or `is_private=True` for sensitive data; default is shareable.

## Performance vs Cost Tradeoffs

### Latency vs Quality
- **Write latency**: 50-200ms (embedding) vs 10ms (keyword-only)
- **Tradeoff**: Accepted for semantic search quality
- **Mitigation**: Async embedding, warm cache

### Storage vs Searchability
- **Chroma overhead**: ~2x SQLite size (vectors + metadata)
- **Tradeoff**: Worth it for semantic search
- **Mitigation**: Pruner limits growth

### Privacy vs Convenience
- **Local embedding**: Slower (100 docs/s) vs cloud (1000+ docs/s)
- **Tradeoff**: Zero privacy leak
- **Mitigation**: Batch embedding, GPU opt-in

## Maintenance Burden Tradeoffs

### Complexity Added
- **Two storage backends**: SQLite + Chroma (vs just SQLite)
- **Reconciliation**: Daily drift checker (vs single source)
- **Embedding model**: Must track version, migrations

### Complexity Avoided
- **No separate service**: Embedded DB (vs Elasticsearch/Qdrant server)
- **No labeled data**: RRF fusion (vs learning-to-rank)
- **No schema drift**: Migrations (vs schema-on-read)

## Future-Proofing Decisions

### 1. Pluggable Embedding Provider
**Config**:
```yaml
memory.embedding.provider: local | openai | cohere | voyage
```
**Rationale**: Users can upgrade quality without code changes

### 2. Hybrid Ranking Weights
**Config**:
```yaml
memory.search.hybrid_weight: 0.5  # 0=FTS only, 1=Chroma only
```
**Rationale**: Can tune per-user without re-ranking algorithm change

### 3. Chroma as Swappable Backend
**Interface**: `EmbeddingStore` protocol
**Rationale**: Can swap to LanceDB/Qdrant without touching core logic

## Lessons Learned

### What Worked Well
1. **Hybrid search**: Covers both keyword + semantic strengths
2. **Progressive disclosure**: Saves tokens, gives agent control
3. **Local-first**: Zero privacy leak, zero cost
4. **Tiered pruning**: Users trust it (dry-run first)

### What We'd Change
1. **Chroma stability**: Occasional drift requires reconciler
2. **Embedding speed**: CPU is slow; GPU opt-in would help
3. **FTS5 tokenization**: Porter stemmer misses some technical terms (e.g., "PostgreSQL" → "postgresql")

### What's Still Open
1. **Knowledge graph**: Wiki entries reference each other; formalize as graph?
2. **Multi-repo sharing**: User has 20 repos; cross-repo wiki is powerful but privacy-sensitive
3. **Embedding drift**: Model updates change vectors; when to re-embed?
