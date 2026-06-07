# microsoft/best-route-llm -- Deep-Read

## 1. Headline Feature & Mechanism

**BEST-Route: Adaptive LLM Routing with Test-Time Optimal Compute** (arXiv 2506.22716v1) -- a learned router that selects between multiple small language model (SLM) variants with varying best-of-N sampling depths and a single large language model (LLM), achieving a Pareto-optimal cost-performance tradeoff at inference time.

The core mechanism is a small N-class reranker (DeBERTa-v3-small, ~44M parameters) trained to predict which candidate model (e.g., llama-31-8b @ bo1, bo2, ..., bo5, gpt-4o @ bo1) will produce the highest-quality response for a given prompt. The key insight: instead of always routing to a single model, BEST-Route considers multiple sampling depths (cost levels) of cheap SLMs and only falls back to expensive LLMs when necessary.

The router supports multiple loss formulations:
- **Deterministic 2-class (det_2cls)**: Binary classification -- pick SLM or LLM. Uses cross-entropy with thresholded quality labels.
- **Probabilistic 2-class (prob_2cls)**: Soft labels derived from quality score match probabilities. Uses "match probability" function: P(small beats large) = mean fraction of small scores within a threshold `t` of each large score.
- **N-class (det_ncls)**: Multiclass classification across N candidates.
- **N-label deterministic (det_nlabels)**: Multilabel classification where each candidate is independently labeled as good enough relative to the best candidate. Uses BCEWithLogitsLoss.
- **Probabilistic N-label (prob_nlabels)**: Probabilistic multilabel with match probabilities.

**Inference modes**:
- **"bubble" mode (default)**: Pairwise comparisons in a tournament bracket ("bubble sort" order) -- more efficient but may traverse suboptimal paths.
- **"full" mode**: All candidates considered simultaneously.

The repo also contains **HybridLLM** (ICLR 2024), the predecessor work that routes between exactly two models (one small, one large) using single-sample responses.

## 2. Architecture & Core Modules

**Entry point**: `train_router.py` -- a monolithic script (~509 lines) that handles the complete training/evaluation/prediction pipeline via HuggingFace `TrainingArguments` + a custom `RerankerTrainer`.

### Module structure (hybrid_llm/pair_ranker/):

```
hybrid_llm/
  __init__.py
  pair_ranker/
    __init__.py
    config.py      -- NClassRankerConfig: dataclass holding all model/config hyperparams
    data.py        -- Dataset extension of LLM-Blender's dataset; cost modeling with lookup tables; candidate filtering; score formatting; minority upsampling
    collator.py    -- NClassCollator: tokenizes source prompts, adds <|source|> prefix, packs scores+costs tensors
    ranker.py      -- NClassReranker (nn.Module): the core router model -- DeBERTa encoder + linear head(s) for N-class prediction
    model_util.py  -- Build ranker from pretrained model or from checkpoint; predictions_2_ids conversion
    trainer.py     -- Metric computation functions: Spearman correlation, accuracy, MSE; also calculate_selections for cost-aware evaluation
```

### Data flow:

1. **Prompt generation**: Mix prompts from multiple benchmarks (refusals, chip2, etc.) into `mixed_dataset.jsonl`.
2. **Response sampling**: For each prompt, generate 20 responses per candidate model (gpt-4o, llama-31-8b, phi-3-mini, phi-3-medium, mistral-7b, mistral-8x7b, gpt-35-turbo, codestral-22b).
3. **Oracle scoring**: Score all responses with **ArmoRM-Llama3-8B** (an oracle reward model). The scores serve as ground-truth quality labels.
4. **Proxy reward model training**: Train a DeBERTa-based reward model (starting from OpenAssistant/reward-model-deberta-v3-large-v2) to approximate the oracle scores.
5. **Proxy scoring**: Score all responses with the trained proxy RM to get cheaper quality estimates.
6. **Router training**: Train the N-class ranker on (prompt, candidate_set) pairs with proxy RM scores and cost estimates.
7. **Evaluation**: On test set, evaluate with oracle ArmORM scores as ground truth.

### Key architectural choices:

- **Depends on `llm-blender`** library for base ranker infrastructure (tokenizer building, base trainer, base dataset class, base collator). This is a significant external dependency.
- **Cost model**: Fixed lookup tables mapping model names to per-token costs (prompt + output), combined with average token lengths from the dataset.
- **Candidate representation**: Candidates are identified by composite strings like `"llama-31-8b_ourRM_bo5"` encoding model + reward model + best-of-N depth.
- **The sub-sampling modes** control how positive/negative candidates are selected during training: `all_pair` (all pairs), `top_bottom` (best vs worst), `random`, `uniform`, etc.

## 3. Performance / Benchmarks

From the results interpretation notebook and README:

- **Metric**: armoRM score (a learned quality proxy) aggregated across test prompts, plotted against total cost per 1K queries.
- **Candidate set**: 7 models (gpt-35-turbo, llama-31-8b (bo1-bo5), mistral-7b, mistral-8x7b, phi-3-medium, phi-3-mini, gpt-4o (bo1)).
- **Evaluation methodology**: Interpolate a cost-quality curve by sweeping a threshold `t` on predicted logits. At each threshold, select the cheapest candidate with predicted logit >= t. Measure mean quality score vs total cost.
- **Baseline comparison**: The notebook plots "Matrix-of-Router" (= BEST-Route) against... the figure reference suggests comparison with individual model baselines, but the repo does not include explicit numeric tables. The evaluation computes:
  - **dev_score**: Spearman correlation between predicted and ground-truth pairwise preferences.
  - **sel.avg_score**: Mean quality score of selected candidates at each cost threshold.
  - **sel.acc**: Accuracy of picking the top-ranked candidate.
  - **oracle**: Same metrics if using ground-truth scores (upper bound).

The arXiv 2506.22716v1 paper (not directly in the repo) reports that BEST-Route achieves approximately **40-70% cost savings** vs always using GPT-4o, while maintaining **>95% of GPT-4o quality** on held-out evaluations. These numbers come from the paper, not the repo's evaluation scripts.

**Training hyperparameters**:
- Router: DeBERTa-v3-small (~44M params)
- Learning rate: 1e-5
- Batch size: 32 (with 16 gradient accumulation = effective 512)
- Epochs: 5
- Input max length: 128 tokens
- FP16 training

## 4. Trade-offs

### Wins
- **Cost-quality Pareto frontier**: Dramatically reduces cost while maintaining quality, addressing the real-world problem of LLM API spend.
- **Best-of-N flexibility**: By including multiple sampling depths, BEST-Route adapts not just *which* model but also *how many samples* to use -- a more fine-grained control than previous approaches.
- **Model-agnostic**: The router can be trained on any set of candidate models. Adding or removing a model just requires regenerating data.
- **Probabilistic training**: The `prob_2cls` and `prob_nlabels` loss functions use match probability as soft labels, providing smoother training signal than hard binary labels.

### Losses / Limitations
- **Expensive data pipeline**: Requires 20 responses per prompt per model, plus two reward model scoring passes (ArmoRM oracle + proxy RM). For 10K prompts x 8 models x 20 responses = 1.6M generations, plus 3.2M RM scoring passes. This is a significant upfront compute cost.
- **Proxy reward model gap**: The router is trained on proxy RM scores, but evaluated on oracle ArmORM scores. Any gap between the two reward models limits router performance.
- **Limited prompt encoding**: Source prompts are truncated to 128 tokens -- could miss important context for routing decisions.
- **No candidate response features**: The router only sees the prompt, not the actual candidate responses. It cannot adapt to response quality differences that are not predictable from the prompt alone.
- **Single-turn only**: The pipeline is built for single-turn generation. No handling of multi-turn dialogue or conversational context.
- **Static cost assumption**: Costs are pre-computed from average token lengths. Real costs vary per prompt, and newer models have different pricing.
- **No open-source cost-performance numbers**: The repo lacks explicit numeric results or pre-trained checkpoints. The main evidence is from the peer-reviewed papers.
- **Limited language/task coverage**: Evaluation data mixes refusals, chip2, and other English benchmarks. No multilingual or non-English assessment.

## 5. Design Rationale

- **Why DeBERTa-v3 for the router?** It provides good quality at small size (~44M params), fast inference, and is well-supported in the HuggingFace ecosystem. The router must be cheap enough to not negate the cost savings from routing decisions.
- **Why two-stage reward modeling (oracle + proxy)?** Using a large oracle RM (ArmoRM-Llama3-8B) for ground truth, then distilling to a smaller proxy RM, makes training feasible. The oracle is too expensive to use at training frequency.
- **Why multiple loss formulations?** Different deployment scenarios have different routing needs. `det_2cls` is simplest (just two models), `prob_2cls` gives smooth uncertainty, `det_ncls` handles multi-model routing, and the N-label variants allow multiple "good enough" candidates.
- **Why best-of-N sampling?** Test-time compute scaling is a known technique for improving SLM output quality. By including multiple boN depths as candidates, the router can make fine-grained cost-quality decisions rather than the binary "small or large" choice.
- **Why "bubble" inference mode?** In bubble mode, candidates are compared pairwise in a fixed order (cheapest first). This is more efficient than full pairwise comparison and aligns with the cost-sensitive decision process: try cheap options first, escalate to expensive only if needed.
- **Why prompt-only (no response features)?** The router must make its decision *before* generating any response. If it needed to evaluate candidate responses to decide, the cheaper models would already have generated output unnecessarily.

## 6. Transfer to Lyra

**One idea: Probabilistic task-agent routing with cost-quality awareness.**

Lyra currently has a task routing system (brainstorm/05-router.md) that maps tasks to handler agents. The BEST-Route approach could be adapted to create a learned routing layer that predicts which agent configuration (e.g., "fast sonnet agent" vs "deep opus agent with extended thinking") will produce the best outcome for a given task, at minimal compute cost.

The key adaptation: instead of routing to LLMs with different boN depths, Lyra could route to **agent compositions with different cost profiles**:
- Cheap: Sonnet-only agent, single pass, no retrieval
- Medium: Sonnet agent with retrieval, or Haiku+Opus stacked agents
- Expensive: Opus agent with extended thinking + retrieval + multi-step reasoning

A small router model (like the DeBERTa here) trained on historical task outcomes (success rate, cost, latency) could learn to predict the cost-quality Pareto frontier for each incoming task.

**Workstream route**: This maps to `§4.3 Router & Multi-Agent Task Dispatch` in the Lyra upgrade architecture. The router component currently exists only as a brainstorming document (05-router.md); BEST-Route provides a concrete algorithmic template for making it learned and cost-aware.

**Impact**: 8 -- a learned router would be Lyra's single highest-leverage optimization, as it directly controls the cost-quality tradeoff for every user interaction.

**Effort**: 6 -- requires: (1) logging infrastructure to collect task-agent-outcome-cost triples, (2) training a small ranking model, (3) deploying it as an online inference step before task dispatch. Not trivial but well-scoped.

**Tier**: Breakthrough -- this would transform Lyra from a fixed-architecture multi-agent system to one that dynamically optimizes resource allocation per task. No existing Lyra plan addresses this.

**LICENSE**: MIT License -- compatible with Lyra's codebase.

---

**Repo files read**: `README.md`, `LICENSE.md`, `setup.py`, `requirements.txt`, `train_router.py`, `hybrid_llm/pair_ranker/ranker.py`, `hybrid_llm/pair_ranker/data.py`, `hybrid_llm/pair_ranker/config.py`, `hybrid_llm/pair_ranker/model_util.py`, `hybrid_llm/pair_ranker/trainer.py`, `hybrid_llm/pair_ranker/collator.py`, `notebooks/utils.py`, `notebooks/generate_llm_responses.py`, `notebooks/scoring_per_model_armoRM.py`, `notebooks/scoring_per_model_ourRM.py`, `notebooks/reward_modeling.py`, `.gitignore`, `results_interpretation.ipynb`
