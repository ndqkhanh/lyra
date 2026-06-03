# Routing, Planning, and Cost Economics — Deep-Read Research

## Table of Contents

1.  [3.14 Model Routing](#314-model-routing)
    - [RouteLLM (Paper + Code)](#routellm)
    - [Hybrid LLM / BEST-Route](#hybrid-llm--best-route)
    - [FrugalGPT](#frugalgpt)
    - [Knowledge Access Beats Model Size](#knowledge-access-beats-model-size)
    - [Bitter Lesson of Diffusion LMs](#bitter-lesson-of-diffusion-lms)
2.  [3.21 Planning & Reasoning](#321-planning--reasoning)
    - [RAP (Reasoning + Planning as World Model)](#rap)
    - [Tree of Thoughts (ToT)](#tree-of-thoughts)
    - [SWE-Search](#swe-search)
    - [AFlow](#aflow)
    - [MC-DML](#mc-dml)
    - [Agentic Reasoning (Mind-Map KG)](#agentic-reasoning)
    - [IterResearch](#iterresearch)
3.  [3.22 Cost & Latency Economics](#322-cost--latency-economics)
    - [Speculative Decoding](#speculative-decoding)
    - [Cost-Augmented MCTS (Cost-Awareness)](#cost-augmented-mcts)
4.  [3.15 Reliability & Observability](#315-reliability--observability)
    - [Langfuse](#langfuse)
    - [OpenLLMetry](#openllmetry)
    - [Phoenix (Arize AI)](#phoenix)
    - [Tau-Bench / Tau2-Bench](#tau-bench--tau2-bench)
    - [SWE-bench Verified](#swe-bench-verified)

---

## §3.14 Model Routing

---

### RouteLLM

**URLs:** [arXiv:2406.18665](https://arxiv.org/abs/2406.18665) (paper), [github.com/lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) (source code)

**Core Mechanism (step-by-step):**

RouteLLM frames model routing as a **binary win-prediction problem**: given a query q, predict the probability that a strong (expensive) model would produce a better answer than a weak (cheap) model. A user-specified threshold alpha converts this probability into a routing decision: route to weak model if P(strong wins) < alpha, otherwise use strong.

The framework tests four router architectures:

1. **Similarity-Weighted (SW) Ranking** -- A Bradley-Terry model with exponential similarity weighting (gamma=10). Embeds queries via `text-embedding-3-small`. Computes cosine similarity between test query and all training queries, weights training comparisons by `w_i = 10^(1+S(q,q_i))`. Learns BT coefficients for 10 model tiers at inference time. No explicit training step. Zero-shot.

2. **Matrix Factorization** -- Inspired by recommender systems. Learns latent embeddings for both model identity (dim d_m) and query (dim d_q) via a bilinear scoring function: `s(M,q) = w2^T(v_m ⊙ (W1^T v_q + b))`. Win probability via Bradley-Terry: `P(win_Mw|q) = sigma(s(M_w,q) - s(M_l,q))`. Trained on 1×8GB GPU, ~10 epochs, Adam lr=3e-4, batch 64.

3. **BERT Classifier** -- Standard text classification: CLS token -> logistic regression head. Full-parameter fine-tuning. Trained on 2×L4 24GB GPUs, ~2000 steps, batch 16, max len 512, lr=1e-5.

4. **Causal LLM Classifier** -- Llama 3 8B backbone with instruction-following: appends comparison labels as vocabulary tokens. Win probability via softmax over label classes. Trained on 8×A100 80GB GPUs, ~2000 steps, batch 8, max len 2048, lr=1e-6.

Training data: 80K Chatbot Arena battles → ~65K pairwise comparisons (pruned <16 chars). Models clustered into 10 Elo tiers. Augmented with (a) D_gold: ~1,500 MMLU validation questions auto-labeled by correctness; (b) D_judge: ~120K Nectar samples with GPT-4-as-judge labels (~$700 total).

**Results (real numbers):**

Metrics: PGR (Performance Gap Recovered), CPT(x%) (minimum strong-model calls for x% PGR), APGR (area under curve).

MT Bench (GPT-4 vs Mixtral 8x7B):
- Matrix Factorization (D_arena + D_judge): CPT(50%)=13.4%, CPT(80%)=31.3%, APGR=0.802 → **3.66x cost savings at 95% of GPT-4 quality**
- SW Ranking (augmented): APGR=0.759
- Random baseline: APGR=0.500

MMLU 5-shot:
- SW Ranking (D_arena + D_gold): APGR=0.603, CPT(50%)=35.4%
- Causal LLM: APGR=0.600, CPT(50%)=35.5%

GSM8K 8-shot:
- Causal LLM (augmented): APGR=0.622, CPT(50%)=33.6%, CPT(80%)=63.3%

Transfer learning (Claude 3 Opus / Llama 3 8B, no retraining):
- Matrix Factorization (aug): APGR=0.703 on MT Bench
- Causal LLM (arena only): APGR=0.645

Routing overhead (per million requests):
- SW Ranking: $37.36 (2.9 req/s) -- expensive due to API embedding calls
- Matrix Factorization: $1.42 (155 req/s) -- cheapest and fastest
- BERT: $3.19 (70 req/s)
- Causal LLM: $5.23 (42 req/s)

**Trade-offs:**
- No router dominates across all benchmarks; best router depends on task distribution
- High-capacity models (BERT, Causal LLM) underperform in low-data regimes but excel with augmentation
- D_arena alone is insufficient for OOD benchmarks (MMLU, GSM8K) due to distribution mismatch
- D_gold (~1,500 samples, <2% of data) dramatically improves structured tasks
- SW Ranking is the most expensive router (API calls) but competitive quality
- Only supports two-model routing; N-way is future work

**Design Rationale:**
- Binary routing (strong vs weak) is the most common real-world scenario and foundation for N-way
- Ties treated as weak-model wins -- conservative cost-saving choice
- 10-model-tier clustering reduces label sparsity
- Router performance "can vary widely" even on identical data -- suggests deeper analysis needed

**Transferable Idea for Lyra (4.5 Router):**
- Deploy a **lightweight BERT or matrix-factorization router** as a gating layer between Lyra's model inventory. The router should learn per-query win probabilities from preference data (Chatbot Arena style) or from Lyra's own execution traces.
- Cost: matrix factorization route costs <$1.42/million requests at 155 req/s -- negligible vs LLM generation.
- The **augmentation strategy** (D_gold, D_judge) is directly applicable: Lyra can bootstrap routing data from its own task evaluations.

**Gap vs Baseline:**
- Lyra currently has **no router** -- every sub-agent invocation defaults to an agent-specific fixed model. A learned router could achieve ~3x cost savings at near-identical quality, and the transfer-learning results show routers generalize to unseen model pairs.

---

### Hybrid LLM / BEST-Route

**URLs:** [github.com/microsoft/best-route-llm](https://github.com/microsoft/best-route-llm) (code), [arXiv:2506.22716](https://arxiv.org/abs/2506.22716) (BEST-Route, ICML 2025), [arXiv:2404.14618](https://arxiv.org/abs/2404.14618) (Hybrid LLM, ICLR 2024)

**Core Mechanism (step-by-step):**

Hybrid LLM (ICLR 2024) demonstrated that routing queries between models can reduce cost, but a single small-model response often cannot beat a large model's response. This observation motivates **BEST-Route** (ICML 2025), which introduces **test-time optimal compute**: dynamically select both the model AND the number of samples (best-of-n) per query.

Three components:
1. **Proxy Reward Model (R_proxy):** Fine-tuned from OpenAssistant RM (DeBERTa-v3-large, 300M params). Trained with pairwise ranking loss on (worst, median, best) response triples from n=20 samples: `L_rank = -1/|P| sum log sigma(R_proxy(s) - R_proxy(s'))`. Avoids using all C(n,2) pairs since similar-quality comparisons are uninformative.

2. **Multi-Head Router:** Shared BERT-style backbone (DeBERTa-v3-small, 44M params) with K×N lightweight classification heads -- one per (model k, sample-count n) pair. Each head predicts: `p_{k,n}(q) = sigma(w_{k,n}^T h_q + b_{k,n})` -- probability that best-of-n responses from model k match reference model quality. Trained with cross-entropy loss for 55 epochs.

3. **Inference Algorithm:**
   1. Compute match probabilities for all (model, n) combinations via multi-head router
   2. Filter: keep only combinations where match_prob >= threshold t
   3. Select lowest-cost valid combination: cost = n × avg_output_len × output_token_price + input_len × input_token_price
   4. Fallback to reference model (GPT-4o) with n=1 if no combo meets threshold
   5. Draw n_samp samples, score with R_proxy, return best

Training data: 10K instruction examples (8K/1K/1K split) from MixInstruct, RewardBench, CodeUltraFeedback, BeaverTails. 20 responses generated per example per model. 8 models total: GPT-4o (reference), GPT-3.5-turbo, Llama-3.1-8B, Mistral-7B, Mistral-8x7B, Phi-3-mini, Phi-3-medium, Codestral-22B.

**Results (real numbers):**

Cost reduction vs quality drop (armoRM metric):
- 10% cost reduction: only 0.19% quality drop
- 20% cost reduction: 0.21% drop
- 40% cost reduction: 0.47% drop
- 60% cost reduction: 0.80% drop ← key headline

Coding domain (with Codestral-22B): up to 20% cost reduction while *exceeding* GPT-4o quality (negative drops).

OOD MT-Bench: 60% cost reduction at 1.59% quality drop -- "up to 4.3% better than strongest baseline."

vs Model Cascades: all cascade variants show ~7.26% quality drop even at 10% cost reduction; BEST-Route achieves 60% reduction at 0.80% drop.

N-class routing baseline: only 0.07% cost reduction (effectively none).

Routing latency: 0.04s for match probability prediction. Best-of-n (n=20) overhead: 0.58s. Total: 18.7x faster than fastest LLM.

Pricing: GPT-4o ($5/$15 per 1M in/out), Llama-3.1-8B ($0.3/$0.61), Mistral-7B ($0.25/$0.25), Phi-3-mini ($0.3/$0.9), Codestral-22B ($1/$3).

**Trade-offs:**
- **Dependency on proxy reward model accuracy** -- misalignment with ground truth causes suboptimal selection
- **Scalability to hundreds of models** -- "may require additional optimizations"
- Best-of-n increases LLM generation latency by 30%-59.3% (n from 1 to 20) but routing stays fast
- The approach is fundamentally about **improving cheap models** (via best-of-n) rather than replacing expensive ones
- Best-of-n with fixed n per model: 4.9% quality drop for Phi-3-mini even at n=5 (standalone). BEST-Route: 20% cost reduction at 0.21% drop with adaptive n.

**Design Rationale:**
- Why not LLM-as-judge scoring? "impractical for real-time inference" -- adds substantial compute/memory
- Why only worst/median/best pairs for R_proxy? "minor misclassifications among similar-quality pairs has minimal impact" since only top response matters for best-of-n
- Why multi-head router vs K×N separate routers? "Training and deploying K×N separate pair-wise routers is computationally expensive"
- Why not cascades? They "involve multiple LLM calls per query" causing substantial overhead

**Transferable Idea for Lyra (4.5 Router, 4.21 Economics):**
- The **multi-head router** architecture is directly applicable: a shared 44M-parameter backbone with per-(agent, n) heads. Lyra's sub-agents and tool-use tasks map cleanly onto this structure.
- The **best-of-n with proxy reward** mechanism is the key insight: instead of deciding "which model," also decide "how many samples" for the chosen model. This is particularly relevant for Lyra's code-generation and verification sub-agents where multiple samples with scoring are already partially supported.
- The **cost-aware selection** (minimize cost among valid combos) gives Lyra a principled framework for its budget-aware routing.
- The negative result about N-class routing (0.07% cost reduction) confirms that simple per-query model classification is insufficient.

**Gap vs Baseline:**
- Lyra's current per-task model selection is effectively a hand-crafted N-class router. BEST-Route shows this captures essentially zero cost savings.
- Lyra has no proxy reward model for response selection, no multi-head routing, and no cost-modeling for dynamic sample-count allocation.

---

### FrugalGPT

**URL:** [arXiv:2305.05176](https://arxiv.org/abs/2305.05176)

**Core Mechanism (step-by-step):**

FrugalGPT (Stanford, May 2023) is the foundational work on LLM cost reduction. It outlines three strategy categories:

1. **Prompt Adaptation:** Reduce prompt size to lower token costs. Sub-strategies:
   - Prompt selection: keep only a subset of in-context examples
   - Query concatenation: batch multiple queries into one prompt

2. **LLM Approximation:** Replace expensive LLMs with cheaper alternatives:
   - Completion cache: store responses, serve cached results for similar queries
   - Model fine-tuning: fine-tune small models on expensive-LLM outputs

3. **LLM Cascade** (primary contribution): A learned cascade that sequentially calls LLMs from cheap to expensive. Key components:
   - **Generation scoring function g(q, a):** A regression model (DistilBERT in experiments) that scores response reliability
   - **LLM Router L:** Selects the ordered list of m LLM APIs
   - **Cascade execution:** Call each API in sequence; if g(q, f_Li(q)) >= threshold τ_i, accept and stop; otherwise, escalate to next API

   The learning problem is a constrained mixed-integer optimization:
   - Maximize `E[r(a, f_Lz(q))]` subject to average cost ≤ budget
   - Solved via: (1) prune search space by ignoring lists with small answer disagreement; (2) approximate objective via interpolation

Tested on 12 LLM APIs from 5 providers (OpenAI, AI21, CoHere, Textsynth, ForeFrontAI) spanning 2 orders of magnitude in cost. Cascade length of 3.

**Results (real numbers):**

Cost savings to match best individual LLM performance:
- HEADLINES (financial news): **98.3% cost savings** (GPT-4 baseline: $33.1 → FrugalGPT: $0.6), with +1.5% accuracy improvement
- OVERRULING (legal): 73.3% cost savings (GPT-4: $9.7 → $2.6)
- COQA (reading comprehension): 59.2% cost savings (GPT-3: $72.5 → $29.6)

Performance-cost trade-off curve: FrugalGPT achieves smooth Pareto frontier across all cost budgets, while individual LLMs are discrete points.

Case study (HEADLINES, budget=$6.50 = 1/5 GPT-4 cost): Cascade = GPT-J → J1-L → GPT-4. Scoring thresholds: GPT-J score > 0.96 → accept; J1-L score > 0.37 → accept. This learned cascade outperforms GPT-4 alone (0.872 vs 0.857 accuracy) at 80% cost reduction.

Diversity analysis (MPI heatmaps): Cheap LLMs complement expensive ones in 6-13% of cases. E.g., GPT-4 makes a mistake but GPT-J gives correct answer for ~6% of HEADLINES, and GPT-3 complements GPT-4 in ~13% of COQA -- demonstrating why model diversity drives cascade efficacy.

**Trade-offs:**
- Cascade requires training a scoring function per domain (DistilBERT in experiments)
- The mixed-integer optimization is computationally expensive; pruning needed
- Budget is average-cost rather than per-query, so some queries exceed budget
- Only tested with cascade length 3; longer cascades may not monotonically improve
- Relies on 2023 model prices which have since changed significantly

**Design Rationale:**
- Cascade exploits model diversity: even cheap models can answer some hard queries correctly
- The scoring function approach (evaluate before accepting) is more sample-efficient than always calling all models
- FrugalGPT is the first work to unify prompt adaptation + model selection + cascade under a budget constraint

**Transferable Idea for Lyra (4.5 Router, 4.21 Economics):**
- The **LLM cascade** pattern maps directly onto Lyra's multi-agent architecture: cheap local models → medium cloud models → premium models. Lyra should implement a cascade with learned reliability scoring at each tier.
- The **completion cache** (LLM approximation) is immediately applicable: Lyra's frequent sub-agent invocations on similar queries (e.g., verification, formatting) can be cached.
- The **cost budget formulation** (`E[cost] <= B` with average-cost constraint) is more practical than per-query budgets for Lyra's batched execution.
- The **98% cost savings at matching quality** finding is the strongest evidence that Lyra's routing tier could achieve radical cost reduction.

**Gap vs Baseline:**
- Lyra has no cascade, no scoring function, no cache, and no budget-aware optimization. Every query pays full price for the agent's default model.

---

### Knowledge Access Beats Model Size

**URL:** [arXiv:2603.23013](https://arxiv.org/pdf/2603.23013)

**Core Mechanism (step-by-step):**

This paper (March 2026) investigates the **interaction between conversational memory and model routing** -- a previously unstudied combination. Core finding: **memory does not change routing decisions; it makes routing worthwhile.**

Three-component pipeline (the "compound strategy"):
1. **Cross-Model Memory Injection:** After each inference call, store the conversation turn-pair in a vector DB (Milvus, 768-dim Matryoshka embeddings). At query time, retrieve top-k relevant memories via hybrid search (BM25 + cosine similarity). Inject as system-context messages.

2. **Confidence-Based Routing:** Probe-then-escalate. Send memory-augmented prompt to cheap model (8B). Compute mean log-probability over all output tokens: `c = (L_bar - L_min) / |L_min|` where L_min = -3. If c >= threshold tau (0.50), accept. Otherwise escalate to expensive model (235B).

3. **Compound Effect:** Routing provides cost savings (nearly all queries on cheap path); memory provides correctness (+17.5 F1). The 2x2 factorial experiment reveals: without memory, the 8B model is "confidently wrong" -- it fabricates plausible answers about user-specific facts with high token-level confidence. Memory transforms confidently wrong into confidently right.

The critical insight: **35% of production queries are genuinely novel; 47% are semantically similar to prior queries; 18% are exact duplicates.** For personalization agents, most queries recur -- creating a natural amortization dynamic where early expensive interactions build memories that enable later cheap correct answers.

**Results (real numbers):**

2x2 factorial on LoCoMo (152 questions, Qwen3-8B / Qwen3-235B-A22B):

| Condition | F1 (%) | % on 8B | EffCost |
|---|:---:|:---:|:---:|
| Cold 8B (no memory, no routing) | 15.4 | 100% | 15K |
| Cold compound (routing only, no memory) | 13.0 | 96% | ~16K |
| Warm mem-only (memory, no routing) | 30.1 | 100% | 110K |
| **Warm compound (memory + routing)** | **30.5** | **100%** | **22K** |
| Cold 235B (no memory) | 13.7 | 0% | 443K |
| Full-context 235B (upper bound) | 43.9 | 0% | 68M |

Key findings:
- Memory-augmented 8B recovers **69% of full-context 235B quality** at **96% cost reduction**
- **235B without memory (13.7%) underperforms standalone 8B (15.4%)** -- model size irrelevant without knowledge
- Hybrid retrieval (BM25 + cosine) adds +7.7 F1 over cosine-only on LongMemEval
- Per-category: memory helps single-hop (+28.9 F1), hurts temporal (-3.8 F1)

Compared to published baselines (which use GPT-4o + structured memory):
- Mem0 (GPT-4o): 41.0% F1 vs Warm compound 8B: 30.5% F1
- The 8B with memory approaches Mem0 quality at ~50x smaller model

**Trade-offs:**
- **Memory adds input tokens**: Warm (memory-only) consumes 102K input tokens, 10x cold baseline. However, the compound pipeline's probe uses truncated context (16K input) for cost-efficient routing.
- **Temporal reasoning degrades**: Turn-pair memories counterproductive for when-based questions (-3.8 F1) -- structured memory representations needed.
- **Startup cost**: Early queries may escalate more frequently until memory store accumulates.
- **Confidence miscalibration risk**: Without calibrated confidence, routing could skip the expensive model when needed.

**Design Rationale:**
- The key insight is that routing and memory address **orthogonal failure modes**: routing provides cost savings, memory provides correctness
- Log-probability-based confidence is chosen because it requires no training data, no classifiers
- Hybrid retrieval is essential because user queries contain both semantic (ideas) and lexical (names, dates) cues
- Verbatim turn-pairs (not summaries) avoid hallucination risk that would compound with retrieval noise
- Cross-model memory means memories from expensive-model interactions benefit future cheap-model queries

**Transferable Idea for Lyra (4.5 Router, 4.16 Memory/Routing interaction):**
- This is the single most directly relevant paper for Lyra. The **memory-makes-routing-worthwhile** finding fundamentally changes how Lyra should design its routing layer.
- Lyra should implement **cross-agent memory injection**: memories from prior sub-agent invocations (across the entire agent fleet) are available as retrieval context for future routing decisions. When a coding agent previously solved a similar issue, a verification agent can use that memory for accurate checking.
- The **log-probability confidence routing** is simpler than learned routers (RouteLLM, BEST-Route) and avoids training data requirements. Lyra can deploy this immediately.
- The **hybrid retrieval** (BM25 + cosine) pattern applies to Lyra's tool-selection and context-retrieval systems.
- The **amortization dynamics** align with Lyra's persistent agent model: as the system accumulates memories, routing decisions improve naturally.

**Gap vs Baseline:**
- Lyra has **no conversational memory**, **no cross-agent knowledge sharing**, and **no confidence-based routing**. The compound strategy would transform Lyra's per-invocation cost structure, amortizing expensive model calls across the fleet's lifetime.

---

### Bitter Lesson of Diffusion LMs

**URL:** [arXiv:2601.12979](https://arxiv.org/pdf/2601.12979)

**Core Mechanism (step-by-step):**

This paper is a **negative result** that evaluates Diffusion-based LLMs (dLLMs: Llada-8B, Dream-7B, FdLLM-7B, DVar-8B) as agentic backbones vs autoregressive LLMs (Qwen-8B, Ministral-8B). Despite dLLMs' promise of **parallel decoding** and higher throughput, they fail catastrophically in agentic settings.

Two agentic paradigms tested:
1. **Embodied Agents** (long-horizon planning): AlfWorld, ScienceWorld, BabyAI via ReAct-style prompting
2. **Tool-Calling Agents** (precise formatting): BFCL-v3

Three contributions:
1. First systematic study of dLLMs as agentic backbones
2. DiffuAgent: evaluation framework integrating dLLMs as 4 cognitive modules in multi-agent setting
3. Evidence that dLLMs are effective only in non-causal roles

**Results (real numbers):**

Embodied agents (average success rate across 3 environments):
- Qwen-8B: 45.0% success, 62.1% progress
- Ministral-8B: 31.8% success, 54.9% progress
- Llada-8B: 7.5% success, 16.4% progress
- Dream-7B: 3.4% success, 8.7% progress
- FdLLM-7B: 3.1% success, 8.9% progress
- DVar-8B: 2.0% success, 8.9% progress

Tool-calling (BFCL overall):
- Qwen-8B: 57.8%
- Ministral-8B: 39.5%
- Llada-8B: 19.4%
- Dream-7B: 13.6%
- FdLLM-7B: 15.0%
- DVar-8B: 28.0%

Failure modes:
- **Retry loops**: dLLMs exhibit significantly more frequent retry loops (3+ consecutive repetitive actions) than autoregressive LMs
- **JSON schema violations**: Diffusion noise causes imprecise tool invocations, hallucinated API parameters
- **Multi-turn tool calls (hallucination irrelevant)**: All dLLMs achieve 0% on irrelevant tool calls -- they cannot distinguish when NOT to call tools

However, dLLMs are effective in **non-causal roles** within multi-agent systems: memory summarization, redundant trajectory detection, relevant tool selection.

**Trade-offs:**
- Higher throughput (up to 167 tok/s for DVar vs 79 for Qwen) but 10-20x worse agentic success rates
- Parallel decoding gains cannot compensate for catastrophic reasoning failures
- Good for information aggregation tasks; bad for anything requiring temporal reasoning or precise formatting

**Design Rationale:**
- The paper's insight is that **efficiency and reasoning quality are orthogonal** for dLLMs
- Diffusion noise fundamentally undermines the causal precision needed for agentic behavior
- Non-causal roles (summarization, selection) align with dLLMs' strengths because these tasks don't require sequential causal reasoning

**Transferable Idea for Lyra:**
- **Do not use dLLMs as agentic backbones.** The throughput advantage is irrelevant if the agent fails on 90%+ of tasks.
- However, dLLMs may be useful as non-causal components: **memory summarization, tool selection filtering, trajectory deduplication** -- tasks where causal precision matters less than processing speed.
- The DiffuAgent evaluation framework (4 cognitive modules) could inform Lyra's module architecture -- separating causal planning components from non-causal information-flow components.

**Gap vs Baseline:**
- Lyra is not currently considering dLLMs, but this paper provides strong evidence to avoid them for decision-making roles. The lesson extends to any non-autoregressive architecture being considered for Lyra's agent backbones.

---

## §3.21 Planning & Reasoning

---

### RAP

**URL:** [arXiv:2305.14992](https://arxiv.org/pdf/2305.14992) (EMNLP 2023)

**Core Mechanism (step-by-step):**

RAP (Reasoning with Language Model is Planning with World Model) repurposes a **single LLM in two roles simultaneously**:
1. **World Model** -- predicts future states and outcomes of reasoning steps
2. **Reasoning Agent** -- takes actions and builds the reasoning trajectory

These are combined via **Monte Carlo Tree Search (MCTS)**. The LLM-as-world-model is prompted to generate possible next states given current state and action. The LLM-as-agent proposes candidate actions. MCTS combines these to explore the reasoning tree, balancing exploration vs exploitation via UCB-style criteria.

The tree search discovers high-reward reasoning paths by:
- **Selection**: Navigate tree using UCB scores
- **Expansion**: LLM-as-world-model proposes multiple possible next states
- **Simulation/Rollout**: Sample trajectories from frontier nodes
- **Backpropagation**: Update value estimates up the tree

State evaluation uses the LLM-as-world-model to judge whether a partial solution is promising, combined with task-specific reward signals.

**Results (real numbers):**

Plan generation:
- RAP on LLAMA-33B **surpasses CoT on GPT-4** with 33% relative improvement

Math reasoning and logical inference: "superiority over various strong baselines, including CoT and least-to-most prompting with self-consistency."

**Trade-offs:**
- World model fidelity is bounded by base LLM capabilities -- if the LLM cannot simulate plausible future states, tree search degrades
- MCTS adds significant inference-time compute: each step requires multiple LLM calls for world model, agent, and evaluation
- The dual role (world model + agent) means the same LLM biases both prediction and action

**Design Rationale:**
- LLMs fundamentally lack an internal world model for simulating action consequences
- Human-like deliberate planning requires exploring alternatives, anticipating consequences, and iteratively refining steps
- MCTS is chosen because it provides principled exploration-exploitation trade-offs without requiring a separate trained policy/value network

**Transferable Idea for Lyra (4.20 Planning):**
- The **LLM-as-world-model** concept is directly applicable to Lyra: the planner can simulate the outcome of sub-agent actions before executing them, using the same LLM as both planner and simulator
- This enables **lookahead planning** without separate trained components
- The MCTS-with-LLM framework can be applied to Lyra's workflow planning (which sub-agents to invoke, in which order)

**Gap vs Baseline:**
- Lyra has **no planning** -- it executes tasks reactively. RAP's MCTS+world-model approach enables proactive plan-space exploration.

---

### Tree of Thoughts

**URL:** [arXiv:2305.10601](https://arxiv.org/abs/2305.10601) (NeurIPS 2023)

**Core Mechanism (step-by-step):**

ToT reframes LLM problem-solving as **tree search over thoughts** (coherent text units serving as intermediate steps) rather than left-to-right token generation. Four components:

1. **Thought decomposition**: Breaking problems into intermediate steps. Granularity is a deliberate trade-off: "small enough for diverse generation, big enough for meaningful evaluation."

2. **Thought generation** (two strategies):
   - (a) Sample i.i.d. from CoT prompt: for rich/creative spaces (paragraphs)
   - (b) Sequential propose prompt: for constrained spaces (equations, words) -- avoids duplication

3. **State evaluation** (two strategies):
   - (a) Value independently: prompt LLM to rate state as sure/likely/impossible via lookahead
   - (b) Vote across states: comparative vote prompt for harder-to-value states (coherency)

4. **Search algorithms**:
   - **BFS** (Algorithm 1): Keep top-b states per step. For Game of 24 and Creative Writing.
   - **DFS** (Algorithm 2): Explore most promising state first; prune subtrees below threshold; backtrack on failure. For Crosswords.

Conceptual contributions:
- IO, CoT, CoT-SC are all **special cases** of ToT (trees of limited depth and breadth)
- Modular: decomposition, generation, evaluation, search are independently variable
- No extra training needed

**Results (real numbers):**

Game of 24 (100 hard games):
- IO: 7.3% | CoT: 4.0% | CoT-SC (k=100): 9.0% | **ToT (b=5): 74%**
- ToT (b=1): 45% -- breadth matters
- IO best-of-100: 33% | CoT best-of-100: 49% -- exploring more nodes vs more samples

Creative Writing (GPT-4 coherency score 1-10):
- IO: 6.19 | CoT: 6.93 | **ToT: 7.56** | ToT + Refine: 7.91
- Human preference: ToT preferred over CoT 41:21 (38 tie)

Mini Crosswords (5x5):
- IO: 38.7% letter / 14% word / 0 game solved
- CoT: 40.6% / 15.6% / 1 game
- **ToT: 78% / 60% / 4 games**

GSM8K and StrategyQA (marginal gains):
- ToT achieves 90% on GSM8K (CoT: 86%) and 83% on StrategyQA (CoT: 82%) -- marginal because CoT already works well

GPT-3.5 experiments:
- GPT-4 gen + GPT-3.5 eval: 64% Game of 24 -- generation is the bottleneck
- GPT-3.5 gen + GPT-4 eval: 31% -- confirms bottleneck

Cost: ToT ~$0.74/case for Game of 24 vs $0.13 (IO) and $0.47 (CoT best-of-100). Creative Writing: ~$0.32/case vs $0.06-0.07.

**Trade-offs:**
- **Cost vs performance**: 5-100x more generated tokens than CoT but dramatic quality gains on hard tasks
- **Depth vs breadth**: BFS b=5 (74%) dramatically outperforms b=1 (45%), but costs more per task
- **Generation quality is the bottleneck** (GPT-4 gen + GPT-3.5 eval better than reverse on Game of 24)
- **Pruning can eliminate viable paths**: in Crosswords, pruning improves word accuracy (60% vs 41.5%) but can incorrectly prune solvable states (obscure vocab)
- **Not beneficial for tasks CoT already masters**: GSM8K (+4%) and StrategyQA (+1%)
- **Limited to three relatively simple tasks** in original paper

**Design Rationale:**
- Token-level autoregressive decoding is "System 1" cognition; needs deliberate "System 2" augmentation
- Heuristic-guided search (via LLM self-evaluation) is novel -- search heuristics are usually programmed or learned, never instantiated via language

**Transferable Idea for Lyra (4.20 Planning):**
- ToT's BFS/DFS over thoughts maps to **Lyra's multi-agent workflow planning**: each thought is a sub-agent invocation, each tree state is a partial execution trace
- The **vote mechanism** (compare multiple states, pick most promising) aligns with Lyra's multi-agent debate patterns
- The finding that **generation quality is the bottleneck** (not evaluation) informs Lyra's resource allocation: spend compute on generating diverse candidate plans, not on evaluating them
- The **"not necessary for easy tasks"** finding guides when to invoke tree search vs simple execution

**Gap vs Baseline:**
- Lyra has **no tree search across sub-agent invocations**. Its current sequential planning is equivalent to a depth-1, breadth-1 ToT -- the worst-performing configuration. Adding BFS/DFS over sub-agent choices would be the most impactful single change.

---

### SWE-Search

**URL:** [ICLR 2025 proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/file/a1e6783e4d739196cad3336f12d402bf-Paper-Conference.pdf)

**Core Mechanism (step-by-step):**

SWE-Search is a multi-agent framework integrating **MCTS with self-improvement** for repository-level software engineering tasks. Four components:

1. **Action Agent (SWE-Agent):** Modified from moatless-tools with flexible state space. Actions: Search, Plan, Edit, and crucially, **run arbitrary tests**. The Plan state can transition to ANY state (not just Edit), enabling flexible backtracking. Each action creates a git-like commit for state restoration.

2. **Value Agent (LLM-based):** Dual output:
   - `vn`: scalar utility estimate
   - `epsilon`: natural language explanation (hindsight feedback)
   Input includes the full trajectory history, enabling context-aware evaluation. Value function accuracy: 73% in solution evaluation.

3. **Search Algorithm (Modified MCTS):** Custom UCT variant with three terms:
   - `exploitation = V(s,a)`
   - `exploration = C * sqrt(ln N(s) / N(s,a))` (standard UCT)
   - `early depth bonus = alpha * e^(-beta*(d-1))` -- encourages wide exploration in early steps
   - `late depth penalty = gamma * sqrt(d)` -- discourages over-exploration deep in tree
   Node abandonment heuristic: drop nodes with consecutive low rewards.

4. **Discriminator Agent:** Multi-agent debate over up to 5 candidate solutions. Each agent argues for/against solutions; a judge selects the best. Improves selection accuracy from 73% (value function alone) to 84%.

**Results (real numbers):**

SWE-bench Lite (300 instances), 5 models:

| Model | Moatless-Adapted | SWE-Search | % Improvement |
|---|---|---|---|
| GPT-4o | 25.7% | 31.0% | +17% |
| GPT-4o-mini | 13.0% | 17.0% | +24% |
| Qwen-2.5-72B-Instruct | 18.0% | 24.7% | +27% |
| DeepSeek-V2.5 | 16.3% | 21.0% | +22% |
| Llama-3.1-70B-Instruct | 13.6% | 17.7% | +23% |
| **Mean** | **17.3%** | **22.3%** | **+23%** |

SWE-Search + Qwen-2.5-72B (24.7%) exceeds GPT-4o + original Moatless (24.3%), enabling open-source models to surpass closed-source.

Performance scales with search depth: resolved issues increase from ~0 at 0 transitions to 20-30 at 100 transitions (varies by model). No saturation observed -- deeper search continues to yield improvements.

Key factor: hindsight feedback from Value Agent (epsilon) drives action diversity. Without it, re-expansion from parent nodes produces very similar actions.

**Trade-offs:**
- Limits: 3 expansions per node, 100 total search iterations -- empirical choices
- Discriminator improves selection (73% → 84%) but adds cost
- Flexible state transitions (Plan→any) introduce risk of infinite loops without MCTS-level control
- Test-execution access is powerful but requires environment setup for each state
- Only tested on SWE-bench Lite; generalization to broader SE tasks unverified

**Design Rationale:**
- MCTS chosen over BFS/DFS because it balances exploration and exploitation without exhaustive search
- LLM-based value function provides both quantitative scores and qualitative feedback (dual output) -- the qualitative feedback is critical for driving diverse re-expansion
- Multi-agent debate for final selection mirrors real engineering collaboration

**Transferable Idea for Lyra (4.20 Planning):**
- The **modified UCT with depth bonus/penalty** is directly applicable to Lyra's sub-agent planning: early in the planning process, explore widely (bonus); deep in a branch, exploit narrow paths (penalty)
- The **dual-output value function** (score + explanation) is a pattern Lyra should adopt: the explanation feeds back into the planning loop, creating self-improving search trajectories
- The **hindsight feedback mechanism** -- using value function explanations to guide node re-expansion -- is Lyra's most directly transferable concept: when a value function identifies an issue, its explanation informs the next attempt
- The **23% relative improvement** figure provides a concrete expectation for Lyra: adding MCTS-based planning to existing agents yields ~20% gains

**Gap vs Baseline:**
- Lyra's current agents execute linear sequences without backtracking. SWE-Search's MCTS with flexible state transitions and hindsight feedback would transform Lyra's error recovery and plan adaptation.

---

### AFlow

**URL:** [arXiv:2410.10762](https://arxiv.org/abs/2410.10762) (ICLR 2025)

**Core Mechanism (step-by-step):**

AFlow reformulates **workflow optimization as a search problem over code-represented workflows**. Each workflow is a DAG of LLM-invoking nodes connected by code edges. MCTS searches this space to find optimal workflows.

Key concepts:
- **Node N**: LLM invocation with parameters (model M, temperature tau, prompt P, output format F)
- **Edge E**: Code representing execution order (supports linear, conditional, loops, parallelism)
- **Operator O**: Predefined reusable node combinations (Generate, Ensemble, Review&Revise, Programmer, Test, Format, Custom)
- **Search space**: S = {(P1,...,Pn, E, O1,...,On) | Pi in P, E in E, Oi in O}

MCTS variant (iterative cycle):
1. **Selection**: Soft mixed-probability strategy combining uniform and score-weighted distributions:
   `P_mixed(i) = lambda * 1/n + (1-lambda) * exp(alpha*(si-smax)) / sum(exp(alpha*(sj-smax)))`
   where lambda=0.2 balances exploration/exploitation, alpha=0.4 controls score influence
2. **Expansion**: LLM-as-optimizer modifies selected workflow (change prompts, add/remove operators, modify code edges), guided by past experience and previous modifications' outcomes
3. **Evaluation**: Execute workflow 5 times on validation set, compute mean and std
4. **Backpropagation**: Store (performance, modification, success flag) in experience tree
5. **Termination**: Early stop if top-k average score shows no improvement for n consecutive rounds; max Nmax=20 rounds

Each tree node represents a **complete workflow** (not individual LLM-invoking nodes) -- enabling discovery of universal solutions for problem classes.

**Results (real numbers):**

Main results (GPT-4o-mini executor, all 6 benchmarks):

| Method | HotpotQA | DROP | HumanEval | MBPP | GSM8K | MATH | Avg |
|---|---|---|---|---|---|---|---|
| IO | 68.1 | 68.3 | 87.0 | 71.8 | 92.7 | 48.6 | 72.8 |
| CoT | 67.9 | 78.5 | 88.6 | 71.8 | 92.4 | 48.8 | 74.7 |
| CoT-SC (5) | 68.9 | 78.8 | 91.6 | 73.6 | 92.7 | 50.4 | 76.0 |
| MedPrompt | 68.3 | 78.0 | 91.6 | 73.6 | 90.0 | 50.0 | 75.3 |
| MultiPersona | 69.2 | 74.4 | 89.3 | 73.6 | 92.8 | 50.8 | 75.1 |
| Self-Refine | 60.8 | 70.2 | 87.8 | 69.8 | 89.6 | 46.1 | 70.7 |
| ADAS (auto) | 64.5 | 76.6 | 82.4 | 53.4 | 90.8 | 35.4 | 67.2 |
| **AFlow** | **73.5** | **80.6** | **94.7** | **83.4** | **93.5** | **56.2** | **80.3** |

AFlow outperforms all manual methods (+5.7% avg) and ADAS (+19.5%). On MATH (hardest), AFlow beats ADAS by **57% relative** (56.2 vs 35.4).

Transferability: AFlow-discovered workflow (using GPT-4o-mini) improves all target models:
- GPT-4o-mini: +7.7% on HumanEval (87→94.7)
- DeepSeek-V2.5: +5.3% (88.6→93.9)
- GPT-4o: +2.3% (93.9→96.2) -- even frontier models benefit
- Claude-3.5-sonnet: +4.6% (90.8→95.4)

Cross-model transfer: workflow found with DeepSeek-V2.5 underperforms on GPT-4o-mini (90.8 vs 94.7) -- different models need different workflows.

Cost: AFlow enables GPT-4o-mini to match/exceed GPT-4o on the Pareto frontier (cost vs performance). For example, on HumanEval: GPT-4o-mini + AFlow (94.7% at ~$0.05) beats GPT-4o direct (93.9% at ~$0.20).

Ablation: Operators help discover better workflows faster, but AFlow **without operators still achieves 93.1%** on GSM8K. The system autonomously develops ensemble-like structures, proving operators are not essential.

**Trade-offs:**
- Each iteration costs 5 validation set executions → significant total cost
- Single-step modification per iteration limits discovery speed
- Valid only for tasks with numerical evaluation functions
- Models need different workflows (no one-size-fits-all)
- Max 20 iterations may be insufficient for complex domains

**Design Rationale:**
- Code representation chosen over graphs for expressivity (supports loops, conditions, parallelism)
- LLM-as-optimizer avoids task-specific heuristic design
- Tree-structured experience preserves exploration history for efficient reuse
- Soft mixed selection (including blank template) avoids local optima

**Transferable Idea for Lyra (4.20 Planning):**
- Lyra should adopt **code-represented workflow graphs** for its agent pipelines. Each sub-agent invocation is a node; edges are programmatic control flow (conditionals, loops, parallelism).
- The **soft-mixed selection** mechanism is directly applicable to Lyra's workflow planner: maintain a tree of candidate workflows, explore via score-weighted + uniform mix.
- The **AFlow-as-optimizer pattern** (LLM modifies workflows over multiple iterations) enables Lyra to auto-evolve its agentic pipelines from execution feedback, without manual workflow design.
- The **cost Pareto result** (weaker model + optimized workflow beats stronger model alone) provides a concrete target: Lyra's SubAgent fleet can deploy cheaper models with optimized workflows to match expensive-model quality.

**Gap vs Baseline:**
- Lyra's agentic workflows are currently **manually designed and static**. AFlow would enable Lyra to **automatically discover and optimize** its own agent invocation patterns from task execution traces.

---

### MC-DML

**URL:** [arXiv:2504.16855](https://arxiv.org/abs/2504.16855) (ICLR 2025)

**Core Mechanism (step-by-step):**

MC-DML (Monte Carlo planning with Dynamic Memory-guided Large language model) integrates LLMs with MCTS for **text-based game agents**. Key innovations:

1. **LLM as Prior Policy in MCTS**: Instead of a trained policy network, uses GPT-3.5-turbo to provide non-uniform action probability distributions within PUCT:
   `a* = argmax[Q(s,a) + Cpuct * LLM(a|Mi, Mc, p) * sqrt(N(s)) / (1+N(s,a))]`

2. **Dual Memory Mechanisms**:
   - **In-Trial Memory (Mi)**: Short-term trajectory of current simulation (recent observations and actions)
   - **Cross-Trial Memory (Mc)**: Episodic memory storing "reflections" from **past failed simulations** -- the LLM analyzes failure trajectories and produces critiques/suggestions

3. **Dynamic Pruning**: Search depth dynamically adjusted between d_min and d_max based on whether high-value nodes are found. Starts shallow; if max Q-value is 0, increases depth by delta_d.

Training data for LLM policy: zero-shot GPT-3.5-turbo with no game-specific fine-tuning. Cross-trial memory caches up to k=3 reflections per root node.

**Results (real numbers):**

Jericho benchmark (9 text-based games):

| Game | MC-DML | MC-LAVE-RL (prev SOTA) | Improvement |
|---|---|---|---|
| Zork1 (hard) | 48.7 | 42.6 | +14% |
| Deephome (hard) | 67 | 34 | **+97% (nearly double)** |
| Ludicorp (hard) | 21.3 | 22.3 | comparable |
| Pentari (possible) | **70 (max)** | 47.3 | completes game |
| Detective (possible) | **347 (max)** | 338 | completes game |
| Library (possible) | 23 | 22.3 | near max |

vs 10 baselines including DRRN, KG-A2C, PUCT-RL, MC-LAVE-RL, Reflection agent, vanilla LLM.

Ablation: removing cross-trial memory reduces game scores; removing both memories causes larger drops. LLM policy alone (no MCTS) performs poorly due to inability to balance exploration/exploitation.

**Trade-offs:**
- Requires GPT-3.5-turbo API calls for every MCTS node (costs scale with tree size)
- Cross-trial memory limited to 3 reflections -- may be insufficient for games with many bottleneck states
- Dynamic pruning heuristic (increase depth when no high-value nodes) may miss solutions requiring initially-low-value steps
- Only tested on text-based games; generalization to broader agent tasks is unverified

**Design Rationale:**
- Previous MCTS+RL approaches need warm-up periods (iterative planning-then-learning). MC-DML achieves strong results at the **initial planning phase** without multiple iterations.
- The dual-memory approach mimics human gameplay: in-trial memory for current game state, cross-trial memory for lessons from past mistakes
- LLM-as-policy provides commonsense priors that make search efficient in high-branching environments

**Transferable Idea for Lyra (4.20 Planning):**
- The **cross-trial memory** concept maps directly to Lyra's job-level planning: when a sub-agent plan fails, its failure trajectory is analyzed and the resulting "reflection" is stored as episodic memory for future plan selection
- The **LLM-as-prior-policy** in PUCT is a simpler alternative to trained value/policy networks: Lyra's planner can use the base LLM to propose action distributions at each planning node
- The **dynamic depth adjustment** (start shallow, deepen when stuck) is practically useful for Lyra's adaptive compute budgeting

**Gap vs Baseline:**
- Lyra has **no MCTS-based planning** and **no cross-episodic memory** for plan failures. MC-DML's dual-memory MCTS would enable Lyra to learn from failed execution trajectories.

---

### Agentic Reasoning

**URL:** [arXiv:2502.04644](https://arxiv.org/pdf/2502.04644)

**Core Mechanism (step-by-step):**

Agentic Reasoning enhances LLM reasoning by integrating **external tool-using agents** during the reasoning process. The reasoning LLM dynamically invokes specialized agents via embedded tokens in its reasoning sequence.

Three essential agents:
1. **Web-Search Agent**: Query breakdown → search service → re-ranking → RAG. Breaks original query into search-optimized sub-queries. Uses re-ranking model to score relevance; if below threshold, iterates on query refinement. Only passes high-relevance pages to RAG.

2. **Code Agent**: Delegates coding tasks to a specialized coding LLM. The reasoning model sends context+query; the coding agent writes code, executes it via compiler, returns natural-language results.

3. **Mind-Map Agent**: Knowledge graph constructed from the reasoning chain:
   - Graph-construction LLM extracts entities and semantic relationships (similar to GraphRAG)
   - Community clustering groups related reasoning context
   - LLM generates summaries for each community
   - Serves as (a) context provider for other agents, and (b) external memory for the reasoning model to query when uncertain

Integration: The reasoning LLM embeds special tokens (`<web-search>`, `<coding>`, `<mind-map>`) in its reasoning chain. When detected, reasoning halts, query + context are dispatched to the appropriate agent, and results are reintegrated.

**Results (real numbers):**

Humanity's Last Exam:
- DeepSeek-R1: 9.4%
- **Agentic Reasoning w/ R1: 23.8%** (+14.4 points, +153% relative improvement)
- OpenAI Deep Research (proprietary): 26.6% -- gap narrowed to just 2.8%
- Surpasses o3-mini (high): 13.0%, Perplexity Deep Research: 21.1%

GPQA:
- DeepSeek-R1: 86.8% (Physics) / 81.3% (Chemistry) / 76.9% (Biology) → Avg 81.7%
- Agentic Reasoning w/ R1: **89.8% / 88.3% / 80.5%** → Avg **86.2%** (+4.5%)

**Trade-offs:**
- Depends on DeepSeek-R1's built-in reasoning capabilities; gains may not transfer to weaker reasoning models
- Web-search quality is the primary bottleneck -- query refinement loop adds latency
- Mind-Map construction cost: graph extraction + community clustering + summarization adds overhead per reasoning chain
- Human evaluation was used (small sample size) but not quantified on standard benchmarks
- Not tested on code generation or math (where R1 already excels) -- complementary to existing reasoning strengths

**Design Rationale:**
- Reasoning models (R1, o1) excel at math/code but fail on knowledge-intensive tasks requiring external info
- The key insight: **delegate tool use to specialized agents during reasoning**, not as a separate retrieval step
- Mind-Map addresses the **long-chain coherence problem**: when reasoning spans many tool calls, the knowledge graph maintains logical structure

**Transferable Idea for Lyra (4.20 Planning):**
- The **reasoning-with-agent-tools** pattern is Lyra's core paradigm: what Agentic Reasoning demonstrates is that **even strong reasoning models benefit from agentic tool delegation**. Apply this to Lyra's planner: the planner reasons, and delegates information gathering, computation, and memory operations to sub-agents.
- The **Mind-Map** knowledge graph is directly applicable to Lyra's context engine: maintain a structured memory of the reasoning chain across multiple sub-agent invocations, with community clustering for efficient retrieval.
- The **+153% relative improvement** on HLE demonstrates the ceiling for Lyra's tool-augmented reasoning over raw LLM reasoning.

**Gap vs Baseline:**
- Lyra has **no structured reasoning chain memory** (Mind-Map equivalent). Its context engine accumulates linear context, losing cross-relationship structure.

---

### IterResearch

**URL:** [arXiv:2511.07327](https://arxiv.org/pdf/2511.07327) (ICLR 2026)

**Core Mechanism (step-by-step):**

IterResearch (Alibaba, ICLR 2026) addresses the fundamental limitation of **mono-contextual deep-research agents**: linear context accumulation causes "context suffocation" and "noise contamination." Their solution: an **MDP-inspired iterative paradigm** with workspace reconstruction.

MDP-inspired formulation: `⟨S, D, E, T, R⟩`
- **State st = (q, Mt, {a_{t-1}, TR_{t-1}})**: (1) constant question q; (2) evolving report Mt (compressed memory); (3) immediate context from previous step
- **Decision dt = [Think_t, M_{t+1}, a_t]**: internal thought, report update, external action
- **Transition T**: workspace reconstruction -- `s_{t+1} = (q, M_{t+1}, {a_t, TR_t})` -- discards history but preserves synthesized knowledge
- Key property: `|st| ≈ O(1)` vs mono-contextual `|s_mono_t| = O(t)` -- constant workspace size

Efficiency-Aware Policy Optimization (EAPO):
1. **Discounted reward shaping**: `rt = gamma^{T-t} * R_T` where gamma in (0,1), T is terminal step. Creates implicit efficiency pressure: shorter successful trajectories get higher rewards.
2. **Adaptive downsampling**: Reduces training corpus to largest multiple of data-parallel size. Each trajectory naturally decomposes into T independent training samples (one per round). Multiple rounds per trajectory → much richer training signal than mono-contextual (1 sample/traj).
3. Implemented on Group Sequence Policy Optimization (GSPO).

**Results (real numbers):**

IterResearch-30B-A3B vs open-source agents (6 benchmarks):

| Benchmark | Best Open-Source | IterResearch | Improvement |
|---|---|---|---|
| HLE | 20.0% (MiroThinker-14B) | **28.8%** | +8.8pp |
| BrowseComp | 17.2% (MiroThinker-32B) | **37.3%** | +20.1pp |
| BrowseComp-zh | 29.4% (MiroThinker-32B) | **45.2%** | +15.8pp |
| GAIA | 64.1% (MiroThinker-32B) | **72.8%** | +8.7pp |
| Xbench-DeepSearch | 56.0% (MiroThinker-32B) | **71.0%** | +15.0pp |
| SEAL-0 | 36.0% | **39.6%** | +18.9pp |
| **Average** | baseline dependent | **--** | **+14.5pp** |

vs proprietary:
- Surpasses OpenAI DeepResearch on HLE (28.8 vs 26.6) and BrowseComp-zh (45.2 vs 42.9)
- Comparable to Perplexity Research and Grok3-ResearchSearch on several benchmarks

Interaction scaling (critical finding):
- Extends to **2048 interactions** with only 40K context length
- Performance: 3.5% (2 interactions) → 42.5% (2048 interactions) on BrowseComp
- Perceived task difficulty drops with exploration capacity -- many hard tasks become solvable with enough search iterations

Cross-paradigm knowledge transfer:
- Trajectories from IterResearch **significantly enhance mono-contextual agents** -- the iterative paradigm induces superior exploration behaviors
- Provides a **model-agnostic prompting strategy**: applying IterResearch's iterative approach to frontier models (no training) yields +12.7-19.2pp over ReAct on BrowseComp

Ablation: EAPO (full) > GSPO (without efficiency pressure) > SFT (no RL), confirming the benefit of efficiency-aware training.

**Trade-offs:**
- Average 14.5pp improvement is significant but still trails proprietary systems on some metrics
- Workspace reconstruction depends on reliable report synthesis -- if the agent generates poor summaries, information is lost
- EAPO's geometric discounting may discourage beneficial long exploratory trajectories when early search is noisy
- Requires two-stage training (RFT + RL) which is compute-intensive

**Design Rationale:**
- The mono-contextual paradigm has a **fundamental scaling ceiling**: context grows linearly, so reasoning quality degrades at longer horizons
- Workspace reconstruction is designed as **strategic forgetting**: discard raw history, preserve synthesized knowledge
- The MDP formulation ensures **state independence**: decisions depend only on current reconstructed workspace, not on entire history
- EAPO addresses the unique training challenge of iterative paradigms: each round is an independent training sample, and efficient trajectories should be preferred

**Transferable Idea for Lyra (4.20 Planning, 4.21 Economics):**
- IterResearch's **workspace reconstruction** is Lyra's most directly applicable concept: instead of accumulating all sub-agent outputs in a growing context, Lyra's planner should periodically synthesize an "evolving report" -- a compressed state containing only essential information.
- The **2048-interaction scaling** demonstrates that with proper architecture, agents can sustain reasoning quality across arbitrarily long execution traces -- directly relevant to Lyra's long-horizon tasks.
- The **EAPO efficiency pressure** (discount longer trajectories) is a concrete mechanism for Lyra's cost-aware optimization: reward sub-agent plans that reach correct conclusions with fewer invocations.
- The **model-agnostic prompting** finding means Lyra can deploy IterResearch's pattern without training -- just restructure the planner's context management.

**Gap vs Baseline:**
- Lyra uses **linear context accumulation** (mono-contextual). This paper demonstrates this is architecturally suboptimal: context suffocation and noise contamination are structural, not incidental.
- Lyra has **no report synthesis**, **no workspace reconstruction**, and **no efficiency-aware training** for its long-horizon agents. These gaps explain why Lyra's agents degrade on long tasks.

---

## §3.22 Cost & Latency Economics

---

### Speculative Decoding

**URL:** [arXiv:2211.17192](https://arxiv.org/abs/2211.17192) (ICML 2023)

**Core Mechanism (step-by-step):**

Speculative decoding accelerates autoregressive model inference by **generating multiple tokens in parallel** using a cheap approximation model, then verifying with the target model -- without changing the output distribution.

Algorithm (SpeculativeDecodingStep):
1. **Propose**: Sample gamma candidate tokens x_1,...,x_gamma from approximation model M_q autoregressively
2. **Verify**: Run target model M_p in parallel on all gamma+1 prefixes to get distributions p_1,...,p_{gamma+1}
3. **Accept/Reject**: For each i, accept token x_i with probability min(1, p_i(x_i) / q_i(x_i)). If rejected, sample from adjusted distribution `p'(x) = norm(max(0, p(x) - q(x)))`.
4. **Output**: Generate 1 to gamma+1 tokens per target-model run.

Theoretical guarantees:
- **Output distribution is identical** to target model alone (proved via rejection sampling on adjusted distributions)
- Expected tokens per iteration (i.i.d. assumption): `E[#tokens] = (1 - alpha^{gamma+1}) / (1 - alpha)` where alpha = E[beta] and beta = acceptance rate
- Expected walltime improvement: `(1 - alpha^{gamma+1}) / ((1-alpha)(gamma*c + 1))` where c = cost_ratio of M_q:M_p
- Upper bound on speedup: `1 / (1-alpha)` as gamma → infinity

Choosing gamma: optimal integer maximizes walltime equation, found numerically. For c=0.01-0.05, optimal gamma grows from ~3 (alpha=0.6) to ~10+ (alpha=0.9).

**Results (real numbers):**

T5-XXL (11B) on WMT En-De translation:
- T5-small (77M) as M_q: 3.4x speedup (temp=0), 2.6x speedup (temp=1)
- T5-base (250M): 2.8x speedup (temp=0), 2.4x speedup (temp=1)
- T5-large (800M): 1.7x speedup (temp=0), 1.4x speedup (temp=1) -- larger M_q has higher alpha but also higher c, reducing net speedup

T5-XXL on CNN/DM summarization:
- T5-small: 3.1x speedup (temp=0), 2.3x speedup (temp=1)
- T5-base: 3.0x speedup (temp=0), 2.2x speedup (temp=1)
- T5-large: 2.2x speedup (temp=0), 1.7x speedup (temp=1)

Alpha values (acceptance rates):
- T5-XXL + T5-small: alpha=0.62-0.75 (varies by task/temp)
- T5-XXL + T5-base: alpha=0.68-0.80
- T5-XXL + T5-large: alpha=0.71-0.82
- Even trivial n-gram models achieve non-zero alpha: bigram on translation gets alpha=0.20, yielding 1.25x speedup with c≈0
- GPT-like (97M) + 6M model: alpha=0.88-0.89

LaMDA 137B + LaMDA 8B: alpha not directly reported but "between 0.5-0.9" for models 2 orders of magnitude smaller.

Caveat on arithmetic operations: total operations may increase (gamma+1 parallel target runs per iteration), but total **memory accesses decrease** since weights and KV cache are read once per iteration.

**Trade-offs:**
- Requires sufficient memory bandwidth to run gamma+1 target model evaluations in parallel
- Approximation model quality determines alpha; alpha of 0.5-0.9 needed for meaningful gains
- The approximation model must be fast enough (c << 1) or slower alpha improvement may not compensate for its cost
- Identical output guarantee holds only for sampling -- argmax (temp=0) has even higher alpha but is less interesting for stochastic tasks
- Optimal gamma depends on both alpha and c, both of which vary during generation

**Design Rationale:**
- The key observation: "hard language-modeling tasks often include easier subtasks that can be approximated well by more efficient models"
- Inference from large models is bottlenecked on memory bandwidth, not arithmetic -- extra compute is available
- Speculative execution (common in processors) generalized to the stochastic setting

**Transferable Idea for Lyra (4.21 Economics):**
- Speculative decoding is directly applicable to **Lyra's sub-agent generation**: for any LLM call in the agent fleet, a cheap approximation model proposes tokens, and the target model verifies in parallel. This requires no training and preserves output distribution.
- The **2-3x speedup** translates directly to cost savings (same output quality, less walltime).
- The **n-gram approximation model** finding is particularly relevant: Lyra's verification and formatting sub-agents often generate predictable tokens (boilerplate, structured output), where simple n-gram approximations can achieve alpha=0.2-0.5.
- The **memory bandwidth bottleneck** applies to Lyra's GPU-enabled inference: speculative decoding exploits available compute at no quality cost.

**Gap vs Baseline:**
- Lyra uses standard autoregressive decoding. Speculative decoding would provide **distribution-identical acceleration** with zero quality degradation.

---

### Cost-Augmented MCTS

**URL:** [arXiv:2505.14656](https://arxiv.org/abs/2505.14656)

**Core Mechanism (step-by-step):**

This paper systematically studies whether tree-search LLM planners (ToT-BFS, ToT-DFS, MCTS, Bidirectional Search) are **cost-aware** -- do they account for heterogeneous action costs and budget constraints?

The testbed is **Budget-BlocksWorld** (1,008 tasks with 6 blocks, non-uniform action costs). Action costs are heterogeneous (pick-up/put-down cost more than stack/unstack). Three budget regimes: TIGHT (cost = optimal), LOOSE (optimal + margin), UNLIMITED (any valid plan).

Reward design (adapted from RAP):
1. **Action evaluation**: LLM predicts best next action given current state, action set, budget, accumulated cost. Log-probability of actual action = confidence reward.
2. **Self-evaluation**: LLM assesses whether action is "good" or "bad" given budget. Log-probability of "good" = self-evaluation signal.
Final node reward = action_confidence + self_evaluation confidence.

**Results (real numbers):**

Success rate comparison (average across all plan lengths):

| Method | UNLIMITED | LOOSE | TIGHT |
|---|---|---|---|
| CoT w/ Claude | 0.36 | 0.36 | 0.36 |
| ToT-BFS | 0.17 | 0.17 | 0.17 |
| ToT-DFS | 0.21 | 0.21 | 0.21 |
| **MCTS** | **0.43** | **0.43** | **0.43** |
| **Bi-Search** | **0.45** | **0.45** | **0.45** |

Optimality (how close to min-cost plan):
- MCTS: 0.83 optimality (best on short-horizon, L=2-4)
- Bi-Search: 0.83-1.00 optimality (best on long-horizon, L=8+)
- All CoT variants: 0.33-1.00 optimality (varies by model)

Key findings:
1. **Tree-search LLM planners struggle to identify cost-optimal plans** -- even MCTS and Bi-Search only achieve ~0.83 optimality
2. **Increasing search compute does NOT reliably improve optimality** -- more node expansions don't translate to better cost solutions
3. **Bidirectional search is most efficient** -- achieves highest success rate on long-horizon tasks with fewer node expansions

Model comparison (CoT with different backbones): Claude matches/exceeds GPT-4.1 and Qwen3 on budget-aware planning (0.36 vs 0.08 vs 0.11 success rate on TIGHT/hard).

**Trade-offs:**
- Bidirectional search requires reverse transitions from goal state -- not always available
- MCTS achieves highest optimality on short tasks but degrades on long horizons
- Current reward design (log-probability based) may not sufficiently penalize cost violations
- The uniform action-cost assumption in most LLM planners is a significant practical limitation

**Design Rationale:**
- Prior work focuses on planning completeness (can the agent find any feasible plan?) but ignores optimality under constraints
- Cost-aware planning is essential for real-world deployment (budget, energy, time constraints)
- Tree-search planners are chosen because their explicit intermediate decisions enable controlled study of cost-awareness

**Transferable Idea for Lyra (4.21 Economics):**
- The finding that **"increasing search compute doesn't reliably improve optimality"** is a caution for Lyra: more exhaustive planning doesn't automatically yield cost-optimal solutions. Need principled cost-aware search, not just more compute.
- **Bidirectional search** (grow trees from initial and goal states, meet in middle) is directly applicable to Lyra's plan-space exploration, particularly for tasks with known goal states (verification, test generation).
- The **Budget-BlocksWorld** framework provides a template for Lyra's own cost-aware planning benchmarks: define action costs, budget constraints, and optimality metrics.
- The **negative result** that ToT-BFS/DFS perform worse than CoT on budget-aware tasks (0.17 vs 0.36 success) is important: naive tree search can hurt cost-awareness. Lyra's tree search must be cost-augmented.

**Gap vs Baseline:**
- Lyra's planning assumes **uniform action costs** -- all sub-agent invocations are equally treated. This paper shows this assumption limits cost-optimality. Lyra needs cost-augmented search that accounts for heterogeneous sub-agent costs.

---

## §3.15 Reliability & Observability

---

### Langfuse

**URL:** [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)

**Core Mechanism:**

Langfuse is an open-source LLM engineering platform for **trace-based observability**, built on ClickHouse. Core features:

1. **Tracing**: OpenTelemetry-based instrumentation of LLM calls, retrieval, embedding, and agent actions. Captures execution traces with timing, token usage, and model metadata.

2. **Prompt Management**: Centralized, version-controlled prompts with strong client/server-side caching (zero latency impact in production).

3. **Evaluations**: Supports LLM-as-judge, code evaluators, user feedback, manual labeling, and custom pipelines. Integrated with LangChain, LlamaIndex.

4. **Datasets**: Versioned test sets for continuous improvement, pre-deployment testing, structured experiments.

5. **LLM Playground**: Test prompts directly from tracing UI -- when a bad result is found, immediately iterate on it.

6. **API**: OpenAPI spec, Python/JS/TS SDKs, Postman collection.

Deployment: Docker self-hosted (minutes) or managed cloud. MIT license. Y Combinator W23.

**Transferable Idea for Lyra (4.16 Observability):**
- Langfuse's **trace-based debugging** pattern (inspect complex agent logs and user sessions) is the baseline for Lyra's observability layer
- The **prompt management with caching** is a component Lyra should adopt: versioned prompts with zero-latency serving
- The **evaluation suite** (LLM-as-judge + code evaluators + user feedback) provides a template for Lyra's quality monitoring

---

### OpenLLMetry

**URL:** [github.com/traceloop/openllmetry](https://github.com/traceloop/openllmetry)

**Core Mechanism:**

OpenLLMetry is an **OpenTelemetry-based observability** framework for LLM applications. It provides auto-instrumentation for popular LLM frameworks (OpenAI, Anthropic, Hugging Face, LangChain, LlamaIndex) and sends traces to any OpenTelemetry-compatible backend.

Key features:
- Auto-instrumentation of LLM calls: captures prompts, completions, token counts, latency
- Support for vector DBs, embeddings, and other RAG components
- Pluggable exporters: send to Datadog, New Relic, Grafana, or any OTel backend
- Distributed tracing across microservices

**Transferable Idea for Lyra (4.16 Observability):**
- OpenLLMetry's **auto-instrumentation pattern** is what Lyra needs: instrument the agent framework once, and all sub-agent invocations are automatically traced. No manual instrumentation per agent.
- The **OpenTelemetry standard** ensures vendor-neutral observability. Lyra should emit OTel spans for every sub-agent invocation, routing decision, and tool call.
- The **pluggable exporter** model means Lyra's observability layer is backend-agnostic.

---

### Phoenix (Arize AI)

**URL:** [github.com/Arize-ai/phoenix](https://github.com/Arize-ai/phoenix)

**Core Mechanism:**

Phoenix is an open-source AI observability platform built on **OpenTelemetry**. It provides:

1. **Tracing**: Runtime instrumentation using OpenInference (Arize's OTel extension). Supports OpenAI Agents SDK, Claude Agent SDK, LangGraph, Vercel AI SDK, Mastra, CrewAI, LlamaIndex, DSPy, and all major LLM providers.

2. **Evaluation**: LLM-based evals for response quality, retrieval relevance, and custom metrics. Python and TypeScript evaluation libraries.

3. **Datasets & Experiments**: Versioned datasets for experimentation, evaluation, and fine-tuning. Track changes to prompts, LLMs, and retrieval.

4. **Playground**: Optimize prompts, compare models, replay traced LLM calls.

5. **Prompt Management**: Version control, tagging, experimentation.

6. **MCP Server**: New (2025) MCP server implementation providing unified interface to Phoenix capabilities via the Model Context Protocol.

Deployment: pip install, Docker, Kubernetes, or managed cloud (app.phoenix.arize.com).

**Transferable Idea for Lyra (4.16 Observability):**
- Phoenix's **MCP server** is directly relevant: Lyra could use it to expose observability data to agents via standard MCP interfaces
- The **OpenInference** standard is the most mature OTel extension for LLM/agent traces. Lyra should adopt OpenInference span conventions.
- The **experiments tracking** (versioned datasets for measuring prompt/model changes) is a template for Lyra's A/B testing of routing decisions and planning strategies.
- Phoenix's native support for **Claude Agent SDK** tracing means Lyra's Anthropic-based agents are already instrumentable.

---

### Tau-Bench / Tau2-Bench

**URLs:** [github.com/sierra-research/tau-bench](https://github.com/sierra-research/tau-bench), [github.com/sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench), [arXiv:2406.12045](https://arxiv.org/abs/2406.12045), [arXiv:2506.07982](https://arxiv.org/abs/2506.07982)

**Core Mechanism (tau-bench):**

Tau-bench measures agent reliability in **tool-agent-user interaction** -- dynamic conversations between LM-simulated users and tool-using agents. Each task is a POMDP with databases (tool-accessible), domain-specific policy documents, and user instructions.

Evaluation: Compare final database state against ground-truth annotated state. Reward `r = r_action × r_output` where both action correctness and information completeness must be satisfied.

Key metric: **pass^k** (pass hat k) = fraction of tasks where ALL k i.i.d. trials succeed. Measures consistency, not just best-case performance.

Domains: retail (order returns, exchanges, refunds) and airline (flight changes, cancellations, rebooking). User simulated by gpt-4-0613.

**Core Mechanism (tau2-bench):**

Tau2-bench introduces **dual-control** (Dec-POMDP) where both agent and user have tools that modify a shared environment. The new telecom domain: agent has CRM tools, user has phone-status tools (airplane mode, data toggle). Tests both reasoning and coordination/communication.

Compositional task generator: programmatically creates diverse, verifiable tasks from atomic base scenarios. Enables controlled complexity and provable correctness.

Fine-grained diagnosis: separate "no-user mode" (agent controls all tools, isolates reasoning) from "dual-control mode" (adds communication/coordination). Enables decomposed error analysis.

**Results:**

Tau-bench (pass^1, best agent TC claude-3.5-sonnet):
- Airline: 46.0% | Retail: 69.2%
- Even best agents fail on >50% of tasks (airline)
- gpt-4o TC: Airline 42.0%, Retail 60.4%
- pass^8 drops to <25% in retail for gpt-4o -- severe inconsistency

Tau2-bench (dual-control telecom, pass^1):
- claude-3.7-sonnet: 49% | o4-mini: 42% | gpt-4.1: 34%
- **Significant performance drops from no-user to dual-control** (~20% pass^1 drop) -- coordination/communication is the bottleneck
- User simulator reliability: telecom domain 16% error rate (6% critical) vs baseline retail 40% error rate (12% critical)

**Trade-offs:**
- User simulation fidelity vs cost: LM-simulated users are scalable but may miss human interaction nuances
- The pass^k metric is expensive (k trials per task) but provides essential consistency signal
- Dual-control adds realism but makes task specification more complex
- Tau2-bench's Dec-POMDP formalism is powerful but requires careful tool design for both agent and user

**Design Rationale:**
- Real-world deployment requires reliability at scale (millions of interactions), not just one-shot accuracy
- Database-state evaluation is efficient and faithful -- avoids expensive LLM-as-judge for outcome assessment
- pass^k measures what practitioners actually care about: "will my agent handle this request consistently?"
- Dual-control models real-world scenarios where users actively participate (tech support, troubleshooting)

**Transferable Idea for Lyra (4.16 Reliability):**
- The **pass^k metric** is Lyra's most critical takeaway: Lyra should measure not just whether an agent can solve a task once, but whether it can solve it consistently across trials. A pass^8 < 25% means even successful demonstrations may be unreliable.
- The **database-state evaluation** approach (programmatic verification of outcomes) is preferable to LLM-as-judge for Lyra's regression testing.
- **Tau2-bench's dual-control paradigm** (Dec-POMDP) formally models Lyra's multi-agent setup: each sub-agent has its own action space and observations, and coordination requires communication.
- The **~20% pass^1 drop from autonomous to dual-control** quantifies the coordination overhead Lyra must address: adding routing/planning layers can hurt reliability if not carefully designed.

**Gap vs Baseline:**
- Lyra has **no systematic consistency evaluation**. Tau-bench provides the methodology (pass^k, database-state verification) and baseline results (best agents <50% on tau-bench).
- Lyra has **no decomposed error analysis** separating reasoning failures from coordination failures.

---

### SWE-bench Verified

**URL:** [www.swebench.com/verified.html](https://www.swebench.com/verified.html)

**Core Mechanism:**

SWE-bench Verified is a curated subset of SWE-bench where real-world GitHub issues (with failing tests) must be resolved by generating correct code patches. The "Verified" subset addresses concerns about the original SWE-bench's evaluation quality:

- **Task quality filtering**: Human annotators (professional software engineers) verified each task for solvability, unambiguous evaluation, appropriate difficulty, and freedom from data contamination. 42% of original tasks passed verification.
- **Evaluation methodology**: Patch execution on real test suites. Pass@k metric: at least one out of k generated patches passes all tests.
- **Task diversity**: Patches span 12 Python repositories including Django, Flask, SymPy, Matplotlib, astropy, scikit-learn, sphinx, etc.

**Transferable Idea for Lyra (4.16 Reliability):**
- The **human-verified task filtering** methodology (42% pass rate) demonstrates the importance of ground-truth quality. Lyra should implement similar quality gates for its own evaluation datasets.
- The **test-suite-based evaluation** (execute patch, run tests, verify all pass) provides the gold standard for agent reliability evaluation -- objective, deterministic, and resistant to LLM-as-judge biases.
- SWE-bench's repository-level tasks (requiring codebase understanding, not just file-level edits) are representative of Lyra's target complexity.

---

## Synthesis: What This Means for Lyra

### For the Router (§4.5)

| Source | Key Transferable Idea |
|---|---|
| RouteLLM | Lightweight MF router (<$1.42/1M req), augment with in-domain preference data |
| BEST-Route | Multi-head router (shared 44M backbone) with per-(agent, n) heads; best-of-n with proxy reward |
| FrugalGPT | Cascade with learned scoring; 98% cost savings at matching quality |
| Knowledge Access | Memory makes routing worthwhile; confidence-based routing with logprobs |
| Hybrid LLM repo | Pair-ranker training pipeline, DeBERTa-based router architecture |

### For Planning (§4.20)

| Source | Key Transferable Idea |
|---|---|
| ToT | BFS/DFS over sub-agent invocations; thought decomposition aligned with tool calls |
| RAP | LLM-as-world-model for simulating sub-agent outcomes before execution |
| SWE-Search | MCTS with hindsight feedback; depth-dependent UCT; 23% improvement |
| AFlow | Code-represented workflows; auto-workflow optimization via MCTS |
| MC-DML | Cross-trial memory for failure reflections; LLM-as-prior-policy in PUCT |
| Agentic Reasoning | Mind-Map KG for reasoning chain memory; tool delegation pattern |
| IterResearch | Workspace reconstruction avoids context suffocation; 2048-interaction scaling |

### For Cost Economics (§4.21)

| Source | Key Transferable Idea |
|---|---|
| Speculative Decoding | 2-3x latency reduction at identical output quality; n-gram approximations for boilerplate generations |
| FrugalGPT | Budget-constrained cascade optimization; 98% cost reduction |
| BEST-Route | 60% cost reduction at 0.80% quality drop; cost-aware best-of-n selection |
| Knowledge Access | 96% cost reduction via memory + routing; amortization dynamics |
| Cost-Augmented MCTS | Heterogeneous action costs must be modeled; Bi-Search for long-horizon cost-aware planning |

### For Reliability/Observability (§4.16)

| Source | Key Transferable Idea |
|---|---|
| Langfuse | Trace-based observability on ClickHouse; prompt versioning; LLM-as-judge eval |
| Phoenix | OpenInference OTel standard; MCP server for observability; experiments tracking |
| OpenLLMetry | Auto-instrumentation of agent framework; pluggable OTel exporters |
| Tau-bench | pass^k consistency metric; database-state verification; <50% success even for best agents |
| Tau2-bench | Dec-POMDP formalism for multi-agent; decomposed error analysis (reasoning vs coordination) |
| SWE-bench Verified | Human-verified task filtering; test-suite-based deterministic evaluation |

### Priority Actions for Lyra

1. **Immediate (Router):** Deploy log-probability confidence routing with cross-agent memory injection (Knowledge Access paper). This requires no training data and achieves 96% cost reduction.

2. **Short-term (Router):** Train a multi-head BERT router (BEST-Route style) on Lyra's execution traces to enable learned routing with best-of-n response selection.

3. **Short-term (Planning):** Implement iterative workspace reconstruction (IterResearch) to eliminate context suffocation in long-horizon tasks. This can be deployed as a prompt-level change without training.

4. **Medium-term (Planning):** Integrate MCTS-based planning (SWE-Search, RAP) with hindsight feedback for sub-agent workflow optimization. Target: 20%+ improvement in task success rate.

5. **Medium-term (Economics):** Implement speculative decoding framework for latency-sensitive sub-agent calls. Target: 2-3x latency reduction at zero quality loss.

6. **Medium-term (Reliability):** Adopt pass^k consistency evaluation methodology across all Lyra benchmark tasks. Implement database-state verification for objective outcome assessment.

7. **Long-term (Planning):** Deploy AFlow-style automated workflow optimization, allowing Lyra to discover optimal agent invocation patterns from execution feedback.

8. **Long-term (Economics):** Implement cost-augmented search (Budget-BlocksWorld style) with heterogeneous action costs, enabling Lyra's planner to produce cost-optimal (not just valid) execution plans.
