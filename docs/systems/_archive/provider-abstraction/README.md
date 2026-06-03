# Provider Abstraction -- Learning Path

> **Phase:** 3 | **Composes blocks:** MCP Adapter, Hooks & TDD Gate, Context Engine | **Architecture doc:** [03-provider-abstraction.md](../../architecture/03-provider-abstraction.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- decoupling all Lyra components from provider-specific APIs via 322 lines of canonical interface, 4 adapters (Anthropic, OpenAI, DeepSeek, Google/stub), zero provider-specific code above the abstraction boundary |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | Canonical type design (Message, ToolCall, ChatRequest, ChatResponse, StreamEvent), effort translation strategy per provider, streaming normalization (6 event types), error taxonomy with retryable flags |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Adapter implementation patterns (Anthropic 442 lines, OpenAI 286 lines, DeepSeek 421 lines), HTTP client strategies, capability matrix queries, provider bridge for skills integration |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Canonical vs pass-through design, per-adapter effort mapping, prompt caching integration strategies, provider SDK vs raw HTTP trade-offs |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | <100us overhead per request, memory footprint per canonical type (<5KB for 20-message conversation), per-provider latency comparison |

## In 30 Seconds

The Provider Abstraction layer is Lyra's architectural seam that normalizes 3+ AI provider APIs into a single canonical interface (7 methods on AbstractProvider). Every higher-level component -- router, skills, orchestration, memory -- writes once against the abstract protocol and runs on any provider. Effort parameters (thinking budget, reasoning effort) are automatically translated per provider: Anthropic's budget_tokens, OpenAI's reasoning_effort, DeepSeek/Google prompt injection. Total overhead is under 100 microseconds per request.

## What This System Composes

| Block | Role |
|-------|------|
| [MCP Adapter](../../blocks/mcp-adapter/) | Partner pattern for external tool integration via standard interfaces |
| [Hooks & TDD Gate](../../blocks/hooks-tdd/) | Pre/post-call hooks for request validation and response transformation across providers |
| [Context Engine](../../blocks/06-context-engine.md) | Provider-adaptive compaction thresholds based on each provider's context window size |

## Quick Reference

- **When you need this:** Adding a new LLM provider, building provider-agnostic tooling, normalizing cross-provider streaming and effort semantics
- **Related architecture doc:** [03-provider-abstraction.md](../../architecture/03-provider-abstraction.md)
- **Concept doc:** [prompt-cache-coordination.md](../../concepts/prompt-cache-coordination.md)
- **Package:** `packages/lyra-provider/src/lyra_provider/`
- **How-to guide:** [configure-providers.md](../../howto/configure-providers.md)

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
