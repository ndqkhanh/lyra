# Claude Code Documentation: Comprehensive Research Analysis

> **Date:** 2026-05-25
> **Sources:** 17+ pages from https://code.claude.com/docs/en/
> **Purpose:** Extract key features, configuration patterns, and identify gaps for Lyra implementation.

---

## Executive Summary

Claude Code represents the state-of-the-art in AI-assisted development tools. This analysis covers 17+ documentation pages, extracting practical implementation patterns, JSON schemas, API contracts, and configuration structures. For each area, we identify what Lyra currently lacks and assign a priority level (Critical/High/Medium/Low).

**Top 5 Critical Gaps:**
1. **Custom Sub-agents with YAML frontmatter** -- Lyra needs a markdown-based subagent definition system
2. **Settings system with 5-level precedence** -- Lyra has basic JSON config, lacks managed/user/project/local/CLI scoping
3. **OpenTelemetry observability** -- Lyra has basic tracing but no OTLP metrics/events/traces export
4. **OS-level sandboxing** -- Lyra has Docker sandbox but lacks macOS Seatbelt / Linux bubblewrap
5. **CLAUDE.md memory system** -- Lyra has advanced memory layers but lacks simple project-instruction file discovery

---

## 1. Sandboxing (OS-Level Tool Isolation)

**URL:** `https://code.claude.com/docs/en/sandboxing`

### Key Features/Capabilities

- **OS-level filesystem and network isolation** for the Bash tool
- **macOS:** Apple Seatbelt (sandbox-exec) -- deny all by default, allowlist specific paths/domains
- **Linux:** bubblewrap (bwrap) -- namespace-based isolation
- **Three approval modes** for sandboxed commands:
  - `auto-allow`: Commands with matching allowlist rules auto-execute
  - `regular`: Standard permission prompts (default)
  - `warn`: Permission prompts even for matching rules (admin enforcement)
- **Path allowlists** via `sandbox.allowedPaths` -- specific directories the sandboxed process can access
- **Domain allowlists** via `sandbox.allowedDomains` -- specific network hosts accessible
- **Excluded commands**: Specific commands can bypass sandbox entirely (e.g., `docker`)
- **Custom proxy**: Sandbox can route traffic through a configured proxy
- **Managed settings enforcement**: Admins can force sandbox configuration org-wide

### Configuration Patterns

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "mode": "regular",
    "allowedPaths": ["/Users/me/project", "/tmp"],
    "allowedDomains": ["api.github.com", "pypi.org", "*.npmjs.org"],
    "excludedCommands": ["docker", "git"],
    "proxy": "http://proxy.corp.example.com:8080",
    "networkAccess": "restricted",
    "readOnlyPaths": [],
    "enableWeakerNestedSandbox": false
  }
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| OS-level sandboxing (macOS Seatbelt) | **Critical** | Lyra has Docker sandbox but no native OS-level isolation for Bash execution |
| Linux bubblewrap integration | **Critical** | Required for Linux deployments |
| Domain allowlists for network isolation | **Critical** | Current sandbox has basic network control, no per-domain allowlists |
| Auto-allow mode for sandboxed commands | **High** | Reduces permission fatigue |
| Excluded commands from sandbox | **High** | Docker, git, etc. should bypass sandbox |
| Managed settings enforcement | **Medium** | Org-wide sandbox policy |
| Custom proxy configuration | **Medium** | Corp environment support |

### Implementation Details

- Claude Code uses macOS `/usr/bin/sandbox-exec` with dynamically generated Seatbelt profiles
- Linux uses `bwrap` with `--unshare-all` for full namespace isolation
- Sandbox profiles are generated per-command invocation, not statically pre-configured
- The `enableWeakerNestedSandbox` flag handles nested container scenarios (Docker-in-sandbox)

---

## 2. Sandbox Environments (6 Isolation Approaches)

**URL:** `https://code.claude.com/docs/en/sandbox-environments`

### Key Features/Capabilities

Six isolation approaches with a comparison matrix:

1. **Sandboxed Bash Tool** (built-in, zero-config) -- Lightweight, per-command OS isolation
2. **`@anthropic-ai/sandbox-runtime`** (SDK) -- Programmatic sandbox for custom agent environments via the SDK
3. **Dev containers** -- `.devcontainer.json` with VS Code / GitHub Codespaces, reproducible environments
4. **Custom containers** -- User-provided Docker images with full OS control
5. **Virtual machines** -- macOS VMs (Parallels, UTM), Linux KVM, full guest isolation
6. **Claude Code on the web** -- Cloud-hosted, no local execution, isolated runner environment

### Configuration Patterns

```jsonc
// .devcontainer/devcontainer.json
{
  "image": "mcr.microsoft.com/devcontainers/universal:2",
  "features": {
    "ghcr.io/devcontainers/features/python:1": {}
  },
  "postCreateCommand": "pip install -r requirements.txt"
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| sandbox-runtime SDK integration | **Medium** | Optional; Docker-based already works |
| Dev container support | **Medium** | Good for team reproducibility |
| Web-based cloud execution | **Low** | Lyra is CLI-first |

---

## 3. Monitoring/Usage (OpenTelemetry)

**URL:** `https://code.claude.com/docs/en/monitoring-usage`

### Key Features/Capabilities

- **OpenTelemetry-based telemetry** with full OTLP protocol support
- **8 metric types** exported as time-series data:
  - Session duration, token usage (input/output/cache), tool call counts, API request counts, cost tracking, permission decisions, model usage, error counts
- **20+ event types** via OTLP logs protocol:
  - `user_prompt`, `llm_request`, `tool_call`, `tool_result`, `permission_decision`, `hook_execution`, `session_start`, `session_end`, `error`, `api_request_body`, `api_response_body`
- **Distributed tracing (beta)** with `claude_code.interaction` root spans
- **8+ environment variables** for configuration
- **Managed settings** for admin-enforced telemetry
- **mTLS support** for secure OTLP export
- **Metrics cardinality control** (session ID, version, account UUID)
- **Privacy controls**: `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_TOOL_DETAILS`, `OTEL_LOG_TOOL_CONTENT`, `OTEL_LOG_RAW_API_BODIES` (all default OFF)

### Configuration Patterns

```bash
# Core telemetry
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer your-token"
export OTEL_METRIC_EXPORT_INTERVAL=60000
export OTEL_LOGS_EXPORT_INTERVAL=5000

# Privacy toggles
export OTEL_LOG_USER_PROMPTS=1
export OTEL_LOG_TOOL_DETAILS=1
export OTEL_LOG_TOOL_CONTENT=1
export OTEL_LOG_RAW_API_BODIES=1  # or file:<dir> for untruncated on disk

# Tracing (beta)
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp

# Cardinality control
export OTEL_METRICS_INCLUDE_SESSION_ID=true
export OTEL_METRICS_INCLUDE_VERSION=false
export OTEL_METRICS_INCLUDE_ACCOUNT_UUID=true
```

### Span Hierarchy

```
claude_code.interaction
  ├── claude_code.llm_request
  ├── claude_code.hook
  └── claude_code.tool
      ├── claude_code.tool.blocked_on_user
      ├── claude_code.tool.execution
      └── (Task tool) subagent spans
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| OTLP metrics export (gRPC/HTTP) | **Critical** | Lyra has `observability/monitoring.py` and `tracing/` but no OTLP metrics protocol |
| Structured event logging to OTLP | **Critical** | Need user_prompt, llm_request, tool_call event types |
| Distributed tracing (W3C traceparent) | **Critical** | Lyra has tracing module but no W3C context propagation |
| Cardinality control for metrics | **High** | Session/version/user ID toggles |
| mTLS for telemetry export | **High** | Secure corp environments |
| Managed/admin-enforced telemetry | **Medium** | Org-wide settings |
| Privacy gates for sensitive data | **Medium** | Redaction of user prompts, tool content |

### Implementation Notes for Lyra

Lyra already has `observability/monitoring.py` and `tracing/` modules. The gap is protocol-level: Lyra needs to emit OTLP-standard metrics via gRPC or HTTP/protobuf, not just log to console/files. The OpenTelemetry Python SDK (`opentelemetry-exporter-otlp-proto-grpc`) should be integrated.

---

## 4. Costs (Token Usage and Spend Management)

**URL:** `https://code.claude.com/docs/en/costs`

### Key Features/Capabilities

- **`/usage` command**: Shows session token breakdown (input, output, cache read, cache write)
- **Workspace spend limits**: `--max-budget-usd` flag for print mode
- **Rate limit recommendations** per team size:
  - Small teams (1-5): Standard tier
  - Medium teams (5-50): Organization tier
  - Large teams (50+): Enterprise tier with higher limits
- **Context management strategies** for cost optimization:
  - Sub-agent delegation for side quests
  - `/compact` for summarizing long conversations
  - CLAUDE.md for persistent instructions (saves input tokens)
- **Agent team cost optimization**: Route tasks to Haiku for simple operations
- **Model selection economics**: Haiku 4.5 at 90% Sonnet capability, 3x cost savings

### Configuration Patterns

```bash
# Spend limit (print mode only)
claude -p --max-budget-usd 5.00 "query"

# Model selection for cost
claude --model haiku
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| `/usage` command with token breakdown | **Critical** | Lyra has `aevo/cost_meter.py` but needs session-level usage display |
| Spend limits per session | **Critical** | `--max-budget-usd` equivalent needed |
| Rate limit management API | **High** | Handle 429s gracefully with backoff |
| Model tier cost routing strategy | **High** | Automatic Haiku for simple tasks, Sonnet/Opus for complex |
| Context cost visualization | **Medium** | Show token usage over session lifetime |

---

## 5. Security (Permission Architecture and Threat Model)

**URL:** `https://code.claude.com/docs/en/security`

### Key Features/Capabilities

- **Permission-based architecture**: Every tool call requires user approval (default)
- **6 permission modes**: Default, Accept Edits, Plan, Auto, Don't Ask, Bypass Permissions
- **Prompt injection protections**: Input sanitization, output validation
- **MCP security**: Server authentication, tool allowlisting
- **IDE security**: Workspace trust model for IDE integrations
- **Credential management**: No hardcoded secrets, env var based auth
- **Cloud execution security**: Isolated runner environments for web sessions

### Configuration Patterns

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npm:*)",
      "Read",
      "Edit"
    ],
    "deny": [
      "Bash(rm:*)",
      "Bash(sudo:*)",
      "Bash(curl:*)"
    ],
    "defaultMode": "default",
    "additionalDirectories": ["/tmp/project2"]
  }
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Granular tool permission rules (allow/deny patterns) | **Critical** | Lyra has hooks but no pattern-based tool permission system |
| Permission mode cycling (Shift+Tab) | **High** | UI toggle between modes |
| Prompt injection detection | **High** | Input sanitization before LLM processing |
| MCP server auth enforcement | **High** | Token-based MCP authentication |
| Workspace trust model | **Medium** | IDE integration safety |

---

## 6. Sub-agents (Custom Sub-agent System)

**URL:** `https://code.claude.com/docs/en/sub-agents`

### Key Features/Capabilities

- **Markdown definition files** with YAML frontmatter
- **5 scope levels** with priority:
  1. Managed settings (org-wide)
  2. CLI `--agents` flag (session)
  3. `.claude/agents/` (project, version-controlled)
  4. `~/.claude/agents/` (user, all projects)
  5. Plugin `agents/` directory
- **Built-in sub-agents**: Explore (Haiku, read-only), Plan (read-only), General-purpose (all tools), statusline-setup, claude-code-guide
- **Forked sub-agents**: Inherit full conversation context for follow-up tasks
- **Background sub-agents**: Run in background, return results when done
- **Recursive sub-directory scanning** for organization

### Configuration Patterns (YAML Frontmatter)

```yaml
---
name: code-reviewer
description: Expert code reviewer. Use proactively after code changes.
tools:
  - Read
  - Grep
  - Glob
  - Bash(git:*)       # Scoped tool rules
  - Bash(npm:*)        # Scoped tool rules
disallowedTools:
  - Bash(rm:*)
  - Bash(sudo:*)
model: sonnet          # haiku, sonnet, opus, or inherit
permissionMode: acceptEdits
maxTurns: 15
skills:
  - code-review
  - security-review
mcpServers:
  github:
    command: npx
    args:
      - "@anthropic/mcp-server-github"
hooks:
  PostToolUse:
    - matcher: Edit
      hooks:
        - command: npx prettier --write $FILE_PATH
memory: user           # user, project, or none
background: true       # Run in background for long tasks
effort: high           # low, medium, high, xhigh, max
isolation: worktree    # worktree or none
color: "#FF6B6B"       # UI color
initialPrompt: |
  Review the code changes for bugs, security issues, and style problems.
---
```

### CLI Sub-agents Definition

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on code quality, security, and best practices.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  },
  "debugger": {
    "description": "Debugging specialist for errors and test failures.",
    "prompt": "You are an expert debugger. Analyze errors, identify root causes, and provide fixes."
  }
}'
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Markdown/YAML sub-agent definition format | **Critical** | Lyra has `agent/` module but no markdown-based definition system |
| 5-level scope priority system (managed > cli > project > user > plugin) | **Critical** | Lyra has no scope hierarchy for agent configs |
| Built-in Explore/Plan/General-purpose agents | **Critical** | Need read-only explore agent with Haiku, plan mode agent |
| Forked sub-agents (inherit context) | **Critical** | Sub-agents with full conversation fork |
| Background sub-agent execution | **High** | Async agent spawning with result collection |
| `/agents` interactive management UI | **High** | TUI for managing sub-agent configs |
| Recursive directory scanning for agents | **Medium** | Organize agents/ into subfolders |
| Color-coded agent UI display | **Medium** | Visual distinction in terminal |
| Persistent per-agent memory directory | **Medium** | `~/.lyra/agent-memory/` for accumulated learning |

---

## 7. Agent SDK Tool Search (Dynamic Tool Discovery)

**URL:** `https://code.claude.com/docs/en/agent-sdk/tool-search`

### Key Features/Capabilities

- **Dynamic tool discovery**: Tools loaded on demand from a catalog of up to 10,000 tools
- **`ENABLE_TOOL_SEARCH` env var** with values: `unset` (auto), `true` (always on), `auto` (500+ tools), `auto:N` (custom threshold), `false` (always off)
- **Model requirements**: Sonnet 4+ and Opus 4+ only
- **Reduced context overhead**: Only relevant tools sent in each request
- **SDK integration**: Tool search is transparent to SDK users

### Configuration Patterns

```bash
export ENABLE_TOOL_SEARCH=true      # Always on
export ENABLE_TOOL_SEARCH=auto      # Auto when 500+ tools loaded
export ENABLE_TOOL_SEARCH=auto:100  # Custom threshold (100 tools)
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Dynamic tool loading/search | **Medium** | Lyra loads all tools eagerly; search optimization useful at scale |
| Tool count threshold auto-enable | **Medium** | Smart activation beyond N registered tools |
| Per-model tool search capability | **Low** | Feature gating by model capability |

---

## 8. Model Configuration

**URL:** `https://code.claude.com/docs/en/model-config`

### Key Features/Capabilities

- **Model aliases**: `default`, `best`, `sonnet`, `opus`, `haiku`, `sonnet[1m]`, `opus[1m]`, `opusplan`
- **Effort levels**: `low`, `medium`, `high`, `xhigh`, `max` (controls reasoning budget)
- **Extended thinking**: Up to 31,999 tokens of internal reasoning
- **1M context window**: Available for `sonnet[1m]` and `opus[1m]` aliases
- **`availableModels`**: Admin restriction of which models users can access
- **`modelOverrides`**: Provider-specific model ID mapping
- **Custom model options**: Environment variables for non-Anthropic providers

### Configuration Patterns

```json
{
  "model": "sonnet",
  "effortLevel": "high",
  "availableModels": ["sonnet", "opus", "haiku"],
  "modelOverrides": {
    "sonnet": "us.anthropic.claude-sonnet-4-6-20250514-v1:0",
    "opus": "us.anthropic.claude-opus-4-5-20251101-v2:0",
    "haiku": "us.anthropic.claude-haiku-4-5-20250514-v1:0"
  }
}
```

```bash
# Environment variables
export ANTHROPIC_MODEL=claude-sonnet-4-6
export ANTHROPIC_DEFAULT_SONNET_MODEL=us.anthropic.claude-sonnet-4-6-20250514-v1:0
export ANTHROPIC_DEFAULT_OPUS_MODEL=us.anthropic.claude-opus-4-5-20251101-v2:0
export ANTHROPIC_DEFAULT_HAIKU_MODEL=us.anthropic.claude-haiku-4-5-20250514-v1:0
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Model alias system (sonnet/opus/haiku) | **Critical** | Lyra uses raw model IDs; need alias resolution layer |
| Effort levels for reasoning budget control | **Critical** | `low`/`medium`/`high`/`xhigh`/`max` mapping to thinking tokens |
| 1M context window flag support | **High** | `[1m]` suffix in model aliases |
| `availableModels` admin restriction | **High** | Organization-level model access control |
| `modelOverrides` for provider-specific IDs | **High** | Map aliases to Bedrock/Vertex-specific ARNs |
| Extended thinking toggle (Option+T) | **Medium** | UI toggle in CLI |

---

## 9. Fast Mode (Optimized Model Variant)

**URL:** `https://code.claude.com/docs/en/fast-mode`

### Key Features/Capabilities

- **2.5x faster Opus** at $30/$150 MTok (input/output)
- **Toggle via `/fast`** command in-session
- **Per-session opt-in** for organization users
- **Separate rate limits** from standard Opus
- **Fast badge indicator** in UI status line

### Configuration Patterns

```bash
claude --model claude-opus-4-5-fast
# Or toggle in-session with /fast command
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Fast mode model variant support | **Medium** | Provider-specific; depends on API availability |
| `/fast` toggle command | **Low** | UI convenience |
| Fast mode rate limit handling | **Low** | Separate rate limit bucket |

---

## 10. Terminal Configuration

**URL:** `https://code.claude.com/docs/en/terminal-config`

### Key Features/Capabilities

- **Shift+Enter for newlines** in input (matrix of platform behaviors)
- **Option key shortcuts**: Option+T for thinking toggle, Option+K for keybindings help
- **Terminal bell/notifications**: Configurable on task completion
- **tmux configuration**: Recommended tmux settings for Claude Code
- **Color themes**: Custom JSON themes in `~/.claude/themes/` directory
- **Fullscreen rendering**: Alt+Enter to toggle
- **Vim keybindings**: Optional Vim navigation mode
- **Input modes**: Bash-style (Ctrl+A/E for line navigation)

### Configuration Patterns

```json
// ~/.claude/themes/my-theme.json
{
  "name": "My Theme",
  "colors": {
    "primary": "#6C8EEB",
    "secondary": "#8B6CEB",
    "background": "#1A1B26",
    "surface": "#24283B",
    "text": "#A9B1D6",
    "subtle": "#565F89",
    "error": "#F7768E",
    "warning": "#E0AF68",
    "success": "#9ECE6A",
    "info": "#7DCFFF"
  },
  "agentColors": {
    "explore": "#7DCFFF",
    "plan": "#BB9AF7",
    "general-purpose": "#9ECE6A"
  }
}
```

```json
// settings.json terminal config
{
  "terminal": {
    "bell": "on-completion",
    "bellDuration": 200,
    "vimMode": false,
    "theme": "my-theme"
  }
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Custom color theme system (JSON themes directory) | **High** | Lyra has basic UI but no theming framework |
| Vim keybindings mode | **Medium** | Optional vim navigation |
| Fullscreen toggle | **Medium** | Alt+Enter rendering |
| Completion notification (bell, desktop) | **Medium** | Terminal bell on task done |
| Agent-specific colors in UI | **Medium** | Color-coded sub-agents |

---

## 11. Settings (Configuration System)

**URL:** `https://code.claude.com/docs/en/settings`

### Key Features/Capabilities

- **5-level settings precedence**: Managed > CLI args > Local > Project > User
- **JSON Schema validation**: `https://json.schemastore.org/claude-code-settings.json`
- **Settings file locations**:
  1. Managed: Deployed via MDM or admin tools
  2. CLI: `--settings` flag (inline JSON or file path)
  3. Local: `.claude/settings.local.json` (gitignored)
  4. Project: `.claude/settings.json` (version-controlled)
  5. User: `~/.claude/settings.json` (all projects)
- **Comprehensive key categories**: General, Attribution, Auth, Env, Permissions, Managed-only, Disable/Block, MCP, Model, Hooks, File Suggestion, Status Line, PR URL, Plans, CLAUDE.md, OTel, Policy Helper, Worktree, Sandbox
- **Permission rule syntax**: Pattern matching with globs and scoping

### Configuration Patterns

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "sonnet",
  "effortLevel": "high",
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(npm:*)",
      "Read",
      "Edit"
    ],
    "deny": [
      "Bash(rm:*)",
      "Bash(sudo:*)"
    ],
    "defaultMode": "default",
    "additionalDirectories": ["/tmp/project2"]
  },
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "command": "npx prettier --write ${CLAUDE_FILE_PATH}"
          }
        ]
      }
    ]
  },
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-github"]
    }
  },
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  },
  "sandbox": {
    "enabled": true,
    "mode": "regular",
    "allowedPaths": ["/Users/me/project"],
    "allowedDomains": ["api.github.com", "*.npmjs.org"]
  },
  "plugins": {
    "my-plugin": {
      "enabled": true
    }
  },
  "worktree": {
    "baseRef": "fresh",
    "autoCleanup": true
  }
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| 5-level settings precedence system | **Critical** | Lyra has single `~/.lyra/config.json`; needs managed > cli > local > project > user hierarchy |
| JSON Schema validation for settings | **Critical** | No schema reference URL or validation |
| Permission rule syntax (globs + scoping) | **Critical** | Pattern-based allow/deny for tools |
| Settings file at multiple scopes | **Critical** | Need `.lyra/settings.json`, `.lyra/settings.local.json`, `~/.lyra/settings.json` |
| Managed (admin-enforced) settings | **High** | MDM-deployable config for orgs |
| CLI `--settings` flag | **High** | Per-session settings override |
| Env key in settings for injecting env vars | **High** | Configure environment from settings file |
| Hook configuration in settings | **High** | Declarative hook definitions |
| MCP server configuration in settings | **High** | Server definitions |
| Sandbox configuration in settings | **High** | Sandbox policy |
| Status line configuration | **Medium** | Custom status bar scripts |
| Worktree configuration | **Medium** | Git worktree defaults |

---

## 12. Channels Reference (MCP Event Channels)

**URL:** `https://code.claude.com/docs/en/channels-reference`

### Key Features/Capabilities

- **MCP-based channel architecture**: Servers push events into Claude Code sessions
- **`claude/channel` capability**: MCP server capability declaration
- **Notification format**: `notifications/message` with `content` and `meta` params
- **Reply tools**: Channels can register reply/action tools Claude can invoke
- **Sender gating**: Filter notifications by sender identity
- **Permission relay**: Channels can relay permission decisions
- **Research preview feature**: Gated behind allowlist

### Configuration Patterns

```bash
# Load channels from a plugin
claude --channels plugin:my-notifier@my-marketplace

# Development channels (local testing)
claude --dangerously-load-development-channels server:webhook
```

### Notification Format

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info",
    "content": "Build completed successfully",
    "meta": {
      "sender": "ci-cd-bot",
      "timestamp": "2026-05-25T12:00:00Z",
      "priority": "high",
      "actions": [
        {
          "label": "View logs",
          "tool": "view_logs",
          "params": {"build_id": "12345"}
        }
      ]
    }
  }
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| MCP channel architecture | **Medium** | Lyra has `channels/` module (discord, slack, etc.) but not MCP-based channel protocol |
| `claude/channel` capability protocol | **Medium** | Standardized MCP channel registration |
| Notification reply tools | **Medium** | Interactive channel actions |
| Sender gating and permission relay | **Low** | Security filtering |

---

## 13. Glossary (~70 Terms)

**URL:** `https://code.claude.com/docs/en/glossary`

### Key Terms Relevant to Lyra Implementation

| Term | Definition | Lyra Status |
|------|-----------|-------------|
| **Agent** | AI model that can use tools and make decisions | Lyra has `agent/` module |
| **Sub-agent** | Specialized agent spawned by parent for specific tasks | **Gap**: No markdown-based definition |
| **Hooks** | Scripts that run before/after tool execution | Lyra has `hooks/` module |
| **Skills** | User-defined slash commands | Lyra has `skills/` module |
| **MCP** | Model Context Protocol for server integration | Lyra has `mcp/` module |
| **Sandboxing** | OS-level isolation for code execution | **Gap**: No native OS sandbox |
| **Worktree** | Isolated git worktree for parallel development | **Gap**: No git worktree support |
| **Compaction** | Summarizing conversation to save context | Lyra has `compression/` module |
| **Plugins** | Distributable packages extending functionality | **Gap**: No plugin system |
| **Background agent** | Agent running independently, monitored remotely | **Gap**: No daemon/supervisor |
| **Permission modes** | Configurable approval levels | **Gap**: No mode system |
| **CLAUDE.md** | Project instructions file loaded at startup | **Partial**: Lyra has blueprint files |
| **Memory** | Persistent learning across sessions | Lyra has `memory/` with L0-L6 layers |

---

## 14. CLI Reference (40+ Commands, 60+ Flags)

**URL:** `https://code.claude.com/docs/en/cli-reference`

### Key Features/Capabilities

- **40+ CLI commands** for session management, auth, updates, plugins, MCP
- **60+ CLI flags** for customization, modes, tools, system prompts
- **Non-interactive mode** (`-p`/`--print`): SDK-style query and exit
- **Session management**: `--continue` (`-c`), `--resume` (`-r <id>`), `--fork-session`
- **Input/output formats**: `text`, `json`, `stream-json` with `--output-format`
- **Structured output**: `--json-schema` for validated JSON responses
- **Worktree support**: `--worktree` (`-w`) with `--tmux` for isolated branches
- **Background sessions**: `--bg` to detach and run independently
- **System prompt flags**: `--system-prompt`, `--append-system-prompt`, file variants
- **Bare mode**: `--bare` for minimal, scripted invocations

### Command Categories

**Session Management:**
```
claude                    # Interactive session
claude -p "query"         # Print mode (SDK)
cat file | claude -p "q"  # Piped input
claude -c                 # Continue last session
claude -r <id> "query"    # Resume by ID/name
```

**Agent Management:**
```
claude agents             # Agent view (monitor/control)
claude agents --json      # Machine-readable output
claude attach <id>        # Attach to background session
claude bg "task"          # Start background agent
claude stop <id>          # Stop background session
claude logs <id>          # View session logs
```

**Administration:**
```
claude update             # Update to latest
claude auth login         # Authenticate
claude auth status        # Check auth status
claude setup-token        # Long-lived OAuth token
claude mcp                # MCP configuration
claude plugin             # Plugin management
claude project purge      # Clear project state
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Print/headless mode (`-p`) | **Critical** | Lyra needs non-interactive SDK mode |
| `--output-format json/stream-json` | **Critical** | Structured output for automation |
| `--json-schema` for validated output | **Critical** | Structured outputs with schema validation |
| Session resume by ID/name | **Critical** | `-r <id>`, `-c` equivalents |
| `--continue` for last session | **High** | Quick resume |
| `--bg` / background sessions | **High** | Detach and run independently |
| `--tools` / `--allowedTools` flags | **High** | Per-session tool restrictions |
| `--effort` flag | **High** | Per-session effort level |
| `--max-turns` flag | **High** | Turn limit for scripts |
| `--max-budget-usd` flag | **High** | Spend cap |
| `--worktree` / `-w` | **Medium** | Git worktree isolation |
| `--bare` mode | **Medium** | Fast scripted startup |
| `--system-prompt` / `--append-system-prompt` | **Medium** | Custom prompt injection |

---

## 15. Environment Variables (120+ Variables)

**URL:** `https://code.claude.com/docs/en/env-vars`

### Key Categories

**Auth/API Keys:**
```bash
ANTHROPIC_API_KEY
ANTHROPIC_AUTH_TOKEN
CLAUDE_CODE_OAUTH_CLIENT_ID
```

**API Endpoints:**
```bash
ANTHROPIC_BASE_URL
CLAUDE_CODE_API_KEY_SOURCE  # anthropic, bedrock, vertex, openai_compatible
```

**Model Configuration:**
```bash
ANTHROPIC_MODEL
ANTHROPIC_DEFAULT_SONNET_MODEL
ANTHROPIC_DEFAULT_OPUS_MODEL
ANTHROPIC_DEFAULT_HAIKU_MODEL
ANTHROPIC_MAX_TOKENS
ANTHROPIC_THINKING_BUDGET
MAX_THINKING_TOKENS
```

**Bash/Tool Execution:**
```bash
CLAUDE_CODE_SANDBOX_MODE   # auto-allow, regular, warn
CLAUDE_CODE_MAX_OUTPUT_TOKENS
CLAUDE_CODE_IDE_SKIP_AUTO_CONNECT
```

**Context/Compaction:**
```bash
CLAUDE_CODE_MAX_CONTEXT_TOKENS
CLAUDE_CODE_COMPACT_AT_PERCENT
CLAUDE_CODE_SKIP_COMPACTION_PROMPT
```

**Agent/Task:**
```bash
CLAUDE_CODE_SUBAGENT_MAX_TURNS
CLAUDE_CODE_FORK_SUBAGENT
CLAUDE_CODE_ENABLE_PARALLEL_TOOLS
OMC_SUBAGENT_MODEL
```

**Memory/Context Files:**
```bash
CLAUDE_CODE_SKIP_PROMPT_HISTORY
CLAUDE_CODE_SKIP_CLAUDE_MD
CLAUDE_CODE_CLAUDE_MD_PATH
```

**UI/Rendering:**
```bash
CLAUDE_CODE_THEME
CLAUDE_CODE_TERMINAL_FONT_SIZE
CLAUDE_CODE_DISABLE_COLORS
```

**Telemetry:**
```bash
CLAUDE_CODE_ENABLE_TELEMETRY
OTEL_METRICS_EXPORTER
OTEL_LOGS_EXPORTER
OTEL_TRACES_EXPORTER
OTEL_EXPORTER_OTLP_ENDPOINT
OTEL_EXPORTER_OTLP_HEADERS
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA
OTEL_LOG_USER_PROMPTS
OTEL_LOG_TOOL_DETAILS
OTEL_LOG_TOOL_CONTENT
OTEL_LOG_RAW_API_BODIES
```

**Feature Toggles:**
```bash
ENABLE_TOOL_SEARCH
CLAUDE_CODE_ENABLE_BACKGROUND_AGENTS
CLAUDE_CODE_SIMPLE              # Bare mode
CLAUDE_CODE_DISABLE_NON_ESSENTIAL_TOOLS
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Comprehensive env var system (120+ vars) | **Critical** | Lyra has scattered env vars; needs organized, documented system |
| `CLAUDE_CODE_SKIP_CLAUDE_MD` equivalent | **Critical** | Control over project instruction loading |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | **High** | Context window management |
| `CLAUDE_CODE_COMPACT_AT_PERCENT` | **High** | Auto-compaction trigger |
| `CLAUDE_CODE_SANDBOX_MODE` | **High** | Sandbox behavior control |

---

## 16. Tools Reference (30+ Built-in Tools)

**URL:** `https://code.claude.com/docs/en/tools`

### Complete Tool Inventory

**Core Tools:**
| Tool | Description | Permission | Lyra Status |
|------|-------------|-----------|-------------|
| `Agent` | Create sub-agent for multi-step tasks | Requires user approval | Partial (agent module) |
| `AskUserQuestion` | Ask user a clarifying question | Auto | Missing |
| `Bash` | Execute shell commands | Requires user approval | Has sandbox |
| `Edit` | Edit files with exact string replacement | Auto (by mode) | Has |
| `Read` | Read files from filesystem | Auto | Has |
| `Write` | Write files to filesystem | Requires user approval | Has |
| `Glob` | Find files by pattern | Auto | Has |
| `Grep` | Search file contents | Auto | Has |
| `WebFetch` | Fetch URL content | Requires user approval | Has |
| `WebSearch` | Search the web | Requires user approval | Has |

**Task/Agent Management:**
| Tool | Description | Lyra Status |
|------|-------------|-------------|
| `TaskCreate/Get/List/Output/Stop/Update` | Sub-agent lifecycle management | Missing |
| `SendMessage` | Send message to background sub-agent | Missing |
| `TeamCreate/Delete` | Agent team management | Partial (orchestration) |

**Session Management:**
| Tool | Description | Lyra Status |
|------|-------------|-------------|
| `EnterPlanMode/ExitPlanMode` | Plan mode toggle | Missing |
| `EnterWorktree/ExitWorktree` | Git worktree management | Missing |
| `TodoWrite` | Task tracking | Partial |
| `Skill` | Invoke skills/slash commands | Has |

**Monitoring/Observability:**
| Tool | Description | Lyra Status |
|------|-------------|-------------|
| `Monitor` | Run a monitor (shell-based watcher) | Missing |
| `PushNotification` | Push notification to user | Missing |

**Advanced:**
| Tool | Description | Lyra Status |
|------|-------------|-------------|
| `LSP` | Language server protocol operations | Partial |
| `NotebookEdit` | Jupyter notebook editing | Missing |
| `ToolSearch` | Dynamic tool discovery | Missing |
| `CronCreate/Delete/List` | Scheduled tasks | Missing |
| `ScheduleWakeup` | Wake from sleep | Missing |
| `RemoteTrigger` | Remote control trigger | Missing |
| `ShareOnboardingGuide` | Onboarding guide generation | N/A |
| `WaitForMcpServers` | MCP server readiness check | Missing |

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Task/Sub-agent lifecycle tools | **Critical** | TaskCreate/Get/Output/Stop for agent management |
| Permission mode tools (PlanMode) | **Critical** | Enter/Exit plan mode |
| Worktree management tools | **High** | Git worktree isolation |
| Monitor tool (watchers/observers) | **High** | Shell-based file watchers |
| Push notification tool | **Medium** | User notification |
| NotebookEdit tool | **Medium** | .ipynb support |
| Cron/Scheduled task tools | **Medium** | Time-based execution |
| ToolSearch (dynamic loading) | **Low** | Scale-dependent |
| RemoteControl | **Low** | Web/mobile control |

---

## 17. Commands (50+ Built-in Commands and Bundled Skills)

**URL:** `https://code.claude.com/docs/en/commands`

### Key Features/Capabilities

- **50+ built-in commands** accessed via `/` prefix
- **Bundled skills**: Extensible via the skills mechanism
- **Context-sensitive availability**: Commands vary by platform, plan, environment
- **Argument support**: `<arg>` required, `[arg]` optional

### Command Inventory by Workflow Phase

**Setup/Configuration:**
```
/init              # Generate starter CLAUDE.md
/memory            # Refine project memory
/mcp               # Configure MCP servers
/agents            # Manage sub-agents
/permissions       # Set approval rules
/statusline        # Configure status line
/theme             # Select/configure theme
/chrome            # Chrome integration settings
```

**During Development:**
```
/plan              # Switch to plan mode
/model             # Switch model
/effort            # Adjust effort level
/fast              # Toggle fast mode
/context           # Show context window usage
/compact           # Summarize conversation
/btw <question>    # Side question (excluded from history)
/bg / /background  # Detach to background
/tasks             # List background tasks
/diff              # Show changes
/add-dir <path>    # Add working directory
/ide               # Connect to IDE
/terminal-config   # Terminal settings
```

**Code Review/Quality:**
```
/code-review       # Review changes for bugs
/review            # Deep read-only review
/security-review   # Security analysis
/lint              # Run linter
/test              # Run tests
```

**Session Management:**
```
/clear             # Start fresh (keep memory)
/resume            # Resume earlier conversation
/branch [name]     # Fork conversation
/rename [name]     # Name current session
/teleport          # Pull web session to local
/remote-control    # Enable remote control
```

**Troubleshooting:**
```
/rewind            # Roll back to checkpoint
/doctor            # Diagnose issues
/debug             # Enable debug mode
/feedback          # Report bug with context
```

**Advanced Workflows:**
```
/batch <instr>     # Parallel worktree-based batch processing
/autofix-pr        # Auto-fix CI failures on PRs
/upgrade           # Upgrade subscription plan
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| `/init` to generate CLAUDE.md equivalent | **Critical** | Auto-generate project memory file |
| `/plan` mode toggle | **Critical** | Plan mode for structured approach |
| `/model` model switching | **Critical** | In-session model change |
| `/effort` effort level adjustment | **Critical** | Reasoning budget control |
| `/compact` conversation summary | **Critical** | Lyra has compression but no user-facing command |
| `/diff` change overview | **Critical** | Show what changed in session |
| `/code-review` automated review | **High** | Built-in review command |
| `/review` / `/security-review` | **High** | Deep review passes |
| `/clear` fresh start | **High** | Reset conversation, keep memory |
| `/context` window usage display | **High** | Token usage visualization |
| `/btw` side questions | **Medium** | Excluded from history |
| `/batch` parallel worktree processing | **Medium** | Large-scale automated changes |
| `/autofix-pr` | **Medium** | CI failure auto-fix |
| `/rewind` checkpoint rollback | **Medium** | Time-travel debugging |
| `/doctor` diagnostics | **Medium** | Self-diagnosis |
| `/teleport` / `/remote-control` | **Low** | Multi-device |

---

## 18. Plugins Reference (Plugin System)

**URL:** `https://code.claude.com/docs/en/plugins-reference`

### Key Features/Capabilities

- **Plugin components**: Skills (`SKILL.md`), Agents (markdown files), Hooks, MCP servers, LSP servers, Monitors
- **Installation scopes**: User (`~/.claude/plugins/`), Project (`.claude/plugins/`), Local (gitignored)
- **Marketplace distribution**: Plugins distributed via plugin marketplaces
- **Plugin manifest**: `plugin.json` with metadata and configuration
- **CLI management**: `claude plugin install/list/uninstall/enable/disable`

### Configuration Patterns

```jsonc
// plugin.json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Custom plugin for Claude Code",
  "author": "Developer Name",
  "components": {
    "skills": ["skills/"],
    "agents": ["agents/"],
    "hooks": ["hooks/"],
    "mcpServers": ["mcp/"],
    "lspServers": ["lsp/"],
    "monitors": ["monitors/"]
  }
}
```

### Skill Structure

```markdown
---
name: my-skill
description: A custom skill for specific tasks
---

# My Skill

## Instructions

Detailed instructions for Claude on how to execute this skill.
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Plugin system with component packaging | **High** | Lyra has skills but no plugin packaging/distribution |
| Plugin marketplace architecture | **Medium** | Distribution mechanism |
| `plugin.json` manifest format | **Medium** | Standardized metadata |
| Plugin CLI management | **Medium** | install/list/uninstall/enable/disable |
| Multi-scope plugin installation | **Medium** | User/project/local scopes |

---

## 19. Status Line (Customizable Status Bar)

**URL:** `https://code.claude.com/docs/en/status-line`

### Key Features/Capabilities

- **Shell script-based**: Any executable that receives JSON on stdin
- **Real-time updates**: Refreshes on session state changes
- **Available data fields**: Model name, context usage (tokens/percentage), cost (USD), duration, git branch, session name, working directory, permission mode, sub-agent count
- **Multi-line support**: Output multiple lines for complex displays
- **Color coding**: ANSI escape codes in output
- **Progress bars**: Context window visualization

### Configuration Patterns

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
}
```

### Input JSON Schema (delivered to script via stdin)

```json
{
  "model": "claude-sonnet-4-6",
  "contextWindow": {
    "used": 45000,
    "total": 200000,
    "percent": 22.5
  },
  "cost": {
    "total": 1.23,
    "currency": "USD"
  },
  "duration": "00:15:30",
  "git": {
    "branch": "feature/auth",
    "dirty": true
  },
  "session": {
    "name": "auth-refactor",
    "id": "abc123"
  },
  "workingDirectory": "/Users/me/project",
  "permissionMode": "default",
  "subAgentCount": 2
}
```

### What Lyra Lacks

| Feature | Priority | Notes |
|---------|----------|-------|
| Custom status line via external script | **High** | Lyra has basic UI but no customizable status bar |
| Real-time context window visualization | **High** | Token usage progress bar |
| Cost tracking display | **High** | Per-session cost in status line |
| Multi-line status bar | **Medium** | Rich status display |

---

## Overall Gap Analysis and Implementation Roadmap

### Critical Priority (Must Implement First)

These are table-stakes features that Claude Code agents expect from their environment:

1. **Custom Sub-agents with YAML frontmatter**
   - Files: Create `packages/lyra-cli/src/lyra_cli/agents/` with markdown parser, scope resolution (managed > cli > project > user > plugin)
   - Effort: Large (8-10 weeks)
   - Dependencies: Settings system, permission system

2. **5-Level Settings Precedence System**
   - Files: Refactor `config.py` to support managed, CLI args, local, project, user scopes
   - Effort: Medium (4-6 weeks)
   - Dependencies: None

3. **OpenTelemetry Observability (OTLP Export)**
   - Files: Extend `observability/` and `tracing/` with OTLP exporters
   - Effort: Medium (4-6 weeks)
   - Dependencies: OpenTelemetry Python SDK

4. **OS-Level Sandboxing (Seatbelt + Bubblewrap)**
   - Files: Create `sandbox/native_sandbox.py` with macOS Seatbelt and Linux bubblewrap
   - Effort: Large (6-8 weeks)
   - Dependencies: None (OS-specific)

5. **CLAUDE.md Memory System**
   - Files: Create file discovery, loading, and merging system
   - Effort: Small (2-3 weeks)
   - Dependencies: Settings system

6. **Print/Headless Mode (`-p`)**
   - Files: Create headless execution path with structured output
   - Effort: Medium (4-6 weeks)
   - Dependencies: None

7. **Granular Permission Rules**
   - Files: Create permission engine with pattern matching (globs, scoping)
   - Effort: Medium (4-6 weeks)
   - Dependencies: Settings system

8. **Model Alias System**
   - Files: Create alias resolver mapping (sonnet/opus/haiku) to provider-specific IDs
   - Effort: Small (2-3 weeks)
   - Dependencies: Settings system

### High Priority (Should Implement Next)

9. **Task/Sub-agent Lifecycle Tools**
   - Files: Implement TaskCreate/Get/List/Stop/Output tools
   - Effort: Medium (4-6 weeks)
   - Dependencies: Sub-agent system

10. **In-Session Commands (/model, /effort, /compact, /diff, /context)**
    - Files: Create command registry and implementations
    - Effort: Medium (3-5 weeks)
    - Dependencies: Settings, model alias system

11. **Permission Mode System (6 modes)**
    - Files: Implement mode cycling, Shift+Tab UI
    - Effort: Medium (3-5 weeks)
    - Dependencies: Permission rules engine

12. **Background Agent Execution (--bg)**
    - Files: Create daemon/supervisor process
    - Effort: Large (6-8 weeks)
    - Dependencies: Sub-agent system

13. **Plugin System**
    - Files: Create plugin packaging, installation, CLI management
    - Effort: Large (6-8 weeks)
    - Dependencies: Settings system

14. **Custom Status Line**
    - Files: Create status bar script integration
    - Effort: Small (2-3 weeks)
    - Dependencies: Observability

15. **MCP Channel Architecture**
    - Files: Extend `channels/` with MCP-based event protocol
    - Effort: Medium (3-5 weeks)
    - Dependencies: MCP integration

### Medium Priority (Implement When Core is Stable)

16. Worktree management (Enter/ExitWorktree tools)
17. Forked sub-agents (context inheritance)
18. Dynamic tool search (ToolSearch)
19. Monitor tool (file watchers)
20. `/batch` parallel processing
21. Custom color theme system
22. Vim keybindings mode
23. `/btw` side questions
24. Session resume by ID/name
25. Git worktree support (`--worktree` / `-w`)

### Low Priority (Nice to Have)

26. Fast mode support
27. Dev container support
28. Web-based cloud execution
29. Remote control (web/mobile)
30. NotebookEdit tool
31. Cron/Scheduled tasks

---

## JSON Schema and API Pattern Reference

### Settings Schema (Simplified)

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "type": "object",
  "properties": {
    "model": { "type": "string" },
    "effortLevel": { "enum": ["low", "medium", "high", "xhigh", "max"] },
    "permissions": {
      "type": "object",
      "properties": {
        "allow": { "type": "array", "items": { "type": "string" } },
        "deny": { "type": "array", "items": { "type": "string" } },
        "defaultMode": { "enum": ["default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"] },
        "additionalDirectories": { "type": "array", "items": { "type": "string" } }
      }
    },
    "hooks": { "$ref": "#/definitions/hooksConfig" },
    "mcpServers": { "$ref": "#/definitions/mcpServersConfig" },
    "sandbox": { "$ref": "#/definitions/sandboxConfig" },
    "plugins": { "type": "object" },
    "statusLine": { "$ref": "#/definitions/statusLineConfig" },
    "env": { "type": "object", "additionalProperties": { "type": "string" } }
  }
}
```

### Sub-agent Frontmatter Schema

```yaml
# Required fields
name: string              # Unique identifier
description: string       # When Claude should use this agent

# Optional fields
tools: string[]           # Tool names (scoped with ToolName(rule:*) syntax)
disallowedTools: string[] # Deny patterns
model: sonnet|opus|haiku|inherit  # Model selection
permissionMode: default|acceptEdits|plan|auto|dontAsk|bypassPermissions
maxTurns: number           # Turn limit
skills: string[]            # Skill names to load
mcpServers: object          # MCP server configs
hooks: object               # Hook definitions
memory: user|project|none   # Persistent memory scope
background: boolean         # Run in background
effort: low|medium|high|xhigh|max  # Reasoning budget
isolation: worktree|none    # Execution isolation
color: string               # UI color (#RRGGBB)
initialPrompt: string       # First message to sub-agent
```

### Permission Rule Syntax

```
ToolName                    # Allow/deny entire tool
ToolName(pattern:*)         # Allow/deny matching calls only
ToolName(exact:match)       # Allow/deny exact call only
```

Examples:
- `Bash(git:*)` -- Allow all git commands
- `Bash(rm:*)` -- Deny all rm commands
- `Read` -- Allow all file reads
- `Edit` -- Allow all file edits

---

## Appendix: Lyra Module Mapping

| Claude Code Feature | Lyra Module | Gap |
|--------------------|-------------|-----|
| Sub-agents | `agent/`, `orchestration/` | No markdown definition, no scope hierarchy |
| Hooks | `hooks/` | Functional but needs settings integration |
| Skills | `skills/`, `skills_enhanced/`, `skills_integration/` | Rich skills, needs plugin packaging |
| MCP | `mcp/`, `mcp_integration/` | Functional, needs channel protocol |
| Memory | `memory/` (L0-L6 layers) | Rich memory, needs CLAUDE.md discovery |
| Sandbox | `sandbox/` (Docker) | Needs OS-native sandbox |
| Observability | `observability/`, `tracing/` | Needs OTLP export |
| Evolution | `evolution/` | Self-improvement loop |
| Compression | `compression/` | Functional, needs /compact command |
| Channels | `channels/` (Slack, Discord, etc.) | Functional, needs MCP channel protocol |
| Config | `config.py` | Needs 5-level precedence |
| Provider | `providers/`, `llm_router.py` | Functional, needs model aliases |
| Aevo | `aevo/` | Self-evolution harness |
| UI | `interactive/`, `ui/` | Functional, needs theme system, status line |

---

*Research completed 2026-05-25. All 17+ Claude Code documentation pages analyzed.*
