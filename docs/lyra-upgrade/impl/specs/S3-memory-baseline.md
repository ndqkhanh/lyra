# S3: Memory Baseline (Real STM/LTM Persistence)

> Plan: §4.2 (02-memory.md) | Depends on: S1 (Provider)
> Sources: CraniMem, LightMem, A-MEM, HAGE, SAGE, EVOLVEMEM, RecMem, Managing Memory for AI Agents (book)

## Scope

Replace the in-memory simulated memory store with real persistence: SQLite-backed STM/LTM with vector search, importance-based consolidation, and cross-session recall.

## Core Upgrades

1. **STM**: Conversation turns stored in SQLite with session-scoped TTL — not just a deque
2. **LTM**: JSON-persisted with pgvector-compatible embeddings (sqlite-vec fallback)
3. **Consolidation**: Importance-scored STM→LTM promotion with deduplication
4. **Retrieval**: Hybrid (keyword + semantic + importance) with configurable weights
5. **Cross-session**: Memory survives agent restart via persistent store

## Key Decisions
- SQLite (via aiosqlite) as primary store — zero-dependency, file-based
- Embeddings via sentence-transformers (all-MiniLM-L6-v2) for semantic search
- Importance decay modeled after Ebbinghaus forgetting curve
