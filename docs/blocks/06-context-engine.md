# Lyra Block 06 — Context Engine (Five-Layer)

The Context Engine is responsible for what the LLM sees each turn. It implements the five-layer context pipeline (prompt cache prefix → cached mid → dynamic → compaction → memory refs) and the progressive-disclosure retrieval pattern borrowed from [claude-mem](../../../../docs/72-claude-mem-persistent-memory-compression.md).

Upstream references: [Orion-Code Block 04](../../../orion-code/docs/blocks/04-context-engine.md), [Claude Code audit](../../../../docs/29-dive-into-claude-code.md), [Four Pillars § Context Architecture](../../../../docs/44-four-pillars-harness-engineering.md), [Context Compaction dive](../../../../docs/08-context-compaction.md).

## Responsibility

1. **Assemble** a fresh transcript at session start from SOUL + plan + seeded observations.
2. **Compact** a running transcript when it crosses the token threshold, preserving invariants.
3. **Reduce** raw tool observations into transcript-sized observations (with artifact offload).
4. **Disclose** memory references on demand (3-tool progressive-disclosure MCP).
5. **Cache** layout strategies per provider (Anthropic explicit breakpoints; OpenAI/Gemini implicit).

## The five layers

Layered from always-present to most ephemeral.

### L1 — Cached prefix (rarely changes)

Contents:

- System prompt (Lyra system instructions).
- Tool schemas (complete, including MCP tools registered for this session).
- Global constants (agent name, version, permission mode name).

Size: ~5-12 KB typical. Stable across sessions; Anthropic prompt cache hits 90%+.

### L2 — Cached mid (session-stable)

Contents:

- `SOUL.md` ([block 08](08-soul-md-persona.md)) — never-compacted persona.
- Plan artifact summary (first page + acceptance tests).
- TODO list current state (derived from plan + progress).
- Skills in scope (names + descriptions only; bodies loaded on invoke).
- MCP server descriptions.

Size: ~3-8 KB. Changes when plan is revised or todo updates; invalidates cache for that mid-block.

### L3 — Dynamic (per-turn growing)

Contents:

- Recent turns (model responses + tool calls + reduced observations).
- Current critique if any (from hooks).
- Current user interjection if interactive.

Size: grows as turns accumulate. Target 40-60 KB steady state; compaction triggers at ~85% of `max_tokens`.

### L4 — Compaction (derived)

When L3 crosses the threshold, a compactor replaces older turns with a summary:

- Summary style: narrative of actions + key decisions + open issues.
- Preserves: file:line anchors, failing test names, unresolved questions, tool-call counts.
- Discards: raw output bodies (already in artifacts), repetitive confirmations.

The compaction itself is a model call (the planner or a cheaper summarizer). Cached artifacts are referenced by hash; model can `View` them.

### L5 — Memory refs (on-demand)

A 3-tool progressive-disclosure MCP surface (aligning with [claude-mem](../../../../docs/72-claude-mem-persistent-memory-compression.md) pattern):

```
MemorySearch(query, limit=5)   → list of {id, title, snippet, score}
MemoryTimeline(tag|date_range) → list of {id, ts, kind, title}
MemoryGet(id)                   → full content (cited)
```

Agent uses them when it suspects the answer exists in memory; never preloaded.

## Assembly

```python
def assemble(session: Session, task: str, plan: Plan|None) -> Transcript:
    msgs = []
    msgs.append(Message.system(session.system_prompt()))                # L1
    msgs.append(Message.system(soul.read(session)))                      # L2: SOUL
    if plan:
        msgs.append(Message.system(plan.summary_for_context()))          # L2: plan
    msgs.append(Message.system(todo.render(session)))                    # L2: todo
    msgs.append(Message.system(skills.scope_descriptions(session)))      # L2: skills
    msgs.append(Message.system(mcp.registered_descriptions(session)))    # L2: mcp
    msgs.append(Message.user(task))                                       # L3: seed
    return Transcript(msgs, cache_breakpoints=[
        after=L1_idx, after=L2_idx,
    ])
```

Each section has a stable ordering so prompt caching works across turns.

## Compaction

Threshold: compact when `transcript.tokens > max_tokens * 0.85`. Hard cap: if compaction fails, drop middle third and annotate.

Algorithm:

1. Identify the **keep-window**: last K turns (default 10), current user interjection, any sticky critique.
2. Identify the **compact-window**: turns between initial seed and the keep-window.
3. Generate summary: run the planner or a summarizer model with the compact-window as input; target 1/5 of original tokens.
4. Replace compact-window with a single system-message summary carrying:
    - Narrative of decisions + actions.
    - Pointers to artifacts (by hash).
    - Unresolved questions.
5. Emit `compaction` trace event with `tokens_before`, `tokens_after`, `summary_artifact_hash`.

**Invariants preserved**:

- Every `PermissionDecision.deny` reason is preserved verbatim (so the agent doesn't retry blocked tools).
- Every TDD-gate critique is preserved.
- Failing-test names and file:line anchors preserved.

## Observation reduction

`reduce(result, session) → observation`:

| Result kind | Reduction |
|---|---|
| Text > 4KB | First 30 lines + tail 10 lines + `…elided…` marker + artifact reference |
| File listing > 100 entries | First 50 + count + hint to `Glob` with a narrower pattern |
| Test output | Pass/fail count summary + first 20 lines of first failure + artifact ref |
| Git diff | Stat summary (files, insertions, deletions) + first N hunks + artifact ref |
| Binary content | `<binary N bytes, sha256:…>` marker |
| Injection-tainted | Sanitized core + `<injection-removed>` marker |

Artifacts written to `.lyra/artifacts/<hash>/` are accessible via a `View(hash)` tool.

## Caching strategies per provider

| Provider | Mechanism | Our usage |
|---|---|---|
| Anthropic Claude | explicit `cache_control: {type: ephemeral}` blocks | breakpoint after L1, after L2 |
| OpenAI GPT-5 | implicit "common prefix" cache | we just keep L1+L2 stable |
| Google Gemini | `cachedContent` context API | we create a cached content object per session-stable L1+L2 |
| Local (Ollama / vLLM) | KV cache internal | prompt stability only |

Savings: 50-90% off input tokens on long sessions — substantial cost win.

## Progressive disclosure (3-tool memory)

Tools registered:

```python
@tool(name="MemorySearch", writes=False, risk="low")
def memory_search(query: str, limit: int = 5) -> list[dict]: ...

@tool(name="MemoryTimeline", writes=False, risk="low")
def memory_timeline(tag: Optional[str] = None,
                    since: Optional[str] = None,
                    until: Optional[str] = None,
                    limit: int = 10) -> list[dict]: ...

@tool(name="MemoryGet", writes=False, risk="low")
def memory_get(observation_id: str) -> dict: ...
```

Usage pattern (the model learns via the tool descriptions):

1. Search with query → candidate IDs + snippets + scores.
2. Inspect promising candidate with Timeline (context of when/why it was stored).
3. Fetch full content with Get.

Only the fetched content enters context — typically 10× smaller than if we preloaded the memory.

## TODO rendering

TODO list is a derived view of the plan's feature items:

```markdown
# TODO (session 01HXK2N…)

- [x] 1. (localize) Find call sites of auth.authenticate. ✓ ff4a2c
- [>] 2. (edit) Rewrite authenticate to use jose. In progress. step=12 cost=$0.34
- [ ] 3. (edit) Update call sites. depends=[2]
- [ ] 4. (test_gen) JWT failure modes. depends=[2]
- [ ] 5. (review) Full suite + security review. depends=[3,4]
```

The TODO is injected as an L2 system message (stable across turns). As items complete, the TODO updates in-place; cache invalidates for that block only.

## Entropy management

Per [Four Pillars Pillar 4](../../../../docs/44-four-pillars-harness-engineering.md): context without maintenance becomes noisy. Context Engine:

- **Stale observation eviction.** Observations older than M turns with no citations are dropped (but remain in trace).
- **Critique decay.** A hook critique that was acted on and resolved is marked `resolved` and removed from the active context.
- **Dead-TODO cleanup.** Items marked `rejected` or `blocked_upstream` are summarized into a single line.

All eviction events are traced.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Compaction loses a critical detail | Invariants preserved list + traceable summary artifact |
| Compact model hallucinates | Summary is compared to source by a second pass heuristic (token overlap); discrepancy flagged |
| Cache misses mid-session | Surfaced in trace; if sustained, suggests L2 volatility issue (frequently changing SOUL or plan) |
| Progressive disclosure under-retrieves | MemorySearch description coached to use broad queries first |
| Context explodes despite compaction | Hard cap: force reduction to half; emit `context.forced_cap` span |
| Observations reduce away too aggressively | `View` tool fetches artifact; agent learns to use when summary insufficient |

## Metrics emitted

- `context.tokens_current` gauge
- `context.compactions.count`
- `context.compaction.tokens_saved`
- `context.cache_hit_ratio` labeled by layer
- `context.offload.count`, `context.offload.bytes`
- `context.reduce.ratio` histogram (input/output size)
- `context.memory_tool_invocations.count` labeled by tool

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_context_engine.py` | Assemble outputs stable layout; compaction preserves invariants |
| Unit `test_reduce.py` | Each observation kind reduces correctly |
| Unit `test_progressive_disclosure.py` | Tool descriptions; 3-tool flow |
| Integration | Long session crosses compaction threshold; verifier still accepts |
| Property | Cache breakpoints stable across turns |
| Replay | Recorded long trace re-runs; compaction is deterministic in temp=0 |

## Open questions

1. **Cache across sessions.** Tempting for L1; we disable to avoid leakage. v2: scoped cache keys.
2. **Compaction model choice.** Planner (Opus) is high-quality but costly; nano is cheap but loses fidelity. Route adaptive?
3. **Per-provider prompt structure divergence.** Different providers prefer different layouts for cache; we pay some token overhead with a lowest-common-denominator layout. v2 per-provider structure.
4. **Vector-based memory ranking.** Beyond BGE-small, exploring stronger embedders at cost.
