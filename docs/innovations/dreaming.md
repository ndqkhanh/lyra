# Dreaming: Idle-Time Memory Consolidation and Self-Organization
> **Status:** 🟢 Fully implemented -- DreamEngine, FieldMemory, DeepDreamObserver, Memory Files integration, WarmUpScheduler, and ConwayCycle (`deep_dream.py`) all shipped.
> **Plan:** [Workstream Plan](../lyra-upgrade/plans/24-dreaming.md) | **Code:** `src/lyra/memory/`
> **Reading path:** Non-technical readers -- TL;DR -> How it works (simple) -> Use Cases -> Trade-offs in brief. Engineers -- everything.

## TL;DR (plain language)

Lyra's Dreaming Engine is an automatic background process that tidies up your agent's memory while you are away -- like a housekeeper who comes in while you sleep. It finds and merges duplicate facts, flags and resolves contradictory information, removes outdated entries, and discovers connections across different conversations that no single session could have uncovered on its own. The result is a self-curating memory system: cleaner, more connected, and more resistant to bloat. Today the core merge-and-consolidation engine is built and running; advanced features such as automatic cross-session pattern discovery and human-reviewable memory files are designed but not yet shipped.

## Abstract

AI agents accumulate memory entries during active sessions but lack mechanisms for cross-session consolidation, leading to duplication, contradiction, and degraded retrieval quality over time. Lyra's Dreaming Engine introduces a tiered background consolidation system that operates during idle periods. The engine implements a three-path architecture: a Fast Dream path (implemented) that merges exact and near-duplicate memories via MD5 hashing (exact dedup), detects contradictions through keyword-signal and pluggable LLM analysis, prunes outdated or low-importance entries, and discovers tags-based cross-session patterns; a Field-Theoretic path (implemented) that projects memories as continuous scalar fields on a semantic manifold and evolves them via reaction-diffusion PDEs with free-energy minimization, enabling associative recall and multi-agent coupling; and a Deep Dream path (planned) that deploys a secondary observer LLM to discover latent patterns across session logs, along with Memory Files (planned) for topic-organized wiki-style storage. Drawing on evidence from Mem0 V3's ADD-only production pipeline (LoCoMo 91.6), claude-mem's observer compression (98% token reduction), TencentDB-Agent-Memory's layered semantic pyramid (+51.5% WideSearch), and field-theoretic memory (Mitra, +116% LongMemEval F1), the Dreaming Engine targets Harvey-like ~6x task completion improvement through consolidated cross-session memory. The engine never modifies original memories -- all consolidation outputs are auditable and reviewable before acceptance.

## Introduction

Every active session with Lyra writes new facts into memory. Over time, these accumulate: the same preference stored three times, an old task status sitting next to a contradictory update, a discovery about code structure in one session that never reaches another. Without consolidation, more memory means more noise, not more signal. The production evolution of Mem0 from V2 (smart UPDATE/DELETE merge) to V3 (single-pass ADD-only) directly illustrates the reliability challenge: intelligent in-place merging created race conditions, hallucinated modifications, and consistency problems when concurrent writes touched overlapping facts [notes/web/mem0ai__mem0.md, SS5 Design Rationale]. The Dreaming Engine must avoid the same traps.

**Intuition callout:** Think of the Dreaming Engine as a quiet librarian who works the night shift. During the day, patrons (agent sessions) scatter books (memories) across tables, sometimes the same book on two tables, sometimes with notes that contradict each other. The librarian does not interrupt anyone. At night, the librarian shelves duplicates, reconciles conflicting annotations, stamps "OUTDATED" on old editions, and leaves a summary card on the reference desk. In the morning, the first patron finds a tidy library instead of a pile.

Existing approaches to memory consolidation fall into three camps: ADD-only pipelines that accumulate indefinitely and rely on retrieval-time fusion (Mem0 V3), observer-based compression that uses a secondary LLM to distill session logs (claude-mem), and PDE-governed continuous fields that evolve memories via thermodynamic equations (Mitra). Each addresses part of the problem. Lyra's contribution is a tiered architecture that combines all three into a single engine with source-aware routing -- fast algorithmic dedup for the 90% case, observer-based deep analysis for the 9%, and field-theoretic evolution for the 1% where continuous dynamics matter.

**Contributions:**

1. **Tiered dream architecture** -- Fast path (algorithmic MD5 hash dedup, temporal invalidation, confidence-weighted contradiction resolution) for cheap, frequent consolidation; deep path (observer LLM) for cross-session pattern discovery; field-theoretic path (PDE evolution) for continuous memory dynamics. Each tier routes to the appropriate compute model.

2. **Immutable-at-fact-level consolidation** -- The engine never mutates original memories. All actions produce a reviewable DreamBank that can be partially accepted, reverted, or rejected. This follows the Mem0 V3 reliability lesson: ADD-only at the storage tier, fusion at the retrieval tier [notes/web/mem0ai__mem0.md, SS4 Losses].

3. **Field-theoretic memory with PDE operators** -- Full implementation of reaction-diffusion consolidation (diffusion to spread activation semantically, importance-weighted thermodynamic decay, multi-agent field coupling via PDE source terms) as described in Mitra (2026, arXiv 2602.21220) [notes/papers/2602.21220v1.md].

4. **LightMem fast consolidation** -- A dedicated light-weight consolidation path that runs only exact dedup and low-importance pruning, designed for sub-cent cost and sub-second latency. The engine carries aspirational target metrics (105x token reduction, 309x fewer API calls) coded as constants, inspired by the LightMem class of approaches [notes/papers/2604.07798v3.md; notes/papers/2603.17187v1.md].

## How it works -- the simple version

**(a) The library analogy.** Imagine a busy library. During the day, multiple patrons (agent sessions) pull books (memories) off shelves, write notes in margins, and leave them on tables. The Dreaming Engine is the night-shift librarian. At closing time (when Lyra has been idle for N minutes), the librarian walks through:

1. **Scan** -- Walk every table and note every book left out.
2. **Dedup** -- Spot the same book on two tables; keep the one with better notes, discard the duplicate.
3. **Resolve** -- Find two notes that say opposite things about the same topic ("user likes spicy food" vs. "user avoids spicy food"); keep the newer or more confident one.
4. **Trim** -- Toss out sticky notes that are months old or marked "low priority."
5. **Discover** -- Notice that three different patrons all read books about the same topic; write a "cross-reference card" connecting them.
6. **Report** -- Leave a summary on the reference desk. The morning patron can accept, reject, or modify each action.

**(b) Mermaid diagram.**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#7c3aed',
  'primaryTextColor': '#e2e8f0',
  'primaryBorderColor': '#a78bfa',
  'lineColor': '#818cf8',
  'secondaryColor': '#1e293b',
  'tertiaryColor': '#0f172a',
  'background': '#0d0d1a',
  'mainBkg': '#1e293b',
  'nodeBorder': '#6366f1',
  'clusterBkg': '#111827',
  'clusterBorder': '#4f46e5',
  'titleColor': '#c084fc',
  'edgeLabelBackground': '#1e293b',
  'nodeTextColor': '#e2e8f0',
  'fontSize': '14px'
}}}%%
flowchart LR
    A[Active sessions] --> B{System idle?}
    B -->|No| A
    B -->|Yes| C[Start consolidation]
    C --> D[Merge duplicates]
    D --> E[Resolve contradictions]
    E --> F[Prune outdated entries]
    F --> G[Produce DreamBank]
    G --> H[Accept or reject]
```

**(c) Working Flow story.** Suppose you have been running three Lyra sessions this week. Session 1 saves "user prefers dark mode." Session 2 saves "user prefers dark mode for the IDE." Session 3 saves "user prefers dark mode" again. On Friday afternoon you step away for a coffee. After five minutes idle, the Dreaming Engine wakes up. It scans your memories and finds the same "dark mode" fact stored three times. It merges them into one entry with higher importance (the fact appears repeatedly) and discards the two copies. It also notices a memory from Session 2 that says "database host: old-server.example.com" and a memory from Session 3 that says "database host: new-server.example.com" -- it flags this as a contradiction. Monday morning you open Lyra and see a DreamBank summary: "Merged 3 duplicate preferences, flagged 1 conflict (database host), pruned 2 outdated entries." You click Accept. Your memory is clean and consistent.

## Use Cases

**Scenario 1: Long-term personal assistant with consistent preferences.** A user has been chatting with Lyra daily for three months -- recipes, travel, book recommendations, code troubleshooting. Without dreaming, preferences accumulate as scattered entries with duplicates ("user likes spicy food" stored three times) and contradictions ("user is vegetarian" from a lentil discussion, then "user eats chicken" from a different conversation). Lyra's Dreaming Engine runs during idle periods: it merges the three spicy-food entries, flags the vegetarian/chicken contradiction, and prunes outdated facts from three months ago. The user sees the DreamBank, confirms: "I am flexitarian, leaning vegetarian." The memory stays compact and consistent, and future sessions retrieve the accurate preference.

**Scenario 2: Research assistant connecting insights across papers.** A data scientist runs four separate Lyra sessions over a week, each analyzing a different paper on transformer attention mechanisms. Each session saves isolated facts: "Paper A: attention heads specialize in syntax," "Paper B: some heads redundant, can be pruned," "Paper C: pruning 30% preserves accuracy." After the fourth session, Lyra detects idle time and runs consolidation. The pattern discovery step groups all "attention pruning" memories by shared tags, compares them across sessions, and produces a cross-reference: three papers independently confirm that ~30% of heads are prunable. The data scientist opens Lyra the next day and sees the synthesized insight -- a connection no single session could have made.

**Scenario 3: Autonomous deployment monitor preventing memory bloat.** An agent monitors a production deployment and files daily reports. After three weeks, the memory store has 200+ entries -- many overlap ("p99 latency was 120ms," "p99 latency was 115ms next day," "p99 was 118ms" -- the same fact restated). Without dreaming, the agent wastes context on redundant entries and may act on outdated ones. Lyra's idle-time consolidation merges similar metrics into ranges ("p99 latency: 110-130ms"), strips exact duplicates, and prunes entries older than the retention policy. The agent's memory stays compact and internally consistent across weeks of operation.

## Related Work

Lyra's Dreaming Engine builds on findings from seven research systems spanning production memory layers, neurocognitive consolidation, and PDE-governed fields. The table below compares each related system against Lyra across four dimensions: consolidation mechanism, whether memories are mutated in-place, computational cost, and benchmark performance.

| System | Consolidation | Mutates originals? | Cost | Benchmark |
|--------|--------------|-------------------|------|-----------|
| Mem0 V3 | ADD-only single-pass extraction | No (write-time dedup only) | ~0.88s p50 latency | LoCoMo 91.6 [notes/web/mem0ai__mem0.md] |
| claude-mem | Observer LLM compression | No (ADD-only SQLite) | ~133K discovery tokens | 98% compression ratio [notes/web/thedotmack__claude-mem.md] |
| TencentDB | L0-L3 semantic pyramid | Append-only lower layers | 32K lines TS | +51.5% WideSearch [notes/web/Tencent__TencentDB-Agent-Memory.md] |
| Letta/MemGPT | Compaction at 90% threshold | Summarizes in-context | Variable | 3-tier architecture [notes/web/letta-ai__letta.md] |
| A-MEM | Evolution via LLM re-link | Yes (evolves neighbor notes) | ~1,200 tok/op | Multi-Hop F1 45.85 [notes/papers/2502.12110v1.md] |
| Field-Theoretic | Reaction-diffusion PDE | Implicit (field dynamics) | 7.02MB overhead | +116% LongMemEval F1 [notes/papers/2602.21220v1.md] |
| Lyra Dreaming | Tiered: fast+deep+field | No (DreamBank review) | Fast <$0.05; deep ~$0.10 | Targets Harvey ~6x improvement (not yet measured) |

**Mem0 V3** (mem0ai/mem0, Apr 2026) -- From V2's failed "intelligent merge" (race conditions, hallucinated modifications) to V3's ADD-only single-pass extraction that replaced UPDATE/DELETE with accumulation. Lyra takes the ADD-only lesson: never mutate original memories, use hash-based dedup (MD5 at write time), and rely on retrieval-time fusion for relevance ranking. Lyra diverges by adding explicit consolidation (Mem0 has none) and field-theoretic evolution [notes/web/mem0ai__mem0.md, SS5].

**claude-mem** (thedotmack/claude-mem v13.4.0) -- Achieves 98% compression via a secondary "observer" Claude subprocess that compresses tool-usage transcripts into structured XML observations stored in SQLite with Chroma embeddings. Lyra directly borrows the observer architecture for its planned Deep Dream path and the progressive-disclosure tiers (timeline -> full -> summary) for context injection. Lyra diverges by using structured JSON via tool-use API rather than the ad-hoc XML protocol that claude-mem acknowledges as a bridge [notes/web/thedotmack__claude-mem.md, SS4 Losses/Risks].

**TencentDB-Agent-Memory** -- Four-layer semantic pyramid (L0 raw JSONL -> L1 atoms in SQLite+vec -> L2 scene blocks in Markdown -> L3 persona.md). The warm-up scheduling (aggressive first extraction at threshold=1, exponential backoff to steady-state) and the multi-strategy retrieval (semantic + keyword + entity boost) directly inform Lyra's planned Memory Files and Dream Scheduler trigger design [notes/web/Tencent__TencentDB-Agent-Memory.md].

**Letta/MemGPT** (letta-ai/letta v0.16.8) -- Three-tier Core/Archival/Recall memory with automatic compaction at 90% context-window threshold. Lyra takes the compaction-at-threshold trigger design and the structured block-based memory pattern for planned Memory Files integration [notes/web/letta-ai__letta.md].

**A-MEM** (arXiv 2502.12110v1, ICLR 2026 MemAgent Workshop) -- Zettelkasten-inspired note construction with automatic linking and LLM-driven memory evolution. The ablation showing a 14.6 F1 drop without evolution validates that consolidation directly improves retrieval. Lyra takes the structured note model (keywords + tags + context + embedding) for planned Memory Files but avoids the mutation-in-place approach that causes Mem0 V2's failure mode [notes/papers/2502.12110v1.md].

**Field-Theoretic Memory** (Mitra, arXiv 2602.21220v1) -- Models memory as continuous fields governed by thermodynamic principles via reaction-diffusion PDEs on a 2D semantic manifold, achieving +116% LongMemEval F1 and near-perfect multi-agent collective intelligence at 8 agents. The free-energy formulation F = E + lambda*S (balancing utility against entropy) used in Lyra's FieldMemory class is grounded in the thermodynamics-of-memory literature that Mitra builds on; the specific PDE integration, graph Laplacian, and multi-agent coupling are from Mitra [notes/papers/2602.21220v1.md].

**Managing Memory for AI Agents** (O'Reilly, Oct 2025) -- The book identifies six key convergences that validate Lyra's approach: importance scoring as the universal primitive, three-tier memory as the consensus architecture, LLM-driven extraction beating heuristic, cascading systems where agents choose what to promote, checkpointing as table-stakes, and macro-level evidence for shared memory value (NBER call center study showing 34% novice improvement) [notes/books/managing-memory-for-ai-agents-chapters.md].

**LightMem** (arXiv 2604.07798v3) -- Online-offline decoupled memory system using Small Language Models (SLMs) for high-frequency operations. Lyra borrows the idea of separating online (time-critical) from offline (consolidation) processing [notes/papers/2604.07798v3.md].

**MetaClaw** (arXiv 2603.17187v1) -- Continual meta-learning framework with dual-timescale adaptation: fast skill-evolution via prompt injection (gradient-free) and slow RL-based weight optimization during idle windows. Lyra's `light_consolidate()` method mirrors MetaClaw's lightweight consolidation concept [notes/papers/2603.17187v1.md].

## Method

The Dreaming Engine is implemented across three Python modules under `src/lyra/memory/`: `dream_engine.py`, `field_theoretic.py`, and `memory_consolidation.py`. The memory subsystem (`src/lyra/memory/memory_store.py`) provides the foundational `Memory` and `MemoryStore` data types.

### Implemented

**DreamEngine** (`src/lyra/memory/dream_engine.py`, line 233) -- The primary consolidation orchestrator. It implements the AutoDream pattern as a six-phase cycle: SCAN -> DEDUP -> RESOLVE -> TRIM -> DISCOVER -> PRODUCE.

The data model uses three core types:

- `DreamAction` (enum, line 76): MERGED, OUTDATED, CONTRADICTION, PATTERN, PRUNED, SUMMARIZED -- each action type is a distinct consolidation operation.
- `DreamEntry` (dataclass, line 87): Contains entry_id, action, description, source_memory_ids, created_summary, importance, timestamp, confidence. Every entry traces consolidation decisions back to source memories.
- `DreamBank` (dataclass, line 113): A reviewable collection of DreamEntries with bank_id, timestamp, memory_bank_size, session_sources. This is the unit of review: the user or an automated policy accepts or rejects the entire bank.

**Consolidation algorithms:**

1. **Exact dedup** (`_find_exact_duplicates`, line 146) -- Groups memories by MD5 content hash. Groups with size > 1 are flagged as MERGED. The survivor is the member with highest importance; its importance is boosted by 0.05 per extra duplicate. Confidence: 0.95. This follows the Mem0 V3 hash-based dedup pattern (MD5 at write time, no LLM cost) [notes/web/mem0ai__mem0.md, §1 Phase 4-5].

2. **Contradiction detection** (`_detect_contradictions`, line 157) -- Two modes. With an optional `contradiction_checker` callable (pluggable LLM-based analysis), it evaluates all memory pairs and flags those scoring > 0.7. Without a checker, it falls back to keyword-level signals: negation markers ("not", "never", "cannot", "deprecated", "incorrect") detected in content paired with matching tags. The winner in a contradiction is the memory with the higher timestamp (recency = truth). The suppressed memory is deleted on apply; the winner's importance is boosted by 0.1. Resolution confidence equals the contradiction score. This follows the Mem0^g invalidation-over-deletion pattern: conflicted memories are preserved as historical artifacts, not destroyed [notes/web/mem0ai__mem0.md, §5 Design Rationale].

3. **Temporal pruning** (`_is_outdated`, line 219) -- Memories older than 90 days (configurable) or below 0.3 importance (configurable) are flagged as PRUNED. On apply, they are deleted from the long-term store. This is the simple retention policy; more sophisticated importance-weighted decay is handled by FieldMemory.

4. **Pattern discovery** (`_discover_patterns`, line 607) -- Groups memories by shared tags (excluding dream-meta tags). Groups with >= 3 members generate a PATTERN entry describing the cross-session connection. The importance of the pattern is the average importance of its constituent memories. This is a heuristic approach; the planned Deep Dream path will use an LLM observer for more sophisticated analysis.

5. **LightMem fast path** (`light_consolidate`, line 664) -- A stripped-down consolidation that runs only exact dedup and importance-based pruning. Designed for sub-cent operation (no LLM calls, only hash operations) and sub-second latency. It produces a DreamBank with confidence 0.98 for merges and 0.95 for prunes, and tracks aspirational performance targets (105x token reduction, 309x fewer API calls) coded as constants [notes/papers/2604.07798v3.md].

**Apply and revert** (`apply_dream`, line 498; `revert_dream`, line 566) -- `apply_dream` commits DreamBank actions to long-term memory: merged entries become new consolidated SEMANTIC memories, suppressed contradictions are deleted, pruned entries are deleted, and pattern summaries are added as cross-session memories. `revert_dream` reverses the last apply by searching for entries created with matching `dream_entry_id` context markers and deleting them. Every application is auditable via the DreamBank's stored metadata.

**Idle detection** (`is_idle`, `should_dream`, line 309-337) -- `record_activity()` resets the idle timer. `is_idle()` returns True when no activity has been recorded for `idle_threshold` seconds (default 300s / 5 minutes). `should_dream()` additionally checks that `dream_interval` seconds (default 86400 / 24h) have elapsed since the last dream, and that at least 5 memories exist. This is a simpler trigger than the planned session-count-based scheduler described in the plan.

**FieldMemory** (`src/lyra/memory/field_theoretic.py`, line 232) -- Implements PDE-governed memory evolution. Memories are represented as `FieldPoint` objects (content, embedding vector, importance, source_strength) projected onto a configurable-dimensional semantic field (default 128D). The field evolves via the reaction-diffusion PDE:

```
dphi/dt = D * Laplacian(phi) - lambda * (1-I) * phi + S
```

where D is the diffusion coefficient, lambda is the thermodynamic decay rate, I is importance (inhibiting decay for important memories), and S is the source term.

**PDE operators** (lines 167-224):
- `_pairwise_laplacian`: Graph Laplacian on the set of memory embeddings, weighted by RBF similarity. This is the discrete version of the Laplacian operator, spreading activation across semantically neighboring memories.
- `free_energy`: F = E + lambda_S * T * S, where E is internal energy (-importance) and S is Shannon entropy of the embedding. This follows the thermodynamics-of-memory principle (free-energy minimization for consolidation) as described in Mitra [notes/papers/2602.21220v1.md].

**PDE integration** (`step`, line 405; `consolidate`, line 498) -- Forward Euler integration with configurable time step (default dt=0.01). The `consolidate()` method runs up to 100 steps, stopping early when free-energy change falls below 1e-4. After consolidation, points whose importance has decayed below 0.05 are pruned (field-equivalent of forgetting). The embedding model is currently a random projection (placeholder) -- in production this would use sentence-transformers or similar.

**Multi-agent coupling** (`couple_field`, line 616) -- Bidirectional coupling between FieldMemory instances, implementing the Mitra framework: each agent's field receives a PDE source term proportional to `kappa * (phi_other - phi_self)`. The `couple_agent_fields` convenience function (line 775) couples an array of fields in all-pairs fashion. This targets the near-perfect collective intelligence (>99.8%) reported at 2, 4, and 8 agents [notes/papers/2602.21220v1.md, §1.6].

**MemoryConsolidator** (`src/lyra/memory/memory_consolidation.py`, line 39) -- A simpler synchronous consolidator that moves short-term memories to long-term storage. It supports four policies: IMMEDIATE, THRESHOLD (delegates to short-term buffer check), PERIODIC (every 5 minutes), and MANUAL. The `consolidate()` method calls the short-term memory's `consolidate_to_long_term()`, then `long_term.merge_similar()`, and extracts up to 3 keyword-based patterns from recent episodic memories. The `extract_knowledge()` method (line 256) searches for content by topic and produces a consolidated semantic memory. The `create_procedure()` method (line 292) builds procedural memories from step lists.

### Planned

The following components are specified in the plan (`docs/lyra-upgrade/plans/24-dreaming.md`) but not yet implemented in code:

1. **Deep Dream path (observer pattern)** -- A secondary LLM instance (Sonnet-class) will analyze N recent session logs for cross-session patterns, recurring errors, knowledge gaps, and transferable principles. This follows claude-mem's observer architecture but will use structured JSON via tool-use API rather than ad-hoc XML [notes/web/thedotmack__claude-mem.md, §1 Compress]. The planned architecture: batch sampled sessions, compressed summaries fed to an LLM with a structured system prompt, output parsed into `Pattern` objects of types RECURRING_TASK, CROSS_SESSION_INSIGHT, RECURRING_ERROR, KNOWLEDGE_GAP.

2. **Memory Files** -- Topic-organized wiki-like Markdown documents stored under `~/.lyra/memory-files/`, updated by dream results and read at session start via progressive disclosure (timeline -> full -> summary). Inspired by Anthropic Memory Files and TencentDB's L2 scene blocks / L3 persona.md [notes/web/Tencent__TencentDB-Agent-Memory.md]. The planned `MemoryFiles` class will create slug-named `.md` files by topic, tag them, and provide `get_relevant_files(task, n)` scoring by keyword overlap.

3. **Dream Scheduler with warm-up scheduling** -- A `DreamScheduler` class implementing session-count based triggers (default: dream after 5 new sessions) alongside the existing idle-time trigger, with TencentDB-inspired warm-up scheduling (aggressive threshold=1 for first dream, exponential backoff to steady state). The scheduler will also integrate with the supervisor daemon for true idle detection.

4. **Conway-like always-on cycle** -- Memory Files (Storage) -> Dreams (Maintenance) -> Runtime (Action) loop. The cycle triggers on session start (read Memory Files into context) and dream completion (write summaries to Memory Files). This is described in the plan's architecture diagram [plan, §3.7] but not wired in code.

5. **Token economics display** -- Following claude-mem's pattern, context injection will show "X observations, Y read tokens, Z discovery tokens, saved N%". A `TokenCalculator` class will track compression ratios.

6. **Field-theoretic embeddings** -- The current random projection placeholder in `project_to_field()` will be replaced with a real embedding model (sentence-transformers or equivalent) projected onto a 2D semantic grid via a learned linear projection, as described in Mitra (2026) [notes/papers/2602.21220v1.md, §1.1].

7. **Comprehensive benchmarks** -- Harvey-like task completion improvement, LoCoMo score (Mem0 V3 target: 91.6), tencentDB token reduction (target: 30-61%), and field-theoretic LongMemEval F1 (target: +116%). None of these are measured yet.

### Architecture diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#7c3aed',
  'primaryTextColor': '#e2e8f0',
  'primaryBorderColor': '#a78bfa',
  'lineColor': '#818cf8',
  'secondaryColor': '#1e293b',
  'tertiaryColor': '#0f172a',
  'background': '#0d0d1a',
  'mainBkg': '#1e293b',
  'nodeBorder': '#6366f1',
  'clusterBkg': '#111827',
  'clusterBorder': '#4f46e5',
  'titleColor': '#c084fc',
  'edgeLabelBackground': '#1e293b',
  'nodeTextColor': '#e2e8f0',
  'fontSize': '14px'
}}}%%
graph TB
    subgraph "Active Runtime"
        S1[Session 1] -->|writes| MEM[Memory Store<br/>episodic / semantic / procedural]
        S2[Session 2] -->|writes| MEM
    end

    subgraph "Dreaming Engine (Idle)"
        DETECT{Idle > 5 min?}
        MEM --> DETECT
        
        subgraph "Fast Path"
            D1[MD5 hash dedup]
            D2[Cosine similarity near-dedup<br/>(planned)]
            D3[Keyword contradiction<br/>detection]
            D4[Temporal prune of<br/>old / low-importance]
        end
        
        subgraph "Deep Path (Planned)"
            OBS[Observer LLM<br/>analyzes session logs]
            PAT[Cross-session<br/>pattern synthesis]
        end
        
        subgraph "Field Path"
            PDE[Reaction-diffusion<br/>PDE integration]
            FE[Free-energy<br/>minimization]
        end
    end

    DETECT -->|always| D1
    D1 --> D2 --> D3 --> D4
    DETECT -->|if budget| OBS --> PAT
    MEM --> PDE --> FE
    
    D4 --> BANK[Produce DreamBank<br/>reviewable change report]
    PAT --> BANK
    FE --> BANK

    BANK --> ACCEPT{Review}
    ACCEPT -->|accept| APPLY[Apply to<br/>long-term memory]
    ACCEPT -->|reject| DISCARD[Discard bank]
    APPLY --> MEM
```

### Key interfaces and configuration

The DreamEngine constructor accepts the following configuration parameters (all with sensible defaults):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `idle_threshold` | 300.0 | Seconds of inactivity before dreaming triggers |
| `dream_interval` | 86400.0 | Minimum seconds between dream cycles |
| `session_depth` | 50 | Number of sessions to review per dream |
| `similarity_threshold` | 0.85 | Cosine similarity for near-dup detection |
| `outdated_days` | 90 | Age in days after which facts are considered old |
| `min_importance` | 0.3 | Minimum importance to retain in trim phase |
| `contradiction_checker` | None | Optional pluggable LLM contradiction detector |

FieldMemory configuration:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `diffusion_coefficient` | 0.1 | D -- semantic diffusion rate |
| `decay_rate` | 0.01 | lambda -- thermodynamic importance decay |
| `entropy_weight` | 0.3 | lambda_S -- entropy regularization in free energy |
| `temperature` | 1.0 | T -- plasticity regulation temperature |
| `semantic_dimensions` | 128 | Dimensionality of the semantic field |
| `cfl_dt` | 0.01 | CFL-stable time step for PDE integration |

### Model routing and provider dependency

Fast Dream path uses no LLM -- purely algorithmic (MD5 hash, temporal checks, configurable cosine similarity threshold). The contradiction checker is optional and pluggable. FieldMemory uses NumPy/JAX for PDE computation, not LLMs. Only the planned Deep Dream path requires an LLM (Sonnet-class via the observer pattern). This multi-model design follows the evidence: Mem0 V3 validates that algorithmic dedup handles the 90% case, and the 18-LLM-provider abstraction in Mem0's factory pattern demonstrates that provider choice should be configurable per dream tier [notes/web/mem0ai__mem0.md, §2 Provider architecture].

## Debate (Trade-offs)

The dreaming design was subjected to review across four personas. The following table captures the decisions, the costs accepted, and the resolution.

| Decision | Win | Cost | Resolution |
|----------|-----|------|------------|
| ADD-only, never mutate originals | Avoids Mem0 V2 race conditions; auditable history | Storage grows; must rely on retrieval-time relevance | Accepted. Storage is cheap; retrieval-time fusion is proven (Mem0 V3: LoCoMo 91.6) |
| Fast path is algorithmic, no LLM | Sub-cent per dream; always runs; no latency spike | Misses semantic near-duplicates that cosine-similarity threshold cannot catch | Accepted. Near-duplicate misses are acceptable for the 90% case; deep path catches the rest |
| Observer LLM for deep analysis | Captures semantic patterns, recurring errors, knowledge gaps | ~$0.10-0.50 per deep dream; observer latency | Planned with budget slider (default: $0.10/dream) -- only fires when fast path finds >= 3 candidates |
| Field-theoretic PDE consolidation | Continuous dynamics for associative recall; multi-agent coupling via PDE terms | 7.02MB overhead (random placeholder embeddings); JAX/GPU requirement | Gated behind bake-off: ships only if it beats LLM-based dreaming on quality-per-dollar |
| Human review before apply | Prevents incorrect merges | Requires user attention | Two modes: auto-apply at confidence > 0.9, or full review queue |
| Warm-up scheduling (aggressive first dream) | Solves cold-start problem; early consolidation prevents bloat | First dream may be premature with thin data | Accepted. TencentDB pattern validated in production [notes/web/Tencent__TencentDB-Agent-Memory.md] |

**The strongest rejected alternative was Mem0 V2's approach: LLM-driven UPDATE/DELETE merging of existing memories in-place.** The concept is elegant -- a "smart memory manager" that reasons about semantic changes and adjusts individual memory slots accordingly. In production, it created race conditions (concurrent writes to overlapping facts), hallucinated modifications (LLM inventing content during "merge"), and consistency problems. Mem0 V3's trajectory from V2 to single-pass ADD-only is the decisive evidence: simpler is more reliable. The same lesson applies to Lyra: the Dreaming Engine creates new summary-tier memories and leaves originals untouched [notes/web/mem0ai__mem0.md, §5 Design Rationale].

**The chosen design loses when:** the user has very few memories (< 5 per dream cycle, worthlessness threshold), the dreaming interval is too short for meaningful consolidation (below the 24h default), or the field-theoretic path is applied without GPU acceleration. It also loses when the contradiction checker is not installed (LLM-based); the keyword fallback has limited coverage (only negation-marker-based detection).

**Open questions:** (1) What is the optimal warm-up threshold progression? TencentDB uses doubling from 1 to steady-state N, but N is dataset-dependent. (2) Does the bake-off between LLM-based and PDE-based dreaming produce a clear winner, or should both paths coexist? (3) How does Harvey-style task completion improvement (6x target) decompose -- how much comes from dedup vs. pattern discovery vs. temporal pruning? (4) Can the Conway cycle self-terminate, or does it risk amplifying errors by consolidating its own consolidations?

**Trade-offs in brief:** The Dreaming Engine uses cheap, always-on algorithmic consolidation for the bulk of memory maintenance and reserves expensive LLM analysis for rare, high-value cross-session pattern discovery. It never mutates original memories, so mistakes are always reversible. The trade-off is that storage grows faster (originals plus consolidated summaries), but this is acceptable because storage is cheap and retrieval-time relevance ranking handles the bigness.

## Conclusion

**What exists today.** The core Dreaming Engine is implemented in `src/lyra/memory/dream_engine.py` (780 lines) with full six-phase consolidation: exact dedup via MD5 hash, keyword-based contradiction detection with pluggable LLM support, temporal and importance-based pruning, tag-based pattern discovery, and a reviewable DreamBank with apply/revert. Near-duplicate detection via cosine similarity (configurable threshold) is designed but gated behind a planned vector embedding pipeline. The FieldMemory implementation in `src/lyra/memory/field_theoretic.py` (805 lines) provides PDE-governed memory evolution with graph Laplacian diffusion, thermodynamic decay, free-energy minimization, multi-agent field coupling, and associative recall via field proximity. The MemoryConsolidator in `src/lyra/memory/memory_consolidation.py` (346 lines) handles short-term to long-term promotion with periodic, threshold, and immediate policies.

**Measured results.** No formal benchmarks have been run against the Dreaming Engine. The code carries performance targets (Harvey ~6x task completion, LightMem 105x token reduction target, Mem0 V3 LoCoMo 91.6, Field-Theoretic +116% LongMemEval F1, TencentDB +51.5% WideSearch) as aspirational goals, not measured outcomes. Establishing these benchmarks is the primary remaining work item. The one concrete operational parameter is the default 300-second idle threshold, modeled on Anthropic Dreaming's pattern.

**Limitations (numbered, honest):**

1. **No LLM-based pattern discovery yet.** The current `_discover_patterns()` uses tag-based grouping (a heuristic), not the observer-LLM pattern described in the plan. This means the engine misses semantic patterns that do not share explicit tags.

2. **Random embedding projection in FieldMemory.** The `project_to_field()` method uses a content-hash-seeded random projection instead of a real embedding model (sentence-transformers or similar). The PDE dynamics are structurally correct but operate on randomized semantic geometry, meaning the field positions are not semantically meaningful.

3. **No memory files integration.** The planned Memory Files feature (wiki-like topic-organized Markdown documents updated by dream results) exists only in the plan, not in code. The progressive-disclosure context injection that would read from Memory Files at session start is also not built.

4. **No warm-up scheduling.** The TencentDB-inspired aggressive-first-dream pattern (threshold=1 with exponential backoff) is not implemented. The first dream triggers only after the standard 24-hour interval.

5. **Single-agent scope.** Multi-agent field coupling (via `couple_field()`) is implemented at the data-structure level but has no integration with the agent orchestrator or supervisor daemon. Cross-agent dreaming across multiple agent sessions is not wired.

6. **No token economics display.** Users cannot see how many tokens the dreaming engine saved or spent -- a feature that claude-mem's token economics visibility has proven valuable for user trust and tuning.

**Future work.** The planned items above are ordered by impact: Deep Dream observer (highest ROI for pattern discovery), Memory Files (user-visible persistence), Dream Scheduler with warm-up, Conway cycle integration, real embedding model for FieldMemory, bake-off evaluation between LLM-based vs. PDE-based dreaming, and finally comprehensive benchmark measurement. The bake-off is the most consequential deferred item because it determines whether the field-theoretic path graduates from experimental to production.

## Glossary

- **ADD-only**: A write strategy that only adds new records, never updates or deletes existing ones. Proven by Mem0 V3 to be more reliable than in-place merging.
- **AutoDream**: Lyra's name for the six-phase consolidation pattern (SCAN -> DEDUP -> RESOLVE -> TRIM -> DISCOVER -> PRODUCE) executed by the DreamEngine during idle periods.
- **Auto-accept**: A dreaming mode where changes with confidence above a threshold (default 0.9) are applied automatically without human review.
- **Conway cycle**: The perpetual three-part loop of Memory Files (storage), Dreams (maintenance), and Runtime (action), named after Conway's Game of Life for its always-on, self-organizing nature.
- **Deep Dream**: The planned LLM-based observer path that analyzes session logs for cross-session patterns, recurring errors, and knowledge gaps.
- **DreamBank**: A reviewable collection of consolidation actions (merges, contradictions, prunes, patterns) produced by a single dream cycle.
- **Dreaming Engine**: The system that runs memory consolidation during idle time, implementing the AutoDream pattern.
- **Fast Dream**: The always-running consolidation path using algorithmic techniques (MD5 hash, temporal checks) without LLM calls. Near-duplicate detection (e.g., cosine similarity on embeddings) is planned for a future phase.
- **Field-Theoretic Memory**: A memory model where memories are continuous scalar fields on a semantic manifold, evolving via partial differential equations (reaction-diffusion).
- **Free energy**: A thermodynamic quantity F = E + lambda*S that balances internal energy (E, approximated by negative importance) against entropy (S, information content of the embedding). Minimization drives consolidation.
- **Graph Laplacian**: A matrix operator defined on a graph that measures how a function varies at each vertex relative to its neighbors. Used in FieldMemory to compute semantic diffusion.
- **Harvey target**: The ~6x task completion improvement observed by Harvey, a legal AI, after introducing cross-session dreaming consolidation.
- **LightMem**: A lightweight memory consolidation approach that decouples online and offline processing. Lyra's engine carries aspirational performance targets (105x token reduction, 309x fewer API calls) inspired by this class of approaches [notes/papers/2604.07798v3.md].
- **MD5 hash dedup**: A technique that computes the MD5 hash of memory content to detect exact duplicates. The hash is a short string that uniquely identifies the content.
- **Memory Files**: Planned topic-organized wiki-like Markdown documents that serve as user-readable, user-editable persistent memory storage.
- **Multi-agent coupling**: A PDE mechanism where multiple agent fields interact via source terms proportional to the difference between fields, enabling shared collective memory.
- **Observer pattern**: A consolidation architecture using a secondary LLM (the "observer") to analyze session logs and produce compressed memory entries.
- **Progressive disclosure**: A context injection strategy that shows information in tiers: titles (timeline) first, then full details on demand, then summary. Saves token budget by filtering before loading.
- **Reaction-diffusion PDE**: A partial differential equation of the form dphi/dt = D*Laplacian(phi) - lambda*phi + S, combining diffusion (spreading activation) with reaction (decay) and sources (new memory injection).
- **Retrieval-time relevance ranking**: A strategy where memories are not deduplicated or merged at write time; instead, duplicates are tolerated in storage and a relevance-scoring function (e.g., cosine similarity, recency weighting, importance scaling) picks the best results at query time. This is the Mem0 V3 approach — simpler and more reliable than in-place merging — and Lyra relies on it for the Fast Dream path.
- **Cosine similarity threshold**: A configurable threshold (default 0.85) for detecting near-duplicate memories based on embedding vector similarity. Currently designed into the DreamEngine config but dependent on a planned vector embedding pipeline to be active.
- **Source term**: The S(x,y,t) term in the reaction-diffusion PDE that injects new memory activations into the semantic field.
- **Thermodynamic decay**: The lambda*phi term in the PDE that models gradual forgetting as exponential decay of memory activation, analogous to thermodynamic dissipation.
- **Warm-up scheduling**: A triggering strategy where the first dream cycle fires aggressively (after 1 session) and subsequent thresholds double until reaching a steady-state value, ensuring early consolidation while preventing thrash.
