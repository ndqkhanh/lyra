# op7418/CodePilot -- Deep-Read

Source: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/op7418__CodePilot`

## 1. Headline Feature & Mechanism

**Headline: Multi-model AI agent desktop client** -- a desktop GUI that connects to 17+ AI providers (Anthropic, OpenRouter, AWS Bedrock, Google Vertex, Zhipu GLM, Kimi, Moonshot, MiniMax, Volcengine, Xiaomi MiMo, Aliyun Bailian, Ollama, LiteLLM, Gemini, etc.), extends via MCP (Model Context Protocol) servers and skills, and provides a full AI agent workspace with persistent memory, scheduled tasks, remote IM bridge, and generative UI widgets.

The core mechanism is a **multi-runtime streaming chat architecture**:
- The `electron/main.ts` process boots a Next.js 16 standalone server on a stable port (47823-47830 range)
- The Next.js server exposes 52 REST endpoints under `src/app/api/`
- Chat send flow: `MessageInput` -> `POST /api/chat/messages` -> `src/lib/claude-client.ts` (creates SDK conversation) -> Claude Agent SDK SSE stream -> `src/lib/stream-session-manager.ts` (manages stream lifecycle) -> `useSSEStream` hook subscribes -> `MessageList` renders -> `src/lib/db.ts` persists to SQLite (WAL mode)
- Three execution engines (runtimes) are available: Claude Code SDK (subprocess), CodePilot Native (in-process), and OpenAI Codex. Users can switch globally or per-session via a pin mechanism
- MCP servers (stdio/sse/http) are registered at runtime alongside built-in CodePilot MCP tools (memory, notify, widget, media, image-gen, cli-tools, dashboard)

## 2. Architecture & Core Modules

**Stack:** Electron 40 (desktop shell) + Next.js 16 App Router (frontend + API) + React 19 + Tailwind CSS 4 + Radix UI (components) + better-sqlite3 WAL (storage) + Claude Agent SDK (AI execution)

**Top-level structure:**
```
electron/main.ts         -- Electron main process (window, IPC, tray, server bootstrap)
src/
  app/                   -- Next.js App Router: 52 API routes + pages
  components/            -- React components (ui/, chat/, ai-elements/, layout/, plugins/, etc.)
  lib/                   -- Core business logic
    claude-client.ts     -- Claude Agent SDK wrapper, streaming orchestration, runtime dispatch
    stream-session-manager.ts -- Client-side SSE stream lifecycle (survives HMR via globalThis)
    db.ts                -- SQLite schema (12+ tables) + CRUD + incremental migrations
    bridge/              -- IM Bridge subsystem (Telegram, Feishu, Discord, QQ, WeChat)
    runtime/             -- Multi-runtime adapter (Claude Code SDK, Native, Codex)
    provider-*.ts        -- Provider catalog, resolver, transport detection
    context-compressor.ts -- Context compression for CONTEXT_TOO_LONG retry
    claude-home-shadow.ts -- ~/.claude shadow for DB-provider isolation
    mcp-loader.ts        -- Project-level MCP loading
  types/index.ts         -- All business types (ChatSession, Message, TokenUsage, etc.)
  hooks/                 -- React hooks
  i18n/                  -- en + zh internationalization
```

**Data flow (chat):**
```
User input -> MessageInput
  -> POST /api/chat/messages
  -> claude-client.ts resolveRuntime() -> runtime.stream()
  -> Claude Agent SDK SSE stream (or Native/Codex equivalent)
  -> stream-session-manager.ts manages stream
  -> useSSEStream hook subscribes
  -> MessageList renders
  -> db.ts persists to SQLite
```

**Database schema (12+ tables):** `chat_sessions`, `messages`, `settings`, `tasks`, `api_providers`, `provider_models`, `media_generations`, `media_tags`, `media_jobs`, `media_job_items`, `media_context_events`, `channel_bindings`, `channel_offsets`, `channel_dedupe`, `channel_outbound_refs`, `channel_audit_logs`, `channel_permission_links`, `channel_configs`, `weixin_accounts`, `weixin_context_tokens`, `cli_tools_custom`, `cli_tool_descriptions`, `scheduled_tasks`, `session_runtime_locks`, `permission_requests`, `task_run_logs`, `notification_events`, `notification_deliveries`

**Pattern highlights:**
- Singleton via `globalThis` pattern for cross-HMR state (stream-session-manager, conversation-registry)
- Capability-aware prompt assembly via Harness Context Compiler (Phase 5d)
- Keyword-gated MCP registration (memory, widget, media, cli-tools, dashboard)
- Permission system with session-level profiles (default/full_access), per-action approval, auto-approve for built-in MCP tools
- Context accounting runtime contract (Phase 7) -- each runtime provides real token breakdowns per category

## 3. Performance / Benchmarks

No formal benchmark suite or performance numbers are published in the repo. Observed design characteristics:

- **SQLite WAL mode** for fast concurrent reads (busy_timeout=5000ms)
- **Stable port range 47823-47830** -- 8-port range for localStorage origin consistency across restarts; avoids OS-assigned port wiping localStorage
- **SSE text emission throttled at 100ms** to avoid excessive React re-renders during fast streaming
- **Idle timeout at 330s** (5.5 minutes) with 10s check interval
- **Stream idle abort with 2s force-abort fallback** for graceful stop
- **CONTEXT_TOO_LONG auto-compress + retry** using rough token estimation (char/4)
- **STM idle timeout: 5 min** GC for stream snapshots after completion
- **Test suite health**: 3233/3233 tests passing (post-flake-fix baseline), with 3086/3086 deterministic after per-worker temp DB isolation
- **Per-session runtime pin immunity** -- changing global runtime doesn't affect pinned sessions
- **Auto-discover models** via provider probe (live API endpoint model discovery)

## 4. Trade-offs (Wins vs. Losses)

| Win | Loss |
|-----|------|
| 17+ providers, switch mid-conversation | Each provider needs its own API key management; third-party Anthropic-compat providers have verified vs experimental tiers |
| Three execution engines (Claude Code SDK, Native, Codex) | Multi-runtime complexity -- runtime detection, capability matrix, per-runtime permission profiles, context accounting contract per runtime |
| Desktop-native file access, terminal, git | Cross-platform build complexity (macOS signing, Windows ARM64, Linux compile-from-source only) |
| Local SQLite storage (WAL mode, no cloud dependency) | All data stays local -- no sync across machines, no cloud backup |
| MCP extensibility (stdio/sse/http) | MCP server reliability varies; in-process MCPs need keyword-gating to avoid overhead (~1s tool discovery per turn) |
| Remote IM Bridge (Telegram, Feishu, Discord, QQ, WeChat) | Each bridge requires its own bot token/credentials; message rendering must downgrade per platform (Telegram HTML / Feishu card / plain text) |
| BSL-1.1 license (free for personal/academic/non-profit) | Commercial use requires separate license; converts to Apache 2.0 in 2029 |
| Assistant Workspace (soul.md, user.md, memory.md, daily check-in) | Workspace files are local markdown -- no structured knowledge graph, no vector search (beyond simple string matching) |
| Generative UI (AI-created dashboards, charts, widgets) | Widget generation requires keyword activation; rendering pipeline (HTML -> screenshot via Chromium CDP) |
| Context accounting breakdown by category (system prompt, memory, skills, MCP, tools, rules) | placeholder values for toolDescriptorTokens (0) and mcpDescriptorTokens (200 per server) -- Phase 1c deferred |

**Known tech debt highlights (from tech-debt-tracker.md, 38 tracked items):**
- ESLint 13 React Compiler errors deferred (on-touch, non-runtime-impacting)
- Codex Account models page returns 404 (console noise, functional fallback exists)
- Context accounting tool/MCP descriptor token placeholders
- @file mention fails with spaces in paths
- Windows shell command generation defaults to bash/POSIX syntax (under investigation)
- macOS notifications sometimes don't surface (likely unsigned dev binary issue)
- Multiple concrete issues from recent phases have been fixed (flake reduction, composer canonical model matching, context storage migration)

## 5. Design Rationale

The project's architecture decisions reflect a clear set of trade-offs shaped by the target audience and operating environment.

**Desktop-first**: By choosing Electron + Next.js 16 (instead of a web-only SaaS), CodePilot gets native file system access, local terminal management, and OS-level notifications. The trade-off is cross-platform distribution complexity (macOS notarization, Windows SmartScreen, no cloud sync).

**Multi-provider from day one**: The provider catalog and resolver system (`provider-catalog.ts`, `provider-resolver.ts`, `provider-doctor.ts`) abstract away AI provider differences. This means the user owns their API keys and provider choice, but the abstraction layer must handle wildly different capabilities (Anthropic Message API vs. OpenAI-compatible vs. Google Gemini) with a unified streaming interface.

**Multi-runtime architecture (Phase 2+)**: The most architecturally interesting decision. Rather than committing to a single AI execution backend, CodePilot defines a `Runtime` interface and implements three adapters (Claude Code SDK, Native, Codex). This allows:
- Pinning sessions to a specific runtime (session pin > global default)
- Per-runtime capability matrices (what models, tools, features each runtime supports)
- Runtime-specific context accounting (each runtime reports its own token breakdown)
- Graceful degradation when a runtime becomes unavailable

The runtime abstraction is supported by a Harness Context Compiler that assembles capability prompts per runtime, a permission system with per-runtime tool approval profiles, and an error classifier that categorizes failures by root cause (16 categories).

**MCP as the extension layer**: Instead of building a proprietary plugin system, CodePilot adopts the Model Context Protocol. This buys compatibility with the growing MCP ecosystem but requires careful transport support (stdio for local, sse/http for remote), runtime status monitoring, and security gating (auto-approve for built-in servers, keyword-gated registration for expensive servers).

**Local-first storage**: SQLite with WAL mode means zero infrastructure dependencies, fast startup, and offline-capable operation. The cost is no cross-device session sync and no multi-user collaboration -- these are deliberately out of scope.

**Controlled evolution via execution plans**: The codebase is organized around an execution-plan discipline: `docs/exec-plans/active/` for in-progress phases, `completed/` for finished ones, and a `tech-debt-tracker.md` that lists 38 tracked items. Every phase has a cross-referenced handover doc (`docs/handover/`) and product insights doc (`docs/insights/`). This is unusually well-documented for an open-source project and reflects a rigorous engineering workflow.

## 6. Transfer to Lyra

**Transferable Idea**: **Multi-runtime agent execution engine** -- the ability to switch between different backends (the "runtime" abstraction) at the session level, with each runtime providing its own capability matrix, permission model, and context accounting. CodePilot's `streamClaude()` entry point in `src/lib/claude-client.ts` (lines 470-668) shows the dispatcher pattern: `resolveRuntime()` -> `runtime.stream()`, where each runtime adapter implements a common `Stream` interface. The runtime pin (`sessionRuntimePin` in `ChatSession`) lets users lock a session to a specific engine, preventing silent model substitutions when the global default changes.

**Workstream Route**: This maps to **Section 4.1 (Architecture)** of the Lyra upgrade plan, specifically the runtime abstraction layer. CodePilot's approach of having a lightweight `Runtime` interface (stream method + capability reporting + permission profiles) with multiple implementations could directly inform Lyra's agent execution orchestration.

**Impact**: 6/10 -- Medium-high. The multi-runtime pattern is directly applicable to Lyra's need for modular agent backends, but implementing it requires significant refactoring.

**Effort**: 7/10 -- High. CodePilot's Phase 2-5 sequence took ~3 weeks of active development with a dedicated team. The runtime abstraction touches the chat send path, permission system, capability matrix, error classifier, and context accounting.

**Tier**: **Tier 1** -- "Directly adoptable with minor adaptation." The concept is clean and well-tested; the specific implementation would need adaptation to Lyra's tech stack but the design pattern transfers directly.

**LICENSE**: BSL-1.1 (Business Source License). Free for personal, academic, non-profit use. Commercial use (by organizations with 100+ employees or for sale) requires a commercial license. Converts to Apache 2.0 on 2029-03-16. Modifications and copy are permitted for non-commercial purposes. **Cannot merge code directly** into an Apache/MIT project without a commercial license, but design patterns and architectural concepts are freely usable.
