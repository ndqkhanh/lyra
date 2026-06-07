# nousresearch/hermes-agent -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline Feature:** A self-improving AI agent with a closed learning loop -- creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations (FTS5), and builds a deepening user model across sessions. Runs on a $5 VPS or a GPU cluster, with six terminal backends (local, Docker, SSH, Singularity, Modal, Daytona) and 15+ messaging platforms.

**How the code really works (the agent loop):**

The core agent loop lives in `agent/conversation_loop.py` (extracted from the ~5,271-line `run_agent.py`). It is an entirely synchronous, blocking loop:

```
while (api_call_count < max_iterations and budget.remaining > 0) or grace_call:
    if interrupt_requested: break
    response = client.chat.completions.create(model=model, messages=messages, tools=tool_schemas)
    if response.tool_calls:
        for tc in response.tool_calls:
            result = handle_function_call(tc.name, tc.args, task_id)
            messages.append(tool_result_message(result))
        api_call_count++
    else:
        return response.content
```

The AIAgent class (`run_agent.py`) is a ~60-parameter constructor (model routing, credentials, callbacks, session context, fallback chains, credential pools, checkpoint config) forwarded to `agent/agent_init.py`. Agent init resolves provider type, fetches model metadata, builds the context compressor, sets up the memory manager, configures tool guardrails, and initializes the credential pool.

The **closed learning loop** works via three post-turn hooks:
1. **Background memory/skill review** (`agent/background_review.py`) -- spawned as a daemon thread after each turn; uses a cheap auxiliary LLM to evaluate whether the conversation produced knowledge worth persisting as MEMORY.md or SKILL.md entries.
2. **Curator** (`agent/curator.py`) -- periodic background system that tracks skill usage (sidecar `~/.hermes/skills/.usage.json`), auto-archives stale agent-created skills, and never deletes (max destructive action: archive to `.archive/`).
3. **Trajectory compression** (`trajectory_compressor.py`) -- post-processes completed agent trajectories for RL training: protects first/last turns, compresses middle turns, replaces compressed regions with human summaries.

Tool discovery is automatic: `tools/registry.py` scans every `tools/*.py` file; each tool calls `registry.register(...)` at import time with schema, handler, check_fn. Toolsets in `toolsets.py` group tools (web, file, terminal, browser, skills, etc.) and platforms inherit from `_HERMES_CORE_TOOLS`. Lazy dependency installation (`tools/lazy_deps.py`) means provider SDKs (anthropic, exa, firecrawl, fal, etc.) are only pip-installed at first use -- tight blast radius for supply-chain attacks.

## 2. Architecture & Core Modules

```
hermes-agent/
  run_agent.py              -- AIAgent class (~5,271 LOC), core conversation loop
  model_tools.py            -- Tool orchestration: get_tool_definitions(), handle_function_call()
  toolsets.py               -- Toolset definitions: _HERMES_CORE_TOOLS + TOOLSETS dict
  cli.py                    -- HermesCLI interactive CLI (~11k LOC, prompt_toolkit + Rich)
  hermes_state.py           -- SessionDB: SQLite + FTS5 + FTS5_trigram for CJK search
  hermes_constants.py       -- Profile-aware path resolution (get_hermes_home())
  hermes_logging.py         -- Rotating file logging (agent.log, errors.log, gateway.log)
  batch_runner.py           -- Parallel trajectory batch processing
  trajectory_compressor.py  -- Post-hoc trajectory compression for RL training data
  mini_swe_runner.py        -- SWE-bench style evaluation runner
  agent/                    -- 80+ modules: agent_init, conversation_loop, memory_manager,
                               context_compressor, prompt_builder, system_prompt, tool_guardrails,
                               background_review, curator, credential_pool, skill_commands,
                               model_metadata, error_classifier, retry_utils, streaming, ...
  hermes_cli/               -- CLI subcommands (100+ files): main, config, models, plugins,
                               gateway, cron, profiles, skills_hub, skin_engine, ...
  tools/                    -- 70+ tool implementations, auto-discovered via registry
    environments/           -- 6 terminal backends: local, docker, ssh, modal, daytona, singularity
  gateway/                  -- Messaging gateway runner + 15+ platform adapters
    platforms/              -- telegram, discord, slack, whatsapp, signal, matrix, email,
                               wecom, weixin, dingtalk, feishu, qqbot, bluebubbles, webhook, sms
  plugins/                  -- Plugin directories: memory/, context_engine/, model-providers/,
                               image_gen/, kanban/, observability/, disk-cleanup, ...
  skills/                   -- Bundled skills (category-organized)
  optional-skills/          -- Niche/heavy skills shipped but not active by default
  cron/                     -- Scheduler (jobs.py + scheduler.py)
  acp_adapter/              -- ACP server for IDE integration (VS Code, Zed, JetBrains)
  ui-tui/                   -- Ink (React) terminal UI
  tui_gateway/              -- Python JSON-RPC backend for TUI
  tests/                    -- ~17,000 tests across ~900 files

Data flow:
  Entry: `hermes` (CLI) or `hermes gateway start` (messaging) or `hermes-acp` (IDE)
    -> cli.py HermesCLI / gateway/run.py GatewayRunner / acp_adapter
    -> AIAgent.__init__() -> agent_init.init_agent()
    -> agent/conversation_loop.py::run_conversation()
    -> model_tools.get_tool_definitions() (tools/registry auto-discovery)
    -> tool dispatch via handle_function_call()
    -> Post-turn: memory_manager.sync_all(), background_review, trajectory persistence
```

**Architecture Pattern:** Plugin-based monolithic agent with layered provider abstraction. The AIAgent is the central orchestrator; every subsystem (tools, memory, models, messaging, skills, cron) connects through it. No microservices -- one process does everything. Provider backends (model providers, terminal backends, memory providers, image-gen) are all pluggable via plugin directories or env-based configuration.

**Key design choices visible in code:**
- All deps exact-pinned (`==X.Y.Z`) for supply-chain security (post-Mini-Shai-Hulud worm response, May 2026)
- Provider SDKs are lazy-installed via `tools/lazy_deps.py` -- not in `[all]` extra
- WAL mode SQLite with application-level jitter retry for write contention
- Profile isolation via `HERMES_HOME` -- every get_hermes_home() call is profile-aware
- Record factory pattern for thread-local session context in logging
- FTS5 + trigram tokenizer for CJK substring search in session history
- Credential pool rotation with per-entry cooldown and exhaustion tracking

## 3. Performance/Benchmarks

The repo does **not** publish benchmark results in its README or AGENTS.md. Key scale metrics extracted from the codebase documentation:

- **Test suite:** ~17,000 tests across ~900 files (as of May 2026); runs in ~30s wall time on 20-core box via xdist + subprocess-per-test isolation
- **Test isolation:** Every test runs in a freshly spawned Python subprocess (`multiprocessing spawn context`), ~0.5-1.0s overhead per test
- **Session DB:** FTS5 full-text search across all session messages; trigram variant for CJK; dual indexes (standard + trigram) maintained via SQL triggers
- **Tool count:** ~70 core tools across ~20 toolsets
- **Cache:** LRU AIAgent cache capped at 128 entries with 1-hour idle TTL in gateway mode
- **Parallel tool execution:** Up to 8 concurrent tool workers (`_MAX_TOOL_WORKERS = 8`)
- **Write throughput:** SessionDB uses BEGIN IMMEDIATE with jitter retry (20-150ms random backoff, 15 max retries), passive WAL checkpoint every 50 writes
- **Dependency footprint:** Core `dependencies` list is deliberately small (15 packages) -- everything else lazy-installed

## 4. Trade-offs

**Wins:**
- **Self-improving loop that actually ships.** The combination of background memory review + skill curation + periodic nudge is one of the few implementations that works in production, not just a paper sketch. The curator automatically maintains skill health without user intervention.
- **Runs anywhere.** Six terminal backends + 15+ messaging platforms + IDE adapters mean the agent goes where the user is, not where the laptop is. Serverless backends (Modal, Daytona) hibernate when idle.
- **Supply-chain resilience.** Exact-pinned deps + lazy installation of provider SDKs means a single quarantined PyPI release cannot break every install. This is a production-hardened posture uncommon in OSS agent projects.
- **Profiles for multi-instance.** Complete isolation via HERMES_HOME scoping -- each profile gets its own config, skills, sessions, gateway, even subprocess HOME. This enables kanban-style multi-agent work on one machine.
- **Plugin system that actually works.** Three distinct plugin surfaces (general, memory, model-providers) with lifecycle hooks, CLI command injection, and tool registration -- without modifying core files.

**Loses:**
- **Monolithic single-process architecture.** AIAgent is a ~60-parameter god object. The conversation_loop is ~3,900 lines. run_agent.py is ~5,200 lines. This makes reasoning about state and concurrency difficult -- evidenced by the compression lock for session_id races.
- **Synchronous blocking loop.** The core conversation loop does not use asyncio for the LLM calls (it uses synchronous OpenAI SDK calls). Async appears only in tool handlers and the gateway layer. This limits throughput and makes cancellation more complex (interrupt checks via a flag).
- **Python supply-chain surface area.** Despite the pinning policy, Hermes depends on ~15 core packages + lazy-installed providers, each of which pulls transitive dependencies. The uv.lock file is likely thousands of entries.
- **Test suite overhead.** Subprocess-per-test isolation (0.5-1.0s per test) means the ~17,000-test suite is not "quick red-green-refactor" friendly for TDD.
- **No sandboxed code execution security.** The terminal tool runs subprocesses in the user's environment (Docker and SSH backends provide some isolation, but the code_execution_tool runs Python inline). The tool guardrails system is prompt-based, not kernel-level.

**Known limitations from code documentation:**
- WAL journal_mode fails on NFS/SMB/FUSE -- falls back to DELETE mode with reduced concurrency
- Native Windows TUI dashboard (PTY) requires WSL2 for the POSIX PTY
- `terminal_cwd` env var deprecated in favor of config.yaml
- Compression lock system needed to prevent parent-session race between two concurrent compress() calls
- Mistralai PyPI supply-chain incident (Mini Shai-Hulud worm, May 2026) drove the exact-pin policy

## 5. Design Rationale

**Why a monolithic synchronous agent loop?** The README and AGENTS.md make clear that simplicity and debuggability were prioritized over throughput. A single-threaded loop with explicit interrupt checks means the agent's behavior is deterministic and reproducible -- critical for debugging tool-calling pipelines and for trajectory-based RL training.

**Why SQLite instead of a vector DB for session search?** Pragmatism. FTS5 is zero-infrastructure, works on any filesystem (with WAL fallback), and provides good-enough text search for session recall. The trigram tokenizer extension for CJK text avoids the complexity of running a separate search service. The entire memory/session system runs out of process without any external dependencies.

**Why exact pinning instead of semver ranges?** The Mini Shai-Hulud worm incident (May 2026) where a malicious `mistralai 2.4.6` release on PyPI would have been auto-installed by any `mistralai>=2.3.0,<3` range. Exact pins mean the only way a new package version reaches a user is via an intentional bump-and-lock. This is defense-in-depth for supply-chain attacks.

**Why profiles over containers for isolation?** Profiles are lighter than Docker containers for multi-instance use. Each profile gets its own `HERMES_HOME` directory, separate config/keys/skills/sessions, and optionally its own `home/` subdirectory for subprocess tools. Gateway platform adapters use token locks to prevent credential conflicts across profiles.

**Why a background thread for memory review instead of inline?** Non-blocking. The AIAgent has a one-turn grace call budget; a synchronous memory review would consume that budget and make every user turn slower. By spawning a daemon thread with a cheap auxiliary LLM, the memory review is eventually consistent without affecting interactive latency.

**Why not publish benchmarks?** The project is positioned as a practical agent framework, not a research benchmark. The focus is on breadth of integrations (200+ models, 15+ platforms, 70+ tools) and production reliability (test isolation, supply-chain hardening, WAL fallback, profile isolation) rather than maximizing a single score.

## 6. Transfer to Lyra

**One idea: The closed skill-creation-and-curation loop.**

Hermes Agent's most transferable mechanism is its post-turn background review thread (`agent/background_review.py`) + curator (`agent/curator.py`) pipeline. After each agent turn, a cheap auxiliary LLM evaluates whether the conversation produced reusable knowledge. If yes, it writes a MEMORY.md or SKILL.md entry. The curator periodically reviews all agent-created skills, tracks usage metrics, auto-archives stale ones, and never deletes (max: archive to `.archive/`).

For Lyra, this means: instead of a static memory system where the user must manually curate knowledge, implement a **post-turn background evaluator** that:
1. Runs on a daemon thread after each successful agent turn
2. Uses a cheap/fast model (not the main conversation model) to score the turn for knowledge-worthiness
3. If score exceeds threshold, writes a structured knowledge entry (memory/skill/recipe) with provenance metadata
4. A periodic curator pass reviews all auto-generated entries, de-duplicates, re-ranks by access frequency, and archives stale entries

This directly addresses Lyra's challenge of making agent knowledge persistent and self-maintaining without user overhead.

**Workstream Route:** This maps to the **memory/routines/context** workstream (Section 4.3 in the Lyra upgrade plan -- knowledge persistence and cross-session learning).

**Impact:** 8/10 -- Directly enables Lyra agents to learn from experience and compound knowledge across sessions, which is a force multiplier for every downstream capability.

**Effort:** 5/10 -- Medium. Requires a background review LLM integration, a structured knowledge format, and a curator pass. But the core pattern (daemon thread post-turn, auxiliary LLM scoring) is straightforward. The hard part is the curation policy (what to keep, what to archive, when).

**Tier:** 2 (High-impact, Medium-effort) -- Ideal for the next planning cycle after foundational tool-calling and memory are stable.

**LICENSE:** MIT -- fully compatible with Lyra's use. No copyleft restrictions, no patent clauses.
