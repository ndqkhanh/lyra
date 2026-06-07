# Memory Architecture & Long-Term State -- Thematic Synthesis

**Date:** 2026-06-07
**Sources consulted:** 22 (12 paper rigor notes, 2 book notes, 6 web/repo notes, 2 survey taxonomies)
**Scope:** Agent memory systems for long-running, multi-turn, multi-session AI agents

---

## 1. Frontier Techniques (ranked by evidence strength)

### Technique 1: LLM-Driven Memory State Machine (ADD/UPDATE/DELETE/NOOP)

- **Sources:** Mem0 (paper: 2504.19413v1, arXiv Apr 2025); Mem0 V3 (repo: mem0ai/mem0, Apr 2026); claude-mem (repo: thedotmack/claude-mem v13.4.0); Managing Memory for AI Agents (book, Ch.2)
- **Mechanism:** For each new fact extracted from conversation, retrieve top-s semantically similar existing memories via vector search, then present fact + retrieved memories to an LLM via function-calling interface. The LLM selects: ADD (novel fact), UPDATE (enriches existing, gated by information-content comparison), DELETE (contradicts existing, marked invalid not physically removed), or NOOP (redundant). The Mem0 V3 production system simplifies this to pure ADD-only single-pass extraction for reliability.
- **Evidence:**
  - Mem0 base: 66.88 J-score overall on LoCoMo, 0.148s p50 search latency, 1,764 memory tokens per conversation (paper, Table 1-2)
  - Mem0 V3 (Apr 2026): LoCoMo 91.6 (+20.2 vs V2), LongMemEval 94.8 (+27.0), BEAM 64.1 at 1M tokens, p50 latency 0.88s (repo README)
  - claude-mem: ~98% compression ratio (2.6K read tokens from 133.8K discovery tokens), fully automated via lifecycle hooks (repo code)
  - Full-context beats all memory methods on accuracy (J=72.90 vs Mem0 66.88), showing the fundamental fidelity-compression trade-off (paper, Table 1)
- **Maturity:** Production deployed -- Mem0 serves live SaaS; claude-mem has 13.4.0 release with production hardening

### Technique 2: Knowledge Graph + Hierarchical Community Summarization (GraphRAG)

- **Sources:** GraphRAG (paper: 2404.16130v2, Microsoft Research, arXiv Feb 2025); Managing Memory for AI Agents (book, Ch.2 NER section, Practice 6/12)
- **Mechanism:** Offline indexing pipeline: (1) LLM extracts entities + relationships from text chunks with gleaning (self-reflection loop), (2) build knowledge graph with exact-string entity resolution, (3) Leiden hierarchical community detection partitions graph into multi-level communities, (4) LLM generates structured reports per community (title, summary, findings). Online query: shuffle community summaries into chunks, map (parallel LLM answer per chunk), rank by helpfulness score, reduce (synthesize global answer). Context window capped at 8K tokens for optimal quality.
- **Evidence:**
  - Comprehensiveness: 72-83% win rate over vector RAG on Podcast and News datasets (p < 0.001) (paper, Section 2)
  - Diversity: 75-82% win rate over vector RAG (p < 0.001) (paper, Section 2)
  - Token efficiency: Root-level (C0) uses 2-3% tokens of raw text while retaining 72% comprehensiveness (paper, Table)
  - Factual claims: 25-35% more claims than vector RAG (paper, Section 2)
  - Loss on directness/concision: Vector RAG wins directness at 35-45% win rate (paper, Table)
  - Indexing cost: 281 min for ~1M tokens with GPT-4-turbo (paper, Section 1)
- **Maturity:** Production deployed -- open-source (MIT), LangChain/LlamaIndex integrations, Microsoft Research backing

### Technique 3: Zettelkasten-Inspired Agentic Memory with Co-Evolution (A-MEM)

- **Sources:** A-MEM (paper: 2502.12110v1, Rutgers/Ant Group, Feb 2025); Managing Memory for AI Agents (book, Practice 12 -- Zettelkasten method)
- **Mechanism:** Four-stage pipeline: (1) Note Construction -- enrich raw interaction with LLM-generated keywords, tags, context description, dense embedding; (2) Link Generation -- cosine similarity top-k + LLM-driven connection analysis to detect causal/subtle relationships; (3) Memory Evolution -- when new memory added, retroactively update attributes (keywords, context) of semantically related existing memories; (4) Retrieval -- standard cosine similarity + top-k. Agency is at storage/evolution time, not retrieval time.
- **Evidence:**
  - Multi-Hop F1: +79.6% to +445% over baselines (MemGPT, MemoryBank) depending on model (paper, Table)
  - Token efficiency: 7-14x fewer tokens than naive full-history (1,200-2,500 vs ~16,900 per answer) (paper, Section 2)
  - Ablation: Full A-MEM = 45.85 F1 (Multi-Hop), w/o Evolution = 31.24 (14.6 point drop), w/o both = 24.55 (paper, Table)
  - t-SNE shows coherent memory clusters without explicit cluster supervision (paper, Section 2)
  - Single evaluation dataset only (LoCoMo), no multi-agent, no code/tool-use evaluation
- **Maturity:** Lab validated -- arXiv preprint, GitHub code, no production deployment known

### Technique 4: Hippocampal Memory Indexing with Personalized PageRank (HippoRAG)

- **Sources:** HippoRAG (paper: 2405.14831v3, Ohio State, NeurIPS 2024)
- **Mechanism:** Three synthetic components mimicking brain memory: LLM acts as neocortex (processes input), Retrieval Encoders act as parahippocampal regions (encode entities), KG + Personalized PageRank acts as hippocampus (stores associations, performs pattern completion). Offline: OpenIE extracts RDF triples from passages, synonymy edges added via embedding similarity > threshold, node specificity computed as inverse passage frequency (local IDF analog). Online: query entities linked to KG nodes, PPR with damping factor 0.5 diffuses probability from query nodes through association edges, passages scored by aggregated node probabilities.
- **Evidence:**
  - 2WikiMultiHopQA R@5: 89.1% (HippoRAG single-step) vs 68.2% (ColBERTv2) vs 74.4% (IRCoT multi-step) -- single-step beats iterative (paper, Table)
  - Cost: $0.1 per 1K queries vs $0 (ColBERTv2) vs $1-3 (IRCoT) -- 10-30x cheaper and 6-13x faster online (paper, Section 2)
  - QA F1 on 2Wiki: 59.5 vs 43.3 (ColBERTv2) -- +16.2 points (paper, Table)
  - Offline indexing: $15 / 10K passages with GPT-3.5, 60 min (paper, Section 2)
  - NER bottleneck causes 48% of errors; OpenIE degrades on long passages (F1 71.8 -> 53.9) (paper, Limitations)
- **Maturity:** Lab validated -- NeurIPS 2024, open-source code, no production deployment known

### Technique 5: LLM-to-LLM Memory Compression with Observer Agent (Automatic Capture)

- **Sources:** claude-mem (repo: thedotmack/claude-mem v13.4.0); Managing Memory for AI Agents (book, Ch.1 -- intelligent compression)
- **Mechanism:** Lifecycle hooks (SessionStart, PostToolUse, Stop) capture raw tool-usage transcripts. A secondary "observer" Claude process (Agent SDK) compresses transcripts into structured XML observations (type, title, facts, concepts) plus session-end summaries (investigated, learned, completed, next_steps). Hybrid search: Chroma vector embeddings + SQLite FTS5. Progressive disclosure at session start: header -> timeline -> full observations -> summary -> prior messages, with displayed token economics.
- **Evidence:**
  - Typical compression: ~98% (131K discovery tokens compressed to 2.6K read tokens) (repo code comments)
  - 3-layer MCP search pattern yields ~10x token savings vs naive full-fetch (repo README)
  - Zero-effort: fully automatic via lifecycle hooks, no manual save/load (repo design)
  - 10+ MCP skills built on the memory substrate (babysit, do, knowledge-agent, smart-explore, etc.) (repo code)
  - No formal benchmarks published; only in-code compression estimates
- **Maturity:** Production deployed -- npm package, 13.4.0 release, "Mentioned in Awesome Claude Code"

### Technique 6: Layered Semantic Pyramid Memory (L0-L3 with Drill-Down)

- **Sources:** TencentDB-Agent-Memory (repo: Tencent/TencentDB-Agent-Memory)
- **Mechanism:** Four-layer pyramid: L0 (raw conversation JSONL), L1 (structured atomic facts with vector embeddings in SQLite+sqlite-vec, deduplicated), L2 (scene blocks grouping related L1 atoms into named Markdown scenes via LLM), L3 (persona synthesis from all scenes into persona.md). Key invariant: every higher layer back-references source material via deterministic file paths. Separate short-term offload module uses Mermaid state graphs with node_id annotations to compress tool logs, with three compression tiers (mild/aggressive/emergency).
- **Evidence:**
  - WideSearch: +51.52% pass rate, -61.38% tokens (repo README benchmarks)
  - SWE-bench (50-turn continuous sessions): +9.93% pass rate, -33.09% tokens
  - AA-LCR: +7.95% pass rate, -30.98% tokens
  - PersonaMem accuracy: 48% -> 76% (+59%)
  - White-box debuggability: every layer is plain text files; recall failures traceable through the pyramid (repo architecture)
  - LLM dependency for L1/L2/L3 extraction; documented bugs from LLM-generated filenames with spaces
- **Maturity:** Production deployed -- npm package @tencentdb-agent-memory, integrated with OpenClaw

### Technique 7: Multi-Agent Memory Critique Loop (Reviewer/Challenger/Refiner)

- **Sources:** Amber (paper: 2504.05312v4, USTC/CAS, 2025)
- **Mechanism:** Three-agent collaboration before memory acceptance: (1) Reviewer examines proposed memory update against current memory and retrieved passages, identifies strengths/weaknesses; (2) Challenger builds on Reviewer's assessment, identifies flaws, overlooked constraints, conflicts; (3) Refiner synthesizes feedback into concrete memory modifications. Paired with two-level filtering: chunk-level (NLI-based relevance classification) and sentence-level (fine-tuned extraction model). Iterative loop with AIC scheduler determining when memory is sufficient.
- **Evidence:**
  - +10-30% accuracy over Vanilla RAG on multi-hop QA across 6 datasets (paper, Table 1)
  - Best performer: Qwen2-7b + Amber = 56.0% 2WikiMQA, 52.6% HotpotQA, 49.7% ASQA (paper, Section 2)
  - Classifier accuracy >90% with >40% negative passage elimination (paper, Figure 2)
  - Ablation: removing AMU drops accuracy by 1.1 points on 2WikiMQA; filters matter more individually (paper, Table 2)
  - Multiple LLM calls per query (3-agent AMU + AIC per iteration, max 3 iterations) -- high latency
- **Maturity:** Lab validated -- arXiv preprint, anonymous code repository, no production deployment

### Technique 8: Autonomous Experience Accumulation with Competence-Gated Reuse (SE-GPT)

- **Sources:** SE-GPT (paper: 2407.08937v1, Harbin IT/iFLYTEK, Jul 2024)
- **Mechanism:** Closed loop: (1) categorize problem into task type, (2) transfer experience from semantically similar known tasks via Faiss retrieval + LLM rephrasing, (3) autonomous practice: generate synthetic examples, answer them, verify against Wikipedia, (4) induce general patterns from correct/incorrect examples, (5) skip learning when 3 consecutive zero-error practices on same task. Memory is task-specific: procedure (ordered steps) + suggestions (cautionary heuristics).
- **Evidence:**
  - +3.8% accuracy (GPT-3.5) / +5.3% (GPT-4) over zero-shot across 6 diverse datasets (paper, Table 1)
  - Experience quality: 99.8% human-evaluated accuracy, 14.0 avg insights per task (GPT-3.5) / 21.9 (GPT-4) (paper, Table 3)
  - Ablation: removing transfer drops avg accuracy 1.5 points; removing induction drops 1.1 points (paper, Table 2)
  - Extreme cost: ~71x token overhead vs zero-shot CoT (13,532 vs 191 tokens per example); 5-day runtime for 6K examples (paper, Table 7)
  - Cold-start problem (empty memory); unbounded memory growth (no pruning) (paper, Limitations)
- **Maturity:** Lab validated -- arXiv preprint, no code released, no production deployment

### Technique 9: Generative Latent Memory Tokens (In-Weights Working Memory)

- **Sources:** MemGen (repo: bingreeky/MemGen; paper: ICLR 2026, arXiv 2509.24704)
- **Mechanism:** Two learned LoRA modules: Memory Weaver (small LM with learnable query latent vectors, projects hidden states into reasoner's embedding stream at delimiter positions -- commas, periods, newlines) and Memory Trigger (binary classifier deciding when to augment). Two-stage training: weaver trained first (SFT or GRPO), trigger trained second (GRPO only). Latents are 4-16 tokens, do not contribute to LM loss. No external database needed -- memory lives entirely in model hidden states.
- **Evidence:**
  - Compact: 4-16 latent tokens per augmentation point (repo config)
  - Parameter-efficient: only LoRA adapters + query vectors trained (repo code)
  - Supports GSM8K, GPQA, KodCode, TriviaQA datasets; Qwen2.5-1.5B and SmolLM3-3B base models (repo code)
  - Not persistent: latent tokens generated fresh each forward pass, no cross-session storage (repo architecture)
  - FSDP not supported; batch size 1 for conversational SFT; O(N^2) complexity in augmentation points (repo FAQ)
- **Maturity:** Lab validated -- ICLR 2026 paper, open-source code, no production deployment

### Technique 10: On-Demand Retrieval Gating with Reflection Tokens (SELF-RAG)

- **Sources:** SELF-RAG (paper: 2310.11511v1, UW/Allen AI/IBM, Oct 2023)
- **Mechanism:** Train LM to emit special reflection tokens during generation: Retrieve (Yes/No/Continue -- gate retrieval), ISREL (Relevant/Irrelevant -- validate passages), ISSUP (Fully/Partially/No Support -- verify claims), ISUSE (1-5 Likert -- overall usefulness). Two-phase training: (1) distill GPT-4 reflection labels into critic model, (2) train generator with reflection tokens and masked passage text. Inference: per-segment beam search with weighted scoring of generation probability + critique signals. Test-time adjustable: increase ISSUP weight for higher citation precision, increase retrieve threshold for lower latency.
- **Evidence:**
  - SELF-RAG 7B beats ChatGPT on PubHealth (72.4 vs 70.1), ASQA fluency (74.3 vs 68.8 MAUVE), Bio FactScore (81.2 vs 71.8) (paper, Table 2)
  - Critic model: >90% agreement with GPT-4 on Retrieve/ISSUP, 80.2% on ISREL, 73.5% on ISUSE (paper, Section 2)
  - Human eval: 92.5% Supported & Plausible on PopQA, 90%+ ISREL/ISSUP accuracy (paper, Section 2)
  - Training cost: ~47K GPT-4 API calls for initial label distillation (paper, Section 1)
  - Wikipedia-only retrieval, no non-English evaluation, training not yet saturated at 150K examples
- **Maturity:** Lab validated -- arXiv preprint, open-source models released, no known production deployment

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy | Latency (p50) | Memory Cost | Complexity | Scalability | Evidence Strength |
|-----------|----------|---------------|-------------|------------|-------------|-------------------|
| **Mem0 V3 (ADD-only)** | 91.6 LoCoMo, 94.8 LongMemEval | 0.88s | 7K tokens/conversation | Medium (single-pass LLM + vector store) | Tested to 10M tokens (BEAM) | HIGH -- production SaaS + paper |
| **GraphRAG (global)** | 72-83% comprehensiveness win | ~minutes (map-reduce) | 2-73% of raw corpus | HIGH (entity extraction + graph + Leiden + summarization) | Tested to ~1.7M tokens | HIGH -- open-source (MIT) + paper |
| **A-MEM (Zettelkasten)** | 45.85 F1 Multi-Hop (GPT-4o-mini) | ~1.4s (per paper p95=4.37s) | 2,520 tokens/answer | MEDIUM-HIGH (3 LLM prompts per write) | Single eval dataset (LoCoMo) | MEDIUM -- preprint only |
| **HippoRAG (neuro)** | 89.1% R@5 2Wiki (single-step) | ~3 min per 1K queries | $15/10K passages offline | HIGH (OpenIE + KG + PPR + synonymy edges) | Tested to ~12K passages | HIGH -- NeurIPS 2024 |
| **TencentDB L0-L3** | +51.5% WideSearch, +9.9% SWE-bench | Unknown (background pipeline) | Token savings: 30-61% | HIGH (4-layer pyramid, LLM per layer, 32K LoC) | 50-turn SWE-bench continuous sessions | HIGH -- production npm package |
| **claude-mem (observer)** | No formal benchmarks | Observer subprocess latency | ~2.6K tokens injected per session | MEDIUM (hooks + observer Claude + SQLite + Chroma) | Per-project (not multi-tenant) | MEDIUM -- in-code estimates only |
| **Amber (3-agent critique)** | +10-30% over vanilla RAG | High (3 LLM calls/iter, max 3 iters) | Not reported | HIGH (fine-tune 2 classifiers + 3-agent debate) | 6 datasets at academic scale | MEDIUM -- preprint + anonymous code |
| **SE-GPT (experiential)** | +3.8-5.3% over zero-shot | N/A (~5 days runtime) | 13.5K tokens/example (71x baseline) | VERY HIGH (5 modules, web retrieval, autonomous practice) | 6K examples, 6 datasets | MEDIUM -- preprint, no code |

**Notes on comparisons:**
- Direct benchmark comparisons are rare across papers; metrics and datasets vary widely. Mem0 and A-MEM both evaluate on LoCoMo but use different baselines and scoring methods (J-score vs F1/BLEU).
- The Mem0 V3 paper reports A-MEM p95 latency of 4.374s vs Mem0's 1.440s on the same LoCoMo benchmark -- Mem0 is 3x faster at p95.
- No paper evaluates multi-agent shared memory scenarios. All evaluations are single-agent.

---

## 3. Convergences

Where multiple independent sources agree -- these are the safe bets for Lyra.

### Convergence 1: Importance scoring is the universal primitive for memory management.

Every serious source converges on this. The book (Managing Memory for AI Agents, Ch.1) proposes 4-dimensional scoring (recency, frequency, user engagement, keyword relevance). TencentDB implements a pipeline timer with warm-up scheduling. claude-mem uses progressive disclosure with configurable observation counts. A-MEM uses embedding similarity + LLM analysis for link decisions. No source disputes that raw FIFO or recency-only strategies are inferior.

**Action for Lyra:** The MemoryManager must include a multi-dimensional importance scorer. The book's 4-dimension model is the simplest starting point; TencentDB's warm-up approach (aggressive early extraction, throttling later) solves the cold-start problem.

### Convergence 2: Three-tier memory is the consensus architecture (short-term / long-term / archival).

The book (Ch.2), Letta/MemGPT, claude-mem, TencentDB, and the Agent-Memory-Paper-List taxonomy all converge on three memory tiers. Letta implements it explicitly as Core (in-context blocks), Archival (vector DB), Recall (conversation history with compaction). TencentDB's L0-L3 is a 4-tier variant of the same idea. The book's Practice 8 explicitly calls for "hierarchical storage tiers (short-term, long-term, archival) with clear promotion/demotion rules."

**Action for Lyra:** This is the already-validated foundation. The question is not *whether* to use three tiers, but *how* promotion/demotion/compaction should work across them.

### Convergence 3: LLM-driven memory extraction beats heuristic extraction.

A-MEM uses LLM for note construction, link generation, and evolution. Mem0 V3 uses LLM single-pass extraction with 600+ line prompt. TencentDB uses LLM for L1/L2/L3 extraction. claude-mem uses observer Claude for compression. GraphRAG uses LLM for entity/relationship extraction with gleaning. The book (Ch.1) recommends "cascading memory systems -- let the agent itself choose what to promote." No source argues for purely heuristic (regex, keyword) memory extraction at production scale.

**Action for Lyra:** Accept that LLM-based extraction is table stakes. The design question is: how many LLM calls per memory operation, and which model (cheap model for routine extraction, expensive model for consolidation)?

### Convergence 4: Vector-only retrieval is necessary but insufficient.

Every source converges on this. GraphRAG adds knowledge graphs for global sensemaking. HippoRAG adds PPR over KGs for multi-hop. Mem0 V3 adds BM25 + entity boost on top of vector search. The book (Practice 6) recommends NER for structured precision alongside semantic search. TencentDB builds a full semantic pyramid with drill-down. MemGen bypasses vector stores entirely with latent tokens. No source claims that pure cosine similarity over embeddings is sufficient for production agent memory.

**Action for Lyra:** Hybrid retrieval (vector + keyword + entity) is the minimum viable retrieval strategy. Knowledge graph augmentation is the next tier for multi-hop queries.

### Convergence 5: Memory must be compact and deduplicated, not a raw transcript archive.

Mem0 V3 uses MD5 hash dedup within and across batches. A-MEM uses memory evolution to merge/prune redundant memories. claude-mem achieves 98% compression. TencentDB uses sqlite-vec similarity + keyword conflict detection for dedup. The book (Ch.1) warns against "naive summarization" but endorses "intelligent compression." Mem0 V3's ADD-only design intentionally avoids deleting memories, relying on retrieval-time fusion rather than storage-time compression -- but this is a reliability trade-off, not a rejection of compactness.

**Action for Lyra:** Deduplication via hash + embedding similarity is table stakes. ADD-only with retrieval-time relevance ranking (Mem0 V3 pattern) is the simpler, more reliable path vs UPDATE/DELETE with LLM reasoning (Mem0 V2/A-MEM pattern).

---

## 4. Contradictions

Where sources disagree -- these need arbitration in Phase 4 plans.

### Contradiction 1: ADD-only vs ADD/UPDATE/DELETE memory operations.

**Mem0 V3 argues:** Single-pass ADD-only extraction is simpler and more reliable. UPDATE/DELETE in V2 caused race conditions, hallucinated modifications, and consistency problems. Let retrieval-time fusion handle relevance.

**A-MEM argues:** Memory evolution (retroactively updating/merging/pruning existing memories) is essential -- removing evolution drops Multi-Hop F1 from 45.85 to 31.24. Static memories miss emergent patterns.

**claude-mem argues:** ADD-only at observation level, but session-end summaries create a second tier of consolidated memory.

**Resolution needed:** Should Lyra's memory be immutable-append with retrieval-time ranking, or mutable with evolution-triggered updates? The evidence suggests a hybrid: immutable at the fact level (Mem0 pattern), with periodic batch consolidation that creates new summary-tier memories without modifying originals (claude-mem pattern, TencentDB L2/L3 pattern).

### Contradiction 2: Global summarization vs local retrieval for long-context queries.

**GraphRAG argues:** Build pre-computed community summaries for whole-corpus questions. Vector RAG cannot answer "what are the main themes across all conversations?" Map-reduce over pre-computed summaries is the only approach.

**HippoRAG argues:** Single-step multi-hop retrieval via PPR over knowledge graph is sufficient, without summarization. 10-30x cheaper and 6-13x faster than iterative approaches.

**Mem0 V3 argues:** Pure vector + BM25 + entity search with 10M token corpus works well enough (BEAM 48.6 at 10M). No summarization needed.

**Resolution needed:** All three can be right for different query types. GraphRAG excels at open-ended sensemaking ("what themes emerge?"). HippoRAG excels at structured multi-hop ("what did X do after Y?"). Mem0 excels at factoid retrieval ("what is X's preference?"). Lyra likely needs all three retrieval strategies, routed by query type.

### Contradiction 3: Observer-agent compression vs in-model memory.

**claude-mem/TencentDB argue:** Use a secondary LLM (observer) to compress primary agent transcripts. Compression is external to the reasoning model. This is battle-tested in production.

**MemGen argues:** Memory should live in the model's own hidden states as latent tokens. No external database needed. ICLR 2026 paper.

**Resolution needed:** These serve different purposes. Observer compression is for cross-session persistence (episodic memory). Latent tokens are for within-session working memory. They are complementary, not competing. Lyra can use both: claude-mem-style compression for session-to-session continuity, MemGen-style latent tokens (if viable) for within-turn context augmentation.

### Contradiction 4: Fixed-schema vs schemaless memory representation.

**Mem0^g / GraphRAG argue:** Graph databases with predefined entity types and relationship labels enable structured querying and temporal reasoning.

**A-MEM argues:** "We reject graph database approaches because predefined schemas and fixed relationship types cannot adapt to novel domains." Zettelkasten's flexible linking is preferred.

**HippoRAG argues:** Schemaless OpenIE extraction + PPR avoids the schema problem while retaining graph advantages.

**Resolution needed:** The schemaless OpenIE approach (HippoRAG) is the pragmatic middle ground -- it gives graph traversal benefits without schema maintenance. However, TencentDB's layered approach (schemaless at L0/L1, structured at L3) demonstrates that some structure emerges naturally from usage and should be captured when it does.

### Contradiction 5: When to compress/summarize -- continuous vs batched.

**Letta argues:** Continuous -- summarization triggers at 90% context window fill, oldest messages get replaced by summary. This is reactive.

**TencentDB argues:** Batched -- L1 extraction triggers every N conversations, L2/L3 on separate timers with warm-up. This is proactive.

**claude-mem argues:** Per-session -- observer generates summary only at session end (Stop hook).

**Resolution needed:** Both are needed. Reactive compression (Letta) handles unpredictable context pressure during a session. Proactive extraction (TencentDB) handles the known pattern of accumulating sessions. The book's Practice 2 ("cascading memory systems") suggests letting the agent decide when to promote -- but this adds LLM cost to the scheduling decision.

---

## 5. Open Problems

What problems does NO source solve yet? These are research opportunities.

### Problem 1: Cross-agent shared memory with consistency guarantees.

No paper or system addresses how multiple agents share a memory store with ACID-like consistency. A-MEM explicitly notes "no multi-agent evaluation." TencentDB and Letta are single-agent systems. The book (Practice 8) calls for "cross-agent knowledge synchronization" but provides no mechanism beyond "version-controlled memory." This is the biggest gap in the literature for multi-agent systems like Lyra.

### Problem 2: Memory fidelity under repeated consolidation cycles.

A-MEM's evolution mechanism rewrites memory attributes -- acknowledged risk of "memory drift" with no fidelity constraint. SE-GPT's memory grows unbounded (no pruning). No source measures how many consolidation cycles a memory can survive before it diverges meaningfully from source truth. The book warns that "summaries lose critical details by definition" but provides no quantitative framework.

### Problem 3: Optimal memory budget allocation.

All sources treat memory as unbounded-in-principle with practical limits (context window, storage cost). No source frames memory as an optimization problem: given a fixed token budget for injected context, what is the optimal allocation across episodic, semantic, and procedural memory? The book's Practice 15 decomposes evaluation but not memory allocation.

### Problem 4: Privacy-aware memory with information barriers.

claude-mem has `<private>` tags but manual. Mem0 V3 has no access control model. TencentDB's personas aggregate user data without per-user privacy boundaries. No source addresses how to maintain memory when some facts must be forgotten (GDPR right-to-erasure, organizational information barriers, user consent withdrawal).

### Problem 5: Memory evaluation beyond QA datasets.

Every paper evaluates on QA benchmarks (LoCoMo, 2Wiki, HotpotQA, ASQA, etc.). No source evaluates memory on code-generation tasks, multi-turn tool-use tasks, or creative tasks. The Agent-Memory-Paper-List taxonomy notes this gap implicitly -- all papers are classified under Factual/Token-level Memory, with Experiential/Procedural categories being thin.

### Problem 6: Real-time memory with sub-second latency guarantees.

Mem0 V3 achieves 0.88s p50 latency. A-MEM's p95 is 4.37s. Amber requires multiple LLM calls per iteration. No system guarantees sub-100ms memory retrieval for real-time agent loops. HippoRAG comes closest with offline indexing + fast online PPR, but the LLM-based OpenIE pipeline is bottlenecked at indexing time.

### Problem 7: Cold-start memory for new agents/users.

SE-GPT acknowledges cold start (empty memory = no transfer benefit). TencentDB addresses it with warm-up scheduling (aggressive early extraction). No source provides a general solution for bootstrapping an agent's memory from similar agents, pre-trained embeddings, or domain templates.

---

## 6. Recommendations for Lyra

Ranked by evidence strength, implementation feasibility, and architectural fit.

### Tier 1 -- Adopt Now (high evidence, moderate effort)

**R1: Three-tier memory architecture with importance scoring.**
- **What:** Core Memory (always in-context, block-editable via tools), Archival Memory (vector + keyword + entity hybrid retrieval), Recall Memory (conversation history with reactive compaction at context threshold + proactive batched extraction).
- **Rationale:** Universal consensus across all sources. Letta, TencentDB, claude-mem, and the book all converge on this pattern. Implementation path is well-understood.
- **Sources:** Letta three-tier design; TencentDB L0-L3; Managing Memory book Ch.2; Agent-Memory-Paper-List taxonomy
- **Lyra route:** Section 4.2 (Memory Architecture)

**R2: Hybrid retrieval (vector + BM25 + entity boost).**
- **What:** Fuse three scoring signals with adaptive normalization (Mem0 V3 scoring pipeline). Query-length-adaptive BM25 parameters. Entity extraction via lightweight NLP (spaCy) with entity-linked memory boosting.
- **Rationale:** Every source converges on hybrid > pure vector. Mem0 V3 provides a production-validated implementation pattern. Low complexity to implement.
- **Sources:** Mem0 V3 scoring pipeline; Managing Memory book Practice 6 (NER); TencentDB sqlite-vec + BM25
- **Lyra route:** Section 4.2 (Retrieval Subsystem)

**R3: LLM-driven memory extraction with single-pass ADD-only design.**
- **What:** For each new interaction, run a single LLM call to extract structured facts (JSON with text + linked memory IDs). MD5 hash dedup + embedding similarity dedup. No UPDATE/DELETE in the extraction path. Retrieval-time fusion handles relevance.
- **Rationale:** Mem0 V3's reliability arguments are compelling. The V2->V3 migration (abandoning smart UPDATE/DELETE for simple ADD-only) directly informs Lyra's design. Simpler and more reliable.
- **Sources:** Mem0 V3 algorithm (Apr 2026); Mem0 paper (2504.19413v1)
- **Lyra route:** Section 4.2 (Memory Write Path)

**R4: Checkpointing with TTL-based cleanup.**
- **What:** Periodically persist agent state (conversation threads, learned patterns, working memory) to persistent storage. Use TTL for automatic cleanup of stale data.
- **Rationale:** Book Practice 14; Letta's persistence-by-default design. Table-stakes capability for any multi-session agent.
- **Sources:** Managing Memory book Practice 14; Letta ORM design
- **Lyra route:** Section 4.1 (Session Persistence)

### Tier 2 -- Investigate (promising but needs adaptation)

**R5: Periodic batch memory consolidation (observer-pattern).**
- **What:** Run periodic (end-of-session or daily) batch jobs that: (a) summarize recent facts into scene-level narratives, (b) detect emergent patterns across memories, (c) generate persona-level summaries. Use a separate "observer" model (cheaper, not the primary reasoning model). Original facts preserved immutably; consolidated summaries are a new tier.
- **Rationale:** Combines the best of A-MEM's evolution (pattern detection) with claude-mem's observer pattern (separation of concerns). Addresses Contradiction 1 (ADD-only vs evolution) by creating new summary-tier memories rather than mutating originals.
- **Sources:** claude-mem observer design; TencentDB L2/L3 pipeline; A-MEM evolution mechanism; SE-GPT experience induction
- **Lyra route:** Section 4.3 (Memory Consolidation)

**R6: Knowledge graph augmentation for multi-hop queries.**
- **What:** Extract entities and relationships from agent memory via OpenIE (schemaless, per HippoRAG). Build a lightweight KG with synonymy edges. Use PPR for single-step multi-hop retrieval when query complexity demands it. Route simple factoid queries to vector search, structured multi-hop queries to KG.
- **Rationale:** Addresses Contradiction 2 (global vs local retrieval). HippoRAG's single-step multi-hop is 10-30x cheaper than iterative approaches. GraphRAG's community summarization can be layered on top for global sensemaking.
- **Sources:** HippoRAG (2405.14831v3); GraphRAG (2404.16130v2); Managing Memory book Practice 12 (Zettelkasten)
- **Lyra route:** Section 4.4 (Knowledge Graph)

**R7: Competence-gated memory reuse (skip when mastered).**
- **What:** Track task-type success/failure history. When last N similar tasks succeeded, skip memory overhead and answer directly. When encountering novel or previously-failed task types, invest in rich memory retrieval and consolidation.
- **Rationale:** SE-GPT's skip-learning mechanism reduces redundant computation. Directly addresses the cost concern of memory operations -- don't pay for memory when you don't need it.
- **Sources:** SE-GPT (2407.08937v1) skip-learning condition
- **Lyra route:** Section 4.2 (Memory Retrieval Gating)

### Tier 3 -- Watch (high potential, premature for deployment)

**R8: Latent memory tokens for within-session working memory.**
- **What:** Learn LoRA adapters that inject compact latent vectors (4-16 tokens) into the model's hidden-state stream at delimiter positions. Use trigger module to decide when to augment.
- **Rationale:** MemGen's approach is novel and eliminates external database latency for working memory. But the technique is ICLR 2026 (very recent), requires model training (not prompting-only), and FSDP is unsupported. Premature for Lyra v1.
- **Sources:** MemGen (ICLR 2026, repo: bingreeky/MemGen)
- **Lyra route:** Section 4.5 (Future Memory Research)

**R9: Multi-agent shared memory with Transactive Memory Systems.**
- **What:** Implement cross-agent memory synchronization where discoveries by one agent benefit the entire fleet. Use version-controlled memory with rollback. Build a Transactive Memory System where agents know "what other agents know."
- **Rationale:** The book (Practice 7-9) makes a compelling case, and Contradiction 4 (no source solves this) represents a genuine innovation opportunity. But the technical challenges (consistency, conflicts, access control) are significant. Address after single-agent memory is stable.
- **Sources:** Managing Memory book Practices 7/8/9; Problem 1 (no source solves this)
- **Lyra route:** Section 7.2 (Cross-Agent Synchronization)

---

## Source Index

### Papers (with arXiv IDs)
1. A-MEM: Agentic Memory for LLM Agents -- arXiv:2502.12110v1 (Feb 2025)
2. Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory -- arXiv:2504.19413v1 (Apr 2025)
3. GraphRAG: From Local to Global -- arXiv:2404.16130v2 (Feb 2025)
4. HippoRAG: Neurobiologically Inspired Long-Term Memory -- NeurIPS 2024, arXiv:2405.14831v3
5. Amber: Adaptive Memory-Based Optimization for Enhanced RAG -- arXiv:2504.05312v4 (2025)
6. SE-GPT: Self-Evolving GPT, A Lifelong Autonomous Experiential Learner -- arXiv:2407.08937v1 (Jul 2024)
7. SELF-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection -- arXiv:2310.11511v1 (Oct 2023)
8. MemGen: Weaving Generative Latent Memory for Self-Evolving Agents -- ICLR 2026, arXiv:2509.24704
9. MACNET: Scaling Large Language Model-Based Multi-Agent Collaboration -- ICLR 2025, arXiv:2406.07155v3
10. Multi-Agent Debate: Voting or Consensus? -- ACL 2025 Findings, arXiv:2502.19130v4
11. Tree of Thoughts: Deliberate Problem Solving with LLMs -- NeurIPS 2023, arXiv:2305.10601v2

### Books
12. Managing Memory for AI Agents (O'Reilly, Oct 2025) -- Chapters + Playbook
    - Author: Benjamin Labaschin, Jim Allen Wallace, Andrew Brookins, Manvinder Singh
    - Key chapters: 1 (Memory Systems), 2 (Long-Term Memory), 3 (Economics), 4 (Portability), 5 (Collective Intelligence)

### Web/Repos
13. claude-mem (thedotmack/claude-mem v13.4.0) -- Persistent memory compression for Claude Code
14. TencentDB-Agent-Memory (Tencent/TencentDB-Agent-Memory) -- 4-layer memory pyramid for OpenClaw
15. Letta/MemGPT (letta-ai/letta v0.16.8) -- Three-tier memory with block editing
16. Mem0 V3 (mem0ai/mem0, Apr 2026 update) -- Single-pass ADD-only extraction pipeline
17. Agent-Memory-Paper-List (Shichun-Liu/Agent-Memory-Paper-List) -- Three-lens taxonomy (Forms x Functions x Dynamics)

### Taxonomy
18. Agent-Memory-Paper-List survey: Memory in the Age of AI Agents -- arXiv:2512.13564 (Dec 2025)
    - Three lenses: Forms (Token/Parametric/Latent), Functions (Factual/Experiential/Working), Dynamics (Formation/Evolution/Retrieval)
