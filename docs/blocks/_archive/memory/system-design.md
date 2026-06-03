# Memory System: High-Level Design

## Design Philosophy

The memory system follows three core principles:

1. **Progressive Disclosure**: Don't preload memory; let the agent search when needed
2. **Hybrid Intelligence**: Combine keyword + semantic search for robustness
3. **Privacy First**: Local by default, explicit consent for cloud

## System Abstraction Layers

```
┌─────────────────────────────────────────────────────────┐
│  L1: Agent Interface (MCP Tools)                        │
│  → memory.search / timeline / get                       │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  L2: Memory Tiers (Logical Partitions)                  │
│  → Procedural / Episodic / Semantic / Persona           │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  L3: Retrieval Strategies                               │
│  → Keyword (FTS5) / Semantic (Chroma) / Hybrid (RRF)    │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  L4: Storage Backends                                   │
│  → SQLite / FTS5 / Chroma / File System                 │
└─────────────────────────────────────────────────────────┘
```

## Core Abstractions

### 1. Memory Tiers (Logical Separation)

```python
class MemoryTier(Protocol):
    """Abstract interface for memory tiers."""
    
    def search(self, query: str, **filters) -> list[Hit]:
        """Search within this tier."""
        ...
    
    def get(self, id: str) -> Entry | None:
        """Retrieve full entry by ID."""
        ...
    
    def write(self, entry: Entry) -> str:
        """Write entry, return ID."""
        ...
```

**Implementations**:
- `ProceduralTier`: Skills, workflows (file-based)
- `EpisodicTier`: Observations, traces (SQLite + Chroma)
- `SemanticTier`: Facts, wiki (SQLite + Chroma + files)
- `PersonaTier`: SOUL.md (file-based, L2 context)

### 2. Retrieval Strategies (Pluggable Search)

```python
class RetrievalStrategy(Protocol):
    """Abstract search strategy."""
    
    def search(
        self, 
        query: str, 
        limit: int = 5
    ) -> list[ScoredResult]:
        """Return scored results."""
        ...
```

**Implementations**:
- `KeywordRetrieval`: SQLite FTS5 (porter stemming)
- `SemanticRetrieval`: Chroma vector search (cosine similarity)
- `HybridRetrieval`: RRF fusion of keyword + semantic

### 3. Embedding Providers (Swappable Models)

```python
class EmbeddingProvider(Protocol):
    """Abstract embedding service."""
    
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to vectors."""
        ...
    
    @property
    def dimensions(self) -> int:
        """Vector dimensionality."""
        ...
```

**Implementations**:
- `LocalBGEProvider`: BGE-small-en-v1.5 (384-dim, CPU)
- `OpenAIProvider`: text-embedding-3-small (1536-dim)
- `CohereProvider`: embed-english-v3.0

### 4. Storage Backends (Physical Persistence)

```python
class StorageBackend(Protocol):
    """Abstract storage interface."""
    
    def write(self, id: str, data: dict) -> None:
        """Persist data."""
        ...
    
    def read(self, id: str) -> dict | None:
        """Load data."""
        ...
    
    def search(self, query: str, **kwargs) -> list[str]:
        """Return matching IDs."""
        ...
```

**Implementations**:
- `SQLiteBackend`: Relational storage, ACID transactions
- `FTS5Backend`: Full-text search (virtual table)
- `ChromaBackend`: Vector storage and similarity search
- `FileBackend`: Markdown files for human-editable content

## API Contracts

### Write API

```python
class MemoryWriter:
    """Unified write interface across all tiers."""
    
    def write_observation(
        self,
        session_id: str,
        kind: ObservationKind,  # fact | decision | mistake | preference
        content: str,
        citations: list[str],    # Trace span IDs
        tags: list[str] = None,
        is_private: bool = False,
    ) -> str:
        """
        Write episodic observation.
        
        Returns:
            observation_id
            
        Emits:
            memory.write trace event
        """
        ...
    
    def write_summary(
        self,
        session_id: str,
        narrative: str,
        citations: list[str],
        artifact_hash: str = None,
    ) -> str:
        """
        Write session summary.
        
        Returns:
            summary_id
        """
        ...
    
    def upsert_wiki(
        self,
        title: str,
        body_md: str,
        tags: list[str] = None,
        ttl_days: int = 90,
        confidence: float = 0.8,
    ) -> str:
        """
        Write or update semantic wiki entry.
        
        Returns:
            wiki_id
        """
        ...
```

**Guarantees**:
- **Atomicity**: SQLite write succeeds or fails atomically
- **Ordering**: Writes are sequentially consistent (SQLite serializes)
- **Durability**: WAL mode ensures crash recovery
- **Async embedding**: Chroma writes don't block

### Read API (MCP Tools)

```python
class MemoryReader:
    """Progressive disclosure read interface."""
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filters: dict = None,  # {tier, type, tags, time_range}
    ) -> list[Hit]:
        """
        Hybrid search across tiers.
        
        Returns:
            [{id, title, snippet, score, source, tier}]
            
        Performance:
            20-100ms for k=5
        """
        ...
    
    def timeline(
        self,
        tag: str = None,
        since: float = None,
        until: float = None,
        limit: int = 10,
    ) -> list[Entry]:
        """
        Temporal view of episodic memories.
        
        Returns:
            [{id, timestamp, snippet, tags}]
        """
        ...
    
    def get(
        self,
        id: str,
    ) -> Observation | None:
        """
        Fetch full content by ID.
        
        Returns:
            Full observation with content + citations
            
        Performance:
            <10ms (SQLite indexed lookup)
        """
        ...
```

**Guarantees**:
- **Privacy filtering**: `is_private=True` excluded from search by default
- **Consistent reads**: SQLite read sees latest committed write
- **Snippet safety**: Max 200 chars per snippet (token budget)

## State Management

### Session State

```python
@dataclass
class SessionState:
    """Per-session memory state."""
    
    session_id: str
    created_at: float
    ended_at: float | None
    status: SessionStatus  # active | ended | archived
    repo_root: str
    
    # In-memory caches
    _hot_observations: dict[str, Observation] = field(default_factory=dict)
    _embedding_queue: Queue = field(default_factory=Queue)
```

**Lifecycle**:
1. **Session start**: Load recent observations (last 20) into `_hot_observations`
2. **During session**: New writes go to `_embedding_queue` (async)
3. **Session end**: Flush queue, trigger consolidation, update `ended_at`

### Memory Index State

```python
class MemoryIndex:
    """Fast in-memory index for memory store."""
    
    tag_index: dict[str, set[str]]           # tag → memory_ids
    type_index: dict[MemoryType, set[str]]   # type → memory_ids
    time_index: list[tuple[float, str]]      # (timestamp, memory_id)
    
    def rebuild(self, store: MemoryStore):
        """Rebuild index from store (startup)."""
        ...
```

**Consistency**:
- **In-sync with SQLite**: Every add/delete updates index
- **Rebuilt on load**: Index cleared and rebuilt from DB at startup
- **No persistence**: Index is ephemeral (rebuilt on crash recovery)

### Embedding State

```python
class EmbeddingState:
    """Tracks embedding model and version."""
    
    provider: str          # local | openai | cohere
    model: str             # BAAI/bge-small-en-v1.5
    version: str           # Model version hash
    dimensions: int        # 384
    
    @classmethod
    def current(cls) -> "EmbeddingState":
        """Load from config."""
        ...
    
    def is_compatible(self, other: "EmbeddingState") -> bool:
        """Check if reembedding needed."""
        return self.model == other.model and self.version == other.version
```

**Migration**:
```python
if not EmbeddingState.current().is_compatible(db_state):
    warn("Embedding model changed, run: lyra mem reembed")
```

## Error Handling

### Write Errors

```python
class MemoryWriteError(Exception):
    """Base class for write errors."""
    pass

class SQLiteWriteError(MemoryWriteError):
    """SQLite transaction failed."""
    pass

class ChromaWriteError(MemoryWriteError):
    """Chroma embedding write failed (non-fatal)."""
    pass
```

**Recovery Strategy**:
- **SQLite failure**: Abort, raise to caller (critical)
- **Chroma failure**: Log, queue for retry, continue (best-effort)
- **Embedding failure**: Fall back to keyword-only search

### Read Errors

```python
class MemoryReadError(Exception):
    """Base class for read errors."""
    pass

class MemoryNotFoundError(MemoryReadError):
    """Requested memory doesn't exist."""
    pass

class CorruptedMemoryError(MemoryReadError):
    """Memory data is malformed."""
    pass
```

**Recovery Strategy**:
- **Not found**: Return `None`, don't raise (expected case)
- **Corrupted**: Skip entry, log warning, continue search
- **DB locked**: Retry with exponential backoff (max 3 attempts)

### Consistency Errors

```python
class ConsistencyError(Exception):
    """SQLite and Chroma are out of sync."""
    
    sqlite_ids: set[str]
    chroma_ids: set[str]
    
    @property
    def missing_in_chroma(self) -> set[str]:
        return self.sqlite_ids - self.chroma_ids
    
    @property
    def orphaned_in_chroma(self) -> set[str]:
        return self.chroma_ids - self.sqlite_ids
```

**Recovery Strategy**:
- **Daily reconciler**: Detect drift, log report
- **Auto-repair**: Reembed missing, delete orphans
- **Manual override**: `lyra mem reconcile --force`

## Scalability Design

### Horizontal Scalability

```python
# NOT supported in v1 (single-user, local DB)
# Future: Shard by user_id for multi-tenant

class ShardedMemoryStore:
    """Multi-user sharded store (v2)."""
    
    def get_shard(self, user_id: str) -> MemoryStore:
        """Route to user's shard."""
        shard_id = hash(user_id) % num_shards
        return self.shards[shard_id]
```

### Vertical Scalability

```python
# Current limits:
# - SQLite: 1TB (practical limit ~10GB for local SSD)
# - Chroma: Millions of vectors (practical ~1M for local)
# - FTS5: Same as SQLite base table

# Optimization:
# 1. Partition by time (hot/cold split)
# 2. Archive old observations to separate DB
# 3. Prune aggressively (default: 365-day retention)
```

### Performance Optimizations

#### 1. Write Path Optimization
```python
class BatchWriter:
    """Batch writes for efficiency."""
    
    def __init__(self, batch_size: int = 32):
        self._queue: list[Observation] = []
        self._batch_size = batch_size
    
    def add(self, obs: Observation):
        self._queue.append(obs)
        if len(self._queue) >= self._batch_size:
            self.flush()
    
    def flush(self):
        # Batch insert to SQLite (single transaction)
        # Batch embed (32 docs at once)
        # Batch Chroma write
        ...
```

#### 2. Read Path Optimization
```python
class QueryCache:
    """Cache recent queries (5-min TTL)."""
    
    _cache: dict[str, tuple[float, list[Hit]]] = {}
    
    def get(self, query: str) -> list[Hit] | None:
        if query in self._cache:
            ts, hits = self._cache[query]
            if time.time() - ts < 300:  # 5 min
                return hits
        return None
```

#### 3. Warm Cache
```python
def warm_memory_cache(store: MemoryStore):
    """Preload hot data at session start."""
    
    # Load recent observations (last 20)
    recent = store.get_recent(limit=20)
    
    # Precompute embeddings for common queries
    common_queries = ["bug", "error", "fix", "test", "deploy"]
    for q in common_queries:
        store.search(q, limit=5)  # Prime cache
```

## Concurrency Model

### Single-Writer, Multi-Reader (SQLite)

```python
# SQLite is serialized (single writer at a time)
# Reads can happen concurrently with writes (WAL mode)

import sqlite3

conn = sqlite3.connect(
    "lyra.db",
    check_same_thread=False,  # Allow multi-thread
    isolation_level=None,      # Autocommit mode
)
conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL
```

### Thread Safety

```python
from threading import Lock

class ThreadSafeMemoryStore:
    """Wrap store with locks for multi-threaded access."""
    
    def __init__(self, store: MemoryStore):
        self._store = store
        self._write_lock = Lock()
    
    def write(self, *args, **kwargs):
        with self._write_lock:
            return self._store.write(*args, **kwargs)
    
    def read(self, *args, **kwargs):
        # Reads don't need lock (SQLite handles it)
        return self._store.read(*args, **kwargs)
```

## Testing Strategy

### Unit Tests
```python
# test_memory_store.py
def test_write_read_roundtrip():
    store = MemoryStore(":memory:")
    obs_id = store.write_observation(...)
    obs = store.get(obs_id)
    assert obs.content == "expected"

# test_hybrid_search.py
def test_keyword_vs_semantic():
    # FTS5 should match exact keywords
    # Chroma should match semantic similarity
    # Hybrid should combine both
    ...

# test_privacy.py
def test_private_observations_excluded():
    store.write_observation(..., is_private=True)
    results = store.search("query")
    assert all(not r.is_private for r in results)
```

### Integration Tests
```python
# test_memory_integration.py
def test_cross_session_memory():
    # Session 1: Write observation
    # Session 2: Search and retrieve
    # Assert: Observation found and correct
    ...

def test_embedding_migration():
    # Write with BGE-small
    # Switch to OpenAI
    # Run reembed
    # Assert: Search still works
    ...
```

### Property-Based Tests
```python
from hypothesis import given, strategies as st

@given(st.text(), st.floats(0, 1))
def test_importance_decay_monotonic(content, importance):
    """Importance only decreases over time."""
    mem = Memory(content=content, importance=importance)
    old_importance = mem.importance
    mem.decay_importance(rate=0.01)
    assert mem.importance <= old_importance
```

## Observability Hooks

### Trace Events
```python
# Every operation emits structured trace
from lyra.tracing import trace

@trace.span("memory.write")
def write_observation(...):
    trace.set_attribute("kind", kind)
    trace.set_attribute("tier", "episodic")
    ...

@trace.span("memory.search")
def search(query, ...):
    trace.set_attribute("query", query)
    trace.set_attribute("strategy", "hybrid")
    results = ...
    trace.set_attribute("result_count", len(results))
    return results
```

### Metrics
```python
from prometheus_client import Counter, Histogram

memory_writes = Counter(
    "memory_writes_total",
    "Total memory writes",
    ["kind", "tier"]
)

search_latency = Histogram(
    "memory_search_latency_seconds",
    "Search latency",
    ["strategy"]
)
```

## Migration Path

### Schema Versioning
```python
CURRENT_VERSION = 3

def migrate_db(conn: sqlite3.Connection):
    """Apply migrations to reach current version."""
    current = get_schema_version(conn)
    
    if current < 1:
        # v0 -> v1: Add is_private column
        conn.execute("ALTER TABLE observations ADD COLUMN is_private INTEGER DEFAULT 0")
    
    if current < 2:
        # v1 -> v2: Add confidence to wiki_entries
        conn.execute("ALTER TABLE wiki_entries ADD COLUMN confidence REAL DEFAULT 0.8")
    
    if current < 3:
        # v2 -> v3: Add citations JSON column
        conn.execute("ALTER TABLE observations ADD COLUMN citations TEXT")
    
    set_schema_version(conn, CURRENT_VERSION)
```

### Backward Compatibility
```python
# Always support reading old schemas
# Write in new schema
# Gradual migration on read (lazy upgrade)
```
