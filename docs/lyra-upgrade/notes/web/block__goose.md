# block/goose (now aaif-goose/goose) -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline**: Goose is a general-purpose, open-source AI agent with a native desktop app (macOS/Linux/Windows), CLI, and embeddable API, built in Rust. It is the flagship agent of the Agentic AI Foundation (AAIF) at the Linux Foundation.

**How the code really works**:

Goose implements an event-driven, loop-based agent architecture. The core loop lives in `crates/goose/src/agents/agent.rs` (3399 lines), specifically the `reply_internal` method which runs a turn loop:

1. **Provider streaming** -- A `Provider` trait (defined in `crates/goose/src/providers/base.rs`) abstracts all LLM backends. The `stream()` method is the single required override; `complete()` and `complete_fast()` are default-provided convenience wrappers. There are 40+ provider implementations (Anthropic, OpenAI, Google, Ollama, Azure, Bedrock, local llama.cpp, Gemini CLI, Claude Code, etc.) in `crates/goose/src/providers/`.

2. **Tool execution via MCP** -- All tools (shell, file editing, reading, extensions) are surfaced through the Model Context Protocol (MCP). The `ExtensionManager` (`crates/goose/src/agents/extension_manager.rs`) manages MCP client connections (stdio and streamable HTTP). Tools are dispatched from `dispatch_tool_call()` in agent.rs, which routes through hook checks, categorizes the tool (shell/read/write/other), runs tool inspectors (security, egress, permission, adversary, repetition), then delegates to the appropriate extension or frontend handler.

3. **Multi-layer tool inspection pipeline** -- Before any tool executes, it passes through: `SecurityInspector` -> `EgressInspector` -> `AdversaryInspector` (LLM-based, optional via `~/.config/goose/adversary.md`) -> `PermissionInspector` -> `RepetitionInspector`. This runs in `ToolInspectionManager` and produces approval/denial/needs-approval buckets.

4. **Lifecycle hooks system** -- Modeled after the Open Plugins hooks specification (`crates/goose/src/hooks/mod.rs`). Hooks fire on: PreToolUse, PostToolUse, PostToolUseFailure, SessionStart, SessionEnd, UserPromptSubmit, BeforeReadFile, AfterFileEdit, BeforeShellExecution, AfterShellExecution, Stop. Stop hooks have a configurable block cap (`GOOSE_STOP_HOOK_BLOCK_CAP`, default 8) to prevent infinite denial loops.

5. **Context management** -- Automatic compaction at 80% context threshold (`DEFAULT_COMPACTION_THRESHOLD = 0.8`), with `tool_call_cut_off` computed from model context limits. Tool-pair summarization is done asynchronously in the background. Uses a `PromptManager` to build the system prompt dynamically from extensions, frontend instructions, and mode.

6. **ACP (Agent Client Protocol)** -- Supports the Agent Client Protocol alongside MCP for provider discovery and configuration, with OAuth flows (including device code grant).

## 2. Architecture & Core Modules

### Crate layout (9 crates in workspace):

| Crate | Purpose |
|-------|---------|
| `goose` | Core agent logic, providers, MCP client, context mgmt, hooks, permissions, security, recipes, sessions |
| `goose-cli` | CLI entry point (`crates/goose-cli/src/main.rs`), interactive shell, TUI, progress bars, config commands |
| `goose-server` | Backend HTTP server (`goosed`), OpenAPI routes, session management, extension validation, MCP server runner |
| `goose-mcp` | Built-in MCP servers: Memory, Tutorial, ComputerController, AutoVisualiserRouter |
| `goose-providers` | Provider type metadata, schema generation, standalone provider definition trait |
| `goose-acp-macros` | Proc macros for ACP schema generation |
| `goose-sdk` | High-level SDK for embedding goose |
| `goose-sdk-types` | SDK type definitions |
| `goose-test` / `goose-test-support` | Test utilities, integration test helpers |

### Entry points:
- **CLI**: `crates/goose-cli/src/main.rs` -- spawns a dedicated 8MB-stack thread with a Tokio multi-thread runtime, then calls `goose_cli::cli::cli()`
- **Server**: `crates/goose-server/src/main.rs` -- supports subcommands: `Agent` (runs the agent HTTP server), `Mcp` (runs individual MCP servers), `ValidateExtensions`
- **Desktop UI**: `ui/desktop/src/main.ts` -- Electron app
- **Agent**: `crates/goose/src/agents/agent.rs` -- `Agent` struct with `reply()` and `reply_internal()` methods

### Data flow:
```
User Input (CLI/Desktop/API)
  -> Agent::reply()
    -> Command detection (/, /clear, etc.)
    -> Session persistence (message saved)
    -> Compaction check (if >80% context, summarize)
    -> reply_internal()
      -> Turn loop (max 1000 by default, GOOSE_MAX_TURNS)
        -> provider.stream(system_prompt, messages, tools)
        -> Categorize tool calls (frontend vs backend)
        -> Tool inspection pipeline
        -> dispatch_tool_call() -> ExtensionManager -> MCP client/stdio
        -> Post-tool hooks
        -> Check final_output tool / goal / grind / retry logic
      -> Stop hook check
```

### Architectural patterns:
- **Provider trait pattern** -- new providers just implement the `Provider` trait and register in `provider_registry.rs`
- **Inspector pipeline** -- chain-of-responsibility for tool safety checks
- **Strategy pattern for extensions** -- both MCP (external processes) and frontend (in-app) extension types share the `ExtensionConfig` enum
- **Event streaming** -- all agent output is a `BoxStream<AgentEvent>` (Message, McpNotification, HistoryReplaced)
- **Builder pattern** -- `PromptManager::builder()`, `Recipe::builder()`, `AgentConfig` with builder methods

## 3. Performance/Benchmarks

The repo includes the **Open Model Gym** evaluation harness (`evals/open-model-gym/`):

- **Matrix**: Models (Opus, GLM-4.7, Kimi K2.5, GPT-OSS 120B/20B, Qwen3-Coder) x Runners (Goose, OpenCode, Pi) x Scenarios (everyday-app-automation, file-editing, multi-turn-edit)
- **Methodology**: Each combination runs 3 repetitions; the **worst result** is kept to catch flaky passes. This is a deliberate design choice for robustness.
- **Validation rules**: file_exists, file_contains, file_matches (regex), command_succeeds, tool_called (regex on args)
- **MCP Harness** (`evals/open-model-gym/mcp-harness/`): A mock MCP server that simulates tools (gdrive, sheets, salesforce, slack, calendar, gmail, jira, github) returning realistic mock data -- no real API calls
- The `goose-self-test.yaml` file at repo root defines a self-validation recipe run via `goose run --recipe goose-self-test.yaml`
- **No published benchmark numbers** in the repo (results are locally generated HTML reports)

The codebase also includes tree-sitter parsing for 10 languages (Go, Java, JavaScript, Kotlin, Python, Ruby, Rust, Swift, TypeScript) for code-aware tooling, and `token_counter.rs` backed by `tiktoken-rs`.

## 4. Trade-offs (wins vs losses)

**Wins:**

1. **Ecosystem reach** -- 15+ providers, 70+ MCP extensions, works with existing Claude/ChatGPT/Gemini subscriptions via ACP. No vendor lock-in.

2. **Three surfaces** -- Desktop app (Electron), CLI, API server. Caters to different user modes (discovery, power use, embedding).

3. **Rust performance & portability** -- Single binary with no heavy runtime dependency. Compiles for macOS, Linux, Windows. LLM inference via llama.cpp (CUDA, Metal, Vulkan). Whisper transcription via candle (local inference feature gate).

4. **Safety architecture** -- Multi-inspector pipeline (security, egress, adversary, permission, repetition) with lifecycle hooks for policy enforcement. Stop hook block cap prevents infinite loops.

5. **ACP for provider abstraction** -- The Agent Client Protocol allows using existing subscriptions (Claude Code, Gemini CLI, ChatGPT Codex) as providers rather than managing API keys.

6. **Open governance** -- Moved to Linux Foundation AAIF, with CONTRIBUTING.md, GOVERNANCE.md, MAINTAINERS.md, SECURITY.md. Apache 2.0 license.

**Losses / complexities:**

1. **Dependency surface** -- Massive: ~200+ workspace dependencies including tree-sitter for 10 languages, llama-cpp-2, candle for local inference, sqlx for SQLite, oauth2, rmcp (MCP library), tiktoken-rs, opentelemetry, etc. The `Cargo.lock` is very large.

2. **Compile time** -- Conditional features (cuda, vulkan, local-inference, aws-providers, system-keyring, nostr, otel) mean the default build takes a long time. The `portable-default` feature excludes cuda/vulkan but still includes many optional deps.

3. **Extension management complexity** -- User extensions are loaded via MCP subprocesses (stdio or streamable HTTP), which means managing process lifecycle, timeouts, crash recovery. Frontend extensions add another layer of indirection.

4. **LLM dependency for core features** -- Session naming, recipe creation, conversation summarization, adversary inspection all require an LLM call. If the provider is down, these features fail.

5. **Context compaction cost** -- Compaction itself calls the LLM (summarization), consuming tokens. Recovery from `ContextLengthExceeded` errors requires compaction which is another LLM call.

6. **Modularity overhead** -- The `goose` crate is a monolith (37 submodules under `src/`). While it has clear internal boundaries, compile caching is limited by the crate structure.

## 5. Design Rationale

**Why Rust**: Performance, safety, portability, and native binary distribution. No JVM/Node runtime dependency for end users.

**Why MCP for tooling**: Decouples tool implementations from the agent. New tools are added as standalone MCP servers without changing the agent core. The MCP ecosystem provides 70+ pre-built extensions.

**Why provider trait over unified API**: LLM APIs diverge too much (streaming format, tool call schema, thinking modes, caching controls). The `Provider` trait lets each backend implement its native protocol while the agent loop remains provider-agnostic.

**Why lifecycle hooks**: Inspired by Open Plugins spec. Allows enterprise policy enforcement (audit logging, command denylists, file access control) via external scripts without modifying the agent. The hook manager is deliberately file-based (hooks.json) for observability.

**Why tool inspection pipeline**: Defense-in-depth for security. Static checks (security inspector for path traversal, shell injection) + LLM-based review (adversary inspector) + user permission prompts. Each inspector is independent and composable.

**Why worst-result benchmarking**: The Open Model Gym uses "keep the worst result" across 3 reps to surface flaky behavior. This prioritizes reliability over average performance -- if an agent can't consistently pass, it's marked failed.

## 6. Transfer to Lyra

**Transferable idea: Tool inspection pipeline as a composable safety layer.**

Lyra currently has a simpler permission/approval model. Goose's multi-inspector pipeline -- where each inspector is a self-contained trait implementation that can block, flag, or approve tool calls -- would give Lyra a clean, extensible way to add safety checks (e.g., "don't delete files in /etc", "warn before network access", "block commands matching regex patterns").

Each inspector in Goose implements `trait ToolInspector { fn inspect(...) -> InspectionResult; }` and is registered in `ToolInspectionManager`. The pipeline runs in order, and results are classified into `approved`, `needs_approval`, and `denied` -- a pattern that maps cleanly to Lyra's existing permission system.

**Workstream route**: Section 4.3 (Safety), specifically 4.3.x "Composable tool inspection pipeline".

**Impact**: 7/10 -- direct improvement to Lyra's safety model without architectural rework.

**Effort**: 5/10 -- requires defining the `ToolInspector` trait, implementing 2-3 core inspectors (path traversal, shell injection patterns, egress blocking), and wiring them into the existing tool dispatch path.

**Tier**: Core (safety is a blocking requirement for production deployment).

**LICENSE**: Apache 2.0 -- compatible with any Lyra licensing model.
