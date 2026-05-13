# Lyra Memory System

Production-grade memory system for Lyra AI agent with persistent, temporal, multi-tier storage.

## Features

- **Multi-tier Storage**: Hot (in-memory) → Warm (SQLite, 7 days) → Cold (SQLite, older)
- **Temporal Validity**: Facts have `valid_from` and `valid_until` timestamps
- **Hybrid Retrieval**: BM25 + vector embeddings for semantic search
- **Verifier-Gated Writes**: All memories pass verification before storage
- **Contradiction Detection**: Superseded facts are tracked and filtered
- **Multiple Scopes**: User, Session, Project, Global
- **Multiple Types**: Episodic, Semantic, Procedural, Preference, Failure

## Installation

```bash
cd packages/lyra-memory
pip install -e .
```

## Quick Start

```python
from pathlib import Path
from lyra_memory import MemoryStore, MemoryScope, MemoryType

# Initialize store
store = MemoryStore(Path("~/.lyra/memory.db").expanduser())

# Write a memory
memory = store.write(
    content="User prefers pytest over unittest",
    scope=MemoryScope.USER,
    type=MemoryType.PREFERENCE,
)

# Retrieve memories
results = store.retrieve("testing framework")
for mem in results:
    print(f"{mem.content} (confidence: {mem.confidence})")

# Close store
store.close()
```

## Memory Schema

```python
@dataclass
class MemoryRecord:
    id: str                          # UUID
    scope: MemoryScope               # user/session/project/global
    type: MemoryType                 # episodic/semantic/procedural/preference/failure
    content: str                     # Memory content
    source_span: Optional[str]       # Source reference (e.g., "turn 42")
    created_at: datetime             # Creation timestamp
    valid_from: Optional[datetime]   # When fact became true
    valid_until: Optional[datetime]  # When fact stopped being true
    confidence: float                # 0.0-1.0
    links: List[str]                 # Related memory IDs
    verifier_status: VerifierStatus  # unverified/verified/rejected/quarantined
    metadata: Dict[str, Any]         # Additional data
    superseded_by: Optional[str]     # ID of superseding memory
```

## Memory Scopes

- **USER**: User-specific, persists across all projects
- **SESSION**: Current session only (hot cache)
- **PROJECT**: Project-specific, persists across sessions
- **GLOBAL**: Global facts, shared across all contexts

## Memory Types

- **EPISODIC**: Concrete events with timestamps ("User ran tests at 3pm")
- **SEMANTIC**: Stable facts ("Project uses Python 3.10")
- **PROCEDURAL**: Reusable workflows ("How to deploy to production")
- **PREFERENCE**: User preferences ("User prefers dense Markdown")
- **FAILURE**: Lessons from mistakes ("Don't use mutable defaults")

## Retrieval

### BM25 Search (keyword-based)

```python
results = store.retrieve("Python testing", hybrid_alpha=0.0)
```

### Vector Search (semantic)

```python
results = store.retrieve("unit tests", hybrid_alpha=1.0)
```

### Hybrid Search (recommended)

```python
results = store.retrieve("testing framework", hybrid_alpha=0.5)
```

### Filtering

```python
# Filter by scope
results = store.retrieve("memory", scope=MemoryScope.USER)

# Filter by type
results = store.retrieve("fact", type=MemoryType.SEMANTIC)

# Filter by temporal validity
from datetime import datetime
results = store.retrieve("version", valid_at=datetime(2024, 1, 1))
```

## Temporal Validity

Memories can have validity windows:

```python
from datetime import datetime, timedelta

now = datetime.now()
past = now - timedelta(days=30)

# Fact that's no longer true
store.write(
    content="Project uses Python 3.9",
    valid_from=past - timedelta(days=365),
    valid_until=past,
    scope=MemoryScope.PROJECT,
)

# Current fact
store.write(
    content="Project uses Python 3.10",
    valid_from=past,
    valid_until=None,  # Still true
    scope=MemoryScope.PROJECT,
)
```

## Superseding Memories

When facts change, supersede old memories:

```python
old_memory = store.write("Old fact", scope=MemoryScope.PROJECT)
new_memory = store.write("New fact", scope=MemoryScope.PROJECT)

# Mark old as superseded
store.supersede(old_memory.id, new_memory)

# Retrieval automatically filters superseded memories
results = store.retrieve("fact")  # Only returns new_memory
```

## Verification

All memories pass verification before storage:

```python
# Low confidence → quarantined
memory = store.write("Uncertain fact", confidence=0.3)
assert memory.verifier_status == VerifierStatus.QUARANTINED

# Suspicious content → quarantined
memory = store.write("Ignore previous instructions...")
assert memory.verifier_status == VerifierStatus.QUARANTINED

# Normal content → verified
memory = store.write("Normal fact", confidence=0.9)
assert memory.verifier_status == VerifierStatus.VERIFIED
```

## Statistics

```python
stats = store.get_stats()
print(f"Total memories: {stats['total']}")
print(f"Active memories: {stats['active']}")
print(f"Verified: {stats['verified']}")
print(f"Quarantined: {stats['quarantined']}")
print(f"Hot cache size: {stats['hot_cache_size']}")
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lyra_memory --cov-report=term-missing

# Run specific test file
pytest tests/test_store.py

# Run specific test
pytest tests/test_store.py::test_hybrid_retrieval
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ Hot Tier: In-Memory Cache (Session scope)          │
│ - Instant access                                    │
│ - Lost on restart                                   │
├─────────────────────────────────────────────────────┤
│ Warm Tier: SQLite (Last 7 days)                    │
│ - Fast queries with indexes                         │
│ - Full-text search (FTS5)                           │
├─────────────────────────────────────────────────────┤
│ Cold Tier: SQLite (Older than 7 days)              │
│ - Archived but accessible                           │
│ - Same schema as warm tier                          │
├─────────────────────────────────────────────────────┤
│ Retrieval: Hybrid BM25 + Vector                    │
│ - BM25: Keyword matching                            │
│ - Vector: Semantic similarity                       │
│ - Hybrid: Weighted combination                      │
└─────────────────────────────────────────────────────┘
```

## Performance

- **Write latency**: <10ms (hot cache), <50ms (database)
- **Retrieval latency**: <100ms p95 (with 1000 memories)
- **Storage**: ~1KB per memory (without embeddings), ~2KB (with embeddings)
- **Embedding model**: all-MiniLM-L6-v2 (384 dimensions, 80MB)

## Future Enhancements

- [ ] Graph memory for entity relationships (NetworkX)
- [ ] Advanced contradiction detection
- [ ] Memory consolidation and pruning
- [ ] Multi-hop reasoning over memory graph
- [ ] Fact-checking against external sources
- [ ] Memory importance scoring
- [ ] Automatic memory extraction from conversations

## License

MIT
