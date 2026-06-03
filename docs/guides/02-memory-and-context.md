# Guide: Memory and Context

> 📖 Guide — Understand how memory and context work together: when Lyra reads from memory, when it writes back, and what happens when the context window gets full.

This guide maps the read/write flow across memory tiers and the context engine, so you understand why Lyra remembers across sessions and how it avoids context overflow.

---

## When Lyra Reads (Retrieval Cascade)

On every turn, the context engine assembles the model's input by walking five layers. Retrieval itself follows a cost-sensitive cascade -- only falling through to more expensive stores when needed:

```
Working (T1, <1ms) -> Episodic (T2, <5ms) -> Semantic (T3, <50ms) -> Archive (T4, <200ms) -> LLM Fallback (>500ms)
```

Each tier tries first. If results have confidence below threshold, the cascade falls through to the next. This yields 52% cost reduction vs always-querying the LLM.

### The Five Context Layers

The assembled prompt has five layers, each with different volatility:

| Layer | Contents | Cache Hit Rate |
|---|---|---|
| L1 prefix | System prompt, tool schemas | 99.2% |
| L2 mid | SOUL.md, plan summary, skill descriptions | 89.4% |
| L3 dynamic | Recent turns, current critique | 15.1% |
| L4 compaction | Narrative summary of older turns | Triggered |
| L5 memory refs | 3-tool MCP: search -> timeline -> get | On demand |

L1 and L2 use explicit `after` cache breakpoints. L3 never caches. L4 is an LLM-compressed summary that replaces old L3 content. L5 uses progressive disclosure -- the model preloads nothing and fetches memory bodies only when promising snippets match.

---

## When Lyra Writes (Admission & Storage)

After each turn, Lyra evaluates what to persist:

### Traces (Always)

Every tool call, permission decision, and model invocation is recorded in the HIR event stream (`trace.jsonl`). This is non-optional -- it powers replay, cost analysis, and drift detection.

### Facts (Admission-Gated)

The A-MAC 5-factor gate scores each candidate on utility (0.30), confidence (0.25), novelty (0.20), recency (0.15), and content priority (0.10). Candidates scoring below 0.50 are rejected or given TENTATIVE status for async evaluation. About 40% are rejected.

### Strategies (ReasoningBank)

Every failure generates at least one anti-skill lesson. Every successful trajectory generates a strategy lesson. The distiller is deterministic (zero LLM cost) and persists to SQLite+FTS5.

### Patterns (Field-Theoretic Dreaming)

During idle cycles, the dreaming engine consolidates memories: merge duplicates, reinforce patterns, decay noise. Light consolidation runs every cycle (~50ms); deep consolidation runs every N cycles or after 5+ minutes idle (1-5s).

---

### Cache Hit Metrics

A healthy session runs at 80%+ L1+L2 hit rate. Cost impact: $1.87/session without caching vs $0.42/session with caching (77.5% savings). The prompt-cache coordinator extends this to multi-agent scenarios -- when N sibling subagents read the same shared prefix, one write upfront saves N-1 full-price reads. On Anthropic, a 6,000-character shared prefix across 10 agents saves ~121K tokens per fan-out.

---

## When Context Gets Full (5-Layer Compression)

The compaction engine triggers when transcript tokens exceed 85% of max tokens:

1. **Identify keep-window**: last K turns (current working context)
2. **Identify compact-window**: older turns
3. **Summarize**: LLM compresses compact-window into a narrative summary
4. **Archive**: raw bodies stored hash-addressed in artifacts/
5. **Rebuild**: new transcript = L1 + L2 + summary + keep-window

Preserved: file:line anchors, failing test names, unresolved questions. Discarded: raw output bodies, repetitive confirmations. SOUL.md is **never** compacted -- persona drift is the dominant long-session failure mode.

---

## Related Docs

- [Architecture: Memory Tiers](../blocks/03-memory.md) -- A-MEM Zettelkasten, four-tier TKG
- [Architecture: Context Engine](../blocks/02-context-engine.md) -- 5-layer assembly, cache breakpoints
- [Concept: Memory Tiers](../concepts/06-memory-tiers.md) -- read/write patterns per tier
- [Concept: Context Engine](../concepts/07-context-engine.md) -- compaction, lean-ctx dialect
- [Concept: Reasoning Bank](../concepts/15-reasoning-bank.md) -- lesson distillation
- [Architecture: Prompt Cache Coordination](../blocks/14-prompt-cache-coordination.md)
- [Guide: Research and Verification](07-research-and-verification.md) -- Reflexion lessons
