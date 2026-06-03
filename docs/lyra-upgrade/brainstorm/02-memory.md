# Brainstorm — Memory Architecture (§4.2)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Source Techniques Gathered

| Technique | Source | Core Idea | Key Numbers |
|-----------|--------|-----------|-------------|
| Zettelkasten Memory | A-MEM (FiM0M8gcct) | Dynamically linked/evolving memory notes with contextual descriptions | — |
| Cost-Sensitive Store Routing | Gaikwad (iGRGjdhl9r) | Route queries to cheapest sufficient memory store | Cuts tokens, improves accuracy |
| Memory Transplants | UCSD (AIJsjIqfsp) | Disentangle memory architecture vs content transfer | Weaker models gain more |
| KV-Cache Norm Eviction | xOW2jXDKG3 | ℓ2-norm of key vectors for gradient-free KV eviction | — |
| SimHash KV Compression | R-KVHash (UTRuEFJ57H) | LSH-based KV-cache eviction of redundant reasoning tokens | ~2× decoding throughput |
| Storage→Reflection→Experience | Survey (l9Ly41xxPb) | Memory evolution framework | Design roadmap |
| Experiential Reflective Learning | Illuin (hQgSl6kj1W) | Reflect on trajectories → reusable heuristics | +7.8% over ReAct on Gaia2 |
| LP-RAG | Souza (Y8Txo8vaH7) | Link prediction-based graph RAG | Model-agnostic predictor |
| SABER | Amazon AGI (En2z9dckgP) | Mutation-gated verification + context cleaning | +28% Airline |
| AOI 3-Layer Memory | Q16XXJou3O | Working/Episodic/Semantic memory + context compressor | 72.4% compression, −34.4% MTTR |
| MemGrad Textual Gradients | TCS (GeaPE7iw1V) | Textual gradients → memory + prompt updates | No fine-tuning |
| Localize Compression | KAIST (ztmwHisqJ4) | Compress within modular memory units | Minimize retrieval-update interference |
| A-MAC Admission Control | Workday (mmdqUrEY24) | 5-factor memory admission (utility/confidence/novelty/recency/type) | LoCoMo F1 0.583, −31% latency |
| MemGAS Multi-Granularity | MemGAS | Session/turn/summary/keyword levels, GMM clustering + entropy routing | 38.4% over HippoRAG 2 |
| MemGen Latent Tokens | MemGen | Generative latent memory tokens woven into inference stream | No external DB |
| CraniMem Active Forgetting | CraniMem | Neurocognitive gated bounded multi-stage memory | −11-16% noise |
| REMem Episodic Reasoning | REMem | Episodic memory reasoning | +13.4% vs Mem0/HippoRAG 2 |
| LightMem Bio-Inspired | LightMem | Sensory→short→long-term, sleep-time consolidation | 105× token reduction, 309× fewer API calls |
| Field-Theoretic Memory | Mitra (2602.21220) | Memory as continuous fields governed by PDEs | +116% F1 on LongMemEval |
| COMPASS Hierarchical | Wan (2510.08790) | Main Agent + Meta-Thinker + Context Manager | — |
| ExtAgents Distributed | Liu (2505.21471) | Distribute input across agents beyond context window | — |
| Mem0 Cross-Session | Mem0 | Scalable cross-session memory layer | — |
| Letta/MemGPT OS Model | Letta | LLM-as-OS, self-editing memory with paging | — |
| Zep/Graphiti Temporal KG | Zep | Temporal knowledge-graph memory | — |
| AnnaAgent Multi-Session | Wang (2506.00551) | Tertiary memory across multiple sessions | — |
| MemAgent ICLR Oral | MemAgent (k5nIOvYGCL) | Segment processing + overwrite strategy + DAPO optimization | 8K→3.5M extrapolation, >95% on 512K NIAH |
| CFGM Coarse-to-Fine | Yang (2508.15305) | Multi-granularity coarse→fine grounded memory | — |
| Anthropic Dreaming | Anthropic (May 2026) | Idle-time memory consolidation, dedup, reorganize | ~6× task completion improvement |

---

## Breakthrough Idea #1: Field-Theoretic Memory with PDE-Governed Consolidation

**Sources Fused:** Field-Theoretic Memory (Mitra) + LightMem bio-inspired + Anthropic Dreaming + A-MAC admission control

**Core Mechanism:**
- Memories are NOT discrete DB entries — they are continuous fields in semantic space governed by partial differential equations (PDEs):
  - **Diffusion term:** Memories spread through semantic space over time (similarity-based spreading activation)
  - **Decay term:** Memories decay thermodynamically by importance (∂m/∂t = -λ·(1-I)·m where I = importance)
  - **Coupling term:** Memories of different agents couple across the fleet (∂m_A/∂t ∝ κ·(m_B - m_A) for related memories)
- **Consolidation (Dreaming):** During idle, run a numerical PDE solver that:
  1. Diffuses related memories closer together (discovering latent connections)
  2. Decays low-importance memories (active forgetting)
  3. Couples agent memories for cross-agent pattern discovery
- **Retrieval:** Query as a "source" in the field → memory activation as field response → top-K activated memories
- **Admission:** A-MAC's 5-factor admission (future utility / confidence / novelty / recency / type) gates what enters the field
- **Implementation:** Discretize semantic space as a sparse grid; use finite difference methods for PDE integration; cosine similarity as the distance metric

**Why It Beats Individual Sources:**
- Field-Theoretic Memory alone doesn't handle consolidation scheduling or admission control
- LightMem's bio-inspired pipeline is rigid (fixed stages) — PDE fields are continuous and adaptive
- Anthropic Dreaming is review-based (LLM-reviews-100-conversations) — expensive; PDE solver is algorithmic and cheap
- A-MAC provides the admission gate that prevents field pollution

**Why It Beats Baseline:**
- Lyra's current memory is JSON-file keyword search — O(n) linear scan, no semantic structure, no cross-session patterns, no consolidation beyond simple merge-by-content
- Field-theoretic memory provides O(log n) field queries, continuous semantic structure, emergent cross-session patterns

**Failure Modes:**
- PDE solver may be computationally expensive for large memory banks (mitigation: run during idle only, use sparse methods)
- Field initialization is tricky — cold start has no field structure (mitigation: bootstrap from embeddings)
- Semantic space dimensionality choice matters — too low = conflation, too high = sparsity (mitigation: use embedding model's native dim)

**Impact:** 5 | **Effort:** 5 | **Risk:** High (novel approach, limited implementation precedent)

---

## Breakthrough Idea #2: Zettelkasten Graph Memory with Cost-Sensitive Multi-Store Routing

**Sources Fused:** A-MEM Zettelkasten notes + Cost-Sensitive Store Routing + LP-RAG link prediction + CraniMem active forgetting + MemGAS multi-granularity

**Core Mechanism:**
- **Storage:** Every memory is a Zettelkasten "note" — atomic, densely linked, with contextual descriptions/keywords/tags. Notes form a directed graph (links = explicit cross-references + predicted links).
- **Multi-Granularity Stores (MemGAS-inspired):**
  - Store 0: Working Memory (current session, ring buffer)
  - Store 1: Episodic Memory (session summaries, recent)
  - Store 2: Semantic Memory (facts, knowledge, stable)
  - Store 3: Procedural Memory (skill templates, how-to)
  - Store 4: External (file system, vector DB, graph DB)
- **Cost-Sensitive Routing:** Query arrives → router predicts which store(s) to query based on:
  - Query embedding similarity to store centroids
  - Historical accuracy-per-cost ratio per store
  - Query type classifier (factual → semantic, recent → episodic, how-to → procedural)
- **Link Prediction (LP-RAG):** When a new note is created, an LLM-prompted linker predicts which existing notes it should connect to (cast as inductive link prediction over chunk→query links). Model-agnostic predictor.
- **Active Forgetting (CraniMem):** Gated bounded mechanism — each memory unit has a capacity; when exceeded, forget lowest-importance memories. Noise reduction: 11-16%.
- **Retrieval:** Query → cost-sensitive routing → multi-hop graph traversal (follow links from top-K matched notes) → result fusion

**Why It Beats Individual Sources:**
- A-MEM alone has no cost-sensitive routing — always queries everything
- Cost-sensitive routing paper has no Zettelkasten structure or link prediction
- CraniMem's forgetting is stand-alone — here it's integrated into the multi-store admission control
- MemGAS's granularity is session/turn/summary/keyword — Zettelkasten notes are finer-grained and more linkable

**Why It Beats Baseline:**
- Lyra's current memory is flat (no graph), single-store (no routing), no active forgetting (just decay), no link prediction
- Graph memory enables multi-hop reasoning ("what else relates to this?"), cost routing saves tokens, link prediction discovers latent connections

**Failure Modes:**
- Link prediction may create spurious connections (mitigation: confidence threshold, human review for high-stakes)
- Multi-store routing may route incorrectly (mitigation: fallback to all-store search, learn from failures)
- Graph traversal can be expensive for dense graphs (mitigation: depth limit, beam search)

**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Generative Latent Memory Tokens with Idle-Time Consolidation

**Sources Fused:** MemGen latent tokens + LightMem sleep-time update + Anthropic Dreaming + MemAgent ICLR Oral (segment processing + overwrite + DAPO)

**Core Mechanism:**
- **No external DB:** Memory is encoded as a fixed-size set of learnable latent tokens (like MemGen) that are prepended to the input at inference time. These tokens are trained/updated to compress and represent the agent's entire memory.
- **Segment Processing (MemAgent):** Long text is processed in segments; memory tokens are updated via an overwrite strategy (not append) — old relevant info is overwritten with newer, more relevant info.
- **DAPO Optimization:** Memory read/write policy is trained end-to-end via RL (DAPO — Direct Alignment from Preference Optimization) to maximize task performance.
- **Idle-Time Consolidation (Dreaming):** During idle periods, the system:
  1. Replays recent interactions
  2. Runs the overwrite policy to consolidate latent tokens (merge duplicates, strengthen important, weaken outdated)
  3. Evaluates consolidation quality via a self-consistency check (does the model produce the same answers?)
- **105× Token Reduction (LightMem):** By storing only latent tokens instead of full conversation history, token usage drops by 105× compared to full-context retention.

**Why It Beats Individual Sources:**
- MemGen has no consolidation/update mechanism — tokens are static after generation
- LightMem's bio-inspired pipeline is explicit (stores, not latent tokens)
- Anthropic Dreaming reviews 100 conversations with an LLM — expensive; latent token consolidation is algorithmic
- MemAgent has no idle-time consolidation — it updates during active processing only

**Why It Beats Baseline:**
- Lyra's memory stores full text in JSON — enormous token waste on retrieval
- Latent tokens compress everything into a fixed-size representation — constant retrieval cost regardless of memory size
- No external DB dependency — memory lives in the model's inference stream

**Failure Modes:**
- Latent tokens may lose fine detail (mitigation: hybrid — latent tokens for gist + external DB for details)
- Training the DAPO policy requires RL infrastructure (mitigation: start with heuristic overwrite, add RL later)
- Cold start: no latent tokens exist initially (mitigation: bootstrap from embedding of first few interactions)

**Impact:** 5 | **Effort:** 5 | **Risk:** High

---

## Expert Check (Memory Personas)

**Senior AI Researcher:** "Field-theoretic memory is the most novel but also the riskiest — there's one paper and no production system using it. Zettelkasten graph is the safest bet — it's well-studied (Memex, Roam, Obsidian) and A-MEM already benchmarks it. Latent tokens are elegant but the DAPO training may be brittle across providers."

**Senior Backend Engineer:** "Graph memory with cost-sensitive routing is the most buildable right now. We can start with SQLite + a graph layer, add embedding search, then route. Field-theoretic requires a PDE solver — that's exotic infrastructure. Latent tokens require RL training loops — that's a whole separate system."

**Senior Data/Knowledge Engineer:** "The pragmatic path: start with Zettelkasten graph (Idea #2) as the (A) parity tier, then add field-theoretic consolidation (Idea #1) as the (B) breakthrough tier for the idle-time dreaming phase. Latent tokens (Idea #3) are a longer-term research bet."

**Adversarial Skeptic:** "All three ideas add significant complexity over Lyra's current flat JSON store. Does the baseline improvement — say, just adding embedding search to the current store — get us 80% of the benefit for 20% of the effort? The answer is probably yes for most use cases. The field-theoretic approach in particular is unproven — one paper on LongMemEval does not make it production-ready."

**Resolution:** Start with embedding-based semantic search as the immediate upgrade (low effort, high impact). Build the Zettelkasten graph memory (Idea #2) as the (A) parity tier. Implement field-theoretic consolidation (Idea #1) as the (B) breakthrough tier — but gate it behind a 3-month eval period after the graph memory ships. Park latent tokens (Idea #3) as a research bet for Run 2.
