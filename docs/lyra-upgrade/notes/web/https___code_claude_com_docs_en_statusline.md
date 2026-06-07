# Customize your status line (code.claude.com - Anthropic/Claude Code Docs)

## Key Technical Claims

- The status line is a customizable bar at the bottom of Claude Code that runs any arbitrary shell script you configure, receiving JSON session data on stdin and displaying whatever your script prints to stdout.
- It provides persistent, at-a-glance visibility of context window usage, session costs, git status, PR status, rate limits, vim mode, worktree info, agent names, and session identity.
- The subagentStatusLine setting extends the pattern to render custom row bodies for each subagent shown in the agent panel, with a structured JSON input containing a `tasks` array and a per-row JSON-line output format.
- Updates are event-driven (post-assistant-message, post-compact, permission mode change, vim mode toggle), debounced at 300ms, with in-flight cancellation if a new update triggers while a script is still running.
- The `refreshInterval` option re-runs the command on a fixed timer (minimum 1s) for time-based or externally-sourced data during idle periods (e.g., when a coordinator waits on background subagents).
- Status line runs locally and does not consume API tokens.

## Architecture/Mechanism Details

- **Data flow**: Claude Code pipes a JSON blob to the script via stdin. The script reads, parses, and prints text to stdout. Claude Code renders stdout output in the bottom bar.
- **Input fields**: Provides ~30+ structured fields including `model.{id,display_name}`, `workspace.{current_dir,project_dir,git_worktree,repo.{host,owner,name}}`, `cost.{total_cost_usd,total_duration_ms,total_api_duration_ms,total_lines_added,total_lines_removed}`, `context_window.{total_input_tokens,total_output_tokens,context_window_size,used_percentage,remaining_percentage,current_usage.{input_tokens,output_tokens,cache_creation_input_tokens,cache_read_input_tokens}}`, `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}`, `session_id`, `session_name`, `effort.level`, `thinking.enabled`, `vim.mode`, `agent.name`, `pr.{number,url,review_state}`, `worktree.{name,path,branch,original_cwd,original_branch}`, `version`, `transcript_path`.
- **Output capabilities**: Multiple lines (each `echo`/`print` = separate row), ANSI escape codes for colors, OSC 8 escape sequences for clickable hyperlinks.
- **Terminal sizing**: `COLUMNS` and `LINES` environment variables (set by Claude Code) for width detection inside scripts, since `tput cols` does not work (stdout is captured, not connected directly to terminal).
- **Caching pattern**: Uses `session_id` as a stable-per-session cache key for expensive operations (git status/diff). Cache file: `/tmp/statusline-git-cache-{session_id}` with 5s TTL. Critical insight: cannot use `$$` or `os.getpid()` since those change on every invocation, defeating caching.
- **Subagent panel**: `subagentStatusLine` setting. Input includes base hook fields + `columns` (usable row width) + `tasks` array with `id`, `name`, `type`, `status`, `description`, `label`, `startTime`, `tokenCount`, `tokenSamples`, `cwd`. Output: one JSON line per row in form `{"id": "<task id>", "content": "<row body>"}`. Empty content hides the row; omitted id keeps default rendering.
- **Settings config**: `statusLine.type: "command"`, `statusLine.command` (path or inline shell cmd), `statusLine.padding` (extra horizontal spacing in chars), `statusLine.refreshInterval` (seconds), `statusLine.hideVimModeIndicator` (bool).
- **Troubleshooting**: Requires workspace trust; disabled when `disableAllHooks: true`; debug via `claude --debug`; null fields possible before first API response.

## Numbers & Benchmarks

- Update debounce: 300ms (rapid changes batch together)
- Cache TTL example: 5 seconds (for git status caching)
- Context window default: 200,000 tokens (1,000,000 for extended models)
- Minimum Claude Code version for COLUMNS/LINES support: v2.1.153
- Minimum version for current context window fields (non-cumulative): v2.1.132
- `padding` default: 0 characters
- `refreshInterval` minimum: 1 second
- `used_percentage` formula: input_tokens + cache_creation_input_tokens + cache_read_input_tokens (excludes output_tokens)

## Transfer to Lyra

### One Idea: Agent Status Pipeline (stdin-based JSON instrumentation for operator HUD)

Lyra should implement an equivalent `agentStatusLine` mechanism where its orchestration loop pipes a structured JSON blob (containing current research task, subagent status, memory state, context usage, cumulative cost, git state, and current phase) to a user-configurable script/command. This gives operators a live, customizable heads-up display during long-running research runs -- exactly as Claude Code's status line gives developers live context awareness.

### Workstream Route: §4.3 Observability & Operator Experience

This fits cleanly into Lyra's observability/monitoring workstream. Specific implementation points:

- **§4.3.1 - Agent HUD pipeline**: Define a JSON schema that Lyra's orchestrator emits on each tick (current phase, active subagents with token counts, memory pressure, cost accumulator, git diff state). Pipe this via stdin to a configurable command.
- **§4.3.2 - Subagent panel equivalent**: For Lyra's multi-agent research workflow, implement a `subagentStatusLine`-like mechanism where each subagent row shows name, status (running/waiting/done), token budget used, and last output snippet.
- **§4.3.3 - Cache discipline for expensive probes**: Port the `session_id`-keyed temp-file caching pattern for Lyra's own expensive probes (e.g., ledger diffs, memory index stats) that run on each tick but only need refresh every N seconds.
- **§4.3.4 - Color-coded thresholds**: Adopt the green/yellow/red threshold pattern (green <70%, yellow 70-89%, red >=90%) for Lyra-specific metrics like context pressure, cost budget, and subagent timeout risk.
- **§4.3.5 - Community extensibility**: Like ccstatusline and starship-claude in the Claude Code ecosystem, Lyra could document a public stdin/stdout contract so the community can build custom HUD widgets.
