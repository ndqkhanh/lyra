# graykode/abtop — Deep-Read

## 1. Headline Feature & Mechanism

**abtop is a terminal-based AI agent monitor (like `btop` for htop-like system monitoring, but for AI coding agents).** It discovers, collects, and renders real-time session telemetry from Claude Code, Codex CLI, and OpenCode processes running on the local machine -- all without any API keys or network calls.

The core mechanism is **OS-level process introspection** combined with **transcript file tailing**:

- **Process discovery**: Every 2 seconds, `ps` (or `/proc` on Linux, `sysinfo` on Windows) scans all running processes to find `claude`, `codex`, and `opencode` binaries. Process ancestry is walked via PID/PPID chains.
- **Config root inference**: For Claude Code, open file descriptors (via `lsof` on macOS, `/proc/<pid>/fd` on Linux) are scanned to discover `~/.claude` / `~/.claude-*` config directories that contain both `sessions/` and `projects/` subdirectories -- this handles multi-profile setups transparently.
- **Transcript tailing**: Session metadata (`sessions/{PID}.json`) and transcript JSONL files (`projects/{encoded-cwd}/{sessionId}.jsonl`) are read incrementally: first a full scan for lifetime cumulative token totals, then byte-offset-based incremental reads for real-time updates. File identity checks (inode+mtime) detect file rotation.
- **Rate limit collection**: A `StatusLine` hook script installed via `abtop --setup` intercepts Claude Code's per-response StatusLine JSON payload, extracts rate-limit percentages for the 5-hour and 7-day windows, and writes them to `~/.claude/abtop-rate-limits.json`. abtop reads this file every 10 seconds.
- **Orphan port detection**: Child processes with open listening ports are tracked across ticks. When a parent session dies but the child stays alive and retains its port, abtop flags it as orphaned and offers `X` to kill it -- with safety checks (fresh lsof scan, PID command verification before SIGKILL).
- **Session summarization**: Background threads invoke `claude --print` with the session's first user prompt to generate a 3-5 word title, cached to `~/.cache/abtop/summaries.json` (max 3 concurrent jobs, max 2 retries, 10s timeout).

## 2. Architecture & Core Modules

```
src/
├── main.rs                  # Entry point, CLI flags (--once, --setup, --theme, --update),
│                             #   terminal setup (raw mode, alternate screen), event loop
├── app.rs                   # App state machine: session list, tick orchestration, key handling,
│                             #   kill confirmation with safety checks, tmux session jump,
│                             #   summary generation (background threads via claude --print)
├── config.rs                # TOML config read/write (~/.config/abtop/config.toml):
│                             #   theme, hidden_agents, claude_config_dirs, panel_visibility, language
├── theme.rs                 # 12 built-in themes including 4 colorblind-friendly options,
│                             #   each with ~20 color slots + 5 RGB gradients (101 steps each)
├── setup.rs                 # StatusLine hook installer for rate limit collection
├── locale.rs                # i18n: English + Simplified Chinese (auto-detected from LANG)
├── host_info.rs             # CPU%/MEM%/loadavg sampler (Linux /proc/stat only; None on other platforms)
├── demo.rs                  # Demo data generator for the --demo flag
├── model/
│   ├── mod.rs               # Re-exports
│   └── session.rs           # AgentSession (30+ fields), SessionStatus (6-state enum),
│                             #   ChildProcess, OrphanPort, RateLimitInfo, ToolCall,
│                             #   ChatMessage, FileAccess, SubAgent, SessionFile (JSON deserialize)
├── collector/
│   ├── mod.rs               # MultiCollector: orchestrates 3 agent collectors + port scanning +
│   │                         #   MCP server detection + git stats caching + orphan detection.
│   │                         #   SharedProcessData: single ps/lsof pass shared across collectors.
│   ├── claude.rs            # Claude Code collector (~4000 lines): session discovery, config root
│   │                         #   inference via open fds, transcript JSONL tail parsing with full
│   │                         #   token/context/compaction/tool extraction, /clear sid override,
│   │                         #   subagent discovery, memory status, effort/model config reading
│   ├── codex.rs             # Codex CLI collector: ps + lsof for rollout-*.jsonl discovery,
│   │                         #   JSONL event parsing (session_meta, token_count, agent_message),
│   │                         #   rate limit extraction from token_count events
│   ├── opencode.rs          # OpenCode collector: ps + sqlite3 CLI for DB querying,
│   │                         #   cwd-based PID matching (no PID→session mapping in OpenCode)
│   ├── mcp.rs               # codex mcp-server detection: identify mcp-server PIDs, map open
│   │                         #   rollout file descriptors, track active vs stale threads by mtime
│   ├── process.rs           # Cross-platform process info (Linux /proc, macOS proc_pidinfo,
│   │                         #   Windows sysinfo, fallback ps/lsof), port detection, git stats,
│   │                         #   cmd_has_binary with autoupdater layout support
│   └── rate_limit.rs        # Read Claude Code rate limits from ~/.claude/abtop-rate-limits.json
│                             #   and Codex rate limits from ~/.cache/abtop/codex-rate-limits.json
└── ui/
    ├── mod.rs               # Layout engine, braille sparkline/graph rendering, meter bars,
    │                         #   gradient interpolation, click_target mapping
    ├── header.rs            # 1-row top bar: CPU%, MEM%, load, agent count, avg ctx %
    ├── context.rs           # Token rate braille sparkline (200pt history) + per-session context bars
    ├── quota.rs             # Claude + Codex rate limit gauges (5h + 7d windows, reset countdown)
    ├── tokens.rs            # Selected-session token breakdown (in/out/cache) + per-turn sparkline
    ├── projects.rs          # Per-project git branch + dirty file counts
    ├── ports.rs             # Open ports (agent-spawned) + orphan ports section
    ├── sessions.rs          # Main session list table + selected session detail panel
    ├── mcp.rs               # MCP server panel: parent CLI, profile, active/total rollouts
    ├── config.rs            # Config overlay: theme cycling, panel toggles
    ├── footer.rs            # Bottom status bar with keybinding hints
    ├── help.rs              # Keybindings help overlay
    └── view_menu.rs         # View toggle menu overlay
```

**Data flow**: `main.rs` event loop -> `app::tick()` -> `MultiCollector::collect()` (one `ps` pass shared across 3 collectors) -> transcript parsing -> session list update -> `ui::draw()` renders 7 panels via ratatui. Token rate sparkline computed from per-session deltas. Rate limits polled every 5 ticks (~10s). Git stats cached and refreshed only on slow ticks.

**Platform support**: macOS (proc_pidinfo), Linux (/proc), Windows (sysinfo + netstat), cross-platform fallback (ps + lsof).

## 3. Performance/Benchmarks

The repo does not include published benchmarks, but the architecture makes strong performance commitments:

- **Poll intervals**: Session scan + transcript tail every 2s. Process tree (`ps`) every 2s. Port scan (`lsof`), git status, and rate limits every 10s (every 5th tick). This staggering avoids freezing the TUI.
- **Incremental transcript parsing**: After an initial full scan, only newly appended bytes are parsed via byte-offset tracking. File identity checks (inode+mtime on Unix) detect rotation.
- **GPU-like rendering**: Render interval of 500ms for smooth animations; data collection every 2s. Uses ratatui's incremental rendering.
- **Background summary threads**: Max 3 concurrent `claude --print` invocations with 10s timeout per job, preventing TUI blocking.
- **Background MCP scan**: Desktop app-server rollout scanning runs in a background thread with 60s cache TTL and 90s timeout, avoiding `lsof` latency on the hot path.
- **Port caching**: Port scan results are cached and only refreshed on slow ticks or when the tracked PID set changes (to mitigate `lsof` slowness on macOS with many open fds).
- **Cached git stats**: Only refreshed on slow ticks (~10s); new cwds are computed on demand.
- **Desktop rollout scanner**: Background thread isolates the expensive `lsof`-based Codex Desktop rollout scan from the TUI thread.

## 4. Trade-offs

**Wins:**

- **Zero configuration, zero network**: No API keys, no auth, no server. Works on any machine running Claude Code / Codex / OpenCode.
- **Multi-profile, multi-agent**: Discovers all running AI coding agent sessions regardless of how many profiles or tools are in use, with per-agent-CLI rate limit attribution.
- **Read-only by design**: Never writes to agent state. Cannot cause side effects beyond the explicit kill feature (which has double-confirmation + PID verification).
- **Cross-platform**: Linux, macOS, and Windows native support for all three agent types.
- **Transcript tailing is efficient**: Even 18MB transcript files incur only O(append) read cost after initial load.
- **Security-conscious**: Redacts 16+ secret patterns from displayed text, strips ANSI/bidi overrides (CVE-2021-42574), validates PIDs before kill, uses O_EXCL temp files for update.
- **Accessibility-first**: 12 themes including 4 colorblind-friendly options (protanopia, deuteranopia, tritanopia, high-contrast).
- **Orphan port detection**: Unique value -- no other tool catches agent-spawned servers that survive session death.

**Losses / Limitations:**

- **Status detection is heuristic**: Cannot reliably distinguish model-thinking vs tool-executing vs rate-limit-waiting vs permission-prompt. Uses CPU activity, tool_use presence, and transcript mtime as proxies, all of which can flicker or lag.
- **Context window hardcoded by model name**: Must know the model's window size (200K vs 1M). Will break if Anthropic/OpenAI ship new models without upstream updates.
- **Rate limit requires install step**: Users must run `abtop --setup` to install the StatusLine hook. Rate limits are Pro/Max only.
- **Transcript parsing is fragile**: All JSONL sources are undocumented internal formats. Schema changes (Claude Code, Codex, OpenCode) can break parsing silently.
- **Summary generation uses API**: `claude --print` makes API calls (the only network dependency), adding latency and cost.
- **No Gemini/Cursor support**: Deliberately scoped to Claude Code, Codex CLI, and OpenCode as non-goals.
- **No remote/SSH monitoring**: Entirely local-machine only.
- **`/clear` + multi-PID ambiguity**: After Claude Code's `/clear` command, the stale session file's sid is overridden by picking the newest transcript in the project dir -- but this fails when two `claude` PIDs share a cwd.
- **`/proc` on macOS**: Limited; `KERN_PROCARGS2` truncates environment variables for non-root, so `CLAUDE_CONFIG_DIR` detection from running processes is Linux-only.
- **Host vitals Linux-only**: CPU/MEM/load gauges in the header only work on Linux; macOS and Windows show `--`.

## 5. Design Rationale

The project is explicitly modeled after `btop` (hence the name) and its BSD-licensed C++ source. The README/AGENTS.md documents specific btop-faithful choices:

- **Btop's rendering model**: The braille sparkline, braille area graph, gradient interpolation (101-step linear RGB, start-mid-end), and meter bar rendering all follow `btop_draw.cpp` conventions exactly.
- **Theme system mirrors btop**: The same color slot structure (`main_bg`, `main_fg`, `title`, `hi_fg`, `proc_box`, `cpu_box`, etc.) with the `btop` theme as default. Theme names like `btop`, `dracula`, `catppuccin`, `tokyo-night`, `gruvbox`, `nord` are directly inspired by btop's theme ecosystem.
- **All read-only, no API keys**: The README states this 3 times. Every data source is local: `ps`, `lsof`, `/proc`, JSONL files, SQLite DBs. The only indirect network call is through `claude --print` for summaries.
- **Staggered polling intervals**: Port scanning (`lsof`) is expensive on macOS -- cached for 10s to avoid TUI freezes. Fast polls (2s) for `ps` and transcript tailing are cheap. This mirrors htop/btop's approach to `/proc` vs device I/O.
- **Defensive parsing everywhere**: `serde(default)` on all JSON fields. Undocumented internal formats are expected to change without notice.
- **Session summarization via `claude --print`**: Rather than building a local NLP model, abtop reuses the installed Claude Code binary to generate one-line summaries, with fallback to the raw prompt text.
- **MultiCollector trait**: Clean plugin architecture for adding new agent types. Each collector implements `AgentCollector::collect(shared: &SharedProcessData)` and receives a single `ps` snapshot, avoiding N redundant passes.
- **tmux integration as first-class**: Session jump (`Enter`) maps PIDs to tmux panes through `tmux list-panes -a -F` and walks the process tree. Only works inside tmux but unlocks cross-workspace navigation.

## 6. Transfer to Lyra

**One idea**: **Process-level agent telemetry layer** -- Lyra could adopt abtop's approach of discovering local agent processes (Claude Code, Codex, etc.) via OS introspection (`ps`, `/proc`, file descriptors) and tailing their transcript JSONL files for real-time token usage, context window saturation, rate limit status, and orphan port detection. This would give Lyra a **zero-configuration process monitoring dashboard** that works across any locally-running AI coding agent, without API keys or agent-side modifications.

**Route**: This fits naturally under Lyra's **Layer 4.x (Observability/Monitoring)** workstream, specifically `§4.1 (Agent Runtime Observability)` -- adding a lightweight agent-side telemetry collector that monitors local process state and surfaces it through Lyra's runtime dashboard.

**Impact**: 7/10 (high value for multi-agent workflows; solves a real pain point of running 3+ agents simultaneously across projects)
**Effort**: 5/10 (moderate -- the core cross-platform process discovery and JSONL parsing logic can be adapted, but needs integration with Lyra's existing data model and dashboard)
**Tier**: Tier 2 (enhancement to Lyra's observability capabilities, not a core requirement)

**LICENSE**: MIT (compatible with Lyra's licensing; no restrictions on adaptation)
