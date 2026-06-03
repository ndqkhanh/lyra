# Performance & Cost Economics — Plan (§4.21)

> Run 1 — June 3, 2026

## Plain-Language Summary

Lyra tracks every token spent — per session, per agent, per workflow — so you know exactly what your fleet costs. Prompt caching cuts costs 90% on repeated prefixes. Token budgets prevent runaway spending. The economics dashboard shows you where your money goes and suggests optimizations.

## Key Features

1. **Token Accounting:** Per-session, per-agent, per-workflow token tracking with real-time cost estimation (Anthropic/DeepSeek/GPT pricing tiers)
2. **Prompt-Cache Strategy:** Static prefix (system prompt + skill frontmatter) designed for 90% cache-hit rate. Stagger parallel session starts to maximize cache reuse. 5-min TTL management.
3. **Token Budgets:** `budget.total`, `budget.spent()`, `budget.remaining()` — workflow scripts query remaining budget to decide scale
4. **Amdahl's Law for Agents:** Parallelism stops paying when coordination overhead > speedup. Fleet concurrency auto-tuned.
5. **Cost Dashboard:** `/cost` command → per-session breakdown, per-model spend, projected monthly cost, cache-hit rate
6. **Speculative Decoding (Anthropic-only):** Haiku drafts tokens → Sonnet/Opus verifies in parallel. 2-3× latency reduction.

## Multi-Provider Note

Pricing tiers auto-detected from provider config. Cache-hit strategy works across Anthropic (native prompt cache) and DeepSeek (KV-cache reuse). Speculative decoding limited to Anthropic (both draft + target same provider).

**Impact:** 3 | **Effort:** 2 | **Tier:** (A) Parity

## Evidence Synthesis

| Source | Key Insight |
|--------|------------|
| Claude Code Costs docs (§3.1) | Per-session, per-workflow token tracking; Haiku-class model for meta/monitoring |
| Prompt Caching (Anthropic docs) | 90% cache-hit rate achievable with static prefix design; 5-min TTL management |
| FrugalGPT (2305.05176) | LLM cascade: route simple queries to cheap models → 98% cost reduction at same accuracy |
| Cost-Augmented MCTS (2505.14656) | Budget-aware search — MCTS that respects token budgets as a constraint |
| IdleSpec (2605.22154) | Speculative planning during tool-waiting time → 2-3× agent loop speedup |
| Amdahl's Law | Parallelism stops paying when coordination overhead > speedup; auto-tune fleet concurrency |

## Baseline Delta

| Component | Change | Migration Cost |
|-----------|--------|---------------|
| lyra-cost (package) | EXTEND: per-workflow, per-agent, per-session tracking | Low — existing cost tracking |
| Prompt-cache strategy | ADD: static prefix design, 5-min TTL management | Low — provider-level config |
| Token budgets | ADD: budget.total/spent/remaining API for workflow scripts | None — new |
| Cost dashboard | ADD: `/cost` command | Low — new slash command |

## Expert Review

**Senior Performance Engineer:** "The biggest cost lever is routing 80% of queries to cheap models. A $0.0001/call Haiku handles meta/monitoring; $0.003 Sonnet handles routine tasks; $0.015 Opus handles reasoning. The router doubles as a cost optimizer."

**Skeptic:** "Budget API (`budget.remaining()`) is clever but unused if users don't set budgets. Default to a daily cost cap ($50) that warns at 80% and stops at 100%." → ADOPTED.
