# Guide: Model Routing

> 📖 Guide — Understand how Lyra picks which model handles each task. Walk through the routing decision: classify, estimate difficulty, check memory, select tier, select provider, apply effort.

The model router decides which LLM handles each call -- fast/cheap for routine work, smart/expensive for complex reasoning. This guide walks the complete decision path.

---

## The Routing Decision (6 Steps)

On every model invocation, the router follows this sequence:

### Step 1: Classify Task

The query classifier identifies the task type from seven categories: factual, recent, procedural, creative, analytical, coding, planning. Classification uses a hybrid heuristic: linguistic pattern matching (57% coverage), then semantic signals (+33% to 90%), then embedding similarity as tiebreaker (+4% to 94%). Total overhead: <1ms for rule-based, ~5ms with embeddings.

### Step 2: Estimate Difficulty

The effort estimator maps task type + complexity signals to one of four levels:

| Effort | Use Case | Model |
|---|---|---|
| low | Simple lookups, formatting, routine edits | Fast slot |
| medium | Standard coding tasks, test generation | Smart or fast |
| high | Architecture decisions, planning | Smart slot |
| ultracode | Complex multi-agent tasks | Smart + fleet |

### Step 3: Check Memory

Before any model invocation, the router checks the memory cache. If the query is a near-duplicate of a previously answered question (embedding similarity > 0.92), the cached answer is served directly from the cheapest memory tier -- no LLM call at all. This yields up to 96% cost reduction on repeat queries (from "Knowledge Access Beats Model Size", arXiv:2603.23013).

### Step 4: Select Tier

| Slot | Default Model | % of Calls | % of Cost |
|---|---|---|---|
| Fast | deepseek-v4-flash | 73% | 22% |
| Smart | deepseek-v4-pro | 27% | 78% |

Why two slots? 90% of decisions collapse to "fast vs smart." Per-role slots (generator, planner, evaluator, safety) explode configuration complexity. Two tiers capture 95% of cost optimization.

### Step 5: Select Provider

Every LLM provider implements a common `Provider` protocol:

```python
class Provider(Protocol):
    async def chat(self, transcript, tools, **kwargs) -> Response: ...
    def count_tokens(self, text: str) -> int: ...
    @property
    def supports_caching(self) -> bool: ...
```

Supported providers: Anthropic (90% cache read discount), DeepSeek (cost leader, 90% prefix cache), OpenAI (50% auto-cache), Google Gemini (75% cache, 1M+ context), open-weight models (local, private). Provider adapters handle auth, message format translation, cache markers, and error retry. Switching providers is a config change:

````toml
[provider]
primary = "deepseek"
fallback = "anthropic"
fallback_on_error = true
```

### Step 6: Apply Effort

The final decision is captured as a `RoutingDecision` struct:

| Field | Example |
|---|---|
| task_type | coding |
| effort_level | high |
| selected_provider | deepseek |
| selected_model | deepseek-v4-pro |
| expected_cost | $0.12 |
| cache_hit_probability | 0.89 |

Below a confidence threshold of 0.6, the router falls back to the next provider in the fallback chain.

---

## Cost Optimization

### The Three Cache Levels

| Level | Cache Breakpoint | Hit Rate |
|---|---|---|
| L1 | System prompt + tool schemas | 99.2% |
| L2 | SOUL + plan + skill descriptions | 89.4% |
| L3 | Recent turns | 15.1% |

Per-session cost: $1.87 without caching, $0.42 with caching (77.5% savings).

### Budget Profiles

```toml
# Budget-conscious: ~$0.50/task, 85% accuracy
smart_slot = "deepseek-chat"
fast_slot = "deepseek-chat"

# Balanced (default): ~$2.00/task, 95% accuracy
smart_slot = "deepseek-v4-pro"
fast_slot = "deepseek-v4-flash"

# Quality-first: ~$8.00/task, 99% accuracy
smart_slot = "claude-opus-4-7"
fast_slot = "deepseek-v4-pro"
```

---

## Related Docs

- [Architecture: Model Router](../architecture/09-model-router.md) -- provider abstraction, two-stage routing
- [Architecture: Provider Abstraction](../architecture/03-provider-abstraction.md) -- adapter pattern, provider matrix
- [Concept: Two-Tier Routing](../concepts/10-two-tier-routing.md) -- effort levels, cost analysis
- [Block: Prompt Cache Coordination](../blocks/14-prompt-cache-coordination.md) -- sibling subagent cache sharing
- [Guide: Agent Execution](01-agent-execution.md) -- the loop that invokes the router
- [Guide: Skills and Evolution](03-skills-and-evolution.md) -- provider-aware skill degradation
