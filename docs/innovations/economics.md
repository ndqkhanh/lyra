# Economics: Cost Tracking, Token Budgeting, and Resource Allocation
> **Status:** 🟡 Partially implemented -- BudgetController, per-provider cost tracking, session budget enforcement, static tier router, memory-augmented routing, effort mapping, and cost estimation types are implemented. LLM cascade routing, learned multi-head router, cost dashboard, prompt-cache hit-rate optimization, cost-aware tree search, idle-time speculative planning, and SLM specialization are planned.
> **Plan:** [Workstream Plan](../lyra-upgrade/plans/21-economics.md) | **Code:** `src/lyra/economics/`, `src/lyra/routing/`, `src/lyra/effort/`
> **Reading path:** Non-technical readers -- TL;DR right arrow How it works (simple) right arrow Use Cases right arrow Trade-offs in brief. Engineers -- everything.

## TL;DR

Every time Lyra calls a language model, it costs money. This module tracks every penny: per session, per provider, per task. It lets you set budget hard limits -- when you are close to running out, Lyra warns you; when you hit the limit, it stops expensive calls or downgrades to cheaper models automatically. A model router picks the cheapest model that can handle each task -- simple lookups go to a fast cheap model, deep reasoning goes to the expensive one -- cutting costs without cutting quality. Prompt caching reuses repeated content (system prompts, tool definitions) automatically, avoiding the cost of re-sending the same text on every call. Some parts work today (budget tracking, tier-based routing, cost estimation, effort mapping); advanced features like learned cost-quality routers, a cost dashboard, and idle-time speculative planning are planned.

## Abstract

LLM agent systems face a fundamental economic tension: using frontier models for every call delivers quality but is prohibitively expensive, while aggressive cost-cutting degrades user experience. Lyra's economics module addresses this with a layered system of budget enforcement, cost-aware model routing, and prompt-cache optimization. The implemented `BudgetController` (`src/lyra/economics/budget.py`) enforces per-session and per-provider dollar caps with warning and critical alerts. The static tier router (`src/lyra/routing/provider/router.py`) maps task types (simple lookup, standard, complex reasoning, research) to effort levels and selects the cheapest qualifying model from a configurable multi-provider fallback chain. The `MemoryAugmentedRouter` (`src/lyra/routing/memory_router.py`) implements cross-agent cache routing: verbatim turn-pair storage with hybrid BM25+cosine retrieval and confidence-gated cheap-model execution, targeting a 58.5% total cost reduction per the Knowledge Access paradigm (Liu et al., arXiv:2603.23013v1). A `LearnedRouter` scaffold (`src/lyra/routing/learned_router.py`) provides the DeBERTa-v3-small multi-head architecture (BEST-Route, arXiv:2506.22716v1) in cold-start mode, awaiting training data. The `EffortManager` (`src/lyra/effort/manager.py`) translates Lyra's six-level reasoning-effort scale into provider-specific API parameters (Anthropic budget_tokens, OpenAI reasoning_effort, DeepSeek prompt-level thinking instructions). Planned additions include LLM cascade routing (FrugalGPT, arXiv:2305.05176v1), a cost dashboard (`/cost` command), budget-aware tree-search planning (arXiv:2505.14656v2), and idle-time speculative planning (IdleSpec, arXiv:2605.22154v1).

## Introduction

For any LLM-powered agent system, the cost-latency-quality triangle is the central design constraint (Architecting Generative AI Applications, Ch 1 -- see notes at `docs/lyra-upgrade/notes/books/architecting-generative-ai-applications-playbook.md`). Each LLM API call burns real money: a single Opus reasoning call can cost $0.015 or more, while a Haiku classification call costs $0.00025 -- a 60x spread. In a multi-agent fleet running hundreds or thousands of calls per session, these costs compound relentlessly. Existing approaches to LLM economics fall into three categories: **(a) model cascade systems** (FrugalGPT, arXiv:2305.05176v1) that route queries through an ordered chain of increasingly expensive models; **(b) learned routers** (RouteLLM, arXiv:2406.18665v4; BEST-Route, arXiv:2506.22716v1) that predict the optimal model per query; and **(c) budget-management tools** (Architecting Generative AI Applications, Practice 10; Generative AI Design Patterns, Pattern 28) that enforce hard and soft spending caps per session or per user. None of these approaches are engineered for the multi-agent, multi-provider, multi-effort-level architecture that Lyra requires.

Lyra fills this gap with a unified economics layer that vertically integrates budget enforcement, cost-aware routing, provider fallback, effort mapping, and prompt-cache optimization. The key contributions are:

1. **BudgetController** with per-session and per-provider dollar caps, warning-at-80% and critical-at-100% alerts, and a real-time `remaining()` query API for workflow scripts to make cost-informed decisions.
2. **Static tier router** that maps task types (simple_lookup, standard, complex_reasoning, research, code_generation, etc.) to model tiers (fast/smart/premium) across multiple providers (Anthropic, OpenAI, DeepSeek, Google) with ordered fallback chains.
3. **Memory-augmented cache router** implementing Knowledge Access (verbatim turn-pair storage, hybrid BM25+cosine retrieval, confidence-gated cheap-model execution) for cross-agent cost savings.
4. **EffortManager** providing a portable six-level reasoning-effort scale (low through ultracode) that translates to native API parameters per provider, enabling cost-accuracy calibration at the turn level.
5. **Learned router scaffold** (BEST-Route multi-head architecture with RouteLLM-style matrix-factorization preference model) in cold-start mode, ready for training-data generation.
6. **Planned workstreams** including LLM cascade routing, cost dashboard, budget-aware tree search, idle-time speculative planning, and SLM specialization pipeline.

> **Intuition callout:** Think of Lyra's economics layer as a CFO for your agent fleet -- it sets budgets, audits spending, negotiates which provider gets which task, and silently finds savings (cache hits, cheap-model routing) without the user noticing. The user sets the budget ceiling; the economics module does the rest.

## How it works -- the simple version

**(a) Everyday analogy.** Imagine a consulting firm with three tiers of lawyers. Junior associates (cheap, fast) handle routine document review. Senior associates (mid-price) draft contracts and handle standard cases. Partners (expensive, slow) only step in for complex litigation or court appearances. Every client gets a project budget. A project manager tracks hours in real-time: when a case is eating the budget, the manager warns the team, reassigns work to lower-cost associates, or stops non-essential research. Lyra's economics module is that project manager -- it knows what each "lawyer" (model) costs, which tier to assign for each "case" (task type), and when the "client's budget" (session budget) is running low.

**(b) Simple Mermaid diagram.**

```mermaid
flowchart TD
    U[You ask a question] --> R[Router picks cheapest suitable model]
    R --> B[Budget tracker records the cost]
    B --> A{Near budget limit?}
    A -- No --> N[Continue normally]
    A -- Yes --> K[Downgrade or stop expensive work]
    R -.-> C[Cache reuses repeated content]
    C -.-> R
```

**(c) Working Flow story.**

You start a Lyra session with a $10 budget. You ask Lyra to "check the syntax of this Python file." The Router classifies this as `simple_lookup` and maps it to `EffortLevel.LOW`. The tier router selects a fast model (Haiku or GPT-4o-mini) and calls the provider. The `BudgetController` records the cost -- about $0.0003. No alert needed; you are at 0.003% of budget.

Next, you ask: "Explain the architecture of the agent loop and identify any deadlock risks." The Router classifies this as `complex_reasoning` and maps it to `EffortLevel.HIGH`. The tier router selects a premium model (Opus or GPT-5). The `BudgetController` records $0.08. Now you are at 0.8% of budget. Still comfortable.

After 20 more turns of mixed complexity, your session has burned $8.50. The `BudgetController` detects you are at 85% of budget -- above the 80% warning threshold. It emits a `BudgetAlert` with level `WARNING`. The Router's `complete_with_fallback` method, seeing `budget_remaining` is only $1.50, starts skipping expensive premium-model candidates and downgrades complex reasoning tasks to the smart tier (Sonnet). You keep working, but the economics module silently adjusts the cost-quality dial.

At $10.00, the `BudgetController` emits a `CRITICAL` alert. The Router's budget check stops all new requests. You get a message: "Session budget exhausted." You extend the budget or start a new session.

Throughout, the `MemoryAugmentedRouter` is quietly caching: when another user asked the same syntax question earlier, the (query, response) pair was stored as a verbatim turn-pair. On your request, the memory router found it with a 0.97 similarity score, injected it into a cheap Haiku call for verification, the confidence gate (Normalised Sequence Probability >= 0.50) approved it, and you received the answer at the cost of a Haiku call instead of the premium model. You never noticed the difference.

## Use Cases

**Scenario 1: A startup deploying an AI support agent.** The startup processes 10,000 customer conversations per month. Without cost management, every call goes through Opus at $0.015 per call -- $4,500/month. They plug in Lyra's economics module. The tier router automatically downgrades password resets, store hours, and account lookups (simple_lookup tasks) to Haiku at $0.00025 per call. Standard troubleshooting (standard tasks) goes to Sonnet at $0.003. Complex technical debugging (complex_reasoning) stays on Opus. The BudgetController enforces a $1,500/month hard cap. Monthly bill drops to $1,200 -- 73% savings -- while customer satisfaction stays flat because 85% of conversations never needed Opus.

**Scenario 2: Enterprise cost allocation across teams.** A large organization has five product teams sharing a $50,000/month LLM budget. Each team has a different profile: documentation (high output tokens, simple generation), data analysis (large input contexts, medium complexity), engineering (many small agent-loop calls), research (deep reasoning, few calls). Lyra's BudgetController supports per-provider budgets and session-level tracking. The ProviderCostRecord aggregates cost per provider per team. The RouterConfig embeds a `max_budget_usd` field that can be set per session context. When the engineering team's agent loops overshoot, the Router automatically downgrades their non-critical sub-agent calls (status checks, progress reports) to the fast tier, keeping their budget within limits without blocking their work.

**Scenario 3: Off-peak batch processing with cost-aware routing.** A nightly job processes 50,000 support ticket summaries. These are latency-tolerant batch operations. Lyra's static tier router routes them through the fast model by default. But for the ~10% of tickets that require complex multi-step reasoning (account recovery, fraud investigation), the budget-aware fallback chain allows escalation to the mid-tier model only if the batch budget has capacity. The BudgetController emits a warning if the batch approaches its $20 nightly budget, and the Router prunes further escalations. The work still gets done -- lower-quality summaries for complex tickets rather than none at all -- because cost awareness is integrated into the routing decision, not imposed as an afterthought.

## Related Work

### Papers

| Paper | Venue | Relevance to Lyra Economics | Note File |
|-------|-------|----------------------------|-----------|
| FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance -- Chen et al., arXiv:2305.05176v1 | ICML 2023, Stanford | **Primary**: LLM cascade (cheapest-first ordered chain, DistilBERT scorer), semantic cache (21% hit rate, 95% savings), complementarity (MPI matrix, ~6% GPT-4 errors answered by GPT-J) | `docs/lyra-upgrade/notes/papers/2305.05176v1.md` |
| RouteLLM: Learning to Route LLMs with Preference Data -- Ong et al., arXiv:2406.18665v4 | ICLR 2025, UC Berkeley/Anyscale/Canva | **Primary**: Binary routing with matrix factorization, 3.66x cost savings at 95% GPT-4 quality, cross-model generalization, open-source framework | `docs/lyra-upgrade/notes/papers/2406.18665v4.md` |
| BEST-Route: Adaptive LLM Routing with Test-Time Optimal Compute -- Ding et al., arXiv:2506.22716v1 | ICML 2025, Microsoft | **Primary**: Multi-head router (DeBERTa-v3-small 44M) + best-of-N, 60% cost reduction with <1% quality drop, specialist routing beats GPT-4o on coding | `docs/lyra-upgrade/notes/papers/2506.22716v1.md` + `docs/lyra-upgrade/notes/web/microsoft__best-route-llm.md` |
| Small Language Models are the Future of Agentic AI -- Belcak et al., arXiv:2506.02153v2 | NVIDIA Research, 2025 | **Strategic**: SLM-first architecture, 10-30x cheaper, 60-70% agent queries replaceable, 6-step conversion pipeline (S1-S6) | `docs/lyra-upgrade/notes/papers/2506.02153v2.md` |
| Cost-Awareness in Tree-Search LLM Planning: A Systematic Study -- Zhang et al., arXiv:2505.14656v2 | Emory + UC Merced | **Supporting**: Budget feasibility filter, Bi-Search 87% success rate (LOOSE budget), LLMs miss infeasibility 36-89% of time | `docs/lyra-upgrade/notes/papers/2505.14656v2.md` |
| IdleSpec: Exploiting Idle Time via Speculative Planning for LLM Agents -- Choi et al., arXiv:2605.22154v1 | KAIST + Amazon AGI, 2026 | **Supporting**: 34.6% idle-time utilization, +5.1% accuracy (Gemini-2.5-Flash), Thompson-sampled dual-strategy drafting | `docs/lyra-upgrade/notes/papers/2605.22154v1.md` |
| Fast Inference from Transformers via Speculative Decoding -- Leviathan et al., arXiv:2211.17192v2 | ICML 2023 Oral, Google | **Supporting**: 3.4x walltime speedup, exact distribution guarantee, API-blocked at token level for Lyra's deployment | `docs/lyra-upgrade/notes/papers/2211.17192v2.md` |
| RMoA: Optimizing Mixture-of-Agents through Diversity Maximization -- Xie et al., arXiv:2505.24442v1 | Meituan + ECNU + Tsinghua, 2025 | **Supporting**: Greedy diversity selection with BGE-m3 embeddings, 31-53% cost reduction vs MoA, K=3 optimal | `docs/lyra-upgrade/notes/papers/2505.24442v1.md` |
| SELF-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection -- Asai et al., arXiv:2310.11511v1 | UW + AI2 + IBM, 2023 | **Supporting**: On-demand retrieval gating (54.9% retrieval usage), learned reflection tokens gate cost by avoiding unnecessary retrieval | `docs/lyra-upgrade/notes/papers/2310.11511v1.md` |

### Books

| Title | Relevant Chapters | Key Citations | Note File |
|-------|-------------------|---------------|-----------|
| Architecting Generative AI Applications (Kuligin, O'Reilly 2024) | Ch 1: Cost-Latency-Quality Triangle; Practice 7: LLM instrumentation; Practice 10: Context budgeting | Cost varies 100x across models; log every call with tokens+cost+latency; budget context window proactively | `docs/lyra-upgrade/notes/books/architecting-generative-ai-applications-playbook.md` |
| Agentic Design Patterns (Gulli, O'Reilly 2025) | Ch 2: Routing; Ch 16: Resource-Aware Optimization; Ch 19: Evaluation | Complexity-based tiering; "For high-throughput, use rule-based or embedding routing"; track token usage for cost optimization | `docs/lyra-upgrade/notes/books/agentic-design-patterns-playbook.md` |
| Generative AI Design Patterns (O'Reilly 2025) | Pattern 24: Small Model Cascade; Pattern 26: Inference Optimization; Pattern 28: Long-Term Memory | 3-tier model strategy (BEST/DEFAULT/SMALL); cost budgets per user/session; anti-pattern: ignoring long context cost | `docs/lyra-upgrade/notes/books/generative-ai-design-patterns-playbook.md` |

### Web / Repos

| Source | Key Content | Note File |
|--------|-------------|-----------|
| Anthropic Claude Code Costs docs (code.claude.com/docs/en/costs) | ~$13/dev/day average, 7x team token multiplier, rate limit sizing per team size, /usage command, auto-compaction cost savings | `docs/lyra-upgrade/notes/web/https___code_claude_com_docs_en_costs.md` |
| microsoft/best-route-llm (GitHub, MIT license) | Production router implementation, DeBERTa-v3 multi-head router training pipeline, proxy reward model training code | `docs/lyra-upgrade/notes/web/microsoft__best-route-llm.md` |
| RouteLLM (GitHub, open source) | Framework for training, serving, and evaluating LLM routers; matrix factorization router trains on single 8GB GPU | (Referenced in `docs/lyra-upgrade/notes/papers/2406.18665v4.md`) |

### Comparison Table

| System | Routing Strategy | Budget Enforcement | Cache Awareness | Multi-Provider | Effort Mapping | Cost Dashboard |
|--------|-----------------|-------------------|-----------------|----------------|----------------|----------------|
| FrugalGPT | LLM cascade (cheapest-first) | Expected-cost constraint | Semantic + exact-match cache | Yes (12 APIs surveyed) | No | No |
| RouteLLM | Learned binary router (matrix factorization) | Cost threshold alpha | No | Yes (cross-model generalisation) | No | No |
| BEST-Route | Learned multi-head (N-class) + best-of-N | Cost-quality threshold sweep | No | No (single-framework routing) | No | Evaluation plots only |
| Claude Code | Manual model switching (`/model`), manual effort (`/effort`) | Session-level `/usage-credits` (Pro/Max) | Prompt caching (automatic, per-provider) | No (Anthropic-only) | Yes (4-level effort menu) | Yes (`/usage` command) |
| **Lyra (implemented)** | Static tier router + memory-augmented cache router + learned scaffold | BudgetController (per-session, per-provider) with 80% warning, 100% critical | Cross-agent verbatim turn-pair cache with hybrid BM25+cosine retrieval | Yes (Anthropic, OpenAI, DeepSeek, Google, open-weights) | 6-level effort scale with per-provider translation | Planned |
| **Lyra (planned)** | FrugalGPT cascade + BEST-Route multi-head + RouteLLM MF + SLM specialization | Budget-aware tree search; IdleSpec speculative planning | Prompt-cache hit-rate optimization; session-coherent KV-cache orchestration | Multi-provider with learned router cross-model generalisation | Dynamic effort calibration | `/cost` dashboard with per-model breakdown, cache-hit rate, latency percentiles |

### What Lyra Borrows and Where It Diverges

From **FrugalGPT**, Lyra borrows the LLM cascade paradigm (cheapest-first ordered chain, DistilBERT-style confidence scoring) and the semantic cache concept (embedding-similarity retrieval for ~21% hit rate). Lyra diverges by planning a parallel-router deployment (BEST-Route style) for latency-sensitive interactive queries alongside the cascade for batch tasks -- the two strategies complement each other.

From **BEST-Route**, Lyra borrows the multi-head DeBERTa-v3-small router architecture with KxN classification heads and the proxy-reward-model-based best-of-N selection. Lyra diverges by wrapping this inside a multi-provider fallback chain (BEST-Route is single-provider) and adding a cross-agent memory layer that BEST-Route does not provide.

From **RouteLLM**, Lyra borrows the matrix-factorisation preference model and the open-source framework for training on single-8GB-GPU hardware. Lyra diverges by planning an N-way extension (RouteLLM is binary only) and by targeting multi-agent routing rather than single-query routing.

From the three **O'Reilly books**, Lyra borrows the principle of cost as a first-class design metric (log every call, budget proactively, tier by complexity). Lyra diverges by implementing budget enforcement as an active constraint on routing decisions rather than a post-hoc monitoring tool.

## Method

### Architecture

Lyra's economics module is a layered system spanning three packages:

```
src/lyra/economics/        -- Budget tracking and enforcement
src/lyra/routing/          -- Model selection, routing decisions, cache-aware routing
src/lyra/effort/           -- Effort-to-provider-API translation
```

```mermaid
flowchart TD
    subgraph Economics["economics/ -- Budget & Cost"]
        BC[BudgetController]
        PCA[ProviderCostRecord]
        BA[BudgetAlert]
    end

    subgraph Routing["routing/ -- Model Selection"]
        MR[ModelRouter<br/>static tier router]
        LR[LearnedRouter<br/>BEST-Route multi-head]
        MAR[MemoryAugmentedRouter<br/>cross-agent cache]
        PRM[ProxyRewardModel<br/>DeBERTa-v3-large]
        MFM[MatrixFactorPreferenceModel<br/>RouteLLM-style]
    end

    subgraph Effort["effort/ -- Effort Mapping"]
        EM[EffortManager]
        EML[EffortLevel<br/>LOW to ULTRACODE]
        EMM[EffortMapping<br/>per-provider translation]
    end

    subgraph Types["routing/provider/types.py"]
        RD[RouteDecision]
        RE[CostEstimate]
        RC[RouteContext<br/>budget_remaining]
        TU[TokenUsage]
    end

    U[User Query] --> MR
    MR --> BC
    BC --> RD
    MR --> RC
    RC -->|budget_remaining check| BC
    MR --> EM
    EM --> EMM
    MR -->|memory fallback| MAR
    MR -->|learned fallback| LR
    LR --> PRM
    LR --> MFM
    BC --> BA
    BC -.-> PCA
```

### Key Interfaces

**BudgetController** (`src/lyra/economics/budget.py`): Central class for session-level and per-provider budget enforcement.

- `__init__(session_budget=0.0)`: 0 = unlimited.
- `set_provider_budget(provider, budget)`: Per-provider cap.
- `record_cost(provider, cost) -> list[BudgetAlert]`: Records cost, checks budgets, returns alerts.
- `check_budgets() -> list[BudgetAlert]`: Checks session (80% warning, 100% critical) and per-provider budgets.
- `session_budget`, `session_cost`, `session_remaining`, `session_usage_ratio`: Property-based access for workflow scripts.
- `reset_session()`: Clears session state while preserving provider budgets.
- `to_dict()`: Serializes state for persistence.

**ProviderCostRecord** (`src/lyra/economics/budget.py`): Per-provider tracking with `total_cost`, `request_count`, `last_request`, `average_cost`.

**BudgetAlert** (`src/lyra/economics/budget.py`): Immutable dataclass with `level` (INFO/WARNING/CRITICAL), `message`, `current_cost`, `threshold`, `provider`, `timestamp`.

**ModelRouter** (`src/lyra/routing/provider/router.py`): Static tier router.

- `route(task_type, context) -> RouteDecision`: Maps task type (simple_lookup, standard, complex_reasoning, research, etc.) to effort level, selects model tier (fast/smart/premium) per provider, builds fallback chain.
- `complete_with_fallback(request, context) -> CompletionResponse`: Executes completion with cost-check before each provider attempt; skips if `cost_estimate > budget_remaining`.
- `session_cost`: Accumulated cost in USD.
- `register_provider(name, backend, models)`: Registers a provider with its adapter and model list.

**MemoryAugmentedRouter** (`src/lyra/routing/memory_router.py`): Compound cache router with three layers: (1) static prefix cache (transparent, provider-handled), (2) cross-agent memory (hybrid BM25+cosine retrieval, 0.95 similarity threshold, confidence-gated cheap-model execution), (3) diversity-kept context (greedy Jaccard-distance selection, RMoA pattern).

- `route(query, task_type, recent_outputs) -> MemoryRouterLayer`: Tries layers in order.
- `MemoryRouterMetrics`: Tracks `cache_hit_rate`, `acceptance_rate`, `cost_reduction_pct`.
- `confidence_gate(response, threshold) -> ConfidenceDecision`: NSP-based gate (geometric mean of token logprobs). ACCEPT if NSP >= 0.50.

**LearnedRouter** (`src/lyra/routing/learned_router.py`): DeBERTa-v3-small multi-head architecture (BEST-Route) in cold-start state.

- `select(query, query_embedding, candidates, quality_threshold) -> ScoredCandidate`: Evaluates (model, effort, n) triples, filters by match probability >= 0.90, selects cheapest qualifying.
- `generate_training_data(queries, generate_fn)`: Generates 20 responses per query per model config for training.
- `ProxyRewardModel`: DeBERTa-v3-large (304M) for best-of-N scoring; falls back to NSP heuristic.
- `MatrixFactorPreferenceModel`: RouteLLM-style MF; cold-start state.

**EffortManager** (`src/lyra/effort/manager.py`): Maps six effort levels (LOW, MEDIUM, HIGH, XHIGH, MAX, ULTRACODE) to provider-specific parameters.

- `map_effort(level, provider) -> EffortMapping`: Returns budget_tokens (Anthropic), thinking_instruction (DeepSeek, Google, open-weights), reasoning_effort (OpenAI), max_tokens_per_turn, orchestration_enabled.
- `record_calibration(provider, level, accuracy, tokens_used, latency_ms)`: Feeds dynamic effort calibration (adjusts budget based on measured accuracy vs target).
- `save()/load()`: Session persistence; non-persistent levels (MAX, ULTRACODE) saved as HIGH.

### Data Model

```mermaid
classDiagram
    class BudgetController {
        +session_budget: float
        +session_cost: float
        +session_remaining: float
        +session_usage_ratio: float
        +record_cost(provider, cost): list~BudgetAlert~
        +set_provider_budget(provider, budget)
        +check_budgets(): list~BudgetAlert~
        +to_dict(): dict
    }
    class ProviderCostRecord {
        +provider_name: str
        +total_cost: float
        +request_count: int
        +last_request: datetime
        +average_cost: float
        +record_request(cost)
    }
    class BudgetAlert {
        +level: BudgetAlertLevel
        +message: str
        +current_cost: float
        +threshold: float
        +provider: str
        +timestamp: datetime
    }
    class RouteDecision {
        +provider_name: str
        +model: str
        +effort: EffortLevel
        +fallback_chain: tuple
        +estimated_cost: CostEstimate
    }
    class CostEstimate {
        +input_cost: float
        +output_cost: float
        +total_max_cost: float
    }
    class RouteContext {
        +task_type: str
        +estimated_complexity: str
        +budget_remaining: float
    }
    class MemoryAugmentedRouter {
        +cache_hit_threshold: float
        +memory_search_k: int
        +confidence_threshold: float
        +diversity_k: int
        +metrics: MemoryRouterMetrics
        +route(query): MemoryRouterLayer
    }
    class LearnedRouter {
        +quality_threshold: float
        +state: LearnedRouterState
        +select(query): ScoredCandidate
        +generate_training_data(queries)
    }
    class EffortManager {
        +current_level: EffortLevel
        +map_effort(level, provider): EffortMapping
        +record_calibration(...)
    }
    BudgetController --> ProviderCostRecord
    BudgetController --> BudgetAlert
    ModelRouter --> RouteDecision
    ModelRouter --> CostEstimate
    ModelRouter --> RouteContext
    MemoryAugmentedRouter --> MemoryRouterMetrics
    LearnedRouter --> ProxyRewardModel
    LearnedRouter --> MatrixFactorPreferenceModel
    EffortManager --> EffortMapping
```

### Implemented

The following components are implemented and operational:

**BudgetController** (`src/lyra/economics/budget.py`, 299 lines): Fully implemented. Session budget enforcement with configurable warning threshold (default 80%). Per-provider budget caps. Alert generation at warning and critical levels. Serialization via `to_dict()`. The `record_or_drain` method provides a symmetrical API for dual-use patterns.

**ProviderCostRecord** (`src/lyra/economics/budget.py`): Fully implemented. Tracks per-provider `total_cost`, `request_count`, `last_request`, `average_cost`.

**ModelRouter (static tier router)** (`src/lyra/routing/provider/router.py`, 346 lines): Fully implemented. Maps 9 task types (simple_lookup, standard, complex_reasoning, research, code_generation, code_review, security_scan, debugging, agentic) to effort levels. Provides `complete_with_fallback()` with cost-check before each provider attempt -- skips candidates whose `total_max_cost > budget_remaining`. Supports 4 providers (Anthropic, OpenAI, DeepSeek, Google) with per-provider model tier definitions. Tracks `session_cost` as accumulated USD.

**MemoryAugmentedRouter** (`src/lyra/routing/memory_router.py`, 637 lines): Fully implemented. Three-layer compound routing: (1) static prefix cache, (2) cross-agent memory with hybrid BM25+cosine retrieval and confidence-gated cheap-model execution, (3) diversity-kept context with greedy Jaccard-distance selection (RMoA pattern). Target metrics on the Knowledge Access paradigm: 58.5% total cost reduction, 69% quality recovery from an 8B model. The memory hardware abstraction (`MemoryStore` protocol) supports pluggable backends (Milvus, FAISS, in-memory dict).

**LearnedRouter** (`src/lyra/routing/learned_router.py`, 681 lines): Scaffold implemented in cold-start state. DeBERTa-v3-small multi-head architecture (BEST-Route). `ProxyRewardModel` with NSP heuristic fallback. `MatrixFactorPreferenceModel` with uniform cold-start fallback. `generate_training_data()` method ready for ~8K queries x 8 models x 20 responses = 1.28M training-data generation. Default candidate set covers 8 models across 3 tiers (Haiku, Sonnet, Opus, GPT-4o-mini, GPT-5, DeepSeek Chat/Reasoner, Llama-3.1-8B) with up to 5 sampling depths and appropriate effort levels. In cold-start, `select()` defaults to `_static_fallback()` which picks the Sonnet-tier at MEDIUM effort with N=1.

**EffortManager** (`src/lyra/effort/manager.py`, 531 lines): Fully implemented. Six-level effort scale (LOW=1024 to MAX=32000 reasoning tokens) with ULTRACODE = XHIGH + orchestration toggle. Per-provider translation for Anthropic (budget_tokens), OpenAI (reasoning_effort), DeepSeek (thinking instruction), Google (thinking instruction), open-weights (prefix-based). Provider effort capabilities with automatic clamping. Dynamic effort calibration: records accuracy-cost-latency data points and adjusts budgets proportionally when accuracy shortfalls are detected. Session persistence via `.lyra/config.json` with is_persistent gating (MAX and ULTRACODE are session-only, restored as HIGH on reload).

**Types and interfaces** (`src/lyra/routing/provider/types.py`): Fully implemented. `CostEstimate`, `RouteDecision`, `RouteContext` (with `budget_remaining`), `TokenUsage`, `CompletionRequest`, `CompletionResponse`, `ModelInfo` (with `input_cost_per_1k` and `output_cost_per_1k`). Every provider adapter must implement `cost_estimate()`.

**MemoryEntry** (`src/lyra/routing/memory_router.py`): Fully implemented. Frozen dataclass with `query`, `response`, `success`, `confidence`, `cost`, `embedding`, `timestamp`, `task_type`, `metadata`. Each entry stores the monetary cost of the generating LLM call, enabling cost-aware retrieval decisions.

**RouterConfig** (`src/lyra/routing/provider/config.py`): Fully implemented. Loads from `.lyra/settings.json` with defaults. Key economics fields: `max_budget_usd` (default 10.0), `fallback_chain` (ordered provider fallback), `fast_model`, `smart_model`, `premium_model`.

### Planned

**LLM cascade routing (FrugalGPT-style):** Sequential cascade with DistilBERT scorer for batch and background tasks. Cheapest-first ordered chain with learned quality thresholds. Planned per the plan file evidence synthesis (Section 6, Technique A). Trigger: after learned router training pipeline is stable.

**Cost dashboard (`/cost` command):** Per-session token and cost breakdown, per-provider and per-model spend, cache-hit rate, projected monthly cost, latency p50/p95/p99. Modeled on Claude Code's `/usage` command (notes at `docs/lyra-upgrade/notes/web/https___code_claude_com_docs_en_costs.md`). Also implement per-workstream cost tracking (Architecting Generative AI Applications, Practice 7). Trigger: user-facing deployment with multi-user support.

**Cost-aware tree search (Budget-Aware MCTS):** Budget feasibility filter in Lyra's multi-step tool-call planning. Computes `accumulated_cost + minimum_remaining_cost` at each reasoning step. Prunes branches exceeding budget. Based on Cost-Augmented MCTS (arXiv:2505.14656v2). Expected: Bi-Search-level efficiency gains (0.96 vs MCTS 0.51 in tight-budget regimes). Trigger: when Lyra's planning module has multi-step tool-call sequences.

**Idle-time speculative planning (IdleSpec):** Dual-strategy (progressive + recovery) drafting during tool-execution idle windows. Beta-Bernoulli Thompson sampling for strategy selection. Expected: 34.6% idle-time utilization, +5.1% accuracy at near-zero latency overhead. Trigger: after measuring Lyra's actual idle ratio -- prerequisite: idle ratio > 5x and ultra-short ratio < 0.3.

**Session-coherent KV-cache orchestration:** Maintain KV-cache for the static session envelope across turns. Inject only delta (new tool result, new user turn). Open-weights tier only (where `past_key_values` is accessible). ~70-80% approximate savings for API-only providers via prompt caching at turn boundaries. Trigger: after multi-provider deployment with open-weights tier.

**SLM specialization pipeline:** 6-step conversion pipeline (arXiv:2506.02153v2): instrument LM calls, curate data, cluster by task, select SLMs, fine-tune via LoRA/QLoRA, iterate. Target: 60-70% of agent queries replaceable by fine-tuned SLMs at 10-30x lower cost. Trigger: after 10K+ accumulated queries per task cluster.

**Learned router training (BEST-Route + RouteLLM):** Full training pipeline: generate 20 responses per query per model (target 8K queries x 8 models = 1.28M generations), train DeBERTa-v3-large proxy reward model, train DeBERTa-v3-small multi-head router. Also train RouteLLM matrix-factorization preference model on Lyra's own preference data (from eval runs). Trigger: after cold-start data collection period (estimated 2-3 sprints).

**Dynamic effort calibration (breakthrough):** Automated per-provider, per-model, per-task-type effort-level optimization. Collects accuracy-cost-latency triples during operation; uses them to adjust `budget_tokens` allocations. The scaffold (`EffortManager.record_calibration`) is already implemented; the closed-loop optimization (auto-adjust effort levels based on calibration data) is planned.

**Prompt-cache hit-rate optimization:** Static prefix (system prompt, skill frontmatter, tool definitions) designed for 90% cache-hit rate. Staggered parallel session starts to maximize cache reuse. 5-minute TTL management. Semantic cache (embedding-based, ~21% hit rate improvement) and completion cache (exact-match, ~8% hit rate, ~99% savings per hit). Both techniques from FrugalGPT (arXiv:2305.05176v1).

**RMoA diversity-based response selection:** Embedding-based diversity maximization for multi-agent consensus. The `_greedy_diversity_select` method is already implemented with token-set Jaccard distance; production deployment should use BGE-m3 embeddings per the RMoA paper (arXiv:2505.24442v1). Estimated: 31-53% cost reduction vs standard Mixture-of-Agents.

## Debate (Trade-offs)

The economics module's design choices were the subject of recorded debate involving a Senior Performance Engineer, a Skeptic, a Research Lead, and an Architecture Lead (full record in `docs/lyra-upgrade/plans/21-economics.md`).

### Trade-off Table

| Decision | Win | Cost | Resolution |
|----------|-----|------|------------|
| Static tier router as default, learned router as planned upgrade | Deployable immediately; zero training cost; works with any provider | Does not adapt to distribution shift; no learned cost-quality Pareto frontier | Static router handles 85%+ of queries correctly (task-type-to-effort mapping covers all 9 defined types). Learned router added in Phase 2. |
| Cascade (FrugalGPT) for batch, parallel routing (BEST-Route) for interactive | Latency-adaptive: cascade is cheap for batch, parallel routing is fast for interactive | Two routing strategies to maintain; inconsistent cost-quality profiles | Architecture already separates batch from interactive execution. Resolution: routing config, not architecture change. |
| BudgetController defaults: $10 session limit, 80% warning, 100% critical | Users get protection without configuration | $10 may be too high for some use cases, too low for others | Default is configurable via `RouterConfig.max_budget_usd`. Users override per session. |
| Cross-agent memory routing before learned routing | Immediate cost savings without training data; proven by Knowledge Access paper | Memory routing only works on repeated/similar queries; ~58% cost reduction vs 60-70% for learned routing | Both layers are complementary. Memory routing handles duplicates/similars; learned routing handles novel queries. |
| Per-provider budget caps | Prevents cost concentration risk on any single provider | Adds configuration overhead for multi-provider deployments | Optional feature -- caps default to 0 (unlimited). Only set when needed. |
| Effort level as a 6-item scale (LOW-ULTRACODE) | Portable across providers with different native APIs | ULTRACODE = XHIGH + orchestration is confusing without documentation | Design principle documented in code: ULTRACODE is NOT a 6th API budget tier. The `EffortManager.map_effort()` explicitly resolves ULTRACODE to XHIGH for API calls. |
| Memory store as a Protocol (no concrete implementation shipped) | Flexible -- deployer chooses Milvus, FAISS, or in-memory | No production memory backend until deployer provides one | Acceptable for an integration-level system. The in-memory dict pattern works for testing and single-user deployment. |

### Steelmanned Rejected Alternative: Dynamic rerouting based on real-time model cost fluctuations

The strongest alternative rejected was a system that monitors real-time per-token costs from each provider (pricing changes, tier discounts, spot pricing) and dynamically reroutes based on the cheapest option at the millisecond level. This was rejected for a single decisive reason: **LLM provider pricing changes at the month-to-quarter granularity, not the millisecond granularity.** The static tier mapping (with quarterly config updates) captures >99% of the available cost savings without the engineering complexity of real-time pricing feeds. Cost fluctuations within a billing period are negligible compared to the 10-100x cost differences between model tiers.

### When the Chosen Design Loses

- **Uniform workload profile:** If all queries are complex_reasoning (e.g., an architecture-design agent), the tier router always picks the premium model, providing zero cost savings. Learned routing would also fail here (no cheap model can do the work). The only solution is SLM specialization (planned, Phase 3) or caching.
- **Memory-first workloads:** If every query is unique (no repetition across sessions), the memory-augmented router provides zero benefit. The LearnedRouter (planned) is the fallback.
- **Budget-default power users:** If users never set budgets (`session_budget=0`, unlimited), the BudgetController does nothing. The plan file recommends defaulting to a $50/day soft limit.

### Open Questions

1. What is the optimal routing strategy mix (cascade vs parallel vs memory vs learned) for Lyra's actual workload distribution? This requires production profiling -- estimated after 1,000+ sessions.
2. Does the BEST-Route cross-model generalisation (Claude Opus/Sonnet routable with zero retraining, per RouteLLM) hold for Lyra's specific task distribution, or does distribution shift degrade routing accuracy?
3. Is the SLM-first architecture (NVIDIA position paper) genuinely cheaper than a centralized-LLM with aggressive caching, or does the economy of scale favor the LLM for Lyra's fleet size? The paper itself labels this "unsettled" (AV2).
4. What is Lyra's actual idle ratio (tool execution time / reasoning time) in production? This determines whether IdleSpec adoption is high-ROI (prerequisite: idle ratio > 5x).

**Trade-offs in brief.** The economics module makes a deliberate bet: static rules work for the common case, learned routing adds value for the edge case. Default budgets protect users who do not configure anything. Simple wins over complex for the 85% of queries that task-type mapping handles correctly. If your workload is mostly identical queries, the memory cache gives the biggest savings. If your workload is uniformly hard problems, no routing strategy helps much until SLM specialization ships.

## Conclusion

Lyra's economics module today provides a working foundation for cost-controlled LLM agent operation. The implemented components (BudgetController, static tier router, ProviderCostRecord, MemoryAugmentedRouter, EffortManager, cost estimation types, learned router scaffold) form a layered system that covers budget enforcement, cost-aware model selection, provider fallback with budget checks, cross-agent cache routing, and portable effort mapping.

The module enters production at a **Partially implemented** status. The budget enforcement and static routing are production-ready (tested, documented, with serialization and persistence). The memory-augmented router is functionally complete and ready for integration with a concrete memory backend. The learned router scaffold compiles and functions in cold-start mode but requires training data before delivering its primary value (learned cost-quality Pareto routing).

### Measured Results

No production benchmarks are available for the combined economics system. Individual component targets are drawn from cited sources:

- **BudgetController**: Sub-millisecond overhead per `record_cost()` call (measured: Python dataclass arithmetic).
- **Static tier router**: ~0.001s routing latency per call (measured: dict lookup + string comparison).
- **Memory-augmented router target**: 58.5% total cost reduction (35% novel + 47% similar + 18% duplicates) per Knowledge Access paradigm (Liu et al., arXiv:2603.23013v1). Quality recovery target: 69% of full-context large-model quality from an 8B model.
- **Learned router target (BEST-Route)**: 40-60% cost reduction with <1% quality drop, per Ding et al. (arXiv:2506.22716v1).
- **LLM cascade target (FrugalGPT)**: Up to 98% cost savings on structured tasks (HEADLINES dataset) per Chen et al. (arXiv:2305.05176v1).
- **Effort mapping**: Provider-specific API translation completes in <0.001s (dict lookup).

### Limitations

1. **No production memory backend shipped.** The MemoryAugmentedRouter requires a concrete `MemoryStore` implementation (Milvus, FAISS, or equivalent). The in-memory dict implementation is for testing only.
2. **Learned router is cold-start only.** The DeBERTa-v3-small multi-head architecture is scaffolded but not trained. The full training pipeline (1.28M generations, proxy RM training, multi-head training) is unstarted.
3. **No cost dashboard.** Users cannot currently inspect per-session, per-provider, or per-model cost breakdowns. The `/cost` command is planned.
4. **No LLM cascade routing.** FrugalGPT-style sequential cascade (DistilBERT scorer, learned quality thresholds) is not implemented. Batch tasks use the same static router as interactive tasks.
5. **No budget-aware tree search.** Cost-Augmented MCTS budget feasibility filter is not integrated into Lyra's planning module.
6. **No idle-time speculative planning.** Lyra does not exploit tool-execution idle windows for speculative drafting.
7. **No SLM specialization pipeline.** The 6-step SLM conversion pipeline (instrumentation, curation, clustering, selection, fine-tuning, iteration) is not started.
8. **Effort calibration is open-loop.** The `record_calibration` and `_apply_calibration` methods exist but the closed-loop optimization (auto-adjusting effort levels based on calibration data) requires production usage data to tune.

### Future Work

- **Learned router training (Phase 2, estimated 2-3 sprints):** Generate 8K training queries, train both RouteLLM matrix-factorization and BEST-Route multi-head routers. Requires eval-run data from Lyra's evaluation harness.
- **Cost dashboard (Phase 2):** Implement `/cost` command with per-session, per-provider, per-model breakdown, cache-hit rate display, latency percentiles, and cost projections.
- **LLM cascade routing (Phase 2):** Implement FrugalGPT-style cascade for batch and background tasks. Latency-adaptive selector to switch between cascade (batch) and parallel routing (interactive).
- **Budget-aware tree search (Phase 3):** Integrate cost feasibility filter into Lyra's multi-step tool-call planning. Trigger: when planning module supports multi-step sequences.
- **Idle-time speculative planning (Phase 3):** Implement IdleSpec-style dual-strategy drafting. Prerequisite: production idle-ratio measurement.
- **SLM specialization pipeline (Phase 4, 12-month strategic direction):** Instrument LM calls, collect 10K+ examples per task cluster, fine-tune specialist SLMs via LoRA/QLoRA. Trigger: accumulated usage data.
- **Session-coherent KV-cache orchestration (Phase 3):** Open-weights tier KV-cache reuse across turns. API-provider approximation at turn boundaries.
- **Dynamic effort calibration (ongoing):** Close the calibration loop -- auto-adjust effort levels based on measured accuracy, cost, and latency.

## Glossary

- **Best-of-N (boN)**: Generating N responses for the same query and selecting the best one via a quality scoring model (proxy reward model). More samples cost more but give higher quality.
- **Budget**: A dollar cap on how much a session or provider can spend on LLM calls. Lyra's BudgetController enforces soft (warning) and hard (critical) limits.
- **Budget feasibility filter**: A deterministic check during multi-step planning that prunes action sequences whose accumulated cost would exceed the remaining budget (Cost-Augmented MCTS).
- **Cache hit**: When a previously computed result (response, token prefix, or KV-cache state) can be reused instead of recomputed. Cache hits reduce cost and latency.
- **Cascade routing**: A strategy that tries the cheapest model first, then escalates to more expensive models only if the cheap model's output does not meet a quality threshold (FrugalGPT).
- **Confidence gate**: A mechanism that checks whether a cheap model's response has sufficient confidence (measured by Normalised Sequence Probability) to be accepted, or whether it needs escalation to a larger model.
- **Cost-Latency-Quality Triangle**: The fundamental trade-off in LLM system design: improving any one of cost, latency, or quality typically worsens one or both of the others.
- **DeBERTa-v3-small**: A 44-million-parameter neural network used as the shared backbone for BEST-Route's multi-head router. Small enough to add negligible overhead (~0.04s per prediction).
- **Diversity selection**: Choosing K maximally different responses from a larger set (via embedding cosine similarity or Jaccard distance) to reduce redundancy in multi-agent aggregation (RMoA).
- **Effort level**: Lyra's six-level scale (LOW through ULTRACODE) that controls how much reasoning budget the LLM spends on each query. Higher effort = more tokens = higher cost but potentially better quality.
- **Effort mapping**: The translation of Lyra's abstract effort level into provider-specific API parameters (Anthropic budget_tokens, OpenAI reasoning_effort, DeepSeek thinking instruction).
- **Fallback chain**: An ordered list of provider-model-effort combinations tried sequentially when the primary choice fails or exceeds budget.
- **FrugalGPT**: A system that routes queries through an ordered chain of LLMs (cheapest first) with a confidence scorer, achieving up to 98% cost savings while matching GPT-4 accuracy.
- **IdleSpec**: A technique that uses tool-execution waiting time (idle time) to speculatively draft future agent actions, recovering 34.6% of idle time for productive computation.
- **KV-cache (Key-Value cache)**: The intermediate state of a transformer model's attention layers during text generation. Reusing KV-cache across turns avoids recomputing the prefix, saving both time and money.
- **Learned router**: A machine learning model (typically DeBERTa-v3 or matrix factorization) that predicts which model configuration will produce the best cost-quality outcome for a given query.
- **LLM Cascade**: An ordered chain of language models from cheapest to most expensive. A query goes to the first model; if its answer is not reliable enough, it escalates to the next (more expensive) model.
- **Match probability**: The predicted probability that a given (model, sampling-depth) configuration will produce a response at least as good as a reference (premium) model on a given query (BEST-Route).
- **Memory-augmented routing**: Using a store of past (query, response, cost) pairs to answer similar queries cheaply, bypassing expensive model calls for repeated or near-identical queries.
- **Model router**: A component that decides which LLM provider and model to use for a given query, based on task type, effort level, remaining budget, and availability.
- **Normalised Sequence Probability (NSP)**: The geometric mean of per-token log probabilities. Used as a cheap heuristic for response quality confidence when a full reward model is not available.
- **Parallel routing**: Using a learned model to predict the optimal (model, effort, sampling-depth) configuration upfront, then calling only that one configuration (BEST-Route), avoiding sequential cascade latency.
- **Prompt caching**: An API-level feature that stores repeated input prefixes (system prompts, tool definitions) on the provider's side so they are not re-encoded on every call, reducing cost and latency.
- **Proxy reward model**: A smaller neural network trained to approximate a larger oracle reward model's quality scores. Used inside best-of-N selection to score candidate responses.
- **Provider**: A company or service that offers LLM APIs (Anthropic, OpenAI, DeepSeek, Google) or a self-hosted inference endpoint (open-weights).
- **RouterConfig**: Configuration object (from `.lyra/settings.json`) that sets default provider, model tiers, fallback chain, and maximum budget.
- **Session budget**: The total dollar amount allocated for LLM API calls within a single Lyra session. Configurable per session.
- **SLM (Small Language Model)**: A language model that fits on consumer hardware (typically under 10 billion parameters). 10-30x cheaper to run than frontier LLMs.
- **Speculative decoding**: A technique where a fast cheap model drafts multiple tokens, and a slow expensive model verifies them in parallel. Achieves 2-3x speedup with mathematically identical output (at the token level).
- **Static tier router**: A rule-based router that maps task types to fixed model tiers (fast/smart/premium) without learned prediction. Deployed now in Lyra.
- **Task type**: A classification of the user's query into categories like simple_lookup, standard, complex_reasoning, research, code_generation, etc. Used by the static tier router to select effort level.
- **Thinking instruction**: A prompt-level instruction appended to the system prompt (for providers without native budget_tokens API) to control reasoning depth. Used for DeepSeek, Google, and open-weights providers.
- **Token budget**: The reasoning budget in tokens, expressed as `budget_tokens` parameter in Anthropic's API (or equivalent for other providers). Controls how much the model "thinks" before responding.
- **Turn-pair**: A matched (query, response) pair stored in cross-agent memory for cache routing. Includes metadata: success flag, confidence score, monetary cost, timestamp.
- **ULTRACODE**: Lyra's highest effort level. It is equivalent to XHIGH in API budget (16,384 reasoning tokens) but additionally enables automatic workflow orchestration. It is NOT a distinct API budget tier.
- **Verbatim turn-pair cache**: A memory store that caches exact (query, response) pairs from previous agent calls. When a new query matches a cached pair (via hybrid similarity search), the cached response can be reused or used as context for a cheap-model verification call.
