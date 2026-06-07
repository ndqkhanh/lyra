# SafeRL-Lab/cheetahclaws — Deep-Read

Repository: https://github.com/SafeRL-Lab/cheetahclaws
Deep-read at commit: 99a3b4a (v3.05.82, June 2026)

---

## 1. Headline Feature & Mechanism

**Headline: A Python-native agent harness infrastructure for long-horizon, multi-model, tool-using AI systems.** CheetahClaws is an open-source reimplementation of Claude Code's core agent loop in ~90K lines of readable Python, supporting any LLM provider (Anthropic, OpenAI, Gemini, Kimi, Qwen, Zhipu, DeepSeek, MiniMax, Ollama, LM Studio, custom OpenAI-compatible endpoints). It runs with zero build step (`python cheetahclaws.py`), switches models at runtime via `/model`, and ships a multi-turn tool-use agent loop, two-layer context compression, persistent memory, task dependency graphs, MCP integration, a plugin system, and bridge adapters for Telegram/WeChat/Slack/QQ.

**How the code really works:**

The REPL entry point `cheetahclaws.py::main()` parses CLI args, loads config from `~/.cheetahclaws/config.json`, applies overrides, then enters `repl()`. The REPL reads user input, dispatches slash commands via `handle_slash()` (a dict of 50+ commands), and routes free-form text to `run_query()`, which calls `agent.run()` — a generator function that yields typed event objects.

The agent loop in `agent.py` (777 lines) is the core:
1. Appends the user message to a neutral `AgentState.messages` list.
2. Calls `providers.stream()` — a unified streaming adapter that normalizes all 8+ providers into a single generator yielding `TextChunk`, `ThinkingChunk`, and `AssistantTurn` events.
3. If the assistant's turn contains `tool_calls`, it iterates through them: checks permissions (auto/accept-all/manual/plan modes), executes tools (parallel if concurrent-safe), and appends results to the message list.
4. Each tool result is checked against the context window — if oversized, `auto_fanout` splits it across parallel sub-LLM map calls.
5. Before each API call, `quota.check_quota()` validates token/cost budgets; `compaction.maybe_compact()` triggers two-layer compression at 70% threshold.
6. Loop guards prevent infinite retries (same-call repetition limit=3, consecutive-error limit=5, read-only dedup).

The multi-provider adapter in `providers.py` is the second critical module. It maintains a `PROVIDERS` dict with per-provider configs (API key env var, base URL, context limit, model list). Most providers use the OpenAI-compatible adapter path (unified `messages_to_openai()` converter), while Anthropic uses its native SDK. Cost tables map each model to per-token pricing.

## 2. Architecture & Core Modules

**Entry point:** `cheetahclaws.py` (2082 lines) — REPL, slash command dispatch, permission prompt UI, streaming render.

**Architecture pattern:** Layered event-driven with a monolithic REPL + optional daemon/kernel layers.

```
                     User Input (terminal / bridge / --print)
                             │
                             ▼
  cheetahclaws.py ── repl(), handle_slash(), run_query()
       │
       ▼
  agent.py ── run() generator loop (777 lines)
       │
       ├──► providers.py ── streaming adapter (anthropic + openai-compat, 1621 lines)
       │         PROIVIDERS dict, detect_provider(), stream()
       │
       ├──► context.py ── system prompt assembly (308 lines)
       │         base prompt + env block + memory + tmux/plan fragments
       │
       ├──► tool_registry.py ── ToolDef registry + dispatch (180 lines)
       │         register_tool(), execute_tool(), read-only cache
       │
       ├──► compaction.py ── two-layer compression (393 lines)
       │         snip_old_tool_results() + compact_messages(AI summarize)
       │
       ├──► quota.py + circuit_breaker.py + error_classifier.py
       │         Budget enforcement, fault tolerance, error classification
       │
       ├──► runtime.py ── RuntimeContext per session (147 lines)
       │
       └──► tools/ ── all built-in tools (Read, Write, Edit, Bash, WebFetch, ...)
```

**Core modules breakdown:**

| Module | Role | Lines |
|--------|------|-------|
| `cheetahclaws.py` | REPL loop, slash dispatch, banner, streaming render, permission prompts | 2082 |
| `agent.py` | Multi-turn agent loop generator, tool execution, retry, loop guards | 777 |
| `providers.py` | Multi-provider streaming adapters + cost tables | 1621 |
| `cc_config.py` | Config load/save from `~/.cheetahclaws/config.json` | ~250 |
| `context.py` | System prompt assembly + prompt-injection scanning | 308 |
| `compaction.py` | Token estimation, snip layer, AI summarization layer | 393 |
| `tool_registry.py` | ToolDef registration, schema export, dispatch, output truncation | 180 |
| `runtime.py` | Per-session RuntimeContext (callbacks, state, bridge flags) | 147 |
| `quota.py` | Token/cost budget enforcement (session + daily) | ~250 |
| `circuit_breaker.py` | Per-provider circuit breaker (CLOSED/OPEN/HALF_OPEN) | ~130 |
| `bootstrap.py` | Startup sequence (logging, tool registry, health server) | ~80 |

**Package ecosystem:**

- `tools/` — 11 files: fs.py, shell.py, web.py, notebook.py, diagnostics.py, etc.
- `commands/` — slash command handlers (core, config, session, advanced, checkpoint, agent, monitor, research, lab, theme, daemon)
- `bridges/` — Telegram, WeChat, Slack, QQ adapters
- `ui/` — Terminal rendering (input.py + render.py with Rich Markdown streaming)
- `web/` — Optional web UI (vanilla JS, no build step)
- `memory/` — Persistent dual-scope memory (user + project)
- `multi_agent/` — Sub-agent spawning with depth gating and worktree isolation
- `task/` — In-session task list with dependency edges
- `checkpoint/` — Auto-snapshot of conversation + file state
- `skill/` — Markdown skill templates
- `cc_mcp/` — MCP client (stdio/SSE/HTTP JSON-RPC)
- `plugin/` — Plugin install from git URLs
- `modular/` — Optional feature modules (voice, video, trading)
- `research/` — Multi-source research pipeline (20 sources)
- `cc_daemon/` — Long-running daemon (server, bridges, scheduler)
- `cc_kernel/` — Agent OS layer (process table, capability model, scheduler, VFS)
- `prompts/` — System-prompt Markdown assets (base + overlays + fragments)

**Data flow:** Messages use a neutral (provider-independent) format in `AgentState.messages`. On each API call, `providers.py` converts to provider-specific format (Anthropic's content blocks or OpenAI's chat format). Tool call IDs, names, and inputs are stored in a tool-agnostic dict and consumed by `tool_registry.execute_tool()`.

**Optional kernel layer (`cc_kernel/`):** A single-node agent OS with SQLite-backed process table, capability model, resource ledger, scheduler, mailbox/registry, virtual filesystem, and Prometheus observability. Activated via `--enable-kernel` flag.

## 3. Performance / Benchmarks

CheetahClaws does not publish GAIA, SWE-bench, or AgentBench scores. The project's value proposition is architectural, not competitive benchmarking. Quantified claims from the repo:

- **~90K lines of core Python** (~127K with tests), 315 source files — compared to Claude Code's ~283K lines across ~1,332 TypeScript files.
- **Agent loop in one file** (`agent.py`, 777 lines) — entire multi-turn tool-use loop visible in one reading.
- **Zero build step** — `pip install -r requirements.txt && python cheetahclaws.py`.
- **27 built-in tools** (compared to Claude Code's 44+); 50+ slash commands.
- **8+ provider adapters** in a single `providers.py` file (1621 lines).
- **2347 tests green** as of the May 2026 security hardening round (133 test files).
- **341+ minimal test suite** (`pytest tests/ -x -q`).
- **Context windows:** 200K (Claude), 128K (OpenAI/DeepSeek), 1-2M (Gemini/Qwen/MiniMax), 128K (Ollama).
- **Token estimation:** `chars/2.8 + 4 tokens/msg framing + 10% buffer` heuristic.
- **Compaction threshold:** 70% of context window triggers two-layer compression.
- **Output truncation:** 32K char cap (model-aware: min(30K tokens - 16K reserve, 32K chars)).
- **Cache TTLs:** Git info cached 30s, CLAUDE.md cached 10s.
- **Circuit breaker defaults:** 5 failures in 60s window, 120s cooldown.

## 4. Trade-offs (wins vs. loses)

**Wins:**
- **Multi-provider flexibility.** Any model at runtime with `/model`, including local/offline (Ollama, vLLM, LM Studio). Claude Code is Anthropic-only.
- **Hackability.** Complete agent loop in 777 lines of Python. Any Python developer can fork and extend in minutes vs. Claude Code's compiled ~12 MB TypeScript bundle.
- **Zero build.** Changes take effect immediately — no Bun/esbuild pipeline.
- **Dynamic extensibility.** Runtime `register_tool()`, MCP servers, git plugins, Markdown skills. Claude Code's tool set is compile-time locked.
- **Two-layer context compression.** Rule-based snip + LLM summarize, with auto-fanout for oversized tool results — critical for small-context local models.
- **Built-in bridges.** Telegram, WeChat, Slack, QQ without external daemons.
- **Budget enforcement.** Pre-call token/cost projection prevents bill shock; auto-saves on quota hit.
- **Rich feature surface:** Trading agent, 20-source research, video/TTS factory, brainstorm debate, SSJ power menu.

**Loses:**
- **No published benchmark scores** (GAIA, SWE-bench, Tau-Bench). Cannot claim parity with Claude Code on task completion.
- **Smaller tool surface.** 27 built-in tools vs. Claude Code's 44+; no `RemoteTrigger`, `EnterWorktree`, etc.
- **No enterprise features** (MDM, team permissions, OAuth, keychain).
- **No AI-driven memory extraction** — Claude Code proactively extracts memories; CheetahClaws requires explicit `/memory consolidate`.
- **React/Ink UI quality.** Claude Code's terminal UI is richer (component tree, streaming rendering, fine-grained diff visualization).
- **Python overhead.** For very large codebases, Python's startup time and per-tool overhead exceed Node.js.
- **Bridge completeness.** Only 4 messaging bridges vs. OpenClaw's 20+.
- **Single-binary distribution.** Claude Code ships as a compiled `cli.js`; CheetahClaws needs Python runtime and pip dependencies.
- **cc_kernel is opt-in.** The agent OS layer is dormant without `--enable-kernel`; the default path is a single-process REPL with no multi-agent concurrency.
- **Token estimation heuristic.** `chars/2.8` is an approximation — can over-count CJK and under-count code tokens.

**Known limitations (from code comments and design documents):**
- Tool-calling compatibility varies by provider; Ollama models need specific function-calling models (qwen2.5-coder, llama3.3, mistral, phi4).
- Loop guard triggers on Gemma 4 + vLLM (hermes parser eats tool call args).
- Windows only supported via WSL2; native Windows is not supported.
- Xiaohongshu research source is brittle (aggressive anti-bot, cookies expire hourly).
- Agent stagnation detection (same-summary limit=3) can false-positive on slowly-progressing multi-day work.
- No cross-process locking for quota counters.
- cc_kernel RFCs are all shipped but the kernel is still additive/opt-in.

## 5. Design Rationale

CheetahClaws was created because Claude Code is a compiled, closed-source TypeScript/Node.js bundle (~283K lines, ~1,332 files) tightly coupled to the Anthropic API. The project's core thesis: **an agent harness should be readable, swappable, and extensible without a build chain.**

Key design decisions:

1. **Python over TypeScript.** Python is more widely readable, has no build step, and has the richest ecosystem for local AI/ML (Ollama bindings, Whisper, numpy, etc.). The sacrifice is runtime performance and single-binary distribution.

2. **Neutral message format.** All conversation history is stored in a provider-agnostic format. `providers.py` handles the conversion to Anthropic/OpenAI-specific formats at API call time. This is the linchpin of multi-provider support — adding a new provider requires only a new entry in `PROVIDERS` and possibly a new `stream_*()` function.

3. **Generator-based agent loop.** Rather than a framework with abstract base classes, CheetahClaws uses a single `run()` generator that yields typed event objects (`TextChunk`, `ToolStart`, `ToolEnd`, `PermissionRequest`, `TurnDone`, `QuotaPause`). The REPL consumes these events for rendering; bridges consume them for streaming; the generator pattern keeps the loop testable and composeable.

4. **Two-layer compression before API call.** Unlike systems that just truncate, CheetahClaws first snips old tool results (rule-based), then falls back to LLM summarization. The compaction triggers at 70% context window usage, before the API would reject an oversized prompt. Critical for local models with small (32K) context windows.

5. **Auto-fanout as context overflow prevention.** When a single tool output (e.g., Read on a 6.6 MB PDF) exceeds 40% of the context window, it's split across parallel sub-LLM summaries. This prevents one oversize tool result from making the next API call uncallable.

6. **RuntimeContext per session.** Bridge connections, proactive timers, and the REPL each own a `RuntimeContext` keyed by `session_id`. This prevents concurrent sessions (chat UI + Telegram bridge) from corrupting each other's callbacks and agent state.

7. **cc_kernel is additive.** The agent OS layer is gated behind `--enable-kernel` — zero change to the single-user REPL path. This avoids destabilizing the core while shipping multi-agent isolation, capability checks, and observability.

8. **Circular import discipline.** Dependencies flow downward: `tools/` never imports `agent.py` or `cheetahclaws.py`. Cross-package references (e.g., `multi_agent.subagent` calling back into `agent.run()`) use lazy imports inside functions.

9. **Notebook editing without a kernel.** `NotebookEdit` directly manipulates `.ipynb` JSON (replace/insert/delete cells) via the `NotebookEdit` tool — no Jupyter kernel required. Design decision from comparing against Claude Code's Read/Write on `.ipynb` files.

10. **Diagnostics without LSP server.** `GetDiagnostics` chains pyright, mypy, flake8, py_compile (Python) and tsc/shellcheck (other languages) — all discovered from PATH. Zero configuration, no LSP protocol overhead.

## 6. Transfer to Lyra

**Best transferable idea: Two-layer context compression with auto-fanout for oversized tool outputs.**

CheetahClaws' compaction pipeline is directly relevant to Lyra's context management challenge. The key insight is that context pressure comes from two sources — accumulated conversation history AND individual oversized tool outputs (reading large files, web fetch results). The repo solves both:

1. **Layer 1 (snip):** Old tool results are truncated to `max_chars` (default 2000) keeping first half + last quarter, preserving the last N turns untouched.
2. **Layer 2 (AI summarize):** When a conversation exceeds 70% of the model's context window, an auxiliary LLM call summarizes old messages.
3. **Auto-fanout:** Tool outputs exceeding 40% of context window are split into chunks, summarized in parallel by sub-LLM calls (default cap 5), then merged with one reduce call.

For Lyra, this pattern solves the problem of context-window pressure from large tool results — an issue we face in §4 Context Management. The auto-fanout mechanism is particularly valuable because it handles the "model reads a huge file then has no room to think about it" failure mode.

**Additional transferable patterns:**
- **Pre-call budget projection** (`quota.py`): project the next request's input + output cost before making the billable API call. Clamp `max_tokens` to remaining budget headroom. Auto-save on quota hit.
- **RuntimeContext per-session** (`runtime.py`): isolate bridge callbacks, agent state, and streaming hooks per session ID — prevents cross-session corruption in multi-user or bridge deployments.
- **Loop guards**: repetition limit (3x same tool call) + consecutive-error limit (5x errors) → break instead of burning tokens on stuck agents.
- **Read-only tool result cache**: LRU cache (64 entries) keyed by `(tool_name, params_hash, session_id)` — identical Read/Glob calls in the same turn short-circuit and show a dedup notice.

**Workstream route:** §4.3 Context Management — the two-layer compaction + auto-fanout pattern directly addresses Lyra's need to manage context window pressure from long conversations and large tool outputs.

**Impact:** 6/10 — Solves a real problem (context overflow from tool results) with a proven, low-complexity approach. Auto-fanout is particularly well-suited to Lyra's multi-turn research workflows where tool outputs (web fetches, file reads) routinely exceed context windows.

**Effort:** 3/10 — Adapting the snip + fanout logic from `compaction.py` and `multi_agent/fanout.py` to Lyra's message format. The core algorithms are ~200 lines and provider-independent.

**Tier:** II — High-impact, moderate-effort integration. Should follow basic context management work (Tier I).

**License:** Apache 2.0 — Compatible with Lyra's licensing. Attribution required.
