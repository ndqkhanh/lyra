# Claude Code Deep Research - Complete Feature Inventory

## Executive Summary

Claude Code is Anthropic's official CLI with a comprehensive ecosystem of tools, skills, plugins, agents, and memory systems. This document catalogs every feature for comparison with Lyra.

---

## 1. BUILT-IN TOOLS

### File & Code Operations
- **Read** - Access file contents with line-number formatting
- **Write/Edit** - Create and modify files with atomic operations
- **Glob** - Pattern-based file discovery
- **Grep** - Regex-based content search across files

### Execution & Automation
- **Bash** - Execute shell commands (bash/PowerShell/zsh)
- **WebFetch** - Retrieve and analyze web content
- **WebSearch** - Search the internet for current information
- **Skill** - Invoke custom skills and commands

### Development Workflows
- **Git** - Full version control integration (status, diff, log, commit, branch, push)
- **LSP Tools** - Language server integration:
  - hover
  - goto-definition
  - find-references
  - diagnostics
  - rename

### AI-Specific
- **Extended Thinking** - Deep reasoning for complex problems
- **Prompt Caching** - Optimize token usage for repeated context

**Lyra Comparison**: ✅ Lyra has all these tools + more (Browser, ExecuteCode, pdf_extract, image tools)

---

## 2. SKILLS SYSTEM ⭐ (Agent Skills Standard)

### Structure
- Markdown files with YAML frontmatter in `.claude/skills/<skill-name>/SKILL.md`
- Follows open [Agent Skills standard](https://agentskills.io) - works across 20+ AI tools
- Can include supporting files (templates, examples, scripts)

### Key Frontmatter Fields
```yaml
---
name: my-skill
description: What this skill does (Claude uses this to auto-invoke)
disable-model-invocation: true  # Only you can invoke
user-invocable: false           # Only Claude can invoke
allowed-tools: Bash(git *) Read Write
context: fork                   # Run in isolated subagent
agent: Explore                  # Which agent type to use
paths: "src/**/*.ts"           # Only load for matching files
effort: high                    # Override reasoning level
model: opus                     # Override model
---
```

### Dynamic Context Injection ⭐
- `` !`git diff HEAD` `` syntax runs commands before Claude sees the skill
- Output replaces the placeholder, so Claude gets live data
- Multi-line commands use ` ```! ` fenced blocks

### Skill Scopes
1. **Enterprise**: `/Library/Application Support/ClaudeCode/CLAUDE.md` (org-wide)
2. **Personal**: `~/.claude/skills/<skill-name>/SKILL.md` (all projects)
3. **Project**: `.claude/skills/<skill-name>/SKILL.md` (this project only)
4. **Plugin**: `<plugin>/skills/<skill-name>/SKILL.md` (where plugin is enabled)

### Bundled Skills
- `/simplify`, `/batch`, `/debug`, `/loop`, `/claude-api` (prompt-based, not fixed logic)

### Invocation
- **Manual**: `/skill-name` or `/skill-name argument1 argument2`
- **Automatic**: Claude loads when relevant to conversation
- **String substitution**: `$ARGUMENTS`, `$0`, `$1`, `$name`, `${CLAUDE_SESSION_ID}`, `${CLAUDE_SKILL_DIR}`

**Lyra Comparison**: 
- ✅ Has skill system (`.omc/skills/`, `~/.omc/skills/`)
- ❌ Missing: Dynamic context injection (`` !`command` ``)
- ❌ Missing: Agent Skills standard compliance
- ❌ Missing: `paths` scoping
- ❌ Missing: `context: fork` isolation
- ⚠️ Different: Uses custom format, not Agent Skills standard

---

## 3. PLUGINS SYSTEM ⭐

### What Plugins Can Contain
- Skills (slash commands)
- Custom agents (subagent definitions)
- Hooks (automation rules)
- MCP server configurations
- Settings and permissions

### Plugin Structure
```
my-plugin/
├── plugin.json          # Metadata
├── skills/
│   └── my-skill/SKILL.md
├── agents/
│   └── my-agent/AGENT.md
├── hooks/
│   └── hooks.json
└── mcp-servers/
    └── server-config.json
```

### Installation
- Local directory: `claude --install-plugin ./path/to/plugin`
- Remote registry: `claude --install-plugin plugin-name`
- Marketplace distribution for team/org sharing

### Plugin Marketplaces
- Centralized discovery and version tracking
- Automatic updates
- Support for multiple source types (git, npm, local)

**Lyra Comparison**:
- ✅ Has plugin discovery (`lyra.plugins` entry points)
- ❌ Missing: Plugin marketplace
- ❌ Missing: `plugin.json` standard format
- ❌ Missing: Plugin installation CLI
- ❌ Missing: Bundled skills/agents/hooks in plugins

---

## 4. AGENT SYSTEM

### Subagents (Lightweight Delegation)
- Run within a single session's context window
- Report results back to main agent only
- Lower token cost than agent teams
- Use for focused tasks (research, verification, code review)
- Defined in `.claude/agents/<agent-name>/AGENT.md`

### Agent Teams ⭐ (Experimental - Parallel Coordination)
- Multiple independent Claude Code instances working together
- Shared task list with self-coordination
- Direct inter-agent messaging (not through lead)
- Each teammate has own context window
- Lead coordinates work, assigns tasks, synthesizes results
- Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

### Agent Team Architecture
- **Team lead**: Main session coordinating work
- **Teammates**: Separate instances working on assigned tasks
- **Task list**: Shared work items at `~/.claude/tasks/{team-name}/`
- **Mailbox**: Messaging system for agent communication
- **Team config**: `~/.claude/teams/{team-name}/config.json`

### Agent Team Features
- Plan approval workflow (lead approves before implementation)
- Task dependencies (auto-unblock when dependencies complete)
- Display modes: in-process (default) or split-pane (tmux/iTerm2)
- Graceful shutdown and cleanup
- Quality gates via hooks (`TeammateIdle`, `TaskCreated`, `TaskCompleted`)

### Agent SDK ⭐
- Open-source foundation powering Claude Code
- Available in Python and TypeScript
- Build custom agents with full control over orchestration, tools, permissions
- Same agent loop and context management as Claude Code
- Supports MCP integration, subagents, managed agents

**Lyra Comparison**:
- ✅ Has subagents (Agent tool with isolation)
- ✅ Has agent types (analyst, architect, executor, etc.)
- ✅ Has team orchestration (`/team` command)
- ❌ Missing: Agent Teams with shared task list
- ❌ Missing: Direct inter-agent messaging
- ❌ Missing: Split-pane display mode
- ❌ Missing: Agent SDK (separate from harness)
- ⚠️ Different: Uses OMC team system, not Claude Code's

---

## 5. MEMORY SYSTEMS

### CLAUDE.md Files (Persistent Instructions) ⭐
- Written by you, loaded at every session start
- Markdown files with project context, conventions, standards
- Locations (priority order):
  1. Managed policy: `/Library/Application Support/ClaudeCode/CLAUDE.md` (org-wide)
  2. Project: `./CLAUDE.md` or `./.claude/CLAUDE.md`
  3. User: `~/.claude/CLAUDE.md`
  4. Local: `./CLAUDE.local.md` (gitignored)

### CLAUDE.md Best Practices
- Target under 200 lines (context cost)
- Use markdown headers and bullets for organization
- Be specific: "Use 2-space indentation" not "Format code properly"
- Import additional files: `@path/to/file.md` syntax
- Loaded in full regardless of length (unlike auto memory)

### Path-Scoped Rules ⭐ (.claude/rules/)
- Organize instructions by topic in `.claude/rules/` directory
- Use YAML frontmatter with `paths` field to scope to specific files
- Only load when Claude works with matching files
- Reduce context noise and save tokens

### Auto Memory ⭐ (Claude's Self-Notes)
- Claude writes notes for itself across sessions
- Stores in `~/.claude/projects/<project>/memory/`
- First 200 lines or 25KB of `MEMORY.md` loaded at session start
- Topic files (debugging.md, patterns.md) loaded on demand
- Captures: build commands, debugging insights, preferences, architecture notes
- Enabled by default; toggle with `/memory` or `autoMemoryEnabled` setting
- Machine-local (not shared across devices)

### Memory Hierarchy
1. Managed CLAUDE.md (org-wide, cannot be excluded)
2. Project CLAUDE.md
3. User CLAUDE.md
4. Local CLAUDE.md
5. Path-scoped rules (load on demand)
6. Auto memory (first 200 lines/25KB)

**Lyra Comparison**:
- ✅ Has CLAUDE.md support (project instructions)
- ✅ Has auto memory (`~/.claude/projects/<project>/memory/`)
- ✅ Has path-scoped rules (`~/.claude/rules/`)
- ✅ Has project memory (`.omc/project-memory.json`)
- ✅ Has notepad (`.omc/notepad.md`)
- ✅ Has shared memory (`.omc/shared-memory/`)
- ⚠️ Different: Uses JSON for project memory, not markdown
- ⚠️ Different: Has more memory types (notepad, shared)

---

## 6. CONTEXT MANAGEMENT

### Context Window Handling
- 1M token context window (Claude Opus 4.7)
- Auto-compaction when context fills up
- Sliding window with intelligent summarization

### Compaction Strategy ⭐
- Summarizes conversation history to free space
- Re-attaches most recent skill invocations (first 5,000 tokens each)
- Invoked skills share combined 25,000-token budget
- Project-root CLAUDE.md survives compaction and re-injects
- Nested CLAUDE.md files reload when Claude reads matching files

### What Survives Compaction
- Project-root CLAUDE.md (re-read from disk)
- System prompt and instructions
- Most recent skill invocations (up to budget)
- Current conversation context (summarized)

### Context Visualization
- `/context-window` command shows token usage breakdown
- Skill listing budget configurable via `skillListingBudgetFraction`

**Lyra Comparison**:
- ✅ Has auto-compaction
- ✅ Has 200K token context (Opus 4.7 1M)
- ✅ Has `/compact` command
- ❌ Missing: `/context-window` visualization
- ❌ Missing: Skill budget configuration
- ❌ Missing: Nested CLAUDE.md reload on file read

---

## 7. HOOKS SYSTEM ⭐

### Hook Types
- **File-level**: `FileEdited`, `FileCreated`, `FileDeleted`
- **Task-level**: `TaskCreated`, `TaskCompleted`, `TeammateIdle`
- **Session-level**: `InstructionsLoaded`, `SessionStart`, `SessionEnd`
- **Tool-level**: `BeforeToolCall`, `AfterToolCall`
- **Prompt-based hooks**: Use Claude to evaluate conditions
- **Agent-based hooks**: Delegate decisions to subagents

### Hook Configuration
- Defined in `.claude/settings.json` or `.claude/settings.local.json`
- Can be scoped to skills: `hooks` field in SKILL.md frontmatter
- Exit code 2 to send feedback and prevent action
- Async hooks supported for long-running operations

### Common Use Cases
- Auto-format after file edits
- Run lint before commits
- Send notifications when waiting for input
- Enforce project rules deterministically
- Validate commands before execution

**Lyra Comparison**:
- ✅ Has hooks (PreToolUse, PostToolUse, Stop)
- ✅ Has lifecycle events (SESSION_START, TURN_START, etc.)
- ❌ Missing: File-level hooks (FileEdited, FileCreated, FileDeleted)
- ❌ Missing: Task-level hooks (TaskCreated, TaskCompleted)
- ❌ Missing: Prompt-based hooks
- ❌ Missing: Agent-based hooks
- ❌ Missing: Exit code 2 feedback mechanism
- ⚠️ Different: Simpler hook system

---

## 8. MODEL CONTEXT PROTOCOL (MCP) ⭐

### MCP Servers
- External processes that provide tools and resources
- Connect via stdio, HTTP, or SSE
- Language-agnostic (Python, Node.js, Rust, Go, etc.)
- Installed in `.claude/mcp-servers/` or via plugins

### MCP Capabilities
- **Tools**: Custom functions Claude can call
- **Resources**: Files, APIs, databases Claude can read
- **Prompts**: Pre-built prompt templates
- **Sampling**: Delegate reasoning to external models

### Official MCP Servers
- GitHub, Slack, Google Drive, Jira, Linear, Notion, Stripe, etc.
- Registry at `https://api.anthropic.com/mcp-registry/`

### MCP in Agent SDK
- Full MCP support in Python and TypeScript SDKs
- Can run as external processes or embedded

**Lyra Comparison**:
- ✅ Has MCP support (autoload from `~/.lyra/mcp.json`)
- ✅ Has MCP tool integration (`mcp__<server>__<tool>`)
- ✅ Has MCP client management
- ❌ Missing: MCP registry integration
- ❌ Missing: MCP Resources (only Tools supported)
- ❌ Missing: MCP Prompts
- ❌ Missing: MCP Sampling
- ⚠️ Different: Uses lyra-mcp package, not official SDK

---

## 9. PERMISSION & SECURITY SYSTEM

### Permission Modes
1. **Read-only** (default): No file edits or commands without approval
2. **Ask**: Prompt for approval on each action
3. **Approve-all**: Auto-approve all actions (risky)
4. **Sandbox**: Isolated execution environment
5. **Managed**: Organization-enforced policies

### Permission Rules
- Allow/deny specific tools: `Bash(git *)`, `Write(src/**)`
- Glob patterns for file paths
- Skill-level permissions: `allowed-tools` frontmatter field
- Deny rules checked first (block regardless of other rules)

### Sandbox Isolation ⭐
- Optional sandboxing for untrusted code
- Prevents access to sensitive files/commands
- Configurable via `sandbox.enabled` setting

### Managed Settings ⭐
- Organization-wide policies deployed via MDM/Group Policy
- Cannot be overridden by users
- Separate from CLAUDE.md (settings enforce, CLAUDE.md guides)

**Lyra Comparison**:
- ✅ Has permission modes (normal, strict, yolo)
- ✅ Has tool approval cache
- ✅ Has permission rules in settings
- ❌ Missing: Sandbox isolation
- ❌ Missing: Managed settings (org-wide policies)
- ❌ Missing: Skill-level `allowed-tools`
- ❌ Missing: Deny rules (only allow rules)

---

## 10. UNIQUE FEATURES

### Extended Thinking ⭐
- Deep reasoning for complex problems
- Transparent step-by-step thought process
- Configurable reasoning depth
- Token cost: reasoning tokens billed separately

### Prompt Caching ⭐
- Caches computation from processing previous tokens
- Cached reads cost 10% of normal token price
- Reduces cost for repeated context (large codebases, long conversations)

### Streaming
- Real-time output as Claude works
- Visible in terminal, VS Code, desktop app

### Tool Approval System
- Per-tool approval granularity
- Pre-approval for skills via `allowed-tools`
- Hooks for custom approval logic
- Audit trail of all tool calls

### Multi-Surface Support ⭐
- **Terminal CLI** (full-featured)
- **VS Code extension** (inline diffs, @-mentions, plan review)
- **JetBrains IDEs** (interactive diff viewing)
- **Desktop app** (visual diff review, scheduled tasks, remote control)
- **Web browser** (no local setup, cloud sessions)
- **iOS app** (remote control, task dispatch)

### Session Management ⭐
- `/resume` and `/rewind` to restore previous sessions
- `/teleport` to move sessions between surfaces
- Remote control for working from phone/browser
- Dispatch for task routing from chat

### Scheduled Tasks ⭐
- **Routines**: Run on Anthropic infrastructure (always on)
- **Desktop tasks**: Run locally on your machine
- **`/loop`**: Repeat within a session for quick polling

### Git Integration
- Full workflow support (status, diff, commit, branch, push)
- Automatic commit message generation
- PR creation and management
- GitHub Actions and GitLab CI/CD integration

### Code Review ⭐
- Automatic PR review on every push (GitHub)
- Security scanning
- Test coverage validation
- Performance analysis

**Lyra Comparison**:
- ✅ Has extended thinking (deep_think flag)
- ✅ Has prompt caching support
- ✅ Has streaming
- ✅ Has tool approval
- ✅ Has session management (`--resume`)
- ✅ Has `/loop` command
- ✅ Has git integration
- ❌ Missing: Multi-surface support (only CLI)
- ❌ Missing: `/teleport` between surfaces
- ❌ Missing: Remote control
- ❌ Missing: Scheduled routines (cloud-based)
- ❌ Missing: Automatic PR review
- ❌ Missing: Desktop app
- ❌ Missing: VS Code/JetBrains extensions
- ❌ Missing: iOS app

---

## 11. SETTINGS & CONFIGURATION

### Settings Hierarchy
1. Managed policy (org-wide, cannot override)
2. User settings (`~/.claude/settings.json`)
3. Project settings (`.claude/settings.json`)
4. Local settings (`.claude/settings.local.json`, gitignored)
5. CLI flags (highest priority)

### Key Settings
- `model`: Default model (Opus, Sonnet, Haiku)
- `effort`: Reasoning level (low, medium, high, xhigh, max)
- `permissions`: Permission mode and rules
- `env`: Environment variables
- `autoMemoryEnabled`: Toggle auto memory
- `skillListingBudgetFraction`: Skill description budget
- `claudeMdExcludes`: Skip specific CLAUDE.md files
- `teammatMode`: Agent team display mode (in-process, tmux, auto)

**Lyra Comparison**:
- ✅ Has settings hierarchy (global, project, local)
- ✅ Has model selection
- ✅ Has permission settings
- ✅ Has env vars
- ✅ Has CLI flags
- ❌ Missing: `effort` setting (uses deep_think boolean)
- ❌ Missing: `skillListingBudgetFraction`
- ❌ Missing: `claudeMdExcludes`
- ❌ Missing: `teammatMode`

---

## 12. PRIORITY RANKING

### Must-Have (Core Features)
1. ✅ Tools (Read, Write, Edit, Bash, Git, LSP)
2. ⚠️ Skills system (has it, but not Agent Skills standard)
3. ✅ CLAUDE.md memory
4. ✅ Permission system
5. ⚠️ Hooks for automation (simpler than Claude Code)

### Nice-to-Have (Productivity)
1. ✅ Auto memory
2. ✅ MCP integration (partial - only Tools)
3. ✅ Subagents
4. ❌ Plugins (no marketplace)
5. ✅ Extended thinking
6. ✅ Prompt caching

### Experimental/Advanced
1. ❌ Agent teams (parallel coordination)
2. ❌ Agent SDK (custom agents)
3. ❌ Managed settings (org deployment)
4. ❌ Sandbox isolation
5. ❌ Multi-surface support
6. ❌ Scheduled routines

---

## KEY GAPS TO STEAL

### High Priority
1. **Agent Skills Standard** - Make skills compatible with 20+ AI tools
2. **Dynamic Context Injection** - `` !`command` `` syntax in skills
3. **Plugin Marketplace** - Centralized discovery and distribution
4. **Agent Teams** - Parallel coordination with shared task list
5. **Path-Scoped Rules** - Load rules only for matching files
6. **File-Level Hooks** - FileEdited, FileCreated, FileDeleted
7. **MCP Resources** - Not just Tools, but Resources and Prompts
8. **Sandbox Isolation** - Untrusted code execution

### Medium Priority
1. **Multi-Surface Support** - VS Code, JetBrains, Desktop, Web, iOS
2. **Scheduled Routines** - Cloud-based always-on tasks
3. **Automatic PR Review** - GitHub integration
4. **`/teleport`** - Move sessions between surfaces
5. **Managed Settings** - Org-wide policy enforcement
6. **Context Visualization** - `/context-window` command
7. **Skill Budget Config** - `skillListingBudgetFraction`
8. **Agent-Based Hooks** - Delegate hook decisions to subagents

### Low Priority
1. **Prompt-Based Hooks** - Use Claude to evaluate conditions
2. **Exit Code 2 Feedback** - Hook feedback mechanism
3. **Nested CLAUDE.md Reload** - Reload on file read
4. **MCP Sampling** - Delegate reasoning to external models
5. **Deny Rules** - Block tools regardless of allow rules

---

## SOURCES

- [Claude Code Overview](https://code.claude.com/docs/en/)
- [Extend Claude with Skills](https://code.claude.com/docs/en/skills)
- [Plugins Reference](https://code.claude.com/docs/en/plugins)
- [Orchestrate Teams of Claude Code Sessions](https://code.claude.com/docs/en/agent-teams)
- [How Claude Remembers Your Project](https://code.claude.com/docs/en/memory)
- [Automate Workflows with Hooks](https://code.claude.com/docs/en/hooks-guide)
- [Connect Claude Code to Tools via MCP](https://code.claude.com/docs/en/mcp)
- [Agent SDK Overview](https://docs.claude.com/en/docs/claude-code/sdk/sdk-overview)
- [Building Agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Equipping Agents for the Real World with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Multi-Agent Coordination Patterns](https://claude.com/blog/multi-agent-coordination-patterns)
- [Best Practices for Claude Code](https://www.anthropic.com/engineering/claude-code-best-practices)

---

**Research Completed**: 2026-05-11
**Agent**: Explore (Claude Code)
**Status**: ✅ Complete
