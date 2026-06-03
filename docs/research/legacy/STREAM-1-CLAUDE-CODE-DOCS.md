# Stream 1: Claude Code Documentation Research

> **Purpose**: Extract portable features, APIs, UX patterns, and architecture decisions from Claude Code's official docs for Lyra (MIT-licensed terminal-based multi-agent AI system).
> **Date**: 2026-05-30
> **Status**: COMPLETE

---

## Priority Ranking Legend

| Tier | Meaning |
|------|---------|
| S (Breakthrough) | Game-changing, high-impact x reasonable-effort. Implement first. |
| A (High) | High impact, moderate-high effort. Core differentiator. |
| B (Medium) | Solid improvement, moderate effort. |
| C (Low) | Nice-to-have, high effort for marginal gain. |

---

## 1. Plugins Reference (plugins-reference)

**URL**: https://code.claude.com/docs/en/plugins-reference
**Relevance**: CRITICAL — This is Lyra's core differentiator as an extensible platform.

### Architecture Overview

A plugin is a **self-contained directory** of components that extends Claude Code with custom functionality. Components include: skills, agents, hooks, MCP servers, LSP servers, and monitors.

```
plugin-root/
  plugin.json          # Manifest
  SKILL.md             # Single root-level skill (optional)
  skills/              # Multiple skills as directories
    pdf-processor/
      SKILL.md
      reference.md
      scripts/
  agents/              # Custom subagent definitions (markdown files)
  hooks/
    hooks.json         # Hook definitions scoped to plugin
  .mcp.json            # MCP server configurations
  monitors/            # Auto-started background monitors
```

### Component Types (All Portable to Lyra)

1. **Skills** (`skills/` or `commands/`): Markdown files or directories with `SKILL.md`. Auto-discovered on install. Claude invokes them automatically based on task context. Skills can include supporting files (reference.md, scripts).

2. **Agents** (`agents/`): Markdown files describing agent capabilities. Custom subagents for specialized tasks, invoked automatically when appropriate.

3. **Hooks** (`hooks/hooks.json`): Structured hook definitions that execute at lifecycle points. Plugins ship hooks that auto-activate when the plugin is enabled.

4. **MCP Servers** (`.mcp.json` at plugin root OR inline in `plugin.json`): Bundle MCP servers that start automatically when the plugin is enabled. Supports stdio, HTTP, SSE, WebSocket transports. Uses `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` path placeholders.

5. **LSP Servers**: Plugins bundle language server configurations for code intelligence (definitions, references, diagnostics).

6. **Monitors**: Background watchers that start automatically when the plugin is active. Watch logs, poll PRs, track file changes.

### Plugin Lifecycle

- Install: `/plugin install name@marketplace`
- Enable/disable: runtime via `/reload-plugins`
- Uninstall: removes the plugin directory
- Marketplaces: GitHub repositories with curated plugin catalogs
- Managed marketplace restrictions: `blockedMarketplaces`, `strictKnownMarketplaces` for enterprise control

### CLI Commands for Plugins

```
/plugin install <name>[@<marketplace>]
/plugin marketplace add <url>
/plugin marketplace list
/plugin list
/plugin uninstall <name>
/plugin update <name>
/reload-plugins
```

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Plugin manifest with component directories | S | Trivially portable; defines the extensibility boundary |
| Skill-as-directory with SKILL.md + assets | S | Clean pattern; Lyra can extend with WASM components |
| Agent definitions in plugins | A | Enables community-contributed worker types |
| Hook bundles (`hooks/hooks.json`) | A | Plugins need lifecycle hooks to integrate properly |
| Plugin MCP servers auto-started on enable | A | Key for zero-config tool integration |
| Plugin scope/user separation (~/.claude vs .claude/) | B | Scope hierarchy already understood |
| Persistent data dir (survives updates) | B | `${CLAUDE_PLUGIN_DATA}` pattern is essential |
| Enterprise managed plugin policies | C | Wait for enterprise adoption |
| Plugin marketplace (git-based) | A | Simple: GitHub repos as marketplaces works well |
| LSP integration via plugins | B | Well-understood; wrap in plugin for distribution |

---

## 2. Tools Reference (tools-reference)

**URL**: https://code.claude.com/docs/en/tools-reference
**Relevance**: HIGH — Defines the agent's capability surface.

### Complete Tool Catalog (34 tools)

| Tool | Permission | Portable? | Notes |
|------|-----------|-----------|-------|
| `Agent` | No | S-tier | Subagent spawning with isolated context |
| `AskUserQuestion` | No | A | Multi-choice user prompts |
| `Bash` | Yes | S-tier | Shell execution with timeout, output limits, background mode |
| `CronCreate/Delete/List` | No | B | Session-scoped scheduled tasks |
| `Edit` | Yes | S-tier | Exact string replacement (read-before-edit, uniqueness check) |
| `EnterPlanMode` | No | B | Plan-before-code mode |
| `EnterWorktree` | No | B | Git worktree isolation |
| `ExitPlanMode` | Yes | B | Plan approval gate |
| `ExitWorktree` | No | B | Worktree cleanup |
| `Glob` | No | A | File pattern matching with ** support |
| `Grep` | No | A | ripgrep-based content search, respects .gitignore |
| `ListMcpResourcesTool` | No | A | MCP resource discovery |
| `LSP` | No | A | Code intelligence (definitions, references, diagnostics) |
| `Monitor` | Yes | A | Background process watching with event feed |
| `NotebookEdit` | Yes | C | Jupyter notebook cell editing |
| `PowerShell` | Yes | C | Windows-native shell |
| `PushNotification` | No | B | Desktop + phone notifications |
| `Read` | No | S-tier | File reading with image/PDF/notebook support |
| `ReadMcpResourceTool` | No | A | MCP resource by URI |
| `RemoteTrigger` | No | C | claude.ai routines (Anthropic-specific) |
| `ScheduleWakeup` | No | C | Self-paced loop interval |
| `SendMessage` | No | A | Agent team inter-agent messaging |
| `ShareOnboardingGuide` | Yes | C | Anthropic-specific |
| `Skill` | Yes | S-tier | Invoke skills in main conversation |
| `TaskCreate/Get/List/Stop/Update` | No | A | Task tracking system |
| `TeamCreate/Delete` | No | A | Agent team lifecycle |
| `TodoWrite` | No | C | Legacy task list (deprecated) |
| `ToolSearch` | No | A | Lazy MCP tool loading |
| `WaitForMcpServers` | No | B | MCP readiness check |
| `WebFetch` | Yes | A | URL fetch with extraction prompt |
| `WebSearch` | Yes | A | Web search with domain filtering |
| `Workflow` | Yes | A | Dynamic multi-subagent orchestration script |
| `Write` | Yes | S-tier | Full file write/create |

### Tool Design Patterns

**Permission rules**: `ToolName(specifier)` format:
- `Bash(npm run *)` — command pattern matching
- `Read(~/secrets/**)` — path pattern matching (gitignore syntax)
- `WebFetch(domain:example.com)` — domain matching
- `Agent(Explore)` — subagent type matching
- `mcp__server__tool` — MCP tool matching

**Bash Tool Architecture** (key for Lyra):
- Timeout: 2 min default, 10 min max
- Output: 30K char default, 150K hard ceiling
- Background: `run_in_background: true` for long processes
- Working directory persists within project boundaries
- Shell aliases/functions sourced from .zshrc/.bashrc
- Recognizes compound commands (&&, ||, ;, |) for permission matching

**Edit Tool**: Requires read-before-edit, exact string match, uniqueness check (or `replace_all`).

**Agent Tool (Subagents)**: Spawns isolated context, returns single result. Tool access controlled via `tools`/`disallowedTools` fields.

**Monitor Tool**: Background command watches, feeds each output line to Claude for reaction.

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| 34-tool catalog as reference architecture | S | Blueprint for Lyra's tool set |
| ToolName(specifier) permission format | S | Clean, extensible permission model |
| Read-before-edit + uniqueness check | S | Safety invariant for file mutation |
| Bash timeout/background/output-limit triad | A | Essential for safe shell execution |
| Glob (with **) + Grep (ripgrep) file ops | A | Standard file system tools |
| MCP tool prefix convention (`mcp__server__tool`) | A | Namespace convention prevents collisions |
| LSP integration (auto-diagnostics after edits) | A | Code intelligence in terminal |
| Monitor tool (background watchers) | A | Unique feature; event-driven agent loop |
| Tool search / lazy loading for MCP tools | A | Critical for scaling to many tools |
| Agent/Subagent tool with per-type allowlists | A | Core multi-agent primitive |

---

## 3. Goal System (goal)

**URL**: https://code.claude.com/docs/en/goal
**Relevance**: HIGH — Autonomous multi-turn execution loop.

### Architecture

`/goal` is a **session-scoped Stop hook wrapper**. The user sets a completion condition, and Claude keeps working across turns until a small fast model (default Haiku) confirms the condition is met.

### Key Mechanics

- **Evaluator**: Small fast model checks condition against conversation transcript after each turn. Returns yes/no + reason.
- **Condition**: Up to 4,000 characters. Should describe a measurable end state that Claude's output can demonstrate.
- **Status display**: Timer, turn count, token spend, most recent evaluator reason.
- **Resume support**: Active goals restored on `--resume`/`--continue` (timer/turns reset).
- **Non-interactive**: Works with `-p` flag for headless execution.
- **Explicit stop**: `/goal clear` (aliases: stop, off, reset, none, cancel).

### Comparison with Other Autonomous Approaches

| Approach | Trigger | Stop Condition |
|----------|---------|----------------|
| `/goal` | Previous turn finishes | Model confirms condition met |
| `/loop` | Time interval elapses | User stops or Claude decides done |
| Stop hook | Previous turn finishes | Script or prompt decides |

Auto mode alone only removes per-tool prompts. `/goal` adds a separate evaluator for per-turn completion checks.

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Separate evaluator model for completion | S | Breakthrough: cheap model watches expensive model |
| Condition-as-directive pattern | A | Simple UX for autonomous loops |
| Session-scoped ephemeral configuration | A | Clean lifecycle; no settings pollution |
| Resume support for active goals | B | Session persistence |
| Status display (turns, tokens, reason) | B | Transparency for long-running tasks |

---

## 4. Hooks Guide (hooks-guide)

**URL**: https://code.claude.com/docs/en/hooks-guide
**Relevance**: CRITICAL — Deterministic control plane for agent behavior.

### Overview

Hooks are **user-defined shell commands** that execute at specific lifecycle points. They provide deterministic control: certain actions always happen rather than relying on the LLM to choose to run them.

### Hook Configuration Locations

| Location | Scope | Shareable |
|----------|-------|-----------|
| `~/.claude/settings.json` | All projects (user) | No |
| `.claude/settings.json` | Single project | Yes (committable) |
| `.claude/settings.local.json` | Single project | No (gitignored) |
| Managed policy settings | Organization-wide | Yes (admin-controlled) |
| Plugin `hooks/hooks.json` | When plugin enabled | Yes (bundled) |
| Skill/Agent frontmatter | While component active | Yes (in component file) |

### Common Use Cases

- **Linting/formatting**: Auto-run after writes
- **Notifications**: Desktop alerts on idle/waiting
- **Security**: Block destructive commands (rm -rf)
- **Environment**: Activate virtualenvs, set env vars
- **Validation**: Enforce commit message formats
- **Auto-approval**: Pre-validate safe operations

### Handler Types

1. **Command hooks** (`type: "command"`): Shell commands. Async mode for background.
2. **HTTP hooks** (`type: "http"`): POST to external endpoint.
3. **MCP tool hooks** (`type: "mcp_tool"`): Call MCP server tools.
4. **Prompt-based hooks** (`type: "prompt"`): Model evaluates condition (single-turn).
5. **Agent-based hooks** (`type: "agent"`): Subagent with tools verifies condition (experimental).

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| PreToolUse / PostToolUse event model | S | Foundation for all agent lifecycle hooks |
| Settings-backed configuration (JSON) | S | Simple, familiar, shareable |
| Permission-level integration (block/allow/ask) | S | Hooks as security boundary |
| Multiple handler types (command/HTTP/MCP/prompt) | A | Flexibility for different integration needs |
| Prompt-based evaluation hooks | A | LLM-as-judge for subjective criteria |
| Agent-based hooks (tool access for verification) | A | Complex rule evaluation |
| Hook scoping (user/project/local/plugin/managed) | A | Clean security boundaries |
| Async hooks with re-wake capability | B | Non-blocking background verification |

---

## 5. Hooks Reference (hooks)

**URL**: https://code.claude.com/docs/en/hooks
**Relevance**: CRITICAL — Complete technical reference for the hooks system.

### Complete Event Catalog (27 events)

**Once per session**: `SessionStart`, `SessionEnd`, `Setup`

**Once per turn**: `UserPromptSubmit`, `UserPromptExpansion`, `Stop`, `StopFailure`

**Per tool call**: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `PermissionDenied`

**Agent lifecycle**: `SubagentStart`, `SubagentStop`, `TeammateIdle`

**Task management**: `TaskCreated`, `TaskCompleted`

**Notifications**: `Notification`, `MessageDisplay`, `Elicitation`, `ElicitationResult`

**Configuration**: `ConfigChange`, `CwdChanged`, `FileChanged`, `InstructionsLoaded`

**Worktree**: `WorktreeCreate`, `WorktreeRemove`

**Compaction**: `PreCompact`, `PostCompact`

### Exit Code Protocol

| Exit Code | Meaning | Behavior |
|-----------|---------|----------|
| 0 | Success | JSON on stdout parsed; context may be added |
| 2 | Blocking error | Action blocked. Stderr shown to Claude |
| Any other | Non-blocking error | Error noted, execution continues |

Exit code 2 blocks: `PreToolUse`, `PermissionRequest`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `ConfigChange`, `PreCompact`, `Elicitation`, `WorktreeCreate`.

### JSON Output Protocol

```json
// Universal
{ "continue": false, "stopReason": "...", "suppressOutput": true }

// Decision control
{ "decision": "block", "reason": "..." }

// PreToolUse-specific
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "..."
  }
}

// Context injection
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "This file is generated..."
  }
}
```

### Matcher Patterns

| Pattern | Behavior |
|---------|----------|
| `"*"`, `""`, omitted | Match all |
| Letters, digits, `_`, `|` | Exact or pipe-separated list |
| Any other character | JavaScript regex |
| `mcp__server__tool` | MCP tool matching |

### Path Placeholders

- `${CLAUDE_PROJECT_DIR}` — Project root
- `${CLAUDE_PLUGIN_ROOT}` — Plugin install directory
- `${CLAUDE_PLUGIN_DATA}` — Plugin persistent data directory

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| 27-event taxonomy | S | Blueprint for Lyra's event system |
| Exit code 2 = block protocol | S | Simple, universal blocking mechanism |
| Structured JSON output protocol | S | Clean API for hook responses |
| Matcher pattern system (exact, regex, wildcard) | S | Flexible event routing |
| Environment variable persistence via CLAUDE_ENV_FILE | A | Smart pattern for session env management |
| Terminal sequences for notifications (OSC 777) | B | Cross-terminal notification protocol |
| `additionalContext` placement rules | B | Clean context injection semantics |
| Path placeholders for plugin/project resolution | B | Essential for portable plugin hooks |

---

## 6. MCP Integration (mcp)

**URL**: https://code.claude.com/docs/en/mcp
**Relevance**: CRITICAL — Open standard for tool integration.

### Architecture

Claude Code implements MCP client protocol with full support for tools, resources, prompts, and elicitation. MCP servers connect over four transports:

| Transport | Use Case | Status |
|-----------|----------|--------|
| HTTP (streamable-http) | Remote cloud services | Recommended |
| SSE | Remote services (deprecated) | Deprecated |
| Stdio | Local processes | Standard |
| WebSocket | Persistent bidirectional | Available |

### Configuration Scopes

| Scope | Config File | Shared |
|-------|------------|--------|
| Local | `~/.claude.json` (per project path) | No |
| Project | `.mcp.json` in project root | Yes (git) |
| User | `~/.claude.json` (cross-project) | No |
| Plugin | Plugin `.mcp.json` or `plugin.json` inline | Yes |
| claude.ai | Cloud-account linked | Team/Enterprise |

Precedence: Local > Project > User > Plugin > claude.ai

### Key Features

**Dynamic tool updates**: MCP `list_changed` notifications allow servers to update tools live without reconnection.

**Automatic reconnection**: HTTP/SSE servers reconnect with exponential backoff (5 attempts, 1s→2s→4s→8s→16s).

**Tool search / lazy loading**: Deferred tool definitions; only tool names load at session start. Claude uses `ToolSearch` to discover relevant tools on demand. Controlled via `ENABLE_TOOL_SEARCH`:
- Unset: Deferred (default)
- `true`: Always deferred
- `auto`/`auto:N`: Threshold mode (10% / N% of context)
- `false`: All tools loaded upfront

**MCP prompts as commands**: `mcp__server__tool` format available in `/` menu.

**MCP resources**: `@server:protocol://path` references with autocomplete in prompt.

**Elicitation**: MCP servers can request structured input (forms or browser auth) mid-task.

**Output management**: Warn at 10K tokens, hard cap at 25K (configurable via `MAX_MCP_OUTPUT_TOKENS`). Per-tool override via `_meta["anthropic/maxResultSizeChars"]`.

**OAuth support**: Full OAuth 2.0 flow with DCR, pre-configured credentials, pinned scopes, custom callback ports.

**Claude Code as MCP server**: `claude mcp serve` exports Claude tools to other MCP clients.

### Plugin MCP Configuration

```json
// .mcp.json at plugin root
{
  "mcpServers": {
    "database-tools": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": { "DB_URL": "${DB_URL}" }
    }
  }
}
```

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| MCP client implementation with all 4 transports | S | Standard protocol; huge ecosystem leverage |
| Lazy tool loading (ToolSearch pattern) | S | Essential for scaling to many tools |
| `.mcp.json` project configuration | S | Simple, shareable, version-controlled |
| Scope hierarchy with precedence | A | Clean multi-tenancy model |
| Plugin-bundled MCP servers | A | Zero-config tool distribution |
| Automatic reconnection with backoff | B | Reliability |
| OAuth 2.0 flow for remote servers | B | Enterprise readiness |
| MCP prompts as command namespace | B | Unified command surface |
| `@` resource references in prompts | B | Natural UX for external data |
| Claude Code as MCP server | A | Recursive composition; powerful pattern |

---

## 7. Interactive Mode (interactive-mode)

**URL**: https://code.claude.com/docs/en/interactive-mode
**Relevance**: HIGH — Terminal UX patterns.

### Keyboard Shortcut System

**General Controls**:
- `Ctrl+C`: Interrupt or clear input (double = exit)
- `Ctrl+D`: Exit session (EOF)
- `Ctrl+G` / `Ctrl+X Ctrl+E`: Open in text editor
- `Ctrl+L`: Redraw screen
- `Ctrl+O`: Toggle transcript viewer
- `Ctrl+R`: Reverse search command history
- `Ctrl+V` (or `Cmd+V`): Paste image from clipboard
- `Ctrl+B`: Background running tasks
- `Ctrl+T`: Toggle task list
- `Esc`: Interrupt Claude mid-turn
- `Esc+Esc`: Open rewind menu (or clear input if text present)
- `Shift+Tab` / `Alt+M`: Cycle permission modes
- `Option+P` (macOS) / `Alt+P`: Switch model
- `Option+T` (macOS) / `Alt+T`: Toggle extended thinking
- `Option+O` / `Alt+O`: Toggle fast mode

**Text Editing** (readline-style):
- `Ctrl+A/E`: Line start/end
- `Ctrl+K/U/W`: Delete to end/from start/previous word
- `Ctrl+Y`: Paste (yank)
- `Alt+Y` after `Ctrl+Y`: Cycle paste history
- `Alt+B/F`: Word navigation

**Quick Commands**:
- `/` at start: Command/skill palette
- `!` at start: Shell mode (direct command execution)
- `@` at start: File path mention with autocomplete

**Multiline Input**: `\`+Enter, `Option+Enter`, `Shift+Enter`, `Ctrl+J`, or paste directly.

**Transcript Viewer** (`Ctrl+O`):
- `{`/`}`: Jump between prompts (vim paragraph motion)
- `Ctrl+E`: Toggle show all content
- `[`: Write to terminal scrollback
- `v`: Open in $EDITOR
- `q`, `Ctrl+C`, `Esc`: Exit

### Vim Editor Mode

Full vim keybindings for prompt input: Normal/Insert/Visual modes, motions (hjkl, w, e, b, f/F/t/T, ;/,), editing (x, dd, D, cc, C, yy, p, >>, <<, u, .), text objects (iw/aw, i"/a", i(/a(, i[/a[, i{/a{), and visual mode operations.

### Intelligent Features

**Prompt suggestions**: Grayed-out example commands from git history. Tab/Right arrow to accept. Runs as background request using prompt cache.

**Side questions with `/btw`**: Ask ephemeral questions without polluting context. Sees full conversation, no tool access. Can fork (`f` key) into full session.

**Session recap**: One-line summary when returning after step away. Auto-generates after 3+ minutes idle, 3+ turns.

**PR review status**: Colored PR link in footer (green=approved, yellow=pending, red=changes-requested, gray=draft). Refreshes every 60s.

**Task list**: `Ctrl+T` to toggle. Up to 5 tasks visible. Persists across compactions. Named task lists via `CLAUDE_CODE_TASK_LIST_ID`.

**Voice input**: Hold/tap Space for dictation (configurable).

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Full keyboard shortcut matrix | A | Terminal UX baseline |
| `/` command palette with fuzzy filter | S | Universal command discovery pattern |
| `!` shell mode (direct exec + context injection) | A | Clean separation of shell vs agent |
| `@` file mention with autocomplete | A | Natural file reference UX |
| Transcript viewer with navigation | B | History browsing pattern |
| Vim keybindings for prompt editing | B | Power user feature |
| Prompt suggestions from git history | B | Smart defaults |
| `/btw` side questions (ephemeral, cache-reusing) | A | Innovative: cheap Q&A without context pollution |
| Session recap on return | B | UX quality-of-life |
| PR review status in footer | C | GitHub-specific integration |

---

## 8. Commands (commands)

**URL**: https://code.claude.com/docs/en/commands
**Relevance**: HIGH — User command surface.

### Command Architecture

Commands are recognized only at the **start of a message**. Text after the command name is passed as arguments. Support for MCP provided prompts (`/mcp__server__prompt`) and plugin/bundled/user skills.

### Command Categories (Complete List)

**Workflow Commands**: `/init`, `/memory`, `/plan`, `/compact`, `/context`, `/btw`

**Model & Performance**: `/model`, `/effort`, `/fast-mode`, `/thinking`

**Agent Management**: `/agents` (subagent manager), `/tasks` (background tasks), `/background` (detach session)

**Parallel Execution**: `/batch` (decompose + worktrees)

**Session Control**: `/clear`, `/resume`, `/rewind`, `/fork`, `/recap`

**Configuration**: `/config`, `/permissions`, `/mcp`, `/hooks`, `/settings`

**Plugin Management**: `/plugin install`, `/plugin marketplace add`, `/plugin list`, `/reload-plugins`

**Authentication**: `/login`, `/logout`, `/status`

**Utility**: `/doctor`, `/pr-comments`, `/terminal-setup`, `/theme`, `/tui`, `/voice`

**Worktrees**: `/worktree`, `/batch`

**Debugging**: `/debug`, `/hooks`

**Team Management** (experimental): `/team`, `/team-onboarding`

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| `/`-prefixed command system with fuzzy filtering | S | Universal UX pattern |
| `/plan` (plan mode before coding) | A | Safety gate before large changes |
| `/compact` (context compression) | A | Essential for long sessions |
| `/rewind` (checkpoint restore) | A | Recovery UX |
| `/agents` (subagent management UI) | A | Multi-agent control panel |
| `/batch` (parallel worktree execution) | B | Advanced parallelism pattern |
| `/config` (settings management) | B | User configuration UX |
| `/doctor` (self-diagnostic) | B | Supportability |
| MCP prompts as commands (`/mcp__server__tool`) | A | Unified command namespace |

---

## 9. Checkpointing (checkpointing)

**URL**: https://code.claude.com/docs/en/checkpointing
**Relevance**: HIGH — Safety net for autonomous code changes.

### Architecture

Claude Code automatically tracks file edits using a **shadow git repo** or similar mechanism. Every user prompt creates a new checkpoint. Checkpoints persist across sessions (30-day auto-cleanup).

### Rewind Menu (`/rewind` or `Esc Esc`)

Lists each prompt sent during the session. Six actions per checkpoint:

1. **Restore code and conversation**: Revert both
2. **Restore conversation only**: Rewind history, keep code
3. **Restore code only**: Revert files, keep conversation
4. **Summarize from here**: Compress from this point forward (keep early context)
5. **Summarize up to here**: Compress before this point (keep recent work)
6. **Never mind**: Return without changes

### Limitations

- Bash command changes NOT tracked (only Edit/Write/NotebookEdit tools)
- External changes not tracked
- Not a replacement for version control

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Automatic checkpoint on every user prompt | S | Zero-config safety net |
| Tri-modal restore (code only / conversation only / both) | S | Granular recovery beats all-or-nothing |
| Targeted summarization (from here / up to here) | A | Sophisticated context management |
| Shadow git repo for tracking | A | Implementation approach |
| `Esc Esc` quick-access UX | B | Keyboard shortcut for safety |
| 30-day TTL with configurable cleanup | C | Storage management |

---

## 10. Permissions (permissions)

**URL**: https://code.claude.com/docs/en/permissions
**Relevance**: CRITICAL — Security model for agent actions.

### Permission Architecture

Tiered system: **read-only** (no approval), **bash** (approval with permanent save), **file modification** (approval until session end).

### Permission Modes

| Mode | Description | Risk |
|------|-------------|------|
| `default` | Prompt on first use of each tool | Low |
| `acceptEdits` | Auto-accept edits + common FS commands | Medium |
| `plan` | Read-only exploration, no edits | Low |
| `auto` | Auto-approve with background safety checks | High (research preview) |
| `dontAsk` | Auto-deny unless pre-approved | Low |
| `bypassPermissions` | Skip all prompts (still guards root/home rm) | Very High |

### Rule Syntax

```
Tool(specifier)
Deny > Ask > Allow (evaluation order)
```

**Tool-specific patterns**:
- `Bash(npm run *)` — command prefix matching
- `Read(~/secrets/**)` — path with gitignore syntax (// absolute, ~/ home, / project, ./ relative)
- `Read(//**/.env)` — filesystem-wide deny
- `WebFetch(domain:example.com)` — domain restriction
- `Agent(Explore)` — subagent type restriction
- `mcp__server__*` — MCP tool restriction

### Key Architecture Decisions

1. **Deny-first evaluation**: Deny rules always win. Cannot be overridden.
2. **Bare vs scoped deny**: Bare `Bash` removes tool from context; `Bash(rm *)` leaves tool but blocks matching calls.
3. **Compound command awareness**: Shell operators (&&, ||, ;, |, &) recognized. Each subcommand checked independently.
4. **Process wrappers stripped**: `timeout`, `time`, `nice`, `nohup`, `stdbuf` stripped before matching.
5. **Read-only commands**: Built-in allowlist (`ls`, `cat`, `echo`, `pwd`, `head`, `tail`, `grep`, `find`, `wc`, `which`, `diff`, `stat`, `du`, `cd`, read-only `git`).
6. **Symlink handling**: Allow rules check both symlink AND target; deny rules block on EITHER.

### Settings Precedence

1. Managed settings (cannot be overridden)
2. CLI arguments
3. Local project (`.claude/settings.local.json`)
4. Shared project (`.claude/settings.json`)
5. User (`~/.claude/settings.json`)

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| ToolName(specifier) rule format | S | Simple, expressive, familiar |
| Deny-first evaluation + scoping hierarchy | S | Security-first design |
| Permission modes (especially `plan` and `auto`) | A | Progressive trust model |
| Gitignore-path syntax for file rules (//, ~/, /, ./) | A | Flexible path matching |
| Compound command awareness in Bash | B | Security correctness |
| Read-only command allowlist | B | Sensible defaults |
| Working directories (`--add-dir`, `additionalDirectories`) | B | Multi-project access |
| Managed settings for enterprise | C | Wait for enterprise adoption |
| Sandbox integration (complementary to permissions) | B | Defense-in-depth |

---

## 11. Agent Teams (agent-teams)

**URL**: https://code.claude.com/docs/en/agent-teams
**Relevance**: HIGH — Multi-agent orchestration pattern.

### Architecture

**Experimental** (disabled by default, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`).

| Component | Role |
|-----------|------|
| Team lead | Main session: creates team, spawns teammates, coordinates |
| Teammates | Independent Claude instances with own context windows |
| Task list | Shared work queue with locking (file-based) |
| Mailbox | Inter-agent messaging system |

### Key Mechanics

- **Team creation**: Natural language request. Lead decides team size/structure.
- **Display modes**: In-process (Shift+Down to cycle) or split panes (tmux/iTerm2).
- **Task coordination**: Lead creates tasks; teammates self-claim or are assigned. File locking prevents races.
- **Dependencies**: Tasks can depend on other tasks; auto-unblock on completion.
- **Communication**: `SendMessage` tool for direct agent-to-agent messaging. Automatic delivery.
- **Plan approval**: Optional per-teammate plan-before-execute with lead approval gate.
- **Permissions**: Teammates inherit lead's permissions at spawn time.
- **Subagent reuse**: Subagent definitions from project/user/plugin can be used as teammate roles.

### How Agent Teams Differ from Subagents

| | Subagents | Agent Teams |
|---|---|---|
| Context | Own window; results return to caller | Own window; fully independent |
| Communication | Report to main agent only | Direct teammate-to-teammate messaging |
| Coordination | Main agent manages all | Shared task list with self-coordination |
| Best for | Focused tasks, result matters | Complex work requiring collaboration |
| Token cost | Lower | Higher (each is separate Claude instance) |

### Limitations (Experimental)

- No session resumption with in-process teammates
- Task status can lag
- One team at a time
- No nested teams (teammates can't spawn their own)
- Lead is fixed (no promotion)

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Shared task list with locking | S | Core coordination primitive |
| Direct agent-to-agent messaging (SendMessage) | S | Enables collaboration, not just delegation |
| Task dependency graph with auto-unblock | A | Sophisticated workflow orchestration |
| Display modes (in-process vs panes) | B | Terminal multiplexing UX |
| Reusable subagent definitions as teammate roles | A | DRY agent definitions |
| Plan approval gate for teammates | A | Safety valve for autonomous workers |
| Permission inheritance from lead | B | Simplified security model |
| File-based team state (config.json, task list) | B | Storage pattern |

---

## 12. Channels Reference (channels-reference)

**URL**: https://code.claude.com/docs/en/channels-reference
**Relevance**: HIGH — Push-based event integration pattern.

### Architecture

A channel is an **MCP server** that pushes events into a Claude Code session. Claude Code spawns it as a subprocess over stdio. The channel declares the `claude/channel` capability.

### Channel Types

- **One-way**: Forward alerts, webhooks, monitoring events. No reply expected.
- **Two-way**: Add reply tool so Claude can send messages back (chat bridges).
- **With permission relay**: Opt-in `claude/channel/permission` capability. Remotely approve/deny tool calls.

### Notification Format

```javascript
await mcp.notification({
  method: 'notifications/claude/channel',
  params: {
    content: 'build failed on main',
    meta: { severity: 'high', run_id: '1234' }
  }
})
// Arrives as: <channel source="server-name" severity="high" run_id="1234">...</channel>
```

### Permission Relay Protocol

1. Claude Code sends `notifications/claude/channel/permission_request` with `request_id` (5 letters, a-z sans `l`), `tool_name`, `description`, `input_preview`
2. Channel forwards to remote user (chat app)
3. Remote user replies `yes <id>` or `no <id>`
4. Channel sends `notifications/claude/channel/permission` with `request_id` + `behavior: allow|deny`
5. First answer (local terminal or remote) wins; other is discarded

### Security: Sender Gating

```javascript
const allowed = new Set(loadAllowlist())
if (!allowed.has(message.from.id)) return  // drop silently
```

Gate on sender identity, not room/chat identity.

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Channel-as-MCP-server architecture | S | Clean: reuse MCP transport for push events |
| `<channel>` tag protocol in agent context | A | Simple markup for external events |
| Two-way channels with reply tool | A | Complete bidirectional communication |
| Permission relay for remote approval | A | Mobile-first safety UX |
| Sender gating via allowlist | A | Security: prevent prompt injection |
| Research preview channels (Telegram, Discord, iMessage) | B | Proven integrations |
| Plugin packaging for channels | B | Distribution pattern |
| SSE stream for testing outbound | C | Development convenience |

---

## 13. Environment Variables (env-vars)

**URL**: https://code.claude.com/docs/en/env-vars
**Relevance**: HIGH — Configuration surface and feature flags.

### Variable Categories

**Authentication**: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_AWS_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, etc.

**Endpoint Routing**: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AWS_BASE_URL`, `ANTHROPIC_BEDROCK_BASE_URL`, `ANTHROPIC_VERTEX_BASE_URL`, `ANTHROPIC_FOUNDRY_BASE_URL`

**Model Selection**: `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_CUSTOM_MODEL_OPTION`

**API Configuration**: `API_TIMEOUT_MS` (default 600000), `ANTHROPIC_BETAS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, `CLAUDE_CODE_MAX_RETRIES`, `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`

**Bash/Tools**: `BASH_DEFAULT_TIMEOUT_MS` (120000), `BASH_MAX_TIMEOUT_MS` (600000), `BASH_MAX_OUTPUT_LENGTH`, `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR`, `CLAUDE_CODE_GLOB_NO_IGNORE`, `CLAUDE_CODE_GLOB_TIMEOUT_SECONDS`

**Feature Toggles**: `CLAUDE_CODE_DISABLE_*` family for agent view, background tasks, fast mode, workflows, cron, checkpointing, thinking, adaptive thinking, attachments, memory, git instructions, terminal title, etc.

**MCP**: `MAX_MCP_OUTPUT_TOKENS` (25000 default), `ENABLE_TOOL_SEARCH`, `ENABLE_CLAUDEAI_MCP_SERVERS`, `MCP_TIMEOUT`

**TLS/Network**: `CLAUDE_CODE_CERT_STORE`, `CLAUDE_CODE_CLIENT_CERT`, `CLAUDE_CODE_CLIENT_KEY`

**Experimental**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CODE_NO_FLICKER` (fullscreen), `CLAUDE_CODE_FORK_SUBAGENT`

**Plugins**: `CLAUDE_CODE_PLUGIN_CACHE_DIR`, `CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS`, `CLAUDE_CODE_PLUGIN_PREFER_HTTPS`, `CLAUDE_CODE_PLUGIN_SEED_DIR`

### Configuration Locations

| Location | Scope |
|----------|-------|
| Shell environment | Per session |
| `~/.claude/settings.json` | User, all projects |
| `.claude/settings.json` | Project, shared |
| `.claude/settings.local.json` | Project, local only |
| Managed settings | Organization-wide |

Precedence: Environment variables override settings file fields.

### Key Insights for Lyra

| Feature | Tier | Rationale |
|---------|------|-----------|
| Dual config (env vars + settings.json `env` key) | A | Flexibility + shareability |
| Feature toggle naming convention (`DISABLE_*`) | B | Consistent pattern |
| Model selection via env vars with tier separation | A | Provider-agnostic model routing |
| Tool behavior tuning (timeouts, limits) | A | Safety boundaries |
| Certificate and mTLS support | B | Enterprise readiness |
| Plugin cache/seed directory configuration | C | Distribution infrastructure |

---

## Summary: Priority-Ranked Feature List for Lyra

### S-Tier (Breakthrough: Implement First)

| # | Feature | Source | Why |
|---|---------|--------|-----|
| 1 | **Plugin system with component directories** (skills, agents, hooks, MCP, monitors) | Plugins Ref | Core extensibility; defines Lyra's ecosystem |
| 2 | **Hooks system with 27 lifecycle events + exit-code blocking** | Hooks Ref | Deterministic control plane; security boundary |
| 3 | **MCP client with all 4 transports + lazy tool loading** | MCP, Tools Ref | Open standard; massive ecosystem leverage |
| 4 | **ToolName(specifier) permission model with deny-first evaluation** | Permissions | Simple, expressive, secure |
| 5 | **Separate evaluator model for goal completion** | Goal | Cheap model watches expensive model |
| 6 | **Automatic checkpointing on every user prompt** | Checkpointing | Zero-config safety net |
| 7 | **Tri-modal restore (code/conversation/both)** | Checkpointing | Granular recovery |
| 8 | **Shared task list with locking for agent coordination** | Agent Teams | Core coordination primitive |
| 9 | **Direct agent-to-agent messaging** | Agent Teams | Enables collaboration beyond delegation |
| 10 | **Channel architecture (MCP servers pushing events)** | Channels Ref | Push-based integration pattern |

### A-Tier (High Priority)

| # | Feature | Source |
|---|---------|--------|
| 1 | `/` command palette with fuzzy filtering | Interactive Mode, Commands |
| 2 | Permission modes (plan/auto/acceptEdits) | Permissions |
| 3 | Tool catalog: Bash (timeout/bg/output-limit), Edit (read-before-edit), Glob, Grep | Tools Ref |
| 4 | Lazy MCP tool search with threshold mode | MCP |
| 5 | `.mcp.json` project configuration + scope hierarchy | MCP |
| 6 | Plugin-bundled MCP servers (zero-config distribution) | MCP |
| 7 | Agent/Subagent tool with per-type allowlists | Tools Ref |
| 8 | Prompt-based evaluation hooks (LLM-as-judge) | Hooks Ref |
| 9 | Agent-based hooks (tool access for verification) | Hooks Ref |
| 10 | Monitor tool (background watchers) | Tools Ref |
| 11 | Condition-as-directive goal UX | Goal |
| 12 | Targeted summarization (from here / up to here) | Checkpointing |
| 13 | Channel two-way reply tool pattern | Channels Ref |
| 14 | Channel permission relay (remote approval) | Channels Ref |
| 15 | `!` shell mode (direct execution + context injection) | Interactive Mode |
| 16 | `@` file mention with autocomplete | Interactive Mode |
| 17 | `/btw` side questions (ephemeral, cache-reusing) | Interactive Mode, Commands |
| 18 | Full keyboard shortcut matrix | Interactive Mode |
| 19 | Reusable subagent definitions as teammate roles | Agent Teams |
| 20 | Claude Code as MCP server (recursive composition) | MCP |
| 21 | Dual config (env vars + settings.json) | Env Vars |
| 22 | LSP integration (auto-diagnostics after edits) | Tools Ref |

### B-Tier (Solid Improvements)

| # | Feature | Source |
|---|---------|--------|
| 1 | Vim keybindings for prompt editing | Interactive Mode |
| 2 | Transcript viewer with navigation | Interactive Mode |
| 3 | Session recap on return | Interactive Mode |
| 4 | Prompt suggestions from git history | Interactive Mode |
| 5 | Plugin marketplace (git-based) | Plugins Ref |
| 6 | Persistent plugin data directory | Plugins Ref |
| 7 | Async hooks with re-wake capability | Hooks Ref |
| 8 | Terminal sequences for notifications (OSC 777) | Hooks Ref |
| 9 | Path placeholders for plugin/project resolution | Hooks Ref |
| 10 | /batch command (parallel worktree execution) | Commands |
| 11 | /doctor and /config UX | Commands |
| 12 | Display modes for agent teams (in-process vs panes) | Agent Teams |
| 13 | File-based team state storage | Agent Teams |
| 14 | Sandbox integration (complementary to permissions) | Permissions |
| 15 | Working directories support | Permissions |
| 16 | Compound command awareness in Bash permissions | Permissions |
| 17 | Symlink-aware permission checking | Permissions |
| 18 | MCP prompts as command namespace | MCP |
| 19 | Shadow git repo for checkpointing implementation | Checkpointing |
| 20 | Certificate and mTLS support | Env Vars |

### C-Tier (Nice-to-Have / High Effort)

- NotebookEdit tool, PowerShell tool, PR review status, Enterprise managed settings, Managed plugin policies, OAuth 2.0 for MCP servers, SSE transport (deprecated), WebSocket transport, Remote trigger (Anthropic-specific), ShareOnboardingGuide, PushNotification

---

## Architecture Patterns to Steal

### 1. Separation of Concerns (Claude Code's Three Layers)

```
1. Agent Loop (LLM decides what to do)
2. Hook System (deterministic rules evaluate/block)
3. Permission System (user-configured allow/deny)
```

Each layer operates independently. Hooks cannot be bypassed by the model. Permissions cannot be bypassed by hooks. This is a clean three-layer security architecture.

### 2. Tool Representation

Tools are defined with: name, description, JSON Schema input, permission requirement, and behavior documentation. Tool names are the same strings used in hooks, permissions, and subagent configs. This unified naming is essential.

### 3. Configuration File Hierarchy

```
Managed > CLI args > Local project (.local.json) > Shared project (.json) > User (~/.claude/)
```

Each level can tighten restrictions but not loosen them from above. This is the correct security model for multi-tenant / enterprise use.

### 4. Event-Driven Architecture

Everything is an event: `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`, etc. Events carry structured JSON with `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, and event-specific fields. This is the correct pattern for an observable, debuggable agent system.

### 5. Plugin = Directory of Components

Simple, filesystem-based. No registry, no packaging format beyond a directory. Components auto-discovered. This is the right level of abstraction — complex enough to be useful, simple enough to be hackable.

### 6. Channel = MCP Server with Push Capability

Reuses the MCP transport layer. Channels are just MCP servers that declare a `claude/channel` capability and emit `notifications/claude/channel` events. This is elegant and correct.

### 7. Small-Fast-Model as Evaluator

The `/goal` pattern of using a cheap model to evaluate whether a more expensive model's output meets a condition is a breakthrough cost-efficiency pattern. It generalizes to code review, test validation, and any boolean completion check.

---

## Implementation Roadmap for Lyra

### Phase 1: Foundation (Weeks 1-4)
- [ ] Tool catalog (Bash, Read, Write, Edit, Glob, Grep)
- [ ] Permission system (ToolName(specifier), deny-first)
- [ ] Hook system (PreToolUse, PostToolUse, SessionStart, Stop)
- [ ] Plugin directory structure + auto-discovery

### Phase 2: Protocol Integration (Weeks 5-8)
- [ ] MCP client (stdio + HTTP transports)
- [ ] Lazy tool loading (ToolSearch pattern)
- [ ] `.mcp.json` configuration
- [ ] Plugin-bundled MCP servers

### Phase 3: Multi-Agent (Weeks 9-12)
- [ ] Subagent system (Agent tool)
- [ ] Agent teams (shared task list, messaging)
- [ ] Channel architecture (push events)
- [ ] Goal system (evaluator model)

### Phase 4: UX & Polish (Weeks 13-16)
- [ ] Command palette (`/` menu)
- [ ] Keyboard shortcuts + vim mode
- [ ] Checkpointing + rewind
- [ ] Session recap, prompt suggestions
- [ ] `/btw` side questions
