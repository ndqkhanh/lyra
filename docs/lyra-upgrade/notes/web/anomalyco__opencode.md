# anomalyco/opencode -- Deep-Read

## 1. Headline Feature & Mechanism

OpenCode is a **fully open-source AI coding agent** running in the terminal (TUI or CLI). It is functionally a Claude Code competitor -- an LLM-powered assistant that reads your codebase, runs shell commands, edits files, and maintains multi-turn conversational sessions -- but is built entirely in TypeScript on Bun and licensed MIT.

**How it works at runtime:**

1. A CLI entry point (`packages/opencode/src/index.ts`) dispatches to subcommands via yargs. The main loop lives in the `run` command, which boots a session runtime.
2. A **Session** (V2) is the central durable unit: it admits user prompts as `SessionInput`, assembles a **System Context** from typed **Context Sources**, resolves a model from the **Catalog** + **SessionRunnerModel**, and initiates one provider turn per `llm.stream(request)` call.
3. Each provider turn streams LLM events (text deltas, reasoning, tool calls) via the `@opencode-ai/llm` package, which has native and AI-SDK-backed adapters for 10+ providers (OpenAI, Anthropic, Google, xAI, Amazon Bedrock, Azure, GitHub Copilot, OpenRouter, etc.).
4. Tool calls are dispatched through a **ToolRegistry** with permission checks: built-in tools (bash, read, write, edit, grep, glob, webfetch, websearch, skill, question), MCP tools, and plugin-contributed tools all flow through the same authorization layer.
5. The session loop continues: tool results settle, the projector persists events, context changes are sampled at safe provider-turn boundaries, and the next turn begins -- bounded at 25 model steps (`MAX_STEPS = 25`).
6. Compaction prunes oversized history (protecting recent 40K tokens, pruning everything before the last 20K tokens) and starts a new **Context Epoch** with a fresh baseline system context.

## 2. Architecture & Core Modules

**Monorepo structure** (22 packages under `packages/`):

| Package | Role |
|---------|------|
| `opencode` | Main entry point: CLI, config, TUI, session V1, provider config, MCP, agent config, permissions |
| `core` | V2 session runtime: event sourcing, session store/runner/projector, system context, tool registry, agent V2, catalog, location, database |
| `llm` | LLM abstraction: provider protocols (Anthropic Messages, OpenAI Chat/Responses), routing, caching, tool schemas |
| `app` / `web` | Web frontends (Solid.js) |
| `desktop` | Desktop app (Electron) |
| `console` | Admin console UI |
| `sdk` / `server` | HTTP API server and JS SDK |
| `plugin` / `script` | Plugin system and scripting |
| `ui` | Reusable UI components (Solid.js) |
| `function` | Cloud functions (SST) |
| `enterprise` / `stats` / `slack` | Enterprise and analytics surfaces |

**Entry point data flow:**

```
opencode CLI (yargs)
  -> run command
    -> createOpencodeClient (SDK)
    -> session.prompt()
      -> SessionV2.prompt()  [admits durable session_input row]
        -> SessionExecution.wake()  [schedules drain]
          -> SessionRunner.run()  [drains eligible work]
            -> SessionRunnerModel.resolve()  [catalog -> LLM model]
            -> SystemContext.initialize()  [baseline context]
            -> llm.stream(request)  [one provider turn]
              -> ToolRegistry.execute()  [settle tool calls]
            -> reload history + next turn
```

**Architecture pattern:** Event-sourced, functional-effect system using **Effect-TS** (Schema, Layer, Service, Context, Stream, Effect) throughout. The V2 Session runtime is a clean CQRS-style design where:
- **EventV2** provides durable event sourcing with aggregates, projectors, and a sync layer
- **SessionStore** reads projected session state
- **SessionProjector** writes from event streams
- **SessionRunnerModel** resolves model/provider from the Catalog
- **ToolRegistry** is a permission-gated plugin point for tool definitions
- **System Context** is the structured assembly of typed `ContextSource` values separated from session history

**Key design documents:**
- `AGENTS.md` -- 273 lines of architecture invariants and design axioms
- `CONTEXT.md` -- glossary of 125 domain terms (System Context, Context Epoch, Safe Provider-Turn Boundary, Context Snapshot, etc.)
- `perf/test-suite.md` -- systematic test suite optimization with hypothesis-driven development

## 3. Performance/Benchmarks

The repo contains extensive **test suite performance benchmarks** (`perf/test-suite.md`) rather than coding-task benchmarks (no SWE-bench scores published):

- **Full test suite** (`bun run bench:test` from `packages/opencode`):
  - Baseline: ~225 seconds
  - After optimization: ~187 seconds (best recorded)
  - After restoring test coverage: ~202 seconds

- **Specific slow-file profiling** (historical, before optimizations):
  | File | Seconds |
  |------|--------:|
  | `test/config/config.test.ts` | 23.546 |
  | `test/provider/provider.test.ts` | 18.747 |
  | `test/control-plane/workspace.test.ts` | 16.447 |
  | `test/plugin/install-concurrency.test.ts` | 14.804 |
  | `test/server/httpapi-cors.test.ts` | 14.620 |

- **Optimizations saved 20-40+ seconds** through systematic hypothesis-driven improvements:
  - Removing unnecessary git repo creation in test fixtures (5-10s savings per targeted area)
  - Reducing timeout values from production defaults (5000ms -> 25ms) in timeout-specific tests
  - Cutting worker counts in concurrency tests
  - Switching from `tmpdir` + manual plumbing to `it.instance` Effect-aware fixtures
  - Each hypothesis is measured with median-of-3 targeted runs before/after

**Adoption benchmarks** from `STATS.md`:
- GitHub downloads: 7.8M+ (as of Jan 2026)
- npm downloads: 2.3M+ (as of Jan 2026)
- Total: 10M+ combined downloads
- Growth: from 58K total in June 2025 to 10M+ by Jan 2026 (~170x in 7 months)
- Record single-day growth: +661K (Jan 16, 2026)

## 4. Trade-offs

**Wins:**
- Fully open-source (MIT) -- no vendor lock-in, self-hostable
- Multi-provider from day one: 10+ LLM providers via the `@opencode-ai/llm` abstraction layer
- Effect-TS provides strong type safety and functional error handling across the entire codebase
- V2 Session architecture is a significant clean-sheet redesign: event-sourced, durable, with explicit System Context/Context Epoch separation from conversation history
- Rich tool system: built-in tools (bash, read, write, edit, grep, glob, webfetch, websearch), plus MCP tools and plugin-contributed tools all gated through unified permission model
- Desktop, web console, and CLI surfaces from one codebase
- TUI built on OpenTUI/Solid.js (not raw ncurses) -- accessible via ssh/remote
- Rapid adoption: 10M+ downloads in 7 months
- V2 Runner design doc (CONTEXT.md) shows deep architectural rigor around data consistency

**Loses / Risks:**
- Massive codebase: ~3,000 source files, extremely high complexity for a single developer to fully understand
- Effect-TS dependency is heavy: the Effect ecosystem (`effect`, `@effect/platform-node`, `@effect/sql-sqlite-bun`, `@effect/opentelemetry`) is a deep commitment -- hard to hire for, hard to onboard
- V1/V2 duality: the codebase simultaneously maintains V1 (`packages/opencode/src/session/`) and V2 (`packages/core/src/session/`) session architectures, which creates ambiguity about which code path is active
- The V2 runner has many `TODO` and `[ ]` checklist items in comments -- it is clearly still under construction, not production-ready for all V1 replacement use cases
- V2 uses specific runtime dependencies: `Bun` (`Bun.file()`, `Bun.spawn`), SQLite (Drizzle), SST for cloud infra -- not portable to Node.js or Deno without significant work
- Agent configuration via markdown files in `.opencode/agent/*.md` is clever but adds another DSL to learn
- Limited benchmarking evidence for coding task performance (no SWE-bench, no HumanEval); benchmark docs focus entirely on test suite wall-clock speed

## 5. Design Rationale

The codebase reveals clear architectural principles, especially visible in the V2 Session design documented in `CONTEXT.md` and `AGENTS.md`:

1. **Separate conversation from context.** The single most important design decision: durable conversation history (Session Messages, SessionInput) is completely separated from runtime context assembly (System Context, Context Sources, Context Epochs). This means the model's system prompt is never "live" -- it is a durable snapshot that changes only at safe boundaries, avoiding drift and enabling deterministic retry.

2. **Context Sources are typed, independent, and composable.** Each source has a stable key, a JSON codec, a loader, and pure renderers for baseline/update/removal. This is a world apart from the "append to system prompt" approach -- it enables reliable diffing, removal, and re-initialization.

3. **Events are the single source of truth.** V2 is built on explicit `EventV2` definitions with typed payloads, aggregate sequences, and projectors. The session projector reads from events; the store reads from projected tables. This is classic event sourcing but applied to an agent runtime, which is unusual and compelling.

4. **Functional effects everywhere.** The team committed to Effect-TS for all effects, dependency injection, error handling, and concurrency. Every service is a `Context.Service`, every layer is composed with `Layer.effect`, every error is a typed `Schema.TaggedErrorClass`. This eliminates entire categories of bugs (unhandled promises, forgotten error branches, implicit dependencies) but at the cost of a steep learning curve.

5. **Plugins as first-class agents.** Both V1 and V2 have explicit plugin systems that can contribute tools, providers, models, context sources, and agents. The agent system itself supports an agent-registry pattern where agents are configured via markdown files with YAML frontmatter.

6. **Permission model is layered.** Every tool execution goes through a permission check against a `Ruleset` that can be defined at the agent level, session level, or project level. The permission system is not an afterthought -- it is baked into `ToolRegistry.Entry.authorize()`.

Key design documents discovered:
- `packages/core/src/session/runner/llm.ts` -- the V2 runner's orchestrator, with explicit `[x]` and `[ ]` checkboxes documenting completion status of its internal sub-features (20 items, ~12 checked)
- `AGENTS.md` at repo root -- 273 lines of coding conventions and V2 architecture invariants
- `CONTEXT.md` -- structured domain glossary with "Avoid:" terms distinguishing OpenCode's vocabulary from common but imprecise alternatives

## 6. Transfer to Lyra

**One transferable idea: System Context Registry with typed Context Sources.**

OpenCode's cleanest architectural contribution is how it separates runtime context from conversation history. Instead of building a system prompt by concatenating fragments (which is what Lyra's brainstorming docs seem to describe), OpenCode models each contextual fact as a **typed Context Source** with four operations: load, baseline-render, update-render, removal-render. These sources are composed lazily at safe provider-turn boundaries, diffed against a stored snapshot, and emitted as durable mid-conversation system messages only when a source actually changes.

For Lyra, this means:
- **No more "live system prompt" drift.** The system prompt is a durable snapshot from a Context Epoch, not a dynamically recomputed string.
- **Deterministic retry.** Because context changes are only admitted at safe boundaries, replaying the same inputs produces the same LLM call.
- **Plugin-contributed context.** Just as OpenCode plugins contribute Context Sources, Lyra plugins could contribute dynamically observed state (current time, workspace files, git status, LSP diagnostics) without each one needing to "append to system prompt."
- **Compaction reinitializes context.** When history grows too long, compaction starts a new Context Epoch with a fresh baseline -- preserving the invariant that the system prompt matches the current environment.

**Workstream route:** Lyra upgrade SS 4.5 (Session System / Context Management) -- this directly maps to the session system redesign Lyra already has planned. The Context Source pattern is a concrete implementation strategy for the "modular system prompt" concept.

**Impact:** 8/10. This is not a tool or a benchmark -- it is an architectural pattern that solves a fundamental problem in agent session management (system prompt staleness, context drift, non-deterministic retry). Adopting this pattern would improve reliability and debuggability across all Lyra agent interactions.

**Effort:** 7/10. Implementing the full System Context Registry with typed sources, codec-based serialization, diff-based update detection, and epoch lifecycle management is a significant engineering investment. However, it can be adopted incrementally: start with one or two Context Sources (current datetime, workspace summary), then add more.

**Tier:** Strategic. This is an architectural pattern that affects the core session loop, not a bolt-on optimization.

**Route:** SS 4.5 (Session System). Section 4.5 of the Lyra upgrade plan covers the session system redesign. The Context Source pattern lives entirely within the session runtime.

**License:** MIT -- no restrictions on adopting the pattern in Lyra.
