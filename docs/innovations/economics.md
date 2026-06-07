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

## Use Cases

**Scenario 1: Startup optimizing LLM costs.** A bootstrapped startup runs an AI-powered customer support agent that handles 10,000 conversations per month. Each call goes through Opus by default — costing $4,000/month. They plug in Lyra's economics module. The BudgetManager tracks spend in real time. The model router automatically downgrades simple queries (password reset, store hours) to Haiku, saving 20x on those turns. Complex troubleshooting stays on Sonnet. Only edge-case escalations use Opus. Monthly bill drops to $1,200. The startup ships the same quality at 70% lower cost.

**Scenario 2: Enterprise budget allocation across teams.** An organization has 5 product teams sharing a $50,000/month LLM budget. Each team has different usage patterns: the documentation team mostly generates text (high output tokens), the data team does heavy analysis (large input context), and the engineering team runs agent loops (many small calls). The economics module tracks cost per team, per primitive (intelligence, engine, agents, tools, learning). At month-end, the burn report shows engineering is overspending on agent loops — each loop iteration costs $0.02 in engine overhead. They optimize by consolidating tool calls, and the following month's report confirms the fix.

**Scenario 3: Cost-aware feature rollout.** A product manager wants to add "AI commit message generation" to the development workflow. Before writing any code, they use the economics module to estimate the cost impact: 100 developers x 5 commits/day x 50 tokens/output = 7,500 tokens/day at Haiku rates = $7.50/day. The prompt cache hit-rate monitor confirms that the commit-message system prompt can be cached at 95% hit rate, bringing effective cost to $2/day. The PM greenlights the feature with a hard monthly budget of $60. The BudgetManager enforces it automatically.

## Conclusion
Implemented: token tracking, budget limits, cost per agent/workflow. Future: prompt-cache hit-rate optimization, speculative decoding for agent workloads.

## Working Flow

Every LLM call costs money, and Lyra tracks every token. Here's how the budget system keeps costs under control.

When you start a session, Lyra assigns a token budget from `src/lyra/economics/budget.py`. Every `ProviderBackend.chat()` call in `src/lyra/routing/` reports its token usage back — input tokens, output tokens, and cache hit tokens. The `BudgetManager` subtracts these from your session budget in real time. If you're approaching the limit, Lyra automatically switches to cheaper model tiers: Sonnet becomes Haiku, Opus becomes Sonnet. The prompt cache hit-rate monitor tracks how often static prefixes (system prompts, tool definitions) get served from cache vs recomputed — targeting 90%+ to minimize wasted spend.

**Example:** You run a 50-turn coding session with a $5 budget:
1. The `BudgetManager` initializes with 5,000,000 token budget at $1/1M tokens
2. Turn 1-10: Opus for architecture (~50K tokens, $0.75) — budget at 85%
3. Turn 11-30: Sonnet for implementation (~200K tokens, $0.60) — budget at 73%
4. Turn 31-50: Haiku for polish + status checks (~100K tokens, $0.03) — budget at 72%
5. The router auto-escalates: expensive model only for novel decisions, cheap model for routine work. Final cost: $1.38 vs $5.00 unoptimized.
