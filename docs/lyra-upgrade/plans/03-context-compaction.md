# Workstream Plan: Context Engineering & Auto-Compaction

> Rewrite — June 7, 2026 | Deep-read evidence from 15 sources: 8 papers, 3 book playbooks, 5 web repos/docs, 1 synthesis

## Plain-Language Summary

Lyra currently has no context management -- context grows unbounded until the model's limit, causing "lost in the middle" degradation, high token costs, and eventual failure. This plan implements a **layered compaction pipeline** combining Anthropic's 3-strategy framework (Clearing + Compaction + Memory) with redundancy-aware pruning (R-KV), structured brief synthesis (COMPASS), progressive-disclosure loading (addyosmani + Aider + lean-ctx), and multi-signal retention scoring (mem0 + Memory Survey). The breakthrough is a **composite retention policy** that scores every token/chunk by `λ*relevance + α*recency - (1-λ-α)*redundancy`, then surgically prunes before compaction, achieving 60-80% context reduction while structurally protecting code-relevant spans (callsites, branch conditions, return statements) from eviction. Phase 2 adds an async memory model (COMEM k-step-off) for latency hiding at production scale.

---

## Evidence Base

### Papers (8 consulted)

| # | ID | Short Title | Venue | Key Contribution |
|---|-----|------------|-------|-----------------|
| 1 | 2605.30842v1 | COMEM | ICML 2026 | Decoupled async memory model, k-step-off pipeline, 2.08x speedup on SWE-bench |
| 2 | 2604.10235v1 | CodeComp | arXiv Apr 2026 | Structural KV cache compression via CPG; 0.0944 Jaccard between attention and structure |
| 3 | 2510.00615v3 | ACON | ICML 2026 | NL compression guideline optimization via contrastive trajectory feedback |
| 4 | 2505.24133v4 | R-KV | NeurIPS 2025 | Redundancy-aware KV cache pruning; `Z = λ·I − (1−λ)·R` joint scoring |
| 5 | 2510.08790v1 | COMPASS | arXiv Oct 2025 | 3-agent hierarchy, 6-section structured briefs, +110% GAIA over SAS baseline |
| 6 | 2510.26493v1 | Context Engineering 2.0 | arXiv Oct 2025 | Self-baking consolidation, 4-level progressive abstraction, entropy reduction framework |
| 7 | 2603.07670v1 | Memory Survey (Du) | arXiv Mar 2026 | POMDP formalization, Pattern B/C recommendations, write-filter-read pipeline |
| 8 | 2512.13564v2 | Memory Survey (Hu) | arXiv Jan 2026 | Forms-Functions-Dynamics taxonomy, 27 benchmarks cataloged |

### Book Playbooks (3 consulted)

| # | Book | Chapter/Section | Key Insight |
|---|------|----------------|-------------|
| 9 | Agentic Design Patterns (Gulli, 2025) | Ch.8 Memory, Ch.4 Context Engineering | Dual Memory Architecture from Day One; Context Engineering is the systematic discipline |
| 10 | Managing Memory for AI Agents | Ch.1-5 | Importance scoring, cascading memory, multi-signal retrieval, checkpointing with TTL |
| 11 | Agentic Architectural Patterns (Arsanjani, 2026) | Ch.5-6 | Shared Epistemic Memory as single source of truth; Persistent Instruction Anchoring; Instruction Drift defense |

### Web Repos/Docs (5 consulted)

| # | Source | Key Mechanism |
|---|--------|---------------|
| 12 | Anthropic Context Engineering Cookbook (platform.claude.com, Mar 2026) | 3 API primitives (compact/clear/memory), diagnostic framework, clearing = 67% free reduction |
| 13 | Claude Code Checkpointing (code.claude.com, 2026) | Orthogonal state dimensions, targeted summarization (from-here/up-to-here) |
| 14 | yvgude/lean-ctx (GitHub, v3.7.x) | 10 compression modes, 97.7% code map compression, 85.5% session token savings, 69 MCP tools |
| 15 | addyosmani/agent-skills (GitHub, 2025) | Progressive-disclosure skill loading, meta-skill decision tree, <300 line skills |
| 16 | Aider-AI/aider (GitHub, 2025) | Repo map via tree-sitter + PageRank, ChatSummary compaction, edit format abstraction |

### Supporting Synthesis

| # | Source | Role |
|---|--------|------|
| 17 | synthesis/context-engineering.md (Jun 7, 2026) | Thematic synthesis of 18 papers + 5 books + 4 web sources; convergences, contradictions, recommendations |

---

## Current Lyra Baseline

BASELINE.md rates Context maturity = **none**. Specific failures:

| Failure Mode | Impact | Mechanism |
|-------------|--------|-----------|
| **No auto-compaction** | Context grows unbounded across multi-turn sessions | Every turn appends; nothing prunes |
| **No compression strategy** | Every tool output enters context at full size | 40-60% of context is stale tool outputs from 10+ turns ago |
| **No budget awareness** | No mechanism to track remaining context | Hits model limit silently, degrades or hard-stops |
| **No hierarchical context** | Main agent holds all history | "Lost in the middle" -- key middle-context info invisible |
| **No tool-result clearing** | Large outputs persist across turns | file reads, search results stay when no longer needed |
| **No multi-signal retention** | FIFO or nothing | No way to distinguish critical from redundant context |

Estimated token waste: 40-60% of context is stale/redundant content. Anthropic's cookbook confirms: on a 200K-token model, a research agent hard-stops at turn 3 (168,242 tokens) without management. Lyra faces the same failure with added complexity from multi-agent handoffs.

---

## Breakthrough Proposals

Each proposal fuses 2+ independently validated sources into a single, novel mechanism. Ranked by impact x feasibility.

---

### BP1: Layered Compaction Pipeline with Composite Retention Scoring

**Fused sources:** Anthropic 3-Strategy Cookbook [12] + R-KV [4] + COMPASS [5] + mem0 [16]

**The combination:** Anthropic's framework tells us *when* to act (clearing at 60%, compaction at 75%). But it doesn't tell us *what* to keep. R-KV provides the joint importance-redundancy scoring `Z = λ·I − (1−λ)·R` to identify the highest-value content. COMPASS provides the output format (6-section structured brief) so compaction produces a machine-parseable summary, not free-form text. mem0 provides multi-signal fusion (semantic + BM25 + entity) for the relevance dimension.

**Concrete mechanism:**
```
Pipeline: Trigger Check → Clearing → Redundancy Pruning → Structured Compaction → Memory Extraction

1. Trigger: After every 3 turns, compute context utilization
2. If >60%: Clear tool results using Anthropic's clear_tool_uses pattern (zero inference cost)
   - Keep last 4 tool results intact
   - Clear only re-fetchable results (file reads, searches, git diffs)
   - 67% token reduction demonstrated in Anthropic cookbook (128,740 → 43,060)
3. If still >70% after clearing: Apply composite retention scoring per chunk
   - Score(chunk) = 0.5*relevance(embedding_sim) + 0.3*recency(exponential_decay) - 0.2*redundancy(cosine_sim_to_retained)
   - Retain top-K by combined score; prune rest
   - R-KV's λ=0.1 original tuned for token-level; chunk-level uses broader λ=0.2 redundancy weight
4. If still >75% after pruning: Trigger compaction with COMPASS-structured output
   - Summarize history into 6-section brief: Task, Evidence, Constraints, Open Items, Next Actions, Tool Hints
   - Target: ~2,783 tokens (Anthropic's measured summary size)
   - Preserve last 5 turns unsummarized
5. Session end: Extract cross-session knowledge to memory (decisions, facts, open threads)
```

**Why the combination wins:**
- Clearing alone (Anthropic): free but only handles tool results; reasoning bloat persists
- R-KV alone: handles KV cache but not tool result bloat; math-domain only
- COMPASS alone: +110% GAIA but 2.2x token cost; needs preprocessing to be efficient
- Combined: the pipeline applies the cheapest strategy first, escalating only when necessary. R-KV's redundancy term removes what clearing misses. COMPASS-structured output ensures compaction preserves downstream usability.

**Trade-off depth:**
- Clearing invalidates cached prompt prefixes (acknowledged in Anthropic cookbook). Mitigated by `clear_at_least` threshold.
- Redundancy scoring requires pairwise cosine similarity, O(n²) per chunk. Mitigated by chunk-level granularity (100-200 chunks, not per-token).
- COMPASS-structured output adds an LLM call (~2,783 tokens). Justified only when budget is actually exceeded.
- False positive risk: redundancy scoring might flag similar-but-distinct code blocks as redundant. Mitigated by the 0.2 weight keeping relevance dominant.

---

### BP2: Progressive-Disclosure Context Loading with Structural Code Awareness

**Fused sources:** addyosmani/agent-skills [15] + Aider repo map [16] + lean-ctx [14] + CodeComp [2]

**The combination:** addyosmani provides the meta-skill decision tree pattern (50-100 token descriptions resolve to full skills on match). Aider provides the repo map via tree-sitter + PageRank (rank code by relevance to query). lean-ctx provides 10 compression modes (full/map/signatures/diff/etc.) with AST-backed structural understanding. CodeComp provides the structural protection rule: callsites, branch conditions, and return statements must never be evicted during compression.

**Concrete mechanism:**
```
On session start:
1. Inject meta-skill decision tree (addyosmani pattern): 50-100 tokens covering all capabilities
2. Load only currently-relevant skill (match via keyword trigger), not all skills

On code context request:
1. Build repo map (Aider pattern): tree-sitter AST tags → graph → PageRank → top-ranked snippets
2. Apply lean-ctx compression mode based on task type:
   - "add feature" → `signatures` mode (97% compression, 92% quality)
   - "debug error" → `map` mode (97.7% compression, 83% quality)
   - "review code" → `diff` mode (change-focused)
3. Apply CodeComp structural protection layer:
   - Unconditionally retain: function signatures, call expressions, control-flow predicates, return statements
   - Fill remaining budget with PageRank-ranked snippets
   - This mirrors CodeComp's 0.0944 Jaccard finding: attention ≠ structural importance
```

**Why the combination wins:**
- addyosmani alone: no code-specific compression; skills only
- Aider alone: repo map is coarse; no per-skill progressive disclosure
- lean-ctx alone: 10 modes but no skill-based routing; no query-conditioned selection
- CodeComp alone: structural protection but no compression mode selection
- Combined: the full pipeline selects the right compression granularity for the task, protects structurally critical code, and loads only what's needed.

**Trade-off depth:**
- Tree-sitter initial scan latency: 2.69s cold start (per lean-ctx benchmarks). Mitigated by caching AST tags in SQLite.
- PageRank personalization depends on query quality; poor query → poor ranking.
- CodeComp structural protection depends on Joern coverage (Python, C/C++, Java, JS; no Go, Rust, Swift). Lyra should use tree-sitter (broader coverage) for AST-based span identification, with CPG extraction only for supported languages.
- Progressive-disclosure adds latency on skill match (loading full SKILL.md). Mitigated by prefetching most-likely skills.

---

### BP3: Async Context Consolidation with Action-Consistency Guard

**Fused sources:** COMEM [1] + ACON [3] + Context Engineering 2.0 [6]

**The combination:** COMEM provides the k-step-off async pipeline (compression runs in background, agent proceeds with cached context). ACON provides the contrastive failure analysis (compare compressed vs. uncompressed trajectories to identify what information was lost). Context Engineering 2.0 provides the self-baking abstraction (4-level progressive consolidation: raw → summary → schema → cross-session merge).

**Concrete mechanism:**
```
Phase 1 (baseline): Synchronous compaction (BP1 pipeline)
Phase 2 (production): Async consolidation with k-step-off

1. Small compressor model (e.g., Claude Haiku) runs k=4 steps behind main agent
2. Every k steps: compressor produces structured brief from all history up to t-k
3. Agent KV cache invalidated; re-prefilled with summary + k recent turns
4. Between cycles: agent uses cached KV, zero compression latency

Self-baking consolidation loop (Context Eng 2.0):
- Level 1: Raw context logs (always preserved)
- Level 2: Per-session NL summaries (written at session end)
- Level 3: Schema extraction (entities + states + relationships) written to structured store
- Level 4: Cross-session merge with contradiction detection

Contrastive quality guard (ACON):
- Periodically collect trajectory pairs: same task, compressed vs. uncompressed
- Where compressed fails and uncompressed succeeds: extract lost information via LLM
- Refine compaction prompt to preserve that class of information
- Cost: <$2 per benchmark per ACON; $0.0004/example with distilled compressor
```

**Why the combination wins:**
- COMEM alone: 2.08x speedup but 90.9% accuracy recovery; needs quality guard
- ACON alone: optimizes prompt but is synchronous; adds 20-39% latency
- Context Eng 2.0 alone: self-baking pattern is conceptual; needs proven infrastructure
- Combined: async pipeline hides compression latency. Self-baking adds progressive depth. ACON guard catches and fixes compression failures.

**Trade-off depth:**
- k=1 degrades to 57.2% resolve (COMEM): too many uncached prefills. k=16 saturates at 60.2%. Sweet spot k=4.
- Requires two-model serving (compressor + agent). COMEM's 4B model serves ~300 concurrent agents. For Lyra: Haiku-class compressor, Opus/Sonnet agent.
- Summary staleness: agent operates on k-step-old summary. OK for code tasks (COMEM: k=4 gives 62.7%), untested for dialogue/creative.
- Self-baking Level 4 (cross-session merge with contradiction detection) is unsolved in literature. Phase 2 only, with human-in-the-loop for contradictions.

---

### BP4: Orthogonal State Checkpointing with Targeted Summarization

**Fused sources:** Claude Code Checkpointing [13] + Agentic Architectural Patterns [11] + Managing Memory for AI Agents [10]

**The combination:** Claude Code separates checkpointing into three orthogonal dimensions (code state, conversation, decision trace) and provides targeted summarization (summarize-from-here / summarize-up-to-here) instead of all-or-nothing compaction. Agentic Architectural Patterns adds Persistent Instruction Anchoring (critical goals wrapped in semantic tags that survive compaction). Managing Memory adds TTL-based checkpoint cleanup.

**Concrete mechanism:**
```
Session state is versioned in 3 independent dimensions:
1. Knowledge state: artifacts, findings, plan files
2. Conversation state: prompts + agent responses + tool calls
3. Decision trace: router decisions, safety checks, guardrail invocations

Per-turn checkpoint: snapshot all 3 dimensions after each agent turn.

On context pressure:
- summarize-up-to-here: compress early setup (boilerplate, exploration) into summary; keep later context intact
- summarize-from-here: compress side-exploration branches; keep core thread intact

Persistent Instruction Anchoring (from Arsanjani):
- Wrap critical constraints in semantic tags: PERSISTENT_GOAL: [CONSTRAINT]
- These tags pass through the entire agent chain
- Compaction/clearing must not remove tagged spans
- Auditor agent verifies tagged constraints survive compaction

TTL-based cleanup (from Managing Memory):
- Checkpoints older than 30 days: auto-clean
- Session-end: extract decisions/facts to long-term memory before cleanup
```

**Why the combination wins:**
- Claude Code alone: solves checkpointing but doesn't address the instruction drift problem in multi-agent chains
- Arsanjani alone: Instruction Anchoring prevents drift but without checkpointing, there's no recovery mechanism
- Combined: orthogonal dimensions enable surgical rollback (rewind code without losing conversation; rewind conversation without discarding findings). Persistent anchoring ensures critical constraints survive compaction.

**Trade-off depth:**
- 3-dimension checkpointing doubles storage per turn (vs. single-dimension). Mitigated by TTL cleanup and differential storage (only store deltas).
- Instruction Anchoring tags consume context budget (~50-100 tokens per constraint). Justified for safety-critical constraints.
- Bash command changes NOT tracked by checkpointing (Claude Code limitation). Lyra should add filesystem snapshot for critical operations.

---

### BP5: Multi-Signal Retrieval Scoring with Redundancy Penalty for Context Assembly

**Fused sources:** mem0 [16] + R-KV [4] + Memory Survey (Du) [7] + Managing Memory [10]

**The combination:** mem0 provides the proven multi-signal fusion: `semantic + BM25 + entity_boost`. R-KV adds the redundancy penalty term: subtract what's already covered by retained chunks. Memory Survey provides the write-filter-read pipeline with dual-buffer consolidation. Managing Memory adds cascading promotion/demotion based on importance scoring.

**Concrete mechanism (for Lyra's context assembly):**
```
When assembling context for a turn:
1. Candidate pool: all available context chunks (recent messages, tool results, retrieved memories, system prompt sections)
2. Score each candidate:
   Score(c) = 0.35*relevance(embedding_sim_to_query) 
            + 0.25*recency(exponential_decay, half_life=6_turns)
            + 0.15*importance(self_assessed_integer_1_to_10)
            - 0.15*redundancy(max_cosine_sim_to_already_retained)
            + 0.10*entity_boost(query_entities ∩ chunk_entities)
3. Greedy selection: retain top-K by combined score until budget exhausted
4. Write-path filter: before storage, filter low-signal records
   - Deduplicate (MD5 hash check, per mem0 V3)
   - Importance score threshold (keep only >3/10)
   - Metadata tag (timestamp, session_id, task_label)
5. Dual-buffer consolidation (Memory Survey):
   - New memories sit in "hot buffer" (probation period)
   - Promoted to long-term only after passing: re-verification + dedup + importance check
```

**Why the combination wins:**
- mem0 alone: good retrieval but no redundancy handling; additive-only scoring
- R-KV alone: redundancy detection but at token-level within KV cache; not at chunk-level for context assembly
- Memory Survey alone: provides the architecture but no concrete scoring formula
- Combined: the 5-term scoring function is the first to apply redundancy-aware pruning at the context assembly level. Each term is independently validated: relevance (mem0), recency (Memory Survey), importance (Managing Memory), redundancy (R-KV), entity boost (mem0).

**Trade-off depth:**
- 5-term scoring requires 5 hyperparameter weights. Initial values from source papers; tune on Lyra-specific benchmarks.
- Entity extraction requires spaCy NER (per mem0). Lightweight alternative: regex-based proper noun extraction.
- Redundancy computation: pairwise cosine similarity grows O(n²). Capped at 200 candidate chunks → ~40K comparisons, negligible.
- Self-assessed importance is noisy (LLMs over-estimate importance). Two mitigations: (a) calibrate with historical frequency of reference, (b) decay importance if never retrieved.

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) — "Safe Primitives, Zero Regret"

**Milestone 1.1: Tool-Result Clearing (Day 1-3)**
- [ ] Implement tool-result identification: flag results >5K chars from re-fetchable tools (Read, WebFetch, Bash, Grep)
- [ ] Implement clearing with `clear_at_least` threshold (minimum 10K tokens freed to justify cache invalidation)
- [ ] Keep last 4 tool results intact; never clear current-turn results
- [ ] Integration point: post-tool-execution hook, before result enters context
- [ ] **Evidence:** Anthropic Cookbook [12] — clearing 3 file reads reduces 128,740 → 43,060 tokens (67%), zero inference cost
- [ ] **Dependency:** None (works independently)

**Milestone 1.2: Token Budget Monitor (Day 2-4)**
- [ ] Per-turn token estimation (chars/4 heuristic, with tiktoken for precise checks)
- [ ] Track budget allocation: system prompt (15%), tools (5%), recent history (30%), memory (10%), current output (40%)
- [ ] Expose budget as observability metric (log per-turn)
- [ ] Alert at 60% (clearing trigger) and 75% (compaction trigger)
- [ ] **Evidence:** Context Engineering 2.0 [6] — context window fullness >50% degrades coding performance (Osmani, 2025)
- [ ] **Dependency:** None

**Milestone 1.3: Progressive-Disclosure Skill Loading (Day 4-7)**
- [ ] Implement meta-skill decision tree (addyosmani pattern): 50-100 token descriptions per skill
- [ ] Load full SKILL.md only on keyword match
- [ ] Prefetch most-likely skills (top 3 by historical frequency)
- [ ] **Evidence:** addyosmani/agent-skills [15] — <300 line skills, progressive disclosure
- [ ] **Dependency:** Skill/plugin system (§4.6)

### Phase 2: Intelligent Pruning (Weeks 2-4) — "Smart What, Not Just When"

**Milestone 2.1: Redundancy-Aware Context Pruning (Week 2-3)**
- [ ] Implement chunk-level redundancy scoring: pairwise cosine similarity of chunk embeddings
- [ ] Implement composite retention score: `0.35*relevance + 0.25*recency + 0.15*importance - 0.15*redundancy + 0.10*entity_boost`
- [ ] Greedy budget-filling selection
- [ ] Tune weights on Lyra-specific benchmarks (start with source-paper values)
- [ ] **Evidence:** R-KV [4] — `Z = λ·I − (1−λ)·R`, ~100% accuracy at 34% retention; mem0 [16] — multi-signal fusion with adaptive BM25
- [ ] **Dependency:** Milestone 1.2 (budget monitor), Embedding infrastructure

**Milestone 2.2: Structural Code Protection (Week 3-4)**
- [ ] Integrate tree-sitter AST extraction for all Lyra-supported languages
- [ ] Identify structurally critical spans: function signatures, call expressions, control-flow predicates, return statements
- [ ] Unconditionally protect identified spans during pruning
- [ ] Fill remaining budget with relevance-ranked content
- [ ] **Evidence:** CodeComp [2] — 0.0944 Jaccard between attention and structure, 12x accuracy recovery; callsite retention 1.00
- [ ] **Dependency:** Milestone 2.1, tree-sitter grammars

**Milestone 2.3: COMPASS-Structured Compaction (Week 4)**
- [ ] Implement 6-section structured brief template: Task, Evidence, Constraints, Open Items, Next Actions, Tool Hints
- [ ] Compaction prompt: summarize history → structured brief (target 2-3K tokens)
- [ ] Preserve last 5 turns unsummarized
- [ ] Rolling note store: accumulate evidence, constraints, open items across compaction events
- [ ] **Evidence:** COMPASS [5] — +110% GAIA over SAS, 200-300 token typical brief; Anthropic Cookbook [12] — ~2,783 token summary size
- [ ] **Dependency:** Milestone 1.1 (clearing), Milestone 1.2 (budget monitor)

### Phase 3: Production Scale (Weeks 5-8) — "Latency Hiding, Cross-Session"

**Milestone 3.1: Orthogonal State Checkpointing (Week 5-6)**
- [ ] Implement 3-dimension state versioning: Knowledge, Conversation, Decision trace
- [ ] Per-turn checkpoint with differential storage
- [ ] Targeted summarization: summarize-from-here and summarize-up-to-here
- [ ] TTL-based cleanup (30 day default)
- [ ] Persistent Instruction Anchoring: wrap PERSISTENT_GOAL tags
- [ ] **Evidence:** Claude Code Checkpointing [13] — orthogonal dimensions, targeted summarization; Arsanjani [11] — Instruction Anchoring
- [ ] **Dependency:** Milestone 2.3 (compaction)

**Milestone 3.2: Async Memory Model (COMEM pattern) (Week 6-8)**
- [ ] Select/train small compressor model (Claude Haiku target)
- [ ] Implement k-step-off async pipeline (k=4 default)
- [ ] KV cache management: invalidate on summary update, cache between cycles
- [ ] Measure: latency speedup vs. accuracy preservation on Lyra benchmarks
- [ ] **Evidence:** COMEM [1] — 2.08x speedup at batch=128, 90.9% accuracy recovery, KV bounded at 1-37% vs. 34-96% full-context
- [ ] **Dependency:** Milestone 2.3 (structured compaction), 2-model serving infra

**Milestone 3.3: Contrastive Compaction Quality Guard (Week 8)**
- [ ] Collect trajectory pairs: compressed vs. uncompressed on same Lyra tasks
- [ ] Identify compression failures: tasks succeeding uncompressed but failing compressed
- [ ] Generate natural language feedback: what information was lost?
- [ ] Refine compaction prompt via feedback loop
- [ ] **Evidence:** ACON [3] — contrastive trajectory feedback, <$2 per benchmark optimization, 26-54% peak token reduction
- [ ] **Dependency:** Milestone 2.3 (compaction), evaluation framework

### Phase 4: Continuous Improvement (Ongoing)

- [ ] A/B test compaction strategies on Lyra benchmarks
- [ ] Tune all hyperparameters (weights, thresholds, k) on Lyra-specific data
- [ ] Self-baking consolidation loop (Context Eng 2.0 Level 3-4)
- [ ] Cross-session coherence with contradiction detection
- [ ] Monitor literature for selective forgetting and causal retrieval breakthroughs
- [ ] **Evidence:** Context Engineering 2.0 [6] — progressive abstraction; Memory Survey [7] — dual-buffer consolidation

---

## Architecture Diagram

```mermaid
graph TB
    subgraph "Agent Loop"
        TURN[Agent Turn]
        TOOL[Tool Execution]
        RESULT[Tool Result]
    end

    subgraph "Phase 1: Safe Primitives"
        CLEAR[Tool-Result Clearing<br/>Re-fetchable, >5K chars<br/>Anthropic Cookbook]
        BUDGET[Token Budget Monitor<br/>Per-Turn Tracking<br/>60%/75% Triggers]
        SKILL[Progressive-Disclosure<br/>Meta-Skill → Match → Load<br/>addyosmani Pattern]
    end

    subgraph "Phase 2: Intelligent Pruning"
        REDUND[Redundancy Scoring<br/>R-KV: λ·I − (1-λ)·R<br/>Chunk-Level Cosine Sim]
        STRUCT[Structural Protection<br/>CodeComp: AST Spans<br/>Callsites, Branches, Returns]
        COMPACT[Structured Compaction<br/>COMPASS 6-Section Brief<br/>2-3K Token Target]
    end

    subgraph "Phase 3: Production Scale"
        CKPT[Orthogonal Checkpointing<br/>Knowledge/Conversation/Decision<br/>Targeted Summarization]
        ASYNC[Async Memory Model<br/>COMEM k-Step-Off<br/>k=4, Haiku Compressor]
        GUARD[Contrastive Quality Guard<br/>ACON Failure Analysis<br/>Prompt Refinement]
    end

    subgraph "Budget Tracking"
        USAGE[Usage Monitor]
        TRIGGER[Auto-Trigger<br/>60% → Clear<br/>70% → Prune<br/>75% → Compact]
    end

    TURN -->|After turn| BUDGET
    TOOL -->|Before context| CLEAR
    CLEAR -->|Cleared| RESULT
    RESULT --> SKILL
    SKILL --> REDUND
    BUDGET -->|>60%| CLEAR
    BUDGET -->|>70% after clear| REDUND
    REDUND --> STRUCT
    STRUCT -->|Pruned context| COMPACT
    BUDGET -->|>75% after prune| COMPACT
    COMPACT -->|Structured brief| TURN

    TURN -->|Per turn| CKPT
    COMPACT -->|Phase 2 stable| ASYNC
    ASYNC --> GUARD
    GUARD -->|Refined prompt| COMPACT

    BUDGET --> USAGE
    USAGE --> TRIGGER
    TRIGGER --> CLEAR
    TRIGGER --> REDUND
    TRIGGER --> COMPACT
```

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Source |
|---|------|-----------|--------|------------|--------|
| R1 | Compaction loses critical information | Medium | High | Keep last 5 turns intact; preserve decisions + open threads; COMPASS 6-section brief includes Evidence and Constraints sections; ACON contrastive guard detects losses | COMPASS [5], ACON [3] |
| R2 | Tool-result clearing removes needed context | Medium | Medium | Only clear re-fetchable results (file reads, searches); never clear current-turn results; keep=4 provides recency buffer | Anthropic Cookbook [12] |
| R3 | Redundancy scoring flags similar-but-distinct code as redundant | Medium | Medium | Low redundancy weight (0.15 in composite score); structural protection overrides redundancy for critical spans; tune threshold on Lyra benchmarks | R-KV [4], CodeComp [2] |
| R4 | Auto-compaction triggers mid-reasoning-chain | Medium | High | "Compaction lock" — agent signals in-reasoning-chain state, compaction deferred; minimum interval between compactions (20 turns) | Reviewer feedback |
| R5 | Cheap model produces poor compaction summaries | Medium | Medium | Route compaction to at least mid-tier (Sonnet); Haiku only for preview summaries; ACON contrastive guard catches quality drops | ACON [3] |
| R6 | COMPASS hierarchy adds latency | Medium | Medium | Meta-Thinker runs async on cheap model; Context Manager is a prompt, not a separate model call (until Phase 3); structured brief replaces full history, reducing downstream latency | COMPASS [5] |
| R7 | k-step-off summary staleness causes errors | Medium | Medium | k=4 is empirically stable (COMEM: 62.7% vs. 57.2% at k=1); k tuned per task type; contrastive guard detects staleness failures | COMEM [1] |
| R8 | KV cache invalidation penalty negates compaction savings | Medium | Low | clear_at_least threshold ensures net savings; k-step-off amortizes prefills over k-1 cached steps; Anthropic: 67% reduction from clearing alone | COMEM [1], Anthropic Cookbook [12] |
| R9 | Structural protection fails on unsupported languages | Low | Medium | Tree-sitter covers 100+ languages; fallback to embedding-only scoring when AST unavailable; Joern CPG only for CPG-supported languages | CodeComp [2] |

---

## Impact x Effort Matrix

| Proposal | Impact (1-5) | Effort (1-5) | Impact/Effort | Phase | Rationale |
|----------|-------------|-------------|---------------|-------|-----------|
| **BP1: Layered Compaction Pipeline** | 5 | 3 | **1.67** | Phases 1-2 | Highest-leverage single intervention. Clearing is free (67% reduction, zero inference cost). Redundancy pruning extends effective session length. Structured compaction preserves downstream usability. Evidence from 4 independent sources. |
| **BP2: Progressive-Disclosure Loading** | 4 | 2 | **2.00** | Phase 1 | Lowest effort for immediate gains. Production-proven (Claude Code, Aider, Cursor). Meta-skill decision tree is ~100 lines. Repo map adapts cleanly from Aider. |
| **BP4: Orthogonal Checkpointing** | 4 | 3 | **1.33** | Phase 3 | Essential for production reliability. Enables surgical rollback. Targeted summarization is more precise than all-or-nothing compaction. Requires storage infrastructure. |
| **BP3: Async Consolidation** | 4 | 4 | **1.00** | Phase 3 | Highest theoretical ceiling (2.08x speedup). But requires two-model serving, GRPO training, async coordination. Only justified when Phase 1-2 bottlenecks are measured at production scale. |
| **BP5: Multi-Signal Retention** | 3 | 3 | **1.00** | Phase 2 | Improves context quality but is an optimization on top of BP1. Five-term scoring adds tuning surface. Most impactful when combined with BP1's pruning stage. |

**Priority ordering:** BP2 → BP1 (Clearing) → BP1 (Pruning) → BP1 (Compaction) → BP5 → BP4 → BP3

---

## Multi-Provider Note

Context management is agent-side, not provider-side. All strategies operate on Lyra's internal message representation before encoding to provider format:

- **Compaction** works identically across Claude, DeepSeek, GPT — it's Lyra's own summarization call
- **Tool-result clearing** is message manipulation, no provider involvement
- **Redundancy pruning** uses Lyra's embedding infrastructure, provider-agnostic
- **Structural protection** uses tree-sitter AST, language-agnostic
- **Progressive disclosure** is file-level organization, provider-agnostic

The only provider-specific consideration: different context window sizes affect threshold values. Store per-provider thresholds in the CapabilityMatrix:
- Claude Opus 4.5: 200K → compact at 150K, clear at 120K
- Claude Sonnet 4.6: 200K → same thresholds
- DeepSeek-V3: 128K → compact at 96K, clear at 76K
- GPT-5: 128K → compact at 96K, clear at 76K

---

## (A) Parity vs (B) Breakthrough

### (A) Parity — What Claude Code already does
- Context compaction via `compact_20260112` for long sessions
- Tool-result clearing via `clear_tool_uses_20250919` for bulky re-fetchable results
- Memory tool for cross-session persistence
- Checkpointing with targeted summarization (summarize-from-here/up-to-here)

### (B) Breakthrough — What Lyra adds

| Breakthrough | Mechanism | Evidence | vs. Claude Code |
|-------------|-----------|----------|----------------|
| **Composite Retention Scoring** | `0.35*r + 0.25*t + 0.15*i - 0.15*d + 0.10*e` multi-signal scoring before compaction | R-KV [4], mem0 [16] | Claude Code has no redundancy penalty; keeps duplicates that attention over-values |
| **Structural Code Protection** | AST-based unconditional protection of callsites, branches, returns during pruning | CodeComp [2] — 0.0944 Jaccard attention vs. structure | Claude Code has no structural awareness in compaction |
| **Progressive-Disclosure Context Loading** | Meta-skill decision tree → match → load; repo map via tree-sitter + PageRank | addyosmani [15], Aider [16], lean-ctx [14] | Claude Code loads all available context; no structural ranking |
| **COMPASS-Structured Compaction Output** | 6-section brief (Task, Evidence, Constraints, Open Items, Next Actions, Tool Hints) replaces monolithic summary | COMPASS [5] — +110% GAIA | Claude Code produces free-form summaries |
| **Two-Stage Escalation with Redundancy Pruning** | Clear at 60% → Prune at 70% → Compact at 75%. Escalates only when necessary. | Anthropic Cookbook [12], R-KV [4] | Claude Code: single threshold, direct compaction |
| **Async Compression Pipeline** (Phase 3) | k-step-off model, compressor runs in background, 2.08x speedup at scale | COMEM [1] | Claude Code compaction is synchronous |
| **Orthogonal State Dimensions** | Independent versioning of Knowledge/Conversation/Decision; surgical rollback | Claude Code Checkpointing [13], Arsanjani [11] | Claude Code has 2 dimensions (code + conversation); Lyra adds decision trace |

---

## Baseline Delta

| Dimension | Before (Lyra current) | Phase 1 (Week 2) | Phase 2 (Week 4) | Phase 3 (Week 8) |
|-----------|----------------------|-------------------|-------------------|-------------------|
| Context growth | Unbounded | Bounded: clear at 60% | Bounded + pruned: clear + redundancy removal | Bounded + pruned + async |
| Tool output size | Full output always | Cleared when re-fetchable | Cleared + compressed (progressive-disclosure) | Cleared + compressed + async |
| History retention | Complete (STM ring buffer) | Summarized >5 turns ago | 6-section structured brief | k-step-off async summary |
| Cross-session memory | None | Memory extraction at session end | Structured memory with dual-buffer | Self-baking consolidation |
| Context architecture | Flat | 3-strategy framework | COMPASS-structured brief | 3-agent hierarchy (Phase 3) |
| Budget allocation | None | Per-section dynamic | Multi-signal with redundancy penalty | Adaptive per task type |
| KV cache pressure | Unmanaged | Bounded by clearing | Bounded + pruned | 1-37% GPU HBM (COMEM) |
| Latency overhead | N/A | Clearing: 0ms | Compaction: ~2-3s LLM call | k-step-off: ~0ms added to critical path |

---

## References

1. Zhang et al., "COMEM: Context Management with A Decoupled Long-Context Model," ICML 2026, arXiv:2605.30842v1. Decoupled async memory model, k-step-off pipeline, 2.08x speedup.
2. Chen et al., "CodeComp: Structural KV Cache Compression for Agentic Coding," arXiv:2604.10235v1, Apr 2026. 0.0944 Jaccard attention vs. structure, 12x accuracy recovery.
3. Kang et al., "ACON: Optimizing Context Compression for Long-horizon LLM Agents," ICML 2026, arXiv:2510.00615v3. Contrastive trajectory feedback, <$2/benchmark optimization.
4. Cai et al., "R-KV: Redundancy-aware KV Cache Compression for Reasoning Models," NeurIPS 2025, arXiv:2505.24133v4. Joint importance-redundancy scoring, ~100% accuracy at 34% retention.
5. Wan et al., "COMPASS: Enhancing Agent Long-Horizon Reasoning with Evolving Context," arXiv:2510.08790v1, Oct 2025. 6-section structured briefs, +110% GAIA.
6. Hua et al., "Context Engineering 2.0: The Context of Context Engineering," arXiv:2510.26493v1, Oct 2025. Self-baking consolidation, 4-level progressive abstraction.
7. Du, "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers," arXiv:2603.07670v1, Mar 2026. POMDP formalization, Pattern B/C, write-filter-read pipeline.
8. Hu et al., "Memory in the Age of AI Agents: A Survey," arXiv:2512.13564v2, Jan 2026. Forms-Functions-Dynamics taxonomy, 27 benchmarks cataloged.
9. Gulli, *Agentic Design Patterns*, Ch.4, Ch.8, 2025. Dual Memory Architecture, Context Engineering as systematic discipline.
10. *Managing Memory for AI Agents*, Ch.1-5, 2025. Importance scoring, cascading memory, multi-signal retrieval.
11. Arsanjani & Bustos, *Agentic Architectural Patterns*, Ch.5-6, 2026. Shared Epistemic Memory, Persistent Instruction Anchoring.
12. Anthropic, "Context Engineering: Memory, Compaction, and Tool Clearing," platform.claude.com/cookbook, Mar 2026. 3 API primitives, diagnostic framework, clearing = 67% reduction.
13. Anthropic, "Checkpointing," code.claude.com/docs, 2026. Orthogonal dimensions, targeted summarization, 30-day retention.
14. yvgude/lean-ctx, GitHub, v3.7.x, 2025. 10 compression modes, 97.7% code map compression, 85.5% session savings.
15. addyosmani/agent-skills, GitHub, 2025. Progressive-disclosure skill loading, meta-skill decision tree, <300 line skills.
16. Aider-AI/aider, GitHub, 2025. Repo map via tree-sitter + PageRank, ChatSummary compaction.
17. Lyra synthesis/context-engineering.md, Jun 7, 2026. Thematic synthesis of 18 papers + 5 books + 4 web sources.

---

## Changelog
- Run 2 (Jun 7, 2026): Complete rewrite with deep-read evidence from 15+ sources. Restructured into 5 Breakthrough Proposals (fused from 2+ sources each). Added Phase 1-3 roadmap with milestones. Added Impact x Effort matrix. Added Risk Register with source-cited mitigations. Replaced speculative design with evidence-backed mechanisms.
- Run 1 (Jun 3, 2026): Initial plan -- 3-strategy framework, lean-ctx compression, auto-compaction trigger, COMPASS hierarchy, minimal context strategy.
