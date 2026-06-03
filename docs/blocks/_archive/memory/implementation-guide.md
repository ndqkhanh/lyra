# Memory System Implementation Guide

## Prerequisites

### Required Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
chromadb = "^0.4.18"
sentence-transformers = "^2.2.2"  # For BGE-small-en-v1.5
```

```bash
# Install
poetry install

# Or with pip
pip install chromadb sentence-transformers
```

### Environment Setup

```bash
# Create memory directory structure
mkdir -p ~/.lyra/memory/{wiki,feedback,archive}
mkdir -p ~/.lyra/skills

# Initialize database
lyra memory init
```

## Step-by-Step Implementation

### Step 1: Initialize SQLite Database

```python
# src/memory/db.py
import sqlite3
from pathlib import Path

def init_database(db_path: str = "~/.lyra/memory/lyra.db"):
    """Initialize memory database with schema."""
    
    db_path = Path(db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
    conn.execute("PRAGMA foreign_keys=ON")   # Enable FK constraints
    
    # Create schema
    conn.executescript("""
        -- Schema version tracking
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );
        
        -- Sessions
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            repo_root TEXT,
            created_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL  -- active|ended|archived
        );
        
        -- Observations (episodic tier)
        CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,  -- fact|decision|mistake|preference
            content TEXT NOT NULL,
            citations TEXT,      -- JSON array of span IDs
            is_private INTEGER DEFAULT 0,
            tags TEXT,           -- JSON array
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        
        -- FTS5 index for observations
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts 
        USING fts5(
            content, 
            tags,
            tokenize='porter unicode61'
        );
        
        -- Trigger to keep FTS in sync
        CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
            INSERT INTO observations_fts(rowid, content, tags)
            VALUES (new.rowid, new.content, new.tags);
        END;
        
        CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
            DELETE FROM observations_fts WHERE rowid = old.rowid;
        END;
        
        CREATE TRIGGER IF NOT EXISTS observations_au AFTER UPDATE ON observations BEGIN
            UPDATE observations_fts 
            SET content = new.content, tags = new.tags
            WHERE rowid = new.rowid;
        END;
        
        -- Summaries
        CREATE TABLE IF NOT EXISTS summaries (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            narrative TEXT NOT NULL,
            artifact_hash TEXT,
            citations TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        
        -- Wiki entries (semantic tier)
        CREATE TABLE IF NOT EXISTS wiki_entries (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body_path TEXT NOT NULL,  -- Path to .md file
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by TEXT,
            ttl_days INTEGER DEFAULT 90,
            confidence REAL DEFAULT 0.8
        );
        
        -- Set schema version
        INSERT OR REPLACE INTO schema_version (version) VALUES (3);
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Database initialized at {db_path}")
```

### Step 2: Set Up Chroma Vector Store

```python
# src/memory/vector_store.py
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

class VectorStore:
    """Wrapper for Chroma vector database."""
    
    def __init__(self, persist_dir: str = "~/.lyra/memory/chroma"):
        self.persist_dir = Path(persist_dir).expanduser()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="lyra_memory",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # Initialize embedding model
        self.model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        
    def add(
        self, 
        id: str, 
        content: str, 
        metadata: dict = None
    ):
        """Add document to vector store."""
        
        # Generate embedding
        embedding = self.model.encode(content).tolist()
        
        # Add to Chroma
        self.collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata or {}]
        )
    
    def add_batch(
        self,
        ids: list[str],
        contents: list[str],
        metadatas: list[dict] = None
    ):
        """Add multiple documents in batch."""
        
        # Generate embeddings in batch (faster)
        embeddings = self.model.encode(contents).tolist()
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas or [{} for _ in ids]
        )
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter: dict = None
    ) -> list[tuple[str, float]]:
        """
        Search for similar documents.
        
        Returns:
            List of (id, score) tuples
        """
        
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Search in Chroma
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter
        )
        
        # Return (id, distance) pairs
        # Note: Chroma returns distance, we convert to similarity
        ids = results['ids'][0]
        distances = results['distances'][0]
        scores = [1.0 - d for d in distances]  # Convert distance to similarity
        
        return list(zip(ids, scores))
    
    def delete(self, id: str):
        """Delete document by ID."""
        self.collection.delete(ids=[id])
```

### Step 3: Implement Memory Store

```python
# src/memory/memory_store.py
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from src.memory.vector_store import VectorStore

@dataclass
class Observation:
    """Episodic observation."""
    id: str
    session_id: str
    ts: float
    kind: str  # fact|decision|mistake|preference
    content: str
    citations: list[str]
    is_private: bool
    tags: list[str]

class MemoryStore:
    """Main memory storage interface."""
    
    def __init__(
        self,
        db_path: str = "~/.lyra/memory/lyra.db",
        chroma_path: str = "~/.lyra/memory/chroma"
    ):
        self.db_path = Path(db_path).expanduser()
        self.vector_store = VectorStore(chroma_path)
        
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        return conn
    
    def write_observation(
        self,
        session_id: str,
        kind: str,
        content: str,
        citations: list[str] = None,
        tags: list[str] = None,
        is_private: bool = False,
    ) -> str:
        """
        Write an observation to episodic memory.
        
        Returns:
            observation_id
        """
        
        obs_id = str(uuid.uuid4())
        ts = time.time()
        
        # Write to SQLite (atomic)
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO observations (
                    id, session_id, ts, kind, content, 
                    citations, is_private, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs_id,
                session_id,
                ts,
                kind,
                content,
                json.dumps(citations or []),
                int(is_private),
                json.dumps(tags or [])
            ))
            conn.commit()
        finally:
            conn.close()
        
        # Write to Chroma (async, best-effort)
        if not is_private:
            try:
                self.vector_store.add(
                    id=obs_id,
                    content=content,
                    metadata={
                        "kind": kind,
                        "tags": json.dumps(tags or []),
                        "session_id": session_id
                    }
                )
            except Exception as e:
                # Log but don't fail the write
                print(f"⚠️  Chroma write failed: {e}")
        
        return obs_id
    
    def get_observation(self, obs_id: str) -> Optional[Observation]:
        """Retrieve full observation by ID."""
        
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM observations WHERE id = ?",
                (obs_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return Observation(
                id=row['id'],
                session_id=row['session_id'],
                ts=float(row['ts']),
                kind=row['kind'],
                content=row['content'],
                citations=json.loads(row['citations']),
                is_private=bool(row['is_private']),
                tags=json.loads(row['tags'])
            )
        finally:
            conn.close()
    
    def search_keyword(
        self,
        query: str,
        k: int = 15
    ) -> list[tuple[str, float]]:
        """Search using FTS5 keyword search."""
        
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT 
                    o.id,
                    bm25(observations_fts) as score
                FROM observations_fts
                JOIN observations o ON o.rowid = observations_fts.rowid
                WHERE observations_fts MATCH ?
                  AND o.is_private = 0
                ORDER BY score
                LIMIT ?
            """, (query, k)).fetchall()
            
            # BM25 returns negative scores (lower is better)
            # Convert to positive scores (higher is better)
            return [(row['id'], -row['score']) for row in rows]
        finally:
            conn.close()
    
    def search_semantic(
        self,
        query: str,
        k: int = 15
    ) -> list[tuple[str, float]]:
        """Search using Chroma semantic search."""
        
        return self.vector_store.search(query, k=k)
    
    def search_hybrid(
        self,
        query: str,
        k: int = 5
    ) -> list[str]:
        """
        Hybrid search using RRF fusion.
        
        Returns:
            List of observation IDs (top k)
        """
        
        # Get results from both engines
        keyword_results = self.search_keyword(query, k=k*3)
        semantic_results = self.search_semantic(query, k=k*3)
        
        # Apply RRF fusion
        rrf_k = 60
        scores = {}
        
        # Score from keyword search
        for rank, (obs_id, _) in enumerate(keyword_results):
            scores[obs_id] = scores.get(obs_id, 0) + 1 / (rrf_k + rank + 1)
        
        # Score from semantic search
        for rank, (obs_id, _) in enumerate(semantic_results):
            scores[obs_id] = scores.get(obs_id, 0) + 1 / (rrf_k + rank + 1)
        
        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return sorted_ids[:k]
```

### Step 4: Implement MCP Tools

```python
# src/memory/mcp_tools.py
from typing import Optional

from src.memory.memory_store import MemoryStore

class MemoryMCP:
    """MCP tool interface for memory system."""
    
    def __init__(self, store: MemoryStore):
        self.store = store
    
    def memory_search(
        self,
        query: str,
        limit: int = 5
    ) -> list[dict]:
        """
        Search memory and return snippets.
        
        Returns:
            [{id, title, snippet, score, source}]
        """
        
        # Get top IDs using hybrid search
        obs_ids = self.store.search_hybrid(query, k=limit)
        
        # Fetch snippets
        results = []
        for obs_id in obs_ids:
            obs = self.store.get_observation(obs_id)
            if obs:
                snippet = obs.content[:200] + "..." if len(obs.content) > 200 else obs.content
                results.append({
                    "id": obs.id,
                    "title": f"{obs.kind} observation",
                    "snippet": snippet,
                    "score": 1.0,  # Normalized
                    "source": "hybrid",
                    "tags": obs.tags
                })
        
        return results
    
    def memory_get(
        self,
        observation_id: str
    ) -> Optional[dict]:
        """
        Get full observation content.
        
        Returns:
            {id, content, citations, tags, kind, timestamp}
        """
        
        obs = self.store.get_observation(observation_id)
        if not obs:
            return None
        
        return {
            "id": obs.id,
            "content": obs.content,
            "citations": obs.citations,
            "tags": obs.tags,
            "kind": obs.kind,
            "timestamp": obs.ts,
            "session_id": obs.session_id
        }
    
    def memory_timeline(
        self,
        tag: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        limit: int = 10
    ) -> list[dict]:
        """
        Get temporal view of observations.
        
        Returns:
            [{id, timestamp, snippet, tags}]
        """
        
        conn = self.store._get_conn()
        try:
            query = "SELECT * FROM observations WHERE is_private = 0"
            params = []
            
            if tag:
                query += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')
            
            if since:
                query += " AND ts >= ?"
                params.append(since)
            
            if until:
                query += " AND ts <= ?"
                params.append(until)
            
            query += " ORDER BY ts DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                {
                    "id": row['id'],
                    "timestamp": float(row['ts']),
                    "snippet": row['content'][:200],
                    "tags": json.loads(row['tags'])
                }
                for row in rows
            ]
        finally:
            conn.close()
```

## Configuration

### Config File

```toml
# ~/.lyra/config.toml
[memory]
db_path = "~/.lyra/memory/lyra.db"
chroma_path = "~/.lyra/memory/chroma"

[memory.embedding]
provider = "local"  # local | openai | cohere
model = "BAAI/bge-small-en-v1.5"
batch_size = 32

[memory.search]
hybrid_weight = 0.5  # 0 = keyword only, 1 = semantic only
rrf_k = 60

[memory.pruning]
enabled = true
run_every_n_sessions = 15
dry_run_first = true
retention_days = 365
```

## Testing

### Unit Tests

```python
# tests/test_memory_store.py
import pytest
from src.memory import MemoryStore

@pytest.fixture
def store():
    # Use in-memory SQLite for tests
    store = MemoryStore(db_path=":memory:")
    yield store

def test_write_read_observation(store):
    """Test basic write and read."""
    
    obs_id = store.write_observation(
        session_id="test-session",
        kind="fact",
        content="Python uses indentation",
        tags=["python", "syntax"]
    )
    
    obs = store.get_observation(obs_id)
    assert obs is not None
    assert obs.content == "Python uses indentation"
    assert obs.kind == "fact"
    assert "python" in obs.tags

def test_private_observations_excluded(store):
    """Test that private observations are excluded from search."""
    
    # Write public observation
    store.write_observation(
        session_id="test",
        kind="fact",
        content="Public information",
        tags=["public"]
    )
    
    # Write private observation
    store.write_observation(
        session_id="test",
        kind="fact",
        content="Secret API key",
        tags=["private"],
        is_private=True
    )
    
    # Search should only return public
    results = store.search_keyword("API", k=10)
    assert len(results) == 0  # Private excluded

def test_hybrid_search(store):
    """Test hybrid search fusion."""
    
    # Add observations
    store.write_observation(
        session_id="test",
        kind="fact",
        content="Python async await syntax",
        tags=["python"]
    )
    
    store.write_observation(
        session_id="test",
        kind="fact",
        content="Asynchronous programming patterns",
        tags=["async"]
    )
    
    # Search with semantic query
    results = store.search_hybrid("async patterns", k=5)
    assert len(results) > 0
```

## Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("lyra.memory")
```

### Common Issues

#### Issue 1: Chroma Write Failures
**Symptom**: Observations written to SQLite but not searchable semantically

**Debug**:
```python
# Check Chroma collection
from src.memory.vector_store import VectorStore
vs = VectorStore()
print(vs.collection.count())  # Should match SQLite count
```

**Fix**: Run reconciler
```bash
lyra memory reconcile --repair
```

#### Issue 2: FTS5 Not Finding Results
**Symptom**: Keyword search returns empty

**Debug**:
```python
# Check FTS5 sync
conn = sqlite3.connect("lyra.db")
fts_count = conn.execute("SELECT COUNT(*) FROM observations_fts").fetchone()[0]
obs_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
print(f"FTS: {fts_count}, Observations: {obs_count}")
```

**Fix**: Rebuild FTS5
```sql
DELETE FROM observations_fts;
INSERT INTO observations_fts(rowid, content, tags)
SELECT rowid, content, tags FROM observations;
```

#### Issue 3: Slow Embedding
**Symptom**: Write latency >1 second

**Debug**:
```python
import time
start = time.time()
embeddings = model.encode(["test content"])
print(f"Embedding latency: {time.time() - start:.3f}s")
```

**Fix**: Use GPU or switch to cloud provider
```toml
[memory.embedding]
provider = "openai"
model = "text-embedding-3-small"
```

## Common Pitfalls

### Pitfall 1: Forgetting to Flush Embeddings
**Problem**: Writes succeed but search returns nothing

**Solution**: Always flush embedding queue at session end
```python
def end_session(session_id: str):
    # Flush pending embeddings
    store.flush_embedding_queue()
    # Update session status
    store.mark_session_ended(session_id)
```

### Pitfall 2: Not Handling Private Observations
**Problem**: Private data leaks in search results

**Solution**: Always filter in SQL
```sql
-- CORRECT
SELECT * FROM observations 
WHERE is_private = 0 AND content MATCH ?

-- WRONG (filters in Python, too late)
SELECT * FROM observations WHERE content MATCH ?
```

### Pitfall 3: Ignoring Schema Migrations
**Problem**: Code expects new columns that don't exist

**Solution**: Run migrations on startup
```python
from src.memory.db import migrate_db

def init_store():
    migrate_db(conn)  # Apply any pending migrations
    return MemoryStore()
```

## Production Checklist

- [ ] Database initialized with correct schema
- [ ] Chroma collection created
- [ ] Embedding model downloaded and cached
- [ ] Config file created and validated
- [ ] Migrations run successfully
- [ ] FTS5 triggers active
- [ ] Private observation filter tested
- [ ] Backup strategy defined
- [ ] Monitoring metrics configured
- [ ] Pruner dry-run reviewed
