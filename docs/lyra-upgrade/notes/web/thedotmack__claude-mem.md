# thedotmack/claude-mem -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Repo**: github.com/thedotmack/claude-mem | **Version**: 13.4.0 | **Stars**: very high (Trendshift badge, "Mentioned in Awesome Claude Code")

**Headline**: Claude-Mem is a persistent memory compression system purpose-built for Claude Code. It automatically captures tool-usage observations across sessions, compresses them via the Claude Agent SDK (a secondary "observer" Claude instance), stores them in SQLite with Chroma vector embeddings for hybrid search, and injects a compressed context string into every future session. No manual save/load commands required.

**The mechanism in four steps:**

1. **Capture**: Claude Code's plugin hooks (Setup, SessionStart, UserPromptSubmit, PostToolUse, Stop) fire shell commands that contact a background Worker Service (HTTP API on port 37777 managed by Bun). PostToolUse forwards tool-usage data (files read, files modified, user prompt, assistant output) to the worker via stdin JSON.

2. **Compress**: The worker spawns a secondary Claude Code process (the "observer" using the Agent SDK) with a structured XML prompt. The observer reads the tool-usage transcript and emits XML-format observations (`<observation><type>...</type><title>...</title><facts>...</facts><concepts>...</concepts></observation>`). At session end, a `<summary>` block is generated with `investigated`, `learned`, `completed`, `next_steps` fields. This is an LLM-to-LLM compression pipeline -- the observer Claude compresses what the primary Claude did into dense structured memory.

3. **Store**: Parsed observations and summaries are written to a local SQLite database (`~/.claude-mem/claude-mem.db`) with FTS5 full-text search indexes. Observations are also synced to a local Chroma vector database (`~/.claude-mem/chroma/`) for semantic search.

4. **Retrieve**: On next SessionStart, the ContextBuilder queries SQLite for observations matching the current project's concepts/types, builds a progressive-disclosure context string, and injects it as a system reminder. The context shows token economics (e.g., "38 observations, 2.6K read tokens, discovery cost 133.8K, saved 131.2K tokens - 98% compression"). Users can also query memory via 3-layer MCP search tools (search -> timeline -> get_observations, ~10x token savings by filtering before fetching full details).

**Key files**:
- `src/services/worker-service.ts` -- Main entry point for the background worker (daemon, HTTP server, initialization)
- `src/services/worker/ClaudeProvider.ts` -- Observer Claude integration using Agent SDK (`@anthropic-ai/claude-agent-sdk`)
- `src/services/context/ObservationCompiler.ts` -- SQLite queries for building context payload
- `src/services/context/ContextBuilder.ts` -- Context string assembly (progressive disclosure)
- `src/sdk/parser.ts` -- XML parsing of observation/summary output from observer Claude
- `src/services/worker/SearchManager.ts` -- Orchestrates hybrid search (Chroma + SQLite FTS5)
- `src/services/worker/search/SearchOrchestrator.ts` -- Multi-strategy search: Chroma, SQLite, Hybrid, with fallback
- `src/services/sync/ChromaSync.ts` -- Vector embedding sync to Chroma
- `plugin/hooks/hooks.json` -- Lifecycle hook definitions (Setup, SessionStart, UserPromptSubmit, PostToolUse, Stop)
- `src/storage/sqlite/schema.ts` -- SQLite schema with FTS5, triggers, indexes (schema version 33)

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Language**: TypeScript (ES2022, ESNext modules)
**Runtime**: Node.js >=20 + Bun (for worker process management)
**Package**: `claude-mem` on npm, CLI via `npx claude-mem`
**License**: Apache-2.0

**Entry points**:
- `src/npx-cli/index.ts` -- CLI entry point (install, start, stop, search, etc.)
- `src/services/worker-service.ts` -- Worker daemon (HTTP server, background initialization)
- `plugin/hooks/hooks.json` -- Claude Code plugin hook definitions

**Core modules**:

| Module | Path | Purpose |
|--------|------|---------|
| Worker Service | `src/services/worker-service.ts` | Daemon management, HTTP API, lifecycle orchestration |
| Claude Provider | `src/services/worker/ClaudeProvider.ts` | Observer Claude via Agent SDK |
| Gemini Provider | `src/services/worker/GeminiProvider.ts` | Alternative observer (Google Gemini) |
| OpenRouter Provider | `src/services/worker/OpenRouterProvider.ts` | Alternative observer (OpenRouter) |
| Session Manager | `src/services/worker/SessionManager.ts` | Active session tracking, message buffering |
| Search Manager | `src/services/worker/SearchManager.ts` | Search orchestration with multi-strategy |
| Context Builder | `src/services/context/ContextBuilder.ts` | Context string assembly (progressive disclosure) |
| Observation Compiler | `src/services/context/ObservationCompiler.ts` | SQLite queries for observations/summaries |
| XML Parser | `src/sdk/parser.ts` | Parse `<observation>` / `<summary>` XML from observer |
| Mode Manager | `src/services/domain/ModeManager.ts` | Mode config (code, chill, investigation) with inheritance |
| ChromaSync | `src/services/sync/ChromaSync.ts` | Vector embedding sync to Chroma |
| Database Manager | `src/services/worker/DatabaseManager.ts` | SQLite connection lifecycle |
| Server | `src/services/server/Server.ts` | Express HTTP server with route registration |
| Supervisor | `src/supervisor/index.ts` | Process registry, signal handling, spawn control |
| Knowledge Agent | `src/services/worker/knowledge/KnowledgeAgent.ts` | Long-form knowledge corpus via observer Claude |

**Data flow**:
```
Claude Code Session
  |
  |-- SessionStart hook --> Worker starts Bun daemon --> ContextBuilder injects prior context
  |-- UserPromptSubmit hook --> Worker logs user intent
  |-- PostToolUse hook --> Worker forwards tool usage to observer Claude via Agent SDK
  |     |-- Observer Claude returns <observation> XML --> parser.ts --> SQLite INSERT
  |     |-- ChromaSync indexes observation for semantic search
  |-- Stop hook --> Observer Claude generates <summary> XML --> SessionSummary stored
  |-- (Next session) SessionStart --> ContextBuilder queries SQLite/Chroma --> injects compressed context
```

**Design patterns**:
- **Singleton**: ModeManager, ChromaMcpManager
- **Strategy**: ChromaSearchStrategy, SQLiteSearchStrategy, HybridSearchStrategy with SearchOrchestrator as facade
- **Observer/Watcher**: TranscriptWatcher for file-system-based session capture
- **Factory**: createSdkSpawnFactory for observer Claude process management
- **Repository**: SessionStore, SessionSearch wrapping SQLite
- **Event broadcasting**: SSEBroadcaster + SessionEventBroadcaster for real-time web viewer

**Architecture style**: Plugin-worker-server architecture. Claude Code runs the plugin hooks (shell commands), which delegate to a long-running Bun-managed worker daemon. The worker hosts an Express HTTP server, manages SQLite+Chroma storage, and spans observer Claude processes. Optionally, a server-beta variant adds Postgres + BullMQ + Docker for multi-user/team deployments.

**Key architectural notes**:
- The observer is a full Claude Code subprocess (not just an API call) -- `ClaudeProvider.ts` uses `query()` from `@anthropic-ai/claude-agent-sdk` with a spawned `claude` executable
- Context injection uses "progressive disclosure": header -> timeline (titles) -> full observations (selected) -> summary fields -> prior messages -> footer with economics
- Token economics are calculated at 4 chars/token estimate; displayed as "X observations, Y read tokens, Z discovery tokens, saved N tokens (M%)"
- The 3-layer MCP search pattern is explicitly documented: `search()` (~50-100 tokens/result) -> `timeline()` -> `get_observations()` (~500-1000 tokens/result)
- Chroma is optional (controlled by `CLAUDE_MEM_CHROMA_ENABLED`); without it, search falls back to SQLite FTS5

## 3. Performance/Benchmarks (real numbers from the repo)

The repo does not ship formal benchmark results in evals/ or docs/. However, several concrete performance claims and measurements are built into the code:

**Token compression**:
- The context header displays live economics. Example from code: "38 observations, 2,646 read tokens, discovery cost 133,852 tokens, saved 131,206 tokens (98%)" -- this is the typical compression ratio from the observer LLM compressing raw transcripts into structured XML observations.
- TokenCalculator.ts uses 4 chars/token estimate (line: `CHARS_PER_TOKEN_ESTIMATE = 4`)

**MCP search efficiency**:
- README claims "~10x token savings" with the 3-layer workflow (search ~50-100 tokens/result, get_observations ~500-1000 tokens/result)
- Default search limit: 20 results (`SEARCH_CONSTANTS.DEFAULT_LIMIT = 20`)

**Context generation**:
- Default observation count: configurable via settings, with separate `totalObservationCount` (for timeline titles) and `fullObservationCount` (for detailed narrative/facts)
- Session count: configurable, with `SUMMARY_LOOKAHEAD = 1` extra fetched for continuity

**Search strategy behavior**:
- Chroma search: top 100 semantic matches, filtered to 90-day recency window, then returns max 1 most recent
- SQLite FTS5: full-text search with `porter unicode61` tokenizer
- Hybrid: FTS5-to-Chroma cross-reference using IDs

**Known latency characteristics**:
- Hook timeouts: SessionStart=60s, PostToolUse=120s, Stop=120s
- MCP init timeout: 60s
- Worker health-check timeout: platform-dependent (up to 15s)
- The observer Claude process is the latency bottleneck -- it must spawn `claude` executable, process transcript, and return XML

**Worktree adoption**: Nested worktrees are detected and merged into parent project's memory, with adoption counts logged per-branch

**Database schema version**: Version 33; includes automatic FTS index rebuild on mismatch

## 4. Trade-offs (wins vs losses -- from issues, design decisions, complexity)

**Wins**:

1. **Zero-effort persistence**: Works automatically via lifecycle hooks. No manual save/load. This is the killer feature -- users get cross-session memory without thinking about it.

2. **LLM-to-LLM compression**: Using a secondary Claude to compress the primary Claude's work is elegant. The compression ratio (~98%) means the context injection is small enough to not degrade the primary session's context window.

3. **Progressive disclosure**: Not all memory is injected at full fidelity. The context string is tiered: index/timeline -> full observations (configurable count) -> summary. This respects the primary session's token budget.

4. **Token economics visibility**: Every context injection shows the cost/benefit. Users see exactly what they're getting and what it costs in tokens, making the trade-off transparent.

5. **Multi-strategy search**: Chroma (semantic) + SQLite FTS5 (keyword) + hybrid, with automatic fallback when Chroma is unavailable. This is robust.

6. **Multi-provider observer**: Claude, Gemini, OpenRouter -- users can pick their compression LLM.

7. **Extensive MCP tooling**: 12 skills (babysit, do, how-it-works, knowledge-agent, learn-codebase, make-plan, mem-search, pathfinder, smart-explore, timeline-report, version-bump, wowerpoint). The platform is genuinely extensible.

8. **Worktree-aware**: Git worktrees are detected and observations merged into the parent project. This shows deep understanding of Claude Code usage patterns.

9. **Privacy controls**: `<private>` tags exclude sensitive content; configurable what gets captured.

10. **OpenClaw gateway support**: Can be deployed as a gateway plugin, not just Claude Code.

**Losses / Risks**:

1. **Observer latency**: The observer Claude subprocess is the critical path. Every PostToolUse hook must wait for the observer to spawn, process, and emit XML. With 120s timeout, this could cause visible delays. The code carefully handles timeouts (e.g., non-blocking error for transcript not found).

2. **Token cost of observer**: The discovery tokens displayed in economics are real API costs. The observer Claude burns through tokens to compress the primary Claude's work. At scale, this adds up (the example shows 133K discovery tokens for 38 observations). The README frames this as "savings," but the observer is real spend.

3. **XML parsing fragility**: Observations and summaries are exchanged as ad-hoc XML (not JSON, not tool-use API). The parser (`sdk/parser.ts`) uses regex-based extraction (`/<observation>([\s\S]*?)<\/observation>/g`). A TODO comment says: `TODO(#2233): migrate to Anthropic tool-use API for deterministic JSON output. This text-XML path is the bridge.` This means the core data format is acknowledged as a temporary bridge to proper tool-use API.

4. **Complex tooling surface**: 12 skills, MCP tools, CLI, web viewer, transcript watcher, OpenClaw gateway -- the surface area is massive. Maintaining all this is non-trivial. The CHANGELOG at 6,633 lines is evidence of rapid iteration with many bug fixes.

5. **Dependency chain**: Requires Node.js, Bun, uv (Python), Chroma (Python), SQLite3. The installer auto-fetches Bun and uv, but this is a lot of moving parts. Multiple GitHub issues reference platform-specific failures (Windows PID reuse, macOS path encoding, etc.).

6. **Thread safety concerns**: The code uses a `SessionMessageBuffer` with dedup (`clear()` resets dedup set), but the hook pipeline is inherently concurrent (PostToolUse can fire while previous observer is still running). The code handles this with careful synchronization, but it's a source of complexity.

7. **Persistence coupling**: The observer Claude process uses OAuth tokens from the primary Claude. Spawn isolation is handled via `sanitizeEnv` and `buildIsolatedEnvWithFreshOAuth`, but credential management adds surface area.

8. **Chroma vs. no-Chroma**: Chroma is a heavy dependency (requires Python/uv). Without it, semantic search is unavailable and only FTS5 keyword matching works. The code handles this gracefully (fallback to SQLite), but the best experience requires the full stack.

9. **Server-beta complexity**: The server-beta track adds Postgres + BullMQ + Docker + Redis + API keys + team/project scope + audit log. This is essentially a second product bolted onto the same codebase. The CHANGELOG shows significant effort here (v13.1.0 is almost entirely server-beta).

10. **Agent SDK version sensitivity**: Pinned to `@anthropic-ai/claude-agent-sdk: ^0.2.138`. SDK breaking changes would break the observer pipeline.

## 5. Design Rationale (why this approach)

**Why lifecycle hooks instead of patching Claude Code internals?**
Claude Code's plugin system exposes lifecycle hooks (SessionStart, PostToolUse, Stop). This is the documented extension point. The hooks invoke shell commands that contact a local HTTP API -- this is portable across platforms and isolates the plugin from the host process. The shell-script mediation layer (finding the plugin root via directory search in `hooks.json`) is awkward but necessary because the hook environment has limited path information.

**Why an LLM-based observer instead of rule-based compression?**
Rule-based log compression would miss semantic meaning. The observer Claude can summarize intent, extract concepts, and judge what matters -- things a regex/parser cannot do. The 98% compression ratio validates this: raw transcripts containing everything (including irrelevant tool outputs) get reduced to structured observations. The ad-hoc XML format is a bridge to proper tool-use API (per TODO #2233), chosen because the initial implementation predates Anthropic's structured output features.

**Why SQLite + Chroma instead of just one?**
SQLite FTS5 provides fast, reliable keyword search with zero infrastructure. Chroma provides semantic/vector search for natural language queries. The hybrid strategy combines both: FTS5 finds exact concept matches, Chroma finds semantically similar content. The fallback chain (Chroma -> SQLite) means the system works without Chroma but gets better with it. This is practical engineering: the minimal install is zero-infrastructure (SQLite only), while power users can opt into vector search.

**Why a separate worker daemon (Bun) instead of in-process?**
The worker must survive Claude Code restarts to persist memory across sessions. A background daemon (managed by Bun as a process supervisor) provides: (a) lifecycle independent of Claude Code, (b) HTTP API for hooks and web viewer, (c) process isolation so observer Claude spawns don't interfere with the primary Claude, (d) independent update/restart cycle.

**Why progressive disclosure in context injection?**
The injected context must be small enough to not crowd out the primary session's actual work. Progressive disclosure (timeline index -> selected full observations -> summary) gives Claude enough signal to reference past work without consuming the full context window. Token economics are displayed so users can tune the trade-off.

**Why the mode system?**
Different workflows need different observation types and concepts. The "code" mode captures bugfixes, features, refactors. The "chill" mode might capture different things. Mode inheritance (e.g., `code--zh` inherits from `code`) reuses base configuration while allowing language/behavior overrides. This is a clean separation of concerns.

**Why Apache-2.0?**
Per docs/license.md: "Claude-Mem is intended to be embedded broadly inside developer tools, local agents, MCP clients, enterprise systems, robotics stacks, and production agent harnesses. Apache-2.0 supports that goal while preserving attribution and including explicit patent license terms." The reserved commercial areas (hosted cloud, team sync, enterprise features) allow the maintainer to monetize without restricting the open-source core.

## 6. Transfer to Lyra (one idea + workstream route)

**One transferable idea**: **Claude-Mem's progressive-disclosure context injection engine** -- specifically, how it queries past observations filtered by concept/type, builds a token-economy-aware context string, and injects it via system reminders. This is directly applicable to Lyra's memory subsystem.

**What Lyra should borrow**:
- The `ObservationCompiler` query pattern: filter past observations by `concepts` (semantic tags) and `type`, sorted by recency, with configurable count limits
- The `TokenCalculator` economics display: show users how many tokens the injected context costs vs. the original discovery cost (the 98% savings figure is compelling)
- The progressive-disclosure tiers: timeline (just titles) -> full details (selected items) -> summary. This means Lyra can inject rich memory without blowing the context window
- The SQLite FTS5 schema: `memory_items_fts` virtual table with porter+unicode tokenizer, auto-synced via triggers

**What Lyra should avoid**:
- The XML-based observer protocol (ad-hoc regex parsing is fragile). Use structured JSON via tool-use API instead
- The heavy dependency chain (Chroma/Python/uv). SQLite FTS5 is sufficient for most use cases; vector search can be opt-in
- The massive skill surface (12 skills, many specialized). Start with 1-2 core memory primitives

**Workstream route**: **Section 4.3** -- Memory & Context Management
- **Route**: `4.3.x` (extend to "Structured Memory Persistence with Progressive Disclosure")
- **Impact**: 7/10 -- Adds concrete, user-visible persistence to Lyra. The compression economics (98% savings) is a compelling demo. Enables cross-session continuity, which is Lyra's current weakest point (no memory across resets)
- **Effort**: 6/10 -- Claude-Mem's SQLite schema, query layer, and context builder are ~2,000 lines of well-isolated TypeScript. Porting the core pattern (not the full plugin infrastructure) is moderate effort. The observer Claude integration is the hardest part (Claude-Mem uses the Agent SDK; Lyra would need its own observer or use the Anthropic API directly)
- **Tier**: Tier 2 (Phase 1-2 deliverable) -- Memory is foundational for multi-turn agents. The progressive-disclosure context builder is Phase 1 material. The observer pipeline for automatic compression is Phase 2.

**Specific implementation sketch for Lyra**:
1. Define an `Observation` type (type, title, narrative/structured-facts, concepts/semantic-tags, timestamps)
2. Add a `memory_items` table with FTS5 index (following Claude-Mem's schema design including auto-sync triggers)
3. Implement an `ObservationCompiler` that queries by concept + type with configurable limits
4. Implement a `ContextBuilder` that assembles a progressive-disclosure string with token economics
5. Add a `CLAUDE_MEM_CONTEXT_*` family of config knobs (observation count, full count, session count, show economics)
6. (Phase 2) Add a background observer that compresses session activity into observations -- could be a simple post-hoc process rather than real-time hooks

**Note file**: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/thedotmack__claude-mem.md`
