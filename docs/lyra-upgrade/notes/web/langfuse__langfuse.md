# langfuse/langfuse -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline: Open-source LLM observability and evaluation platform.**

Langfuse provides tracing, prompt management, evaluations, datasets, and an LLM playground -- all packaged as a self-hostable or cloud platform. The headline feature is **real-time LLM tracing at scale**: capturing every LLM call, retrieval, agent action, embedding, and guardrail invocation as structured, wide events stored in ClickHouse.

The core mechanism is an **event ingestion pipeline** that flows through three stages:

1. **Validation & Auth** (Next.js API handler at `web/src/pages/api/public/ingestion.ts`): Incoming POST batches of events are parsed through Zod discrimininated union schemas (`packages/shared/src/server/ingestion/types.ts`) supporting 15+ event types (trace-create, generation-create, span-update, score-create, etc.). Auth check via API key, rate-limit check (fail-open), and per-event authorization follow.

2. **S3 Archive + Queue Dispatch** (`packages/shared/src/server/ingestion/processEventBatch.ts`): Each validated event is uploaded to S3 (raw JSON, keyed by `{project}/{entityType}/{eventBodyId}/{eventId}.json`) and a BullMQ `IngestionJob` is enqueued in Redis. Events are grouped by `eventBodyId` to reduce S3 operations. Updates are sorted after creates within a batch. For date-boundary safety, a configurable delay (default 5s) prevents duplicate processing around UTC midnight.

3. **Async ClickHouse Write** (`worker/src/queues/ingestionQueue.ts` + `worker/src/services/ClickhouseWriter/index.ts` + `worker/src/services/IngestionService/index.ts`): The worker dequeues jobs, reads event payloads from S3, enriches them (token counting, model matching against pricing tiers, cost calculation, prompt version resolution, tool normalization), and writes them as immutable rows to ClickHouse ReplacingMergeTree tables via a batched singleton `ClickhouseWriter` with configurable batch size, flush interval, and retry with exponential backoff.

**Data model (ClickHouse):**
- `traces` -- ReplacingMergeTree, partitioned by month, ordered by `(project_id, toDate(timestamp), id)`. One trace per LLM interaction root.
- `observations` -- ReplacingMergeTree, partitioned by month, ordered by `(project_id, type, toDate(start_time), id)`. All spans, generations, events, agents, tools, retrievers, evaluators, embeddings, guardrails.
- `scores` -- ReplacingMergeTree, same partition/order strategy. Numeric, categorical, boolean, correction, and text scores.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Monorepo structure (pnpm workspaces, Turborepo):**

```
web/                          # Next.js 15 app (Pages Router)
  src/pages/api/public/       # Public REST API (ingestion, traces, scores, etc.)
  src/server/api/             # tRPC routers (internal UI)
  src/features/               # Feature modules (evaluations, prompts, datasets, etc.)
  src/components/ui/          # Shadcn/ui primitives

worker/                       # BullMQ consumer processes
  src/queues/                 # Queue processors (ingestion, eval, batch export, etc.)
  src/services/               # ClickhouseWriter (batched insert), IngestionService
  src/features/tokenisation/  # Token counting (async + sync paths)

packages/shared/              # Shared contracts
  src/domain/                 # Zod domain models (traces, observations, scores, prompts)
  src/server/                 # Server-only code
    ingestion/                # Event type schemas, batch processor, sampling
    clickhouse/               # ClickHouse client, schema utils, migrations
    queues.ts                 # Queue name and payload type contracts
    repositories/             # Data access layer (ClickHouse + Postgres adapters)
    redis/                    # Queue instances, rate limiter, S3 slowdown tracking
  prisma/schema.prisma        # Postgres schema (1822 lines)
  clickhouse/migrations/      # SQL migration files (clustered + unclustered)

ee/                           # Enterprise-licensed features
```

**Infrastructure dependencies:**
- **ClickHouse** -- Primary analytical database. All trace/observation/score data lives here.
- **Postgres (Prisma ORM)** -- Project settings, user accounts, prompt definitions, eval configs, pricing tiers.
- **Redis (BullMQ)** -- Job queues: ingestion, eval execution, batch export, data retention, webhooks, cloud metering.
- **S3-compatible storage** -- Raw event archive (event sourcing / replay). Blob storage for media (images, files uploaded in traces).
- **OpenTelemetry** -- ~60% of observations arrive via OTLP. Propagation of trace-level attributes (user_id, session_id, tags) uses OTel Context + Baggage.

**Key patterns:**
- **Zod-as-contract**: Every public API schema, domain model, and queue payload is defined as a Zod schema first. Types are inferred. Public and internal schemas differ only in environment validation rules.
- **Batch-and-flush ClickHouse writer**: Singleton pattern. Configurable batch size (default env var), flush interval, max retries. Exponential backoff with 3 written strategies: full batch retry, split-on-string-length-error, split-on-size-error with record truncation.
- **S3-as-event-store**: All ingested events are durably written to S3 before queue processing. This enables replay, retention management, and decouples ingestion throughput from database write throughput.
- **Sampling**: Configurable trace-level sampling. Out-of-sample events are acknowledged but dropped before ClickHouse write.
- **Graceful degradation**: Rate-limiter failures are logged but do not reject requests (fail-open). S3 upload errors abort the batch (events not lost, just rejected to caller).
- **Migration-aware dual writes**: V4 events-only mode filters out legacy trace/observation events from the /ingestion endpoint, accepting only scores, SDK logs, and dataset-run-items.

**Data flow (end-to-end):**
```
SDK/API POST /api/public/ingestion
  -> Zod validation + Auth + Rate limit
  -> Upload event JSON to S3 ({project}/{entityType}/{id}/{eventId}.json)
  -> Enqueue IngestionJob in BullMQ (Redis) with configurable delay
  -> Worker dequeues
  -> Read event data from S3
  -> Inflate/enrich (token count, model match, cost calculation, prompt lookup)
  -> Queue into ClickhouseWriter batched singleton
  -> Periodic flush to ClickHouse ReplacingMergeTree
```

## 3. Performance/Benchmarks (real numbers from the repo)

From the public scale blog (March 2026) and repository data:

| Metric | Value |
|--------|-------|
| GitHub stars | ~28,600 |
| Docker pulls | >20M (badge in README) |
| npm downloads | Significant (badge) |
| Infrastructure growth | 19x data processed over ~2 years |
| Node size growth | 15x (from data growth) |
| Dashboard load time improvement (post-V4 migration) | **>10x for longer durations** |
| Table load time improvement | **"from seconds to tens of milliseconds"** |
| Initial query improvement (post-migration) | 2-3x |
| Final target improvement | 10-20x (with all optimizations) |
| S3 cost reduction (OTel-only projects) | ~85% for some self-hosters |
| OTel adoption in Langfuse Cloud | ~60% of all observations |
| Background migration throughput | 4x (after concurrency fix, up to 15 parts parallel) |
| Propagation job runtime | ~45 seconds per run |
| Node metadata lag (worst case before fix) | ~25 minutes |
| Current version | v3.178.0 |
| Open issues | 667 |

**Benchmarkable env defaults:**
- `LANGFUSE_INGESTION_CLICKHOUSE_WRITE_BATCH_SIZE` -- configurable (env)
- `LANGFUSE_INGESTION_CLICKHOUSE_WRITE_INTERVAL_MS` -- configurable (env)
- `LANGFUSE_INGESTION_CLICKHOUSE_MAX_ATTEMPTS` -- 3 (default in tests)
- `LANGFUSE_INGESTION_QUEUE_DELAY_MS` -- configurable delay around UTC midnight boundaries

## 4. Trade-offs (wins vs loses)

**Wins:**
- **Wide events > metrics/logs/traces triad**: Observations carry rich context (input, output, metadata, usage, cost, model params, tool calls) in a single row, avoiding fragmentation.
- **S3 for linear scale**: S3's near-infinite capacity decouples ingestion throughput from database capacity. Cost is O(storage) not O(operations).
- **ClickHouse for columnar analytics**: 10-100x faster dashboard queries than Postgres for the same data. Ordering keys aligned with query patterns (project + time range).
- **Real-time via OTel context propagation**: Trace-level attributes arrive on observations without staging tables, at the cost of SDK complexity.
- **MIT-licensed core**: Permissive license with enterprise add-ons. Low barrier for self-hosters.
- **Immutable append-only events**: Removes read-time deduplication overhead. ReplacingMergeTree + event_ts dedup at compaction time rather than query time.

**Loses / Known limitations:**
- **ReplacingMergeTree dedup overhead**: Before V4 migration, every query paid a dedup tax scanning billions of records. Even with V4's immutable model, the ReplacingMergeTree engine still does eventual dedup at compaction.
- **Dual complexity at Te-ClickHouse boundary**: Postgres (Prisma) for metadata + ClickHouse for events means two databases, two query languages, two migration pipelines. Operational burden is real.
- **5-minute metadata propagation delay**: Trace-level attributes added after observation creation take ~5 min to propagate via micro-batch job. Deliberate trade-off against eventual consistency.
- **Part fragmentation at scale**: ~1000 parts per partition vs. expected 150-200. Merge stalls from row sizes approaching 150 GiB limit. Requires ongoing tuning.
- **Materialized view serialization**: By default removes insert parallelization. Must set `parallel_view_processing=1`.
- **SDK compatibility tax**: Legacy SDKs that use separated trace create + observation create events require delayed propagation rather than real-time OTel context.
- **Ingestion delay around UTC midnight**: Events around 23:45-00:15 UTC get a configurable delay to avoid duplicates from out-of-order processing at date boundaries.
- **S3 API cost**: S3 SlowDown errors under high throughput triggered secondary queue routing. `isS3SlowDownError()` + `markProjectS3Slowdown()` in ingestion pipeline.

**Design trade-offs called out explicitly in architecture principles:**
- "Treat cost and operational simplicity as architectural constraints. Extra databases, queues, materialized views, and migrations must earn their long-term operational burden."
- "Favor immutable or append-oriented event records... Updates that force read-time deduplication create hidden query costs at scale."
- "Before adding a join, ask whether the attribute should be propagated or denormalized onto the observation path."

## 5. Design Rationale (why this approach)

Langfuse's architecture is grounded in the **wide events observability model** (influenced by Charity Majors' Observability 2.0 and the "All You Need is Wide Events" philosophy). The key choices:

1. **Observations as primary analytical unit, not traces.** A trace is a correlation handle linking related observations. This reflects real usage: agentic traces can have thousands of spans where the interesting signal is at the observation level, not the trace root. Architecture principles: "Model observations as the primary analytical unit."

2. **Immutable events avoid read-time merges.** Every query on a ReplacingMergeTree previously scanned for duplicates. Making observation events immutable (one-shot writes with OTel-style start/end) eliminates the dedup tax, letting queries stream data in disk order.

3. **S3 event archive for operational decoupling.** Three concerns motivated this: (a) durable raw events enable replay after bugs; (b) S3 decouples ingestion throughput from ClickHouse write capacity -- the queue drains at ClickHouse speed, not HTTP request speed; (c) retention policies can delete from ClickHouse while preserving raw data for compliance.

4. **Denormalized schema for columnar efficiency.** The ClickHouse tables are deliberately denormalized: observation rows carry trace-level attributes (user_id, session_id, release, tags) directly rather than requiring joins. This makes the ordering key (`project_id, type, toDate(start_time)`) directly filterable for the most common queries.

5. **Real-time propagation via OTel Context, not batch.** Rather than a staging table or streaming system, Langfuse propagates trace metadata through OTel's `Context` and `Baggage` APIs. This is zero-lag for new data but requires SDK-level support.

6. **Public contracts via Fern + generated typed SDKs.** The OpenAPI spec is the source of truth for the public API, with typed SDKs auto-generated. Internal developer experience uses tRPC for the frontend.

## 6. Transfer to Lyra (one idea + route + Impact/Effort/Tier + LICENSE)

**Transferable idea: S3-backed event ingestion pipeline with ClickHouse columnar analytics.**

Lyra already emits structured events (agent traces, tool calls, LLM invocations). We could build a light-weight observability pipeline that records every agent-invocation event into a local ClickHouse database, with S3 as a durable event archive for replay and debugging.

**Specific mechanism to port:**
The three-phase ingestion pattern from `processEventBatch.ts` -- (1) Zod validation + auth check, (2) S3 archive push + BullMQ queue enqueue, (3) batched ClickHouse write via a singleton `ClickhouseWriter` that accumulates rows and flushes on interval or batch size. The ClickHouse schema mirrors Lyra's own observation types (agent steps, tool calls, LLM generations, evaluation scores).

**Workstream route:**
Section 4.x (Observability/Monitoring infrastructure for Lyra agents).

**Impact: 7** (High -- direct observability into every agent execution, enabling debugging, cost analysis, and performance optimization at scale)

**Effort: 5** (Medium-high -- requires ClickHouse deployment, S3-compatible storage configuration, and Zod schema definitions mirroring Lyra's domain model)

**Tier: 2** (Important for production multi-agent deployments but not MVP-crushing)

**LICENSE: MIT (core).** Full compatibility with Lyra's preferred licensing. The enterprise features under `ee/` use a separate commercial license, but the core tracing and evaluation pipeline is permissive MIT. The ClickHouse Writer, ingestion schemas, and public API handlers are all MIT-licensed.

**Note location:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/langfuse__langfuse.md`
