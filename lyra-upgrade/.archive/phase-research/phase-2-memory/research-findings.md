# Phase 2 Memory Architecture Research Findings

## Research Methodology

Comprehensive analysis of ICLR 2026 MemAgent Workshop papers, arXiv preprints, and open-source memory repositories to identify breakthrough memory architecture patterns for Lyra.

**Sources analyzed:**
- 15+ ICLR 2026 MemAgent Workshop papers
- 5 arXiv papers on agent memory systems
- 8 open-source memory repositories (Mem0, Letta, Zep/Graphiti, TencentDB, Acontext, claude-mem, MemPalace, A-MEM)

---

## Paper-by-Paper Analysis

### ICLR 2026 MemAgent Workshop Papers

| Paper | Problem | Mechanism | Results | Limitations | Transferable Idea | Impact | Effort | Tier |
|-------|---------|-----------|---------|-------------|-------------------|--------|--------|------|
| **A-MEM: Agentic Memory for LLM Agents** | Current memory systems lack sophisticated organization despite using graph databases | Zettelkasten-based dynamic memory organization: generates contextual descriptions, keywords, tags; identifies connections with historical memories; enables memory evolution through triggered updates | Superior performance vs SOTA baselines across 6 foundation models (NeurIPS 2025) | Requires LLM calls for memory organization; potential latency overhead | **Dynamic memory linking with Zettelkasten principles** — memories self-organize through contextual attributes and bidirectional connections | HIGH | MED | **BREAKTHROUGH** |
| **Cost-Sensitive Store Routing** | Memory-augmented agents retrieve from all stores for every query, causing inefficiency | Frames retrieval as store-routing problem; oracle router achieves higher QA accuracy with fewer context tokens; formalizes as cost-sensitive decision balancing accuracy vs retrieval cost | Oracle router: better accuracy + substantially reduced token usage | Oracle is not learnable; needs practical routing policy | **Selective memory store routing** — route queries to relevant memory stores only, not all stores | HIGH | LOW | **PARITY** |
| **Memory Transplants** | Unclear whether memory transfer gains come from architecture (storage/retrieval) or content (experiences) | 2×2 factorial design separating architecture vs content transfer using code-to-math domain shift; tests 7 transplant conditions, 5 memory systems, 6 validation gates | Architecture transfer is system-dependent; content transfer provides limited benefit in static mode; weaker models gain +15pp vs +7pp for stronger models | Limited to code-to-math shift; static regime shows minimal content benefit | **Memory transfer is model-capability dependent** — weaker models benefit more from memory transfer | MED | LOW | INSIGHT |
| **SelfEvoWM** | World models for robot learning lack grounding and fail to self-improve | Generate-verify-repair loop with DROID-grounded world models; VLM critic audits physical consistency; automated simulation environments repair weak regions | Early-stage system design; identifies failure modes (retrieval collapse, contact artifacts, VLM sensitivity) | Not production-ready; no finished benchmarks | **Self-evolving memory through generate-verify-repair** — applicable to agent memory refinement | MED | HIGH | FUTURE |
| **Norm-Guided KV-Cache Eviction** | KV-cache scales quadratically with context length in reasoning models | ℓ₂-Norm Eviction: scores tokens by mean ℓ₂-norm of key vectors; keeps high-norm + recent tokens; single-pass, no attention tracking | At 512-2048 tokens: matches full cache; at 256 tokens (87.5% reduction): sliding window (EM=0.25) > ℓ₂-Norm (EM=0.05) on GSM8K | Recency dominates at very tight budgets; needs adaptive pool sizing | **Norm-based token importance** — lightweight alternative to attention-based scoring | LOW | LOW | PARITY |
| **MemGrad** | Agentic systems don't translate multi-trajectory feedback into lasting behavioral improvements | Textual gradients convert feedback batches into interpretable improvement directions; dual memory: retrospective (patterns/failures) + prospective (gradient-derived strategies); updates system prompts without fine-tuning | Improved task success, reasoning stability, user intent alignment on AgileCoder | Requires batch feedback; prompt-based only (no weight updates) | **Retrospective-prospective memory architecture** — learn from past failures, plan future strategies | HIGH | MED | **BREAKTHROUGH** |
| **LP-RAG** | Graph-based RAG fails to exploit query-based semantic cues | Builds similarity graph among chunks; generates chunk-conditioned synthetic queries; treats retrieval as inductive link prediction; model-agnostic (works with GNNs) | Consistently outperforms existing RAG methods across diverse benchmarks | Requires synthetic query generation; GNN overhead | **Link prediction for retrieval** — frame memory retrieval as graph link prediction | MED | MED | PARITY |
| **A-MAC (Adaptive Memory Admission Control)** | Agents accumulate excessive conversational content including hallucinations; opaque LLM-driven policies | 5 interpretable factors: future utility, factual confidence, semantic novelty, temporal recency, content type prior; rule-based extraction + LLM utility assessment; cross-validated optimization | F1=0.583 on LoCoMo; 31% latency reduction vs LLM-native systems; content type prior most influential | Requires labeled data for optimization; factor weights need tuning | **Multi-factor memory admission control** — structured decision using interpretable factors | HIGH | MED | **BREAKTHROUGH** |
| **AOI Multi-Agent System** | Cloud-native IT ops generate overwhelming data volumes; microservices create complexity | Multi-agent framework with LLM-based context compressor; dynamic task scheduling; **3-layer memory: Working, Episodic, Semantic** | 72.4% context compression preserving 92.8% critical info; 94.2% task success; 34.4% MTTR reduction | Domain-specific (IT ops); requires specialized agents | **3-layer memory architecture (Working/Episodic/Semantic)** — hierarchical memory with different retention policies | HIGH | HIGH | **BREAKTHROUGH** |
| **Experiential Reflective Learning (ERL)** | LLM agents fail to leverage past interactions; struggle in specialized environments | Reflects on task trajectories to generate heuristics; retrieves relevant heuristics at test time; injects into context to guide execution | +7.8% success rate on Gaia2 vs ReAct; outperforms prior experiential learning; selective retrieval essential; heuristics > few-shot trajectories | Requires successful trajectories to learn from; heuristic quality varies | **Heuristic extraction from trajectories** — abstract transferable lessons from experiences | HIGH | LOW | **PARITY** |
| **Localize Compression** | Memory compression causes behavioral interference in long-horizon agents | Formalizes interference as expected policy divergence; modular designs minimize retrieval-update overlap; routing stability controls interference via retrieval probability | Mathematical bounds on update-induced interference; modular architectures reduce behavioral drift | Theoretical framework; needs empirical validation | **Modular memory to localize compression effects** — isolate updates to minimize interference | MED | MED | INSIGHT |
| **SABER** | LLM agents fail on long-horizon tasks; unclear if all actions contribute equally | Distinguishes mutating (environment-changing) vs non-mutating steps; deviations in mutating actions reduce success by 92-96%; SABER: mutation-gated verification + Targeted Reflection + block-based context cleaning | Qwen3-Thinking: +28% Airline, +11% Retail, +7% SWE-Bench; Claude: +9%, +7% | Requires action classification; overhead for verification | **Mutating action safeguards** — focus verification on environment-changing actions | HIGH | MED | **PARITY** |
| **Storage to Experience Survey** | Fragmented LLM agent memory research lacks unified framework | 3-stage evolution: Storage (trajectory preservation) → Reflection (refinement) → Experience (abstraction); identifies drivers: long-range consistency, dynamic environments, continual learning | Provides design principles and roadmap for next-gen agents | Survey paper; no implementation | **Memory evolution framework** — progression from storage to experience-based learning | MED | N/A | INSIGHT |
| **Feedback Descent** | Scalar rewards create information bottleneck in text optimization | Pairwise comparison with preference + rationale; rationales provide directional guidance; operates at inference time without weight updates | Matches SOTA prompt optimization (GEPA); outperforms GRPO, REINVENT; discovers molecules >99.9th percentile | Requires evaluator model; pairwise comparison overhead | **Textual feedback over scalar rewards** — richer optimization signals through explanations | MED | MED | PARITY |
| **R-KVHash** | Reasoning models generate verbose traces causing excessive KV-cache growth; R-KV requires expensive pairwise similarity calculations | SimHash-based locality-sensitive hashing for key similarity estimation; sub-linear memory/compute; buckets keys via binarized Gaussian projection | 2× higher decoding throughput vs R-KV; competitive accuracy on MATH500, GSM8K with DeepSeek-R1-Distill 7B/14B | Specific to reasoning models; hash collision tradeoffs | **LSH for KV-cache compression** — efficient similarity estimation without attention tracking | MED | MED | PARITY |

---

### arXiv Papers

| Paper | Problem | Mechanism | Results | Limitations | Transferable Idea | Impact | Effort | Tier |
|-------|---------|-----------|---------|-------------|-------------------|--------|--------|------|
| **Memp (2508.06433)** | Agents lack learnable, updatable, lifelong procedural memory | Distills trajectories into fine-grained step-by-step instructions + higher-level script-like abstractions; explores Build, Retrieval, Update operations | Improved performance and efficiency across tasks | Requires trajectory distillation; abstraction quality varies | **Dual-level procedural memory** — fine-grained + abstract representations | HIGH | MED | **PARITY** |
| **PersonaAgent (2506.06254)** | LLMs lack personalization beyond fixed context windows | Personalized memory module (episodic + semantic) + personalized action module | Enables user-specific adaptation | Requires user interaction data; privacy concerns | **Episodic + semantic memory for personalization** | MED | MED | PARITY |
| **MemSearcher (2511.02805)** | Multi-turn interactions cause unbounded context growth | Fuses question with memory to generate reasoning traces, search actions, memory updates; retains only task-essential info; end-to-end RL training | Stabilizes context length across multi-turn interactions; maintains accuracy | Requires RL training; complex optimization | **Memory-as-action with RL** — learn what to remember through RL | HIGH | HIGH | **BREAKTHROUGH** |
| **Contextual Experience Replay (2506.06698)** | Language agents can't reuse solutions from structurally similar tasks | Synthesizes past experiences for self-improvement; enables learning from previous interactions | Improved performance on web navigation tasks (ACL 2025) | Requires experience buffer; similarity matching overhead | **Experience replay for language agents** — reuse solutions from similar past tasks | HIGH | MED | **PARITY** |
| **MemAgent ICLR Oral (2507.02259)** | Long-context LLMs struggle beyond training context length | Multi-conversation RL-based memory agent with overwrite strategy | Extrapolates 8K→3.5M tokens with <10% loss; 95%+ on 512K NIAH | Requires RL training; complex architecture | **RL-based memory management** — learn optimal memory operations | HIGH | HIGH | **BREAKTHROUGH** |

---

### Open-Source Memory Repositories

| Repository | Architecture | Key Features | Strengths | Limitations | Transferable Idea | Impact | Effort | Tier |
|------------|--------------|--------------|-----------|-------------|-------------------|--------|--------|------|
| **Mem0** | Universal memory layer | Multi-provider support; semantic search; automatic memory updates | Simple API; broad compatibility | Basic memory model; limited structure | **Universal memory interface** — provider-agnostic memory API | HIGH | LOW | PARITY |
| **Letta (MemGPT)** | Stateful agents with persistent memory | Virtual context management; memory blocks; agent serialization (.af format) | Production-ready; strong community | Complex setup; opinionated architecture | **Virtual context management** — OS-like memory paging for LLMs | HIGH | HIGH | **BREAKTHROUGH** |
| **Zep/Graphiti** | Temporal knowledge graph | Real-time KG construction; temporal reasoning; entity/relationship extraction | Enterprise-grade; outperforms MemGPT on DMR benchmark | Requires graph database; complexity overhead | **Temporal knowledge graphs** — time-aware entity relationships | HIGH | HIGH | **BREAKTHROUGH** |
| **TencentDB Agent Memory** | 4-tier progressive pipeline | Fully local; zero external API dependencies; tiered memory hierarchy | Privacy-preserving; self-contained | Limited documentation; Chinese-focused | **4-tier progressive memory** — hierarchical memory with progressive refinement | MED | MED | PARITY |
| **Acontext** | Agent skills as memory | Captures learnings from agent runs; stores as Markdown; shareable across agents/LLMs | Human-readable; portable; simple | Limited structure; no semantic search | **Skills-as-memory** — procedural knowledge as portable artifacts | MED | LOW | PARITY |
| **claude-mem** | Persistent context across sessions | Captures agent actions; AI-powered compression; injects relevant context | Works with multiple agents (Claude Code, OpenClaw, etc.) | Compression quality varies; requires tuning | **Session-aware compression** — compress and inject relevant past context | HIGH | MED | PARITY |
| **MemPalace** | Benchmarked memory system | Semantic search with knowledge graph; remember/recall/forget operations | Claims best benchmark scores | Limited documentation; unclear architecture | **Benchmark-driven memory** — optimize for memory benchmarks | MED | MED | PARITY |
| **A-MEM (agiresearch)** | Zettelkasten-based | Dynamic memory organization; contextual linking; memory evolution | Research-backed (NeurIPS 2025); sophisticated organization | Requires LLM for organization; latency overhead | **Zettelkasten for agents** — self-organizing memory network | HIGH | MED | **BREAKTHROUGH** |

---

## Additional Papers from Search

| Paper | Problem | Mechanism | Results | Transferable Idea | Impact | Tier |
|-------|---------|-----------|---------|-------------------|--------|------|
| **AnnaAgent (2506.00551)** | Realistic seeker simulation in counseling lacks memory continuity | Tertiary memory mechanism integrating short-term + long-term across sessions; emotion modulator + complaint elicitor | More realistic seeker simulation vs baselines | **Tertiary memory (short-term + long-term integration)** | MED | PARITY |
| **DAVIS (2410.09252)** | Traditional RAG fails to exploit temporal structure | Structured temporal memory with model-based planning; agentic multi-turn retrieval (inner monologue) | Greater reasoning over past experiences | **Inner monologue retrieval** — multi-turn reasoning over memory | HIGH | **PARITY** |
| **ACON (2510.00615)** | Long-horizon agents face memory bloat | Context compression optimized for long-horizon tasks | 26-54% memory reduction; >95% accuracy preserved | **Task-aware context compression** | HIGH | **PARITY** |
| **MSI-Agent (2409.16686)** | LLMs struggle with multi-scale planning | Multi-scale insight summarization across different abstraction levels | Improved planning and decision-making | **Multi-scale memory abstraction** | MED | PARITY |
| **Multi-Agent Memory (2603.10062)** | Multi-agent systems lack memory architecture principles | 3-layer hierarchy (I/O, cache, memory); shared vs distributed memory paradigms | Computer architecture framing for agent memory | **3-layer memory hierarchy** | MED | INSIGHT |
| **Memory Survey (2603.07670)** | Fragmented memory research lacks synthesis | Comprehensive survey of memory mechanisms, evaluation, emerging frontiers (2022-2026) | Unified view of agent memory landscape | **Memory taxonomy and evaluation framework** | MED | INSIGHT |

---

## Key Insights & Patterns

### 1. **Multi-Layer Memory Architectures** (BREAKTHROUGH)

**Pattern:** Multiple papers converge on hierarchical memory with different retention policies and access patterns.

**Evidence:**
- **AOI System:** Working (immediate context) → Episodic (recent experiences) → Semantic (long-term knowledge)
- **MemGrad:** Retrospective (past patterns/failures) → Prospective (future strategies)
- **TencentDB:** 4-tier progressive pipeline with hierarchical refinement
- **Multi-Agent Memory:** I/O layer → Cache layer → Memory layer
- **AnnaAgent:** Tertiary memory integrating short-term + long-term

**Transferable to Lyra:** Implement 3-4 layer memory hierarchy with distinct purposes and retention policies.

---

### 2. **Dynamic Memory Organization** (BREAKTHROUGH)

**Pattern:** Static memory structures fail; dynamic self-organization through semantic linking improves retrieval and reasoning.

**Evidence:**
- **A-MEM:** Zettelkasten-based dynamic linking with contextual attributes
- **Zep/Graphiti:** Temporal knowledge graphs with entity/relationship extraction
- **MemGrad:** Memory evolution through triggered updates
- **LP-RAG:** Link prediction for retrieval

**Transferable to Lyra:** Memories should self-organize through semantic connections, not just chronological storage.

---

### 3. **Selective Memory Operations** (HIGH IMPACT)

**Pattern:** Not all memories are equal; selective admission, routing, and eviction improve efficiency and accuracy.

**Evidence:**
- **A-MAC:** 5-factor admission control (utility, confidence, novelty, recency, content type)
- **Cost-Sensitive Routing:** Route queries to relevant stores only
- **SABER:** Focus verification on mutating actions (92-96% impact)
- **R-KVHash:** Evict low-importance tokens based on norm

**Transferable to Lyra:** Implement intelligent memory admission and routing policies.

---

### 4. **Experience Abstraction** (HIGH IMPACT)

**Pattern:** Raw trajectories are inefficient; abstract into reusable heuristics, procedures, or insights.

**Evidence:**
- **ERL:** Extract heuristics from trajectories (+7.8% on Gaia2)
- **Memp:** Dual-level procedural memory (fine-grained + abstract)
- **Storage to Experience Survey:** Evolution from storage → reflection → experience
- **Acontext:** Skills-as-memory (procedural knowledge)

**Transferable to Lyra:** Store both raw experiences and abstracted lessons/heuristics.

---

### 5. **Memory-as-Action with RL** (BREAKTHROUGH)

**Pattern:** Treat memory operations (what to store, retrieve, update, forget) as learnable policies optimized through RL.

**Evidence:**
- **MemSearcher:** End-to-end RL for reasoning, search, memory management
- **MemAgent:** Multi-conversation RL with overwrite strategy (8K→3.5M extrapolation)
- **A-MAC:** Cross-validated optimization of admission policies

**Transferable to Lyra:** Long-term opportunity to learn optimal memory policies through RL.

---

### 6. **Compression with Preservation** (HIGH IMPACT)

**Pattern:** Compress memory to fit context limits while preserving task-critical information.

**Evidence:**
- **AOI:** 72.4% compression preserving 92.8% critical info
- **ACON:** 26-54% memory reduction with >95% accuracy
- **claude-mem:** AI-powered compression with relevance injection
- **Localize Compression:** Modular design to minimize interference

**Transferable to Lyra:** Implement intelligent compression that preserves task-relevant information.

---

### 7. **Temporal Reasoning** (HIGH IMPACT)

**Pattern:** Time-aware memory enables better context understanding and retrieval.

**Evidence:**
- **Zep/Graphiti:** Temporal knowledge graphs
- **DAVIS:** Temporal memory with model-based planning
- **A-MAC:** Temporal recency as admission factor
- **AnnaAgent:** Cross-session temporal integration

**Transferable to Lyra:** Track temporal relationships between memories.

---

## Synthesis: Breakthrough Architecture Opportunities

### **Option A: Fusion Architecture** (HIGHEST POTENTIAL)

Combine the best techniques from multiple papers into a unified system:

1. **3-Layer Hierarchy** (from AOI + Multi-Agent Memory)
   - **Working Memory:** Current session context (sliding window)
   - **Episodic Memory:** Recent experiences with temporal ordering
   - **Semantic Memory:** Long-term knowledge graph with Zettelkasten linking

2. **Dynamic Organization** (from A-MEM + Zep)
   - Zettelkasten-style bidirectional linking
   - Temporal knowledge graph for entity/relationship tracking
   - Automatic memory evolution through triggered updates

3. **Intelligent Admission** (from A-MAC)
   - 5-factor scoring: utility, confidence, novelty, recency, content type
   - Learned admission thresholds per memory layer

4. **Experience Abstraction** (from ERL + Memp)
   - Store raw trajectories in Episodic
   - Extract heuristics/procedures into Semantic
   - Dual-level representation (fine-grained + abstract)

5. **Selective Routing** (from Cost-Sensitive Routing)
   - Route queries to relevant memory layers/stores
   - Minimize unnecessary retrieval overhead

6. **Compression with Preservation** (from AOI + ACON)
   - Layer-specific compression strategies
   - Preserve task-critical information
   - Modular design to localize compression effects

**Impact:** BREAKTHROUGH — no single paper combines all these techniques
**Effort:** HIGH — requires integrating 6+ distinct mechanisms
**Risk:** Complexity; integration challenges; performance overhead

---

### **Option B: Minimal Viable Memory** (FASTEST TO IMPLEMENT)

Start with proven, low-effort techniques:

1. **2-Layer Hierarchy**
   - Working Memory: Current session (sliding window)
   - Long-Term Memory: Vector store with semantic search

2. **Simple Admission Control**
   - Recency + semantic novelty threshold
   - Content type filtering (exclude logs, debug output)

3. **Basic Compression**
   - Summarize old working memory before moving to long-term
   - Keep only high-importance items

**Impact:** PARITY — matches existing systems like Mem0, claude-mem
**Effort:** LOW — 2-3 weeks implementation
**Risk:** LOW — well-understood patterns

---

### **Option C: RL-Optimized Memory** (HIGHEST CEILING)

Focus on learnable memory policies:

1. **Memory-as-Action Framework** (from MemSearcher + MemAgent)
   - Treat store/retrieve/update/forget as RL actions
   - Learn optimal policies through task performance feedback

2. **Adaptive Routing** (from Cost-Sensitive Routing)
   - Learn which memory stores to query for each task type

3. **Dynamic Compression** (from ACON + Localize Compression)
   - Learn what to compress and when
   - Minimize task performance degradation

**Impact:** BREAKTHROUGH — highest potential performance
**Effort:** VERY HIGH — requires RL infrastructure, training data, compute
**Risk:** HIGH — RL training instability; requires significant data

---

## Recommendations for Lyra

### Phase 2A: Foundation (Weeks 1-3)
Implement **Option B** (Minimal Viable Memory) to establish baseline:
- 2-layer hierarchy (Working + Long-Term)
- Vector store with semantic search
- Simple admission control (recency + novelty)
- Basic compression (summarization)

### Phase 2B: Enhancement (Weeks 4-8)
Incrementally add **Option A** components:
- Expand to 3-layer hierarchy (Working + Episodic + Semantic)
- Add Zettelkasten-style linking (from A-MEM)
- Implement 5-factor admission control (from A-MAC)
- Add experience abstraction (heuristic extraction from ERL)
- Implement selective routing (from Cost-Sensitive Routing)

### Phase 2C: Optimization (Weeks 9-12)
Add advanced features:
- Temporal knowledge graph (from Zep/Graphiti)
- Intelligent compression (from AOI + ACON)
- Memory evolution (triggered updates from MemGrad)

### Phase 3: Research (Future)
Explore **Option C** (RL-Optimized Memory):
- Design RL framework for memory operations
- Collect training data from Lyra usage
- Train memory policies
- Evaluate against benchmarks

---

## Open Questions

1. **Memory Persistence:** How to serialize/deserialize complex memory structures (KG, Zettelkasten links)?
2. **Multi-Provider Support:** How to maintain memory consistency across different LLM providers?
3. **Privacy:** How to handle sensitive information in long-term memory?
4. **Evaluation:** What benchmarks to use for Lyra memory system? (LoCoMo, DMR, custom?)
5. **Scalability:** How does memory performance degrade with 1K, 10K, 100K memories?
6. **Conflict Resolution:** How to handle contradictory memories?
7. **Memory Decay:** Should old memories fade or remain indefinitely?
8. **Cross-Session Continuity:** How to resume interrupted tasks using memory?

---

## References

### ICLR 2026 MemAgent Workshop
- [A-MEM](https://openreview.net/forum?id=FiM0M8gcct)
- [Cost-Sensitive Store Routing](https://openreview.net/forum?id=iGRGjdhl9r)
- [Memory Transplants](https://openreview.net/forum?id=AIJsjIqfsp)
- [SelfEvoWM](https://openreview.net/forum?id=lVn5vLOkjP)
- [Norm-Guided KV-Cache](https://openreview.net/forum?id=xOW2jXDKG3)
- [MemGrad](https://openreview.net/forum?id=GeaPE7iw1V)
- [LP-RAG](https://openreview.net/forum?id=Y8Txo8vaH7)
- [A-MAC](https://openreview.net/forum?id=mmdqUrEY24)
- [AOI Multi-Agent](https://openreview.net/forum?id=Q16XXJou3O)
- [ERL](https://openreview.net/forum?id=hQgSl6kj1W)
- [Localize Compression](https://openreview.net/forum?id=ztmwHisqJ4)
- [SABER](https://openreview.net/forum?id=En2z9dckgP)
- [Storage to Experience Survey](https://openreview.net/forum?id=l9Ly41xxPb)
- [Feedback Descent](https://openreview.net/forum?id=Uw5G3H26ps)
- [R-KVHash](https://openreview.net/forum?id=UTRuEFJ57H)

### arXiv Papers
- [Memp (2508.06433)](https://arxiv.org/abs/2508.06433)
- [PersonaAgent (2506.06254)](https://api.emergentmind.com/papers/2506.06254)
- [A-MEM Full (2502.12110)](https://arxiv.org/abs/2502.12110)
- [MemSearcher (2511.02805)](https://arxiv.org/abs/2511.02805)
- [Contextual Experience Replay (2506.06698)](https://arxiv.org/abs/2506.06698)
- [MemAgent ICLR Oral (2507.02259)](https://arxiv.org/abs/2507.02259)
- [AnnaAgent (2506.00551)](https://arxiv.org/abs/2506.00551)
- [DAVIS (2410.09252)](https://arxiv.org/abs/2410.09252)
- [ACON (2510.00615)](https://arxiv.org/abs/2510.00615)
- [MSI-Agent (2409.16686)](https://arxiv.org/abs/2409.16686)
- [Multi-Agent Memory (2603.10062)](https://arxiv.org/abs/2603.10062)
- [Memory Survey (2603.07670)](https://arxiv.org/abs/2603.07670)

### Open-Source Repositories
- [Mem0](https://github.com/mem0ai/mem0)
- [Letta (MemGPT)](https://github.com/letta-ai/letta)
- [Zep/Graphiti](https://github.com/getzep/graphiti)
- [TencentDB Agent Memory](https://github.com/Tencent/TencentDB-Agent-Memory)
- [Acontext](https://github.com/memodb-io/Acontext)
- [claude-mem](https://github.com/thedotmack/claude-mem)
- [MemPalace](https://github.com/mempalace/mempalace)
- [A-MEM Implementation](https://github.com/agiresearch/A-mem)

---

**Research completed:** 2026-05-31
**Next steps:** Create detailed architecture plan (01-memory-architecture.md) and context optimization plan (02-context-optimization.md)
