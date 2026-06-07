# Model Routing & Cost Optimization — Thematic Synthesis

**Synthesized:** 2026-06-07
**Sources:** 15 papers, 3 books, 1 production repo, 2 web references
**Scope:** Model selection, cost-quality Pareto optimization, speculative execution, and tiered deployment architectures for the Lyra agent orchestration platform.

---

## 1. Frontier Techniques (ranked by evidence strength)

### 1.1 BEST-Route: Multi-Head Router with Best-of-N Test-Time Compute

- **Technique:** Adaptive multi-head router that dynamically selects both model and sampling depth (best-of-N) per query, using a shared DeBERTa backbone with KxN lightweight classification heads.
- **Sources:** BEST-Route paper (arXiv:2506.22716v1, ICML 2025); microsoft/best-route-llm repo (MIT license, deployed at Microsoft); also cited as predecessor to the RouteLLM framework.
- **Mechanism:**
  1. Train a proxy reward model R_proxy (DeBERTa-v3-large, 300M) via pairwise ranking on (worst, median, best) triples from 20-response generation.
  2. Train a multi-head router (DeBERTa-v3-small, 44M shared backbone + KxN lightweight classification heads) to predict "match probability": whether model k's best-of-n response is at least as good as reference model M_ref's single response.
  3. At inference: compute match probabilities for all (model, n) pairs, filter by threshold t, select the cheapest qualifying pair, generate n responses, return the highest-scored by R_proxy.
  4. Match probability: p_{k,n}(q) = sigma(w_{k,n}^T * h_q + b_{k,n})
  5. Selection: (M*, n*) = argmin cost[(M,n)] s.t. match_prob[(M,n)] >= t
- **Evidence:**
  - 40% cost reduction with only 0.47% quality drop (armoRM score)
  - 60% cost reduction with only 0.80% quality drop
  - vs. best baseline (N-label): 5.08% quality drop at 60% cost reduction (BEST-Route is 6.35x better)
  - OOD on MT-Bench: 1.56% quality drop at 40% cost reduction
  - Adding Codestral-22b as coding specialist: quality GAIN over GPT-4o at 10% cost reduction (-0.10%)
  - Router overhead: 0.04s prediction + 0.58s scoring = 0.62s total, 18.7x faster than Llama-3.1-8B inference
  - Beats cascading methods: 0.80% vs 7.26% quality drop at 60% cost reduction
- **Maturity:** Production deployed (Microsoft internal, ICML 2025 paper, open-source MIT licensed repo with training/evaluation pipeline).

### 1.2 RouteLLM: Preference-Data-Driven Binary Routing

- **Technique:** Learned binary router between strong (expensive) and weak (cheap) LLMs, trained on human preference data from Chatbot Arena.
- **Sources:** RouteLLM paper (Ong et al., arXiv:2406.18665v4, ICLR 2025); UC Berkeley + Anyscale + Canva; Open source framework released.
- **Mechanism:**
  1. Bradley-Terry formulation: P(wins|q) estimates probability strong model outperforms weak model.
  2. Routing decision: use weak model if P(wins|q) < alpha, strong otherwise. alpha controls cost-quality tradeoff.
  3. Four architectures spanning cost-capability: SW Ranking (no training), Matrix Factorization (8GB GPU), BERT classifier (2xL4 24GB), Causal LLM (8xA100).
  4. Data augmentation: golden-labeled data (MMLU, ~1500 samples) and LLM-judge data (~120K samples, $700).
  5. Matrix Factorization router with similarity-weighted Bradley-Terry:
     - delta(M, q) = w_2^T (v_m hadamard (W_1^T v_q + b))
     - P_theta(wins|q) = sigma(delta(M, q) - delta(M', q))
- **Evidence:**
  - MT Bench: 3.66x cost savings at 95% GPT-4 quality; CPT(50%) = 13.40% (only 13.4% of calls need GPT-4)
  - MMLU: 1.41x cost savings at 92% GPT-4 quality
  - GSM8K: 1.49x cost savings at 87% GPT-4 quality
  - Cross-model generalization: Claude 3 Opus/Sonnet routing achieves CPT(50%)=23.27% with ZERO retraining
  - Router overhead <0.4% of LLM generation cost
  - Outperforms commercial routers (Unify AI, Martian) with up to 40% fewer GPT-4 calls
- **Maturity:** Production validated (ICLR 2025, open source, commercial router comparison). Demonstrates cross-model generalization without retraining.

### 1.3 FrugalGPT LLM Cascade

- **Technique:** Three-strategy cost optimization framework: prompt adaptation, completion caching, and learned LLM cascade that routes queries sequentially through a tiered model chain.
- **Sources:** FrugalGPT paper (Chen et al., arXiv:2305.05176v1, ICML 2023); Stanford University.
- **Mechanism:**
  1. Cascade: ordered LLM list [M_1...M_m] sorted by cost (cheapest first).
  2. Train DistilBERT (66M) scoring function g(q,a) -> [0,1] predicting answer reliability.
  3. Learn per-model thresholds tau_i via grid search on validation set.
  4. At inference: cheapest model generates answer -> scorer evaluates -> if score > tau_i, accept and return; else escalate to next tier.
  5. Complementarity (MPI matrix): GPT-J sometimes gets right what GPT-4 gets wrong (~6% of queries), making cascade strictly better than any single model.
  6. Additional strategies: prompt selection (top-k examples by embedding similarity), query concatenation (batch of 3), semantic cache (21% hit rate, 95% savings).
- **Evidence:**
  - HEADLINES: 98.3% cost savings vs GPT-4, matching GPT-4 accuracy
  - OVERRULING: 73.3% cost savings
  - COQA: 59.2% cost savings
  - +1.5-4% absolute accuracy improvement at equal cost
  - Prompt selection: 70% fewer tokens with minimal accuracy loss
  - Model fine-tuning: 94-98.5% cost reduction
- **Maturity:** Research concept validated on classification/short-answer tasks. ICML 2023. Foundational paper that established the cascade paradigm. No production deployment evidence provided.

### 1.4 Speculative Decoding

- **Technique:** Draft model proposes candiate tokens autoregressively, target model verifies in parallel. Rejection sampling preserves exact output distribution.
- **Sources:** Speculative Decoding paper (Leviathan et al., arXiv:2211.17192v2, ICML 2023 Oral); Google Research. Also: Generative AI Design Patterns book (speculative decoding section, vLLM support). Cross-referenced in Lyra's existing plan.
- **Mechanism:**
  1. Draft gamma tokens from small model M_q autoregressively.
  2. Run M_p in one parallel forward pass on all gamma+1 prefixes.
  3. Sequential rejection: accept token i if r_i <= p_i(x_i)/q_i(x_i); first rejection terminates.
  4. Adjust final distribution: p'(x) = norm(max(0, p_{n+1}(x) - q_{n+1}(x))). This guarantees identical output distribution.
  5. Acceptance rate: beta = 1 - D_LK(p,q) = sum_x min(p(x), q(x)).
  6. Walltime improvement: (1 - alpha^{gamma+1}) / ((1 - alpha)(gamma*c + 1)), where c is cost ratio.
  7. Lenience extension: relax strict distribution matching for higher acceptance (up to 5X speedup).
- **Evidence:**
  - T5-XXL (11B) with T5-small (77M) draft: 3.4X walltime speedup (EnDe translation, temp=0)
  - LaMDA 137B with 8B draft: alpha = 0.75 acceptance rate
  - GPT-like: 97M target / 6M draft: alpha = 0.88
  - Even bigram draft achieves alpha = 0.20, enabling ~1.25X improvement
  - Lenience l=0.1 yields up to 5X speedup with bounded quality loss
  - Guarantee: output distribution is mathematically identical to target model (Appendix A.1 theorem)
- **Maturity:** ICML 2023 Oral, theoretical foundation proven. vLLM supports it out of the box (per Generative AI Design Patterns book). Key limitation: requires same-vocabulary draft/target pair, which Anthropic API does not expose at token level. Lyra's planned chunk-level approximation sacrifices the exact distribution guarantee.

### 1.5 Heterogeneous SLM-First Agentic Architecture

- **Technique:** Default to small language models for most agent operations, invoke large LLMs only selectively. Instrument, cluster, specialize, and replace LLM invocations with fine-tuned SLM specialists over time.
- **Sources:** "Small Language Models are the Future of Agentic AI" (Belcak et al., NVIDIA Research, arXiv:2506.02153v2, 2025). Cross-referenced: Generative AI Design Patterns book (Chapter: "Deploy Smaller Models"), Agentic Design Patterns book (Ch 16: Resource-Aware Optimization).
- **Mechanism:**
  1. S1 — Instrument all LLM call sites (prompts, outputs, metrics).
  2. S2 — Curate collected data (strip PII, filter noise).
  3. S3 — Cluster invocations by task type (intent recognition, summarization, tool-call generation, etc.).
  4. S4 — Select SLMs for each cluster (criteria: instruction following, benchmark perf, license, deployment footprint).
  5. S5 — Fine-tune SLMs via LoRA/QLoRA per task cluster. Optionally distill from LLM outputs.
  6. S6 — Iterate: retrain periodically with new usage data.
  7. Core argument: agents expose only narrow LM functionality (Argument A4) — deploying full LLMs for all calls is misallocation of resources.
- **Evidence:**
  - SLM inference is 10-30x cheaper (latency/energy/FLOPs) than 70-175B LLMs (meta-analysis of published numbers)
  - SLM fine-tuning: GPU-hours vs weeks for LLMs
  - Case-study estimates: MetaGPT 60% replaceable queries, Cradle 70%, Open Operator 40%
  - Cited model benchmarks: Phi-2 (2.7B) matches 30B models; DeepSeek-R1-Distill-Qwen-7B outperforms Claude-3.5-Sonnet on reasoning
  - Agentic AI market: $5.2B (2024) projected to $200B (2034)
  - **No new experiments** — position paper with synthesis of published results
- **Maturity:** Position paper (no end-to-end experimental validation of the conversion algorithm). Strong conceptual framework; heterogeneous architecture direction validated by multiple independent sources (Generative AI Design Patterns, Agentic Design Patterns).

### 1.6 Mixture-of-Agents with Diversity Maximization (RMoA)

- **Technique:** Multi-layer agent ensemble where each layer: (a) N proposers generate responses, (b) greedy diversity-based embedding selection picks K responses, (c) residual extraction agent identifies cross-layer improvements, (d) adaptive termination checks for convergence.
- **Sources:** RMoA paper (Xie et al., arXiv:2505.24442v1, 2025); Meituan + ECNU + Tsinghua. Open source code released.
- **Mechanism:**
  1. Greedy diversity selection: embed all N responses with BGE-m3, compute cosine similarity matrix, pick K maximally diverse responses via iterative min-max algorithm.
  2. Residual extraction: concatenate current and previous layer responses, extract cross-layer deltas (errors, discrepancies, missing info) via dedicated agent.
  3. Adaptive termination: monitor convergence of residuals across m consecutive layers; LLM-judged stopping.
  4. Role-playing personas per proposer to increase initial diversity.
  5. Aggregation at final layer combines prior responses with accumulated residuals.
- **Evidence:**
  - +4.55–11.10% average accuracy across all model sizes (7B-72B + GPT-4o)
  - 31.88% TFLOP reduction vs baseline MoA at same accuracy
  - 53.3% cumulative cost savings at turn 8 vs MoA
  - Hallucination reduction: 3.77%/round (7B models), 2.95%/round (GPT-4o)
  - DeepSeek-V3 + RMoA on MATH500: 92.40% (+4.20%)
  - DeepSeek-R1 + RMoA on MATH500 Level5 (hardest 41): 82.92% (+4.88%)
  - K=3 optimal diversity selection size across all benchmarks
  - MoA degrades at deeper layers; RMoA sustains improvement through residual connections
- **Maturity:** Research validated (multiple benchmarks, multiple model scales). Practical cost advantage demonstrated. Open source. Not yet production-deployed at scale.

### 1.7 On-Demand Retrieval Gating (SELF-RAG)

- **Technique:** Train the LLM itself to emit reflection tokens (Retrieve, ISREL, ISSUP, ISUSE) that gate retrieval, validate relevance, and self-critique output, using a canned critic model distilled from GPT-4.
- **Sources:** SELF-RAG paper (Asai et al., arXiv:2310.11511v1, 2023); University of Washington + AI2 + IBM Research.
- **Mechanism:**
  1. Train critic model C (Llama2-7B) on GPT-4-labeled reflection tokens (~47k calls).
  2. Train generator M (Llama2-7B or 13B) on augmented corpus where reflection tokens control retrieval.
  3. At inference: M predicts Retrieve token -> if confidence > delta, retrieve top-K passages -> predict ISREL relevance -> generate -> predict ISSUP support score -> beam-search with segment scoring.
  4. Segment score: f(y_t, d) = p(y_t|x,d,y_<t) + sum w_G * s_G, where s_G are normalized critique probabilities.
  5. Customizable at test time: adjust weights for citation precision vs fluency trade-off.
- **Evidence:**
  - SELF-RAG 7B beats proprietary ChatGPT on PubHealth (72.4 vs 70.1) and Bio FactScore (81.2 vs 71.8)
  - SELF-RAG 13B surpasses ChatGPT on 4/6 tasks
  - Retrieval gating: only 54.9% accuracy on PopQA vs 24.7% if retrieval disabled entirely — validates adaptive approach
  - Citation precision: 66.9% (7B), 70.3% (13B) — best among retrieval-augmented baselines
  - Human eval: 92.5% supported-and-plausible outputs on PopQA
- **Maturity:** Research validated (multiple benchmarks). Cost-saving mechanism is retrieval gating (not calling retrieval when unnecessary). No production deployment evidence.

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy Retention | Cost Savings | Latency Profile | Router Complexity | Multi-Turn | Evidence Strength |
|-----------|-------------------|--------------|-----------------|-------------------|------------|-------------------|
| **BEST-Route** | >99% at 40% cost reduction; >99.2% at 60% | 40-70% vs always-GPT-4o | +0.62s overhead (low) | Medium (train proxy RM + multi-head router) | Single-turn only | ICML 2025; Microsoft deployed; open source |
| **RouteLLM** | 95% (MT Bench), 92% (MMLU), 87% (GSM8K) | 1.4-3.7x vs strong-only | <0.4% of LLM generation | Low-Medium (SW/MF/ BERT/Causal LLM options) | Arena conversations only | ICLR 2025; cross-model generalization; open source |
| **FrugalGPT Cascade** | Matches or beats best single LLM | 59-98% vs best single LLM | Sequential calls increase worst-case | Low (DistilBERT 66M) | No | ICML 2023; foundational; no latency analysis |
| **Speculative Decoding** | 100% identical (guaranteed) | 2-3.4X walltime reduction | Faster (parallel verify) | Very Low (drop-in) | Yes (per-step) | ICML 2023 Oral; mathematical guarantee; API-limited |
| **SLM-First Heterogeneous** | Depends on SLM quality | 10-30x cheaper per call | Faster (local inference) | High (instrumentation + specialization pipeline) | Yes (architectural) | Position paper; no experiments; aligned with multiple books |
| **RMoA** | +4.55-11.10% accuracy gain | 31-53% cost reduction vs MoA | Multiple LLM calls per layer | Medium (embedding + residual agents) | No (single-turn eval) | Multi-benchmark; open source; practical gains |
| **SELF-RAG Gating** | 7B beats ChatGPT on 3/6 tasks | Reduces unnecessary retrieval cost | Beam search multiplies compute | Medium (critic training) | No | Multi-benchmark; GPT-4 dependency concern |

**Summary insight:** BEST-Route and RouteLLM are the two most directly deployable for Lyra. BEST-Route provides finer control (model + sampling depth) and stronger numbers but requires proxy RM infrastructure. RouteLLM is simpler (binary routing) and demonstrates cross-model generalization. Speculative Decoding provides the strongest theoretical guarantee but has an Anthropic API blocker at the token level. FrugalGPT Cascade is the simplest (DistilBERT scorer) but adds sequential latency. The SLM-first architecture is a long-term strategic direction, not a drop-in.

---

## 3. Convergences

### 3.1 Three-Tier Model Architecture (Strongest Consensus — 7 independent sources)

Every source that addresses deployment architecture converges on a three-tier model structure:

- **Tier 1 (Cheap/Fast):** Local or edge models, small APIs (Haiku, Gemini Flash Lite). For guardrails, classification, simple retrieval, format validation.
- **Tier 2 (Standard):** Mid-tier APIs (Sonnet, Gemini Flash, GPT-4o-mini). For standard reasoning, tool calling, code generation.
- **Tier 3 (Premium):** Frontier models (Opus, GPT-4o, Gemini Pro). For complex reasoning, architecture decisions, safety-critical validation.

**Sources agreeing:** FrugalGPT (2305.05176v1 — explicit 3-tier cascade), Generative AI Design Patterns book (BEST_MODEL/DEFAULT_MODEL/SMALL_MODEL strategy), Agentic Design Patterns book (Ch 16: "simple/cheap for routine, powerful/expensive for complex"), NVIDIA SLM position paper (2506.02153v2 — SLM-default + LLM-selective), BEST-Route (2506.22716v1 — heterogeneous model pool with tiered selection), Architecting Generative AI Applications book (cost-latency-quality triangle, 100x cost variation), Lyra's own brainstorm/05-router.md (Haiku/Sonnet/Opus tiers).

### 3.2 Router Must Be Cheap (4 independent sources)

All routing systems agree the router overhead must be negligible relative to the LLM calls being routed:

- FrugalGPT: DistilBERT (66M params) — "essentially free" per call
- RouteLLM: Router overhead <0.4% of LLM generation cost
- BEST-Route: DeBERTa-v3-small (44M) — 0.04s prediction + 0.58s scoring = 18.7x faster than smallest LLM
- Agentic Design Patterns book (Ch 2): "For high-throughput systems, use rule-based or embedding routing — cheaper and faster than LLM classification."

### 3.3 Cost Tracking as First-Class Metric (3 independent sources)

Multiple books independently emphasize that LLM cost must be a first-class observability dimension:

- Architecting Generative AI Applications book: "Track cost per request as a first-class metric — model costs vary by 100x. Log every LLM interaction with: model, prompt template version, input, output, tokens, latency, cost."
- Agentic Design Patterns book (Ch 19): "Track token usage for cost optimization." Anti-pattern: "Missing cost tracking."
- Generative AI Design Patterns book: "Ignoring the cost implications of long context windows in production" listed as critical anti-pattern. Cost budgets and hard limits per user/session recommended.

### 3.4 Prompt Caching for Static Prefixes (4 independent sources)

- Generative AI Design Patterns book: "Cache repeated prompt prefixes (system prompts, tool definitions, static context) to reduce latency and cost."
- FrugalGPT: Semantic cache achieves 21% hit rate, 95% cost reduction per hit.
- Claude API patterns: Prompt caching for system prompts and tool definitions.
- Lyra existing plan: Already identified as cost-saving mechanism in §4.21 Economics.

### 3.5 Quality Degradation Tiers with SLAs (3 independent sources)

- Generative AI Design Patterns book: "Define SLAs for each degradation tier; implement automated monitoring and alerting."
- Agentic Design Patterns book (Ch 19): Multi-dimensional evaluation with drift detection.
- Architecting Generative AI Applications book: Continuous monitoring of cost/latency/quality with automated fallback.

### 3.6 Complementarity Wins Over Single-Model Optimality (2 independent sources)

- FrugalGPT: MPI analysis proves GPT-J correctly answers ~6% of queries GPT-4 gets wrong. Cascade exploits this complementarity to beat the single best model.
- BEST-Route: Adding Codestral-22b specialist not only reduces cost but IMPROVES quality (-0.10% quality drop = quality gain). Routing to specialized models can surpass the strongest generalist.

---

## 4. Contradictions

### 4.1 Cascade (Sequential) vs. Parallel Routing

**Contradiction:** FrugalGPT advocates sequential cascade (cheapest model first, escalate if unreliable). BEST-Route advocates parallel routing (predict optimal model upfront, generate only from selected model). Both claim cost savings, but with fundamentally different latency implications.

- FrugalGPT: "Sequential LLM calls increase worst-case response time." When multiple models are queried, latency compounds. Not measured in paper.
- BEST-Route: Directly compares against cascading methods (Table 8): cascade shows 7.26% quality drop at 60% cost reduction vs BEST-Route's 0.80%. BEST-Route's parallel prediction (0.04s) avoids sequential LLM calls.
- **Resolution for Lyra:** Sequential cascade is appropriate when latency budget allows (batch/background tasks). Parallel routing is appropriate when latency matters (interactive queries). Lyra should implement BOTH strategies with a latency-adaptive selector that switches between them. The BEST-Route quality advantage at equivalent cost is decisive for quality-sensitive applications.

### 4.2 Binary vs. N-Way Routing

**Contradiction:** RouteLLM explicitly restricts to binary routing (strong vs weak model pair). BEST-Route handles K models x N sampling depths configurations simultaneously. RouteLLM argues binary covers the "most common practical scenario" but acknowledges real-world may need 3+ tiers.

- RouteLLM (ICLR 2025): "Binary routing only. No N-way extension demonstrated."
- BEST-Route (ICML 2025): Multi-head router with K x N heads. Tested with 7-8 models simultaneously.
- **Resolution for Lyra:** Lyra needs N-way routing (Haiku, Sonnet, Opus, local Llama, plus specialized models for code/tool-calling). RouteLLM's binary approach is insufficient for Lyra's heterogeneous model pool. BEST-Route's multi-head design or a tree-of-binary-routers approach should be adopted.

### 4.3 Prompt-Only vs. Response-Aware Routing

**Contradiction:** BEST-Route and RouteLLM route based solely on the prompt, before any model generates. FrugalGPT's cascade evaluates actual responses before deciding to escalate. RMoA evaluates actual responses for diversity selection.

- BEST-Route rationale: "The router must make its decision before generating any response. If it needed to evaluate candidate responses to decide, the cheaper models would already have generated output unnecessarily."
- FrugalGPT rationale: Response evaluation reveals cases where cheap models actually produce good answers, enabling exact confidence before escalation.
- **Resolution for Lyra:** Prompt-only routing is appropriate for the initial model selection (avoid wasted generation). Response-aware routing is appropriate for the cascading fallback decision (verify actual quality before escalating). This suggests a **two-phase routing design**: Phase 1 (prompt-only) selects initial model tier; Phase 2 (response-aware) decides whether to escalate or use the response.

### 4.4 SLM-First vs. LLM-Default Architecture

**Contradiction:** NVIDIA SLM paper (2506.02153v2) argues for SLM-by-default with LLM-selective fallback. But the same paper acknowledges (AV2) that economies of scale in centralized LLM inference "may offset per-token SLM cost advantages." The paper explicitly states "the jury is still out."

- Pro-SLM: 10-30x cheaper per token, faster, more agile to fine-tune, sufficient for narrow agent subtasks.
- Pro-LLM: $57B in data center investment in centralized infrastructure, massive economies of scale, tooling and ecosystem maturity (Barrier B1).
- **Resolution for Lyra:** This is not an either/or question. Lyra should adopt a data-driven approach: instrument actual LM calls, measure complexity distribution, and determine what percentage are truly SLM-suitable. The 60-70% replaceability estimate from the paper provides a starting hypothesis, but Lyra-specific telemetry must confirm. The architecture should support BOTH SLM and LLM backends interchangeably, with the router deciding per query.

### 4.5 Best-of-N Test-Time Compute vs Single-Sample Routing

**Contradiction:** BEST-Route argues best-of-N sampling is essential because the quality gap between single-shot small and large models is too large for effective routing. RouteLLM routes on single samples. RMoA uses parallel proposers (multiple samples) but with diversity-based selection.

- BEST-Route: "Best-of-n with n=5 alone: 4.9% quality drop for Phi-3-mini. BEST-Route with max n=5: 0.21% quality drop at 20% cost reduction." Best-of-N closes the quality gap for small models.
- RouteLLM: Single-response routing works because the binary decision (which model to call) is decoupled from response quality optimization.
- **Resolution for Lyra:** Best-of-N out of reach when using proprietary APIs (no n>1 without n parallel API calls). But for locally hosted SLMs, best-of-N is nearly free (generating multiple samples in one batch). Lyra should use best-of-N for local SLMs when API cost structure permits, and single-sample routing for proprietary API models.

---

## 5. Open Problems

### 5.1 Distribution Shift in Router Training (No source solves this)

RouteLLM, BEST-Route, and FrugalGPT all acknowledge that router performance degrades under distribution shift. RouteLLM routers trained purely on Chatbot Arena data perform at **random level** on MMLU/GSM8K. Data augmentation helps but doesn't generalize to arbitrary distributions. No source provides a principled solution — they rely on human-labeled data from the target domain.

**Research opportunity:** Online router adaptation using Lyra's own query distribution. A router that continuously updates its routing policy based on observed outcomes (reinforcement learning from task success/failure) could close this gap.

### 5.2 Multi-Turn Routing (No source addresses this)

Every routing paper evaluates single-turn, stateless queries. Real agent interactions are multi-turn conversations with memory, tool calls, and evolving context. The optimal model for turn 1 may differ from turn 5, and routing decisions compound across turns.

**Research opportunity:** A stateful router that considers conversation history, agent state, and accumulated context when making per-turn routing decisions. The routing optimization should account for the total session cost, not per-turn cost in isolation.

### 5.3 Router Feedback Loops and Bias (No source acknowledges this)

If the router learns from its own routing decisions, it creates a feedback loop: the router routes complex queries to expensive models and simple queries to cheap models. Over time, the cheap model's training data skews toward simpler queries, reinforcing the pattern. The router never discovers that cheap models might have improved on complex queries.

**Research opportunity:** Explore-exploit tradeoff in router training. Occasionally route queries to suboptimal model tiers to collect counterfactual data. Adaptation of bandit algorithms (epsilon-greedy, UCB, Thompson sampling) to model routing.

### 5.4 Dynamic Model Marketplace (Acknowledged but unsolved)

New models enter the market continuously (Claude 4.5, GPT-5, Gemini 2.5, etc.). All current routing approaches assume a static model pool with pre-collected training data. BEST-Route requires 20 responses per query per model. Retraining for every new model release is cost-prohibitive.

**Research opportunity:** Zero-shot model routing — predicting routing behavior for a new model based on benchmark scores and architectural properties, without generating training data. Transfer learning across model generations.

### 5.5 Router Explainability (No source addresses this)

No routing paper provides explanations for WHY a particular model was selected. For debugging, trust, and compliance, a routing decision should be transparent: "Routed to Sonnet because the query involves multi-step reasoning with code generation." Current routers are black-box classifiers.

**Research opportunity:** Train routers that output natural language rationales alongside routing decisions. The BERT-based classifiers used in RouteLLM and BEST-Route could be augmented with explanation heads via attention attribution or concept-based explanations.

### 5.6 Latency-Constrained Routing (Acknowledged gap)

FrugalGPT explicitly notes "latency unaddressed." RouteLLM measures throughput but not per-request latency. BEST-Route mentions router overhead (0.62s) but not end-to-end latency optimization. No source formulates routing as a latency-budget-constrained problem.

**Research opportunity:** Formulate routing as a constrained optimization: minimize cost subject to both quality >= q_min AND latency <= l_max. This requires latency prediction models for each model tier and query type, combined with the existing cost-quality optimization.

### 5.7 Token-Level vs. Chunk-Level Speculative Decoding for APIs

The speculative decoding paper's mathematical guarantee requires same-vocabulary draft/target pairs at the token level. Anthropic does not expose token-level speculative decoding as a public API. The chunk-level approximation (Haiku drafts full response chunks, Sonnet/Opus verifies) loses the exact distribution guarantee.

**Research opportunity:** Formal analysis of quality bounds for chunk-level speculative decoding with API-constrained draft/target pairs. When does the chunk-level approximation degrade unacceptably?

### 5.8 Routing for Agent Compositions (Not Just Single LLM Calls)

All routing papers route individual LLM API calls. In an agent system like Lyra, the "cost unit" is not a single LLM call but an agent composition: a planner model, tool-calling model, response model, and verifier model, potentially with different models at each step.

**Research opportunity:** Compositional routing — jointly optimizing model selection across an agent's entire execution graph, accounting for dependencies between steps (e.g., using a stronger planner may reduce the number of expensive tool-calling rounds).

---

## 6. Recommendations for Lyra

### Immediate Priority (Phase 4A — implement within 1-2 sprints)

1. **Implement Three-Tier Model Architecture with Static Router (Impact: 5, Effort: 2)**
   - Rationale: Strongest consensus across 7+ independent sources. Lyra already has model selection code; formalize into three explicit tiers (local/Haiku → Sonnet → Opus) with query-type-based static routing rules.
   - Starting configuration: classification/safety/guardrails → tier 1; tool calls/standard reasoning → tier 2; architecture/planning/complex debugging → tier 3.
   - Sources: FrugalGPT (2305.05176v1), Generative AI Design Patterns book, Agentic Design Patterns book Ch 16, NVIDIA SLM paper (2506.02153v2).

2. **Add Cost Tracking as First-Class Observability (Impact: 4, Effort: 2)**
   - Rationale: 3 independent book sources agree this is foundational. Cannot optimize what isn't measured.
   - Log per-call: model, prompt tokens, completion tokens, latency_ms, dollar_cost, cache_hit.
   - Implement cost budgets and hard limits per user/session.
   - Sources: Architecting Generative AI Applications book, Agentic Design Patterns book Ch 19, Generative AI Design Patterns book.

3. **Enable Prompt Caching for System Prompts and Tool Definitions (Impact: 3, Effort: 1)**
   - Rationale: Immediate cost reduction with zero architecture change. Anthropic and OpenAI both support prompt caching. Most Lyra calls share large system prompts and tool definitions.
   - Sources: Generative AI Design Patterns book, FrugalGPT (2305.05176v1 — semantic cache), Claude API patterns.

### Short-Term Priority (Phase 4B — implement within 3-5 sprints)

4. **Implement Response-Level Speculative Execution (Impact: 4, Effort: 3)**
   - Rationale: Already in Lyra's §4.21 plan. 2-3.4X latency reduction with mathematical guarantee (at token level). Lyra's chunk-level adaptation: Haiku drafts candidate responses, Sonnet/Opus scores and refines.
   - Limitation: No exact distribution guarantee at chunk level. Acceptable for Lyra's use case (agent responses, not safety-critical generation).
   - Sources: Speculative Decoding (2211.17192v2), Lyra §4.21.

5. **Train a Learned Router Using Lyra's Own Eval Data (Impact: 5, Effort: 4)**
   - Rationale: RouteLLM demonstrated that preference data from Lyra's own eval harness can train an effective router. Matrix factorization approach (8GB GPU, open source) is the lowest-effort starting point.
   - Phase 1: Collect pairwise model comparison data from Lyra's existing benchmark runs.
   - Phase 2: Implement matrix factorization router (RouteLLM architecture).
   - Phase 3: Calibrate alpha threshold for Lyra's specific quality targets.
   - Sources: RouteLLM (2406.18665v4), BEST-Route (2506.22716v1).

6. **Implement Latency-Adaptive Cascade vs Parallel Selection (Impact: 3, Effort: 3)**
   - Rationale: Resolves the cascade vs parallel contradiction (Section 4.1). Interactive queries use prompt-only parallel routing. Background/batch queries use response-aware cascade (cheap model first, escalate if needed).
   - Sources: FrugalGPT (2305.05176v1) for cascade, BEST-Route (2506.22716v1) for parallel.

### Medium-Term Priority (Phase 4C — implement within 6-10 sprints)

7. **Instrument and Begin SLM Specialization Pipeline (Impact: 4, Effort: 4)**
   - Rationale: NVIDIA's SLM position paper and the three-tier consensus from books argue for progressive SLM substitution. Start with highest-volume, narrowest-scope call sites (format validation, intent routing, simple classification).
   - Phase 1: Instrument call sites and collect data (2 weeks).
   - Phase 2: Cluster invocations and select candidate SLMs (1 sprint).
   - Phase 3: Fine-tune SLM specialists via LoRA and A/B test against LLM baseline (2 sprints).
   - Sources: NVIDIA SLM paper (2506.02153v2), Generative AI Design Patterns book.

8. **Implement BEST-Route-Style Multi-Head Router (Impact: 5, Effort: 5)**
   - Rationale: BEST-Route achieves the strongest cost-quality numbers and supports N-way routing with best-of-N sampling. Upgrades from the matrix factorization router (#5 above) to full multi-head architecture.
   - Requires: proxy reward model training, multi-head router training, threshold calibration.
   - Sources: BEST-Route (2506.22716v1), microsoft/best-route-llm repo (MIT license).

9. **Adopt Diversity-Based Response Selection for Multi-Agent Outputs (Impact: 3, Effort: 2)**
   - Rationale: RMoA's greedy diversity selection replaces expensive judge-model calls with cheap embedding operations. Directly applicable to Lyra's multi-agent consensus and debate modules.
   - Implementation: Add BGE-m3 embedding + greedy K-selection (~50 lines of code) to agent output aggregation.
   - Sources: RMoA (2505.24442v1).

### Long-Term Research (Phase 5 — beyond initial release)

10. **Explore-Exploit Router with Counterfactual Data Collection (Research)**
    - Rationale: Addresses the open problem of router feedback loops (Section 5.3). Use epsilon-greedy or Thompson sampling to occasionally route queries to non-optimal tiers for data collection.
    - This is a research contribution if executed rigorously.

11. **Compositional Routing for Agent Execution Graphs (Research)**
    - Rationale: Addresses the open problem of agent-composition routing (Section 5.8). Jointly optimize model selection across Lyra's entire agent execution graph.
    - Potential approach: Formulate as constrained optimization over Markov Decision Process where states are agent execution steps, actions are model selections, rewards are task success, costs are cumulative LLM spend.

---

## Source Index

### Papers
| ID | Title | Citation |
|----|-------|----------|
| 2305.05176v1 | FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance | Chen et al., ICML 2023, Stanford |
| 2211.17192v2 | Fast Inference from Transformers via Speculative Decoding | Leviathan et al., ICML 2023 Oral, Google Research |
| 2406.18665v4 | RouteLLM: Learning to Route LLMs with Preference Data | Ong et al., ICLR 2025, UC Berkeley + Anyscale + Canva |
| 2506.22716v1 | BEST-Route: Adaptive LLM Routing with Test-Time Optimal Compute | Ding et al., ICML 2025, Microsoft + UBC + Google DeepMind |
| 2505.24442v1 | RMoA: Optimizing Mixture-of-Agents through Diversity Maximization and Residual Compensation | Xie et al., 2025, Meituan + ECNU + Tsinghua |
| 2506.02153v2 | Small Language Models are the Future of Agentic AI | Belcak et al., 2025, NVIDIA Research |
| 2310.11511v1 | SELF-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | Asai et al., 2023, UW + AI2 + IBM |
| 2410.10762v4 | AFlow: Automating Agentic Workflow Generation | Zhang et al., ICLR 2025, MetaGPT |
| 2505.12467v1 | Beyond Frameworks: Unpacking Collaboration Strategies in Multi-Agent Systems | Wang et al., 2025 |
| 2406.07155v3 | Scaling Large Language Model-Based Multi-Agent Collaboration | Qian et al., 2025 |

### Books
| Title | Relevant Chapters |
|-------|-------------------|
| Agentic Design Patterns (O'Reilly) | Ch 2: Routing; Ch 4: Reflection; Ch 16: Resource-Aware Optimization; Ch 19: Evaluation |
| Generative AI Design Patterns (O'Reilly) | Ch 1: Model Landscape; Ch 6: Deploy Smaller Models; Ch 10: Guardrails; Ch 16: Composable Patterns |
| Architecting Generative AI Applications (O'Reilly) | Ch 1: Cost-Latency-Quality Triangle; Ch 9: Observability; Ch 12: Cost Controls |

### Web/Repos
| Source | Content |
|--------|---------|
| microsoft/best-route-llm | Production router implementation (MIT); DeBERTa-v3 multi-head router training pipeline; proxy reward model training |
| Anthropic Engineering Blog | Multi-agent research system architecture with implicit routing patterns |

### Lyra Internal
| Document | Content |
|----------|---------|
| brainstorm/05-router.md | Lyra router design brainstorm — intent classification, tool-selection routing |
| MASTER-PLAN.md | §4.21 Economics — speculative decoding plan, cost-conscious design |
| ARCHITECTURE-DEBATE.md | Ongoing architecture debates including model selection strategy |
