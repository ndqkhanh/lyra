# Performance & Cost Economics -- Plan (Section 4.21)

> Run 2 -- June 7, 2026 (deep-read enhanced)
> Run 1 -- June 3, 2026

## Plain-Language Summary

Lyra tracks every token spent -- per session, per agent, per workflow -- so you know exactly what your fleet costs. Prompt caching cuts costs 90% on repeated prefixes. Token budgets prevent runaway spending. The economics dashboard shows you where your money goes and suggests optimizations.

## Key Features

### 1. Token Accounting

Per-session, per-agent, per-workflow token tracking with real-time cost estimation (Anthropic/DeepSeek/GPT pricing tiers). Track cost per request as a first-class observability dimension -- model costs vary by 100x (Architecting Generative AI Applications, Ch 1: "Cost-Latency-Quality Triangle"; Agentic Design Patterns, Ch 19: "Track token usage for cost optimization"). Log per-call: model identifier, prompt template version, full input, full output, token count, latency, cost estimate, and success/failure (Architecting Generative AI Applications, Practice 7).

**Benchmark context:** Average Claude Code enterprise deployment costs ~$13 per developer per active day, $150-250 per developer per month; 90% of users remain below $30/day. Agent teams use ~7x more tokens than standard sessions in plan mode (Anthropic Claude Code Costs docs, code.claude.com/docs/en/costs).

Rate limit sizing for Lyra's multi-user deployment follows the Anthropic-suggested scale tiers: 1-5 users at 200k-300k TPM per user, scaling down to 15k-20k TPM per user at 100-500 user scale (Anthropic Claude Code Costs docs).

### 2. Prompt-Cache Strategy

Static prefix (system prompt + skill frontmatter) designed for 90% cache-hit rate. Stagger parallel session starts to maximize cache reuse. 5-min TTL management.

**Techniques from evidence:**
- **Simple exact-match cache**: ~8% hit rate, ~99% cost savings per hit (FrugalGPT, arXiv:2305.05176v1, ICML 2023).
- **Semantic cache**: Embedding-based similarity lookup achieves ~21% hit rate, ~95% cost/latency reduction per hit (FrugalGPT, arXiv:2305.05176v1). Requires threshold backtesting on ~5K requests.
- **Completion caching**: Cache full LLM completions for identical queries; combined with prompt caching yields additive savings (FrugalGPT).
- **Generative AI Design Patterns** (O'Reilly): "Cache repeated prompt prefixes (system prompts, tool definitions, static context) to reduce latency and cost." This applies directly to Lyra's orchestrator system prompt and agent definitions.

**Trade-off:** Cache can serve stale or wrong answers if not invalidated. Implement TTL-based invalidation with fallback to fresh generation. Cost of cache miss during cold start is covered by staggered session starts.

### 3. Token Budgets

`budget.total`, `budget.spent()`, `budget.remaining()` -- workflow scripts query remaining budget to decide scale. This implements the proactive context budgeting approach from Architecting Generative AI Applications (Practice 10): define explicit percentage allocations for system prompt, tool definitions, conversation history, and working memory; compress or evict strategically as limits approach.

**Budget-enforcement mechanisms from evidence:**
- **Per-call hard limits**: Cost budgets and hard limits per user/session (Generative AI Design Patterns, Pattern 28; Agentic Design Patterns, Ch 19).
- **Token-level budget for agents**: Assign each spawned agent a per-invocation token budget -- soft limit + hard cap on output tokens to prevent runaway spend (Anthropic Claude Code Costs docs).
- **Background cost awareness**: Background token usage (conversation summarization, command processing) typically under $0.04 per idle session (Claude Code docs).
- **Extended thinking budget**: Default budget can be tens of thousands of output tokens per request; adjustable via `MAX_THINKING_TOKENS` environment variable or `/effort` command (Claude Code docs).

### 4. Amdahl's Law for Agents

Parallelism stops paying when coordination overhead > speedup. Fleet concurrency auto-tuned.

**Real-world evidence of idle-time economics:**
- IdleSpec (arXiv:2605.22154v1, KAIST + Amazon): Agents spend substantial wall-clock time waiting for tool calls. IdleSpec exploits this idle window for speculative planning, achieving 34.6% idle-time utilization. In GAIA benchmarks, Gemini-2.5-Flash goes from 50.5% (vanilla) to 55.6% (+5.1% average) with near-zero end-to-end latency overhead (+2s on 374s GAIA L3 tasks).
- **Prerequisite for Lyra**: Profile Lyra's actual idleness ratio (tool execution time / reasoning time). If idle ratio > 5x and ultra-short ratio < 0.3, IdleSpec is a high-ROI adoption candidate.
- **Token cost of idleness**: IdleSpec adds ~5,284 tokens per GAIA L2 task for speculative drafting. This is acceptable when it delivers +5-9% accuracy gains at 0% latency increase.

### 5. Cost Dashboard

`/cost` command -- per-session breakdown, per-model spend, projected monthly cost, cache-hit rate. Modeled on Claude Code's `/usage` command which shows token usage for current session and plan-level breakdown by skills, subagents, plugins, and MCP servers as attribution percentages over 24h/7d windows (Claude Code Costs docs). Also implement per-workstream cost tracking (Architecting Generative AI Applications, Practice 7): dashboards for cost per workstream, latency p50/p95/p99, error rates by model, token usage trends; with alerts for cost spikes, latency degradation, guardrail trigger rate increases.

### 6. LLM Cascade Routing (Enhanced)

Replace the previous single-strategy routing plan with a multi-strategy cost-quality router:

**Technique A -- FrugalGPT LLM Cascade (arXiv:2305.05176v1, ICML 2023, Stanford):**
- Ordered LLM chain sorted by cost (cheapest first). DistilBERT (66M) scorer at each tier evaluates answer reliability. If score > learned threshold, accept and return. Otherwise escalate.
- **Key insight -- Complementarity (MPI matrix)**: ~6% of GPT-4 errors on HEADLINES are correctly answered by GPT-J. This means cascading can outperform any single model.
- **Results**: 98.3% cost savings on HEADLINES (matching GPT-4 accuracy), 73.3% on OVERRULING, 59.2% on COQA; +1.5-4% absolute accuracy improvement at equal cost.
- **Limitations**: Sequential LLM calls increase worst-case latency (not addressed in FrugalGPT paper). All-models-wrong failure: when every model fails, system queries all tiers at maximum cost for zero gain. Requires labeled validation set from target distribution for threshold tuning.

**Technique B -- RouteLLM (arXiv:2406.18665v4, ICLR 2025, UC Berkeley/Anyscale/Canva):**
- Binary routing: matrix factorization or BERT-based router between strong (expensive) and weak (cheap) models, trained on human preference data from Chatbot Arena.
- **Results**: MT-Bench 3.66x cost savings at 95% GPT-4 quality (CPT(50%) = 13.40% -- only 13.4% of calls need GPT-4). Router overhead <0.4% of LLM generation cost. Cross-model generalization: Claude 3 Opus/Sonnet routing achieves CPT(50%) = 23.27% with zero retraining.
- **Limitations**: Binary routing only -- no N-way extension. Distribution shift vulnerability: routers trained on Arena chat data perform at random level on MMLU/GSM8K without domain-specific augmentation. Augmentation costs ~$700 for 120K LLM-judge labels.

**Technique C -- BEST-Route (arXiv:2506.22716v1, ICML 2025, Microsoft):**
- Multi-head router (DeBERTa-v3-small 44M shared backbone + KxN classification heads) with best-of-N sampling via proxy reward model (DeBERTa-v3-large 300M). Selects cheapest (model, n) pair satisfying quality threshold.
- **Results**: 40% cost reduction with only 0.47% quality drop; 60% cost reduction with only 0.80% quality drop. Beats cascading methods 6-9x at equivalent cost. Adding Codestral-22b specialist achieves QUALITY GAIN over GPT-4o (-0.10% quality drop) at 10% cost reduction.
- **Key mechanism**: Best-of-n for small models closes the quality gap that makes pure routing ineffective. Best-of-n with n=5 gives 4.9% quality drop for Phi-3-mini alone; BEST-Route with max n=5 gives 0.21% quality drop at 20% cost reduction.
- **Limitations**: Requires proxy RM training data (20 responses per query per model -- 1.28M API calls for 8 models x 8K queries). Output length estimation error: $0.0001-$0.0027/query using average length estimates. Single-turn evaluation only.

**Technique D -- SLM-First Heterogeneous Architecture (arXiv:2506.02153v2, NVIDIA Research, 2025):**
- Six-step pipeline: (S1) InstrumentLM calls, (S2) Curate data, (S3) Cluster by task, (S4) Select SLMs, (S5) Fine-tune via LoRA/QLoRA, (S6) Iterate.
- **Claim**: SLM inference is 10-30x cheaper than 70-175B LLMs. MetaGPT ~60% replaceable, Open Operator ~40%, Cradle ~70%. xLAM-2-8B achieves SOTA tool calling, surpassing GPT-4o and Claude 3.5.
- **Limitations**: Position paper with no end-to-end experiments. SLM-by-default vs. centralized-LLM economies of scale is acknowledged as unsettled. "The jury is still out" (AV2).

**Lyra's composite strategy:** Implement FrugalGPT cascade for batch/background tasks (latency-tolerant), BEST-Route for quality-sensitive interactive queries (parallel prediction), and start RouteLLM-style matrix factorization router (8GB GPU, open source) as the near-term deployment. RouteLLM's open-source framework provides the fastest path to a learned router. LONG-TERM: Adopt SLM-first pipeline (S1-S6) to progressively replace LLM calls with fine-tuned specialists on high-volume clusters.

### 7. Cost-Aware Tree Search (New)

Budget-Aware MCTS (arXiv:2505.14656v2, Emory + UC Merced): Explicit budget feasibility filter during multi-step agent planning. Computes `accumulated_cost + minimum_remaining_cost` at each reasoning step and prunes branches exceeding the budget.

**Results (Budget-BlocksWorld, 1,008 tasks):**
- Bidirectional Search achieves 87% average success rate vs. 13% CoT/Qwen3, 27% CoT/GPT-4.1, 53% CoT/Claude (LOOSE budget regime).
- Bi-Search efficiency: 0.96 vs. MCTS 0.51 (TIGHT budget) -- uses only 4% of node budget on average.
- However, 92% of Bi-Search failures are budget violations -- finds plans fast but rarely cost-optimal.
- LLMs alone fail at cost-infesibility detection 36-89% of the time. The deterministic pruning filter is what provides the gains.

**Transfer to Lyra:** Implement budget feasibility filter in Lyra's multi-step tool-call planning. Use deterministic cost model for tools (API calls cost known; file I/O cost estimated by size). The cost-informed pruning is orthogonal to the underlying planner and requires no model retraining.

### 8. Idle-Time Speculative Planning (New)

IdleSpec (arXiv:2605.22154v1, KAIST + Amazon AGI): Dual-strategy planning during tool-execution idle time -- progressive drafting (assume forward progress) and recovery drafting (assume failure). Self-adjusting strategy selection via Beta-Bernoulli Thompson sampling.

**Results:**
- Gemini-2.5-Flash: Vanilla 50.5% -> IdleSpec 55.6% (+5.1% avg across GAIA/FRAMES)
- Qwen3.5-4B: Vanilla 33.2% -> IdleSpec 40.0% (+6.8%)
- GAIA Level 3 (hardest): 25.6 -> 32.1 (+6.5% for Gemini, +10.3 points for Qwen3.5-4B)
- MLE-Bench: Any Medal rate 36.4% -> 45.5% (+9.1%)
- Latency: Near-identical to vanilla (+2s on 374s GAIA L3 task)
- Idle-time utilization: 34.6% vs. Sleep-time Compute 13.2%

**Trade-off:** Adds ~5,284 tokens per GAIA L2 task for speculative drafting. Only benefits when tool calls are longer than one reasoning step (fails on ultra-short ratio > 0.75). Requires no model training -- only prompt engineering and a Beta counter.

### 9. Speculative Decoding (Anthropic-only, Enhanced)

Haiku drafts tokens; Sonnet/Opus verifies in parallel. 2-3x latency reduction.

**Mathematical foundation** (arXiv:2211.17192v2, Google Research, ICML 2023 Oral):
- Acceptance rate: beta = 1 - D_KL(p, q) = sum_x min(p(x), q(x))
- Walltime improvement: (1 - alpha^{gamma+1}) / ((1 - alpha)(gamma*c + 1)), where c is cost ratio, gamma is number of draft tokens.
- **Evidence**: T5-XXL (11B) with T5-small (77M) draft: 3.4x walltime speedup (EnDe translation). LaMDA 137B with 8B draft: alpha = 0.75 acceptance rate. GPT-like 97M/6M: alpha = 0.88. Even bigram draft achieves alpha = 0.20, enabling ~1.25x improvement.
- **Guarantee**: Appendix A.1 theorem proves output distribution is mathematically identical to target model under rejection sampling.

**Critical limitation for Lyra**: Same-vocabulary draft/target pair required at token level. Anthropic does not expose token-level speculative decoding as a public API. Lyra's chunk-level approximation (Haiku drafts full response, Sonnet verifies) loses the exact distribution guarantee. Open problem: formal analysis of quality bounds for chunk-level speculative decoding with API-constrained draft/target pairs.

## Breakthrough Proposals

Each proposal fuses techniques from 2-5 independent sources. None are single-source transplants.

---

### Breakthrough 1: Five-Primitive Task Typing for Deterministic Cost Routing

**Fusion:** OpenJarvis 5-primitive typed spec + FrugalGPT cascade + Knowledge Access Beats Model Size + Agentic Design Patterns complexity-based tiering

**What it is:** Every agent task decomposes into one of five typed primitives (Search, Navigate, Select, Extract, Write) drawn from the OpenJarvis typed-spec paradigm. The (teacher) expensive model defines the spec once per benchmark ($15.6 total), and the (student) cheap model executes it for <$0.001 per query thereafter -- a teacher-student amortization that is the inverse of FrugalGPT's per-call cascade. Each primitive maps deterministically to a cost-optimal model tier: Search/Write to Tier 1 (Haiku/Llama-8B), Navigate/Select to Tier 2 (Sonnet/GPT-4o-mini), Extract to Tier 3 (Opus/GPT-5). The typed spec IS the router -- no learned model needed for the ~85% case.

**Why it wins over SOTA learned routing:** BEST-Route and RouteLLM require 1.28M training API calls and full retraining when model pools change. A 4KB JSON lookup table over five primitives costs zero training, zero inference compute (<0.001s), and is immediately deployable. OpenJarvis's teacher-student amortization means one expensive pass defines all primitives, then cheap execution dominates. Knowledge Access augments this: if Search("paris weather") was already executed in-session, route directly to the cached turn-pair without any LLM call -- the primitive type gates caching eligibility. Agentic Design Patterns (Ch 2) independently recommends complexity-based routing tiers; typed primitives give it a formal foundation.

**Skeptic:** "Primitives are too coarse. A 'Select' in a 200K-token code review is harder than a 'Select' in a single-file lint. Deterministic routing ignores within-primitive variance." **Counter:** The primitive defines the minimum capability floor; the already-planned cost-aware MCTS filter (Section 7) adds budget-feasibility pruning for within-primitive variance. The typed spec sets the floor; the budget filter sets the ceiling. Hybrid deployment: typed spec for known operations, BEST-Route fallback for ambiguous tasks.

**Trade-offs:** Requires instrumenting every agent call with a typed-spec annotation -- low code cost, high discipline cost. Ambiguous tasks (e.g., a query that is both Search and Write) need explicit disambiguation logic. Does not replace learned routers for open-ended reasoning (architecture debates, research synthesis).

**Impact:** 4 | **Effort:** 2 | **Tier:** (B) Breakthrough

---

### Breakthrough 2: Session-Coherent KV-Cache Orchestration with Iterative Speculative Execution

**Fusion:** KV-cache reuse across turns (Anthropic prompt caching, DeepSeek KV management) + IdleSpec (idle-time speculative planning) + Speculative Decoding (chunk-level draft/verify) + Knowledge Access (verbatim turn-pair pre-warming)

**What it is:** A session-level protocol that maintains KV-cache for the static session envelope (system prompt + agent identity + tool schemas) across ALL turns of an agent loop, not just per-call. On each turn, inject ONLY the delta (new tool result, new user turn) into a maintained cache frame -- avoiding re-encoding the 10K-token prefix 10 times. During tool-execution idle windows, the cheap model speculatively decodes the next N agent actions against the maintained cache, pre-computing branch probabilities. When the tool result arrives, Thompson sampling (IdleSpec) matches against pre-computed branches; on match, skip the expensive model call entirely.

**Why it wins over single-source approaches:**
- Anthropic/OpenAI prompt caching currently re-encodes the full prefix per call independently. On a 10-turn agent session with an identical 10K-token prefix, this wastes 90K tokens in prefix re-encoding. Session-coherent cache reuses ~90% of prefix encoding across turns.
- IdleSpec achieves 34.6% idle-time utilization but plans forward speculatively without caching past plans. KV-cache pre-computation means speculative work is cached and reusable when plans shift, not discarded.
- Speculative decoding's chunk-level approximation (Haiku drafts, Sonnet verifies) fits naturally: cheap model drafts the next action under maintained cache while waiting for tools; expensive model verifies using the same cache frame.
- Knowledge Access pre-warms from cross-session: if a similar turn sequence occurred in another session, initialize the KV-cache from the matching prefix.

**Skeptic:** "KV-cache is provider-internal. Anthropic/OpenAI do not expose cache persistence handles across API calls. You cannot 'maintain' cache at the API level." **Counter:** True for opaque API providers. But Lyra's multi-provider deployment includes self-hosted models (Llama, Qwen, DeepSeek open weights; see plan/05-router.md) where `past_key_values` tensors are exposed via PyTorch -- session-coherent cache is implementable today. For API-only tiers, approximate with prompt caching at the turn boundary (~70-80% savings). The hybrid (open-weights + API) architecture makes this viable immediately for the self-hosted tier.

**Trade-offs:** Open-weights only for exact KV-cache reuse. Prompt-caching approximation at turn boundaries loses 20-30% of theoretical savings. Memory pressure: 128K-token KV-cache at 8-bit precision needs ~4GB per active session; 50 concurrent sessions = 200GB, requiring GPU memory management or CPU offloading. Implementation complexity is moderate (cache frame management, delta encoding, invalidation on context change).

**Impact:** 5 | **Effort:** 4 | **Tier:** (B) Breakthrough

---

## Multi-Provider Note

Pricing tiers auto-detected from provider config. Cache-hit strategy works across Anthropic (native prompt cache) and DeepSeek (KV-cache reuse). Speculative decoding limited to Anthropic (both draft + target same provider).

**Impact:** 3 | **Effort:** 2 | **Tier:** (A) Parity

## Evidence Synthesis

| Source | Key Insight |
|--------|-------------|
| Claude Code Costs docs (code.claude.com/docs/en/costs) | Per-session, per-workflow token tracking; ~$13/dev/day average; 7x token multiplier for team mode; Haiku-class model for meta/monitoring |
| FrugalGPT (arXiv:2305.05176v1, ICML 2023) | LLM cascade: route simple queries to cheap models -- 98% cost reduction at same accuracy; semantic cache 21% hit rate, 95% savings; ~6% complementarity (GPT-J gets what GPT-4 misses) |
| RouteLLM (arXiv:2406.18665v4, ICLR 2025) | Binary learned routing: 3.66x cost savings at 95% GPT-4 quality; zero-retraining cross-model generalization; open-source framework |
| BEST-Route (arXiv:2506.22716v1, ICML 2025) | Multi-head router + best-of-N: 60% cost reduction with <1% quality drop; specialist routing beats GPT-4o on coding queries (-0.10% quality drop); deployed at Microsoft |
| SLM-First (arXiv:2506.02153v2, NVIDIA 2025) | 10-30x cheaper per token; 60-70% agent queries replaceable by SLMs; LoRA/QLoRA fine-tuning pipeline; heterogeneous architecture (SLM-default, LLM-selective) |
| Cost-Augmented MCTS (arXiv:2505.14656v2) | Budget-aware tree search: Bi-Search 87% success rate, 0.96 efficiency; LLMs miss infeasibility 36-89% of time; deterministic pruning filter is the lever |
| IdleSpec (arXiv:2605.22154v1, KAIST + Amazon) | Speculative planning during tool-waiting: +5.1% accuracy, 34.6% idle-time utilization, near-zero latency overhead; Thompson-sampled dual-strategy drafting |
| Speculative Decoding (arXiv:2211.17192v2, ICML 2023 Oral) | 2-3.4x walltime reduction with mathematical distribution guarantee; API-blocked at token level for Lyra's draft/target pair |
| RMoA (arXiv:2505.24442v1, Meituan + ECNU + Tsinghua) | Diversity-based response selection: +4.55-11.10% accuracy vs. MoA; 31-53% cost reduction via embedding-based diversity maximization; K=3 optimal |
| SELF-RAG (arXiv:2310.11511v1, UW + AI2 + IBM) | On-demand retrieval gating: 54.9% retrieval usage vs. 24.7% without gating on PopQA; 7B beats ChatGPT on 3/6 tasks; learned reflection tokens gate retrieval cost |
| Architecting Generative AI Applications (O'Reilly, 2024) | Cost-latency-quality triangle as first-class design dimension; practice 7: log every LLM interaction; practice 10: budget context window proactively; model costs vary by 100x |
| Agentic Design Patterns (O'Reilly, 2025) | Ch 2: complexity-based tiering; Ch 16: resource-aware optimization; Ch 19: track token usage, drift detection, evaluate with cost-awareness |
| Generative AI Design Patterns (O'Reilly, 2025) | Pattern 24: small model cascade (3 tiers); Pattern 26: inference optimization; Pattern 28: cost budgets per user/session; anti-pattern: ignoring long context cost implications |
| Amdahl's Law for Agents (synthesis) | Parallelism stops paying when coordination overhead > speedup; auto-tune fleet concurrency; IdleSpec provides empirical validation of idle-time utilization bounds |

## Convergence Highlights (from synthesis/routing.md)

**Three-Tier Model Architecture** (7 independent sources agree): FrugalGPT, Generative AI Design Patterns, Agentic Design Patterns (Ch 16), NVIDIA SLM paper, BEST-Route, Architecting Generative AI Applications, Lyra brainstorm/05-router.md. Tier 1: local/edge or Haiku (guardrails, classification). Tier 2: Sonnet/GPT-4o-mini (standard reasoning). Tier 3: Opus/GPT-4o (complex reasoning, architecture decisions).

**Router Must Be Cheap** (4 independent sources): FrugalGPT DistilBERT (66M) = "essentially free"; RouteLLM <0.4% of LLM cost; BEST-Route DeBERTa-v3-small (44M) = 0.04s prediction; Agentic Design Patterns (Ch 2) recommends rule-based or embedding routing for high-throughput systems.

**Cost Tracking as First-Class Metric** (3 independent books): Architecting Generative AI Applications (Ch 1), Agentic Design Patterns (Ch 19), Generative AI Design Patterns (Pattern 28). All agree: cannot optimize what is not measured. Log every LLM call with model, prompt version, tokens, cost, latency.

**Complementarity Beats Single-Model Optimality** (2 papers): FrugalGPT's MPI analysis proves GPT-J gets ~6% queries GPT-4 misses. BEST-Route adds Codestral-22b specialist for quality GAIN over GPT-4o. Routing to specialized models can surpass the strongest generalist.

## Cascade vs. Parallel Routing Contradiction

FrugalGPT advocates sequential cascade (cheapest first, escalate if unreliable). BEST-Route advocates parallel routing (predict optimal model upfront). BEST-Route directly compares: cascade shows 7.26% quality drop at 60% cost reduction vs. BEST-Route's 0.80%. BEST-Route's parallel prediction (0.04s) avoids sequential LLM calls.

**Resolution for Lyra:** Sequential cascade for batch/background tasks (latency-tolerant). Parallel routing for interactive queries (latency-sensitive). Lyra should implement BOTH strategies with a latency-adaptive selector that switches between them. The BEST-Route quality advantage at equivalent cost is decisive for quality-sensitive applications.

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| lyra-cost (package) | EXTEND: per-workflow, per-agent, per-session tracking | Low -- existing cost tracking |
| Prompt-cache strategy | ADD: static prefix design, 5-min TTL management; EXTEND: semantic cache (FrugalGPT, 21% hit rate), completion cache | Low -- provider-level config + embedding DB |
| Token budgets | ADD: budget.total/spent/remaining API for workflow scripts; context window budgeting (Architecting GenAI Practice 10); per-agent output token caps | None -- new |
| Cost dashboard | ADD: `/cost` command; per-model spend breakdown; cache-hit rate; latency p50/p95/p99 dashboards | Low -- new slash command |
| LLM Cascade Router | ADD: FrugalGPT-style cascade for batch tasks; RouteLLM matrix factorization router for interactive (8GB GPU, open-source framework) | Medium -- needs preference data from Lyra evals |
| BEST-Route multi-head router | ADD: long-term -- proxy RM training + multi-head router (replaces matrix factorization) | High -- requires training data (20 responses/query/model) |
| Cost-aware planning | ADD: budget feasibility filter for multi-step tool-call planning (Cost-Augmented MCTS) | Low -- deterministic filter, no model retraining |
| Idle-time speculation | ADD: IdleSpec-style dual-strategy planning during tool idle time | Medium -- execution loop change, prompt engineering |
| SLM specialization pipeline | ADD: instrument LM calls, cluster by task, fine-tune SLM specialists (NVIDIA SLM paper pipeline) | High -- multi-phase, requires data collection |
| Diversity-based response selection | ADD: RMoA-style BGE-m3 embedding + greedy K-selection for multi-agent consensus | Low -- ~50 lines of code |
| Amdahl's Law auto-tuning | REFINE: measure coordination overhead empirically; integrate IdleSpec idle-time profiling data | Low -- monitoring addition |

## Expert Review

**Senior Performance Engineer:** "The biggest cost lever is routing 80% of queries to cheap models. A $0.0001/call Haiku handles meta/monitoring; $0.003 Sonnet handles routine tasks; $0.015 Opus handles reasoning. The router doubles as a cost optimizer. But the evidence now shows we need TWO routers: a fast prompt-only router (BEST-Route style, 0.04s overhead) for latency-sensitive queries and a response-aware cascade (FrugalGPT style) for batch work. The BEST-Route results at Microsoft -- 60% cost reduction with <1% quality drop -- are the strongest we have. The IdleSpec result is also striking: +5.1% accuracy at near-zero latency cost. That's essentially free quality if our idle ratio is high enough."

**Skeptic:** "Budget API (`budget.remaining()`) is clever but unused if users don't set budgets. Default to a daily cost cap ($50) that warns at 80% and stops at 100%." --> ADOPTED. Also add: 3 out of 3 major O'Reilly books on generative AI architectures recommend cost budgets and hard limits per user/session. Enable budgets by default with `$50/day` soft limit, `$100/day` hard cap.

**Research Lead:** "The BEST-Route training data requirement (20 responses per query per model) is prohibitive for Lyra's initial deployment. Start with RouteLLM's matrix factorization approach -- it trains on a single 8GB GPU using preference data from Lyra's existing eval runs. That gives us a learned router in 2-3 sprints. Upgrade to BEST-Route's multi-head architecture in Phase 4C when we have enough training data. The RouteLLM cross-model generalization result (Claude Opus/Sonnet routable with zero retraining) is particularly relevant since Lyra already uses the Claude family."

**Architecture Lead:** "The cascade vs. parallel routing contradiction resolves cleanly for Lyra: our architecture already separates interactive (orchestrator prompts) from batch (planned research) execution. We apply parallel routing to interactive and cascade to batch. This is a routing config, not an architecture change. The SLM-first pipeline is our 12-month strategic direction but should not delay launch -- start with FrugalGPT-style 3-tier routing, iterate toward learned routers."

## Evidence Base

### Papers (with arXiv IDs)

| ID | Title | Venue | Relevance to Lyra Economics |
|----|-------|-------|-----------------------------|
| 2305.05176v1 | FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance | ICML 2023, Stanford | **Primary**: LLM cascade, semantic cache, prompt adaptation, complementarity (MPI matrix), 98% cost savings |
| 2406.18665v4 | RouteLLM: Learning to Route LLMs with Preference Data | ICLR 2025, UC Berkeley/Anyscale/Canva | **Primary**: Binary routing with preference data, matrix factorization (8GB GPU), cross-model generalization, open-source framework |
| 2506.22716v1 | BEST-Route: Adaptive LLM Routing with Test-Time Optimal Compute | ICML 2025, Microsoft | **Primary**: Multi-head router + best-of-N, 60% cost cut <1% quality drop, specialist routing beats GPT-4o, deployed at Microsoft |
| 2506.02153v2 | Small Language Models are the Future of Agentic AI | NVIDIA Research, 2025 | **Strategic**: SLM-first architecture, 10-30x cheaper, 60-70% replaceability, 6-step conversion pipeline |
| 2505.14656v2 | Cost-Awareness in Tree-Search LLM Planning: A Systematic Study | arXiv, Emory + UC Merced | **Supporting**: Budget feasibility filter, Bi-Search 87% success rate, LLMs miss infeasibility 36-89% |
| 2605.22154v1 | IdleSpec: Exploiting Idle Time via Speculative Planning for LLM Agents | arXiv, KAIST + Amazon AGI | **Supporting**: Idle-time utilization 34.6%, +5.1% accuracy, zero latency increase, Thompson-sampled dual-strategy drafting |
| 2211.17192v2 | Fast Inference from Transformers via Speculative Decoding | ICML 2023 Oral, Google | **Supporting**: 3.4x speedup, mathematical distribution guarantee, API-blocked at token level for Lyra |
| 2505.24442v1 | RMoA: Optimizing Mixture-of-Agents through Diversity Maximization | arXiv, Meituan + ECNU + Tsinghua | **Supporting**: Diversity selection, 31-53% cost reduction vs MoA, K=3 optimal |
| 2310.11511v1 | SELF-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | UW + AI2 + IBM, 2023 | **Supporting**: Retrieval gating, only 54.9% of queries need retrieval; gates cost by avoiding unnecessary retrieval |
| 2305.10601v2 | Tree of Thoughts: Deliberate Problem Solving with Large Language Models | NeurIPS 2023 | **Background**: Foundation for cost-aware tree search; ToT enabled subsequent budget-aware extensions |

### Books

| Title | Relevant Chapters | Key Citations |
|-------|-------------------|---------------|
| Architecting Generative AI Applications (Kuligin, O'Reilly 2024) | Ch 1: Cost-Latency-Quality Triangle; Practice 7: LLM instrumentation; Practice 10: Context budgeting | Cost varies 100x across models; log every call with tokens+cost+latency; budget context window by category |
| Agentic Design Patterns (Gulli, O'Reilly 2025) | Ch 2: Routing; Ch 16: Resource-Aware Optimization; Ch 19: Evaluation | Complexity-based tiering; "For high-throughput, use rule-based or embedding routing"; track token usage for cost optimization |
| Generative AI Design Patterns (O'Reilly 2025) | Pattern 24: Small Model Cascade; Pattern 26: Inference Optimization; Pattern 28: Long-Term Memory | 3-tier model strategy (BEST/DEFAULT/SMALL); cost budgets per user/session; anti-pattern: ignoring long context cost |

### Web / Repos

| Source | Key Content |
|--------|-------------|
| Anthropic Claude Code Costs docs (code.claude.com/docs/en/costs) | ~$13/dev/day average, 7x team token multiplier, rate limit sizing per team size, /usage command, auto-compaction cost savings, extended thinking budget |
| microsoft/best-route-llm (GitHub, MIT license) | Production router implementation, DeBERTa-v3 multi-head router training pipeline, proxy reward model training code |
| RouteLLM (GitHub, open source) | Framework for training, serving, and evaluating LLM routers; matrix factorization router trains on single 8GB GPU |

### Lyra Internal

| Document | Content |
|----------|---------|
| synthesis/routing.md | 15-paper thematic synthesis on model routing and cost optimization; head-to-head comparisons; convergences; contradictions; open problems |
| brainstorm/05-router.md | Lyra router design brainstorm -- Haiku/Sonnet/Opus tiering, intent classification, tool-selection routing |
| MASTER-PLAN.md | Section 4.21 economics; cost-conscious design principles; integration with other workstreams |
| ARCHITECTURE-DEBATE.md | Ongoing architecture debates including model selection strategy and provider diversification |
