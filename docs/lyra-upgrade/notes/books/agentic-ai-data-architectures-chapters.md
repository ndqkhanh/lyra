# Agentic AI Data Architectures — Chapter Notes

**Author:** Blaize Stewart and Ed Huang | **Year:** 2026 | **Publisher:** O'Reilly Media (commissioned by PingCAP)

**Core Thesis:** Agentic AI's biggest bottleneck is not model size but memory infrastructure. Distributed SQL provides the unified foundation needed to bind transactional truth with semantic meaning, enabling agentic AI systems to act with continuity, coherence, and trustworthiness at scale. Memory must be treated as first-class infrastructure — not patched together from fragmented storage systems.

**Target Audience:** Enterprise architects, data platform engineers, and AI infrastructure teams building production agentic AI systems.

---

## Chapter 1: What Is Agentic AI and Why Memory Matters (pp. 6–14)

- **Key insight:** The difference between generative AI and agentic AI is analogous to a recipe book vs. a personal chef. A chef remembers preferences, tracks pantry state, and adapts over time. Agentic AI requires the same: persistent memory, not just stateless generation.

- **The Perceive/Reason/Act/Learn loop:** The four pillars that distinguish agents from static models:
  - **Perceive** — draw signals from text, APIs, databases, sensors, prior memory
  - **Reason** — evaluate inputs against objectives and constraints; decide next action
  - **Act** — trigger workflows, invoke external systems, coordinate subtasks without continuous human prompting
  - **Learn** — ingest feedback to refine future performance (closed-loop improvement)

- **Model scaling is diminishing:** Chinchilla scaling laws show that a mid-sized model trained on more data outperforms much larger models trained on less. The real bottleneck is retrieval quality, not parameter count.

- **Context engineering over prompt engineering:** Transformers process in-context information (supplied at inference time) differently from knowledge in weights. Reliance on external context yields more reliable, up-to-date outputs than what is embedded in static model weights. Memory becomes the "durable substrate of context."

- **Three memory tiers defined:**
  - **Short-term (working) memory:** coherence within a single task/conversation. Without it, every conversational turn resets.
  - **Long-term memory:** persistence across sessions (days, weeks, months). Retained facts, preferences, past instructions.
  - **Episodic memory:** sequences of events + outcomes. Enables learning from past attempts — what worked, what failed.

- **Why traditional databases fail:** Conventional systems manage transactional state (static snapshots, like a camera roll). Agentic AI needs evolving state (continuous film reel, where each frame is shaped by what came before). Session tables, caches, and orchestration layers are brittle work-arounds.

- **Key failure modes of stateless infrastructure for agents:** conversational resets, planning agents that lose track of subtasks, inconsistent responses because context was not preserved across turns.

- **Best practices:**
  - Treat memory as a first-class architectural concern, not an application afterthought
  - Design for evolving state, not just transactional snapshots
  - Ground retrieval in external, up-to-date sources rather than relying solely on model weights
  - Distinguish between short-term coherence, long-term persistence, and episodic learning

- **Anti-patterns:**
  - Relying on prompt context as the only form of memory (it vanishes after the session)
  - Patching continuity with session tables and caches on top of stateless databases
  - Assuming bigger models solve the memory problem — they don't

- **Relevant to Lyra §4.x:** §4.2 (Memory architecture) — This chapter validates Lyra's need for a tiered memory system (working/STM, persistent/LTM, and episodic/event stores) grounded in durable infrastructure. §4.1 (Agent loop architecture) — The perceive→reason→act→learn loop maps directly to Lyra's own agent execution cycle.

---

## Chapter 2: Memory as Infrastructure (pp. 15–25)

- **Key insight:** Memory is not an application concern — it is shared infrastructure, like networks or storage systems. When unified, memory enables coordination; when fragmented, intelligence stalls.

- **Three data types agents require:**
  - **Structured data (~20% of enterprise data):** facts, transactions, metadata. Functions like "immutable digital laws" for grounding reasoning with clarity.
  - **Unstructured data (~80%):** documents, conversations, logs, images. Holds tone, intent, context. Requires embeddings and semantic retrieval to unlock meaning.
  - **Temporal continuity:** episodic memory, state tracking, time-sensitive retrieval. Enables agents to recall, adapt, and act over time.

- **Three common failure modes of fragmented memory stacks:**

  1. **The Latency Trap:** Multihop reasoning loops (plan → retrieve → act → reflect) add compounding latency. When memory spans multiple backends (vector store + SQL + cache), every handoff accumulates delay and inconsistency. Mitigations like adaptive looping, cascading models, and aggressive caching add orchestration complexity that creates new points of failure.

  2. **Scaling Limits of Legacy Systems:** Agentic AI introduces spiky, inference-driven workloads — an agent may query thousands of records and apply semantic filters in real time, then sit idle. Conventional inelastic architectures choose between throughput (serving many queries with stale caches) and freshness (accurate but slow). Agents need both. Example: a fraud detection agent must analyze transactions as they occur, not hours later.

  3. **Operational Complexity — Orchestration Fragility and Monitoring Blind Spots:** Agentic systems lack a "Kubernetes for agents." Tooling for deployment, scaling, and monitoring is fragmented and hand-stitched. Tracing why an agent made a decision is notoriously difficult due to dynamic reasoning paths and nondeterministic loops. A single timeout or agent failure can cascade across the system.

- **Distributed SQL as the solution:** Extends relational databases (tables, schemas, ACID transactions) across multiple nodes with horizontal scalability, strong consistency, and high availability. Uses Raft consensus for partition tolerance. Exposes a single SQL interface while running across many servers.

- **CAP theorem in agentic context:** Distributed SQL typically favors consistency over availability (using consensus protocols). This consistency-first approach is vital for agents that depend on synchronized memory and coherent state. But not all agents require strict consistency — distributed SQL provides flexibility.

- **Unified retrieval foundation:** When vector search is integrated into distributed SQL, transactional accuracy and semantic similarity operate side by side. Eliminates the fragmentation of "relational DB + separate vector store."

- **Why SQL's declarative power matters for agents:** Agents can filter, join, and aggregate with ACID accuracy while simultaneously reasoning about meaning and context via vector search — all in a single query. Leverages decades of existing governance, tooling, and workforce expertise.

- **Elasticity for spiky workloads:** Distributed SQL scales horizontally to meet demand spikes and retracts when idle. Supports many agents acting concurrently without sacrificing speed.

- **Agentic apps as "living systems":** Agents autonomously plan workflows, write code, spawn subagents, alter schemas, and maintain long-running state. Distributed SQL mirrors this behavior — it can create lightweight, isolated data environments on demand (branch/explore/terminate), supports online schema evolution, snapshotting, and safe rollback.

- **Self-regulating agents via economic feedback:** Distributed SQL platforms expose granular usage accounting, transparent metering, and resource budgets. When agents receive cost signals, they can adjust strategies, optimize queries, and self-regulate.

- **Best practices:**
  - Unify structured, unstructured, and temporal data under a single storage substrate
  - Design for spiky, inference-driven workloads — not predictable batch patterns
  - Favor consistency-first for coordination-critical agent workloads
  - Build monitoring at the infrastructure level, not in application code
  - Expose cost telemetry so agents can self-optimize

- **Anti-patterns:**
  - Running separate vector stores, relational DBs, and caches that agents must coordinate across
  - Using batch ETL pipelines between operational and analytical systems for agents that need real-time data
  - Building orchestration logic "stitched together by hand" instead of relying on infrastructure guarantees
  - Assuming Kubernetes solves the storage problem (it only addresses compute)

- **Relevant to Lyra §4.x:** §4.2 (Memory architecture), §4.5 (Infrastructure design) — Distributed SQL with integrated vector search directly supports Lyra's need for a unified multimodal memory backend. §4.7 (Observability) — The monitoring blind spots described here map to Lyra's observability requirements. §4.8 (Harness engineering) — The "no Kubernetes for agents" gap validates Lyra's harness-engineering mission.

---

## Chapter 3: Beyond Storage — Patterns for Agentic Applications (pp. 26–42)

- **Key insight:** Infrastructure alone does not create intelligence. Patterns — repeatable strategies for retrieval, joining, and memory activation — transform distributed SQL from a theoretical substrate into a practical framework for adaptive reasoning.

### Semantic and Transactional Patterns

**Semantic-Transactional Join (p. 27):**
- Combines vector similarity search with relational WHERE filters
- Example: retrieve support cases similar to a new ticket, but only from active accounts (`WHERE status='active'`)
- Research shows hybrid search improves precision by excluding semantically relevant but operationally invalid results
- Strengthens explainability and auditability by grounding semantic reasoning in authoritative facts

**Contextual Fact Augmentation (p. 27):**
- Embeddings are enriched with structured data (not just filtered by it)
- Example: pair similar past conversations with renewal dates, account size, region
- Research confirms combining unstructured + structured signals improves accuracy and reduces hallucinations

**Probabilistic Joins for Ambiguous Context (p. 27–28):**
- Expands traditional SQL joins with fuzzy/probabilistic matching
- Match attributes with similarity functions instead of strict equality
- Produces match probabilities or confidence scores
- Powerful for fraud detection, entity resolution, intelligence analysis
- Allows agents to reason under uncertainty instead of discarding partial signals

### Mixed Workload Patterns (Real-Time + Historical)

**Sliding Window Context (pp. 29–30):**
- Maintains a moving slice of recent data alongside aggregated measures across longer horizons
- Most aggregates (counts, sums, averages) can be updated in constant time; complex metrics use approximate structures (sketches, t-digests)
- Memory scales with window size (W) and number of partitions (K), but incremental/approximate methods reduce this dramatically
- Updates are incremental and idempotent — failed batches replay safely without duplication
- Example: cybersecurity — a single failed login means little; dozens from the same IP within minutes against historical behavior reveals real risk

**Microbatch Refresh (pp. 30–32):**
- Processes small increments of new data at frequent intervals (every few seconds or minutes)
- Bridges the gap between real-time streaming and batch analytics without overwhelming the system
- Seven-step pattern: (1) set target freshness, (2) trigger on timer or row count, (3) ingest only new data with safety delay, (4) validate/dedupe/transform, (5) merge atomically into aggregates, (6) advance watermark and log metrics, (7) expose refreshed results with timestamp
- Failure-aware: fall back to last successful watermark, retry with exponential backoff, signal agents via stale-data flags if delay exceeds freshness window

### Retrieval Patterns for Agentic Memory

**RAG (Retrieval-Augmented Generation) (pp. 32–34):**
- Four stages: Indexing → Retrieval → Augmentation → Generation
- 85% of organizations are testing or deploying LLMs; 29% have implemented RAG
- Key advantage: stay up to date without retraining — just update the external knowledge base
- Citations/references to retrieved documents boost user confidence via traceability
- RAG is the foundational retrieval mechanism used for all memory types (STM, LTM, episodic)

**Long-Term Memory: Persistent Stores (pp. 35–36):**
- Four-step lifecycle:
  1. **Capture** — generate summary/embedding of important content at session end (avoid verbatim storage)
  2. **Filter/Decide** — heuristics for importance, scoring (recency/frequency/user signals), forgetting rules for unused memories
  3. **Storage** — vector DB for semantic recall, structured DB/key-value for explicit facts, multitiered systems with short/mid/long-term layers
  4. **Retrieval** — query memory stores like RAG, inject into context window
- Two primary functions: persisting user context and persisting intention in prompts
- Eliminates redundancy: agents don't force users to repeat details

**Episodic Memory: Session-Based Retention (pp. 36–38):**
- Tied to a particular conversation or task — captures "the flow of what just happened"
- Avoids repetition, preserves dialogue continuity, keeps multistep reasoning on track
- Four-step lifecycle:
  1. **Capture** — record events, exchanges, outcomes during active session (rolling transcript, structured logs, embeddings)
  2. **Filter** — heuristics for task-critical interactions, scoring by temporal sequence/relevance, session-bound expiry rules
  3. **Storage** — temporary: session buffers, rolling windows (last N exchanges), event logs; may compress into summary for LTM transfer
  4. **Retrieval** — recall during session to maintain thread coherence
- Creates an agent that feels attentive and situationally aware: "Earlier you asked me to compare options A and B"

**Temporal Consistency Retrieval (pp. 38–39):**
- Enables reasoning on facts as they existed at a specific time, not just current state
- Uses temporal tables with `AS OF TIMESTAMP` predicates
- Embeddings tied to historical records ensure semantic recall is historically anchored
- Prevents "time travel hallucinations," supports regulatory compliance (audits, medical histories)

**Multiagent Shared Memory (pp. 39–40):**
- Distributed SQL as a coordinated memory layer for multiple agents
- SQL tables hold structured facts, semantic embeddings, and inter-agent commitments
- Atomic updates (locking resources, recording task progress) prevent race conditions
- Agents read shared state and enrich with semantic recall for coordinated strategies
- Prevents agents from "talking past" each other or duplicating effort

**Incremental Fact Synchronization (p. 40):**
- Keeps vector indexes aligned with transactional state without fragile ETL pipelines
- Uses CDC (change data capture) or streaming replication: row-level changes → re-embed → store in vector index
- Guarantees agents query embeddings that reflect current transactional truth
- Prevents reasoning on stale or contradictory data

- **Best practices:**
  - Always pair semantic search with transactional filters (WHERE clauses) to ground results in facts
  - Use probabilistic joins when identities are uncertain — don't discard partial signals
  - Maintain sliding windows for real-time decisions; use constant-time aggregate updates
  - Implement microbatch refresh with failure-aware watermarks and exponential backoff
  - Combine episodic capture with LTM transfer (session ends → compress to summary → persist if significant)
  - Use CDC/streaming replication to keep embeddings aligned with transactional state

- **Anti-patterns:**
  - Treating vector search and SQL queries as separate concerns handled by different systems
  - Building fragile batch ETL pipelines between operational DB and vector store
  - Storing all conversation data verbatim instead of summarizing and filtering
  - Using binary join logic when real-world identities are probabilistic
  - Letting agents share memory without atomic commit protocols (race conditions)

- **Relevant to Lyra §4.x:** §4.2 (Memory architecture) — The capture/filter/store/retrieve lifecycle for LTM and episodic memory is a direct template for Lyra's memory subsystem. §4.3 (Tool use and plugins) — The Semantic-Transactional Join pattern maps to Lyra's need to filter tool results. §4.4 (Multi-agent coordination) — Multiagent Shared Memory pattern directly supports Lyra's multi-agent design. §4.6 (Context management) — Sliding Window Context and Temporal Consistency Retrieval are essential patterns.

---

## Chapter 4: Operationalizing the AI Memory Layer (pp. 43–51)

- **Key insight:** "Applications consume; systems guarantee." The burden of reliability, latency enforcement, governance, and accuracy must live in the infrastructure itself — not in individual services writing ad hoc code.

### Latency Management (pp. 43–45)

Five latency modes that must be addressed at the system level:

1. **Best-case (average-path) latency:** the "happy path" — fast indexing, in-memory access, minimal internal overhead
2. **Tail/worst-case latency:** 95th/99th percentile outliers dominate UX and violate SLAs. Mitigate via redundancy, speculative execution, scheduling, resource isolation
3. **Cold lookup / cache miss latency:** fallback to deeper storage. Mitigate via prefetching, efficient index structures, smart cache invalidation to avoid latency cliffs
4. **Network/cross-node latency:** coordination, partitioning, remote lookups. Minimize cross-node calls, colocate related data, leverage locality, batch requests
5. **Index maintenance/update latency:** writes, reindexing, compaction must not degrade read performance. Use incremental updates, background compaction

System-level requirements:
- Fast indexes, multimodal unified search, efficient data structures for both normal and cold-path queries
- Partitioning, intelligent routing, locality awareness to control network latency
- Speculative execution, isolation, adaptive resource management to bound tail latency
- Background index updates that never block reads

### Elasticity and Isolation (pp. 45–48)

Distributed SQL principles for production-grade retrieval:

- **Horizontal scaling on demand:** partition and replicate across nodes; scale out under load, scale back when idle. TiDB splits data into regions and dynamically redistributes loads to prevent hotspots.
- **Resource isolation across tenants/agent workloads:** enforce CPU, memory, query quotas at the scheduler level so one high-volume query doesn't degrade retrieval for others.
- **Partition-aware locality and data coplacement:** minimize cross-node hops by colocating frequently-accessed-together partitions.
- **Elastic compute-storage decoupling:** independently scale query processing nodes (stateless SQL engines) and storage/replica nodes.
- **Safe scaling and versioning:** rolling upgrades, transparent migration without "cold gaps" or slowed lookups during rebalancing.
- **Noisy neighbor mitigation:** throttle or sandbox heavy index updates so other tenants' latency guarantees remain intact.
- **Multiparadigm storage:** emerging distributed SQL supports vectors, JSON, knowledge-graph data alongside traditional tables — enables richer querying with LTM and versioned data.

### Governance: Baked-In, Not Layered on Top (pp. 48–49)

Three governance mechanisms at the retrieval layer (not the application layer):

1. **Standardized Metadata per Request:** Every retrieval carries context, data source/shard, timestamp, version/revision IDs, user/principal identity, and provenance. Without this, audits and compliance reviews are brittle.
2. **Enforced Access Control at the Boundary:** RBAC enforced inside the retrieval layer. Even if the application is compromised, unauthorized data cannot be fetched through retrieval. Centralizes policy, reduces duplication, avoids policy divergence.
3. **Immutable Audit Logs for Every Fetch:** Every retrieval event (success or denial) generates an immutable log: who requested, what was requested, metadata, access granted/denied, timing. Designed for traceability, compliance, forensic review — not just debugging.

### Accuracy: Continuous, Systemic Responsibility (pp. 49–50)

- **System-level instrumentation:** Measure precision, recall, MRR, NDCG, hit rates against ground truth or proxy signals continuously. Without this, models, heuristics, and filters accumulate erosion over time as data shifts (domain drift).
- **Infrastructure-supported feedback loops:** Capture explicit user corrections (relevant/not relevant, clicks, star ratings) and route them into reranker or ranking-tuning logic. Detect model disagreements (when the generative model declines context, revises its answer, or returns low confidence) and feed back as supervision.
- **Living indexing:** The retrieval engine becomes adaptive — learned improvements in ranking weights, scoring fusion strategies, periodic embedding updates. All feedback handling lives inside the infrastructure (not scattered across applications), enabling consistent update logic, versioning, safe rollback, and deduplicated feedback pipelines.

### The Central Principle (pp. 50–51)

"Applications consume; systems guarantee." The application's role is to issue a query; the infrastructure's role is to fulfill it with speed, trust, and meaning. This separation enables:
- Composable systems where agents evolve without re-engineering retrieval logic
- Trust baked into architecture, not bolted on
- Memory transformed from a footnote into a first-class backbone of intelligent systems

- **Best practices:**
  - Bound tail latency at the infrastructure level — don't leave it to individual services
  - Colocate related data partitions and decouple compute from storage
  - Enforce governance (metadata, RBAC, audit logs) inside the retrieval layer, not in middleware
  - Instrument precision/recall/MRR/NDCG at the system level for continuous accuracy monitoring
  - Build closed-loop feedback from user corrections into ranking/index updates
  - Design for "living indexing" — retrieval that learns from mistakes and refines relevance at scale

- **Anti-patterns:**
  - Letting each microservice patch latency, security, or relevance gaps with ad hoc code
  - Treating governance as a secondary concern layered on via API gateways and wrappers
  - Measuring only median latency while ignoring 99th percentile tail latency
  - One-time indexing that never adapts to domain drift
  - Scattering feedback pipelines across services instead of centralizing in the retrieval engine

- **Relevant to Lyra §4.x:** §4.7 (Observability and monitoring) — The five latency modes and system-level metrics map directly to Lyra's observability design. §4.5 (Infrastructure design) — Elasticity, isolation, and multiparadigm storage are core infrastructure requirements. §4.9 (Safety and governance) — Baked-in RBAC, immutable audit logs, and standardized metadata per request are the governance blueprint. §4.8 (Harness engineering) — "Applications consume; systems guarantee" is the core design philosophy for Lyra's harness layer.

---

## Summary: Book's Architecture Blueprint

The book's argument follows a clear progression:

1. **Chapter 1 (Why):** Agentic AI is defined by the perceive→reason→act→learn loop. Memory (short-term, long-term, episodic) is what makes this possible. Bigger models aren't the answer — better memory infrastructure is.

2. **Chapter 2 (What infrastructure):** Traditional databases fail because they manage static snapshots, not evolving state. Fragmented memory stacks (SQL + vector store + cache + ETL) introduce latency, inconsistency, and operational fragility. Distributed SQL with integrated vector search is the unifying substrate.

3. **Chapter 3 (How — patterns):** Concrete architectural patterns — semantic-transactional joins, contextual fact augmentation, probabilistic joins, sliding windows, microbatch refresh, RAG, LTM lifecycle, episodic memory, temporal consistency, multiagent shared memory, incremental fact sync.

4. **Chapter 4 (How — operations):** Production readiness requires infrastructure-level guarantees for latency (all five modes), elasticity/isolation, governance (RBAC, audit logs, metadata), and continuous accuracy improvement via feedback loops.

**The core architectural principle:** "Applications consume; systems guarantee."
