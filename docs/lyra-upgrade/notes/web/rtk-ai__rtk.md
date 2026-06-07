# rtk (Rust Token Killer) -- Deep-Read

- Repository: https://github.com/rtk-ai/rtk
- Note date: 2026-06-07
- Version read: v0.42.2

## 1. Headline Feature & Mechanism

**rtk is a high-performance CLI proxy that intercepts shell commands and filters/compresses their outputs before they reach an LLM context, achieving 60-90% token savings.** It is a single Rust binary (~4 MB stripped) supporting 100+ commands across 9 ecosystems (git, Rust, JS/TS, Python, Go, Ruby, .NET, cloud, system).

The mechanism is a command proxy pattern:

1. An LLM agent hook (PreToolUse for Claude Code/Cursor/Copilot, or TS plugin for OpenCode) transparently rewrites commands before execution: `git status` becomes `rtk git status`.
2. RTK's Clap parser routes the command to a specialized filter module in `src/cmds/<ecosystem>/`.
3. The filter executes the underlying command via `std::process::Command`, captures stdout/stderr, and applies compression strategies (regex stripping, JSON parsing, state machine, NDJSON streaming, line deduplication, tree compression).
4. Filtered output is printed; the original output is discarded but optionally saved to a "tee" file on command failure (for LLM re-read).
5. Token savings are tracked in local SQLite (`~/.local/share/rtk/history.db`) using a 4-char ~ 1 token heuristic.

Two filter tiers: **Rust compiled filters** (complex transformations in `src/cmds/`) and **TOML DSL filters** (declarative 8-stage pipeline in `src/filters/*.toml`, loaded at compile time via `build.rs`). If neither matches, the command passes through raw with the exit code preserved.

14 LLM agents are supported: Claude Code, GitHub Copilot (VS Code + CLI), Cursor, Gemini CLI, Codex, Windsurf, Cline/Roo Code, OpenCode, OpenClaw, Pi, Hermes, Kilo Code, Google Antigravity, Mistral Vibe (planned).

## 2. Architecture & Core Modules

### Entry point (`src/main.rs`)
- `Cli` struct with `Commands` enum (~60+ command variants) parsed by Clap derive macros.
- `run_cli()` routes to specialized modules via `match cli.command`.
- `run_fallback()` handles any command not in the enum: checks TOML DSL filters, then pure passthrough.
- Global flags: `-v` (verbosity, 3 levels), `--ultra-compact` (ASCII icons), `--skip-env`.
- SIGPIPE is reset to default handler to avoid crashes on `rtk git log | head`.

### Core infrastructure (`src/core/`)
- **`runner.rs`** -- Shared command execution skeleton. `RunMode` enum: Filtered, FilteredWithExit, Streamed, Passthrough. Automates timer start, execution, filtering, token tracking, and exit code propagation.
- **`filter.rs`** -- Language-aware code filter: `NoFilter`, `MinimalFilter` (strip comments), `AggressiveFilter` (strip function bodies, keep signatures). Supports Rust/Python/JS/TS/Go/C/C++/Java/Ruby/Shell/Data. `smart_truncate()` prioritizes structurally important lines with an end-of-output marker.
- **`tracking.rs`** -- SQLite-backed token tracking. `TimedExecution::start()`/`.track()` pattern. 90-day retention. Project-scoped queries via GLOB matching. Schema: id, timestamp, original_cmd, rtk_cmd, input_tokens, output_tokens, saved_tokens, savings_pct, exec_time_ms, project_path.
- **`toml_filter.rs`** -- Declarative 8-stage filter pipeline: strip_ansi -> regex replace -> match_output (short-circuit) -> strip/keep lines -> truncate lines -> head/tail -> max_lines -> on_empty. Loads from three tiers: built-in (embedded by `build.rs`), global (`~/.config/rtk/filters.toml`), project-local (`.rtk/filters.toml`, trust-gated). 59 built-in filters.
- **`tee.rs`** -- On command failure, saves raw unfiltered output to `~/.local/share/rtk/tee/` so the LLM can re-read without re-executing.
- **`utils.rs`** -- `strip_ansi()`, `truncate()`, `resolved_command()` (PATHEXT-aware on Windows), `ruby_exec()` (auto-detect bundle exec), `package_manager_exec()` (pnpm/yarn/npx).
- **`config.rs`** -- `~/.config/rtk/config.toml` with sections: tracking, display, filters, tee, telemetry, hooks, limits.

### Command filter modules (`src/cmds/`)
Organized by ecosystem, each with a `run()` function following the `runner.rs` pattern:
- **git/** -- git status/diff/log/add/commit/push/pull/branch/fetch/stash/show, gh, glab, gt
- **rust/** -- cargo build/test/clippy/check/install/nextest, generic runner (err/test)
- **js/** -- npm, npx, pnpm, vitest, tsc, lint, next, prettier, playwright, prisma
- **python/** -- ruff, pytest, mypy, pip (auto-detects uv)
- **go/** -- go test/build/vet, golangci-lint
- **ruby/** -- rake, rspec, rubocop
- **dotnet/** -- dotnet build/test/restore/format, binlog, trx
- **cloud/** -- aws, docker/kubectl, curl, wget, psql
- **system/** -- ls, tree, read, grep, find, wc, env, json, log, deps, summary, format, pipe, local_llm

### Hook system (`src/hooks/`)
- **`init.rs`** -- `rtk init` command: writes hook shell scripts, patches `settings.json`, generates RTK.md. Supports all 14 agents.
- **`rewrite_cmd.rs`** -- `rtk rewrite` command: single source of truth for command rewriting (used by hooks).
- **`hook_cmd.rs`** -- Hook processors for Claude/Cursor/Gemini/Copilot JSON protocols.
- **`integrity.rs`** -- SHA-256 hook verification at runtime for security.
- **`trust.rs`** -- Project-local TOML filter trust model (untrusted by default, `rtk trust` to enable).
- **`verify_cmd.rs`** -- `rtk verify` command to run inline TOML filter tests (CI-mode with `--require-all`).
- **`hook_check.rs`** -- 1/day outdated hook warning.
- **`hook_audit_cmd.rs`** -- Hook rewrite audit metrics (requires `RTK_HOOK_AUDIT=1`).

### Analytics (`src/analytics/`)
- `gain.rs` -- `rtk gain` dashboard: daily/weekly/monthly stats, ASCII graph, JSON/csv export, project-scoped.
- `cc_economics.rs` -- Claude Code spending (ccusage) vs RTK savings analysis.
- `session_cmd.rs` -- Session adoption reporting.
- `ccusage.rs` -- Claude Code usage data parsing.

### Discover & Learn (`src/discover/`, `src/learn/`)
- **discover/** -- `rtk discover`: scans Claude Code session history for commands that could benefit from RTK. Includes `lexer.rs` (shell tokenizer), `provider.rs` (session providers), `registry.rs` (command rewrite registry with compound command handling), `rules.rs` (60+ command match patterns).
- **learn/** -- `rtk learn`: detects CLI correction patterns (e.g., a user ran `git puhs` then `git push`) and suggests aliases/rules.

### `build.rs`
Concatenates all `src/filters/*.toml` files into a single `builtin_filters.toml` embedded at compile time via `include_str!`. Also injects the `schema_version = 1` header.

### Build configuration
- **Cargo.toml**: Rust edition 2021, MSRV 1.91. Key deps: clap 4, anyhow, regex, serde_json, rusqlite (bundled), toml, chrono, colored, ureq, sha2, flate2, quick-xml.
- **Release profile**: opt-level=3, LTO, single codegen unit, panic=abort, strip.
- `unsafe_code = "deny"` as a lint (except for two explicit SIGPIPE/SIGTERM signal handlers with `#[allow(unsafe_code)]`).

## 3. Performance/Benchmarks

Measured targets and real numbers from the repo:

| Metric | Target | Verification |
|--------|--------|--------------|
| Startup time | <10 ms | `hyperfine 'rtk git status' 'git status'` |
| Memory usage | <5 MB resident | `/usr/bin/time -v rtk git status` |
| Binary size | <5 MB stripped | `ls -lh target/release/rtk` |
| Token savings | 60-90% per filter | Snapshot + inline token-count tests |

Per-operation overhead from ARCHITECTURE.md:
- `rtk git status`: +8 ms overhead (58 ms total)
- `rtk grep "pattern"`: +12 ms overhead (145 ms total)
- `rtk read file.rs`: +5 ms overhead (15 ms total)
- `rtk lint`: +15 ms overhead (2.5 s total)

Token savings projection (30-min Claude Code session): ~118,000 standard tokens -> ~23,900 RTK tokens (-80%).

Per-filter savings targets (from cli-testing rules): git log 80%+, cargo test 90%+, gh pr view 87%+, pnpm list 70%+, docker ps 60%+.

Overhead sources: Clap parsing ~2-3 ms, command execution ~1-2 ms, filtering/compression ~2-8 ms, SQLite tracking ~1-3 ms.

Achieved through: zero async (no tokio), lazy_static! regex, borrow-over-clone, on-demand config loading (no file I/O on startup).

## 4. Trade-offs

### Wins
- **Massive token savings** (60-90%) directly reduce LLM API costs and extend effective context.
- **Zero-config install**: `brew install rtk && rtk init -g` provides immediate value.
- **Fail-safe design**: If a filter panics or parsing fails, raw command output passes through unchanged. No silent data loss, no command blocking.
- **14 agent integrations** across every major AI coding tool.
- **Comprehensive analytics** (`rtk gain`, `rtk discover`, `rtk learn`, `rtk cc-economics`) that measure and communicate value to the user.
- **TOML DSL filter system** allows non-Rust developers to add filters declaratively with inline tests.
- **Security-first**: Project-local TOML filters are untrusted by default (`rtk trust` required), SHA-256 hook integrity verification, explicit telemetry opt-in (GDPR-compliant).
- **Tee recovery** on failure ensures the LLM can still read full unfiltered output without re-executing the command.

### Loses / Limitations
- **Built-in tools bypass the hook**: Claude Code's `Read`, `Grep`, and `Glob` tools do not pass through the Bash hook, so RTK cannot intercept them. Users must explicitly call `rtk read`, `rtk grep`, or `rtk find`.
- **Not universal**: Many CLI tools lack RTK filters and pass through raw (0% savings). The `rtk discover` command surfaces these opportunities.
- **Windows limitations**: The auto-rewrite hook requires a Unix shell. Native Windows users get only `CLAUDE.md` injection mode (prompt-level guidance, no automatic rewrite).
- **Increased pipeline complexity**: The hook adds a subprocess call (`rtk rewrite`) to every command, and the filter proxies add a second subprocess. For commands with negligible output, this overhead outweighs the token savings.
- **Monorepo tightness**: `main.rs` is ~2600 lines with the Commands enum, all sub-enums, routing, and fallback logic in one file. The ARCHITECTURE.md itself notes the need to extract `cli.rs` and split routing.
- **Name collision on crates.io**: Another project named "rtk" (Rust Type Kit) exists, causing confusion. `rtk gain` serves as a canary (Rust Type Kit doesn't have this command).
- **Agent-specific JSON formats**: Each of the 14 agents has its own JSON hook protocol, requiring separate shell/Rust logic in hooks/.
- **Token estimation is heuristic**: Uses `ceil(chars / 4.0)`, which is a rough approximation. Real token counts depend on the specific LLM tokenizer.

## 5. Design Rationale

**Why Rust?** Performance (~5-15 ms overhead), safety (no null/race bugs), single binary distribution (no runtime deps), cross-platform (macOS/Linux/Windows).

**Why single-threaded/no async?** Async runtimes (tokio, async-std) add 5-10 ms startup time, which is a significant fraction of RTK's <10 ms budget. All I/O is blocking (subprocess execution, SQLite writes). No concurrency benefit for a sequential CLI proxy.

**Why SQLite for analytics?** Zero-config (no server), ~100 KB for 90 days of history, ACID compliant, rich SQL queries for the `rtk gain` dashboard. Bundled via `rusqlite`.

**Why `lazy_static!` for regex?** Compiling a regex in a hot function is expensive. `lazy_static!` compiles once at first use. This is consistent with the performance-first design.

**Why `anyhow` for errors?** `.context()` adds meaningful context at each layer. The `?` operator provides concise propagation. No custom error types needed for a CLI application.

**Why Clap derive?** Less boilerplate than manual parsing, auto-generated `--help`, type-safe argument extraction, global flags that work across all commands.

**Why two filter tiers (Rust + TOML)?** Rust modules handle complex transformations (JSON parsing, state machines, NDJSON streaming) that require imperative logic. TOML DSL handles simpler cases (regex line filtering, truncation) that benefit from declarative configuration -- and can be written by non-Rust contributors.

**Why hook-based interception vs. prompt-level guidance?** Hooks provide transparent, automatic rewrite with zero user effort. The alternative (CLAUD.md instructions asking the agent to use `rtk` prefix) achieves only ~70-85% adoption according to the ARCHITECTURE.md.

## 6. Transfer to Lyra

### Transferable Idea: Declarative TOML-DSL Output Compression Pipeline

RTK's `toml_filter.rs` implements an 8-stage declarative filter pipeline (strip_ansi -> regex replace -> match_output -> strip/keep_lines -> truncate_lines_at -> head/tail_lines -> max_lines -> on_empty) that can be defined in simple TOML config files. This allows non-Rust developers to add support for new CLI tools without modifying the Rust binary. The pipeline includes inline test support (`[[tests.<filter-name>]]`) for regression safety and a trust model (`.rtk/filters.toml` requires `rtk trust`).

Lyra could adopt a similar DSL for its command output post-processing layer -- a plugin system where users (or researchers) can define compact output profiles for arbitrary commands without touching Lyra's core code. The multi-tier loading (built-in -> user-global -> project-local) and inline testing patterns are directly applicable.

### Workstream Route

Route through **Section 4.x: Plugin System** -- Lyra's plugin architecture (brainstorm/07-plugins.md) is the natural home for a TOML-defined filter pipeline. This could be a `plugin` or `transformer` that sits between command execution and output delivery.

### Impact / Effort / Tier

- **Impact**: 7 (high) -- A declarative output compression system would significantly reduce Lyra's token consumption and make the system more cost-effective for long-running research sessions, similar to RTK's effect on Claude Code.
- **Effort**: 5 (medium) -- The TOML filter engine itself is ~700 lines of Rust (parse, compile, apply pipeline). Adapting it to Lyra's plugin system (or embedding it as a Rust dependency) requires integration work, a schema design, and the inline test infrastructure, but the core algorithm is well-defined and battle-tested.
- **Tier**: Tier 2 (strategic feature) -- Not a critical path blocker, but a high-value addition that should follow the core plugin architecture.

### LICENSE

Apache License 2.0. Compatible with Lyra's licensing model. rtk's code (specifically `toml_filter.rs` as a standalone module) can be adapted or ported without license conflicts.
