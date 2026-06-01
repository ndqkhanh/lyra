# Phase 1 Research Findings — Feature Parity

**Date**: 2026-05-31  
**Status**: In Progress

---

## Claude Code Documentation — Key Findings

### §4.6 Tools Reference

**Complete tool inventory** (30+ built-in tools):
- **File operations**: Read, Write, Edit, Glob, Grep, NotebookEdit
- **Execution**: Bash, PowerShell, Monitor
- **Code intelligence**: LSP (language server protocol)
- **Web**: WebFetch, WebSearch
- **Agent orchestration**: Agent, SendMessage, TeamCreate, TeamDelete
- **Task management**: TaskCreate, TaskGet, TaskList, TaskUpdate, TaskStop
- **Session control**: EnterPlanMode, ExitPlanMode, EnterWorktree, ExitWorktree
- **Scheduling**: CronCreate, CronDelete, CronList, ScheduleWakeup
- **User interaction**: AskUserQuestion, PushNotification
- **Skills**: Skill (invokes user-defined skills)
- **MCP**: ListMcpResourcesTool, ReadMcpResourceTool, ToolSearch, WaitForMcpServers
- **Workflows**: Workflow (dynamic workflow orchestration)
- **Misc**: RemoteTrigger (Routines on claude.ai), ShareOnboardingGuide

**Key insights for Lyra**:
1. **Tool permission system** — every tool has granular allow/deny/ask rules with pattern matching
2. **Multi-provider abstraction** — tools work across Claude API, Bedrock, Vertex, Foundry
3. **Read-before-edit constraint** — Edit tool requires prior Read in conversation (prevents blind overwrites)
4. **Background execution** — Bash/Monitor support `run_in_background` for long-running processes
5. **Output limits** — Bash caps at 30k chars (configurable), saves overflow to disk
6. **LSP integration** — automatic type-checking after edits, no separate build step needed

**Port priorities for Lyra**:
- ✅ Already have: Read, Write, Edit, Bash, Grep (basic versions)
- 🔴 High-impact missing: LSP, Monitor, PowerShell, NotebookEdit, Glob with gitignore awareness
- 🟡 Medium: WebFetch (with extraction prompt), WebSearch, AskUserQuestion
- 🟢 Lower: PushNotification, RemoteTrigger (claude.ai-specific)

---

### §4.7 Plugins Reference

**Plugin system architecture**:
- **Self-contained directories** with multiple component types
- **Components**: Skills, Agents, Hooks, MCP servers, LSP servers, Monitors
- **Discovery**: Auto-loaded from `.claude/plugins/` or installed via marketplaces
- **Lifecycle**: `enabledPlugins` in settings, `/reload-plugins` for hot-reload

**Plugin structure**:
```
my-plugin/
├── plugin.json (metadata + inline config)
├── skills/
│   └── my-skill/
│       └── SKILL.md
├── agents/
│   └── my-agent.md
├── hooks/
│   └── PostToolUse.sh
├── .mcp.json (MCP servers)
└── monitors/
    └── my-monitor.json
```

**Key features**:
- **Persistent data directory**: `${CLAUDE_PLUGIN_DATA}` survives updates
- **Environment variables**: `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`
- **Marketplace distribution**: GitHub repos, npm packages, local directories
- **Managed plugins**: Force-enabled via managed settings (enterprise control)

**Lyra adoption**:
- Design a **provider-agnostic plugin system** (not Claude-specific)
- Support **filesystem-based discovery** (no registry required)
- Enable **hot-reload** without session restart
- Package **skills + tools + hooks** together

---

### §4.8 MCP Integration

**MCP (Model Context Protocol)** — open standard for AI-tool integrations:

**Transport types**:
1. **HTTP** (recommended for remote): `claude mcp add --transport http name url`
2. **SSE** (deprecated): Server-Sent Events
3. **Stdio** (local processes): `claude mcp add name -- command args`
4. **WebSocket** (bidirectional): For push events

**Scopes**:
- **Local**: Current project only, stored in `~/.claude.json` under project path
- **Project**: Shared via `.mcp.json` in repo (requires approval)
- **User**: All projects, stored in `~/.claude.json` globally
- **Plugin-provided**: Bundled with plugins, auto-loaded

**Authentication**:
- **OAuth 2.0**: Dynamic client registration or pre-configured credentials
- **Header-based**: Static tokens or `headersHelper` script for dynamic tokens
- **Callback port**: `--callback-port` for fixed redirect URIs

**Key features**:
- **Tool search**: Defer tool loading until needed (scales to 100+ MCP servers)
- **Resources**: `@server:protocol://path` mentions (like file mentions)
- **Prompts as commands**: MCP prompts become `/mcp__server__prompt` commands
- **Elicitation**: Mid-task structured input requests (forms or browser flows)
- **Dynamic updates**: `list_changed` notifications refresh tools without reconnect
- **Auto-reconnect**: Exponential backoff for HTTP/SSE servers

**Lyra MCP strategy**:
- Implement **stdio + HTTP transports** first (cover 90% of servers)
- Build **tool search** to scale beyond 20-30 servers
- Support **OAuth 2.0** for cloud connectors (GitHub, Slack, Notion, etc.)
- Enable **project-scoped `.mcp.json`** for team sharing
- Add **resource mentions** (`@mcp:...`) for context injection

---

### §4.9 Commands & Interactive Mode

**Command system**:
- **Slash commands**: `/` prefix triggers command/skill picker
- **Shell mode**: `!` prefix runs commands directly, adds output to context
- **File mentions**: `@` triggers file path autocomplete
- **Voice input**: Hold/tap Space for dictation (when enabled)

**Built-in commands** (30+):
- Session: `/clear`, `/resume`, `/compact`, `/rewind`, `/btw` (side question)
- Config: `/config`, `/permissions`, `/mcp`, `/agents`, `/model`, `/effort`
- Planning: `/plan`, `/init`, `/memory`
- Execution: `/goal`, `/loop`, `/background`, `/batch`, `/tasks`
- Tools: `/terminal-setup`, `/voice`, `/theme`, `/recap`

**Keyboard shortcuts** (50+):
- **Ctrl+O**: Toggle transcript viewer (detailed tool usage)
- **Ctrl+R**: Reverse search command history
- **Ctrl+V**: Paste image from clipboard
- **Ctrl+B**: Background running tasks
- **Ctrl+T**: Toggle task list
- **Esc Esc**: Clear input or open rewind menu
- **Shift+Tab / Alt+M**: Cycle permission modes
- **Alt+P**: Switch model
- **Alt+T**: Toggle extended thinking
- **Alt+O**: Toggle fast mode

**Vim mode**: Full modal editing (NORMAL/INSERT/VISUAL) with text objects

**Lyra adoption**:
- Implement **slash command system** with fuzzy search
- Add **shell mode** (`!` prefix) for direct command execution
- Build **file mention autocomplete** (`@` prefix)
- Support **keyboard shortcuts** for common operations
- Consider **vim mode** as optional plugin

---

### §4.10 Hooks & Automation

**Hook types**:
1. **PreToolUse**: Before tool execution (validation, parameter modification)
2. **PostToolUse**: After tool execution (auto-format, linting, notifications)
3. **Stop**: When session ends (final verification, cleanup)
4. **SessionStart**: On session initialization (env setup, welcome message)
5. **UserPromptSubmit**: Before user prompt is sent (preprocessing)

**Hook execution modes**:
- **Command hooks**: Shell scripts with JSON input/output
- **Prompt-based hooks**: LLM-evaluated conditions (uses small/fast model)
- **Agent-based hooks**: Full subagent with tools (for complex decisions)
- **Async hooks**: Non-blocking, result delivered later

**Hook configuration**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit(**/*.ts)",
        "command": "npx prettier --write ${file}",
        "description": "Format TypeScript files"
      }
    ]
  }
}
```

**Key features**:
- **Matcher patterns**: Tool name + glob patterns for file paths
- **Environment variables**: `CLAUDE_PROJECT_DIR`, `CLAUDE_TOOL_NAME`, `CLAUDE_FILE_PATH`
- **JSON I/O**: Structured input with tool parameters, structured output with actions
- **Managed hooks**: Enterprise control via `allowManagedHooksOnly`
- **Permission integration**: Hooks can `allow`, `ask`, or `deny` tool calls

**Lyra adoption**:
- Implement **PreToolUse/PostToolUse/Stop** hooks first
- Support **command + prompt-based** hooks (agent-based later)
- Build **matcher system** with glob patterns
- Enable **auto-format on save** via PostToolUse hooks
- Add **permission gates** via PreToolUse hooks

---

### §4.11 Sessions & Checkpointing

**Session management**:
- **Automatic tracking**: Every user prompt creates a checkpoint
- **Persistence**: Checkpoints survive across `--resume` / `--continue`
- **Cleanup**: Auto-deleted after 30 days (configurable)

**Rewind menu** (`/rewind` or `Esc Esc`):
- **Restore code and conversation**: Full rollback to checkpoint
- **Restore conversation**: Rewind messages, keep current code
- **Restore code**: Revert files, keep conversation
- **Summarize from here**: Compress conversation forward from checkpoint
- **Summarize up to here**: Compress conversation before checkpoint

**Limitations**:
- **Bash changes not tracked**: Only Edit/Write tool changes are checkpointed
- **External changes not tracked**: Manual edits outside session not captured
- **Not version control**: Complements Git, doesn't replace it

**Session commands**:
- `/clear`: Start new session (preserves previous for resume)
- `/resume`: Continue most recent session
- `/continue --fork-session`: Branch off new session from current state
- `/recap`: Generate summary of session so far

**Lyra adoption**:
- Implement **checkpoint system** for Edit/Write operations
- Build **rewind UI** with restore + summarize options
- Add **session persistence** to disk (JSON or SQLite)
- Support **session forking** for trying alternatives
- Track **conversation + code state** together

---

### §4.12 Permissions & Credentials

**Permission system** (3-tier):
1. **Read-only tools**: No approval (Read, Grep, Glob, LSP)
2. **Bash commands**: Approval required, "don't ask again" persists per project+command
3. **File modifications**: Approval required, persists until session end

**Permission modes**:
- `default`: Prompt on first use
- `acceptEdits`: Auto-approve file edits in working directory
- `plan`: Read-only, no edits allowed
- `auto`: Auto-approve with background safety checks (research preview)
- `dontAsk`: Deny unless pre-approved
- `bypassPermissions`: Skip all prompts (dangerous, container-only)

**Rule syntax**:
- `Bash(npm run *)`: Wildcard command matching
- `Read(~/secrets/**)`: Gitignore-style path patterns
- `Edit(/src/**)`: Project-relative paths
- `WebFetch(domain:example.com)`: Domain restrictions
- `Agent(Explore)`: Subagent type restrictions

**Credential management**:
- **Environment variables**: `~/.claude/settings.json` `env` field
- **Secrets**: Stored in system keychain (macOS) or credentials file
- **OAuth tokens**: Auto-refreshed, stored securely
- **API keys**: `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, etc.

**Managed settings** (enterprise):
- **Managed-only keys**: `allowManagedHooksOnly`, `allowManagedMcpServersOnly`, `strictPluginOnlyCustomization`
- **Precedence**: Managed > CLI args > Local > Project > User
- **Delivery**: MDM/OS policies, managed files, server-managed settings

**Lyra adoption**:
- Implement **3-tier permission system** (read-only / command / file-edit)
- Build **rule engine** with glob patterns + wildcards
- Support **permission modes** (default, plan, auto, bypass)
- Add **credential storage** (keychain on macOS, encrypted file elsewhere)
- Enable **managed settings** for enterprise deployments

---

## Comparable Harnesses — Cloning Status

✅ **Cloning in progress** (background tasks):
- OpenCode (anomalyco/opencode)
- DeerFlow 2.0 (bytedance/deer-flow)
- Kilo Code (Kilo-Org/kilocode)
- Hermes Agent (nousresearch/hermes-agent)

⏳ **Pending**:
- OpenClaw (via awesome-openclaw list)
- Kilo Marketplace
- Pi (getpi/pi)
- Goose (block/goose)
- Cline (cline/cline)
- Aider (Aider-AI/aider)
- Crush (charmbracelet/crush)

---

## Next Steps

1. ✅ Wait for harness clones to complete
2. ⏳ Analyze each harness for unique features
3. ⏳ Clone awesome lists (harness-engineering, mcp-servers, context-engineering)
4. ⏳ Build feature-parity matrix
5. ⏳ Produce 7 workstream plans (§4.6–§4.12)

---

## Key Insights So Far

### What Makes Claude Code Stand Out

1. **Granular permission system** — every tool has allow/deny/ask rules with pattern matching
2. **Multi-provider abstraction** — works across Claude API, Bedrock, Vertex, Foundry
3. **MCP as first-class citizen** — tool search, OAuth, resources, prompts-as-commands
4. **Hooks everywhere** — PreToolUse, PostToolUse, Stop, SessionStart, UserPromptSubmit
5. **Session checkpointing** — rewind code + conversation independently
6. **Plugin ecosystem** — skills + agents + hooks + MCP servers packaged together
7. **LSP integration** — automatic type-checking after edits
8. **Background execution** — long-running processes don't block conversation

### What Lyra Should Prioritize

**P0 (Must-have for feature parity)**:
- LSP integration (code intelligence)
- MCP stdio + HTTP transports
- Permission system with glob patterns
- Hooks (PreToolUse, PostToolUse, Stop)
- Session checkpointing
- Plugin system

**P1 (High-value differentiators)**:
- Tool search (scale to 100+ MCP servers)
- OAuth 2.0 for MCP servers
- Monitor tool (watch logs/files, react mid-conversation)
- Managed settings (enterprise control)
- Background task execution

**P2 (Nice-to-have)**:
- WebFetch with extraction prompt
- WebSearch integration
- PowerShell tool (Windows)
- NotebookEdit (Jupyter)
- Voice dictation

---

## References

- Claude Code Plugins: https://code.claude.com/docs/en/plugins-reference
- Claude Code Tools: https://code.claude.com/docs/en/tools-reference
- Claude Code MCP: https://code.claude.com/docs/en/mcp
- Claude Code Hooks: https://code.claude.com/docs/en/hooks-guide
- Claude Code Permissions: https://code.claude.com/docs/en/permissions
- Claude Code Sessions: https://code.claude.com/docs/en/checkpointing
- Claude Code Commands: https://code.claude.com/docs/en/commands
- Claude Code Interactive Mode: https://code.claude.com/docs/en/interactive-mode
- Claude Code Goals: https://code.claude.com/docs/en/goal
