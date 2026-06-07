# Cost & Latency Economics: Token Budget Accounting with Prompt Cache Strategy
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/21-economics.md) | [Code](../../src/lyra/economics/)

## Abstract
Lyra's economics module tracks token usage and cost as first-class metrics per session, per agent, and per workflow. A token budget system enforces hard limits per session. The prompt cache hit-rate strategy targets 90%+ on static prefixes (system prompts, tool definitions). Combined with the model router's memory-augmented routing, Lyra targets 40-60% cost reduction vs single-model baseline.

## Method
**Budget management** (`src/lyra/economics/`): per-session token budget with hard limits, per-agent cost tracking, burn reports. **Five-primitive cost model** (from OpenJarvis): Intelligence (model) + Engine (runtime) + Agents (loop) + Tools & Memory + Learning (optimizer) — each with independent cost accounting.

| Primitive | Cost Driver | Optimization |
|-----------|------------|-------------|
| Intelligence | Model tier × tokens | Router → cheapest qualifying model |
| Engine | KV-cache + batch size | Prompt caching, speculative decoding |
| Agents | Loop iterations × tokens/iteration | WorkspaceReport M_t (O(1) context) |
| Tools & Memory | Retrieval calls × embedding cost | Two-stage retrieval, caching |
| Learning | Optimization runs × eval cost | Bounded-edit, amortized teacher cost |

## Conclusion
Implemented: token tracking, budget limits, cost per agent/workflow. Future: prompt-cache hit-rate optimization, speculative decoding for agent workloads.
