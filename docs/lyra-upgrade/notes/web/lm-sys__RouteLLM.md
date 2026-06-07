# lm-sys/RouteLLM -- Deep-Read

## 1. Headline Feature & Mechanism

RouteLLM is a framework for serving and evaluating LLM routers. It learns to route user queries between a strong (expensive) model and a weak (cheap) model using preference data from Chatbot Arena. The headline claim: **reduce costs by up to 85% while maintaining 95% GPT-4 performance on MT-Bench, and >40% cheaper than commercial routing offerings at the same quality**.

**Core mechanism** -- a two-step decision per query:

1. **Predict** a "strong model win rate" for the query (a float in [0,1]) using one of four router strategies.
2. **Compare** that win rate to a user-configured threshold. If win_rate >= threshold, route to the strong model; otherwise route to the weak model.

The threshold is calibrated via quantiles over the Chatbot Arena dataset (e.g., "set threshold such that 50% of arena queries would be routed to the strong model"). At inference time, the call is delegated to LiteLLM, which supports 100+ model providers.

**Four router strategies** (all pretrained on GPT-4-1106-preview / Mixtral-8x7B-Instruct-v0.1, but claimed to generalize to other model pairs):

- **`mf` (Matrix Factorization)** -- The recommended router. Learns per-model embeddings (P matrix) and per-prompt embeddings (Q matrix) in a shared latent space (dim=128). At inference: embed query via OpenAI text-embedding-3-small, project through learned text_proj, compute strong-vs-weak win rate via sigmoid(model_embed * prompt_embed). Trained with pairwise ranking loss (BCEWithLogitsLoss). Architecture: `MFModel` extending `PyTorchModelHubMixin`.
- **`sw_ranking` (Similarity-Weighted Elo)** -- Embeds the incoming query with OpenAI text-embedding-3-small, computes cosine similarity to 55k+ arena battle conversations. Uses similarities as sample weights to re-compute Elo ratings via logistic regression (MLE with tie handling). Returns expected strong win rate from the weighted Elo scores.
- **`bert` (BERT Classifier)** -- Fine-tuned BERT for sequence classification with 3 labels (weak wins / tie / strong wins). Computes softmax over logits, returns 1 - P(tie or strong_win) as the "strong win rate".
- **`causal_llm` (LLM-based Classifier)** -- Fine-tuned Meta-Llama-3-8B that predicts a score [1-5] for a query (higher = weak model is more likely sufficient). Uses special tokens `[[1]]` through `[[5]]`. Returns P(score >= threshold) as routing probability. Requires GPU at inference.
- **`random`** -- Uniform random [0,1] baseline.

**The key insight**: The routers are trained on human preference judgments (which model produced a better response for a given query), not on explicit difficulty labels. The matrix factorization and SW ranking methods are both lightweight (no GPU needed for MF at inference; SW ranking needs an embedding API call). The BERT and Causal LLM routers are heavier but potentially more accurate.

## 2. Architecture & Core Modules

```
routellm/
├── controller.py              # Central Controller class (drop-in OpenAI SDK replacement)
├── openai_server.py           # FastAPI OpenAI-compatible server (port 6060)
├── calibrate_threshold.py     # CLI for calibrating cost-quality thresholds
├── routers/
│   ├── routers.py             # Abstract Router base + all 5 router implementations
│   ├── matrix_factorization/
│   │   ├── model.py           # MFModel (inference) + MODEL_IDS mapping (64 models)
│   │   └── train_matrix_factorization.py  # Training loop with PairwiseDataset
│   ├── similarity_weighted/
│   │   ├── utils.py           # Elo MLE, tier computation, preprocessing, OpenAI client
│   │   └── generate_embeddings.py  # Batch embedding generation for arena battles
│   └── causal_llm/
│       ├── model.py           # CausalLLMClassifier (score prediction [1-5])
│       ├── configs.py         # RouterModelConfig, prompt format configs
│       ├── llm_utils.py       # Model/tokenizer loading, OpenAI message formatting
│       ├── prompt_format.py   # PromptFormat for different model architectures
│       ├── system_ft_v5.txt   # System prompt for fine-tuned classifier
│       └── classifier_ft_v5.txt  # Classifier instruction template
├── evals/
│   ├── evaluate.py            # CLI evaluation runner + plotting + metrics (AUC, APGR)
│   ├── benchmarks.py          # Abstract Benchmark + MMLU/MTBench/GSM8K implementations
│   ├── mmlu/                  # MMLU precomputed responses (57 domains)
│   ├── gsm8k/                 # GSM8K precomputed responses
│   └── mt_bench/              # MT-Bench precomputed GPT-4 judgements
└── tests/
    ├── test_openai_client.py  # Unit test for Controller completion
    └── test_openai_server.py  # Unit test for FastAPI server
```

**Entry points**:
- `Controller` class in `controller.py` -- mimics `openai.OpenAI()` interface via `SimpleNamespace` magic (`client.chat.completions.create`)
- `python -m routellm.openai_server` -- launches FastAPI server
- `python -m routellm.calibrate_threshold` -- CLI threshold calibration
- `python -m routellm.evals.evaluate` -- CLI evaluation runner

**Data flow**:
1. User calls `client.chat.completions.create(model="router-mf-0.11593", messages=...)`
2. Controller parses model name -> router="mf", threshold=0.11593
3. Controller extracts last-turn prompt text from messages
4. Router's `calculate_strong_win_rate(prompt)` returns float
5. If win_rate >= threshold -> use strong_model, else use weak_model
6. Controller delegates to LiteLLM `completion()` with the chosen model

**Pattern**: Plugin architecture via `ROUTER_CLS` dict mapping router name to class. The abstract `Router` class requires implementing only `calculate_strong_win_rate()`. A `@no_parallel` decorator marks routers incompatible with pandas parallel_apply.

**Config**: YAML file mapping router names to HuggingFace dataset/checkpoint paths. A default `GPT_4_AUGMENTED_CONFIG` is hardcoded in `controller.py` matching `config.example.yaml`.

## 3. Performance/Benchmarks

**From the paper and README** (based on GPT-4-1106-preview / Mixtral-8x7B-Instruct-v0.1 pair):

| Metric | Value |
|--------|-------|
| Cost reduction vs always-GPT-4 | Up to 85% |
| Performance retention on MT-Bench | 95% of GPT-4 |
| Cost vs commercial routers (at same quality) | >40% cheaper |

**Benchmark suite in the repo**:
- **MT-Bench**: Multi-turn conversation quality judged by GPT-4 (precomputed judgements for the model pair). Primary metric: average score (1-10).
- **MMLU**: 57-domain multiple-choice knowledge benchmark (precomputed responses). Metric: accuracy %.
- **GSM8K**: Grade-school math word problems (precomputed responses). Metric: accuracy %.

**Metrics computed by evaluation framework**:
- **AUC** (Area Under the Curve): Accuracy integrated over strong-model-call percentage.
- **APGR** (Area under the Performance Gain Ratio): Normalized AUC relative to weak-only and strong-only baselines.
- **Strong-model call percentages at quality targets**: "20% qual", "50% qual", "80% qual" -- what % of calls go to strong model to achieve 20/50/80% of the quality gap between weak and strong.

**Evaluation methodology**: For each router, thresholds are evenly quantile-split into bins. For each bin threshold, accuracy and model-call percentages are computed. The random router is averaged over 10 seeds for reproducibility. Results are cached per router as `.npy` files.

## 4. Trade-offs

**Wins**:
- Drop-in replacement for OpenAI's Python SDK (zero code change for existing integrations)
- OpenAI-compatible server means any OpenAI client library can use it immediately
- Four diverse router strategies with different cost/accuracy profiles
- Pre-trained routers available on HuggingFace, ready to use without training
- Threshold calibration is intuitive: "I want X% of queries to go to the strong model"
- Evaluation framework with standard benchmarks and multiple metrics (AUC, APGR)
- Plugin architecture makes adding new routers trivial (one abstract method)
- Generalization across model pairs -- routers trained on GPT-4/Mixtral work for Claude/Sonnet too
- Decontamination: all three benchmarks strip prompts that appear in the Chatbot Arena training data
- Apache 2.0 license -- permissive for commercial use

**Losses / Limitations**:
- **Requires OpenAI API key** even when routing between non-OpenAI models (needed for text-embedding-3-small embeddings for MF and SW ranking routers)
- **First-turn routing only** -- explicitly commented in controller.py line 109: "Our current routers were only trained on first turn data, so more research is required here."
- **Static threshold per request** -- no per-user or per-query-type dynamic threshold adjustment
- **Binary routing only** -- chooses between exactly two models (strong/weak), no multi-model ranking
- **Causal LLM router needs GPU** -- the Llama-3-8B classifier won't run on CPU practically
- **Cold start for SW ranking** -- needs to load 55k+ arena battle embeddings and recompute weighted Elo on every request (O(n) in arena size per query, though the embedding dot product is fast with numpy)
- **Router accuracy depends on distribution match** -- if your queries are very different from Chatbot Arena, calibration and routing quality degrades
- **Precomputed benchmark responses** lock evaluation to specific model pairs; evaluating on new model pairs requires re-running expensive SGLang inference
- **No streaming support branching** -- the server streams responses, but the routing decision is always made before any generation starts
- **No fallback on router failure** -- if the router errors (e.g., CausalLLM returns None), it defaults to the strong model (conservative but more expensive)

## 5. Design Rationale

- **Why threshold-based routing instead of learned cost functions?** -- Simplicity and user control. The threshold gives an intuitive dial: "what percentage of queries should go to the expensive model?" The paper shows this is nearly as good as optimal oracle routing.
- **Why last-turn prompt only?** -- The routers were trained on Chatbot Arena data, which mostly consists of single-turn comparisons. Multi-turn routing is noted as future work.
- **Why OpenAI embeddings for non-OpenAI routing?** -- text-embedding-3-small has the best quality/cost ratio and the MF model is trained with 1536-dim embeddings. This creates a dependency but avoids needing to host a separate embedding model.
- **Why quantile-based threshold calibration?** -- Maps directly to the intuitive user goal ("I want to use the expensive model for the top 50% of queries"). The quantile of win rates on a representative dataset gives the threshold.
- **Why matrix factorization as the recommended router?** -- It is the best combination of accuracy and speed. Unlike SW ranking (O(n) similarity search) and Causal LLM (8B parameter model on GPU), MF is just a learned dot product + sigmoid -- sub-millisecond per query once embeddings are computed. And it outperforms BERT in the paper.
- **Why LiteLLM for model calls?** -- Rather than building provider-specific integrations, LiteLLM provides a unified interface to 100+ LLM providers. This makes RouteLLM model-agnostic with zero additional integration work.
- **Why precomputed benchmark results?** -- Running GPT-4 and Mixtral on MMLU/GSM8K/MT-Bench costs significant time and money. Precomputing and caching means evaluating a new router takes only the (cheap) router inference time.

## 6. Transfer to Lyra

**Transferable Idea: Cost-Aware Query Router for Planner Tiering**

The core insight is that there is a long tail of simple queries that do not need the most expensive model -- a lightweight predictor can identify them with high accuracy.

**For Lyra**: Implement a **cost-aware router** that sits before the Lyra planner. When a user request arrives:
1. A lightweight classifier (a few hundred lines of PyTorch or scikit-learn) predicts whether the request is "simple" or "complex".
2. Simple requests are routed directly to a fast/cheap model (Haiku) for immediate handling.
3. Complex requests proceed to the full Lyra planner pipeline (Sonnet/Opus).

The router could be a simple logistic regression on query features (length, intent keywords, number of tool calls, task type from project memory) -- no expensive embeddings needed. Over time, feedback from actual routing decisions can be used to refine the threshold.

**Route**: This fits under **SS4.x (Routing/Planner subsystem)** -- specifically as a new module `lyra/planner/cost_router.py` that the planner consults before deciding which model tier to invoke.

**Impact: 6** -- Significant cost savings for Lyra users (potentially 40-60% reduction in LLM API costs) with minimal quality degradation for simple queries.

**Effort: 3** -- Moderate effort. No model training required; a simple feature-based heuristic or logistic regression. Integration is a single gating function in the planner. Requires collecting a small labeled dataset of past queries (simple vs complex from user interaction data).

**Tier: high** -- High value, low effort. The cost savings compound across all users.

**LICENSE**: Apache License 2.0 -- fully compatible with Lyra's licensing. Can copy/adapt code without restriction.

**Key files to study further**:
- `/routellm/routers/routers.py` -- `Router` base class and `route()` method (the pattern to replicate)
- `/routellm/controller.py` -- The `Controller.route()` flow (how routing decisions are made at inference time)
- `/routellm/calibrate_threshold.py` -- Threshold calibration methodology (how to set the right threshold for Lyra)
