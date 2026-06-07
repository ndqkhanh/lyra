# sst__opencode (github.com/anomalyco/opencode) -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** OpenCode is the open-source AI coding agent -- a full-featured terminal agent comparable to Claude Code, Cursor terminal mode, or GitHub Copilot CLI, but fully open source (MIT).

**How the Code Really Works:**

The core loop is an **event-sourced, Effect-TS-powered session runner** that assembles a "System Context" from independently refreshable typed sources, dispatches an LLM provider turn with tool definitions, persists every event durably (SQLite), and loops until no pending steer/queue input remains.

The critical inner mechanism -- and OpenCode's most novel contribution -- is the **System Context** abstraction (`packages/core/src/system-context/index.ts`). Instead of appending diffs to a monolithic system prompt, OpenCode models system context as typed `Source<A>` values:

- Each source has a stable namespaced `key`, a `codec` (JSON Schema for durable comparison), an effectful `load` (returns the value or `Unavailable`), a pure `baseline` renderer, a pure `update` (prev, curr) renderer, and an optional `removed` renderer.
- Sources are composed via `SystemContext.combine(...)` which asserts unique keys and packs them into an opaque carrier.
- The `SystemContextRegistry` collects all built-in, plugin, and instruction sources. At a **Safe Provider-Turn Boundary**, the registry evaluates all sources concurrently, compares against the durable **Context Snapshot**, and emits targeted **Mid-Conversation System Messages** only for changed sources.
- This replaces the raw text-diff approach with structured, codec-verified change detection.

The **Session Runner** (`packages/core/src/session/runner/llm.ts`) orchestrates the full loop:

1. Load session from durable store (SQLite via Drizzle + Effect)
2. Select agent, resolve model from the catalog
3. Initialize or reconcile a **Context Epoch** (the span during which one baselined system context remains immutable)
4. Load projected history, translate V2 session messages to `@opencode-ai/llm` format
5. Stream one LLM provider turn via `llm.stream(request)`
6. For each non-provider-executed tool call: settle it through `ToolRegistry` (authorize, execute, bound oversized output, persist)
7. Continue the loop if there is pending steer/queue input or tool results to replay
8. Max 25 steps per drain cycle; overflow triggers compaction

The **Run Coordinator** (`packages/core/src/session/run-coordinator.ts`) ensures exactly one drain chain per session at a time: idle wakes coalesce, explicit runs dominate, and interrupts pause the current chain.

## 2. Architecture & Core Modules

**Monorepo topology (Bun workspaces + Turborepo):**

```
packages/
  opencode/        -- CLI entry point (yargs), commands, TUI, installation
  core/            -- Core engine: sessions, tools, agents, plugins, config
  cli/             -- Minimal CLI binary wrapper
  llm/             -- LLM abstraction layer (protocol adapters, model routing)
  plugin/          -- Plugin definition and permission system
  server/          -- HTTP API server (Hono + Effect)
  sdk/             -- TypeScript SDK for embedding OpenCode
  ui/              -- UI primitives shared across desktop/web/console
  app/             -- Web application (SolidJS)
  desktop/         -- Electron desktop wrapper
  console/         -- SST Console (infrastructure management)
  web/             -- Landing/marketing website
  docs/            -- Documentation site
  identity/        -- Auth system (OpenAuth)
  enterprise/      -- Enterprise features
  stats/           -- Download/usage statistics
  effect-drizzle-sqlite/  -- Effect-TS integration for Drizzle + SQLite
  effect-sqlite-node/     -- Lower-level Effect SQLite bindings
  slack/           -- Slack integration
  script/          -- Shared build/utility scripts
  function/        -- Serverless functions
  containers/      -- Docker/container definitions
  http-recorder/   -- HTTP interaction recorder for testing
  storybook/       -- Component storybook
```

**Entry Point:** `packages/opencode/src/index.ts` uses `yargs` to parse CLI commands (`run`, `generate`, `serve`, `debug`, `stats`, `export`, `import`, `github`, `mcp`, `acp`, `session`, `plugin`, `db`, etc.). This is a thin CLI shell that loads the Effect-TS layer stack and dispatches commands.

**Architecture Pattern:** **Event-driven / Event-sourcing with Effect-TS functional effects.** Key patterns:
- **Layer composition** -- Every service is an Effect-TS `Layer` (dependency injection + initialization)
- **Service + Context tags** -- Typed service interfaces via `Context.Service` tags
- **Durable event sourcing** -- All session mutations (AgentSwitched, ModelSwitched, Prompted, Step.Started, Tool.Called, etc.) are events persisted to SQLite via Drizzle
- **Projectors** -- Session info rows are projected from the event stream
- **State transforms** -- Mutable in-memory state managed via `immer`-backed `State.transform(...)` with scoped contributions (plugins attach tools through scoped transforms that auto-cleanup when the scope closes)
- **Concurrency via FiberSet + Deferred** -- The run coordinator uses Effect `FiberSet` and `Deferred` for single-threaded-per-session orchestration with interrupt support

**Core Modules:**

| Module | File | Size | Responsibility |
|--------|------|------|----------------|
| System Context | `core/src/system-context/index.ts` | 317 lines | Typed, composable, refreshable context sources with codec-verified change detection |
| System Context Registry | `core/src/system-context/registry.ts` | ~ | Scoped registry of context producers |
| Session Runner (LLM) | `core/src/session/runner/llm.ts` | 396 lines | Full provider-turn orchestration loop |
| Session Runner Model | `core/src/session/runner/model.ts` | 148 lines | Model resolution from catalog (Anthropic/OpenAI/OpenAI-compatible) |
| Run Coordinator | `core/src/session/run-coordinator.ts` | 288 lines | Single-threaded drain-loop with coalesced wake-ups |
| Tool Registry | `core/src/tool/registry.ts` | 251 lines | Location-scoped tool contribution, effective lookup, validation, and execution |
| Tool AGENTS.md | `core/src/tool/AGENTS.md` | 139 lines | Architecture spec for tool lifecycle |
| Core Tools | `core/src/tool/{read,bash,edit,grep,webfetch,websearch,...}.ts` | Various | Built-in tools (read, bash, edit, grep, web fetch/search, skill, patch, etc.) |
| Agent System | `core/src/agent.ts` | 143 lines | Multi-agent state machine |
| Event System | `core/src/event.ts` | 268 lines | Durable event-sourcing infrastructure |
| Session | `core/src/session.ts` | 447 lines | Session CRUD, prompt admission, model switching |
| Plugin Boot | `core/src/plugin/boot.ts` | ~ | Plugin loading and lifecycle |
| Permission | `core/src/permission.ts` | ~ | Permission-based tool authorization |
| Catalog | `core/src/catalog.ts` | ~ | Provider/model catalog management |
| Config | `core/src/config.ts` | ~ | Configuration loading |

**Data Flow (one provider turn):**

```
User prompt --[Event: Prompted]--> SQLite --[Event: Admitted]--> RunCoordinator.run()
  --> SessionRunner.runTurn()
    --> AgentV2.select() + SystemContextRegistry.load() + SkillGuidance.load()
    --> SystemContext.combine() --> ContextEpoch.initialize() or .prepare()
    --> SessionHistory.entriesForRunner() --> translate to LLM messages
    --> ToolRegistry.definitions(agent.permissions)
    --> llm.stream(request) --> persist events as they stream (Step.Started, Text.Delta, Tool.Called...)
    --> for each non-provider-executed tool: ToolRegistry.settle()
    --> continue loop if pending steer/queue input
```

## 3. Performance/Benchmarks

OpenCode ships a detailed performance regression test suite (`perf/test-suite.md`) with the following real metrics:

**Full Test Suite:**
- Baseline before optimization: ~225 seconds
- After optimization: ~186 seconds
- After restoring coverage: ~202 seconds

**Individual Test File Performance (before optimization):**
| Test File | Time | Bottleneck |
|-----------|------|-----------|
| `test/control-plane/workspace.test.ts` | 12.9s | Git repo initialization |
| `test/server/httpapi-listen.test.ts` | 10.5s | WebSocket/listener lifecycle |
| `test/config/config.test.ts` | 10.3s | Large serial file |
| `test/plugin/install-concurrency.test.ts` | 7.8s | Many subprocesses |
| `test/provider/provider.test.ts` | 7.5s | Large serial file |

**Optimization wins (before -> after for specific transformations):**
- Removed `git: true` from non-git tests: 10.6s -> 7.8s (httpapi-listen)
- Removed 1000ms fixed sleep: 10.3s -> 9.4s (config)
- Added `withProject` default no-git: 8.0s -> 5.2s (SDK helpers)
- `it.instance` pattern for config tests: 23.5s -> ~2s (config)
- No-server runner for non-LLM tests: 25.4s -> 21.0s (prompt tests)
- Marked subprocess tests concurrent: 11.9s -> 4.1s (run-process)

**Adoption Metrics (from `STATS.md`):**
- ~2.5M+ GitHub downloads as of Jan 2026
- ~2.3M+ npm downloads as of Jan 2026
- Peak daily growth: ~300K+ combined downloads (Jan 2026)
- Rapid acceleration from ~500K total in Sep 2025 to ~10M+ total in Jan 2026

## 4. Trade-offs

### Wins
- **True open source (MIT)** -- No proprietary agent lock-in; full transparency of agent behavior, context assembly, and tool execution
- **Multi-provider** -- Supports Anthropic, OpenAI, Google, xAI, Groq, Mistral, Together, DeepInfra, Azure, Bedrock, Cerebras, Perplexity, Cohere, OpenRouter, Alibaba, Venice, GitLab, and OpenAI-compatible providers
- **Plugin system** -- Hot-reloadable npm-package plugins with permission scoping
- **Event-sourced durability** -- Every operation is an event; sessions survive process restarts
- **System Context abstraction** -- Structured, typed, composable context sources (not raw prompt text manipulation)
- **Rich ecosystem** -- Web app, desktop app (Electron), Slack integration, SDK, console, stats, LSP protocol support
- **Stringent test discipline** -- Detailed performance regression tracking, hypothesis-driven optimization
- **Internationalization** -- README in 20+ languages

### Loses/Cons
- **Effect-TS complexity** -- The entire codebase uses Effect-TS heavily (Layer, Effect, Schema, Stream, FiberSet, Deferred, etc.). This is a significant learning curve. The `Context.Service`, `TaggedError`, `Layer.provide`, and `Effect.gen` patterns are pervasive. Developers unfamiliar with Effect-TS will struggle to contribute.
- **SQLite-only persistence** -- No clustered/HA mode. Session ownership is process-local. Distributed sessions are listed as a future TODO.
- **Many V2 session operations are still `OperationUnavailableError`** -- shell, skill, switchAgent, compact, and wait are all stubs that return errors. The V2 session rewrite is incomplete.
- **Single-threaded per-session** -- The run coordinator guarantees exactly one drain chain per session. Though multiple sessions can run concurrently, one session is always serial (no parallel provider turns per session).
- **Bun-specific** -- Package manager is Bun. Build scripts assume Bun. Some runtime code uses `#imports` with `bun`/`node` conditions. The `node-pty` fix script is Bun-specific. Porting to pure Node.js would be non-trivial.
- **Young project** -- Still in 1.x. Some APIs are evolving rapidly. The V1 -> V2 migration is ongoing (there is a `v1/` directory with legacy session code).
- **Massive dependency surface** -- 100+ direct dependencies in the main package alone, including 15+ AI provider SDKs, 3+ PTY implementations, WebAssembly tree-sitter binaries, etc. Bundle size is large.
- **Limited session management** -- Sessions are identified by flat IDs with no hierarchical organization. No built-in session versioning or branching.

## 5. Design Rationale

The architectural choices in OpenCode reveal a clear philosophy:

**Why Effect-TS?** The project treats correctness and determinism as first-class properties. Effect-TS provides algebraic effects for error handling, structured concurrency (FiberSet, Deferred), dependency injection (Layer, Context), and schema-based validation (Schema, Codec). This allows the runtime to reason about failures, interruptions, and resource cleanup without try/catch spaghetti.

**Why event sourcing?** Sessions must survive crashes, restarts, and process migrations. Recording every mutation as a durable event means the full session history can be replayed, projected into read-optimized views, and audited. The Context Snapshot system leverages this: every system context update is tied to a durable event, so context is never lost on restart.

**Why composable System Context instead of a monolithic system prompt?** The CONTEXT.md document explicitly names the design: "One independently observed typed value within the System Context, represented by a stable key, JSON codec, infallible loader, pure baseline/update renderers." This mirrors the architectural principle of "separation of concerns" at the prompt level. Each source (date, environment, instructions, skills) independently loads and renders. When a source changes, only its update message is emitted. This is far more maintainable than appending raw text diffs.

**Why "stale-while-revalidate" for unavailable context?** Context Epoch initialization is blocked if any source returns Unavailable; the session does not start with incomplete context. But during an epoch, Unavailable sources silently retain their last admitted value. This prevents transient load failures from corrupting the active context.

**Why "uninterruptibleMask" around tool settlement?** Tools execute irreversible side effects (file writes, bash commands). The settlement region must complete even if the LLM stream is interrupted. OpenCode uses `Effect.uninterruptibleMask` to make the tool execution + persistence region atomic from an interruption perspective.

**Why three layers of tool storage (registry, application-tools, native)?** This reflects the layered architecture: plugins contribute at the process level, Location-scoped built-ins at the Location level, and the Tool Registry performs final resolution. The AGENTS.md tool architecture doc explicitly warns: "Do not make ToolRegistry process-global. Do not move Location resources into ApplicationTools."

**Why per-session single-threaded drain?** The run coordinator design is explicit: "one Session's process-local execution lane: one active demand and at most one coalesced follow-up." This avoids the complexity of distributed session ownership and makes the concurrency model easy to reason about. Distributed coordination is deferred to a future "durable multi-node ownership" use case.

## 6. Transfer to Lyra

**Transferable Idea: Typed, Composable System Context Sources**

OpenCode's `SystemContext` abstraction is directly applicable to Lyra's agent context management problem. Lyra currently assembles a monolithic system prompt via concatenation. OpenCode demonstrates a better approach: model each context dimension (workspace environment, git state, current date, project instructions, tool permissions, skill definitions, user preferences) as an independent typed source with a stable key, JSON codec for comparison, and pure baseline/update/removal renderers.

The mechanism works as follows in OpenCode:
1. Each source is a `Source<A>` with a `key`, `codec` (for durable comparison), `load` (effectful fetch), `baseline` renderer, and `update(prev, curr)` renderer
2. Sources compose via `combine([...])` with duplicate key detection
3. At the provider-turn boundary, all sources are loaded concurrently
4. Each loaded value is compared against the durable Context Snapshot using the codec
5. Only changed sources emit a **Mid-Conversation System Message** -- a targeted instruction update, not a full prompt replacement
6. Unchanged sources remain silent (preserving provider cache prefix)

For Lyra, adapting this design would provide:
- **Deterministic change detection** -- No more asking "did this part of the prompt change?"; codec comparison answers precisely
- **Targeted updates** -- When the git branch changes, only the git context source emits an update message; the workspace and instruction sources are untouched
- **Provider cache preservation** -- Because the baseline system context only changes on Epoch transitions (compaction), the unchanged prefix remains valid for prompt caching
- **Durable snapshots** -- Context is never lost on process restart; the snapshot is stored and compared on reload
- **Plugin/extension context** -- External plugins can contribute their own context sources without modifying the core prompt assembly code

**Workstream Route:** This maps to **section 4.x (Architecture and System Design)** -- specifically a sub-section on "Context Assembly and Epoch Management." It touches on:
- 4.1: Core architecture (System Context Registry)
- 4.2: Session management (Context Epoch lifecycle)
- 4.3: Reliability (durable snapshots, stale-while-revalidate)

**Impact:** 8/10 -- High. This directly addresses Lyra's context staleness problem and would enable more predictable agent behavior with less wasted context window space.

**Effort:** 7/10 -- Significant. The approach requires:
- Defining typed context sources with codecs and renderers
- Building or adapting a durable snapshot store
- Integrating the Context Epoch lifecycle into the session runner
- Testing the comparison/reconciliation logic edge cases

**Tier:** Tier 2 (Major Enhancement) -- This is a meaningful architectural improvement that changes how the session runner manages context, but it is backward-compatible at the outer API level.

**License:** MIT -- Compatible with any Lyra license. Full freedom to copy, adapt, and incorporate the System Context design.

**File reference:** The primary reference implementation is `packages/core/src/system-context/index.ts` (317 lines). The registry that collects and evaluates sources is at `packages/core/src/system-context/registry.ts`. The Context Epoch lifecycle is in `packages/core/src/session/context-epoch.ts`. The built-in context sources (date, environment, instructions) are at `packages/core/src/system-context/builtins.ts`. The entire design spec is documented in `CONTEXT.md` (the project's domain-language document defining every term and relationship).
