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
