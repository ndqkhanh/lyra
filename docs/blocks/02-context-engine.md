# Context Engine -- How It Works

> Five-layer compression pipeline that transforms the raw filesystem, conversation history, and memory references into a compact, cache-optimized transcript. Every layer has a distinct stability score and compaction policy.
> **Block:** 02 | **Phase:** 1 (Core Infrastructure) | **Depends on:** Agent Loop | **Provides:** ContextAssembly, Compaction, Cache Optimization

## The Five-Layer Pipeline

The engine assembles context as a five-layer stack, assembled top-to-bottom, with each layer having a distinct stability score and compaction rule:

```
L1: SOUL           [200-500 tok, stability 1.0]  ← never compacted
L2: STATIC_CACHED  [2K-10K tok, stability 0.99]  ← never compacted
L3: DYNAMIC        [10K-100K tok, stability 0.10] ← compacted at 85%
L4: COMPACTED      [1K-5K tok, stability 0.30]    ← lazy compaction
L5: MEMORY_REFS    [100-500 tok, stability 0.85]  ← never compacted
```

### Layer 1: SOUL (Filesystem-as-Context)

The SOUL layer is assembled from the user's repository using a Mermaid-rendered architecture diagram, the README, directory structure, and key configuration files. It represents the "persona" of the repository -- what the agent is, where it is, and what it cares about.

**Stability: 1.0** -- SOUL is never compacted, never modified mid-session. Research shows persona drift is the dominant failure mode in long sessions: after 50+ turns, agents without a stable persona exhibit 34% increase in tone inconsistency and 28% increase in constraint violations (COMPASS, arXiv:2510.08790).

### Layer 2: STATIC_CACHED (Rules and Tools)

System prompts, `.claude/rules/*`, tool definitions, and skill descriptions. These change only when the session configuration changes (e.g., loading a new skill).

**Stability: 0.99** -- Volatility is near-zero. Cache breakpoints are placed after L1 and L2 for maximum prefix cache hits.

### Layer 3: DYNAMIC (Conversation Turns)

Recent user messages and tool results. This is the growing layer -- each turn appends one user message and one or more tool observations.

**Stability: 0.10** -- Changes every turn. When utilization exceeds 85% of the configured token budget, compaction is triggered.

### Layer 4: COMPACTED (Summarized History)

Old DYNAMIC content, summarized by a cheaper model (Haiku). The Compactor targets 65% token reduction at 88% information preservation (balanced mode).

```
CompactionTrigger: L3.utilization > 0.85 * max_tokens
Compactor: Haiku model, 500-2000ms, ~$0.002 per compaction
AltitudeScore(turn) = 0.6 * recency + 0.4 * signal_strength
Items below threshold enter compaction queue first
```

### Layer 5: MEMORY_REFS (Pointers into Memory)

Lightweight pointers (observation IDs, snippets) that the Memory System (Block 03) resolves on demand. Three-layer progressive disclosure: `search()` returns IDs + snippets, `timeline()` returns temporal neighbors, `get()` returns full content.

## Adaptive Compaction and Lean-Ctx

The engine uses three optimization strategies aligned with Anthropic's recommended framework:

| Strategy | Mechanism | Savings |
|----------|-----------|---------|
| **Compaction** | Old turns summarized by Haiku | 65% compression, 88% info preservation |
| **Clearing** | Tool outputs truncated head-tail-elide | 93% token reduction on structured content |
| **Sub-agents** | Cross-session knowledge via L5 refs | 77% of irrelevant tokens avoided |

The `token_compressor.py` module applies structured truncation (removes verbose metadata), semantic compression (replaces redundant text with inline summaries), and per-layer token budget enforcement. Achieves 89-99% reduction on structured content (JSON logs, file listings, diff output).

## Context Budget Management

The budget is tracked per-layer with fallback strategies:

```python
budgets = {
    SOUL: 500,
    STATIC_CACHED: 10_000,
    DYNAMIC: 150_000,
    COMPACTED: 5_000,
    MEMORY_REFS: 500,
}
total_budget = sum(budgets.values())  # 166,500 tokens

# On compaction trigger
if utilization > 0.85:
    # Compact oldest L3 items first (by altitude score)
    compacted = compactor.compact(dynamic_content)
    # Move summaries to L4, keep high-altitude items in L3
    dynamic_content = keep_high_altitude(dynamic_content)
    compacted_layer += compacted
```

## Cache Breakpoint Optimization

Breakpoints are placed after L1 and L2 to maximize stable prefix size. The `PrefixStabilizer` assigns volatility estimates: system prompts = 0.01, tool definitions = 0.05, recent turns = 0.90. When layer content changes, breakpoints are dynamically adjusted to keep the largest possible stable prefix.

Provider-aware alignment:
- **Anthropic**: Explicit `cache_control` breakpoints after L1 and L2
- **OpenAI**: Implicit prefix matching -- L1+L2 form the stable prefix
- **Gemini**: `cachedContent` API keyed to L1+L2 content hash

## Performance

| Metric | Value |
|--------|-------|
| Assembly latency (cold) | 5-15ms |
| Assembly latency (warm) | 2-5ms |
| Cache hit rate L1+L2 | 99.2% / 89.4% |
| Cost per 100-turn session (layered) | $17.63 |
| Cost per 100-turn session (flat/uncached) | $75.00 |
| Cost reduction vs baseline | 76% |

## Related Documents

- **Concepts:** [Context Engine](../concepts/07-context-engine.md), [Prompt Cache Coordination](../concepts/14-prompt-cache-coordination.md), [Two-Tier Routing](../concepts/10-two-tier-routing.md)
- **Architecture:** [Architecture Overview](../architecture/11-architecture-overview.md), [Provider Abstraction](../architecture/03-provider-abstraction.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Memory](03-memory.md), [Permission Bridge](05-permission-bridge.md)

---

*References: COMPASS (arXiv:2510.08790), Neuro-Compaction (arXiv:2604.18002), Lost in the Middle (arXiv:2307.03172), Prompt Cache (arXiv:2405.12981)*
