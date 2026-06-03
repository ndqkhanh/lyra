# MemAgent Workshop @ ICLR 2026 -- Memory Papers Deep-Read

> Deep-read of all memory papers from the ICLR 2026 MemAgent Workshop.
> Conducted: 2026-06-03
> Researcher: Senior AI Researcher, Lyra Project

---

## 1. Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer Under a Code-to-Math Shift
**URL:** https://openreview.net/pdf?id=AIJsjIqfsp
**Authors:** Zhaoxiang Feng, Mingyang Yao, David Scott Lewis (UC San Diego / AIXC)

**Core Mechanism (step-by-step):** Provides a **memory transplant protocol** that cleanly separates architecture (retrieval policies, pruning rules, gating) from content (canonical memory items) as independent experimental factors. Uses a 2x2 factorial design across a code (LiveCodeBench 60 problems) -> math (MATH 30 build + 100 eval) domain shift. Defines seven transplant conditions: NM (no memory), E_MATH (math arch, empty), E_CODE (code arch, empty), C_ONLY (math arch, code content, static), FULL (code arch, code content, static), IN_DOM (math arch, math content, static), CROSS (code arch, math content, static). Canonical items exported as JSONL with id, text, type, source domain, episode_id, success boolean, order index. Import loads verbatim; architecture-dependent structures (embeddings, tier placements) are recomputed by the receiving system. Prompt-freeze rule enforced via SHA-256 hash verification.

**Results (real numbers):** Qwen 2.5 7B: NM baseline ~64%. Best: AGENT KB E_MATH at budget 400 = 71.0% (+6.7pp). Most effects within 2-5pp range. Llama 3.2 3B: NM baseline ~37%. Best: EXPEL E_MATH at budget 800 = 52.0% (+15pp). Content transfer (C_ONLY) limited; only EXPEL showed notable static content transfer (70.0% at budget 800 vs 64.0% NM at 7B). Architecture transfer is system-dependent with no universal direction. AGENT KB favors E_MATH at 400-token budget (71% > 66.3%) but favors E_CODE at 800-token budget (68% > 66.7%). Negative transfer observed: several conditions below NM baseline. Budget non-monotonicity: increasing retrieval budget from 400 to 800 sometimes helps (EXPEL C_ONLY: 63.3% -> 70.0%) sometimes hurts (NO MEM C_ONLY: 67.7% -> 63.3%).

**Trade-offs:** Architecture transfer is system-dependent and budget-sensitive with no universal direction. Content transfer provides limited benefit in static mode. Weaker models benefit more (+15pp vs +7pp). Negative transfer is common. 95% CIs span 2-8pp for 3-seed cells, limiting statistical power. Prompt-freeze rule depresses absolute accuracy vs published benchmarks.

**Design Rationale:** 2x2 factorial design is the paper's key innovation -- enables causal claims about what transfers. The code-to-math shift is deliberately large to make the transfer question non-trivial. Seven conditions plus four negative control types (random retrieval, placebo, write-only, frozen-store MU) address major confounds. Six pre-registered validation gates prevent data leakage, prompt leakage, and grader errors.

**Transferable Idea for Lyra:** The transplant protocol itself: Lyra should systematically evaluate whether memory gains come from architecture (retrieval/ pruning policies) or content (specific stored items). The prompt-freeze rule (SHA-256 hash verification) is directly applicable. The finding that "retrieval frequency control acts as a natural regularizer" (lightweight memory with N=3) is directly relevant to Lyra's token-budget management.

**Gap vs Baseline:** Partial. Lyra's MemoryStore + MemoryIndex does NOT systematically disentangle architecture from content. Lyra should adopt this paper's factorial methodology for evaluating memory design changes.

---

## 2. A-MEM: Agentic Memory for LLM Agents
**URL:** https://openreview.net/pdf?id=FiM0M8gcct
**Authors:** Wujiang Xu et al. (Rutgers University)

**Core Mechanism (step-by-step):** Zettelkasten-inspired agentic memory. Each memory note m_i = {c_i, t_i, K_i, G_i, X_i, e_i, L_i} where c_i = interaction content, t_i = timestamp, K_i = LLM-generated keywords, G_i = LLM-generated tags, X_i = LLM-generated contextual description, e_i = dense embedding, L_i = linked memories. Note construction: K_i, G_i, X_i <- LLM(c_i || t_i || Ps1). Embedding: e_i = f_enc(concat(c_i, K_i, G_i, X_i)). Link generation: cosine similarity s_{n,j} = (e_n . e_j)/(|e_n||e_j|), nearest neighbors M_n_near = top-k, then LLM generates links. Memory evolution: m*_j <- LLM(m_n || M_n_near \ m_j || m_j || Ps3) -- updates context, keywords, tags of existing memories. Retrieval: cosine similarity with query embedding, top-k. Uses k=10 default, tuned per category (up to 50). Embedding model: all-minilm-l6-v2.

**Results (real numbers):** LoCoMo dataset (7,512 QA pairs, 9K tokens avg, up to 35 sessions). GPT-4o-mini: A-MEM Avg F1=27.02, BLEU=20.09 vs LoCoMo (2.4,2.4), MemGPT (2.4,2.4). Temporal category: A-MEM F1=45.85 vs MemGPT F1=25.52. Adversarial: A-MEM F1=50.03 vs MemGPT F1=43.29. On DialSim: A-MEM F1=3.45 vs LoCoMo 2.55 vs MemGPT 1.18. Token cost: ~1,200 tokens/operation vs LoCoMo/MemGPT ~16,900 tokens (85-93% reduction). Processing time: 5.4s with GPT-4o-mini, 1.1s with Llama 3.2 1B on single GPU. Retrieval time scales from 0.31 us (1K entries) to 3.70 us (1M entries). Ablation: w/o LG&ME drops from 27.02 to 9.65 F1 (Multi Hop). w/o ME (only link generation active): 21.35 F1.

**Trade-offs:** LLM-dependent quality -- K_i, G_i, X_i quality limited by underlying LLM. Token cost for LLM calls per memory operation (~1,200 tokens). Requires careful tuning of k per task category. Performance degrades at very high k values due to noise. Text-only; no multimodal support.

**Design Rationale:** Zettelkasten provides principled framework for atomic notes and flexible linking. LLM-driven analysis goes beyond embedding similarity for subtle pattern identification. Memory evolution mimics human learning -- new connections trigger updates to existing memories.

**Transferable Idea for Lyra:** The multi-attribute note structure (content + LLM-generated context/keywords/tags + embedding + links) is directly applicable to Lyra's MemoryStore. The link generation and memory evolution mechanism could transform Lyra from flat store to interconnected knowledge network. The token efficiency (1,200 vs 16,900 tokens) is critical for production deployment.

**Gap vs Baseline:** Significant gap. Lyra's MemoryStore stores flat items with basic keyword extraction. A-MEM's structured notes with LLM-generated context/keywords/tags + automatic linking + memory evolution would be a major upgrade. Implementation cost is moderate (adds LLM calls per memory write).

---

## 3. Did You Check the Right Pocket? Cost-Sensitive Store Routing for Memory-Augmented Agents
**URL:** https://openreview.net/pdf?id=iGRGjdhl9r
**Authors:** Madhava Gaikwad (Independent)

**Core Mechanism (step-by-step):** Formulates memory store selection as a routing problem. Given stores S = {STM, Summary, LTM, Episodic}, policy pi selects subset G_hat = pi(q) subset S. Evaluated via Coverage = (1/N) sum 1[G_i subset G_hat_i], Exact Match = (1/N) sum 1[G_i = G_hat_i], Waste = (1/N) sum |G_hat_i\G_i|. Cost-sensitive objective: pi*(q) = argmax_{G subset S} [E[Acc(q,G)] - lambda * sum_{s in G} c_s]. Hybrid heuristic combines semantic pattern matching + embedding similarity tiebreaker. 7 query types mapped to store requirements.

**Results (real numbers):** Synthetic routing (1,000 queries): Hybrid achieves 94% coverage, 58% EM, 1.2 waste vs Uniform 100%/8%/2.9, Oracle 100%/100%/0.0. LLM evaluation (150 questions): Oracle routing 86.7% accuracy with 299 tokens vs Uniform 81.3% with 787 tokens (62% fewer tokens). On long-context questions: Oracle 72% vs Uniform 60%. Fixed STM+Sum+LTM achieves 84.7% accuracy with 591 tokens. Hybrid heuristic only 70.7% -- 16-point gap to oracle. Feature ablation: Linguistic alone 57% coverage, +Semantic signals 90% (+33%), +Embedding similarity 94% (+4%).

**Trade-offs:** Routing adds <1ms (rule-based) to ~5ms (embedding). Hybrid heuristic achieves 94% coverage but only 70% QA accuracy (routing errors 12%, extraction errors 18%). Uniform retrieval can degrade performance due to conflicting information across stores. Long context amplifies penalty of over-retrieval.

**Design Rationale:** Two-stage evaluation decouples routing quality from retrieval/generation quality. Decision-theoretic formulation makes accuracy-cost tradeoff explicit. Hybrid design leverages cheap pattern matching with embedding fallback.

**Transferable Idea for Lyra:** Lyra should implement store-level routing as a cost-sensitive decision. Given Lyra's multiple memory tiers (working/episodic/semantic/summary), selective store retrieval could reduce tokens by 62% while improving accuracy. The routing policy (rule-based + embedding) is simple to implement and adds <5ms overhead.

**Gap vs Baseline:** Significant gap. Lyra currently retrieves from all stores uniformly (or via simple keyword match). Implementing cost-sensitive routing is a high-impact, low-effort improvement.

---

## 4. Self-EvoWM: Self-Evolving Task Discovery and Consistency Repair in DROID-Grounded Generative World Models
**URL:** https://openreview.net/pdf?id=lVn5vLOkjP
**Authors:** Anonymous (under review ICLR 2026)

**Core Mechanism (step-by-step):** Generate-verify-repair loop for controllable world models (built on Ctrl-World). Loop: (1) goal proposal via LLM from memory, (2) DROID anchor retrieval as simulation-ready initial states, (3) Ctrl-World rollout, (4) VLM critic audit for success and physical consistency, (5) repair path: localize failure -> construct targeted simulation environment -> generate supplemental data -> refresh world model. Algorithm uses anchor retrieval, VLM-based success/consistency scoring, failure localization, targeted simulation construction, and world model refresh. Retrieval diversity via clustering in embedding space.

**Results (real numbers):** Workshop paper -- preliminary findings only. Key observations: retrieval can overfit loop (near-duplicate anchors inflate early success), contacts are where realism breaks first, VLM judgments are sensitive to phrasing/viewpoint changes. No benchmark scores reported.

**Trade-offs:** Anchoring reduces drift but limits diversity. VLM critic is useful but unstable. Repair loops introduce new tuning knobs (frequency, buffer size, overfitting risk). Correct but incomplete localization leads to non-representative repair environments.

**Design Rationale:** Simulation-chain view -- treat world model learning as end-to-end pipeline with explicit interfaces. Filtering alone is insufficient; active repair strengthens weak regions. Anchoring keeps distributions close to real data.

**Transferable Idea for Lyra:** The generate-verify-repair loop architecture is transferable. Specifically: (1) anchor retrieval to ground generation in real data, (2) VLM-based consistency auditing with targeted failure localization, (3) automated repair via focused simulation construction. The retrieve-collapse diagnosis (near-duplicate anchors) is relevant for Lyra's retrieval diversity.

**Gap vs Baseline:** Indirect relevance. Lyra is an agent framework not a world model, but the generate-verify-repair loop and anchor-based retrieval are architectural patterns applicable to Lyra's skill learning and memory consolidation.

---

## 5. Norm-Guided KV-Cache Eviction for Memory-Efficient Reasoning
**URL:** https://openreview.net/pdf?id=xOW2jXDKG3
**Authors:** Prasanth Yadla (Independent)

**Core Mechanism (step-by-step):** Proposes ell2-Norm Eviction for KV-cache compression. Importance score I_t = (1/H) * sum_{h=1..H} ||K^h_t||_2 (mean ell2-norm of key vectors across attention heads). Budget B split into Recent Pool k_r = 0.2B (most recent tokens) and Heavy-Hitter Pool k_h = 0.8B (top-k_h by importance). Eviction rule: R = {T - k_r + 1 .. T}, H = argmax_{S subset C\R, |S|=k_h} sum_{t in S} I_t. Retained set = H union R. Complexity: O(T * H * d_h) for score computation, O(T log k_h) for top-k selection. <2% per-step latency overhead.

**Results (real numbers):** Mistral-7B-Instruct-v0.3 on GSM8K (40 problems) and Logic (20 prompts). At budgets 512-2048: all methods match full-cache baseline (sequence lengths never exceed 512 tokens, eviction never fires). At budget 256 (87.5% reduction): Sliding Window GSM8K EM=0.25, ell2-Norm EM=0.05 (drop of -0.55 from full-cache 0.60). Logic: both drop to 0.65 (from 0.75). Latency at budget 256: 14.23s vs 6.58s at larger budgets (2x overhead). Peak VRAM constant across budgets (14.56 GB -- model weights dominate).

**Trade-offs:** ell2-Norm underperforms sliding window at extreme budgets (256 tokens) on GSM8K. Recency dominates global token importance for chain-of-thought continuation at tight budgets. Requires minimum budget B >= 512 for advantage. 20:80 recency-HH split is fixed and may be suboptimal at different budgets.

**Design Rationale:** Gradient-free, single-pass importance score -- simpler than H2O's cumulative attention tracking. Built on heavy-hitter hypothesis but discovers its limitations at extreme budgets ("minimum viable budget effect").

**Transferable Idea for Lyra:** The concept of token-level importance scoring for selective retention is not directly applicable (Lyra works at higher abstraction), but the finding that "recency dominates at tight budgets" has implications for Lyra's context window management. The structured eviction policy (recent pool + importance pool) mirrors Lyra's working/episodic memory split.

**Gap vs Baseline:** Low direct applicability. KV-cache compression operates at attention mechanism level, far below Lyra's memory abstraction layer.

---

## 6. R-KVHash: KV Cache Compression of Reasoning Traces via SimHash-Based Estimation of Redundant Tokens
**URL:** https://openreview.net/attachment?id=UTRuEFJ57H&name=pdf
**Authors:** Anonymous (under review ICLR 2026)

**Core Mechanism (step-by-step):** Replaces R-KV's pairwise cosine-similarity redundancy computation with Locality-Sensitive Hashing (SimHash). Projects key vectors K_h in R^{n x d} to b-bit binary hash codes via Gaussian projection matrix R in R^{d x b}: K'_h = K_h R, threshold at zero. For x,y in R^d: (1/b)*E[Hamming(H(x), H(y))] = arccos(theta). Redundancy score for bucket i: S'_i = sum_{i!=j} c_j cos(Hamming(i,j)/b) / sum_j c_j. Bucket size b=16 best. Avoids both O(n^2 d) Gram matrix computation and attention-based importance tracking. Reduces from O(n^2) to O(n) complexity.

**Results (real numbers):** DeepSeek-R1-Distill-Qwen-7B and 14B on MATH-500 and GSM8K. Budget 1,024 tokens. R1-Distill-Qwen-7B MATH-500: Full 0.63, R-KV 0.23, R-KVHash 0.41. GSM8K: Full 0.50, R-KV 0.43, R-KVHash 0.45. R1-Distill-Qwen-14B MATH-500: Full 0.64, R-KV 0.22, R-KVHash 0.40. GSM8K: Full 0.82, R-KV 0.57, R-KVHash 0.75. Decoding throughput: R-KVHash nearly 2x R-KV, matching uncompressed on Llama-8B. Memory savings: R-KVHash more efficient as budget grows (uses binary hash tables vs FP64 similarity matrices).

**Trade-offs:** Bucket size b controls granularity: larger b risks overly random evictions, smaller b may discard important tokens. Single random Gaussian matrix (fixed seed) works across experiments -- no per-run sampling needed. LSH-based approximation loses exact cosine similarity fidelity but gains dramatically in efficiency.

**Design Rationale:** Redundancy estimation is the bottleneck in R-KV for long reasoning traces. SimHash provides sub-linear alternative that happens to be a better eviction strategy (not just faster). The key insight: grouping tokens by low-dimensional hash codes functions as superior bucketing of irrelevant tokens compared to exact cosine similarity + attention.

**Transferable Idea for Lyra:** SimHash-based similarity estimation for deduplication of memory items. Lyra could hash new memory items and compare against stored items to detect near-duplicates before storage, reducing redundancy without pairwise embedding comparisons. Particularly useful for long reasoning traces where repeated thoughts waste storage.

**Gap vs Baseline:** Medium applicability. Lyra does not currently do LSH-based deduplication. Adding SimHash as a fast approximate similarity check before inserting into MemoryStore would reduce storage bloat.

---

## 7. From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms
**URL:** https://openreview.net/attachment?id=l9Ly41xxPb&name=pdf
**Authors:** Anonymous (under review ICLR 2026)

**Core Mechanism (step-by-step):** Proposes three-stage evolutionary framework for LLM agent memory: (1) Storage -- raw trajectory preservation (linear, vector, structured), (2) Reflection -- semantic transformation F_ref: T -> S, refining trajectories via introspection/environment/coordination, (3) Experience -- cross-trajectory abstraction via Minimum Description Length principle, extracting generalizable schema K = F_exp(T_batch) s.t. |K| << sum|tau|. Formalizes agent action: a_t ~ pi_theta(a_t | I, o_t, m_t) where m_t = Retrieve(M, o_t). Defines trajectory tau = <(o_1,a_1),...,(o_T,a_T)> and raw storage M_raw = {tau_i}. Experience is further split into explicit (human-readable policies), implicit (fine-tuned into weights), and hybrid (dynamic cycle).

**Results (real numbers):** Survey paper -- no new experiments. Comprehensive taxonomy of ~100+ papers across the three stages.

**Trade-offs:** Each stage trades off fidelity vs abstraction. Storage preserves everything but scales poorly. Reflection improves quality but fragments memory. Experience compresses to generalizable patterns but may lose task-specific nuances.

**Design Rationale:** Unifies fragmented research under a single evolutionary lens. The three drivers: long-range consistency, dynamic environment adaptation, continual learning. Addresses why/how/what of memory evolution.

**Transferable Idea for Lyra:** The three-stage framework provides a roadmap for Lyra's memory evolution: Lyra is currently at Storage (trajectory preservation) with some Reflection (experience summarization). The Experience stage (cross-trajectory abstraction) is the next frontier. The MDL principle for compression is directly applicable to Lyra's memory consolidation. The explicit/implicit/hybrid experience categorization helps frame Lyra's design choices.

**Gap vs Baseline:** Provides the conceptual framework Lyra needs for its memory evolution roadmap. Lyra's MemoryStore/ExperienceStore maps to Storage/Reflection. The Experience tier is largely missing.

---

## 8. Experiential Reflective Learning for Self-Improving LLM Agents (ERL)
**URL:** https://openreview.net/forum?id=hQgSl6kj1W
**Authors:** Marc-Antoine Allard, Arnaud Teinturier, Victor Xing, Gautier Viaud (Illuin Technology)

**Core Mechanism (step-by-step):** Two-component framework: (1) Heuristic generation: agent reflects on task trajectories + outcome to generate structured heuristic containing analysis (what led to success/failure) + learned guideline (trigger conditions + recommended actions). (2) Retrieval-augmented execution: LLM scores stored heuristics for relevance based on task description similarity, experience diversity, and guideline informativeness. Top-k=20 heuristics injected into system prompt. Heuristics extracted from single-attempt trajectories (no repeated rollouts needed).

**Results (real numbers):** Gaia2 benchmark (Search + Execution splits). GPT-5-mini backbone. ERL 56.1% overall success rate vs ReAct baseline 48.3% (+7.8%), vs ExpeL 50.9%, vs AutoGuide 50.8%, vs few-shot trajectory prompting 46.4%. Execution: ERL 51.4% vs baseline 43.1% (+8.3%). Search: ERL 60.7% vs baseline 53.6% (+7.1%). Pass^3 (reliable completion): ERL gains +8.3% (Execution) and +10.6% (Search). LLM-based retrieval (56.1%) outperforms embedding retrieval (53.3%) and random selection (best random at ~40-60 heuristics: 53.8%). Failure-only heuristics perform best overall (58.9%) but favor Search; success-only best for Execution (52.1%). No retrieval (random heuristics) degrades to 53.8%.

**Trade-offs:** Heuristic pool grows unbounded without pruning mechanism. LLM-based retrieval at every call introduces latency. Single-attempt heuristics may be noisier than contrastively derived ones. Failure vs success heuristics show task-type-dependent performance.

**Design Rationale:** Designed for practical deployment where tasks cannot be retried (single-attempt trajectories). Contrasts with ExpeL (requires repeated rollouts) and AutoGuide (expensive per-turn retrieval). Heuristics preserve granular details lost in cross-task aggregation.

**Transferable Idea for Lyra:** ERL's single-attempt heuristic generation is directly applicable to Lyra's experience summarization. The LLM-based retrieval (scoring heuristics for relevance) could replace or augment Lyra's current keyword/embedding retrieval for experience store. The finding that failure heuristics outperform success heuristics for Search (negative constraints prune ineffective strategies) is actionable for Lyra's Experience tier.

**Gap vs Baseline:** Relevant gap. Lyra's ExperienceStore stores summaries but does not use LLM-based relevance scoring for retrieval. ERL's heuristic generation (analysis + guideline with trigger conditions) is more structured than Lyra's current free-text experience summaries.

---

## 9. LP-RAG: Link Prediction-Based Framework for Retrieval-Augmented Generation
**URL:** https://openreview.net/pdf?id=Y8Txo8vaH7
**Authors:** Erik Jhones Nascimento et al. (Federal University of Ceara, University of Sao Paulo)

**Core Mechanism (step-by-step):** Formulates retrieval as inductive link prediction. Pipeline: (1) LLM-prompted chunker extracts atomic chunks from documents. (2) Synthetic queries generated per chunk-batch: S_B ~ LLM(S-PROMPT || B; n_B=2). (3) Graph construction: nodes = chunks U synthetic queries, chunk-chunk edges via mutual k-NN (k=5) on Contriever embeddings, query-chunk edges from batch association. Edge weights: sim(z_u,z_v) for chunk-chunk, 1.0 for query-chunk. (4) Train GNN (NCN) for link prediction: phi_theta: V x V -> R, BCE loss with negative sampling. (5) Inference: add query as unseen node, score edges to all chunks, select top candidates.

**Results (real numbers):** Retrieval (R@2/R@5): HotpotQA 77.9/89.6, MuSiQue 53.6/61.8, 2Wiki 89.9/93.2. Beats GFM-RAG on MuSiQue (+4.5% R@2, +3.6% R@5). QA (EM/F1): HotpotQA 53.2/69.1, MuSiQue 32.6/43.9, 2Wiki 72.6/78.3. Arena benchmarks (W+T): Science 0.920, Recreation 0.907, Tech 0.948. Controlled eval: Acc 89-91% across 5 datasets, 2.2-3.8K tokens retrieved. Ablation: NCN best GNN arch. Without synthetic queries, NCN* drops to 69.15% on HotpotQA-S (vs 89.32% with queries). Cross-domain transfer (trained on MuSiQue, eval on HotpotQA): LP-RAG R@2=65.4, R@5=78.3 -- second only to GFM-RAG (pretrained on 60 KGs).

**Trade-offs:** Indexing time 152-183 min on Arena datasets (vs NodeRAG 10-17 min) due to GNN training. Storage 143-175 MB (vs NodeRAG 80-157 MB). Query time comparable (6-9s). K-NN chunk graph with mutual k=5. NCN with specific per-dataset hyperparameters (LR 0.0043, 1-3 layers, epochs 50-1000). Atomic chunks too small for similarity-based methods (NaiveRAG accuracy drops below 20%).

**Design Rationale:** Synthetic queries bridge the gap between document structure and user intent. GNN-based link prediction can leverage graph structure beyond embedding similarity. Inductive setting enables handling unseen queries without retraining.

**Transferable Idea for Lyra:** The synthetic query generation to learn chunk-query associations is directly applicable to Lyra's memory index. Lyra currently indexes memories with embeddings; adding synthetic query supervision could improve retrieval relevance. The GNN-based ranking over memory item graphs could replace simple cosine similarity, especially for multi-hop reasoning tasks.

**Gap vs Baseline:** Significant gap. Lyra uses embedding similarity (flat search) not learned retrieval. LP-RAG demonstrates 20-30% accuracy improvements via link prediction over similarity search. Implementation requires GNN training infrastructure but the gains are substantial.

---

## 10. SABER: Small Actions, Big Errors -- Safeguarding Mutating Steps in LLM Agents
**URL:** https://openreview.net/attachment?id=En2z9dckgP&name=pdf
**Authors:** Alejandro Cuadron, Pengfei Yu, Yang Liu, Arpit Gupta (Amazon AGI Foundations)

**Core Mechanism (step-by-step):** Three-component safeguard: (1) Mutation-gated human verification -- only mutating actions (environment-changing: cancellations, refunds, file deletions) trigger user confirmation. Non-mutating actions (information-gathering) proceed autonomously. (2) Targeted reflection -- injects distilled constraint summary before mutating steps to counter "lost-in-the-middle" drift. (3) Block-based context cleaning -- partitions trajectory into blocks, summarizes, retrieves most relevant blocks by embedding similarity. Auxiliary model performs verification/reflection/context management separate from main agent.

**Results (real numbers):** tau-Bench and SWE-Bench Verified. Qwen3-Thinking-235B: Airline 49.3%->63.3% (+14pp), Retail 64.3%->71.6% (+7.3pp). tau-Bench Verified Air: 58.5%->78.2% (+19.7pp), Verified Retail: 66.9%->77.7% (+10.8pp). GPT-5 (med): Airline 45.3%->62.6% (+17.3pp), Retail 77.1%->76.5% (-0.6pp). Claude Sonnet 4: Airline 51.3%->56.0% (+4.7pp), Retail 73.3%->78.3% (+5.0pp). SWE-Bench Verified: Qwen3 42.6%->45.1% (+2.5pp -- only reflection applicable). Ablation: Reflection alone 68.0%, Verification alone 68.7%, Full SABER 78.7% on tau-Bench Verified Airline -- synergy. Mutating actions: only 14-18% of total steps but single mutating deviation reduces success odds by 57-96%.

**Trade-offs:** Auxiliary model adds latency. Relies on user/user simulator for confirmation. Some tasks (SWE-Bench) cannot support human verification. Block-based filtering requires embedding cache and summary storage. Ceiling effects: tau-Bench Verified needed to reveal genuine headroom.

**Design Rationale:** Formalizes "decisive deviation" concept -- earliest action-level divergence flipping success to failure. Logistic regression validates mutating-dominates hypothesis. The 14-18% vs 57-96% asymmetry motivates targeted intervention. Released tau-Bench Verified to address benchmark artifacts.

**Transferable Idea for Lyra:** The mutation-gated verification pattern is directly applicable to Lyra's permission system. Lyra should classify agent actions as mutating (state-changing tool calls) vs non-mutating (read-only queries) and apply differential scrutiny. The block-based context cleaning (partition, summarize, retrieve relevant blocks) is relevant for Lyra's working memory management in long-horizon tasks.

**Gap vs Baseline:** Relevant gap. Lyra does not distinguish mutating from non-mutating actions in its memory/safety systems. SABER's decisive deviation analysis provides theoretical grounding for selective intervention.

---

## 11. AOI: Multi-Agent Collaborative Framework for Intelligent IT Operations
**URL:** https://openreview.net/attachment?id=Q16XXJou3O&name=pdf
**Authors:** Yixin Wang et al. (Hefei University of Technology, Columbia, UC Davis)

**Core Mechanism (step-by-step):** Three-agent architecture: Observer (coordination/decomposition), Probe (read-only diagnosis), Executor (controlled remediation under checkpoint-rollback). LLM-based Context Compressor with sliding window mechanism: W_i = [start_i, start_i + w_size], start_i = i * (w_size * 0.5 overlap). Three-layer memory: Layer 1 (raw context, 24h retention), Layer 2 (task queue), Layer 3 (compressed context cache, 7-day retention). Dynamic scheduling: argmax_{a in {probe, execute}} E[Reward(a, x(t), C(t))]. Formalized as Dec-POMDP.

**Results (real numbers):** AIOpsLab + Loghub benchmarks. TSR 94.2% vs B-MAS 86.4% (+9.0%), vs SA-LLM 81.5%, vs TAP 75.1%, vs RES 67.8%. MTTR 22.1 min vs B-MAS 33.7 min (-34.4%). CCR 72.4% with IPS 92.8% (vs TAP 35.7%/81.4%). FPR 3.1% (lowest). SSS 96.7%. Ablation: w/o compressor: TSR drops to 88.5% (-5.7pp), MTTR +7.7 min. w/o dynamic scheduling: MTTR +4.6 min (+20.8%). w/o hierarchical memory: TSR drops to 89.4%. Optimal window size: 768 tokens. Best scheduling balance: lambda=0.35.

**Trade-offs:** Compression window size has diminishing returns beyond 768 tokens. Episodic memory retention best at 72 hours (3.5% improvement over 24h; minimal gain beyond). Latency from LLM-based compression (2.3s per window). Checkpoint-rollback overhead for Executor actions. GPT-4 API latency spikes under extreme load.

**Design Rationale:** Role separation for safety (read-only Probe vs write-capable Executor). Domain-aware compression (not generic summarization) preserves operationally critical information. Uncertainty-aware scheduling balances exploration vs exploitation.

**Transferable Idea for Lyra:** The three-agent pattern (Observer/Probe/Executor) maps to Lyra's planner/tool-use pattern. The sliding-window context compressor with information preservation guarantees is directly applicable for Lyra's context management. The three-layer memory (raw/working/compressed) with explicit retention policies is a well-engineered version of what Lyra needs.

**Gap vs Baseline:** Medium gap. Lyra's memory architecture is simpler (no explicit three-layer, no compression guarantees). The compressor with provable information bounds and the hierarchical memory with retention policies are directly applicable enhancements.

---

## 12. MemGrad: Memory-Guided Optimization of Agentic Software Development via Abstracted Textual Gradients
**URL:** https://openreview.net/attachment?id=GeaPE7iw1V&name=pdf
**Authors:** Anish Natekar et al. (TCS Research)

**Core Mechanism (step-by-step):** Transforms batched behavioral feedback into textual gradients that update dual memory (retrospective + prospective). Pipeline: (1) Beta-tester generates trajectory, (2) TextGrad loss L(q) = tg.TextLoss(tau(q); E), (3) TextGradDecomposer extracts feedback-resolution pairs {F, dL/dF}, (4) Role-based gradient routing via embedding similarity: assignRole(F) = argmax_{r in R} cos(phi(F), phi(r)), (5) RoleBasedAbstractor compresses clusters into abstracted feedback-resolution pairs, (6) Backward engine computes prompt-level gradient dL/dp_r, (7) TGD.step updates role-specific system prompt. Dual memory: M_ret,r stores failure patterns, M_pro,r stores feedback-resolution pairs. Inference: Retrieve(M_ret,r, a) -> F_r(a), then Retrieve(M_pro,r, F_r(a)) -> R_r(a). System prompt augmented with both.

**Results (real numbers):** AgileCoder on 30 CLI games (10 train, 20 test). Unit test pass rate: MemGrad 48.3% vs AgileCoder 15.3%, TextGrad 24.1%, MemGrad w/o memory 35.4%. Human evaluation (requirements satisfied): MemGrad 65.5% vs 58.0%/56.0%/63.5%. Token cost: MemGrad 2.92M vs TextGrad 2.29M tokens (total cost <$1 for 3 epochs). TextGrad prompts exhibit redundant instructions (e.g., repeated "proper invalid input handling"). MemGrad prompts are more concise and structured.

**Trade-offs:** Minimal token overhead (~0.08 USD) for significant performance gains. Role-based clustering helps less-frequent agents (Software Test Engineer, Code Reviewer) get meaningful updates. Prompt-level gradients can cause prompt bloat if not abstracted. Requires access to execution feedback for loss computation.

**Design Rationale:** Textual gradients provide interpretable optimization direction. Retrospective-prospective split separates "what went wrong" from "what to do next" -- mirrors classical psychology distinction. Role-based routing ensures specialized updates. Abstraction prevents gradient explosion and prompt bloat.

**Transferable Idea for Lyra:** The retrospective-prospective memory split is directly applicable to Lyra's experience store. The textual gradient framework for converting execution feedback into persistent memory updates is a natural extension of Lyra's reflection mechanism. Role-based routing has implications for multi-agent Lyra configurations.

**Gap vs Baseline:** Significant gap. Lyra does not use textual gradients or structured feedback aggregation. MemGrad's abstraction pipeline (decompose -> route -> abstract -> apply) is a sophisticated learning mechanism that Lyra could adopt for its reflection and consolidation tiers.

---

## 13. ReMemR1: Look Back to Reason Forward -- Revisitable Memory for Long-Context LLM Agents
**URL:** https://openreview.net/pdf?id=1cymflI2Lh
**Authors:** Yaorui Shi et al. (USTC, NUS, Shanghai Jiao Tong, DP Technology, Meituan)

**Core Mechanism (step-by-step):** Addresses "memorize while reading" paradigm limitations (premature pruning of latent evidence, progressive information loss from overwriting, sparse/delayed supervision). Augments state from s_t = m_t to s_t = (m_t, q_t) where q_t is a callback query enabling retrieval over entire memory history. At each step, agent updates m_t based on new chunk c_t AND generates callback query q_{t+1} to revisit past memories {m_i}_{i <= t}. Multi-level reward design: final-answer reward + dense step-level signals that guide effective memory use. Enables non-linear reasoning paths over long documents.

**Results (real numbers):** Significantly outperforms SOTA baselines on long-context QA with negligible computational overhead. Specific numbers in the paper (not fully extracted) demonstrate benefits over full-text retrieval and "memorize while reading" paradigms. Code at https://github.com/syr-cn/ReMemR1.

**Trade-offs:** Callback mechanism adds per-step overhead vs vanilla linear memory. Multi-level reward design requires careful tuning. The "memorize while reading" paradigm with callbacks is more complex than either full-text retrieval or simple linear scanning.

**Design Rationale:** Identifies three specific failure modes of linear memory overwriting. The callback query mechanism is a minimal extension that enables non-linear reasoning without full-text retrieval complexity. Multi-level rewards address sparse supervision problem.

**Transferable Idea for Lyra:** The callback mechanism -- enabling memory to revisit past entries based on generated queries -- is applicable to Lyra's working/episodic memory tier. Instead of overwriting working memory, Lyra could maintain a callback index that allows the agent to selectively revisit earlier memories.

**Gap vs Baseline:** Medium gap. Lyra does not currently use callback queries or multi-level reward for memory management. The concept of "revisitable memory" could enhance Lyra's working memory tier.

---

## 14. Bias Amplification in Language Model Evolution: An Iterated Learning Perspective
**URL:** https://openreview.net/pdf?id=BSYn7ah4KX
**Authors:** Yi Ren et al. (UBC, University of Edinburgh, MIT)

**Core Mechanism (step-by-step):** Applies Bayesian Iterated Learning (IL) framework to LLM self-improvement. Models iterative self-data-augmentation as a chain of Bayesian agents where each generation learns from the previous generation's outputs. Shows theoretically that agents engaged in such a process gradually amplify bias in their priors. The amplification can be steered by introducing interaction phases that "filter" or "re-rank" generated messages. Establishes that LLM in-context behavior can be approximated by Bayesian update.

**Results (real numbers):** Experimental verification with various LLMs supporting theoretical predictions. Specific numbers in the paper.

**Trade-offs:** Theoretical framework relies on assumptions about Bayesian behavior. Not all iterative methods may follow the predicted patterns.

**Design Rationale:** Draws parallels between LLM evolution and human cultural evolution studied for decades in cognitive science. Provides mechanism for understanding bias amplification in self-improving systems.

**Transferable Idea for Lyra:** The bias amplification framework applies to Lyra's self-improving loops. Lyra's memory consolidation could accumulate biases (e.g., over-weighting recent experiences). Understanding this can inform Lyra's memory update policies to prevent runaway bias.

**Gap vs Baseline:** Theoretical framework. Not directly actionable as an algorithm, but provides important perspective on risks of iterative self-improvement without diversity injection.

---

## 15. ACE: Agentic Context Engineering -- Evolving Contexts for Self-Improving Language Models
**URL:** https://openreview.net/pdf?id=eC4ygDs02R
**Authors:** Qizheng Zhang et al. (Stanford, SambaNova Systems, UC Berkeley)

**Core Mechanism (step-by-step):** Treats contexts as evolving playbooks that accumulate, refine, and organize strategies through generation, reflection, and curation. Prevents "context collapse" (iterative rewriting eroding details) with structured, incremental updates. Modular process: generate strategies from experience, reflect on outcomes, curate for relevance. Works for both offline (system prompts) and online (agent memory) contexts.

**Results (real numbers):** AppWorld agents: ACE 59.5% vs ICL 46.0%, GEPA 46.4%, DC 51.9%. FiNER (domain knowledge): ACE 78.3% vs GEPA 73.5%, DC 74.2%. Formula (numerical reasoning): ACE 76.5% vs GEPA 71.5%, DC 69.5%. +10.6% on agents, +8.6% on finance vs baselines. On AppWorld leaderboard, ACE matches top-ranked production agent and surpasses on harder test-challenge split, using smaller open-source model. Also matches full-dataset performance with ~30% of training tasks via curriculum curation.

**Trade-offs:** Requires careful generation-reflection-curation cycle design. Context collapse prevention adds complexity. Curriculum curation introduces ordering sensitivity.

**Design Rationale:** Context adaptation avoids weight updates while providing interpretable improvements. Playbook metaphor provides intuitive mental model for accumulated context. Modular approach prevents collapse that naive iterative rewriting suffers.

**Transferable Idea for Lyra:** ACE's "evolving playbooks" concept maps directly to Lyra's context management. The generation-reflection-curation cycle is applicable to Lyra's experience tier. The finding that careful data selection (30% of tasks can match full dataset) is relevant for Lyra's limited-memory scenarios.

**Gap vs Baseline:** Medium gap. Lyra does not currently use structured playbook evolution. ACE's curriculum curation is relevant for Lyra's experience store maintenance.

---

## 16. ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory
**URL:** https://openreview.net/pdf?id=jL7fwchScm
**Authors:** Siru Ouyang et al. (UIUC, Google Cloud AI Research, Yale)

**Core Mechanism (step-by-step):** Distills generalizable reasoning strategies from agent's self-judged successful and failed experiences. Retrieves relevant memories at test time to inform interaction, then integrates new learnings. Memory-Aware Test-Time Scaling (MATTS): scales up interaction experience by allocating more compute per task, generating abundant diverse experiences for richer contrastive signals. Memory bank stores reasoning strategies (not raw trajectories or successful routines only). Synergy between memory and test-time scaling: better memory guides more effective scaling.

**Results (real numbers):** Consistently outperforms existing memory mechanisms (raw trajectory storage, success-only routines) on web browsing and software engineering benchmarks. Improves both effectiveness and efficiency. MATTS further amplifies gains. Code at https://github.com/google-research/reasoning-bank.

**Trade-offs:** MATTS increases compute per task for richer experience generation. Requires effective self-judgment mechanism for distinguishing successful from failed experiences.

**Design Rationale:** Agents should learn from both success and failure, not just store raw trajectories. Test-time scaling and memory form a virtuous cycle: more compute -> richer experience -> better memory -> more effective scaling.

**Transferable Idea for Lyra:** ReasoningBank's contrastive memory (learning from both successes and failures) is directly applicable to Lyra's Experience tier. MATTS's compute-scaling framework could inform Lyra's budget allocation for experience generation. The synergy between memory and test-time scaling is a new scaling dimension Lyra should consider.

**Gap vs Baseline:** Significant gap. Lyra does not currently implement contrastive memory distillation or compute-aware test-time scaling. ReasoningBank provides concrete architecture for both.

---

## 17. CaTS: Calibrated Test-Time Scaling for Efficient LLM Reasoning
**URL:** https://openreview.net/pdf?id=jrSc4RJXy1
**Authors:** Chengsong Huang et al. (Washington University in St. Louis, CMU, UW)

**Core Mechanism (step-by-step):** Self-Calibration: distills Self-Consistency-derived confidence into the model itself via one forward pass. Uses pseudo training tuples (query, answer, confidence). CaTS (Calibrated Test-Time Scaling) applies confidence-based dynamic sampling: early stopping for Best-of-N, adaptive N for Self-Consistency. Provably better than vanilla Self-Consistency.

**Results (real numbers):** MathQA: CaTS-ES improves Best-of-N accuracy from 73.7 to 83.6 with budget of 16 responses. Saves 39.8-94.2% samples compared to vanilla Self-Consistency at matched accuracy. Three LLMs across nine datasets.

**Trade-offs:** Requires training for self-calibration (distillation step). Confidence estimation may not transfer across domains.

**Design Rationale:** Confidence as intrinsic uncertainty measure. LLMs are overconfident, so Self-Calibration corrects via distillation. Adaptive sampling avoids wasting compute on simple queries while allocating more to hard ones.

**Transferable Idea for Lyra:** CaTS's confidence-based dynamic budget allocation is relevant for Lyra's compute management. Lyra could use confidence estimates to decide how much budget to allocate per query, saving on easy tasks, spending more on hard ones.

**Gap vs Baseline:** Low direct applicability to memory. Primarily about inference compute management, but the adaptive budget concept extends to memory retrieval budget allocation.

---

## 18. Scaling Large Language Model-Based Multi-Agent Collaboration (MACNET)
**URL:** https://openreview.net/pdf?id=K3n5jPkrU6
**Authors:** Chen Qian et al. (Tsinghua University)

**Core Mechanism (step-by-step):** Organizes agents into Directed Acyclic Graph (DAG)-structured collaboration network. Each edge managed by supervisory critic (issues commands), each node by compliant actor (provides artifacts). Agents interact in topological order; only refined artifact propagates (not full dialogue) preventing context explosion. Six topology variants (chain, tree, graph).

**Results (real numbers):** Supports effective collaboration among 1000+ agents. Collaborative scaling law: logistic growth pattern as agents scale. Collaborative emergence occurs earlier than neural emergence. Irregular topologies outperform regular ones.

**Trade-offs:** DAG construction and management complexity. Artifact-only propagation may lose intermediate reasoning context. Critics add overhead per edge.

**Design Rationale:** Neural scaling law inspired -- increasing agents improves performance, but with diminishing returns (logistic). Only refined artifact propagation prevents context explosion that would limit scalability.

**Transferable Idea for Lyra:** MACNET's DAG-based agent collaboration and artifact-only propagation are relevant for Lyra's multi-agent scenarios (if Lyra expands to multi-agent). The collaborative scaling law informs agent count decisions.

**Gap vs Baseline:** Low direct applicability. Lyra is single-agent focused. However, the DAG-based collaboration pattern could inform future multi-agent extensions.

---

## 19. LAR: Latent Action Reparameterization for Efficient Agent Inference
**URL:** https://openreview.net/pdf?id=nmFfyHEs76
**Authors:** Qingwen Zeng et al. (Sydney, Montreal, Chicago, Fudan, Yale, DeepWisdom, Amazon, Stanford)

**Core Mechanism (step-by-step):** Learns a compact latent action space where each latent action corresponds to a multi-step semantic behavior. Compresses low-entropy, structurally recurring patterns (system prompts, tool invocation syntax, recurring configurations) into latent units while preserving high-entropy parameter-rich inputs (specific queries, entities) in explicit output. Treats action representation as first-class modeling choice.

**Results (real numbers):** Significant reductions in action tokens and wall-clock inference time. Maintains or improves task success rates across diverse LLM agent benchmarks. Specific numbers per benchmark in the paper.

**Trade-offs:** Requires learning latent actions from trajectories. Balancing abstraction vs executability is key design challenge. Not all actions benefit equally from abstraction.

**Design Rationale:** Inference efficiency bottleneck is not per-token generation speed but number of decision steps. Latent abstractions shorten effective horizon. Executability constraint ensures compatibility with external tools.

**Transferable Idea for Lyra:** LAR's action compression is complementary to Lyra's memory. If Lyra agents execute repeated patterns (tool calls, query formats), LAR could compress them into latent actions, reducing token usage and effective horizon. The entropy-based selection (what to compress vs preserve) is directly applicable.

**Gap vs Baseline:** Low-medium direct applicability. Complementary to memory -- action representation optimization is orthogonal to memory system design.

---

## 20. Learning What to Learn: Curriculum Curation for Test-Time Agent Learning
**URL:** https://openreview.net/pdf?id=Qr5bhBbBOb
**Authors:** Anonymous (under review ICLR 2026)

**Core Mechanism (step-by-step):** Studies task selection and ordering for context-based test-time adaptation. Uses ACE framework for implementation. Hypothesis: redundant/overly simple examples offer diminishing returns. Experiments with data selection and ordering on AppWorld benchmark.

**Results (real numbers):** Achieves comparable performance using ~30% of full training set through strategic example selection. Task ordering measurably affects learning outcomes. Harder examples may provide richer learning signal. Specific numbers in the paper.

**Trade-offs:** Curriculum curation adds overhead for determining optimal selection and ordering. Platform-dependent findings may not transfer across benchmarks.

**Design Rationale:** Traditional ML curriculum design principles apply to test-time agent learning. Not all examples are equally valuable -- selection and ordering can dramatically improve sample efficiency.

**Transferable Idea for Lyra:** Curriculum curation for Lyra's experience store maintenance. Instead of storing all experiences equally, Lyra could select diverse/hard examples preferentially. Task ordering during consolidation could improve learning efficiency.

**Gap vs Baseline:** Medium gap. Lyra does not currently apply curriculum-based selection to its experience store. The finding that 30% of tasks can match full-dataset performance is directly actionable.

---

## 21. Human-Like Lifelong Memory: A Neuroscience-Grounded Architecture for Infinite Interaction
**URL:** https://openreview.net/pdf?id=QufkvHbQs7
**Authors:** Diego C. Lerma-Torres (Universidad de Guanajuato)

**Core Mechanism (step-by-step):** Bio-inspired framework grounded in Complementary Learning Systems theory, CBT belief hierarchy, dual-process cognition, and fuzzy-trace theory. Three principles: (1) Memory has valence (pre-computed emotional-associative summaries in emergent belief hierarchy), (2) Retrieval defaults to System 1 with System 2 escalation (spreading activation + passive priming, deliberate retrieval only when needed, graded epistemic states), (3) Encoding is active, present, feedback-dependent (thalamic gateway tags/routes information, executive forms "gists" through curiosity-driven investigation). Dual-store: Working Memory + Knowledge Graph. Seven functional properties specified. Over time, system converges toward System 1 processing.

**Results (real numbers):** Architectural proposal -- no experimental results. Context expansion alone degrades performance up to 85% (citing Du et al., 2025). Processing 1M input tokens costs $0.30-$5.00 (Q1 2026).

**Trade-offs:** Full neuroscience grounding may be over-engineered for practical systems. Valence computation adds overhead. System 1/2 routing introduces complexity.

**Design Rationale:** Neuroscience principles provide the most complete model of memory. Context windows alone cannot produce memory -- need structured, multi-component architecture.

**Transferable Idea for Lyra:** The System 1/2 retrieval routing (fast automatic vs slow deliberate) maps to Lyra's working/episodic memory split. The valence vector concept (emotional-associative pre-computation) could enhance Lyra's relevance scoring. The thalamic gating mechanism (active encoding with feedback) informs Lyra's memory admission policy.

**Gap vs Baseline:** Conceptual gap. Lyra doesn't use neuroscience-grounded principles. However, the System 1/2 routing and active encoding concepts are practically applicable.

---

## 22. CoMEM: Context Management with a Decoupled Long-Context Model
**URL:** https://openreview.net/pdf?id=tc9GAKlxQC
**Authors:** Anonymous (under review ICLR 2026)

**Core Mechanism (step-by-step):** Decouples memory management from primary agent workflow by introducing a k-step-off asynchronous pipeline. Memory model's summarization overlaps with agent's inference, masking context processing latency. Reward-driven training aligns memory model to capture sufficient statistics for agent decision-making. Theoretical analysis proves superior efficiency-effectiveness trade-off vs coupled architectures.

**Results (real numbers):** SWE-Bench-Verified: 1.4x latency improvements over vanilla long-context solutions while preserving most of the performance. Latency gains scale favorably with increased system throughput.

**Trade-offs:** Asynchrony introduces staleness risk. Reward-driven alignment requires careful design. Not all contexts benefit equally from decoupling.

**Design Rationale:** Context management is a bottleneck that can be parallelized. Memory model can run independently, producing summaries that agent consumes asynchronously. Overlap masks latency of compression.

**Transferable Idea for Lyra:** CoMEM's decoupled architecture is directly applicable to Lyra's memory system. Lyra's memory consolidation (Experience tier) could run asynchronously, parallel with agent execution, using a k-step-off pipeline. This would mask memory update latency.

**Gap vs Baseline:** Medium gap. Lyra currently couples memory operations with agent execution (synchronous reads/writes). Decoupling via CoMEM's architecture would improve throughput.

---

## 23. CraniMem: Cranial Inspired Gated and Bounded Memory for Agentic Systems
**URL:** https://openreview.net/pdf?id=Tts94WVw40
**Authors:** Pearl Mody et al. (DJSCE)

**Core Mechanism (step-by-step):** Neurocognitively motivated, gated and bounded multi-stage memory. Goal-conditioned gating + utility tagging + bounded episodic buffer (near-term continuity) + structured long-term knowledge graph (durable semantic recall). Scheduled consolidation loop replays high-utility traces into graph while pruning low-utility items. Selective forgetting via importance weighting and temporal decay.

**Results (real numbers):** On long-horizon benchmarks, CraniMem more robust than Vanilla RAG and Mem0 baselines. Exhibits smaller performance drops under injected noise/distraction. Code at https://github.com/PearlMody05/Cranimem, PyPI package at https://pypi.org/project/cranimem.

**Trade-offs:** Consolidation loop adds periodic overhead. Bounded buffers may lose rare but important items. Knowledge graph construction quality depends on entity extraction.

**Design Rationale:** Biological memory is gated, bounded, and multi-stage. Explicit separation of episodic and semantic memory with consolidation pathways enables rapid adaptation alongside stable knowledge formation.

**Transferable Idea for Lyra:** CraniMem's gated/bounded design with scheduled consolidation is directly applicable. Lyra's working/episodic/semantic tiers could use CraniMem's gating mechanism (what enters memory), utility tagging (importance scoring), and scheduled consolidation (replay high-utility into graph, prune low-utility). The noise robustness finding is relevant for Lyra in production environments.

**Gap vs Baseline:** Medium gap. Lyra has a three-tier memory but lacks CraniMem's principled gating, utility scoring, and consolidation scheduling.

---

## 24. Entropic Memory: A Thermodynamics-Inspired Consolidation Mechanism for Lifelong Agent Learning
**URL:** https://openreview.net/pdf?id=um6VpjcOtj
**Authors:** Jing Du, Hang Zhao (Northeastern University)

**Core Mechanism (step-by-step):** Two-tier memory (hot working buffer -> cold long-term store) with consolidation via free energy minimization: F = E + lambda*S. Internal energy E(m) = -Utility(m) (query relevance + recency). Entropy S(m) = H(e_m) (Shannon entropy of embedding distribution). Temperature T regulates plasticity. Candidate c replaces victim v with probability P = min(1, exp(-Delta F/T)). Stochastic replacement prevents local utility optima.

**Results (real numbers):** Infinite Room environment (5,000-step horizon, concept drift rate delta=0.005). At 30% noise: Entropic matches greedy Importance (SR ~0.29). At 50% noise: greedy Importance degrades to SR=0.24, Entropic maintains SR=0.28 (+15% relative). Hit@3, Info Density also match or exceed. Metrics vs Random (0.02), FIFO (0.26), LRU (0.27).

**Trade-offs:** Temperature parameter needs tuning per environment. Stochastic replacement may discard high-utility items in low-entropy regimes. Embedding entropy calculation adds overhead.

**Design Rationale:** Thermodynamic annealing provides principled exploration-exploitation tradeoff for memory consolidation. Entropy term penalizes noisy/distractor embeddings even if frequently accessed. Stochastic acceptance rule escapes local utility optima.

**Transferable Idea for Lyra:** Entropic Memory's free-energy minimization framework is directly applicable to Lyra's memory consolidation. Lyra could use a similar temperature-controlled stochastic replacement for its episodic->semantic consolidation, with entropic regularization to penalize noisy/distractor memories. The concept drift handling is relevant for Lyra's dynamic environments.

**Gap vs Baseline:** Medium gap. Lyra's memory consolidation (if any) is ad-hoc. Entropic Memory provides a principled, theoretically grounded consolidation mechanism with proven noise robustness.

---

## 25. Memory is Reconstructed, Not Retrieved: Graph Memory for LLM Agents (MRAgent)
**URL:** https://openreview.net/pdf?id=YPoHy6lgKP
**Authors:** Shuo Ji, Yibo Li, Bryan Hooi (National University of Singapore)

**Core Mechanism (step-by-step):** Cue-Tag-Content graph where associative tags serve as semantic bridges. Active reconstruction mechanism integrates LLM reasoning into memory access -- agent iteratively explores and prunes retrieval paths based on accumulated evidence. Formally: active policy pi^{(t)}_a selects next memory unit conditioned on evolving evidence: v^{(t)} = pi^{(t)}_a(x, S^{(t-1)}). Tags encode associations between fine-grained cues and specific memory contents. Theoretical proof that active retrieval policies are strictly more expressive than passive. Beam-search-like exploration prevents combinatorial explosion.

**Results (real numbers):** LOCOMO and LONGMEMEVAL benchmarks. Significant improvements over strong baselines (up to 23%). Substantially reduces token and runtime cost. Specific numbers per benchmark in the paper.

**Trade-offs:** Active reconstruction adds complexity vs simple top-k retrieval. LLM-driven path selection may hallucinate or get stuck in local optima. Tags need careful design for the domain.

**Design Rationale:** Cognitive neuroscience frames retrieval as active reconstruction, not passive readout. Tags provide lightweight semantic bridges that enable guided exploration without unconstrained expansion. Theoretical framework proves expressiveness advantage.

**Transferable Idea for Lyra:** MRAgent's active reconstruction paradigm is a transformative idea for Lyra's memory system. Instead of one-shot retrieval (current Lyra: embed query -> cosine similarity -> top-k), Lyra could implement iterative retrieval with LLM-driven path exploration over a memory graph. The Cue-Tag-Content graph structure is richer than flat embeddings.

**Gap vs Baseline:** Significant gap. Lyra's retrieval is passive (single-shot embedding similarity). MRAgent's active, multi-step reconstruction with LLM guidance could dramatically improve multi-hop reasoning. Implementation requires graph memory structure and iterative retrieval loop.

---

## 26. A-MAC: Adaptive Memory Admission Control for LLM Agents
**URL:** https://openreview.net/attachment?id=mmdqUrEY24&name=pdf
**Authors:** Guilin Zhang et al. (Workday)

**Core Mechanism (step-by-step):** Treats memory admission as a structured decision problem. Decomposes memory value into five interpretable factors: future utility, factual confidence, semantic novelty, temporal recency, content type prior. Combines lightweight rule-based feature extraction + single LLM-assisted utility assessment. Learns domain-adaptive admission policies through cross-validated optimization. Hybrid design: rules for confidence/novelty/recency/type, LLM only for utility.

**Results (real numbers):** LoCoMo benchmark. A-MAC achieves F1=0.583 (vs Mem0 baseline). Latency reduced by 31% vs SOTA LLM-native memory systems. Ablation: content type prior identified as most influential factor for reliable admission.

**Trade-offs:** LLM utility assessment still adds cost vs purely rule-based. Single confidence assessment may miss nuanced hallucination. Content type prior requires domain-specific calibration.

**Design Rationale:** Admission control is a critical but under-specified problem. Heuristic methods (MemGPT) are too rigid; LLM-native (A-Mem, Mem0) are expensive and opaque. Hybrid provides best of both: interpretability, efficiency, expressiveness. Hallucination as first-class concern -- factual confidence dimension directly mitigates hallucinated content entering memory.

**Transferable Idea for Lyra:** A-MAC's five-factor admission framework is directly applicable to Lyra's MemoryStore write policy. Lyra currently admits all interactions to memory; A-MAC would enable selective admission based on utility, confidence, novelty, recency, and type. The content type prior (most influential factor) suggests Lyra should prioritize admitting certain content types over others. The hallucination mitigation (factual confidence) is critical for production reliability.

**Gap vs Baseline:** Significant gap. Lyra has no admission control -- everything is stored. A-MAC provides a principled, interpretable framework with 31% latency reduction and better precision-recall tradeoff.

---

## 27. Feedback Descent: Open-Ended Text Optimization via Pairwise Comparison
**URL:** https://openreview.net/attachment?id=Uw5G3H26ps&name=pdf
**Authors:** Anonymous (under review ICLR 2026)

**Core Mechanism (step-by-step):** Iterative optimization loop: evaluator compares current best artifact vs new candidate, returns preference + textual rationale. Rationales accumulated in history, providing directional information for next mutation. Formalizes why textual feedback enables dimension-free convergence under idealized assumptions, while zeroth-order methods suffer exponential slowdown. Purely inference-time, no weight updates, task-agnostic.

**Results (real numbers):** Matches SOTA prompt optimization (GEPA). Outperforms RL baselines (GRPO, REINVENT). Molecule discovery: molecules surpassing 99.9th percentile of 260,000+ compounds across six protein targets. Visual design, prompt optimization, and molecule discovery domains demonstrated.

**Trade-offs:** Requires strong evaluator model. Feedback quality determines optimization quality. Cumulative history may grow large. Not all problems benefit equally from comparative feedback.

**Design Rationale:** Scalar rewards discard information about why one behavior is better. Textual rationales provide richer optimization signal. Pairwise comparison is easiest form of human feedback to elicit.

**Transferable Idea for Lyra:** Feedback Descent could inform Lyra's experience generation. Instead of scalar success signals, Lyra could use comparative textual feedback to derive improvement directions. The theoretical framework (dimension-free convergence with textual feedback) provides justification for Lyra's textual memory format.

**Gap vs Baseline:** Low-medium direct applicability. Complementary optimization technique applicable to Lyra's experience refinement loop.

---

## 28. Agentic Memory Should Localize Compression (KAIST Position Paper)
**URL:** https://openreview.net/attachment?id=ztmwHisqJ4&name=pdf
**Authors:** Izaaz Inhar (KAIST)

**Core Mechanism (step-by-step):** Formalizes memory interference as update-induced behavioral drift: Delta_t(Q) = E_{q~Q}[D(pi_t(.|q) || pi_{t+1}(. | q))]. Proves that expected interference is controlled by retrieval-update overlap: Delta_t(Q) <= rho_t * epsilon_t, where rho_t = Pr_{q~Q}(U_t intersect R(q, M_t) != empty). Under routing stability, modularity reduces overlap. Proposition: monolithic memory (K=1) yields rho_t ~= 1; modular design reduces rho_t << 1. Concrete design requirements: (1) local compression with update isolation, (2) sparse routing, (3) explicit composition interface.

**Results (real numbers):** Position paper -- no experiments. Formal proof in Appendix A that modular compression reduces interference by factor of retrieval-update overlap probability.

**Trade-offs:** Modularity increases system complexity. Sparse routing may misroute (confidence gating with fallback as mitigation). Cross-module composition requires careful interface design.

**Design Rationale:** The key design question is not whether to compress, but where compression lives. Modularity-first: each module has own storage, compression policy, access boundary. Local updates affect only queries that retrieve updated modules.

**Transferable Idea for Lyra:** This is the most directly relevant theoretical paper for Lyra. Lyra's monolithic MemoryStore should be decomposed into modular sub-stores with independent lifecycles, compression policies, and access distributions. Formalizes what Lyra's three-tier memory should achieve: each tier is a module with its own retention/compression policy, and retrieval should route queries to the minimal subset of modules. The interference bound (Delta_t(Q) <= rho_t * epsilon_t) provides a metric for evaluating Lyra's memory stability under updates.

**Gap vs Baseline:** Significant validation of Lyra's direction. Lyra's three-tier architecture (working/episodic/semantic) is moving toward modularity, but needs explicit (1) independent lifecycle policies per tier, (2) sparse routing to minimize overlap, (3) explicit composition interfaces between tiers. The interference metric should be added to Lyra's evaluation.

---

## Synthesis: Key Themes for Lyra

### High-Impact, Directly Transferable Techniques
1. **Modular compression with interference control** (KAIST paper #28): Partition memory into modules with independent policies, sparse routing, explicit interfaces.
2. **A-MAC admission control** (#26): Five-factor admission (utility, confidence, novelty, recency, type) before writing to memory.
3. **MRAgent active reconstruction** (#25): Replace one-shot retrieval with iterative LLM-guided path exploration over memory graph.
4. **LP-RAG learned retrieval** (#9): GNN-based link prediction over memory graph, trained with synthetic queries.
5. **A-MEM structured notes** (#2): Multi-attribute notes (content + context + keywords + tags + embedding + links) with automatic linking and evolution.
6. **Entropic Memory consolidation** (#24): Free-energy minimization with stochastic replacement for episodic->semantic transfer.
7. **Cost-sensitive store routing** (#3): Selective store retrieval reduces tokens by 62% while improving accuracy.
8. **CraniMem gated/bounded design** (#23): Goal-conditioned gating + utility tagging + scheduled consolidation.

### Critical Insights for Lyra Architecture
- **Memory transplant protocol** (#1): Systematically evaluate whether gains come from architecture or content changes.
- **Solver capability moderates memory value** (#1): Weaker models benefit more (+15pp vs +7pp) -- memory as capability augmentation.
- **Content type prior dominates admission** (#26): Lyra should prioritize which content types persist.
- **Mutating vs non-mutating action distinction** (#10): Guide selective safety intervention.
- **Retrieval-update overlap controls stability** (#28): Monolithic memory always suffers interference on update.
- **Failure heuristics outperform success heuristics for search** (#8): Negative constraints prune ineffective strategies.
- **Callback mechanism for non-linear reasoning** (#13): Overcome linear memory overwriting limitations.

### Neglected Directions Lyra Should Exploit
- **Graph-based memory retrieval** (LP-RAG, MRAgent): Neither Lyra nor most baselines use learned graph retrieval.
- **Active reconstruction** (MRAgent): Only this paper integrates LLM reasoning into the retrieval loop itself.
- **Entropy-aware consolidation** (Entropic Memory): No system uses embedding entropy as a consolidation signal.
- **Contrastive memory distillation** (ReasoningBank): Most systems store raw trajectories; few distill contrastive strategies.
- **Decoupled async memory** (CoMEM): No system masks memory latency via asynchronous pipelines.
