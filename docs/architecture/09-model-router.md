# Model Router -- Deep Dive

## 1. Executive Summary

Lyra's Model Router implements a 3-tier cascading decision pipeline that routes every user task to the optimal AI model at the lowest possible cost. Rather than relying on a single model for all tasks -- which would waste capacity on trivial requests and under-serve complex ones -- the router progressively escalates task classification from cheap deterministic rules through lightweight semantic similarity to an online-learning neural contextual bandit. The cascade is designed so that Tier 1 (rule-based, zero marginal cost) handles 50-60% of all requests, Tier 2 (TF-IDF or embedding similarity, sub-millicent cost) handles another 20-30%, and Tier 3 (20-100ms neural inference, approximately $0.001 per call) catches only the remainder. The result is a router that makes roughly 80% of its decisions at near-zero cost while learning continuously from every outcome.

The router is budget-aware. A BudgetTracker implementing the Google BATS pattern divides a session's $5.00 cap into four regimes (HIGH, MEDIUM, LOW, CRITICAL) and dynamically downgrades model tier selections as the budget is consumed. A circuit breaker halts routing when the session limit is reached, preventing runaway spending. A ProviderRegistry holds pricing and capability data for nine models across five providers (Anthropic, DeepSeek, Google, OpenAI, OpenRouter), and the router's fallback chain degrades gracefully through provider tiers when the primary choice is unavailable or too expensive.

The architecture is grounded in the `ProviderBackend` protocol -- a normalization layer that abstracts message format, tool-call schema, streaming, and token accounting across all LLM providers. Every component above the API speaks to models through this single interface, enabling runtime provider swapping without code changes. A `CapabilityMatrix` maps per-provider capabilities (vision, audio, JSON mode, long context, thinking modes) and is queryable at routing time to filter models by task requirements.

The architecture grounds itself in the 2025 DecisionBench finding (arXiv:2605.19099) that routing fidelity across real-world LLM evaluation benchmarks is only 7.5-29.5% -- meaning the gap between what an oracle router would select and what current routers achieve is large. Lyra's approach closes this gap through three distinct mechanisms that operate at different latency and cost points, with a NeuralUCB online learner that provably converges toward the optimal policy as feedback accumulates.

**Memory-augmented routing** is the breakthrough addition: every query + its answer is cached in a cross-agent memory store with embedding similarity matching. Cache hits (similarity > 0.92) route directly to a cheap model with the cached answer as context, achieving a target >=40% per-session cost reduction. This is inspired by the Knowledge Access paper (arXiv 2603.23013), which demonstrates 69% of full-context 235B quality at 96% cost reduction through memory injection + confidence-based routing.

An **effort scale** (low/medium/high/xhigh/max/ultracode) provides a provider-neutral reasoning budget mapping. Each effort level maps to provider-specific parameters: Anthropic `budget_tokens`, DeepSeek extended thinking, GPT `reasoning_effort`, and prompt-level analogs for open-weight models. The mapping is configurable per deployment and enables consistent quality-latency tradeoffs across providers.

**Cascade fallback** ensures robustness: budget-driven tier downgrade (LOW/CRITICAL regimes downgrade expensive tiers), provider unavailability fallback (walks down tiers for any available provider), and a last-resort hardcoded fallback. The consensus router provides an additional multi-model verification path for critical decisions.

The model router is implemented in the `lyra-router` package at `packages/lyra-router/src/lyra_router/`. It contains 6 core modules (router.py, tiers.py, neural_ucb.py, budget.py, providers.py, models.py) plus the consensus router (consensus_router.py, verdict_combiner.py, dissent_detector.py) for multi-model verification of critical decisions. The test suite covers 63 test cases across 1,100+ lines of tests with 98% code coverage.

## 2. The 3-Tier Architecture

The cascade is the central pattern. Every call to `ModelRouter.route(task, context)` enters at Tier 1. If that tier returns a `TierResult` whose `confidence` meets the acceptance threshold (0.50 for Tier 1, 0.40 for Tier 2), the router returns immediately. Otherwise it falls through to the next tier. Tier 3 always returns a result, so the cascade is guaranteed to terminate.

```python
# From router.py -- the cascade in pseudocode
def route(self, task, context, force_tier=None):
    if force_tier is None or force_tier == 1:
        result = self._tier1.route(task, context)
        if result and result.confidence >= 0.50:
            return self._build_decision(result, tier_used=1, ...)

    if force_tier is None or force_tier == 2:
        result = self._tier2.route(task, context)
        if result and result.confidence >= 0.40:
            return self._build_decision(result, tier_used=2, ...)

    # Tier 3: always returns
    result = self._tier3.route(task, context)
    return self._build_decision(result, tier_used=3, ...)
```

The confidence thresholds (0.50, 0.40) encode an engineering judgement: it is better to spend a few extra milliseconds on semantic or neural routing than to make a wrong cheap decision that wastes API dollars downstream. The thresholds also reflect the inherent reliability of each tier's signal -- rules are cleanly categorical so 0.50 is a high bar; semantic matching is noisier so the bar is lower at 0.40; the neural tier is expected to handle ambiguity so it always returns something.

The `force_tier` parameter allows callers to bypass the cascade entirely. This is used in testing (`force_tier=3` to test the neural tier in isolation) and could be used in production for tasks that require a specific tier (e.g., a known-hard problem should skip rules and go straight to the neural tier).

### 2.1 Tier 1: Rule-Based

**Characteristics: 0-1ms latency, $0 cost, targets 50-60% hit rate.**

The rule tier (`RuleTier` in `tiers.py`) operates by scanning the task string against a set of priority-ordered rules. The ordering is deliberate: domain-specific safety-critical keywords are checked first, then trivial conversation patterns, then complexity-based keyword lists, and finally heuristics.

**Domain-specific rules (highest priority, confidence 0.85).** These are stored in `_DOMAIN_RULES` and route to `ModelTier.PREMIUM`:

```python
_DOMAIN_RULES = {
    "security": ModelTier.PREMIUM,
    "authentication": ModelTier.PREMIUM,
    "cryptography": ModelTier.PREMIUM,
    "payment": ModelTier.PREMIUM,
    "compliance": ModelTier.PREMIUM,
    "medical": ModelTier.PREMIUM,
    "legal": ModelTier.PREMIUM,
    "production deployment": ModelTier.PREMIUM,
    "infrastructure": ModelTier.PREMIUM,
}
```

These domains are non-negotiable -- sending a security audit prompt to a budget model would be irresponsible. The confidence of 0.85 reflects the fact that domain matches are strong signals but not absolute guarantees (a task might mention "security" in passing while being genuinely trivial). Note that 0.85 exceeds the 0.50 acceptance threshold, so domain matches always terminate at Tier 1.

**Trivial conversation patterns (confidence 0.95).** These are regex patterns matched against the start of the task string:

```python
_TRIVIAL_PATTERNS = [
    r"^(hi|hello|hey|yo|sup)\b",
    r"^(yes|no|yep|nope|yeah|nah)\b",
    r"^(ok|okay|thanks|thank you|thx)\b",
    r"^(good morning|good afternoon|good evening)\b",
    r"^(bye|goodbye|see you|cya)\b",
    r"^what('?s| is) up\b",
    r"^how are you",
]
```

Tasks matching these patterns route to `ModelTier.LOCAL_SLM` (a local small language model at zero cost) at 0.95 confidence. The high confidence reflects the fact that these patterns are unambiguous -- there is no circumstance in which "hello" should be routed to Opus.

**Keyword sets (confidence 0.80).** Five ordered lists, checked from most specific to least specific. The first matching keyword wins:

| Keyword Set | Examples | Complexity | Model Tier |
|---|---|---|---|
| AGENTIC | "build a complete", "autonomous", "multi-agent", "from scratch", "self-correcting", "orchestrate", "deploy to production", "end-to-end", "full pipeline" | AGENTIC | AGENTIC |
| COMPLEX | "architecture", "security audit", "performance optimization", "distributed system", "database schema", "design pattern", "migration strategy", "microservices" | COMPLEX | PREMIUM |
| MODERATE | "implement", "debug", "refactor", "write tests for", "add feature", "configure", "api endpoint", "database query", "middleware", "authentication" | MODERATE | STANDARD |
| SIMPLE | "what is", "define", "lookup", "convert", "translate", "syntax for", "example of" | SIMPLE | HAIKU |

The ordering by specificity is critical. "What is the architecture of a distributed system" contains both the SIMPLE keyword "what is" and the COMPLEX keyword "architecture". Because COMPLEX is checked first, the task is correctly classified as COMPLEX. If the order were reversed, every "what is X" question that mentioned architecture would be misclassified as simple.

**Heuristic fallbacks (confidence 0.55).** If no keyword matches, two heuristics fire:

- **Short tasks** (3 or fewer words) default to SIMPLE at 0.55 confidence. The logic: a 3-word task cannot express the nuance of a complex architectural question.
- **Questions** (ending in `?` or starting with wh-/how/can/is/do/does) default to SIMPLE at 0.55 confidence. The logic: most questions are factual lookups rather than complex analyses.

The 0.55 confidence for heuristics is intentionally below the 0.50 acceptance threshold. In practice, they pass because 0.55 >= 0.50, but the margin is thin enough that the confidence can be reduced by budget downgrades (which multiply by 0.9) and still remain above threshold for most cases.

**When Tier 1 returns None.** If none of the domain rules, patterns, keywords, or heuristics match, Tier 1 returns None and the cascade proceeds to Tier 2. This occurs for tasks that use unfamiliar vocabulary, are expressed in non-English languages, or are genuinely novel.

**Runtime extensibility.** `RuleTier.add_rule(keyword, tier)` adds custom domain rules that override the defaults. The router's `add_domain_rule` method delegates here. This is used for application-specific routing policies (e.g., a banking plugin could add "wire transfer" prepending PREMIUM without modifying the router source).

### 2.2 Tier 2: Semantic

**Characteristics: 5-50ms latency, <$0.001 cost, targets 20-30% hit rate.**

When Tier 1 cannot classify the task, the semantic tier (`SemanticTier`) attempts to match it against a labeled reference corpus using embedding similarity or TF-IDF cosine similarity.

**The reference corpus.** Twenty curated examples spanning all five complexity levels:

```
AGENTIC: "build a complete e-commerce application from scratch"
AGENTIC: "create an autonomous agent that researches topics and writes reports"
AGENTIC: "refactor the entire codebase to use dependency injection"
AGENTIC: "deploy a production-grade microservices cluster with monitoring"
COMPLEX:  "design the database schema for a multi-tenant SaaS platform"
COMPLEX:  "evaluate the trade-offs between PostgreSQL and MongoDB for our use case"
COMPLEX:  "perform a security audit of our authentication system"
COMPLEX:  "design a scalable event-driven architecture for real-time analytics"
MODERATE: "implement a JWT authentication middleware"
MODERATE: "write a function to parse CSV files with error handling"
MODERATE: "add pagination to the API endpoint"
MODERATE: "debug why the database connection pool is exhausted"
SIMPLE:   "what is the syntax for list comprehension in Python"
SIMPLE:   "convert this JSON to YAML"
SIMPLE:   "find all files modified in the last 24 hours"
SIMPLE:   "what does the git status command do"
TRIVIAL:  "hello"
TRIVIAL:  "yes"
TRIVIAL:  "thanks"
TRIVIAL:  "good morning"
```

The examples are carefully chosen to be representative of each complexity level while using distinct vocabulary. Note that the TRIVIAL examples are the same ones handled by Tier 1's regex patterns -- Tier 2 serves as a secondary check if for some reason the regex failed (e.g., a whitespace variation that the pattern didn't handle).

**Dual-backend design.** The tier has two backends, selected at initialization time:

1. **Sentence-transformers (primary).** If `all-MiniLM-L6-v2` is installed, the tier encodes all corpus examples into 384-dim embeddings (cached after first computation). At routing time, the task is encoded and cosine similarity is computed against all corpus embeddings. The closest match's complexity and tier are returned:

```python
confidence = min(0.85, best_similarity)
```

The 0.85 cap prevents the semantic tier from being too confident. Even a perfectly matched embedding should leave room for the neural tier to override based on learned experience. A task that is semantically identical to a corpus example but known from feedback to be better served by a different model deserves the neural tier's judgement.

2. **TF-IDF (fallback).** If sentence-transformers is not installed (which can happen in minimal deployment environments), the tier builds a sparse TF-IDF vector representation:

```python
def _build_tfidf(self):
    corpus_size = len(self._corpus_texts)
    df = Counter()
    for text in self._corpus_texts:
        tokens = self._tokenize(text)
        df.update(set(tokens))
    self._tfidf_idf = {
        term: log(corpus_size / (freq + 1)) + 1
        for term, freq in df.items()
    }
```

The TF-IDF confidence adds a 0.1 fudge factor (`confidence = min(0.75, sim + 0.1)`) to compensate for TF-IDF's lower discriminative power. However, if the best TF-IDF similarity is below 0.1, Tier 2 returns None and the cascade continues -- this prevents spurious matches that would degrade routing quality.

**Graceful embedding degradation.** A notable design decision: the first time the embedding backend throws an exception, the tier permanently sets `self._encoder = None` and falls back to TF-IDF for all subsequent calls. This prevents a transient embedding loading failure (e.g., disk I/O, corrupted model file) from repeatedly adding 50ms to the critical routing path. The tier logs the failure and continues producing routing decisions.

**Extensibility.** `add_example(text, complexity, tier)` adds new training data to the corpus. When called, it invalidates the embedding cache (`self._corpus_embeddings = None`) and rebuilds the TF-IDF index. This allows the corpus to grow with usage without requiring a restart.

### 2.3 Tier 3: NeuralUCB

**Characteristics: 20-100ms latency, ~$0.001 cost (numpy computation only), catches remainder.**

Tier 3 (`NeuralTier`) wraps a NeuralUCB contextual bandit (`NeuralUCB` in `neural_ucb.py`). Unlike Tier 1 and Tier 2, which are purely lookup-based, Tier 3 learns from every routing outcome. It is the mechanism by which the router adapts to observed quality, cost, and latency patterns.

**Feature extraction.** Before routing, the tier converts the task string into a fixed-length 10-dimensional feature vector. The features are deliberately fast to compute -- no LLM calls, no embeddings, just string counting and set membership tests:

```python
@staticmethod
def _extract_features(task, context=None):
    words = task.split()
    word_count = len(words)
    char_count = len(task)
    avg_word_len = char_count / max(word_count, 1)
    question_count = task.count("?")
    code_indicators = task.count("`") + task.count("def ") + task.count("function ")
    cap_ratio = sum(1 for w in words if w and w[0].isupper()) / max(word_count, 1)

    technical_terms = ["api", "database", "server", "client", "endpoint", "json",
        "xml", "http", "docker", "kubernetes", "microservice", "sql", "nosql",
        "redis", "cache", "queue", "async", "thread", "process", "lambda",
        "class", "interface", "module", "package", "dependency"]
    tech_count = sum(1 for term in technical_terms if term in task.lower())

    imperative_verbs = ["implement", "create", "build", "fix", "debug", "add",
        "remove", "update", "delete", "write", "read", "run", "deploy", "configure"]
    imperative_count = sum(1 for v in imperative_verbs if v in task.lower().split())

    return [
        float(char_count),        # 0: task length
        float(word_count),        # 1: word count
        avg_word_len,              # 2: avg word length
        float(question_count),    # 3: question count
        float(code_indicators),   # 4: code indicator count
        cap_ratio,                 # 5: capitalized word ratio
        1.0 if "please" in task.lower() else 0.0,  # 6: politeness flag
        float(tech_count),        # 7: technical term count
        float(imperative_count),  # 8: imperative verb count
        1.0 if "://" in task else 0.0,  # 9: URL indicator
    ]
```

These ten features capture five orthogonal dimensions of task difficulty:

| Dimension | Features | Signal |
|---|---|---|
| **Structure** | char_count, word_count, avg_word_len | Longer tasks tend to be more complex |
| **Specificity** | tech_count, code_indicators | Technical detail correlates with complexity |
| **Intent** | imperative_count, question_count | Commands are more effort than questions |
| **Formality** | cap_ratio, politeness_flag | Capitalization and politeness hint at context |
| **Scope** | URL_indicator | URLs indicate context-heavy requests |

The features are deliberately coarse. A finer-grained feature set (e.g., per-domain embeddings, N-gram frequencies) would improve prediction accuracy but would add latency and memory overhead. The 10-dim vector can be computed in under 10 microseconds for any task string.

**The NeuralUCB algorithm.** The bandit maintains a 2-layer MLP with He-initialized weights. The network has only 1,096 parameters total (10 * 64 + 64 + 64 * 6 + 6 = 640 + 64 + 384 + 6 = 1,094):

```python
# Neural network weights (He initialization for ReLU)
self._W1 = np.random.randn(input_dim, hidden_dim) * math.sqrt(2.0 / input_dim)
self._b1 = np.zeros((1, hidden_dim))
self._W2 = np.random.randn(hidden_dim, n_models) * math.sqrt(2.0 / hidden_dim)
self._b2 = np.zeros((1, n_models))
```

The forward pass is pure numpy matrix multiplication with ReLU activation:

```python
def _forward(self, X):
    hidden = np.maximum(0, X @ self._W1 + self._b1)
    return hidden @ self._W2 + self._b2
```

For each candidate model tier, the network predicts a reward. Model selection uses the UCB criterion:

```
selected = argmax_i (predicted_reward_i + c * sqrt(log(t) / n_i))
```

where `c` is the exploration bonus (default 0.1), `t` is the total number of pulls across all models, and `n_i` is the count of pulls for model `i`.

**Mathematical interpretation of the UCB bonus.** The term `sqrt(log(t) / n_i)` comes from the Hoeffding inequality for sub-Gaussian rewards. At confidence level `1 - 1/t`, the true expected reward for model `i` lies in the interval `[predicted_i - bonus, predicted_i + bonus]`. The UCB algorithm selects the model with the highest _upper_ confidence bound, which corresponds to being optimistic in the face of uncertainty. As `t` increases, `log(t)` grows slower than any polynomial, so the bonus shrinks and the algorithm progressively commits to the best model.

**Three-phase selection behavior.** The NeuralTier operates in three distinct phases depending on data accumulation:

**Phase 1: Pure heuristic (pulls < min_samples=10).** The bandit has insufficient data for meaningful predictions. `_route_heuristic` fires instead, using hard-coded feature thresholds:

```python
def _route_heuristic(self, task):
    features = self._extract_features(task)
    char_count, word_count, _, question_count, code_indicators = features[0:5]
    tech_count, imperative_count = features[7], features[8]

    if word_count <= 3 and char_count < 20 and question_count == 0 and code_indicators == 0:
        complexity = TaskComplexity.TRIVIAL;  confidence = 0.70
    elif tech_count >= 3 or imperative_count >= 3:
        if char_count > 100:
            complexity = TaskComplexity.AGENTIC;  confidence = 0.55
        else:
            complexity = TaskComplexity.COMPLEX;  confidence = 0.55
    elif code_indicators > 2 or tech_count >= 2:
        complexity = TaskComplexity.MODERATE;  confidence = 0.50
    elif question_count >= 1 and word_count < 15:
        complexity = TaskComplexity.SIMPLE;  confidence = 0.60
    elif word_count < 10:
        complexity = TaskComplexity.SIMPLE;  confidence = 0.45
    else:
        complexity = TaskComplexity.MODERATE;  confidence = 0.40
    ...
```

The decision tree uses the same features as the neural network but with explicit thresholds. Its confidence values are lower than Tier 1 equivalents (0.55 vs 0.80 for complex, 0.60 vs 0.80 for simple) because the heuristic has no keyword-specific signal -- it must guess purely from aggregate statistics.

**Phase 2: Bootstrap exploration (total_pulls >= min_samples, but some models have few pulls).** During this phase, the neural path is active, but models with fewer than `min_samples` pulls receive an inflated exploration bonus:

```python
if n < self.config.min_samples:
    bonus = 1.0 + (self.config.min_samples - n) / self.config.min_samples
    ucb = self.config.exploration_bonus * bonus
elif n > 0:
    ucb = self.config.exploration_bonus * math.sqrt(math.log(total_pulls) / n)
else:
    ucb = self.config.exploration_bonus * math.sqrt(math.log(total_pulls) + 1.0)
```

The bootstrap bonus ensures that every model tier receives at least `min_samples` explorations before the bandit makes exploitative commitments. Without this, a model that happened to have a slightly lower initial prediction would never be selected and would remain in the cold permanently.

**Phase 3: Mature exploitation (all models have sufficient pulls).** The UCB bonus converges to its standard form. The network weights are updated every 5 pulls via SGD on a random batch of up to 32 experiences from the replay buffer:

```python
def _train_step(self):
    buffer_len = len(self.replay_buffer)
    if buffer_len == 0:
        return
    batch_size = min(32, buffer_len)
    indices = np.random.choice(buffer_len, batch_size, replace=False)

    for idx in indices:
        features, model_idx, reward = self.replay_buffer[idx]
        X = features.reshape(1, -1)

        # Forward pass
        z1 = X @ self._W1 + self._b1
        h = np.maximum(0, z1)
        z2 = h @ self._W2 + self._b2
        pred = z2[0, model_idx]

        # MSE gradient
        error = pred - reward
        dL_dW2_col = error * h.T
        dL_db2 = error
        dL_dh = error * self._W2[:, model_idx:model_idx+1].T
        dL_dz1 = dL_dh * (z1 > 0).astype(float)
        dL_dW1 = X.T @ dL_dz1
        dL_db1 = dL_dz1

        # SGD update
        lr = self.config.learning_rate
        self._W2[:, model_idx] -= lr * dL_dW2_col.flatten()
        self._b2[0, model_idx] -= lr * dL_db2
        self._W1 -= lr * dL_dW1
        self._b1 -= lr * dL_db1
```

The training is single-sample SGD (not batched) because the update frequency (every 5 pulls) and batch size (32) are small enough that the variance of single-sample gradients is tolerable. The gradient computation is hand-coded rather than using autograd because the network is tiny (1,094 parameters) and manual backpropagation is actually faster than setting up an autograd graph.

**Cost-aware reward computation.** When `update_with_outcome` is called:

```python
cost_penalty = cost * self.config.cost_sensitivity
reward = float(success) * self.config.quality_weight - cost_penalty
```

With default parameters (cost_sensitivity=0.5, quality_weight=1.0):
- A successful cheap model (cost=$0.001): reward = 1.0 - 0.0005 = 0.9995
- A successful expensive model (cost=$0.05): reward = 1.0 - 0.025 = 0.975
- A failed cheap model (cost=$0.001): reward = 0.0 - 0.0005 = -0.0005

The cost penalty is proportional to absolute cost, not cost relative to the model's tier. This means premium models are inherently penalized relative to budget models, which is correct: the router should prefer the cheapest model that gets the job done.

**Online learning frequency.** The `_update_counter` increments on every call to `update`. Training fires every 5 updates:

```python
self._update_counter += 1
if self._update_counter % 5 == 0 and len(self.replay_buffer) >= self.config.min_samples:
    self._train_step()
```

This means the network receives a training update approximately every 5 routing decisions. In a session with 100 routing decisions, the network updates roughly 20 times. This is aggressive enough to adapt to distribution shifts within a session but conservative enough to avoid over-fitting to individual outcomes.

**The replay buffer as bounded memory.** The buffer stores up to 1000 (features, model_idx, reward) tuples. As new experiences arrive, old ones are evicted (deque with maxlen). This bounded memory serves two purposes:
1. **Memory efficiency:** 1000 * (10 floats + 1 int + 1 float) ~= 48 KB.
2. **Adaptation:** The sliding window ensures the network trains on recent experiences, naturally forgetting outdated patterns (e.g., a provider that was slow earlier but has recovered).

**The `_fitted` flag.** NeuralTier tracks whether it has accumulated enough data for neural predictions via a boolean flag. This transitions from False to True the first time the replay buffer reaches `min_samples`. Once True, `route()` uses the neural network (Phase 2 or 3) instead of the heuristic (Phase 1). The flag is never reset during a session, even if the buffer is later emptied (which shouldn't happen in normal operation).

## 3. Budget Tracking

The BudgetTracker (`budget.py`) implements a Google BATS-inspired (Budget-Aware Tier Selection) pattern that injects cost awareness into every routing decision. It tracks spending across tasks within a session, identifies four budget regimes, and provides both advisory (per-task budget limits) and enforcement (tier downgrade, circuit breaker) mechanisms.

**Four regimes.** The tracker divides a session's budget into four regimes based on the fraction of budget remaining:

| Regime | Remaining Budget | Max Task Budget | Tier Downgrade Rule |
|---|---|---|---|
| HIGH | >70% remaining | 20% of remaining | None |
| MEDIUM | 30-70% remaining | 10% of remaining | None |
| LOW | 10-30% remaining | 5% of remaining | Downgrade PREMIUM and AGENTIC |
| CRITICAL | <10% remaining | 2% of remaining | Downgrade anything except LOCAL_SLM and HAIKU |

The regime is computed from the remaining ratio, not the used ratio. This means a session that spent $3.50 of a $5.00 budget has 30% remaining (MEDIUM regime). A session that spent $4.70 has 6% remaining (CRITICAL regime). The thresholds are tested explicitly in the test suite:

```python
def test_regime_high(self):
    self.tracker.record(cost_usd=1.0)       # 20% used, 80% remaining
    assert self.tracker.regime == BudgetRegime.HIGH

def test_regime_medium(self):
    self.tracker.record(cost_usd=2.0)       # 40% used, 60% remaining
    assert self.tracker.regime == BudgetRegime.MEDIUM

def test_regime_low(self):
    self.tracker.record(cost_usd=3.7)       # 74% used, 26% remaining
    assert self.tracker.regime == BudgetRegime.LOW

def test_regime_critical(self):
    self.tracker.record(cost_usd=4.7)       # 94% used, 6% remaining
    assert self.tracker.regime == BudgetRegime.CRITICAL
```

**Circuit breaker at $5/session.** The `CIRCUIT_BREAKER_LIMIT_USD` constant is set to 5.0. When `total_spent >= session_budget_usd`, the tracker sets `_tripped = True`. The downstream effects are:

1. **`route()` raises RuntimeError.** The router checks `if self.budget.is_tripped` before any tier processing. The error message includes precise spending details: `"Circuit breaker tripped: $5.50 spent of $5.00 budget. Reset the tracker or increase the budget to continue."`.

2. **`record_outcome()` returns False.** The tracker refuses to record new costs, returning False silently. This prevents downstream code from accidentally accumulating unbounded costs after the breaker trips.

3. **Further `record()` calls are no-ops.** Once tripped, the tracker checks `if self._tripped: return False` at the top of `record()`. The state persists until `reset()` is called.

The $5 default is reasonable for a single session of agentic coding (approximately 100-200 HAILU-tier tasks, or 50-100 STANDARD-tier tasks). Heavier users can configure a higher limit at construction time.

**Budget-aware tier downgrade (enforcement).** The critical integration point is in `ModelRouter._build_decision`. After the cascade selects a target tier, the router checks:

```python
if self.budget.should_downgrade_tier(target_tier):
    fallback = self.providers.get_fallback_model(target_tier, self.budget.regime.value)
    if fallback:
        target_tier = fallback.tier
```

The `should_downgrade_tier` method implements the regime-based rule:

```python
def should_downgrade_tier(self, target_tier):
    if self.regime == BudgetRegime.CRITICAL:
        return target_tier not in (ModelTier.LOCAL_SLM, ModelTier.HAIKU)
    if self.regime == BudgetRegime.LOW:
        return target_tier in (ModelTier.PREMIUM, ModelTier.AGENTIC)
    return False
```

When a downgrade occurs, the router:
1. Calls `get_fallback_model` to find the cheapest available model at the next-lower tier.
2. Constructs a new `TierResult` with the fallback tier.
3. Reduces confidence by 10% (`tier_result.confidence * 0.9`).
4. Appends a budget reason to the reasoning string: `"(downgraded from {original} for budget)"`.

This means every `RoutingDecision` carries provenance: downstream code can inspect `decision.reasoning` to see if a downgrade occurred and why.

**Per-task budget guidance (advisory).** For callers that want to constrain model cost on a per-task basis, `get_max_task_budget()` returns a recommended spending limit:

```python
def get_max_task_budget(self):
    ratio = self.budget_remaining_ratio
    if ratio > 0.70:   # HIGH
        return self.remaining * 0.20
    if ratio > 0.30:   # MEDIUM
        return self.remaining * 0.10
    if ratio > 0.10:   # LOW
        return self.remaining * 0.05
    return self.remaining * 0.02  # CRITICAL
```

This can be passed to NeuralUCB's `select_model(features, candidates, budget_constraint=...)`. The bandit then filters out models whose estimated per-task cost exceeds the recommendation:

```python
if budget_constraint is not None:
    filtered = [m for m in candidate_models
                if _MODEL_COST_ESTIMATES.get(m, 0.0) <= budget_constraint]
    if filtered:
        candidate_models = filtered
```

If all models are over budget, the constraint is silently ignored (the empty `if filtered` check prevents the router from having zero candidates).

**Budget XML context.** The tracker's `to_xml_context()` method produces structured XML for injection into reasoning prompts:

```xml
<budget>
  <session_name>session-a1b2c3d4</session_name>
  <spent>$2.3500</spent>
  <limit>$5.00</limit>
  <remaining>$2.6500</remaining>
  <ratio_used>47.0%</ratio_used>
  <regime>MEDIUM</regime>
  <tasks>47</tasks>
  <success_rate>95.7%</success_rate>
  <circuit_breaker>OK</circuit_breaker>
  <max_next_task>$0.2650</max_next_task>
</budget>
```

This XML is designed for consumption by an LLM (e.g., injected into the system prompt to make the model aware of budget constraints). The structured format is machine-readable and self-describing.

**Thread safety.** The BudgetTracker uses a `threading.Lock` for all mutations (`record`, `reset`). Reads of scalar properties (total_spent, regime, is_tripped) are not locked because Python's GIL makes simple scalar reads atomic. This is sufficient for the current single-threaded usage but would need revisiting if routing becomes async or multi-threaded.

**Resetting between sessions.** `reset()` clears all state: total_spent, task_count, success_count, entries, and the circuit breaker flag. This is the intended mechanism for starting a new session without constructing a new BudgetTracker.

## 4. Provider Registry

The ProviderRegistry (`providers.py`) maintains a catalog of AI model providers with May 2026 pricing data. It is the router's source of truth for what models exist, what they cost, and whether their API keys are available.

**9 models across 5 providers:**

| Provider | Models | Tiers | Cost/1M Input Tokens | Context Window |
|---|---|---|---|---|
| Anthropic | claude-haiku-4-20250514 | HAIKU | $1.00 | 200K |
| | claude-sonnet-4-20250514 | STANDARD | $3.00 | 200K |
| | claude-opus-4-20250514 | PREMIUM | $15.00 | 200K |
| DeepSeek | deepseek-chat-v4 | FAST | $0.27 | 128K |
| | deepseek-reasoner-v4 | STANDARD | $0.55 | 128K |
| Google | gemini-2.5-flash | HAIKU | $0.15 | 1M |
| | gemini-2.5-pro | STANDARD | $1.25 | 1M |
| OpenAI | gpt-4o-mini-2025 | HAIKU | $0.15 | 128K |
| | gpt-4o-2025 | STANDARD | $2.50 | 128K |
| | gpt-5 | PREMIUM | $12.50 | 256K |
| OpenRouter | openrouter/deepseek/deepseek-chat-v4 | FAST | $0.27 | 128K |
| | openrouter/anthropic/claude-sonnet-4-20250514 | STANDARD | $3.00 | 200K |

**ModelTier enum.** The six tiers are ordered by capability (and cost):

```python
class ModelTier(str, Enum):
    LOCAL_SLM = "local_slm"    # Local small language model (~$0)
    HAIKU = "haiku"             # Claude Haiku / Gemini Flash (~$0.0001)
    FAST = "fast"               # GPT-4o-mini / DeepSeek-Lite (~$0.0005)
    STANDARD = "standard"       # Sonnet 4 / GPT-4o (~$0.01)
    PREMIUM = "premium"         # Opus 4 / DeepSeek-V4-Pro (~$0.05)
    AGENTIC = "agentic"         # Opus + tool orchestration (~$0.10+)
```

The ordering is significant: `get_fallback_model` walks from the selected tier downward through the enum, so `ModelTier.FAST` falls back to `ModelTier.HAIKU`, not to `ModelTier.LOCAL_SLM`. The enum values are stored as strings (e.g., "standard") to make them JSON-serializable.

**Provider dataclass.** Each provider is defined by:

```python
@dataclass(frozen=True)
class Provider:
    name: str
    models: list[str] = field(default_factory=list)
    base_url: str = ""
    api_key_env: str = ""
    supports_streaming: bool = True
    max_requests_per_minute: int = 100
```

Notable: `api_key_env` stores the _environment variable name_ (e.g., "ANTHROPIC_API_KEY"), not the key itself. The registry never stores API key values; it reads them from `os.environ` at call time.

**API key detection is lazy and per-call.** `has_api_key(provider_name)` reads the environment variable on every invocation. This means:
- A provider becomes available as soon as its key is set, without restart.
- A provider becomes unavailable as soon as its key is unset, without restart.
- No keys are ever stored in memory beyond their natural lifetime in `os.environ`.

**Model selection by tier.** `get_best_model_for_tier(tier, require_key=True)` returns the cheapest available model at a given tier:

```python
def get_best_model_for_tier(self, tier, require_key=True):
    candidates = [
        m for m in self._models.values()
        if m.tier == tier
        and (not require_key or self.has_api_key(m.provider))
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda m: m.cost_per_1m_tokens)
    return candidates[0]
```

At the HAIKU tier, for example, this would prefer Google's gemini-2.5-flash ($0.15/1M) over Anthropic's haiku ($1.00/1M) or OpenAI's gpt-4o-mini ($0.15/1M -- tied on price). The `require_key=False` mode is used by the fallback chain to find any structurally viable model regardless of whether credentials are currently available.

**Fallback model resolution.** `get_fallback_model(tier, budget_regime)` walks down the tier list from the selected tier:

```python
def get_fallback_model(self, tier, _budget_regime="high"):
    tier_order = list(ModelTier)
    idx = tier_order.index(tier)
    if idx == 0:
        return self.get_best_model_for_tier(tier, require_key=False)

    for fallback_idx in range(idx - 1, -1, -1):
        candidate = self.get_best_model_for_tier(tier_order[fallback_idx], require_key=False)
        if candidate:
            return candidate
    return self.get_best_model_for_tier(tier, require_key=False)
```

If PREMIUM is selected and no keys exist for PREMIUM models, the fallback checks STANDARD (cheapest: DeepSeek reasoner at $0.55), then FAST (DeepSeek chat at $0.27), then HAIKU (Google Flash at $0.15), then LOCAL_SLM. The first tier with any available model wins.

**Custom provider registration.** The public API allows adding providers at runtime:

```python
def register_provider(self, provider):
    self._providers[provider.name] = provider

def register_model(self, model):
    self._models[model.model_name] = model
    provider = self._providers.get(model.provider)
    if provider and model.model_name not in provider.models:
        provider.models.append(model.model_name)
```

Note that `register_model` automatically links the model to its provider's model list. This bidirectional linking ensures `list_models(provider_name)` and `get_model(model_name)` are both consistent after registration.

## 5. Fallback Chain

The router implements three distinct fallback mechanisms: budget-driven tier downgrade, provider unavailability handling, and last-resort model selection. These operate at different stages of the routing pipeline and provide progressively broader degradation.

**Stage 1: Budget-driven tier downgrade.** This is the primary fallback mechanism, operating in `_build_decision` after the cascade selects a target tier. The BudgetTracker's regime and `should_downgrade_tier` determine whether a downgrade is needed:

- **CRITICAL regime**: Any tier above HAIKU is downgraded. Rationale: when only ~$0.50 remains, every task should use the cheapest possible model unless proven otherwise.
- **LOW regime**: Only PREMIUM and AGENTIC are downgraded (to STANDARD or FAST respectively). Rationale: STANDARD models still provide good quality at much lower cost than PREMIUM.
- **HIGH and MEDIUM regimes**: No downgrade. Rationale: the session has enough budget to use the preferred tier.

When a downgrade occurs, `get_fallback_model` finds the cheapest available model at the next-lower tier. The fallback is _always_ at a single tier below -- there is no multi-tier cascade from budget alone. The reasoning: if the budget regime is CRITICAL and the neural tier selects PREMIUM, the router downgrades to STANDARD, not all the way to LOCAL_SLM. This preserves as much quality as the budget permits.

**Stage 2: Provider unavailability.** If `get_best_model_for_tier` returns None (no models at the target tier have valid API keys), `get_fallback_model` is called without budget regime influence. This is a structural fallback: it searches ALL lower tiers for ANY model with available credentials. Because the built-in providers include five different AI companies, it is unlikely that all providers would be unavailable simultaneously.

**Stage 3: Last-resort fallback.** If both `get_best_model_for_tier` and `get_fallback_model` return None, `_build_decision` calls `_pick_any_model()`:

```python
def _pick_any_model(self):
    for tier in ModelTier:
        model = self.providers.get_best_model_for_tier(tier, require_key=False)
        if model:
            return model
    # Should never happen -- providers are pre-configured
    return ModelAssignment(
        model_name="claude-haiku-4-20250514",
        provider="anthropic",
        cost_per_1m_tokens=1.0,
        tier=ModelTier.HAIKU,
    )
```

This iterates all tiers from LOCAL_SLM to AGENTIC, returning the first model it finds regardless of key availability. The hardcoded fallback at the end is a safety net for pathological states (e.g., custom registry with zero models).

**Consensus router fallback (separate path).** The `ConsensusRouter` in `consensus_router.py` provides a completely separate fallback mechanism for tasks explicitly routed through it (usually critical decisions requiring multi-model verification). The consensus router supports:

1. **Single best**: Fast path, one model, no fallback.
2. **Dual verify**: Two models. If they disagree, a tie-breaker is added.
3. **Majority quorum**: Three models, majority vote. If the vote is tied, escalation.
4. **Full consensus**: All eligible models, weighted vote.

When models fail, the consensus router retries up to `max_retries=2`. If models disagree, a new model is added from the eligible list. If dissent reaches CRITICAL severity, the decision is blocked entirely (requiring human intervention).

The consensus router is not part of the main ModelRouter cascade -- it is a separate entry point for high-stakes decisions that are flagged by the `ConsensusRouter.should_ensemble()` check.

**Fallback Chain Summary:**

| Trigger | Mechanism | Latency Impact |
|---|---|---|
| Budget LOW/CRITICAL | `get_fallback_model` (one tier down) | ~0ms |
| No models at target tier | `get_fallback_model` (any lower tier) | ~0ms |
| All selection methods fail | `_pick_any_model` (any model) | ~0ms |
| Model execution failure | Consensus router retry (up to 2x) | 100-200ms per retry |
| Model disagreement | Consensus router tie-breaker | 100ms per extra model |

### 5.6 ProviderBackend Protocol

The `ProviderBackend` protocol is the single most important architectural decision in Lyra's model routing. Every component above the API talks to models through one abstraction:

```python
@runtime_checkable
class ProviderBackend(Protocol):
    """Unified interface for any LLM provider."""

    async def chat(
        self, messages: list[Message], config: ModelConfig
    ) -> ChatResponse: ...

    async def stream_chat(
        self, messages: list[Message], config: ModelConfig
    ) -> AsyncIterator[ChatResponse]: ...

    def supports(self, capability: Capability) -> bool:
        """Query provider capabilities at runtime."""
        ...

    @property
    def context_window(self) -> int: ...

    @property
    def pricing(self) -> PricingTier: ...

    @property
    def thinking_config(self) -> ThinkingConfig:
        """Maps Lyra effort level to provider-specific thinking params."""
        ...
```

**Normalization contract** (the hard part):
- **Message format**: Role + content (text + multimodal parts) + tool_calls + tool_result -> normalized into a common `Message` dataclass.
- **Tool schema**: Anthropic tool-use format vs. OpenAI function-calling vs. DeepSeek tool format -> normalized into `ToolDef` dataclass.
- **Streaming**: Different chunk types (content_delta, tool_call_delta, thinking_delta) -> normalized into unified `StreamingChunk` union.
- **Token accounting**: Input, output, cache_read, cache_write -> normalized into `TokenUsage` dataclass with optional fields.
- **Thinking**: Anthropic budget_tokens -> DeepSeek extended thinking flag + budget -> GPT reasoning_effort enum -> Ollama N/A.
- **Errors**: Provider-specific rate limits, auth errors, timeouts -> normalized into `ProviderError` hierarchy.

Concrete implementations: `ClaudeBackend`, `DeepSeekBackend`, `OpenAIBackend`, `QwenBackend`, `OllamaBackend`, `vLLMBackend`.

### 5.7 Capability Matrix

The `CapabilityMatrix` maps per-provider capabilities and is queryable at routing time:

| Capability | Anthropic | DeepSeek | OpenAI | Google | Open-Weights |
|-----------|-----------|----------|--------|--------|-------------|
| Max context window | 200K | 128K | 128K-256K | 1M | 32K-128K |
| Tools | Yes | Yes | Yes | Yes | Yes (varies) |
| Streaming | Yes | Yes | Yes | Yes | Yes |
| Vision | Yes | Yes | Yes | Yes | Varies |
| Audio input | Yes | No | Yes | Yes | No |
| PDF input | Yes | No | Yes | Limited | No |
| JSON mode | Yes | Yes | Yes | Yes | String-only |
| Extended thinking | budget_tokens | CoT prompt | reasoning_effort | N/A | Prompt-level |

The capability matrix enables capability-gated routing: a task requiring vision filters out providers without vision support before the cascade even runs. When a required capability is absent, the degradation map specifies fallback behavior (e.g., no vision -> describe images via OCR -> route description to text model).

### 5.8 Memory-Augmented Routing

The breakthrough addition to Lyra's router is **memory-augmented routing**, inspired by "Knowledge Access Beats Model Size" (arXiv 2603.23013):

**Mechanism**:
1. Every query + its answer is cached in a cross-agent memory store.
2. New query: compute embedding similarity against cached queries.
3. Similarity > 0.92 (cache hit): route to cheap model (Haiku-class) with cached answer as context -> ~96% cost reduction on recalled queries.
4. Similarity 0.7-0.92 (partial match): route to mid-tier model with top-3 cached answers as context.
5. Similarity < 0.7 (cold): route through standard 3-tier cascade.
6. Learning: track when cheap model answers were overridden, adjust thresholds.

**Expected impact**: >=40% per-session cost reduction through cache hits alone. The Knowledge Access paper's findings support this: memory-augmented 8B recovers 69% of full-context 235B quality at 96% cost reduction. The compound strategy (memory + routing) is orthogonal: memory provides correctness, routing provides cost savings.

```python
class MemoryAugmentedRouter:
    def __init__(self, memory_store, base_router, confidence_threshold=0.50):
        self.memory = memory_store
        self.router = base_router

    async def route(self, task, context):
        # Stage 1: Memory check
        cached = await self.memory.similarity_search(task, threshold=0.92)
        if cached:
            return RoutingDecision(
                model_id="cost_optimal_model",
                cache_hit=True,
                context=cached.answer,
                estimated_cost=cached.answer_cost * 0.04  # ~96% reduction
            )
        # Stage 2: Standard cascade
        return await self.router.route(task, context)
```

### 5.9 Effort Scale as Provider-Neutral Reasoning Budget

The effort scale provides a unified 6-tier abstraction across all providers:

| Effort | Anthropic | DeepSeek | GPT | Open-Weights |
|--------|-----------|----------|-----|-------------|
| low | thinking: 1024 | prompt: "be concise" | reasoning: low | max_tokens: 512 |
| medium | thinking: 4096 | default config | reasoning: medium | max_tokens: 2048 |
| high | thinking: 8192 | extended thinking on | reasoning: high | max_tokens: 4096 |
| xhigh | thinking: 16384 | CoT + self-check | reasoning: max | max_tokens: 8192 |
| max | thinking: 31999 | CoT + multi-round | reasoning: max + ext | max_tokens: 16384 |
| ultracode | thinking: 16384 + orchestration ON | CoT + orchestration ON | max + orch. ON | 8192 + orch. ON |

Ultracode is NOT a 6th API budget tier -- it is "xhigh + orchestration toggle." This makes the scale portable to providers with fewer native effort levels. For providers with no thinking budget API, prompt-level analogs are used (CoT instructions, self-critique prompts, multi-round verification).

## 6. Architecture Diagram

```
                           ┌──────────────────────────────┐
                           │         User Task             │
                           │  "implement JWT auth"         │
                           └─────────────┬────────────────┘
                                         │
                           ┌─────────────▼────────────────┐
                           │     EffortLevel Resolution    │
                           │   low│medium│high│xhigh│max   │
                           │  maps to thinking budget +    │
                           │  reasoning_effort params      │
                           └─────────────┬────────────────┘
                                         │
                           ┌─────────────▼────────────────┐
                           │   Circuit Breaker Check       │
                           │   budget.is_tripped?          │
                           │   if True: RuntimeError       │
                           └─────────────┬────────────────┘
                                         │
                      ┌──────────────────┼──────────────────┐
                      │                  │                   │
           ┌──────────▼──────────┐      │      ┌────────────▼───────────┐
           │   TIER 1: RULE      │      │      │   TIER 2: SEMANTIC     │
           │   Domain keywords   │      │      │   Sentence-transformers │
           │   Regex patterns    │      │      │   or TF-IDF fallback    │
           │   Keyword sets      │      │      │   20-example corpus     │
           │   Heuristics        │      │      │   5-50ms, <$0.001       │
           │   0-1ms, $0         │      │      │   Hit: 20-30%           │
           │   Hit: 50-60%      │      │      └────────────┬───────────┘
           └──────────┬──────────┘      │                   │
                      │   confidence    │                   │
                      │   < 0.50?       │                   │   confidence
                      └─── continue ────┼───── continue ────┘   < 0.40?
                                        │
                                        ▼
                           ┌──────────────────────────────────────┐
                           │        TIER 3: NEURALUCB             │
                           │                                      │
                           │  ┌────────────────────────────────┐  │
                           │  │  Feature Extraction (10-dim)   │  │
                           │  │  char_count, word_count,       │  │
                           │  │  tech_terms, imperative_verbs,  │  │
                           │  │  code_indicators, questions,    │  │
                           │  │  capitalization, politeness,    │  │
                           │  │  URL_presence, avg_word_len     │  │
                           │  └──────────────┬─────────────────┘  │
                           │                 ▼                    │
                           │  ┌────────────────────────────────┐  │
                           │  │  2-layer MLP (10→64→6)         │  │
                           │  │  ReLU hidden, linear output    │  │
                           │  │  1,094 parameters total        │  │
                           │  └──────────────┬─────────────────┘  │
                           │                 ▼                    │
                           │  ┌────────────────────────────────┐  │
                           │  │  UCB Selection:                │  │
                           │  │  argmax(pred + c√(log(t)/n))  │  │
                           │  │  Exploration bonus (c=0.1)     │  │
                           │  └──────────────┬─────────────────┘  │
                           │                                      │
                           │  Heuristic fallback (cold start)     │
                           │  20-100ms, ~$0.001, remainder        │
                           └──────────────────┬───────────────────┘
                                              │
                                              ▼
                           ┌──────────────────────────────────────┐
                           │    BUDGET-AWARE DECISION REFINEMENT   │
                           │                                      │
                           │  ┌──────────────────────────────┐    │
                           │  │  BudgetTracker:               │    │
                           │  │  HIGH (>70%, no down)         │    │
                           │  │  MEDIUM (30-70%, no down)     │    │
                           │  │  LOW (10-30%, down PREM/AG)   │    │
                           │  │  CRITICAL (<10%, down all)    │    │
                           │  │  Circuit breaker at $5.00     │    │
                           │  └──────────────┬───────────────┘    │
                           │                 ▼                    │
                           │  should_downgrade_tier(target)?      │
                           │  → get_fallback_model(target)        │
                           │  → reduce confidence × 0.9          │
                           │  → append budget reason to reasoning │
                           └──────────────────┬───────────────────┘
                                              │
                                              ▼
                           ┌──────────────────────────────────────┐
                           │     MODEL SELECTION (ProviderReg)    │
                           │                                      │
                           │  get_best_model_for_tier(target)     │
                           │  → filter by tier                    │
                           │  → filter by API key availability    │
                           │  → sort by cost_per_1m_tokens        │
                           │  → return cheapest                   │
                           │                                      │
                           │  9 models × 5 providers              │
                           │  Anthropic | DeepSeek | Google       │
                           │  OpenAI | OpenRouter                 │
                           │  May 2026 pricing data               │
                           └──────────────────┬───────────────────┘
                                              │
                                              ▼
                           ┌──────────────────────────────────────┐
                           │      RoutingDecision (frozen)        │
                           │                                      │
                           │  model: "claude-sonnet-4-20250514"   │
                           │  tier: ModelTier.STANDARD             │
                           │  complexity: TaskComplexity.MODERATE  │
                           │  confidence: 0.80                    │
                           │  reasoning: "Keyword 'implement'..." │
                           │  cost_estimate_usd: $0.01            │
                           │  tier_used: 1 (rule tier)            │
                           │  budget_regime: BudgetRegime.HIGH    │
                           │  effort_level: "high"                │
                           │  effort_budget_tokens: 8192          │
                           │  effort_instruction: "..."           │
                           │  effort_reasoning: "high"            │
                           │  orchestration_enabled: False        │
                           └──────────────────┬───────────────────┘
                                              │
                                              ▼
                           ┌──────────────────────────────────────┐
                           │         FEEDBACK LOOP                │
                           │                                      │
                           │  record_outcome(decision, success,   │
                           │    latency_ms, cost, task)            │
                           │                                      │
                           │  ┌──────────────────────────────┐    │
                           │  │  1. BudgetTracker.record()   │    │
                           │  │    → accumulate total_spent   │    │
                           │  │    → check circuit breaker    │    │
                           │  │    → update success stats     │    │
                           │  └──────────────────────────────┘    │
                           │                                      │
                           │  ┌──────────────────────────────┐    │
                           │  │  2. NeuralUCB.update_with_   │    │
                           │  │     outcome(task, model_id,   │    │
                           │  │     success, latency, cost)   │    │
                           │  │    → extract features         │    │
                           │  │    → compute cost-aware       │    │
                           │  │      reward                  │    │
                           │  │    → store in replay buffer   │    │
                           │  │    → train step every 5       │    │
                           │  └──────────────────────────────┘    │
                           │                                      │
                           │  Returns True  (within budget)       │
                           │  Returns False (circuit breaker)     │
                           └──────────────────────────────────────┘
```

The diagram shows the complete lifecycle of a routing decision, from effort resolution through the cascading tiers, budget enforcement, model selection, and finally the feedback loop that closes the learning cycle.

**Timing breakdown of a full cascade:**

| Stage | Cumulative Time | Cumulative Cost |
|---|---|---|
| Effort resolution | ~0.1ms | $0 |
| Circuit breaker check | ~0.01ms | $0 |
| Tier 1 (rule) | ~1ms | $0 |
| Tier 2 (semantic) | ~50ms (with embeddings) | <$0.001 |
| Tier 3 (neural) | ~100ms | ~$0.001 |
| Budget refinement | ~0.1ms | $0 |
| Model selection | ~0.1ms | $0 |
| **Total (worst case)** | **~151ms** | **~$0.001** |
| **Total (typical, Tier 1)** | **~1ms** | **$0** |

## 7. Trade-Off Analysis

### 7.1 Cascade Depth vs. Latency

The 3-tier cascade is the single most consequential design decision. Every task passes through Tier 1 at sub-millisecond cost. Only when the rule tier is uncertain does the semantic tier run. Only when both are uncertain does the neural tier run.

**Latency distribution under the cascade:**

- 50-60% of tasks pay 0-1ms total routing latency (Tier 1 hit).
- 20-30% of tasks pay 5-55ms total routing latency (Tier 1 miss, Tier 2 hit).
- 10-30% of tasks pay 25-155ms total routing latency (all three tiers).

The alternative would be to always run all three tiers and combine their outputs via weighted voting or stacking. This would improve accuracy (by aggregating multiple signals) but would multiply latency by 3-5x for every request and waste the cheap signal from Tier 1 on tasks that are trivially classifiable.

**Ensemble accuracy vs. cascade efficiency.** An ensemble router that combines all three tier outputs would achieve higher routing accuracy at the cost of latency. The cascade's tiered confidence thresholds are a pragmatic middle ground: they give the simple methods first refusal and only escalate when they are uncertain. The confidence thresholds (0.50 for Tier 1, 0.40 for Tier 2) are tuneable knobs that control this tradeoff. Lower thresholds increase the cascade's hit rate but risk more misclassifications. Higher thresholds push more tasks to the neural tier, increasing latency but improving accuracy.

### 7.2 Deterministic Rules vs. Learned Policy

Tier 1 is fully deterministic -- given the same task, it always produces the same result. This is both a strength and a weakness.

**Strengths of deterministic rules:**
- **Safety guarantees.** Domain rules for security, cryptography, medical, and legal are irrevocable. No learning can override them.
- **Auditability.** Every Tier 1 decision includes a `matched_rule` field (e.g., `"keyword:implement"`, `"domain:security"`, `"pattern:trivial"`, `"heuristic:short"`). Logs can be queried to verify routing behavior.
- **Zero latency.** String comparisons and regex patterns run in microseconds.
- **Testability.** The rule tier has 22 dedicated tests verifying specific task-to-tier mappings. Any change to the keyword sets or domain rules is validated by the test suite.

**Weaknesses of deterministic rules:**
- **Language dependence.** The keyword lists are English-only. A task phrased in Vietnamese or Japanese may not match any keyword and will fall through to Tier 2 or 3 regardless of its actual complexity.
- **No learning from feedback.** If the rule tier consistently misclassifies a particular type of task (e.g., "implement a quantum circuit" classified as MODERATE when it is actually COMPLEX), the rules cannot self-correct. The error persists until someone updates the keyword lists.
- **Maintenance burden.** The keyword sets must be kept current as new task patterns emerge. An underspecified set degrades the Tier 1 hit rate; an over-specified set may misclassify tasks.

The system compensates for these weaknesses by placing the neural tier as the final arbiter. Even if Tier 1 misclassifies a task, the cascade's budget refinement and the neural tier's learning can override the decision over time.

### 7.3 TF-IDF vs. Embeddings in Tier 2

Tier 2's dual-backend design is a pragmatic deployment trade-off. Sentence-transformers embeddings provide better semantic matching but require an additional 80MB+ package download. The TF-IDF fallback requires only numpy (which is already a dependency) and adds negligible disk footprint.

**When embeddings win.** Consider a task "craft a method to interpret comma-separated values." The TF-IDF backend would compute cosine similarity against "write a function to parse CSV files with error handling." The overlap tokens would be: "craft" (none), "method" (none), "interpret" (none), "comma" (none), "separated" (none), "values" (none) -- zero overlap, zero similarity. The embedding backend, however, would recognize that "craft a method" and "write a function" are semantically similar, and "CSV" and "comma-separated values" are synonyms. The embedding similarity might be 0.6-0.7, resulting in a correct MODERATE classification.

**When TF-IDF is sufficient.** For tasks that use the same vocabulary as the corpus examples, TF-IDF is surprisingly effective. "What is the syntax for async/await in Python" and "what is the syntax for list comprehension in Python" share "what is the syntax for" and "python" -- enough overlap to produce a similarity of 0.3-0.4, which exceeds the 0.1 threshold for a Tier 2 result.

**The embedding cache invalidation design.** When `add_example()` is called, the tier sets `_corpus_embeddings = None`. The next call to `_route_with_embeddings` will recompute all embeddings from the expanded corpus. This is correct but causes a one-time latency spike of 50-100ms (the time to encode 20+ sentences with the embedding model). For production deployments that add examples frequently, this could add latency to individual routing calls. The fix, which the current code does not implement, would be to either compute embeddings incrementally or to defer recomputation to a background thread.

### 7.4 NeuralUCB vs. Full RL (PPO/GRPO)

The current NeuralUCB implementation uses a 2-layer MLP with numpy-only forward/backward passes. The V3 architecture research (`model-routing-v3-design.md`) describes PPO-based policy gradient methods and GRPO-based preference optimization, which the current implementation deliberately does not use.

**What the current NeuralUCB gives up compared to full RL:**
- No value network for advantage estimation (actor-critic architecture).
- No clipping objective (PPO's primary training stability mechanism).
- No multi-epoch minibatch training across a replay buffer.
- No generalized advantage estimation (GAE) for credit assignment across time.
- No trajectory-level reward aggregation.

**What NeuralUCB gains in return:**
- **Zero external dependencies.** Pure numpy fits into any Python environment without torch, jax, or CUDA.
- **Single-sample online updates.** The network is updated after every 5 routing decisions. Full RL methods typically require batched trajectories.
- **Provable regret bounds.** UCB is known to achieve O(sqrt(T)) cumulative regret. PPO has no comparable guarantee.
- **Microsecond inference.** The 2-layer MLP with 1,094 parameters does a forward pass in ~10 microseconds. A transformer-based policy network would take milliseconds.

**When would full RL be better?** If routing decisions had long-term consequences (e.g., choosing a model for an early step affects the quality of later steps in a multi-turn conversation), trajectory-level credit assignment would be valuable. The current architecture treats each routing decision as independent, which is appropriate for single-turn interactions but suboptimal for multi-turn conversations.

**The cost-quality Pareto tradeoff.** NeuralUCB's cost-aware reward function (`reward = success * 1.0 - cost * 0.5`) implicitly encodes a linear Pareto tradeoff between quality and cost. Full multi-objective optimization via Pareto frontier discovery (as described in the V3 research) would be more principled: it would find all non-dominated model selections and let the user or application choose the desired tradeoff point. The current approach works because the reward function is simple enough to be intuitive, but it does not expose the full tradeoff surface.

### 7.5 Budget Circuit Breaker vs. Soft Throttling

The circuit breaker is binary: either routing is fully functional or it raises a RuntimeError. This is the simplest correct behavior for a system that must not exceed its budget.

**Arguments for hard cutoff:**
- **Guaranteed cost control.** There is no scenario where the system spends beyond the budget cap.
- **Simple semantics.** The error is explicit and must be handled by the caller. No silent degradation.
- **Easy to debug.** The error message includes the exact spending breakdown.

**Arguments against hard cutoff:**
- **Abrupt denial of service.** A user midway through a complex task may suddenly be unable to route new sub-tasks, leaving work partially completed.
- **No graceful degradation.** The system could continue with LOCAL_SLM-only routing after the breaker trips, providing degraded but non-zero service.

The mitigation is in the BudgetTracker's four regimes. The breaker is the final safety net, but the regimes provide progressive cost awareness: by the time the breaker trips, the system has already been operating in CRITICAL mode (maximum cost restriction) for the last 10% of the budget. The breaker mostly fires when spending accelerates unexpectedly (e.g., an infinite retry loop or a very expensive unexpected task).

### 7.6 Effort Mapping Integration

The ModelRouter integrates with `lyra_effort` (the `EffortManager`) to map effort levels (low, medium, high, xhigh, max, ultracode) into concrete execution parameters. This integration is implemented in `_build_decision`:

```python
effort_mapping = self._effort.map_effort(level, provider=model.provider)
```

The mapping produces:
- `budget_tokens`: Maximum tokens for extended thinking (used by Anthropic).
- `thinking_instruction`: Prompt-level instruction for providers that don't support budget_tokens natively.
- `reasoning_effort`: OpenAI-compatible reasoning_effort parameter ("low", "medium", "high").
- `orchestration_enabled`: Whether auto-orchestration (multi-tool, self-correction) is active.

These parameters are attached to the RoutingDecision and passed downstream to model executors. The key design decision is that effort mapping happens _after_ model selection, not before. This means a task routed to PREMIUM with effort="max" receives a larger thinking budget than one routed to STANDARD with effort="low", and the thinking budget is specific to the selected provider's API format.

### 7.7 Model Router Overall Design Tradeoffs

| Decision | Current Choice | Alternative | Why Current Wins |
|---|---|---|---|
| Cascade order | Rule -> Semantic -> Neural | Neural first (most accurate) | Cost: 80% of decisions at $0 |
| Neural architecture | 2-layer MLP (numpy) | Transformer (PyTorch) | Latency: 10us vs 10ms |
| Learning algorithm | NeuralUCB | PPO/GRPO | Simplicity: no batching, no GPU |
| Budget enforcement | Circuit breaker + tier downgrade | Soft throttling | Predictability: hard guarantee |
| Provider state | Static (checked at routing) | Dynamic (health polling) | Simplicity: no background monitoring |
| Feature extraction | 10 hand-crafted features | LLM-generated embeddings | Speed: 10us vs 100ms |
| Semantic backend | Embeddings with TF-IDF fallback | Always embeddings | Robustness: works without GPU |
| Multi-turn awareness | None (per-request routing) | Conversation history features | Scope: V4 target, not V3 |

## 8. (B) Breakthrough: Provider-Aware NeuralUCB

The current NeuralUCB implementation treats model tiers as actions in a contextual bandit whose context vector is derived solely from the _task description_. This is a significant limitation: the optimal routing decision depends not just on what the task is but on which providers are currently healthy, what their recent latency has been, and how their cost profiles interact with the session budget.

**The breakthrough is to extend the context vector with provider state features, transforming a task-contextual bandit into a task-AND-provider-contextual bandit.**

### 8.1 Extended Feature Vector

The current 10-dim feature vector would be extended to 16-20 dimensions:

```
[0-9]:  Task features (unchanged)
 [10]:  Provider health score (0-1, smoothed over 5-min sliding window)
 [11]:  Provider p95 latency (seconds, normalized to [0,1] via min-max scaling)
 [12]:  Provider rate limit remaining (0-1, as fraction of max_requests_per_minute)
 [13]:  Provider cost premium vs cheapest at same tier (0-1, normalized)
 [14]:  Provider error rate in last 5 minutes (0-1)
 [15]:  Session budget remaining ratio (0-1, from BudgetTracker)
 [16+]: Optional: learned provider embedding (via a small lookup table)
```

The provider state features must be computed _per candidate model_, not globally. A model from Anthropic might have a health score of 0.95 (all systems nominal) while a model from DeepSeek at the same tier has a score of 0.3 (rate-limited). The MLP would then learn that for certain task types, the health-adjusted reward for the DeepSeek model is lower, and the UCB exploration bonus would increase for the Anthropic model to compensate.

### 8.2 Provider State Integration Points

The provider state features would be injected at two points in the routing lifecycle:

**At routing time** (in `NeuralTier._route_neural`): Before calling `ucb.select_model`, the tier would assemble a per-candidate feature vector by querying each candidate provider's current health state. The health scoring function would be a new method on `ProviderRegistry`:

```python
def get_provider_health_vector(self, provider_name: str) -> list[float]:
    """Return normalized health features for provider-aware routing."""
    stats = self._health_buffer.get(provider_name, {})
    return [
        stats.get("health_score", 1.0),          # 10: health score
        stats.get("p95_latency_normalized", 0.5), # 11: normalized latency
        stats.get("rate_limit_remaining", 1.0),   # 12: rate limit
        stats.get("cost_premium", 0.0),           # 13: cost premium
        stats.get("error_rate_5min", 0.0),        # 14: error rate
        self._budget.budget_remaining_ratio,      # 15: budget
    ]
```

The `_health_buffer` would be populated by a background health-checker that polls each provider every 30 seconds. The polling would be lightweight: a single ping to a cheap endpoint (e.g., Anthropic's models list endpoint or DeepSeek's health endpoint). Failures and latency would be tracked in a sliding window.

**At feedback time** (in `NeuralUCB.update`): The reward computation would remain unchanged (`success * quality_weight - cost * cost_sensitivity`), but the feature vector stored in the replay buffer would now include the provider state that was present when the decision was made. This is essential for learning correct counterfactuals: if a model performed poorly because its provider was rate-limited at that moment, the network should learn to prefer that model when the provider is healthy, not to avoid it permanently.

### 8.3 Cold Start With Provider Priors

Provider-aware routing introduces a cold-start challenge: when a new provider is added to the registry, the network has no experience with its health characteristics. The solution is to seed the replay buffer with synthetic training examples that encode reasonable priors:

```python
def _seed_provider_priors(self, provider_name: str, tier: ModelTier):
    """Seed synthetic observations for a new provider."""
    # Healthy provider prior
    healthy = np.array([0.0]*10 + [0.95, 0.3, 1.0, 0.0, 0.0, 0.8])
    for _ in range(5):
        self._ucb.update(tier.value, healthy, success=True, latency_ms=100,
                         cost=get_cost_estimate(tier))

    # Degraded provider prior
    degraded = np.array([0.0]*10 + [0.3, 0.9, 0.2, 0.0, 0.1, 0.8])
    for _ in range(2):
        self._ucb.update(tier.value, degraded, success=False, latency_ms=2000,
                         cost=get_cost_estimate(tier))
```

The synthetic priors are pushed into the replay buffer. They are naturally displaced by the sliding window (maxlen=1000) as real observations accumulate. The prior count should be small (5-10 per model tier) to avoid dominating the network's weights.

### 8.4 Expected Impact

Provider-aware NeuralUCB addresses three classes of routing failures that are invisible to the current architecture:

**1. Provider degradation mid-session.** Currently, if a provider becomes rate-limited during a session, the router continues selecting it at its normal rate because it has no provider health signal. The user sees increased latency and error rates. With provider-aware routing, the degraded provider's health score drops, which reduces its predicted reward. The router naturally shifts traffic to healthier providers at the same tier. When the provider recovers, its health score rises, and traffic shifts back.

**2. Cost-aware provider substitution.** When the budget regime drops to LOW or CRITICAL, the current router downgrades the entire tier. Provider-aware routing enables a more nuanced response: within the same tier, prefer cheaper providers. For example, at STANDARD tier, DeepSeek reasoner costs $0.55/1M while Anthropic Sonnet costs $3.00/1M. In LOW regime, the router could prefer DeepSeek for non-critical tasks while reserving Anthropic for tasks that require its specific capabilities.

**3. Latency-aware routing during burst.** When multiple concurrent routing decisions arrive, the current router does not consider provider load. A burst of requests might all target the same provider, overloading it. Provider-aware routing would detect the rising latency (via the p95 latency feature) and distribute subsequent requests across providers with lower current load.

**Implementation cost.** The changes are localized and small:
- Add 5-6 features to `_extract_features` (or a companion method).
- Add a `_health_buffer` dict to `ProviderRegistry` with a `update_health(provider, stats)` method.
- Add a background health-checker task (optional; could be driven by execution feedback).
- Modify `_route_neural` to append provider features to the candidate evaluation.

The total code change is approximately 100 lines, plus tests. The latency impact is negligible (a dict lookup and a few floating-point operations per candidate).

**Potential risks.**
- **Overfitting to transient health fluctuations.** A single slow response could temporarily depress a provider's health score, causing a cascade of routing away from it that is unjustified. Mitigation: use a smoothed health score (exponential moving average with alpha=0.3) rather than a point estimate.
- **Cold-start thrashing.** When a new provider is added, the synthetic priors could cause over- or under-exploration. Mitigation: use small prior counts (5-10) and verify that the bandit explores the new provider sufficiently before making exploitative decisions.
- **Feedback delay.** Provider health changes faster than the neural network can adapt (seconds vs. minutes for re-training). Mitigation: keep the health-aware routing _non-learned_ for the health component (use a gating mechanism: if health < threshold, deprioritize without waiting for the neural network to learn).

## 9. Key Sources

**Research Papers:**
- DecisionBench (arXiv:2605.19099): Establishes that routing fidelity across real-world LLM evaluation benchmarks is only 7.5-29.5%, motivating the need for learned routing. This paper provides the baseline against which Lyra's router measures itself.
- Neural Contextual Bandits with UCB Exploration (Zhou et al., 2020): Theoretical foundation for the NeuralUCB algorithm used in Tier 3. Provides convergence guarantees and regret bounds.
- CARROT Minimax Regret Bound (arXiv:2502.03261): Achieves the theoretical lower bound for model routing regret. Matches GPT-4o quality at 30% cost with provable optimality guarantees. Planned for V4 integration.
- MTRouter (arXiv:2604.23530): Multi-turn cost-aware routing achieving 58.7% cost reduction through joint history/task embeddings. Identifies that optimal model selection changes as conversation context accumulates.
- SCOPE (arXiv:2601.22323): GRPO-trained router with slider-controlled accuracy-cost tradeoff and confidence-based escalation. Provides an alternative training paradigm for the neural tier.
- ARIS Cross-Model Adversarial Review (arXiv:2605.03042): Multi-model consensus routing for critical decisions, informing the ConsensusRouter design for safety-critical decisions.
- Budget-Aware Tier Selection (BATS): Google Cloud internal pattern for cost-aware resource selection. The four-regime design (HIGH/MEDIUM/LOW/CRITICAL) and the circuit breaker are direct adaptations.

**Existing Lyra Architecture Documents:**
- `docs/architecture/MODEL-ROUTER-V3.md` (v3.0.0): The NeuralUCB-based V3 design targeting 84% cost reduction. Describes the initial 3-tier cascade, NeuralUCB algorithm, and Pareto optimization.
- `docs/research/model-routing-v3-design.md`: Comprehensive RL-optimized routing design with decomposer-allocator architecture, Pareto optimization, PPO/GRPO training, continuous learning with EWC, and A/B testing framework. 2,847 lines of research depth.
- `docs/research/PLAN-4.4-MODEL-ROUTER.md`: Phase 4 plan integrating CARROT regret bounds, MTRouter multi-turn awareness, SCOPE slider, and provider fallback chains.
- `docs/research/GAP-ANALYSIS-2026-05-30.md` (Section 3): Identifies six gaps between V3 and state-of-the-art routing research, including CARROT, MTRouter, SCOPE, and multi-model ensemble voting.

**Implementation Reference (complete source):**
- `packages/lyra-router/src/lyra_router/router.py` (380 lines): Main ModelRouter class with 3-tier cascade, budget-aware decision building, and feedback loop.
- `packages/lyra-router/src/lyra_router/tiers.py` (819 lines): RuleTier (keyword/pattern matching), SemanticTier (TF-IDF/embedding similarity), NeuralTier (NeuralUCB contextual bandit with heuristic fallback).
- `packages/lyra-router/src/lyra_router/neural_ucb.py` (318 lines): Pure-numpy NeuralUCB implementation with 2-layer MLP, UCB exploration, online SGD training, and provider-aware model statistics.
- `packages/lyra-router/src/lyra_router/budget.py` (270 lines): BudgetTracker with four BATS regimes, circuit breaker at $5/session, per-task budget guidance, and budget XML context generation.
- `packages/lyra-router/src/lyra_router/providers.py` (274 lines): ProviderRegistry with 9 models across 5 providers, May 2026 pricing, lazy API key detection, and fallback model resolution.
- `packages/lyra-router/src/lyra_router/models.py` (153 lines): Frozen dataclasses for ModelTier, TaskComplexity, BudgetRegime, ModelAssignment, RoutingDecision, Provider, and cost estimation functions.
- `packages/lyra-router/src/lyra_router/consensus_router.py` (483 lines): Multi-model consensus routing for critical decisions with four consensus modes, dissent detection, and escalation.

**Test Suite:**
- `packages/lyra-router/tests/test_router.py` (689 lines): 44 test cases covering all tiers, all budget regimes, provider registry, and cascade integration.
- `packages/lyra-router/tests/test_neural_ucb.py` (432 lines): 19 test cases covering UCB selection, exploration decay, budget constraints, online learning discrimination, and Pareto-style cost-quality tradeoffs.
- `packages/lyra-router/tests/test_consensus.py`: Tests for the consensus router, dissent detection, and verdict combination.
- `packages/lyra-router/tests/test_effort_integration.py`: Tests for effort mapping integration with the ModelRouter.
