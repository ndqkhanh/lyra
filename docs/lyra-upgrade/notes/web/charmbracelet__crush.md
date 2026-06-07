# charmbracelet/crush -- Deep-Read

## 1. Headline Feature & Mechanism

Crush is a **terminal-native AI coding assistant** built by Charmbracelet, Inc. -- a Go-based TUI competitor to tools like Claude Code, Cursor, and GitHub Copilot. Its headline feature is a **fully self-contained, zero-configuration terminal coding agent** that runs in any terminal on any platform (macOS, Linux, Windows, FreeBSD, OpenBSD, NetBSD, Android) with built-in support for 20+ LLM providers (Anthropic, OpenAI, Bedrock, VertexAI, Gemini, Groq, OpenRouter, local models via Ollama/LM Studio, and more).

How it works at the code level:
- **Entry** is `main.go` which delegates to `cmd.Execute()` in `internal/cmd/root.go`.
- `root.go` parses cobra CLI flags and calls `setupWorkspace()`, which branches on the `CRUSH_CLIENT_SERVER` env var: either creates an in-process `AppWorkspace` (wrapping `app.App`) or connects to a detachable server process (`ClientWorkspace` via HTTP over a Unix socket / Windows named pipe).
- The `app.App` in `internal/app/app.go` wires together: session management (SQLite), message persistence, history/file tracking, LSP manager, skills manager, permissions service, and the `AgentCoordinator`.
- The coordinator in `internal/agent/coordinator.go` resolves the LLM provider+model config, builds the system prompt (with MCP instructions, skill prompts, etc.), creates the `fantasy.Agent` (the Charm `fantasy` library's multi-provider LLM abstraction), and delegates to `sessionAgent.Run()` in `internal/agent/agent.go`.
- The `sessionAgent` manages the full conversation lifecycle: message history, auto-summarization (when context approaches the model's window), tool execution, permission prompts, queueing of concurrent prompts, and cancellation via an accept-sequence-based dispatch system.
- The TUI in `internal/ui/model/ui.go` is a Bubble Tea v2 program that provides the interactive chat interface, session sidebar, model picker, permission dialogs, and more.
- MCP (Model Context Protocol) support in `internal/agent/tools/mcp/` provides stdio, HTTP, and SSE transport types for third-party tool servers.

## 2. Architecture & Core Modules

```
main.go
├── internal/cmd/root.go          -- CLI entry: cobra commands, workspace setup
├── internal/app/app.go           -- App wiring: sessions, messages, LSP, skills, agent
├── internal/agent/
│   ├── agent.go                  -- sessionAgent: LLM conversation orchestration
│   ├── coordinator.go            -- Coordinator: resolves provider/model, builds agent
│   ├── tools/                    -- Built-in tools: bash, edit, grep, view, write, fetch, etc.
│   │   └── mcp/                  -- MCP protocol client (stdio/http/SSE)
│   └── notify/                   -- Event types for agent lifecycle
├── internal/session/session.go   -- Session CRUD (SQLite), including agent tool sessions
├── internal/message/             -- Message persistence (SQLite)
├── internal/config/
│   ├── config.go                 -- Config model: provider, model, LSP, MCP
│   ├── store.go                  -- ConfigStore: layered config loading
│   ├── resolve.go                -- Variable resolution ($VAR, $(cmd))
│   └── provider.go               -- Provider configuration
├── internal/server/server.go     -- HTTP API over Unix socket / named pipe
├── internal/backend/backend.go   -- Transport-agnostic business logic
├── internal/workspace/
│   ├── workspace.go              -- Workspace interface (TUI/CLI abstraction)
│   ├── app_workspace.go          -- In-process implementation
│   └── client_workspace.go       -- Client/server implementation
├── internal/lsp/                 -- LSP client integration
├── internal/ui/model/ui.go       -- Bubble Tea TUI entry
├── internal/skills/              -- Agent Skills standard support
├── internal/db/                  -- SQLite via SQLC codegen
├── internal/pubsub/              -- Generic pub/sub broker
├── internal/permission/          -- Permission prompting service
├── internal/filetracker/         -- File read tracking
├── internal/history/             -- File history management
├── internal/hooks/               -- Post-tool hooks system
├── internal/commands/            -- Command detection/parsing
├── internal/diff/                -- Diff computation
├── internal/csync/               -- Concurrent-safe collections
└── internal/version/             -- Build version metadata
```

**Data flow for a user prompt:**
1. TUI captures input -> `Workspace.AgentRun()` -> `Coordinator.Run()` -> `sessionAgent.Run()`
2. `sessionAgent` validates the call, creates user message in DB, builds fantasy agent
3. Fantasy agent streams the LLM response with callbacks for reasoning, text, tool calls
4. Each tool call goes through `hooked_tool.go` -> `permission.Service` (if needed) -> tool implementation
5. Tool results are persisted and fed back to the LLM as tool result messages
6. On step finish, usage/cost is updated in session; when approaching context limit, auto-summarization triggers
7. Session messages are persisted in SQLite via Message Service

**Key patterns:**
- **Pub/sub everywhere**: sessions, messages, LSP events, agent notifications, run completions all flow through `pubsub.Broker`
- **Dual-mode architecture**: same `Workspace` interface for local in-process and remote client/server
- **Provider abstraction**: all LLM providers go through the `fantasy` library (openai, anthropic, gemini, bedrock, etc.)
- **Concurrency-safe agent dispatch**: per-session mutexes, accept sequences, cancel marks, queueing -- industrial-grade concurrent prompt handling

## 3. Performance/Benchmarks

The repository does not ship formal benchmarks (no `BenchmarkXxx` functions found in the source tree). The `config/load_bench_test.go` suggests internal benchmarks exist for config loading but no published numbers. The `Taskfile.yaml` has profiling commands (`profile:cpu`, `profile:heap`, `profile:allocs`) pointing to pprof, indicating the team uses profiling for performance work. Metrics collection is pseudonymous and metadata-only.

Key performance-relevant design decisions pulled from the source:
- SQLite for persistence (embedded, no separate server)
- Auto-summarization at configurable thresholds (large: 200k window - 20k buffer; small: 80% of window)
- Bounded blocking for the RunComplete publish (5s timeout)
- Background context for cleanup writes after cancellation/error
- Embedded shell for variable expansion ($VAR, $(cmd)) -- avoids spawning a system shell

## 4. Trade-offs

**Wins:**
- **Zero configuration**: just set an API key and run. No config file, no setup wizard needed.
- **Multi-platform**: first-class support on macOS, Linux, Windows (PowerShell and WSL), Android, FreeBSD, OpenBSD, NetBSD.
- **Self-contained**: single binary, embedded SQLite, no Node.js or Python runtime dependency. Install via `go install` or one of 10+ package managers.
- **Multi-provider from day one**: 20+ LLM providers supported through the `fantasy` abstraction layer. Switch models mid-session while preserving context.
- **MCP native**: stdio, HTTP, and SSE transports for third-party tools. Shell expansion in config values.
- **LSP integration**: the assistant can query LSP servers for diagnostics and context.
- **Agent Skills standard**: supports the open `agentskills.io` standard for extensible skills. Reads from the same paths as Claude Code, Cursor, etc.
- **Shared workspaces**: multiple TUI instances can connect to the same workspace, sharing session state, permissions, LSP, and MCP.
- **Attribution system**: configurable commit attribution (`Co-Authored-By`, `Assisted-by`, or none).
- **Industrial-grade concurrency**: accept-sequence-based dispatch with proper cancellation semantics, queueing with per-prompt lifecycle.
- **Metrics with opt-out**: pseudonymous usage metadata helps maintainers prioritize; prompts and responses are never collected.

**Losses:**
- **Requires Go 1.26.4**: very recent Go toolchain, may be a barrier for some build environments.
- **FSL-1.1-MIT license**: NOT pure MIT. FSL-1.1 is a source-available license that restricts "competing use" (e.g., offering a similar CLI coding assistant). Only converts to MIT after 2 years. This is a deliberate business decision but limits certain use cases.
- **Heavy dependency tree**: `go.mod` has ~220 direct+indirect dependencies, including AWS SDK, Azure SDK, Google Cloud, PostgreSQL, various LLM SDKs. Binary size is likely substantial.
- **Dual-mode complexity**: the client/server vs in-process split adds significant complexity (two implementations of every workspace method, startup orchestration with socket management, version mismatch detection).
- **Slog logging as a side effect**: the codebase itself notes that `config.Load` uses slog before the file-based logger is set up, requiring a workaround (`slog.DiscardHandler`).
- **Metrics in a CLI tool**: pseudonymous metrics collection (even opt-out) is controversial in a terminal tool. The `PostHog` dependency confirms real analytics infrastructure.
- **Desktop notification dependency**: uses `beeep` and `go-toast` for notifications, which adds platform-specific complications (macOS notifications lack icons due to platform limitations, noted in README).
- **macOS clipboard limitation**: requires additional tools on Linux/BSD (wl-clipboard, xclip).

## 5. Design Rationale

The architecture is driven by a deliberate set of design choices:

- **Go + Bubble Tea for the TUI**: Charmbracelet's own ecosystem (Bubble Tea, Lip Gloss, Bubbles) enables a fully terminal-native experience with no Electron/WebView overhead. The choice of Go means a single static binary with no runtime dependency.
- **In-process first, client/server as opt-in**: the default path runs everything in the same process (zero setup, no daemon management). The client/server mode (behind `CRUSH_CLIENT_SERVER=1`) exists for advanced use cases like shared workspaces across terminals. The `Workspace` interface abstracts both cleanly.
- **Fantasy as LLM abstraction**: rather than building provider support into Crush itself, the team created the `fantasy` library (separate module) providing a unified agent interface. This allows Crush to support any provider without coupling to their SDKs. The separate `catwalk` module provides community-maintained provider/model metadata.
- **SQLite for persistence**: embedded database means no infrastructure. Message history, sessions, configuration all live in a local SQLite file via SQLC codegen (type-safe SQL).
- **Accept-sequence dispatch system**: the agent's concurrent dispatch model is notably sophisticated (more industrial than most CLI coding assistants). Every accepted prompt gets a monotonically increasing sequence number; cancellation records a high-water mark so only prompts at or below the mark are canceled. This prevents race conditions between concurrent prompts, cancellations, and queue drains.
- **MCP as the extensibility layer**: rather than building a plugin system, Crush adopts the Model Context Protocol standard. This means any MCP-compatible server works out of the box, and tools can be written in any language.
- **Skills as markdown**: the Agent Skills standard (`.md` files with YAML frontmatter) is a deliberately simple extension mechanism -- no compilation, no binary plugins, just instructions the agent reads and follows.
- **Auto-summarization as a safety net**: rather than imposing a hard context limit, Crush automatically summarizes sessions when approaching the context window boundary, then continues the conversation. This is transparent to the user but adds latency at the summarization point.

## 6. Transfer to Lyra

**One transferable idea**: **Accept-sequence dispatch and per-session cancellation**

Crush's `internal/agent/agent.go` implements a concurrent dispatch system that is far more robust than most CLI assistants. The key mechanism:
- Every prompt dispatch gets a monotonic accept sequence number (`acceptSeqGen`)
- `BeginAccepted()` increments the counter and returns a handle
- `Cancel()` records a high-water mark at the current sequence
- On entry, `Run()` checks if the handle's sequence is at or below the mark -> cancel-on-entry
- Queue-drain also checks sequences to drop only covered prompts while keeping post-cancel prompts

This means: **cancel is lossless, race-free, and compositional** -- a user can cancel a busy session, then immediately send a new prompt, and the new prompt runs (not poisoned by the earlier cancel). A cancelled prompt with a RunID still gets a terminal `RunComplete` event so callers don't hang. Lyra's current cancellation logic is likely simpler (e.g., a single `Cancel()` that may clear or may race). Porting this pattern would improve reliability, especially in multi-session or multi-client scenarios.

**Workstream route**: §4.2 (Concurrency & Correctness) -- this pattern specifically addresses the "dispatch-ack-cancel" correctness gap in Lyra's agent lifecycle.

**Impact**: 7 (High -- eliminates a class of race conditions in concurrent prompt handling, which affects reliability, user trust, and the multi-session feature)

**Effort**: 4 (Medium -- the core logic is ~200 lines; adding accept reservation, sequence tracking, and proper cancel marks requires careful integration with Lyra's session/agent lifecycle but is mechanically straightforward)

**Tier**: P2 (Strong quality-of-life improvement; existing logic works for single-prompt cases but will fail under concurrent load)

**LICENSE**: FSL-1.1-MIT (Functional Source License, version 1.1, with MIT future license after 2 years). Not pure MIT -- the FSL-1.1 restricts "competing use" (e.g., offering a substitute coding assistant). Source can be read for research and non-commercial purposes. The concrete MIT grant activates on the second anniversary of release. For Lyra's purposes (research and internal use), reading and adapting the dispatch pattern is fine; commercial redistribution of adapted code would violate the FSL until the MIT conversion date.
