# Lyra Block 07 — Memory (Three-Tier)

A hybrid memory system combining keyword search (SQLite FTS5) and semantic search (Chroma), partitioned across three tiers: **procedural** (skills), **episodic** (traces, observations), and **semantic** (facts, agentic wiki). The persona partition lives in [SOUL.md](08-soul-md-persona.md) and is treated separately.

Design lineage: [Hermes Agent three-layer memory](../../../../docs/55-hermes-agent-self-improving.md), [claude-mem hybrid store + progressive disclosure](../../../../docs/72-claude-mem-persistent-memory-compression.md), [SemaClaw three-tier context architecture](../../../../docs/54-semaclaw-general-purpose-agent.md).

## Responsibility

1. Persist durable knowledge across sessions with low-friction lookup.
2. Support two query modes (keyword + semantic) and fuse results.
3. Provide the progressive-disclosure MCP tool surface used by [Context Engine § L5](06-context-engine.md).
4. Enforce privacy (`<private>` tag) and citation-based auditability.
5. Ship a background pruner that prevents entropy runaway.

## Tiers

### Procedural — *how to do things*

- Skills (`SKILL.md` folders) — full bodies.
- Workflow templates (`.lyra/skills/<name>/`).
- Lives on disk; catalogue indexed at session start.
- Update path: Skill Extractor ([block 09](09-skill-engine-and-extractor.md)) writes / refines.

### Episodic — *what happened*

- Observations: per-turn notes an agent recorded ("user prefers functional over class components").
- Trace summaries: compacted narrative of past sessions.
- Artifact references (diff, test output hashes).
- Update path: automatic (on compaction + session end) + explicit (`memory.write`).

### Semantic — *what is known*

- Facts: durable user-private facts ("their database is Postgres 17 with pgvector").
- Agentic wiki entries: diffable cited notes the agent maintains on the user's projects/tools.
- Update path: agentic wiki skill + user-edited `MEMORY.md`.

### Persona — *who the agent is with this user*

`SOUL.md` — see [block 08](08-soul-md-persona.md). Listed here for completeness; treated as a separate partition with stricter update semantics.

## Storage

| Backend | Stores |
|---|---|
| `lyra.db` (SQLite) | sessions, observations, summaries, wiki metadata, extraction provenance |
| SQLite FTS5 virtual tables | full-text search over observations / wiki entries |
| Chroma (on-disk) | semantic embeddings for same content |
| Files (.md) | SOUL.md, MEMORY.md, wiki/*.md, feedback/*.md, skills/*/SKILL.md |

Consistency: writes go to SQLite first (atomic), then Chroma (best-effort with retry). A daily reconciler reconciles drift.

## Schema (SQLite)

```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  repo_root TEXT, created_at TEXT, ended_at TEXT, status TEXT
);

CREATE TABLE observations (
  id TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id),
  ts TEXT, kind TEXT,                -- fact|decision|mistake|preference
  content TEXT, citations TEXT,      -- JSON array of trace span ids
  is_private INTEGER DEFAULT 0,
  tags TEXT                          -- JSON array
);

CREATE VIRTUAL TABLE observations_fts USING fts5(
  content, tags, tokenize='porter unicode61'
);

CREATE TABLE summaries (
  id TEXT PRIMARY KEY,
  session_id TEXT, ts TEXT, narrative TEXT, artifact_hash TEXT,
  citations TEXT
);

CREATE TABLE wiki_entries (
  id TEXT PRIMARY KEY,
  title TEXT, body_path TEXT,       -- path to .md file
  tags TEXT, created_at TEXT, updated_at TEXT, updated_by TEXT,
  ttl_days INTEGER, confidence REAL
);
```

FTS5 trigger keeps `observations_fts` in sync.

## Embedding model

Default: **BGE-small-en-v1.5** (33M params), local CPU. Chroma stores 384-dim vectors. Configurable:

```yaml
memory:
  embedding:
    provider: local          # local | openai | cohere | voyage
    model: BAAI/bge-small-en-v1.5
    batch_size: 32
```

Cloud embedding is opt-in; defaults to local for privacy.

## Write API

```python
memory.write_observation(
    session_id="...",
    kind="preference",
    content="User prefers pytest over unittest.",
    citations=[span_id],
    tags=["test","python"],
    is_private=False,
)

memory.write_summary(session_id="...", narrative="...", citations=[...])

memory.upsert_wiki(title="...", body_md="...", tags=[...], ttl_days=90)
```

Every write emits a `memory.write` trace event (HIR primitive = `memory_write`).

## Read API (progressive disclosure MCP)

Covered in [block 06 § Progressive disclosure](06-context-engine.md). Three tools:

```python
memory.search(query, limit=5) -> list[Hit]        # hybrid: FTS5 ∪ Chroma, re-ranked
memory.timeline(tag, since, until, limit=10) -> list[Entry]
memory.get(observation_id) -> Observation         # full content + citations
```

Hybrid ranking:

```python
def search(query, limit=5):
    fts_hits = fts.search(query, k=limit*3)       # keyword
    sem_hits = chroma.query(query, k=limit*3)     # semantic
    fused = reciprocal_rank_fusion(fts_hits, sem_hits, k=60)
    return fused[:limit]
```

Each `Hit` carries `{id, title, snippet, score, source: fts|sem|both}`.

## Privacy controls

1. **`<private>` tag** in observation content or `is_private=True` parameter.
    - Excluded from `memory.search` by default.
    - Visible via `memory.get` only when explicitly requested by ID.
    - Redacted in trace exports.
2. **`lyra mem wipe --confirm`** — deletes SQLite + Chroma. Trace retained separately.
3. **`lyra mem export --redact`** — produces a redacted dump (replaces private / secret content with markers).
4. **Scope control** — team-mode (v2) will scope observations by workspace; v1 is per-user local.

## Agentic wiki skill

A built-in skill (`.lyra/skills/wiki/`) runs opportunistically at session-end:

1. Survey session trace for durable claims ("the project uses GraphQL Yoga").
2. Propose wiki entries (new or updates).
3. Write `.lyra/memory/wiki/<slug>.md` with frontmatter and cited evidence.
4. User can review via `lyra mem wiki review`.

Entries decay by TTL unless reinforced by further sessions.

## Feedback-fed skill refinement

Per Hermes: after a skill invocation, the skill extractor reads the session's outcome and records feedback for the skill (success / partial / fail + notes). This feedback accumulates in `memory/feedback/<skill-name>.md` and informs refinement ([block 09](09-skill-engine-and-extractor.md)).

## Entropy management (pruner)

A background cron job (invoked by [Scheduler](../system-design.md#4-public-apis)):

- Observations older than 365 days with zero citations → archive.
- Wiki entries with `confidence < 0.3` and no recent updates → flag for user review.
- Skills with consistent "fail" feedback across ≥ 10 uses → mark `stale`; router skips unless explicitly invoked.
- Duplicate summaries → merge.
- Chroma collection rebuild if SQLite source diverges.

Pruning events emit `memory.prune` spans with `removed_count`, `archived_count`.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Search under-retrieves (misses obvious hit) | Hybrid fusion; tunable via `memory.search.hybrid_weight` |
| Over-retrieves noise | Re-rank score threshold; `limit` parameter |
| Chroma & SQLite drift | Daily reconciler + write-ahead log inspection on startup |
| Embedding model changes between versions | Migration: `lyra mem reembed`; old embeddings kept until swap completes |
| Private info leaks to search | FTS5 query explicitly filters `is_private=0`; integration test |
| Memory DB corruption | WAL mode + auto-repair on startup |
| Wiki sprawl | TTL + `confidence` decay + user review surface |
| Embedding latency on hot path | Embed async on writes; warm cache on startup |

## Metrics emitted

- `memory.writes.total` labeled by kind
- `memory.reads.total` labeled by tool
- `memory.search.latency_ms` histogram
- `memory.hybrid.fts_hit_ratio` / `sem_hit_ratio`
- `memory.pruner.removed` / `archived`
- `memory.private_records.count` gauge
- `memory.chroma.drift_count` (reconciler)

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_sqlite_fts.py` | FTS trigger sync, tokenizer choices |
| Unit `test_chroma.py` | Embedding + query determinism (fixed seed) |
| Unit `test_memory_store.py` | Write/read round-trip, private filter |
| Unit `test_pruner.py` | Decay rules; dry-run mode |
| Integration | Cross-session write-then-read; hybrid ranking |
| Property | Hybrid fusion is commutative in tie-breaks |
| Replay | Pre-recorded trace's observation writes reproduce same state |

## Open questions

1. **Personal knowledge graph.** Wiki entries implicitly form a graph via references. Formalize as a graph DB at v2?
2. **Embedding drift.** Model updates change vectors; re-embedding is expensive. How often is necessary?
3. **Multi-repo knowledge sharing.** User has 20 repos; cross-repo wiki is powerful but privacy-sensitive. Opt-in scope control.
4. **Memory privacy and attention.** If the agent attends to a private observation, it can mention it in response. We filter but not foolproof. User controls with `mem wipe` in worst case.
