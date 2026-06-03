# Model Router -- Learning Path

> **Phase:** 3 | **Composes blocks:** Context Engine, Permission Bridge, Hooks & TDD Gate, Observability HIR | **Architecture doc:** [09-model-router.md](../../architecture/09-model-router.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- intelligent inference routing across providers, 5-slot architecture (NORMAL, THINKING, COMPACT, CRITIQUE, VLM), cost optimization and automatic failover |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | 4-tier model pool (REASONING, STANDARD, FAST, CHEAP), 5 routing strategies (COST_OPTIMAL, PERFORMANCE_MAX, BALANCED, MULTI_TURN, CONFORMAL), multi-turn escalation logic, budget enforcement via cost multipliers |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Router code patterns, gateway integration pattern, agent loop multi-turn integration, fallback cascades, slot health state machine |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Keyword-based vs ML routing, slot granularity trade-offs, health state algorithms (exponential moving average), error decay on success |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | Routing decision latency (<1ms), throughput benchmarks, cost savings per strategy, fallback rates |

## In 30 Seconds

The Model Router is Lyra's intelligent routing layer that selects the optimal LLM for each task. It uses a 5-slot system (NORMAL, THINKING, COMPACT, CRITIQUE, VLM) with automatic health-based fallback. A 4-tier model pool assigns models by capability (REASONING, STANDARD, FAST, CHEAP) and tracks cost and accuracy. Multi-turn routing escalates complex or long-context tasks to reasoning-tier models. All decisions are frozen dataclasses for auditability. Zero external dependencies -- pure Python with immutable data structures.

## What This System Composes

| Block | Role |
|-------|------|
| [Context Engine](../../blocks/06-context-engine.md) | Context window limits and compaction triggers per slot |
| [Permission Bridge](../../blocks/04-permission-bridge.md) | Budget/quota enforcement and cost-aware routing decisions |
| [Hooks & TDD Gate](../../blocks/hooks-tdd/) | Pre/post-routing hooks for decision logging and analytics |
| [Observability HIR](../../blocks/13-observability-hir.md) | Routing decision traces and cost analytics per turn |

## Quick Reference

- **When you need this:** Routing tasks across multiple LLM providers, optimizing cost vs. quality, building fallback-resilient agent systems
- **Related architecture doc:** [09-model-router.md](../../architecture/09-model-router.md)
- **Upgrade plan:** [05-model-router.md](../../lyra-upgrade/plans/05-model-router.md)
- **Concept docs:** [two-tier-routing.md](../../concepts/two-tier-routing.md), [prompt-cache-coordination.md](../../concepts/prompt-cache-coordination.md)
- **Key packages:** `packages/lyra-model-router/` (intelligent router), `packages/lyra-core/src/lyra_core/orchestration/model_router/` (core 5-slot router)

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
