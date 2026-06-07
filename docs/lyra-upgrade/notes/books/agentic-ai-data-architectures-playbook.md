# Agentic AI Data Architectures — Best Practices Playbook

*Extracted from: Agentic AI Data Architectures by Blaize Stewart & Ed Huang (O'Reilly, 2026)*
*For: Lyra harness engineering — actionable patterns from distributed SQL memory architecture*

---

## Practice 1: Treat Memory as First-Class Infrastructure

- **What:** Design memory as a shared, governed, infrastructure-level concern — not as application-level state patched together from disparate storage systems. Memory spans structured facts (transactions), unstructured meaning (embeddings), and temporal continuity (event streams). All three must be unified under a single retrieval substrate.

- **Why:** When memory is fragmented across separate systems (relational DB + vector store + cache + ETL pipelines), agents experience compounding latency, stale data, and inconsistent results. Multi-hop reasoning loops amplify these problems. A unified memory layer eliminates handoffs, ensures transactional-semantic consistency, and provides the durability agents need to maintain continuity across sessions.

- **Lyra route:** §4.2 (Memory architecture), §4.5 (Infrastructure design) — Lyra should consolidate its working memory, long-term memory, and episodic event stores into a unified memory subsystem — not separate bolt-ons per agent.

- **Source:** Chapters 1, 2

---

## Practice 2: Design for Evolving State, Not Transactional Snapshots

- **What:** Traditional databases excel at transactional state — discrete, consistent snapshots (like a camera roll). Agentic AI requires evolving state — a continuous film reel where each frame is shaped by what came before. This means the data layer must support versioned records, temporal queries (`AS OF TIMESTAMP`), and the ability to recall what was true when.

- **Why:** Without evolving state, agents experience conversational resets, lose track of subtasks in multi-step plans, and produce inconsistent responses because context was not preserved. Session tables and caches are brittle work-arounds — they were never designed for inference-driven workloads.

- **Lyra route:** §4.2 (Memory architecture), §4.6 (Context management) — Lyra's context window management and session persistence must be built on infrastructure that natively supports temporal versioning, not just key-value snapshots.

- **Source:** Chapter 1 (pp. 12–13), Chapter 3 (Temporal Consistency Retrieval, pp. 38–39)

---

## Practice 3: Ground Retrieval in Facts with Semantic-Transactional Joins

- **What:** Always pair vector similarity search with relational WHERE clauses. Semantic matches find meaning; transactional filters enforce factual correctness. For example, retrieve cases similar to a support ticket but only from active accounts (`WHERE status='active'`). Embeddings can be enriched with structured attributes (renewal dates, account size, region) rather than just filtered.

- **Why:** Research on hybrid search shows this pattern improves precision by excluding semantically relevant but operationally invalid results. It strengthens explainability and auditability — semantic reasoning is grounded in authoritative facts, not just vector proximity. Combining unstructured and structured signals reduces hallucinations in RAG.

- **Lyra route:** §4.3 (Tool use and plugins), §4.2 (Memory retrieval) — Lyra's tool-calling and knowledge retrieval should always pair semantic search with factual filters. When an agent retrieves past conversations or documents, it must cross-reference against operational constraints.

- **Source:** Chapter 3 (Semantic-Transactional Join, Contextual Fact Augmentation, pp. 27–28)

---

## Practice 4: Implement a Capture→Filter→Store→Retrieve Lifecycle for All Memory Tiers

- **What:** Both long-term memory (LTM) and episodic memory should follow a disciplined four-step lifecycle:
  1. **Capture** — at session end or checkpoints, generate summaries/embeddings of important content (do not store everything verbatim)
  2. **Filter** — use heuristics, scoring (recency/frequency/user signals), and forgetting rules; only retain what is important, frequently referenced, or explicitly marked
  3. **Store** — vector DB for semantic recall, structured DB for explicit facts, tiered systems with short/mid/long-term layers
  4. **Retrieve** — inject retrieved memories (summaries, facts, embeddings) into the agent's context window

- **Why:** Without filtering, memory stores grow unbounded and dilute relevance. Without capturing summaries instead of verbatim transcripts, storage costs explode and retrieval precision drops. The capture→filter→store→retrieve cycle ensures agents remember what matters, forget what doesn't, and retrieve coherent context at inference time.

- **Lyra route:** §4.2 (Memory architecture), §4.6 (Context management) — This lifecycle is the direct implementation template for Lyra's memory subsystem. Each memory tier (STM, LTM, episodic) should implement these four steps.

- **Source:** Chapter 3 (LTM and Episodic Memory patterns, pp. 35–38)

---

## Practice 5: Use Multiagent Shared Memory with Atomic Commit Protocols

- **What:** When multiple agents collaborate, use a shared memory table in a transactional store (distributed SQL) as the coordination layer. Structured facts, semantic embeddings, and inter-agent commitments reside in the same tables. SQL ensures atomic updates — locking resources, recording task progress, committing state transitions — so agents never "talk past" each other or duplicate effort.

- **Why:** Without atomic commit protocols, multiagent systems suffer race conditions: two agents claim the same task, conflicting state updates corrupt shared context, and agents duplicate work. A transactional shared memory layer eliminates these failure modes while preserving semantic richness (agents can discover semantically related contributions from peers via embedded search).

- **Lyra route:** §4.4 (Multi-agent coordination) — Lyra's agent orchestration should use transactional shared memory for task handoffs, not ad-hoc message passing. This is the architectural alternative to fragile agent-to-agent communication patterns.

- **Source:** Chapter 3 (Multiagent Shared Memory, pp. 39–40)

---

## Practice 6: Bind Tail Latency at the Infrastructure Level

- **What:** Don't let individual application services handle latency mitigation. The retrieval infrastructure must guarantee all five latency modes:
  - Best-case (average-path) — fast indexing, in-memory access
  - Tail/worst-case (95th–99th percentile) — redundancy, speculative execution, isolation
  - Cold lookup / cache miss — prefetching, efficient index structures
  - Network/cross-node — partition-aware locality, intelligent routing
  - Index maintenance — incremental updates, background compaction that never blocks reads

- **Why:** Median latency is deceptive. The 99th percentile tail dominates user experience and determines SLA compliance. When each microservice patches latency with its own caching and bulkheads, the result is inconsistency, duplicated effort, and fragile performance. Infrastructure-level guarantees mean applications simply issue queries and assume fast, reliable responses.

- **Lyra route:** §4.7 (Observability), §4.5 (Infrastructure design) — Lyra's performance requirements must specify tail latency bounds (p99), not just average response times. The harness must monitor all five latency modes.

- **Source:** Chapter 4 (Latency, pp. 43–45)

---

## Practice 7: Bake Governance Into the Retrieval Layer

- **What:** Embed three governance mechanisms inside the retrieval infrastructure itself — not in middleware, API gateways, or application wrappers:
  1. **Standardized metadata per request** — context, data source, timestamp, version ID, user identity, provenance
  2. **RBAC enforced at retrieval boundary** — even if the application is compromised, unauthorized data cannot be fetched
  3. **Immutable audit logs for every fetch** — records of who requested what, whether access was granted/denied, with timing

- **Why:** Governance bolted onto applications via middleware or API gateways is fragile, inconsistent, and risky at scale. Policy divergence across services creates security gaps. Centralized governance ensures every retrieval — regardless of which agent or application initiated it — is traceable, auditable, and access-controlled.

- **Lyra route:** §4.9 (Safety and governance) — Lyra's safety architecture must enforce access control and audit logging at the retrieval boundary, not in individual agent logic. Every context fetch should carry standardized metadata and produce immutable audit records.

- **Source:** Chapter 4 (Governance, pp. 48–49)

---

## Practice 8: Drive Accuracy Through System-Level Feedback Loops

- **What:** Treat retrieval accuracy as a continuous, systemic property — not a one-time configuration. Instrument precision, recall, MRR (mean reciprocal rank), NDCG (normalized discounted cumulative gain), and hit rates at the retrieval engine level. Capture user corrections (relevant/not relevant, clicks, ratings) and model disagreement signals (when the LLM declines to use context, revises its answer, or returns low confidence) and feed them back as supervision into ranking and indexing logic.

- **Why:** Without continuous measurement, models and heuristics accumulate erosion as data shifts and domain drift occurs. Application-level ranking heuristics drift silently until failures become severe. Infrastructure-level feedback loops enable "living indexing" — retrieval that learns from mistakes, refines relevance at scale, and adapts to changing data distributions without manual re-tuning.

- **Lyra route:** §4.7 (Observability), §4.10 (Self-improvement and evolution) — Lyra's evaluation harness must instrument retrieval quality metrics continuously, not just during offline eval runs. Feedback from agent corrections should flow back into memory ranking.

- **Source:** Chapter 4 (Accuracy, pp. 49–50)

---

## Practice 9: Build Economic Self-Regulation into Agent Execution

- **What:** Expose granular cost telemetry (usage accounting, resource consumption, query costs) back to agents. When agents can see the cost of their retrieval strategies and model calls, they can adjust behavior — optimize queries, reduce unnecessary lookups, or defer non-urgent work.

- **Why:** Agentic systems generate their own tasks and queries autonomously, which means cost can spiral without guardrails. Traditional systems treat cost as an external operational concern. Exposing cost signals to the agents themselves creates a self-regulating feedback loop — agents learn to trade off completeness against cost, just as human engineers do.

- **Lyra route:** §4.8 (Harness engineering), §4.5 (Infrastructure design) — Lyra's agent loop should include cost-awareness as a first-class signal. The harness should expose per-action cost telemetry so agents can budget and throttle their own resource usage.

- **Source:** Chapter 2 (Economic dimension, pp. 24)

---

## Practice 10: Use Sliding Window Context with Idempotent Incremental Updates

- **What:** For real-time agent decisions, maintain a sliding window of recent data alongside aggregated historical measures. Most aggregates (counts, sums, averages) can be updated in constant time; complex metrics use approximate structures (sketches, t-digests). Updates must be incremental and idempotent — failed batches replay safely without duplication.

- **Why:** Agents need both the latest signals (what's happening now) and historical grounding (what normally happens). A sliding window provides both views efficiently: memory scales with window size W and partition count K, not with total historical data. Idempotent updates ensure fault tolerance — no duplicated counts from retries.

- **Lyra route:** §4.6 (Context management) — Lyra's context window management for streaming/real-time scenarios should implement sliding windows with incremental aggregate updates and idempotent replay. This is the pattern for continuous agent loops that monitor ongoing events.

- **Source:** Chapter 3 (Sliding Window Context, pp. 29–30)

---

## Practice 11: Keep Embeddings Synchronized with Transactional Truth via CDC

- **What:** Use change data capture (CDC) or streaming replication to incrementally update vector indexes when the underlying transactional data changes. Row-level changes are re-embedded and stored in the vector index. Agents then query embeddings guaranteed to reflect current transactional truth — not a stale batch snapshot.

- **Why:** Fragile batch ETL pipelines between operational DB and vector store create a gap between "what is true" (transactions) and "what is searchable" (embeddings). CDC eliminates this gap. Agents reasoning on stale embeddings produce hallucinations or outdated decisions. Incremental sync keeps semantic memory fresh without batch lag.

- **Lyra route:** §4.2 (Memory architecture), §4.5 (Infrastructure) — Lyra's knowledge base and document indexing should use incremental sync patterns rather than periodic full-reindexing. When external data sources change, embeddings must reflect those changes in near-real-time.

- **Source:** Chapter 3 (Incremental Fact Synchronization, p. 40)

---

## Practice 12: Reason Under Uncertainty with Probabilistic Joins

- **What:** When identities or relationships are uncertain, expand SQL joins with fuzzy/probabilistic matching. Match attributes with similarity functions instead of strict equality. Embeddings provide semantic context, weighted by probabilistic match scores. Agents reason over graded confidence levels, not binary matches.

- **Why:** In domains like fraud detection, entity resolution, and intelligence analysis, strict joins discard partial signals that may be the only evidence available. Agents that can only handle binary matches lose critical information. Probabilistic joins allow the system to preserve uncertainty and let the reasoning layer weigh evidence appropriately.

- **Lyra route:** §4.3 (Tool use), §4.6 (Context management) — Lyra's retrieval and tool-calling should support confidence-weighted results. When matching entities across data sources (user identities, company names, product references), use fuzzy matching with confidence scores rather than exact-match-or-nothing logic.

- **Source:** Chapter 3 (Probabilistic Joins, pp. 27–28)

---

## Practice 13: Separate Application Logic from Infrastructure Guarantees

- **What:** The principle: "Applications consume; systems guarantee." The application's role is to issue a query; the infrastructure's role is to fulfill it with speed, trust, and meaning. Reliability, latency enforcement, governance, and accuracy are infrastructure-level guarantees — not responsibilities scattered across application services writing ad hoc code.

- **Why:** When each service implements its own caching, access control, error handling, and ranking heuristics, the result is policy divergence, duplicated effort, inconsistent behavior, and fragile operations. A clean boundary between application consumption and infrastructure guarantees enables composable systems, agents that evolve without re-engineering retrieval logic, and trust baked into architecture rather than bolted on.

- **Lyra route:** §4.8 (Harness engineering) — This is the foundational design philosophy for Lyra's harness. The harness must provide reliability guarantees (retries, observability, governance, cost tracking) so individual agents and skills can focus on reasoning and action — not infrastructure plumbing.

- **Source:** Chapter 4 (Applications Consume; Systems Guarantee, pp. 50–51)
