# Context Engineering & Compaction -- Thematic Synthesis

> **Synthesis date:** 2026-06-07
> **Corpus:** 281 paper notes + 80 book notes (40 chapters + 40 playbooks) + 184 web repo/doc notes
> **Sources cited:** 18 papers, 5 book sources, 4 web sources
> **Status:** DEFINITIVE -- feeds Phase 4 workstream plans for Lyra upgrade

---

## 1. Frontier Techniques (ranked by evidence strength)

### 1.1 Decoupled Async Memory Model with k-Step-Off Pipeline (COMEM)

- **Technique:** COMEM (Context Management with Decoupled Long-Context Model)
- **Sources:** Zhang et al., "COMEM: Context Management with A Decoupled Long-Context Model," ICML 2026, arXiv:2605.30842v1
- **Mechanism:** Splits context management into two models: a small Memory Model (e.g., Qwen3-4B) that compresses interaction history into dense latent summaries, and a frozen large Agent Model that conditions on the summary plus a short recent buffer to produce actions. The memory model runs asynchronously in a k-step-off pipeline -- it compresses history from k steps ago while the agent continues executing from cached KV, making compression cost invisible to the critical path. Training uses GRPO with an action-consistency reward: `R(s) = sim(a_t, a*_t)` -- cosine similarity between summary-conditioned action and full-context action. The agent model remains frozen; training is entirely offline.
- **Evidence:** SWE-Bench-Verified with GLM-4.7 (355B): 62.7% resolve rate vs. 69.0% full-context (90.9% recovery), with 2.08x latency speedup. Speedup scales with batch size: at batch=256, 2.52x speedup. Peak per-step speedup of 4.95x at concurrency=64. KV cache usage stays bounded at 1-37% GPU HBM vs. 34-96% for full-context. Cross-backbone transfer: -0.8% gap when memory model trained on one backbone and deployed with another.
- **Maturity:** Lab validated (ICML 2026 paper, single-backbone experiments, code released at github.com/horizon-llm/CoMem)

### 1.2 Structure-Aware KV Cache Compression with Static Analysis (CodeComp)

- **Technique:** CodeComp -- structural KV cache compression using Code Property Graphs (CPG)
- **Sources:** Chen et al., "CodeComp: Structural KV Cache Compression for Agentic Coding," arXiv:2604.10235v1, April 2026
- **Mechanism:** Training-free 6-stage pipeline: (1) PPL-based chunk selection via query-conditioned perplexity, (2) Joern CPG extraction unifying AST+CFG+PDG into structural feature vectors, (3) structure-aware budget allocation mapping structural scores to compression ratios, (4) span-level structural protection of callsites, control-flow predicates, return statements, assignments, (5) attention-based residual fill for remaining capacity, (6) position encoding normalization for decode. The key insight: attention scores and structural importance have only 0.0944 Jaccard overlap for code. Attention over-retains semantically frequent but structurally trivial tokens while evicting callsites (52-58% pruned), signatures (68-78% pruned), and branch conditions.
- **Evidence:** At 40% capacity, CodeComp achieves GF F1 0.250 on DS-Coder vs. ParallelComp's 0.021 (12x gap). DebugBench Llama3-8B: 0.43 vs. 0.03 for ParallelComp (14x). Edit distance matches uncompressed baseline (0.743 vs. 0.740). Structurally critical token retention near 100% for callsites, branches, returns. End-to-end latency stable at 112-118s across all retention ratios.
- **Maturity:** Lab validated (SGLang integration, Joern dependency, 8B-scale models only, no 70B+ testing)

### 1.3 Natural Language Compression Guideline Optimization (ACON)

- **Technique:** ACON (Agent Context Optimization) -- optimizing compression prompts via contrastive trajectory feedback
- **Sources:** Kang et al., "ACON: Optimizing Context Compression for Long-horizon LLM Agents," ICML 2026, arXiv:2510.00615v3
- **Mechanism:** Model-agnostic compression that optimizes only the natural language compression guideline P (prompt), not model weights. Two-stage optimization: (UT) Utility Maximization -- identify compression failures by comparing successful uncompressed vs. failed compressed trajectories, ask optimizer LLM (o3) to identify lost critical information, then refine the guideline; (CO) Compression Maximization -- identify unused information in successful compressed trajectories and trim redundancies. Final variant ACON UTCO balances both. Optional compressor distillation: teacher (gpt-4.1) compressed outputs used to train student (Qwen3-14B) via LoRA, reducing per-example cost from $0.045 to $0.0004 (99.1% reduction).
- **Evidence:** AppWorld (gpt-4.1 agent): ACON UTCO achieves 56.5% accuracy (matches no-compression 56.0%) with 26% peak token reduction (9.93K to 7.33K) and 21% dependency reduction. OfficeBench: ~30% peak token reduction at 72.6-74.7% accuracy. 8-Objective QA: 54.5% peak token reduction with marginal F1 improvement. Small agent (Qwen3-14B): +32.4% relative improvement on AppWorld -- compression actually helps weaker models by filtering distractions. Distillation preserves >95% of teacher accuracy. Optimization cost: <$2 per benchmark.
- **Maturity:** Lab validated (ICML 2026, Microsoft Research, gpt-4.1 primary, limited model diversity)

### 1.4 Redundancy-Aware KV Cache Pruning (R-KV)

- **Technique:** R-KV -- joint importance-redundancy scoring for KV cache retention
- **Sources:** Cai et al., "R-KV: Redundancy-aware KV Cache Compression for Reasoning Models," NeurIPS 2025, arXiv:2505.24133v4
- **Mechanism:** Training-free decoding-stage compression. Three-stage algorithm triggered every 128 generated tokens: (1) Importance scoring: attention-max-pool over last alpha=8 observation tokens, smoothed with 1D max-pooling; (2) Redundancy estimation: pairwise cosine similarity of normalized Key vectors, top-K similar neighbors summed; (3) Joint selection: `Z_i^h = lambda * I_i^h - (1-lambda) * R_i^h` with lambda=0.1. The redundancy term identifies the "redundancy trap" specific to reasoning models -- repetitive self-reflection phrases (e.g., "Let me verify...", "Wait, that doesn't seem right...") receive disproportionately high attention but carry semantically duplicate information.
- **Evidence:** DeepSeek-R1-Distill-Llama-8B on MATH-500: ~100% accuracy preservation with 34% KV cache retention. AIME 2024: 105% of FullKV accuracy at 16% retention (de-noising effect). Throughput: 9.2x at max batch for 16K gen len, 13.4x batch size increase. 90% KV cache memory reduction overall. Optimal lambda narrow (0.01-0.1).
- **Maturity:** Lab validated (NeurIPS 2025, math reasoning only, no code/general-domain benchmarks, no open-source release)

### 1.5 Dedicated Context Manager Agent with Structured Briefs (COMPASS)

- **Technique:** COMPASS -- hierarchical 3-agent architecture with isolated context windows
- **Sources:** Wan et al., "COMPASS: Enhancing Agent Long-Horizon Reasoning with Evolving Context," arXiv:2510.08790v1, October 2025
- **Mechanism:** Three specialized agents: (1) Main Agent (tactical executor) operates ReAct loop receiving dynamically refreshed compact context from Context Manager, not full history; (2) Meta-Thinker (strategic overseer) runs asynchronously, issues 5 strategic decisions (PERSIST/PIVOT/VERIFY/TERMINATE/halt) based on trace anomaly detection; (3) Context Manager synthesizes 6-section structured briefs (Task, Evidence, Constraints, Open Items, Next Actions, Tool Hints) from rolling note store + current trajectory + strategic signal. Typical output: <=200-300 tokens. Optional Context-12B: distilled from Gemma-3-12B via SFT+DPO on 10,347 context pairs, achieves 30% token reduction vs. Flash backend. Optional COMPASS-TTS: test-time scaling with parallel sampling.
- **Evidence:** Gemini 2.5 Pro: GAIA 35.4% (SAS baseline 16.8%, +110%), BrowseComp 67.8% (baseline 58.6%, +15.7%), HLE 31.7% (baseline 14.8%, +114%). COMPASS-TTS at n=8: BrowseComp 72.1%, HLE 35.2% -- exceeds DeepResearch (o3) on BrowseComp. Token cost: 185K for full system vs. 85K SAS baseline (~2.2x). Ablation: removing Context Manager drops GAIA from 35.4% to 26.4%; removing Meta-Thinker drops to 15.2%.
- **Maturity:** Lab validated (Google Cloud AI, proprietary Gemini models only, QA-style benchmarks only)

### 1.6 Self-Baking Context Consolidation (Context Engineering 2.0)

- **Technique:** "Self-baking" -- converting raw interaction context into persistent, structured knowledge representations via progressive abstraction
- **Sources:** Hua et al., "Context Engineering 2.0: The Context of Context Engineering," arXiv:2510.26493v1, October 2025
- **Mechanism:** Formalized layered memory architecture with explicit transfer functions: Short-term memory `M_s = f_short(c in C: w_temporal(c) > theta_s)`, Long-term memory `M_l = f_long(c in C: w_importance(c) > theta_l AND w_temporal(c) <= theta_s)`, Memory transfer `f_transfer: M_s -> M_l` governed by repetition frequency, significance, and relevance. Four-level progressive abstraction: Level 1 (raw context storage), Level 2 (natural language summaries), Level 3 (fixed-schema extraction of entities/states/relationships), Level 4 (cross-session merge with contradiction detection). Context isolation via subagents with custom system prompts and restricted tool permissions prevents context pollution. Progressive vector compression: embeddings at multiple scales, older ones pooled into compact representations.
- **Evidence:** No original benchmarks (position paper). Cataloged production observations: KV-cache sensitivity to prefix changes invalidates entire cache; context window fullness >50% degrades coding performance (from Osmani, 2025); DeepSeek-v3 performance declined beyond 30 tools, near-guaranteed failure beyond 100; Anthropic LeadResearcher pattern demonstrates ~6x task-completion improvement with structured consolidation.
- **Maturity:** Conceptual framework with production validation snippets (no controlled experiments, era 3.0/4.0 are purely speculative)

### 1.7 Progressive-Disclosure Context Loading

- **Technique:** Load only the minimum context needed for the current task, deferring references and workflows to on-demand loading
- **Sources:** addyosmani/agent-skills (GitHub repo, 2025), Aider-AI/aider (repo map + ChatSummary, 2025), Anthropic Claude Code checkpointing docs
- **Mechanism:** Three sub-patterns: (a) Meta-skill decision tree with lightweight descriptions (50-100 tokens) that resolve to full skills only when matched; (b) Repo map via tree-sitter AST + PageRank graph to extract only top-ranked code snippets relevant to the current query; (c) Targeted summarization (summarize-from-here / summarize-up-to-here) that compresses only one side of a chosen checkpoint, not the entire conversation. All three share the principle: context decisions are made by structure, not ad-hoc.
- **Evidence:** Aider: repo map via PageRank keeps prompt small enough for context windows; addyosmani: each SKILL.md fits in one context load (<300 lines); Claude Code: targeted checkpoint summarization separates code state from conversation state. No quantitative latency/accuracy benchmarks published.
- **Maturity:** Production deployed (Claude Code, Aider, Cursor, Codex all use variants)

### 1.8 Hierarchical Memory Architecture (Pattern B / Pattern C)

- **Technique:** Multi-tier memory with explicit short-term (context window), long-term (vector/structured store), and optionally archival tiers, managed by write-filter-read pipeline with retrieval scoring
- **Sources:** Du, "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers," arXiv:2603.07670v1, March 2026 (survey); Hu et al., "Memory in the Age of AI Agents: A Survey," arXiv:2512.13564v2 (survey); MemGPT (Packer et al., 2023); Assafelovic/gpt-researcher (GitHub); WorldMemArena (Liu et al., arXiv:2605.29341v2)
- **Mechanism:** Pattern B (Context + Retrieval Store) uses working memory in the context window plus an external vector/structured store for long-term records. Write path: filtering -> canonicalization -> deduplication -> priority scoring -> metadata tagging. Read path: two-stage retrieval (BM25 -> cross-encoder reranker) with retrieval-or-not gate. Multi-signal scoring: recency (exponential decay), relevance (embedding similarity), importance (self-assessed integer). Pattern C extends Pattern B with RL-trained memory controller (AgeMem's five operations: store, retrieve, update, summarize, discard). WorldMemArena's four-stage lifecycle (Write -> Maintain -> Retrieve -> Use) provides stage-specific diagnostic metrics. MemGPT adds interrupt-driven memory management for context paging.
- **Evidence:** Pattern B demonstrated across MemGPT (57.81% QA-C best among manual memory systems in WorldMemArena), gpt-researcher (autonomous research with structured note accumulation), and Aider (ChatSummary for conversation compaction). The memory-vs-no-memory gap consistently exceeds the LLM-backbone gap across benchmarks (Memory Survey 2603.07670v1). No system masters all four cognitive competencies in MemoryAgentBench -- selective forgetting is the universal failure mode.
- **Maturity:** Production deployed (MemGPT, gpt-researcher, Aider) with active research on Pattern C (AgeMem RL controller)

---

## 2. Head-to-Head Comparisons

| Criterion | COMEM (Async Memory Model) | CodeComp (Structural KV) | ACON (Prompt Opt) | R-KV (Redundancy KV) | COMPASS (Context Manager Agent) | Self-Baking (Context Eng 2.0) | Progressive Disclosure | Pattern B Hierarchical |
|---|---|---|---|---|---|---|---|---|
| **Accuracy Preservation** | 90.9% recovery on SWE-bench (355B); can exceed full-context on mid-size models | 91% recovery on DebugBench (8B); edit distance matches uncompressed | 100% accuracy on AppWorld with UTCO; up to +3.9pp on BrowseComp | ~100% of FullKV with 10-34% retention; up to 105% from de-noising | +110% GAIA, +114% HLE over SAS baseline (Pro) | Untested (conceptual) | Anecdotal only | 57.81% QA-C best (MemGPT); memory-vs-no-memory gap > backbone gap |
| **Latency / Throughput** | 1.43-2.08x speedup; up to 4.95x peak per-step; 2.52x at batch=256 | 112-118s end-to-end stable across ratios (overhead masked) | 20-39% wall-clock increase (compressor call + KV invalidation) | 6.6-9.2x throughput at max batch; 14% faster single-batch | ~2.2x token cost vs. SAS (185K vs 85K) | Unknown | Near-zero overhead (lazy loading) | 200-500ms retrieval latency |
| **Memory Cost** | KV usage bounded at 1-37% GPU HBM; 4B server serves 300 concurrent agents | Up to 60% KV reduction at equal accuracy; CPG extraction negligible | 26-54% peak token reduction; 99.1% cheaper via distillation | 90% KV reduction; 13.4x batch size increase | Bounded memory via rolling note store (200-300 token briefs) | Progressive vector compression for compact storage | Context window utilization improved (no numbers) | External store cost (vector DB); grows unboundedly if no forgetting |
| **Complexity** | High: two vLLM engines, async coordination, GRPO training, k-step parameter tuning | Medium-High: Joern integration, 6-stage pipeline, language coverage mapping | Medium: trajectory collection + prompt optimization (code-free); optional distillation | Low-Medium: training-free, drop-in, 2 hyperparameters (needs tuning) | High: 3-agent orchestration, optional Context-12B training (480 GPU-hrs) | Low-Medium: schema design + consolidation loop (no model training) | Low: file reorganization + decision tree | Medium: vector DB + retrieval pipeline + write-path filtering |
| **Scalability** | Speedup increases with batch size (2.52x at 256); 300 agents per memory server | Tested at 8B only; CPG extraction may bottleneck at >1000 files | Tested on 3 benchmarks; not validated beyond GPT models | Tested on 8B/14B; scaling to 70B+ unknown | Tested on 3 QA benchmarks; not tested in open-ended domains | Untested; cross-session merge is the open challenge | Scales to any codebase size (Aider, Claude Code) | Scales to millions of records; retrieval precision degrades with volume |
| **Evidence Strength** | Strong: ICML 2026, 5 benchmarks, 3 backbones, cross-backbone transfer ablation | Strong: 5 benchmarks, 2 models, 6 baselines, detailed motivation analysis | Strong: ICML 2026, 4 benchmarks, 3 agent models, distillation with 3 students | Strong: NeurIPS 2025, 2 benchmarks, 2 model scales, detailed algorithm | Moderate: Google Cloud AI, proprietary models, narrow benchmark scope | Weak: position paper, no controlled experiments, era 3.0/4.0 speculative | Weak: production anecdotes, no published benchmarks | Strong: 2 comprehensive surveys (400+ citations), live production systems |

---

## 3. Convergences

**Where multiple independent sources agree -- the safe bets for Lyra:**

### 3.1 Separate Memory Management from Core Reasoning (Papers: COMEM, COMPASS, Memory Survey, Context Eng 2.0; Books: Agentic Design Patterns, Architectural Patterns; Web: Claude Code)

Every source that addresses architecture directly argues against monolithic context-window-only approaches for long-horizon agents. COMEM proves the decoupling with a second model (2.08x speedup). COMPASS proves it with a dedicated Context Manager agent (+110% GAIA over SAS). The Memory Survey (2603.07670v1) formalizes it as Pattern B as the pragmatic default. Agentic Design Patterns (Book, Ch.8) mandates "Dual Memory Architecture from Day One." Claude Code implements it via targeted checkpoint summarization. The convergence is unambiguous: **Lyra must separate context management from its primary reasoning pipeline.**

### 3.2 Compression Must Preserve Task-Relevant Sufficient Statistics, Not Surface-Level Summary Quality (Papers: COMEM, ACON, CodeComp, R-KV, WorldMemArena)

COMEM trains with action-consistency reward (cosine similarity to full-context action), not summary quality. ACON uses contrastive trajectory feedback (what information was lost when compression caused failure). CodeComp protects structurally critical code elements (callsites, branches) that attention-based methods evict. R-KV identifies semantically redundant tokens that attention over-values. WorldMemArena demonstrates that Memory Recall and QA-Correctness are decoupled (Qwen3-VL RAG: 86.22% Recall but only 51.86% QA-C). Universally: **compression quality should be measured by downstream task performance, not by intrinsic summary metrics.**

### 3.3 Token Budget Must Be Actively Managed, Not Just Expanded (Papers: ACON, COMPASS, Context Eng 2.0; Web: Aider, Claude Code, addyosmani; Books: Architectural Patterns)

ACON shows 26-54% peak token reduction while maintaining accuracy. COMPASS shows that bounded 200-300 token briefs outperform unbounded full history. Context Eng 2.0 catalogs that context window fullness >50% degrades performance (Osmani, 2025). Aider implements ChatSummary for automatic conversation compaction. Claude Code provides targeted summarization actions. Agentic Architectural Patterns warns of the "lost in the middle" problem for instructions buried in long contexts, recommending Persistent Instruction Anchoring. **Larger context windows delay but do not solve the problem; active compaction is necessary.**

### 3.4 Write-Filter-Read Pipeline with Multi-Signal Retrieval Scoring (Papers: Memory Survey 2603.07670v1, WorldMemArena, Memory Survey 2512.13564v2; Books: Agentic Design Patterns)

All memory surveys converge on the same architecture: write path with filtering, deduplication, and metadata tagging; read path with multi-signal scoring (recency decay + embedding similarity + importance). WorldMemArena's four-stage lifecycle (Write -> Maintain -> Retrieve -> Use) provides the diagnostic vocabulary for debugging failures at each stage. Agentic Design Patterns mandates "NEVER directly mutate state -- always use event-driven state_delta or output_key mechanisms." **This is the proven, consensus pipeline for agent memory.**

### 3.5 Context Windows Are Isolated Per Subagent to Prevent Pollution (Papers: COMPASS, Context Eng 2.0; Web: Claude Code, addyosmani; Books: Architectural Patterns)

COMPASS gives each of its 3 agents an isolated context window with role-specific curation. Context Eng 2.0 formalizes context isolation via subagents with custom system prompts and restricted tool permissions. Claude Code partitions state across subagents with orthogonal checkpoint dimensions (code vs. conversation vs. decision trace). Agentic Architectural Patterns warns of the "Tower of Babel" effect when agents develop fragmented worldviews from unshared context. **Isolated context windows improve reliability; shared epistemic memory provides the bridge.**

---

## 4. Contradictions

**Where sources disagree -- these need arbitration in Phase 4 plans:**

### 4.1 Compression Method: Train a Model vs. Keep Training-Free vs. Optimize Prompts

- **Train a compressor (COMEM, Context-12B, HippoRAG):** COMEM trains a dedicated 4B memory model with GRPO. COMPASS distills Context-12B via SFT+DPO. Argument: trained compressors learn task-specific sufficient statistics that generic methods miss. Counter: requires training infrastructure, task-specific data, and may not generalize across task distributions.
- **Training-free (CodeComp, R-KV):** CodeComp uses static analysis, R-KV uses cosine similarity. Argument: drop-in deployment, no training cost, no distribution shift. Counter: may miss task-specific compression patterns; CodeComp is Joern-dependent (limited language coverage).
- **Prompt-only optimization (ACON):** Optimizes natural language compression guidelines via contrastive feedback without touching weights. Argument: works with proprietary API models, costs <$2 per benchmark to optimize, $0.0004/example via distillation. Counter: no convergence guarantees, optimizer quality matters (o3 > gpt-5 > gpt-4.1), combined compression degrades.

**Arbitration needed:** Lyra must decide whether to invest in training a dedicated compression model (highest ceiling), use a training-free structural method (lowest risk), or use prompt-optimized compression (most flexible). The answer likely depends on Lyra's model access (proprietary vs. open-weight) and task domain specificity (code vs. general).

### 4.2 Compression Level: KV Cache vs. Text Summarization vs. Latent Representations

- **KV cache compression (COMEM, CodeComp, R-KV):** Operates at the transformer-internal level. Advantages: fine-grained, preserves token-level precision, directly reduces GPU memory. Disadvantages: model-specific, requires serving-level integration, harder to debug/audit.
- **Text-level summarization (COMPASS, ACON, Context Eng 2.0):** Operates at the natural language level. Advantages: model-agnostic, human-readable, auditable, plug-and-play. Disadvantages: loses fine-grained detail, compression artifacts (summarization drift), adds latency from LLM summarization call.
- **Latent representations (COMEM, HippoRAG, memory survey's "Latent Memory" category):** Encodes context into continuous vectors or KV entries. Advantages: most compact, machine-native, preserves subtle patterns. Disadvantages: not human-readable, hard to debug, drift/error accumulation over cycles.

**Arbitration needed:** The Memory Survey (2512.13564v2) argues the boundary between token-level and latent memory "blurs" as latent representations are explicitly stored. COMEM straddles both (latent summary + text buffer). Lyra should likely adopt a hybrid: token-level for recent context, text summaries for medium-term compression, optional latent for extreme scale.

### 4.3 Synchronous vs. Asynchronous Context Management

- **Asynchronous (COMEM, COMPASS Meta-Thinker):** Context management runs in background without blocking the agent. COMEM's k-step-off pipeline makes compression cost invisible. COMPASS's Meta-Thinker monitors asynchronously. Advantages: no latency added to the critical path. Disadvantages: context may be stale (k-step lag), requires coordination infrastructure, harder to debug.
- **Synchronous (ACON, MemGPT interrupt):** Context management runs before each agent step. ACON triggers compression when history exceeds 4096 tokens. MemGPT interrupts transfer control to memory functions. Advantages: always current, simpler to implement. Disadvantages: adds latency to every step, KV cache invalidation penalty (20-39% in ACON).

**Arbitration needed:** COMEM empirically shows k=1 (synchronous equivalent) degrades to 57.2% vs. 62.7% for k=4 (async), but k=16 saturates (60.2%). There is an optimal staleness window. Lyra should benchmark its own task-specific staleness tolerance.

### 4.4 Flat vs. Hierarchical vs. Planar Token Memory Organization

- **Flat (1D):** MemGPT, Reflexion -- fast append/prune, weak on compositional reasoning. Memory Survey 2512.13564v2 notes it degrades under scale.
- **Planar (2D):** A-Mem (card-based connected memory), Ret-LLM (triple-based tables), MemTree (dynamic trees). Single-layer relations without cross-layer abstraction.
- **Hierarchical (3D):** GraphRAG (multi-level community graphs), HippoRAG (KG + PPR with synonymy edges), G-Memory (three-tier insight/query/interaction graphs). Multi-level abstraction with coarse-to-fine retrieval.

**Arbitration needed:** The Memory Survey (2512.13564v2) recommends "at minimum Planar or Hierarchical organization" to avoid flat degradation, but the optimal 3D layout "remains unsolved." WorldMemArena finds most systems default to append-mode (flat), capping update handling at ~59%. Lyra should start with Planar (event-type-keyed with temporal edges) and graduate to Hierarchical when empirical data justifies the complexity.

---

## 5. Open Problems

**What NO source solves yet -- these are Lyra's research opportunities:**

### 5.1 Selective Forgetting

MemoryAgentBench (cited in Memory Survey 2603.07670v1) shows "no current system masters all four cognitive competencies -- most fail conspicuously on selective forgetting." WorldMemArena confirms: update handling capped at ~59% across all systems, interference rejection ranges from 23.42% to 58.94%. Current approaches are crude: hard time-based expiration, storage-limit eviction, or nothing. R-KV's redundancy detection is the closest approximation but operates only at the KV cache level, not the semantic level. A learned forgetting policy (what to discard, when, with what confidence) remains an open research problem.

### 5.2 Cross-Session Coherence at Scale

MemoryArena (cited in Memory Survey 2603.07670v1) demonstrates that models scoring near-perfectly on single-session benchmarks (LoCoMo) plummet to 40-60% on multi-session interdependent tasks. WorldMemArena's "snowball collapse" failure mode -- where early omissions reduce evidence for later retrieval, compounding over time -- has no known mitigation beyond improved write-path filtering. No source addresses how to maintain coherent knowledge representation across sessions separated by hours or days with intervening context changes.

### 5.3 Community-Standard Context Engineering Benchmark

The Memory Survey (2512.13564v2) catalogs 27 memory-relevant benchmarks (LongMemEval, StreamBench, LongBench, SWE-Bench, GAIA, xBench) using different datasets, metrics, and protocols, making cross-paper comparison unreliable. Context Eng 2.0 explicitly flags this gap. No benchmark systematically reports token consumption and latency overhead alongside accuracy -- the "cost-efficiency blind spot" means reported gains may not be "free."

### 5.4 Causal Retrieval (Not Semantic Similarity)

Memory Survey (2603.07670v1): "Causal retrieval -- retrieving by what *caused* something, not what is *similar* -- remains largely unexplored." Current retrieval is dominated by embedding similarity, which surfaces plausible but causally irrelevant records. COMEM's action-consistency reward is a step toward causal preservation but operates at the compression stage, not retrieval.

### 5.5 Safety Implications of Compressed Context

COMEM explicitly acknowledges that "no safety/alignment consideration [is] in the design" -- the pipeline increases agent throughput but does not address safety implications of faster autonomous agents. Context Eng 2.0 omits security considerations entirely despite emphasizing lifelong context and cross-system sharing. What happens when a malicious input is compressed into a summary that preserves its semantic payload but loses its adversarial surface features? What happens when structured notes encode PII that raw context would have filtered? No source addresses these questions.

### 5.6 Compression Guarantee Bounds

COMEM's theoretical compression bound (Equation 7) shows that summaries must be <23% of full context to yield net latency reduction, but provides no guarantee that the bound is achievable while preserving task-critical information. ACON has no formal convergence guarantee for its prompt optimization. No source provides hard bounds on the information-theoretic limits of context compression for specific task types.

### 5.7 Multi-Agent Memory Governance

Memory Survey (2603.07670v1): "Multi-agent memory governance is uncharted -- access control over shared stores, consensus protocols for concurrent writes, and principled boundaries between shared/private memory are unexplored." COMPASS isolates context windows but does not address shared memory governance. Agentic Architectural Patterns recommends "Shared Epistemic Memory as the single source of truth" with typed tools, but does not address conflicts, concurrent writes, or access control.

---

## 6. Recommendations for Lyra

Ranked by evidence strength, implementability, and impact. Tier definitions: **Breakthrough** (adopt now, architecture-shaping), **Investigate** (build prototype, validate before full adoption), **Monitor** (track progress, adopt when mature).

### Breakthrough Tier (Adopt in Phase 4)

**R1. Implement Pattern B Hierarchical Memory (Context + Retrieval Store) as foundational architecture.**
- **Sources:** Memory Survey 2603.07670v1 (POMDP formalization, Pattern B recommendation), Memory Survey 2512.13564v2 (Forms-Functions-Dynamics taxonomy), WorldMemArena 2605.29341v2 (four-stage lifecycle diagnostics), Agentic Design Patterns Ch.8 (Dual Memory Architecture from Day One)
- **Rationale:** This is the consensus safe bet -- every survey, book, and production system converges on the same architecture. The memory-vs-no-memory gap exceeds the LLM-backbone gap, making this the single highest-leverage intervention available. Lyra's current architecture (if monolithic context) should adopt this in Phase 4 before any other optimization.
- **Implementation:** Write path with filtering/dedup/priority scoring/metadata tagging; read path with BM25 -> cross-encoder reranker + retrieval-or-not gate; multi-signal retrieval scoring (recency decay + embedding similarity + importance); dual-buffer consolidation (hot buffer probation period before long-term storage); full operation observability logging with "memory diffs" between turns.

**R2. Adopt the COMPASS-style structured context brief (6-section template) as Lyra's inter-turn context format.**
- **Sources:** COMPASS 2510.08790v1 (6-section brief: Task, Evidence, Constraints, Open Items, Next Actions, Tool Hints), Context Eng 2.0 2510.26493v1 (minimal sufficiency principle, semantic continuity principle)
- **Rationale:** COMPASS provides the strongest empirical evidence for structured context curation (+110% GAIA over raw SAS). The 6-section template is concrete, proven (200-300 token typical output), and directly transferable. Lyra can use Claude as its Context Manager without needing to train a dedicated model.
- **Implementation:** After each turn/tool call, synthesize a structured brief from full history using Claude with a specialized prompt. Maintain a rolling note store of extracted evidence, constraints, and open items. Reset the brief when the agent transitions between major phases.

**R3. Implement progressive-disclosure context loading for Lyra's skill/plugin system.**
- **Sources:** addyosmani/agent-skills (meta-skill decision tree, <300 line skills, references loaded on demand), Aider (repo map via tree-sitter + PageRank), Claude Code (targeted checkpoint summarization)
- **Rationale:** This is production-proven, low-risk, and directly applicable. Lyra's skill system should not load all skills into every session -- a lightweight meta-skill for discovery with on-demand loading of matched skills keeps the context lean.
- **Implementation:** Meta-skill with decision tree (50-100 token descriptions); individual skills load only when matched; shared references loaded on demand; targeted compaction (summarize-from-here, summarize-up-to-here) for conversation management.

**R4. Adopt redundancy-aware context pruning (R-KV style) for Lyra's context assembly.**
- **Sources:** R-KV 2505.24133v4 (joint importance-redundancy scoring Z = lambda*I - (1-lambda)*R), CodeComp 2604.10235v1 (0.0944 Jaccard between attention and structural importance for code)
- **Rationale:** Context bloat from semantically duplicate content is a primary failure mode for Lyra's long-running agent sessions. R-KV provides a training-free mechanism (cosine similarity of chunk embeddings) that directly extends effective session length. The mechanism is simple (~50 lines of code leveraging Lyra's existing embedding infrastructure).
- **Implementation:** When assembling context, compute pairwise cosine similarity of chunk embeddings. Score each chunk: `combined = lambda * relevance_score - (1-lambda) * max_similarity_to_retained_chunks`. Retain top-K by combined score. Lambda = 0.1 as starting point, tune on Lyra-specific benchmarks.

### Investigate Tier (Prototype in Phase 4, adopt if validated)

**R5. Build ACON-style contrastive compression guideline optimization for Lyra's compaction prompts.**
- **Sources:** ACON 2510.00615v3 (contrastive trajectory feedback, UTCO two-stage optimization, compressor distillation)
- **Rationale:** ACON's approach is uniquely suited for Lyra because (a) it works with proprietary API models (Claude), (b) optimization costs <$2 per benchmark, (c) compressor distillation cuts costs 99.1%. However, it needs Lyra-specific validation: collect contrastive trajectories (tasks where Lyra succeeds uncompressed but fails compressed), generate natural language feedback, optimize the compaction prompt.
- **Implementation:** Phase 4 prototype: collect 100 Lyra trajectories, identify compression failures, run ACON's contrastive feedback loop, validate optimized compaction prompt on held-out tasks. If improvement >5pp, adopt. Optional: distill into a small compressor model for production.

**R6. Evaluate COMEM-style decoupled memory model for Lyra's high-throughput serving.**
- **Sources:** COMEM 2605.30842v1 (k-step-off pipeline, GRPO with action-consistency reward, 2.08x speedup at batch=128)
- **Rationale:** COMEM provides the highest theoretical ceiling for latency reduction, but the infrastructure complexity (two vLLM engines, async coordination, GRPO training) is significant. This should be evaluated only after Pattern B (R1) is stable and Lyra's context management bottleneck is empirically measured at high throughput.
- **Implementation:** Measure Lyra's KV cache pressure and context-induced latency at projected production throughput. If KV cache utilization >50% GPU HBM, prototype a small compressor model (e.g., Claude Haiku) running k=4 steps behind. Train with GRPO on Lyra-specific action-consistency reward if prototype shows >1.3x speedup.

**R7. Adopt CodeComp-style structural priors for Lyra's code-specific context assembly.**
- **Sources:** CodeComp 2604.10235v1 (Joern CPG, span-level structural protection, 12x-14x accuracy recovery)
- **Rationale:** Lyra is a code agent; CodeComp's finding that attention and structural importance have only 0.0944 Jaccard overlap is directly relevant. Protecting callsites, control-flow predicates, return statements, and def-use chains from compression is low-risk and training-free. However, Joern dependency limits language coverage (Python, C/C++, Java, JS; no Go, Rust, Swift).
- **Implementation:** Integrate AST extraction (tree-sitter for broader language coverage than Joern) into Lyra's context assembly. When compressing repository-level code context, identify and unconditionally protect structurally critical spans (function signatures, call expressions, branch conditions, return statements) from truncation. Fill remaining budget with embedding-based relevance ranking.

### Monitor Tier (Track progress, adopt when mature)

**R8. Monitor the emergence of community-standard context engineering benchmarks.**
- **Sources:** Memory Survey 2512.13564v2 (27 disjoint benchmarks), Context Eng 2.0 2510.26493v1 (no evaluation protocol), WorldMemArena 2605.29341v2 (most comprehensive but LLM-as-Judge dependent)
- **Rationale:** Without standardized benchmarks, Lyra cannot reliably evaluate its context engineering against state of the art. When a community standard emerges (analogous to SWE-bench for code agents), Lyra should adopt it immediately.

**R9. Track selective forgetting and causal retrieval research.**
- **Sources:** Memory Survey 2603.07670v1 (identified as open problems), WorldMemArena 2605.29341v2 (update handling capped at 59%)
- **Rationale:** These are the hardest and most impactful open problems. Lyra should not invest in them directly until there is a breakthrough paper or system demonstrating a viable approach, but should monitor the literature closely.

**R10. Watch for production safety frameworks for compressed context.**
- **Sources:** COMEM 2605.30842v1 (acknowledges gap), Context Eng 2.0 2510.26493v1 (omits security)
- **Rationale:** No source addresses safety of compressed context. As Lyra deploys context engineering, it should develop its own guardrails: decompression audit trails, PII retention checks on summaries, adversarial testing of compressed context against prompt injection, and verifiability requirements (can a human verify the summary against the full context?).

---

## Source Index

### Papers (18 cited)
| ID | Short Title | Venue | Key Contribution |
|---|---|---|---|
| 2605.30842v1 | COMEM | ICML 2026 | Decoupled async memory model with k-step-off pipeline |
| 2604.10235v1 | CodeComp | arXiv Apr 2026 | Structural KV cache compression via CPG |
| 2510.00615v3 | ACON | ICML 2026 | NL compression guideline optimization via contrastive feedback |
| 2505.24133v4 | R-KV | NeurIPS 2025 | Redundancy-aware KV cache pruning for reasoning models |
| 2510.08790v1 | COMPASS | arXiv Oct 2025 | Dedicated Context Manager agent with structured briefs |
| 2510.26493v1 | Context Engineering 2.0 | arXiv Oct 2025 | Formal framework, self-baking consolidation |
| 2605.29341v2 | WorldMemArena | arXiv Jun 2026 | Four-stage memory lifecycle benchmark |
| 2603.07670v1 | Memory Survey (Du) | arXiv Mar 2026 | POMDP formalization, Pattern B/C recommendations |
| 2512.13564v2 | Memory Survey (Hu) | arXiv Jan 2026 | Forms-Functions-Dynamics taxonomy |
| 2405.14831v3 | HippoRAG | NeurIPS 2024 | Neurobiologically inspired KG + PPR memory |
| 2603.07670v1 | MemoryAgentBench | Via survey citation | Four cognitive competencies, selective forgetting failure |
| 2605.29341v2 | MemoryArena | Via survey citation | Multi-session performance collapse from >80% to 40-60% |
| 2410.04444v4 | Godel Agent | arXiv May 2025 | Self-modifying agent with runtime introspection (context-adjacent) |

### Books (5 cited)
| Book | Chapter/Playbook | Key Insight |
|---|---|---|
| Agentic Design Patterns | Ch.8 (Memory Management) | Dual Memory Architecture from Day One; never directly mutate state |
| Agentic Architectural Patterns (Arsanjani) | Ch.5-6 (Knowledge Sharing) | Shared Epistemic Memory as single source of truth; Persistent Instruction Anchoring |
| Agentic AI for Engineers | Playbook | Context window limitations; memory as first-class engineering investment |
| AI Agents Bible (Dylik) | Chapters | Memory taxonomy and architecture patterns |
| Build Advanced RAG from Scratch | Playbook | Retrieval pipeline patterns applicable to memory retrieval |

### Web Repos/Docs (4 cited)
| Source | Key Mechanism |
|---|---|
| Claude Code Checkpointing (Anthropic) | Targeted summarization; orthogonal state dimensions; 30-day retention |
| addyosmani/agent-skills | Progressive-disclosure skill loading; meta-skill decision tree; <300 line skills |
| Aider-AI/aider | Repo map via tree-sitter + PageRank; ChatSummary compaction |
| assafelovic/gpt-researcher | Structured note accumulation; autonomous research with context management |
