# Tencent/TencentDB-Agent-Memory -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: A four-layer (L0->L1->L2->L3) local memory system plugin for AI coding agents (OpenClaw, Hermes) that rejects flat vector storage in favor of layered, symbolically-compressed memory with full drill-down traceability.

**How the code really works:**

The system implements two distinct but complementary memory mechanisms:

### A. Long-term Memory (the L0->L1->L2->L3 semantic pyramid)

This is the core contribution. Instead of shredding conversations into flat vector fragments and relying on blind similarity search, TencentDB Agent Memory builds a progressive semantic pyramid:

- **L0 (Conversation)**: Raw dialogue persisted as JSONL files under `~/.openclaw/state/memory-tdai/conversations/`. Captured automatically at every `agent_end` hook via `auto-capture.ts`. Each turn produces a JSONL line with role, content, timestamp.
- **L1 (Atom)**: Structured memory extraction performed by `l1-extractor.ts` using an LLM. Called on a pipeline timer (every N conversations, default 5). Extracts atomic facts (preferences, decisions, project context) and stores them both as SQLite rows (with `sqlite-vec` vector embeddings for semantic search) and as JSONL files. Dedup via `l1-dedup.ts` uses embedding similarity or keyword conflict detection.
- **L2 (Scenario)**: Scene block extraction via `scene-extractor.ts`. Groups related L1 atoms into named scenes (e.g., "Project architecture discussion", "Database schema review"). Each scene is a Markdown file under `scene_blocks/` with full natural language description. Uses LLM with file-tool access to write structured scene files.
- **L3 (Persona)**: User profile generation via `persona-generator.ts`. Synthesizes all scene blocks into `persona.md` -- a summary of user preferences, communication style, goals, and recurring task patterns. Triggered every N new memories (default 50).

Key invariant: **Lower layers preserve evidence; upper layers preserve structure.** Every higher-level abstraction maintains backward references to its source material via deterministic file paths and cursors. Debugging follows a chain: Persona -> Scenario -> Atom -> Conversation.

### B. Short-term Symbolic Memory (Context Offload)

The separate `offload/` module addresses in-task token explosion. Tool call logs (search results, code, error traces) are the largest context consumers. The solution:

1. Full tool logs are offloaded to external ref files (`refs/*.md`) in real-time via `after_tool_call` and `after_prompt_build` hooks.
2. A compact Mermaid state graph (with `node_id` annotations) replaces the verbose logs in-context.
3. When the agent needs detail on any node, it greps `node_id` (e.g., `node_0037`) against offloaded storage to retrieve exact context.
4. Three compression tiers: mild (above 50% context window) -> aggressive (above 85%) -> emergency (truncation as last resort).

Benchmarks from the README tell the story:

| Benchmark | Pass Rate Delta | Token Reduction |
|-----------|----------------|----------------|
| WideSearch | +51.52% | -61.38% |
| SWE-bench (50-turn sessions) | +9.93% | -33.09% |
| AA-LCR | +7.95% | -30.98% |
| PersonaMem accuracy | 48% -> 76% (+59%) | -- |

---

## 2. Architecture & Core Modules

**Language/Platform**: TypeScript, Node.js >= 22.16, npm package `@tencentdb-agent-memory/memory-tencentdb`

**Architecture Pattern**: Plugin + HostAdapter -- TdaiCore is the host-neutral facade; OpenClawHostAdapter and StandaloneHostAdapter translate host-specific APIs into abstract interfaces (HostAdapter, LLMRunner, LLMRunnerFactory). This mirrors a hexagonal/ports-and-adapters architecture.

**Entry Point**: `index.ts` (the default export `register()` function, conforming to OpenClaw's plugin API). It:
1. Parses config via `parseConfig()` from `src/config.ts`
2. Creates `OpenClawHostAdapter` wrapping the OpenClaw plugin API
3. Creates `TdaiCore` (the host-neutral core) with the adapter and config
4. Registers hooks: `before_prompt_build` (auto-recall), `agent_end` (auto-capture), `gateway_stop` (shutdown)
5. Registers tools: `tdai_memory_search`, `tdai_conversation_search`
6. Optionally registers the context-offload module

**Core Modules (32,059 lines TypeScript)**:

| Module | Path | Lines | Role |
|--------|------|-------|------|
| Plugin Entry | `index.ts` | 867 | OpenClaw plugin registration, hook wiring |
| Config | `src/config.ts` | 664 | Type-safe config parser, 3-tier validation |
| Core Facade | `src/core/tdai-core.ts` | 535 | Host-neutral memory API (recall/capture/search) |
| Core Types | `src/core/types.ts` | 242 | Abstract interfaces (HostAdapter, LLMRunner) |
| Pipeline Manager | `src/utils/pipeline-manager.ts` | 1174 | L0->L1->L2->L3 scheduler with timers, queues, warm-up |
| Pipeline Factory | `src/utils/pipeline-factory.ts` | 738 | Factory wiring for all pipeline runners |
| Auto-Recall | `src/core/hooks/auto-recall.ts` | -- | Memory retrieval before LLM turn |
| Auto-Capture | `src/core/hooks/auto-capture.ts` | -- | L0 recording after agent turn |
| L1 Extractor | `src/core/record/l1-extractor.ts` | -- | LLM-based memory extraction from conversations |
| L1 Dedup | `src/core/record/l1-dedup.ts` | -- | Vector/keyword dedup for L1 |
| L2 Scene Extractor | `src/core/scene/scene-extractor.ts` | -- | LLM-based scene extraction from L1 records |
| L3 Persona Generator | `src/core/persona/persona-generator.ts` | -- | LLM-based persona synthesis from scenes |
| Prompts | `src/core/prompts/*.ts` | 4 files | LLM prompt templates for L1/L2/L3 |
| SQLite Store | `src/core/store/sqlite.ts` | -- | SQLite + sqlite-vec implementation |
| TCVDB Store | `src/core/store/tcvdb.ts` | -- | Tencent Cloud Vector Database adapter |
| BM25 | `src/core/store/bm25-local.ts` | -- | Local BM25 keyword search |
| Embedding | `src/core/store/embedding.ts` | -- | OpenAI-compatible embedding service |
| Offload Module | `src/offload/` | ~20 files | Context compression with Mermaid canvas |
| Adapters | `src/adapters/` | OpenClaw + Standalone | Host abstraction implementations |
| CLI | `src/cli/index.ts` | -- | Plugin CLI (seed, query, stats) |

**Data Flow (normal turn)**:

```
User sends message
  -> before_prompt_build hook fires
    -> TdaiCore.handleBeforeRecall()
      -> auto-recall: query L1 memories (hybrid BM25+vector)
      -> inject <relevant-memories> into prependContext
      -> inject Persona/Scene Navigation into appendSystemContext
  -> LLM generates response (with optional tool calls)
  -> agent_end hook fires
    -> TdaiCore.handleTurnCommitted()
      -> auto-capture: write L0 JSONL
      -> notify pipeline manager
        -> if threshold reached: schedule L1 extraction
        -> after delay: schedule L2 scene extraction
        -> after L2: trigger L3 persona generation
  -> Next turn repeats
```

**Key Dependencies**: `sqlite-vec` (vector search), `@tencentdb-agent-memory/tcvdb-text` (BM25), `ai`/`@ai-sdk/openai` (LLM calls), `js-tiktoken` (token counting), `zod` (schema validation), `yaml`, `undici`, `@node-rs/jieba` (Chinese tokenizer).

---

## 3. Performance/Benchmarks

All benchmarks measured over **continuous long-horizon sessions** (not isolated turns):

| Metric | OpenClaw (no memory) | With Plugin | Relative Change |
|--------|:---:|:---:|:---:|
| **WideSearch Pass Rate** | 33% | 50% | **+51.52%** |
| **WideSearch Token Usage** | 221.31M | 85.64M | **-61.38%** |
| **SWE-bench Pass Rate** | 58.4% | 64.2% | **+9.93%** |
| **SWE-bench Token Usage** | 3474.1M | 2375.4M | **-33.09%** |
| **AA-LCR Pass Rate** | 44.0% | 47.5% | **+7.95%** |
| **AA-LCR Token Usage** | 112.0M | 77.3M | **-30.98%** |
| **PersonaMem Accuracy** | 48% | 76% | **+59%** |

SWE-bench runs **50 consecutive tasks per session** to simulate real-world context-accumulation pressure.

**Engineered performance details from the offload module**:
- Token counting: fast character-based estimate (~51x faster than tiktoken) for pre-check, falling back to exact tiktoken only when needed
- Aggressive compression: single-pass O(N) cut instead of 6-round iterative full tiktoken (615 messages: 84s -> ~14s)
- Fast incremental skip: 38s -> 122ms for replay scenarios (310x improvement)
- First assemble: 29s -> ~1.4s via fast-token-estimate short-circuit
- Embedding timeouts: separated recall-path (short, user-facing) from capture-path (long, background)

---

## 4. Trade-offs (wins vs loses)

**Wins**:
1. **Massive token savings (30-61%)** without sacrificing task success -- the Mermaid canvas + node_id pattern preserves full traceability while compressing context by orders of magnitude.
2. **White-box debuggability**: Every layer (persona.md, scene blocks, L1 JSONL, L0 JSONL) is plain text files. Recall failures can be traced deterministically through the pyramid chain.
3. **Zero-config startup**: Defaults to local SQLite + sqlite-vec with no external dependencies. Remote embedding is opt-in.
4. **Production engineering**: 3-tier config, graceful degradation when embedding unavailable, retry logic with backoff, session GC to prevent unbounded memory growth, timezone awareness, guarded retention policies (refuses retention < 3 days unless explicitly allowed).
5. **Warm-up scheduling**: New sessions get aggressive early extraction (threshold starts at 1 conversation, doubles each time up to the steady-state N), solving the cold-start problem where early turns carry the most meaningful context.

**Loses / Complexity**:
1. **LLM dependency for extraction**: L1, L2, and L3 all require LLM calls. This means latency, cost, and the risk of LLM errors propagating through the memory pyramid. The CHANGELOG documents several real bugs from LLM-generated filenames with spaces breaking scene navigation, LLM failures half-writing scene_blocks, etc.
2. **Prompt language sensitivity**: L1/L2/L3 prompts must adapt to the user's language -- the system recently added automatic detection, but any prompt-template inconsistency can degrade extraction quality.
3. **Operational complexity**: The offload module has a complex state machine with L1/L1.5/L2/L4 pipelines, multiple timer types, and backend vs local modes. The CHANGELOG reveals hard-won stability fixes: L2 cold-start skip racing with minInterval, L1.5 settle never returning causing L2 deadlock, offload-token counting precision issues.
4. **Host coupling**: The plugin is deeply coupled to OpenClaw's hook system. The Hermes/Gateway path requires a separate Docker deployment with a Gateway HTTP sidecar, adding operational overhead vs the OpenClaw in-process path.
5. **Two separate systems**: Long-term memory and short-term context offload are architecturally separate (separate module, separate config, separate hooks), yet they interact. The code has guards to prevent offload MMD canvases from being captured as L0 memories, but the complexity of two memory systems running side-by-side is non-trivial.

**Known Limitations (from CHANGELOG)**:
- Version compatibility with OpenClaw hook policies (multiple CHANGELOG entries about `allowConversationAccess` gatekeeping)
- Local embedding provider is deliberately removed from user-facing config (only remote embedding is supported)
- TCP port conflict detection and gateway watchdog for Hermes deployments
- Concurrency race conditions in scheduler startup (fixed via promise-gate pattern in tdai-core.ts, line 86-108)
- Scene filename sanitization required after LLM-generated names with spaces broke Markdown references

---

## 5. Design Rationale

The system makes several deliberate architectural choices:

**Reject flat vector storage**: Traditional memory systems dump everything into a vector DB and rely on KNN search for recall. The Tencent team argues this lacks macro-level guidance -- a query for "database schema" returns fragmented fragments, not structured knowledge. Their layered pyramid provides progressive disclosure: the persona layer carries daily preferences, the scene layer provides context, and the atom layer supplies precise facts. The agent only drills down as needed.

**Symbolic compression over brute-force truncation**: Rather than using a fixed context window and dropping old messages, the system compresses tool histories into Mermaid symbol graphs. This is lossy in token count but lossless in semantic traceability -- every Mermaid node_id maps back to the full raw text on disk. The LLM can navigate the graph like a map rather than reading a transcript.

**Progressive extraction scheduling**: The pipeline doesn't extract after every turn. Instead it uses a warm-up schedule (exponential backoff of threshold), an idle timeout (extract when user stops talking), and L2/L3 timers that run on their own schedules. This avoids wasting LLM calls on trivial exchanges while ensuring extraction eventually catches up.

**Host-neutral core**: TdaiCore depends only on abstract interfaces (HostAdapter, LLMRunner). This allowed the team to support both OpenClaw (in-process) and Hermes/Gateway (HTTP sidecar) from the same codebase. The StandaloneHostAdapter + StandaloneLLMRunner can work with any OpenAI-compatible API, not just Hermes.

**Graceful degradation everywhere**: Every external dependency (embedding service, vector store, LLM) can fail without crashing the agent. Config errors disable specific features with logged warnings rather than throwing. L1 falls back from SQLite to JSONL reading. Recall degrades from hybrid to keyword-only when embeddings time out.

**Data completeness over speed**: L0 layers always write JSONL before returning (synchronous path), while embedding writes are deferred to a background task. This ensures conversation data is never lost even if embedding calls time out. The `before_message_write` hook strips recall artifacts from persisted user messages to prevent polluting the historical transcript.

---

## 6. Transfer to Lyra

**One concrete idea**: Adopt the **Mermaid Canvas + node_id Tracing** pattern (from the `offload/` module) as Lyra's primary context management strategy. Instead of linearly truncating the context window when it fills, Lyra should:

1. Offload verbose tool call logs (directory listings, git diffs, test output, API responses) to external files with a predictable naming scheme (`refs/<turn_N>_<tool_name>.md`).
2. Maintain a lightweight Mermaid state graph in-context that summarizes the task's progression, with each node carrying a `node_id`.
3. Keep the Mermaid graph within a fixed token budget (~20% of context window). When the budget is exceeded, trigger compression (summarize stale branches into higher-level nodes).
4. Implement `node_id` retrieval: when the LLM references a `node_id`, the runtime fetches the full context from disk.

**Route**: This maps directly to **Section 4.x -- Context & Memory Management** in Lyra's upgrade plan. Specifically:
- The offload mechanism is a 4.x feature (short-term context optimization).
- The layered memory pyramid (L0->L3) maps to Lyra's long-term memory/persona system (4.x or 5.x).
- The `node_id` hyperlinking between compressed and raw artifacts is a pattern transferable to Lyra's artifact storage layer.

**Why it fits**: Lyra currently suffers from context window bloat in long coding sessions -- agent tool calls (git, npm, test runners, linters) produce verbose outputs that accumulate and push out relevant conversation history. The Mermaid canvas pattern is lightweight enough to implement incrementally (start with tool log offloading, add Mermaid graphing later) and directly addresses the "I can't remember what we were doing" failure mode in extended Lyra sessions.

**Impact**: High (8/10). This directly addresses Lyra's most painful user-facing problem: context loss in long sessions. The benchmark data shows 30-61% token reduction with *improved* task success rates, which is a rare win-win.

**Effort**: Medium (5/10). Implementing tool log offloading and node_id lookup is a well-scoped engineering task (~1-2 weeks for a prototypes). The Mermaid graph generation and compression tiers require more design work. However, the basic pattern (write to refs, keep summary in context) can be prototyped quickly.

**Tier**: Tier 1 (foundational). Context management is a prerequisite for every other Lyra improvement. Without a scalable memory strategy, longer agent runs degrade in quality regardless of other improvements.

**License**: MIT. Compatible with any Lyra license. Can reference patterns and borrow implementation ideas without restriction. Full copyright notice: "Copyright (C) 2026 Tencent. All rights reserved."
