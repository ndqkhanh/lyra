# OpenDev-to/OpenDev -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline: Compound AI System Architecture -- Parallel coding agents, each bound to an independently configured LLM, with per-workflow model routing across 5 slots.**

OpenDev is an open-source, terminal-native AI coding agent built as a compound AI system. The core architectural innovation is that it does not use a single monolithic LLM. Instead, work is organized into concurrent sessions composed of specialized sub-agents, each executing typed workflows (Execution, Thinking, Compaction, Self-Critique, Vision) that independently bind to a user-configured LLM.

The mechanism works as follows:
- **5 Workflow Model-Binding Slots**: Normal (execution), Thinking (reasoning), Compact (context summarization), Critique (output verification), and VLM (vision). Each slot binds to any LLM from any of 9 supported providers. Example: Claude Opus handles execution, GPT-o3 handles reasoning, a lightweight Qwen model handles compaction.
- **Agent Fleet Spawning**: A single master session can spawn N sub-agents in parallel, each with its own LLM binding, context window, and tool access. All run concurrently via Tokio async. The README gives the example of surveying all crates in a codebase by spawning one agent per crate.
- **ReAct Loop with Doom-Loop Detection**: The central execution model is a Reason-Act cycle. Each iteration: LLM call -> parse response -> execute tools -> feed results back -> repeat. A doom-loop detector tracks tool call fingerprints (name + args hash) in a sliding window and detects repeating cycles of length 1-3, escalating from redirect (1st) to notify (2nd) to force-stop (3rd).
- **Staged Context Compaction**: 5-level progressive context optimization (70% warning, 80% observation masking, 85% fast pruning, 90% aggressive trimming, 99% full LLM-powered compaction). Sliding window keeps 50 recent messages verbatim for sessions with 500+ messages.
- **Tool Schema Deferral**: Only core tools (Bash, Read, Write, Edit, Glob, Grep, AskUser, TaskComplete, ToolSearch) are sent with every LLM call. All other tools are deferred and loaded on-demand via the ToolSearch meta-tool, reducing per-turn input tokens from ~13k to ~6k.

Written in Rust (edition 2024). Version 0.1.8 as of April 2026. Very early but production-quality architecture.

## 2. Architecture & Core Modules

**21 crates in a Cargo workspace. Binary entrypoint: `opendev-cli`.**

### Crate Map (data flow direction)

```
opendev-cli (entry point)
  |-- opendev-config (hierarchical: project > user > env > defaults)
  |-- opendev-runtime (orchestrator: AgentRuntime struct owns all services)
  |     |-- opendev-agents (MainAgent, ReAct loop, doom loop, prompts, subagents)
  |     |-- opendev-context (compaction, context picker, environment context)
  |     |-- opendev-http (AdaptedClient, provider adapters for Anthropic/OpenAI/Gemini/etc.)
  |     |-- opendev-models (shared types: ChatMessage, Session, AppConfig, ToolCall)
  |     |-- opendev-tools-core (BaseTool trait, ToolRegistry, middleware)
  |     |-- opendev-tools-impl (30+ tool implementations: bash, edit, file ops, web, agents)
  |     |-- opendev-tools-lsp (LSP integration)
  |     |-- opendev-tools-symbol (AST-based symbol navigation)
  |     |-- opendev-mcp (Model Context Protocol integration)
  |     |-- opendev-sandbox (microsandbox VM isolation)
  |     |-- opendev-hooks (hook system)
  |     |-- opendev-channels (channel routing)
  |     |-- opendev-plugins (plugin manager)
  |     |-- opendev-history (session persistence, JSON per project, atomic writes)
  |-- opendev-tui (ratatui + crossterm terminal UI)
  |-- opendev-web (axum + WebSocket web backend)
  |-- opendev-repl (REPL loop, query enhancement)
```

### Entry Points & Data Flow

1. **`opendev-cli/src/main.rs`** -- Binary entry. Parses clap args, dispatches to:
   - `runners::run_non_interactive()` for `-p` flag (single prompt)
   - `runners::run_interactive()` for TUI mode
   - Subcommands: `setup`, `config`, `mcp`, `run ui`, `session`, `channel`, `remote`

2. **`opendev-runtime/src/lib.rs`** -- `AgentRuntime` struct is the central orchestrator. Its `new()` constructor:
   - Creates `ToolRegistry` with all tools
   - Discovers custom tools from `.opendev/tools/`
   - Scans for skill directories from working dir up to git root
   - Registers invoke_skill, spawn_subagent, team tools, and checkpoint middleware
   - Creates `AdaptedClient` with provider-specific adapter (Anthropic, OpenAI, Gemini, Ollama, Azure, or generic OpenAI-compatible)
   - Sets up LLM caller with model config (supports temperature, max tokens, reasoning effort)
   - Creates per-turn prompt composer with section caching

3. **`opendev-agents/src/main_agent.rs`** -- `MainAgent` uses composition: `LlmCaller` + `ReactLoop` + `PromptComposer` + `ToolRegistry` + `ResponseCleaner`. The `BaseAgent` trait defines `build_system_prompt()`, `build_tool_schemas()`, `call_llm()`, and `run()`.

4. **`opendev-agents/src/react_loop/execution.rs`** -- The `run_inner()` method implements the full ReAct cycle:
   - Per-turn context collectors (live data: todos, git, plan mode)
   - Safety checks (interrupt, max iterations)
   - Tool schema deferral (core tools + activated via ToolSearch)
   - LLM call via phases::execute_llm_call
   - Response processing with doom-loop detection
   - Parallel execution (all spawn_subagent calls first)
   - Batched execution (read-only tool parallelism)
   - Sequential execution fallback

### Patterns
- **Composition over inheritance**: `MainAgent` holds `LlmCaller`, `ReactLoop`, etc. as fields rather than using Python-style mixins (the codebase explicitly notes this as a migration from Python).
- **Hierarchical config merge**: project settings > user settings > env vars > defaults. Arrays are concatenated+deduplicated, not replaced.
- **Provider adapter pattern**: ProviderAdapter trait normalizes disparate API formats (Anthropic Messages API, OpenAI Responses API, Gemini API, Chat Completions) into a uniform internal representation.
- **Atomic file writes**: Config files use write-to-tmp-then-rename to prevent corruption.
- **Arc-based sharing**: ToolRegistry, HttpClient, skill_loader, subagent_manager all shared via Arc for concurrent subagent access.

## 3. Performance/Benchmarks

The README provides rigorous published benchmarks using standard tools:

| Agent | Startup (mean +- sigma) | Peak Memory (median) | Install Size |
|-------|------------------------|---------------------|--------------|
| **OpenDev** 0.1.8 | **4.3 ms +- 0.4 ms** | **9.4 MB** | **18 MB** |
| Codex 0.116.0 | 37.8 ms +- 0.8 ms (9x) | 43.7 MB (4.6x) | 116 MB |
| Claude Code 2.1.87 | 87.3 ms +- 2.0 ms (20x) | 214.6 MB (22.8x) | 188 MB |
| OpenCode 1.2.27 | 557.4 ms +- 31.8 ms (128x) | 285.9 MB (30.4x) | 90 MB |

Methodology: macOS ARM64 (Apple Silicon), hyperfine --shell=none --warmup 10 --runs 100 for startup, /usr/bin/time -l median of 20 runs for memory. Multipliers relative to OpenDev.

Additional performance characteristics from the codebase:
- **Tool schema deferral** reduces per-turn input tokens from ~13k to ~6k (measured internally).
- **Fully async I/O** via Tokio with zero interpreter overhead (no GIL).
- **Parallelized startup I/O** (v0.1.6 changelog) to fix slow init on large codebases.
- **Background MCP connections** overlapped with system prompt building.
- The `benches/baseline.json` file is empty ({}), indicating no Criterion benchmarks have been set up yet -- the published numbers are from external hyperfine runs only.

## 4. Trade-offs

### Wins
- **Extreme performance**: 4.3ms startup and 9.4MB RAM is orders of magnitude faster than TypeScript-based agents (Claude Code, Codex, OpenCode). This is the core competitive advantage.
- **True multi-model orchestration**: No other tool lets you bind different models per workflow phase (execution vs reasoning vs critique vs compaction vs vision) within a single session.
- **Agent fleet parallelism**: Rust + Tokio enables launching many concurrent sub-agents with near-zero overhead per agent. No GIL, no sequential queue.
- **Doom-loop detection**: Real cycle-detection with 3-level escalation prevents infinite tool-calling loops without needing manual intervention.
- **Tool schema deferral**: The ToolSearch pattern (deferred tools loaded on-demand) is a practical cost optimization that mirrors Claude Code's approach.
- **Config migration**: Versioned config with automatic migration (v0.1.6+).

### Losses / Limitations
- **Very early stage**: v0.1.8. The CHANGELOG shows rapid iteration with many bug fixes -- this is not yet battle-tested. Key missing features (by admission in ROADMAP.md) likely include production reliability.
- **No Memory/Embedding pipeline**: The codebase has a `memory_consolidation` module but it appears to be basic file-based consolidation, not vector/semantic search (the `opendev-memory` crate documented in CLAUDE.md does not exist in the actual Cargo.toml).
- **DashScope compatibility hack**: DashScope coding endpoint requires a curl subprocess transport because it rejects reqwest (HTTP 405). This is an integration fragility.
- **TOCTOU vulnerability (fixed)**: Changelog v0.1.6 mentions "TOCTOU vulnerability in auth.json creation" -- suggests the auth system needed hardening.
- **Single binary limitation**: Web UI requires a separate `opendev run ui` command rather than being built-in.
- **Dependency on git**: The `git_root()` helper and worktree manager assume a git repository context, potentially limiting use in non-git directories.
- **No Python comparison**: The text claims Python ancestry but the Rust port has diverged significantly. The architecture notes say "Uses composition instead of Python's mixin-based inheritance" -- the original Python code is no longer in the repo.
- **Context compaction is token-estimate-based**: Uses `len()/4` for token counting which is a rough approximation, not an actual tokenizer.

### Complexity Hotspots
- `opendev-runtime/src/runtime/mod.rs` (1044 lines) is the largest single file. The `AgentRuntime::new()` method is a massive constructor that wires up all services, tools, and provider configurations.
- `opendev-http/src/adapted_client.rs` (38,653 bytes) is the largest crate source file -- the provider adaptation layer is inherently complex due to API divergences.
- 30+ tool implementations in `opendev-tools-impl` with substantial test coverage.

## 5. Design Rationale

The design follows several deliberate principles:

1. **"Rust-first for performance"**: The choice of Rust over Python or TypeScript is fundamental to the identity of the project. The README leads with performance benchmarks. Every architectural decision (async I/O, zero-overhead agent spawning, minimal memory footprint) flows from this.

2. **"Configuration over lock-in"**: The 5-slot model binding is a political/architectural stance against vendor lock-in. The docs explicitly contrast with "Claude Code / Codex CLI / Gemini CLI: closed-source tools that lock you into a single provider." The ability to mix-and-match per workflow phase is the unique selling proposition.

3. **"Proactive autonomy"**: The README says "Proactive, not reactive. OpenDev can plan, execute, and iterate autonomously." The design emphasizes autonomous operation (fleet spawning, doom-loop recovery, background agents, session resume) over interactive chatbot-style interaction.

4. **"Compound AI over monolithic"**: Rather than a single large model call, the system decomposes work into typed phases, each handled by an optimal model. This is explicitly framed as a "compound AI system."

5. **"Multiple surfaces for different users"**: TUI for power users, Web UI for visual monitoring (including remote phone access), REPL for scripts, and single-prompt mode for CI.

6. **"Minimal dependency philosophy"**: Despite 21 crates, the dependency tree is relatively lean (reqwest + tokio + ratatui + clap as major deps). No heavy frameworks, no Electron. The README brags about the 18 MB single binary.

7. **"Defense in depth"**: Multiple safety systems: doom-loop detection, tool approval channels, sandbox execution, circuit breakers for HTTP, secret detection/redaction, file checkpoint middleware, permission rule sets.

## 6. Transfer to Lyra

### Transferable Idea: Per-Workflow Model Binding (5-Slot Compound AI System)

The most unique and directly transferable concept in OpenDev is its **per-workflow model routing across 5 independent slots**: Normal, Thinking, Compact, Critique, and VLM. Each slot binds to a different model from a different provider, enabling fine-grained cost-latency-capability trade-offs per phase of the agent loop.

**Apply to Lyra**: Define analogous workflow slots for Lyra's internal agent pipeline:
- **Router slot**: Fast, cheap model for intent classification and routing (e.g., Haiku 4.5)
- **Thinker slot**: Deep reasoning model for planning and complex analysis (e.g., Opus or o3)
- **Compiler slot**: Code generation model optimized for structured output (e.g., Sonnet)
- **Verifier slot**: Different model for cross-checking outputs (reduces correlated errors)
- **Memory slot**: Small model for context compaction and summarization

This maps to Lyra's **Section 4.1 (Router Architecture)** and **Section 4.3 (Agent Orchestration)** routes.

### Workstream Route: Section 4.3 -- Agent Orchestration

The multi-agent fleet spawning and per-workflow model binding directly aligns with Section 4.3 (Agent Orchestration and Coordination). OpenDev's agent manager is already doing what Lyra plans to do: spawn typed sub-agents with independent model bindings, run them concurrently, and converge results.

### Impact / Effort / Tier

| Dimension | Value |
|-----------|-------|
| **Impact** | 8/10 -- Per-workflow model binding is a genuine architectural innovation that no major competitor (Claude Code, Codex, Gemini CLI) offers. Would be a strong differentiator for Lyra. |
| **Effort** | 6/10 -- The provider adapter layer and slot routing are non-trivial to implement. OpenDev's codebase (21 crates, Rust) would need to be adapted to Lyra's architecture. The concept is portable but the implementation is significant. |
| **Tier** | **Platinum** -- This is the kind of architectural feature that would appear in Lyra's README as a "why Lyra is different" bullet point. It is a competitive moat rather than an incremental improvement. |

### LICENSE
MIT License. OpenDev is permissively licensed, so code can be studied freely. However, direct code reuse into Lyra would need to comply with the MIT license (retain copyright notice).

### File Paths
- Main entry: `/crates/opendev-cli/src/main.rs`
- Core runtime: `/crates/opendev-runtime/src/runtime/mod.rs`
- Agent definition: `/crates/opendev-agents/src/main_agent.rs`
- ReAct loop: `/crates/opendev-agents/src/react_loop/execution.rs`
- Doom loop: `/crates/opendev-agents/src/doom_loop.rs`
- Prompt composer: `/crates/opendev-agents/src/prompts/composer.rs`
- Context compaction: `/crates/opendev-context/src/compaction/mod.rs`
- HTTP provider adapters: `/crates/opendev-http/src/adapted_client.rs` + `/crates/opendev-http/src/adapters/`
- Config models: `/crates/opendev-models/src/config/mod.rs`
- Tool registry: `/crates/opendev-tools-core/src/registry.rs`
- README: `/README.md`
- CHANGELOG: `/CHANGELOG.md`
- All benchmarks documented in README table (no Criterion benchmarks in repo yet)
