# MCP, Hooks, Automation & Integration Systems Research

**Date:** 2026-05-29  
**Status:** Complete  
**Research Scope:** Model Context Protocol, Hooks System, Automation Workflows, Commands, Credentials & Security

---

## Executive Summary

This research provides comprehensive analysis of Claude Code's integration systems and proposes architecture for Lyra's MCP integration, hooks framework, automation engine, and command system.

**Key Findings:**
1. **MCP Protocol** - Standardized tool integration with 3 transports (HTTP, SSE, stdio)
2. **Hooks System** - 5 hook types across 12+ lifecycle events
3. **Goal-Based Automation** - Model-evaluated completion conditions
4. **Commands Architecture** - Unified command registry with plugin extensibility
5. **Security Model** - Multi-layer credential management with OAuth 2.0

**Current Lyra State:**
- 93 packages, 55,437 Python files
- Basic MCP manager (92 lines)
- Simple command registry (87 lines)
- Hook registry foundation (164 lines)
- **Gap:** No MCP client, limited hook types, no automation engine

---

## Table of Contents

1. [Model Context Protocol (MCP)](#1-model-context-protocol-mcp)
2. [Hooks System Architecture](#2-hooks-system-architecture)
3. [Automation & Workflows](#3-automation--workflows)
4. [Commands System](#4-commands-system)
5. [Credentials & Security](#5-credentials--security)
6. [Lyra Integration Architecture](#6-lyra-integration-architecture)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Model Context Protocol (MCP)

### 1.1 Protocol Overview

MCP is an open standard for AI-tool integrations enabling Claude Code to connect to external systems.

**Core Capabilities:**
- **Tools** - Executable functions with parameters
- **Resources** - @-mentionable content (files, docs, data)
- **Prompts** - Reusable prompt templates as commands
- **Sampling** - LLM completion requests from servers

**Transport Types:**

| Transport | Use Case | Connection |
|-----------|----------|------------|
| **HTTP** (Streamable) | Remote cloud services | POST to `/mcp` endpoint |
| **SSE** (Deprecated) | Legacy remote servers | Server-sent events |
| **stdio** | Local processes | stdin/stdout communication |

**Key Features:**
- **Dynamic tool updates** - `list_changed` notifications
- **OAuth 2.0 authentication** - Automatic token refresh
- **Tool search** - Deferred loading for large tool sets
- **Elicitation** - Mid-task user input requests
- **Resources as @mentions** - `@server:protocol://path`
- **Prompts as commands** - `/mcp__server__prompt`

### 1.2 MCP Server Configuration

**Scope Hierarchy:**
1. **Local scope** - Project-specific, private (`~/.claude.json`)
2. **Project scope** - Team-shared (`.mcp.json` in repo)
3. **User scope** - Cross-project, private (`~/.claude.json`)
4. **Plugin-provided** - Bundled with plugins
5. **Claude.ai connectors** - Synced from web

**Configuration Schema:**
```json
{
  "mcpServers": {
    "server-name": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      },
      "oauth": {
        "clientId": "...",
        "callbackPort": 8080
      },
      "timeout": 600000,
      "alwaysLoad": false
    }
  }
}
```

**Environment Variable Expansion:**
- `${VAR}` - Required variable
- `${VAR:-default}` - Variable with fallback
- `${CLAUDE_PROJECT_DIR}` - Project root path
- `${CLAUDE_PLUGIN_ROOT}` - Plugin installation directory
- `${CLAUDE_PLUGIN_DATA}` - Plugin persistent data

### 1.3 MCP Tool Search

**Problem:** Loading 1000+ tools upfront consumes context window

**Solution:** Deferred loading with on-demand discovery

**How it works:**
1. Only tool names load at session start
2. Claude uses `ToolSearch` to find relevant tools
3. Only used tools enter context
4. Server instructions guide discovery

**Configuration:**
```bash
# Default: all tools deferred
ENABLE_TOOL_SEARCH=true

# Threshold mode: defer only overflow
ENABLE_TOOL_SEARCH=auto:10  # 10% threshold

# Disable: load all upfront
ENABLE_TOOL_SEARCH=false
```

**Per-server override:**
```json
{
  "mcpServers": {
    "core-tools": {
      "alwaysLoad": true  // Never defer
    }
  }
}
```

### 1.4 MCP Authentication

**OAuth 2.0 Flow:**
1. Server responds with 401/403
2. Claude Code marks server as needing auth
3. User runs `/mcp` to start OAuth flow
4. Browser opens for authorization
5. Tokens stored securely in keychain
6. Automatic refresh on expiry

**Pre-configured credentials:**
```bash
claude mcp add --transport http \
  --client-id your-client-id \
  --client-secret \
  --callback-port 8080 \
  my-server https://mcp.example.com/mcp
```

**Custom authentication (non-OAuth):**
```json
{
  "headersHelper": "/opt/bin/get-auth-headers.sh"
}
```

The helper runs on each connection and outputs JSON headers.

---

## 2. Hooks System Architecture

### 2.1 Hook Types

Claude Code supports 5 hook types for different execution contexts:

| Type | Purpose | Input | Output |
|------|---------|-------|--------|
| **command** | Shell script execution | JSON via stdin | JSON via stdout |
| **http** | HTTP POST request | JSON body | JSON response |
| **mcp_tool** | Call MCP server tool | Tool parameters | Tool result |
| **prompt** | LLM yes/no decision | Prompt + context | Boolean decision |
| **agent** | Spawn subagent | Full context | Agent result |

### 2.2 Hook Lifecycle Events

**Per-session events:**
- `SessionStart` - Session initialization
- `SessionEnd` - Session cleanup
- `Setup` - First-time project setup

**Per-turn events:**
- `UserPromptSubmit` - Before processing user input
- `UserPromptExpansion` - After expanding @mentions
- `Stop` - After Claude finishes response
- `StopFailure` - When response fails

**Per-tool events:**
- `PreToolUse` - Before tool execution (can block/modify)
- `PermissionRequest` - When permission needed
- `PermissionDenied` - When permission denied
- `PostToolUse` - After successful execution
- `PostToolUseFailure` - After failed execution
- `PostToolBatch` - After batch of tools

**Async events:**
- `FileChanged` - File system watch
- `CwdChanged` - Working directory change
- `ConfigChange` - Settings update
- `Notification` - External notification
- `WorktreeCreate` / `WorktreeRemove` - Worktree lifecycle
- `Elicitation` - MCP elicitation request

### 2.3 Hook Configuration Structure

**Three-level nesting:**
```json
{
  "hooks": {
    "PreToolUse": [              // 1. Hook event
      {
        "matcher": "Bash",       // 2. Matcher (filter)
        "hooks": [               // 3. Hook handlers
          {
            "type": "command",
            "if": "Bash(rm *)",  // Fine-grained filter
            "command": "./validate.sh"
          }
        ]
      }
    ]
  }
}
```

**Matcher patterns:**
- `*` or empty - Match all
- `Bash|Edit|Write` - Exact match or list
- `^Notebook` - Regex pattern
- `mcp__.*` - Regex for MCP tools

### 2.4 Hook Decision Flow

**PreToolUse decisions:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Database writes not allowed"
  }
}
```

**PostToolUse decisions:**
```json
{
  "decision": "block",
  "reason": "Tests failed, fix before continuing",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Test output: 3 failures in auth.test.ts"
  }
}
```

### 2.5 Common Hook Patterns

**Auto-format on file write:**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "prettier",
          "args": ["--write", "${tool_input.file_path}"]
        }]
      }
    ]
  }
}
```

**Block destructive commands:**
```bash
#!/bin/bash
COMMAND=$(jq -r '.tool_input.command')
if echo "$COMMAND" | grep -q 'rm -rf'; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Destructive command blocked"
    }
  }'
  exit 0
fi
exit 0
```

**Load git context at session start:**
```bash
#!/bin/bash
BRANCH=$(git branch --show-current)
CHANGES=$(git status --short | wc -l)
jq -n --arg branch "$BRANCH" --arg changes "$CHANGES" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: "Branch: \($branch)\nUncommitted: \($changes)"
  }
}'
```

---

## 3. Automation & Workflows

### 3.1 Goal-Based Automation (`/goal`)

**Concept:** Set a completion condition and Claude works autonomously until met.

**How it works:**
1. User sets goal: `/goal all tests pass and lint is clean`
2. Goal starts a turn immediately with the condition as directive
3. After each turn, evaluator checks if condition holds
4. If not met, Claude starts another turn automatically
5. If met, goal clears and records achievement

**Evaluator model:** Uses configured small fast model (default: Haiku)

**Example goals:**
```bash
/goal all tests in test/auth pass and the lint step is clean
/goal CHANGELOG.md has an entry for every PR merged this week
/goal all files under 800 lines or stop after 20 turns
```

**Status check:**
```bash
/goal  # Shows: condition, duration, turns, tokens, last reason
```

**Clear early:**
```bash
/goal clear
```

### 3.2 Comparison: Autonomous Approaches

| Approach | Trigger | Stops When | Use Case |
|----------|---------|------------|----------|
| `/goal` | After each turn | Condition met | Verifiable end state |
| `/loop` | Time interval | Manual or Claude decides | Periodic monitoring |
| Stop hook | After each turn | Script/prompt decides | Custom evaluation |
| Auto mode | N/A (per-tool) | Claude decides | Remove tool prompts |

**Key insight:** `/goal` adds separate evaluator for objective completion check.

### 3.3 Graph of Algorithms Pattern

**Business as decomposable workflows:**
- Every process breaks into discrete algorithmic steps
- Steps chain together (output → input)
- Recursive decomposition (steps contain sub-steps)
- AI optimizes by analyzing the graph

**Application to Lyra:**
```
User Goal
  ↓
Goal Decomposer (Kahn's algorithm)
  ↓
Dependency Graph
  ↓
Fleet Orchestrator (parallel execution)
  ↓
Consensus Builder (voting)
  ↓
Verification
  ↓
Completion
```

**Dynamic workflow generation:**
- Parse goal into tasks
- Identify dependencies
- Generate execution DAG
- Optimize for parallelism
- Execute with monitoring

---

## 4. Commands System

### 4.1 Command Architecture

**Command sources:**
1. Built-in commands (Claude Code core)
2. Skills (user-authored workflows)
3. Plugins (installable extensions)
4. MCP prompts (`/mcp__server__prompt`)

**Command discovery:**
- Type `/` to see all commands
- Type `/` + letters to filter
- Commands show in unified menu

### 4.2 Command Registry Pattern

**Current Lyra implementation (87 lines):**
```python
@dataclass
class Command:
    name: str
    description: str
    handler: Callable
    aliases: list[str] = None
    category: str = "general"
    source: str = "lyra"

class CommandRegistry:
    def __init__(self):
        self.commands: dict[str, Command] = {}
        self.aliases: dict[str, str] = {}
    
    def register(self, command: Command):
        self.commands[command.name] = command
        for alias in command.aliases:
            self.aliases[alias] = command.name
    
    def get(self, name: str) -> Command | None:
        if name in self.aliases:
            name = self.aliases[name]
        return self.commands.get(name)
```

**Enhancement needed:**
- Parameter validation
- Help text generation
- Command composition/chaining
- Async execution support
- Permission integration

### 4.3 Interactive Mode Features

**Keyboard shortcuts:**
- `Ctrl+R` - Reverse search command history
- `Ctrl+O` - Toggle transcript viewer
- `Ctrl+T` - Toggle task list
- `Ctrl+B` - Background running tasks
- `Shift+Tab` - Cycle permission modes
- `Alt+P` - Switch model
- `Alt+T` - Toggle extended thinking

**Shell mode (`!` prefix):**
```bash
! npm test
! git status
! ls -la
```
- Adds command + output to context
- Real-time progress
- History-based autocomplete
- Supports backgrounding with Ctrl+B

**Side questions (`/btw`):**
```bash
/btw what was the name of that config file again?
```
- Quick question without adding to history
- Full conversation visibility
- No tool access
- Ephemeral overlay
- Can fork to new session with `f`

---

## 5. Credentials & Security

### 5.1 Credential Management

**API Key precedence:**
1. `ANTHROPIC_API_KEY` - Direct API key
2. `ANTHROPIC_AUTH_TOKEN` - Custom auth header
3. `CLAUDE_CODE_OAUTH_TOKEN` - OAuth access token
4. `/login` - Interactive Claude.ai login
5. Provider-specific keys (AWS, Vertex, etc.)

**Environment variable patterns:**
```bash
# Set in shell (temporary)
export ANTHROPIC_API_KEY="sk-ant-..."
claude

# Set in settings.json (persistent)
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "API_TIMEOUT_MS": "600000"
  }
}
```

### 5.2 OAuth 2.0 Flow

**Automatic discovery:**
1. Server responds with 401/403
2. Claude Code checks `WWW-Authenticate` header
3. Discovers authorization server metadata
4. Registers dynamic client (or uses pre-configured)
5. Opens browser for user authorization
6. Stores tokens in system keychain
7. Auto-refreshes on expiry

**Pre-configured OAuth:**
```bash
claude mcp add --transport http \
  --client-id your-client-id \
  --client-secret \
  --callback-port 8080 \
  my-server https://mcp.example.com/mcp
```

**Scope restriction:**
```json
{
  "oauth": {
    "scopes": "channels:read chat:write search:read"
  }
}
```

### 5.3 Security Model

**Multi-layer security:**

**1. TLS/mTLS:**
```bash
CLAUDE_CODE_CERT_STORE="bundled,system"
CLAUDE_CODE_CLIENT_CERT="/path/to/cert.pem"
CLAUDE_CODE_CLIENT_KEY="/path/to/key.pem"
CLAUDE_CODE_CLIENT_KEY_PASSPHRASE="secret"
```

**2. Custom headers:**
```bash
ANTHROPIC_CUSTOM_HEADERS="X-API-Key: abc123
X-Tenant-ID: tenant-1"
```

**3. Dynamic headers (headersHelper):**
```json
{
  "headersHelper": "/opt/bin/get-auth-headers.sh"
}
```

**4. Managed MCP configuration:**
- `allowedMcpServers` - Whitelist
- `deniedMcpServers` - Blacklist
- `managed-mcp.json` - Enterprise deployment

**5. Hook security:**
- Timeout enforcement (default: 600s)
- Exit code behavior (0=success, 2=block, other=warn)
- Workspace trust required
- `disableAllHooks` kill switch

---

## 6. Lyra Integration Architecture

### 6.1 Current State Analysis

**Existing components:**
- **MCP Manager** (92 lines) - Basic server registration
- **Command Registry** (87 lines) - Simple command storage
- **Hook Registry** (164 lines) - Foundation with priority sorting
- **93 packages** - Mature ecosystem
- **55,437 Python files** - Large codebase

**Gaps identified:**
1. No MCP client implementation (stdio, HTTP, SSE)
2. No OAuth 2.0 authentication
3. Limited hook types (no HTTP, prompt, agent hooks)
4. No goal-based automation engine
5. No tool search/deferred loading
6. No dynamic workflow generation
7. No credential management system

### 6.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Lyra Integration Layer                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     MCP      │  │    Hooks     │  │  Automation  │      │
│  │   Gateway    │  │   Engine     │  │   Engine     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────┴──────────────────┴──────────────────┴───────┐    │
│  │           Unified Execution Coordinator             │    │
│  └──────┬──────────────────┬──────────────────┬───────┘    │
│         │                  │                  │              │
├─────────┼──────────────────┼──────────────────┼─────────────┤
│         │                  │                  │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐     │
│  │ MCP Servers  │  │ Hook Scripts │  │ Goal Tracker │     │
│  │ (stdio/HTTP) │  │ (5 types)    │  │ (evaluator)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Component Design

**1. MCP Gateway**
```python
class MCPGateway:
    """Unified MCP client supporting all transports"""
    
    def __init__(self):
        self.servers: dict[str, MCPConnection] = {}
        self.tool_cache: dict[str, list[ToolDefinition]] = {}
        self.auth_manager = OAuthManager()
    
    async def connect_server(
        self, 
        config: MCPServerConfig
    ) -> MCPConnection:
        """Connect to MCP server (stdio, HTTP, or SSE)"""
        
    async def discover_tools(
        self, 
        server_name: str
    ) -> list[ToolDefinition]:
        """Discover tools from server"""
        
    async def call_tool(
        self, 
        server: str, 
        tool: str, 
        args: dict
    ) -> Any:
        """Execute tool on MCP server"""
```

**2. Hooks Engine**
```python
class HooksEngine:
    """Enhanced hook system with all 5 types"""
    
    def __init__(self):
        self.registry = HookRegistry()
        self.executor = HookExecutor()
    
    async def execute_hooks(
        self, 
        event: HookEvent,
        context: HookContext
    ) -> list[HookResult]:
        """Execute all matching hooks for event"""
        
    def register_hook(
        self, 
        hook: HookDefinition
    ) -> None:
        """Register hook with validation"""
```

**3. Automation Engine**
```python
class AutomationEngine:
    """Goal-based automation with evaluator"""
    
    def __init__(self):
        self.active_goal: Goal | None = None
        self.evaluator = GoalEvaluator()
        self.turn_count = 0
        self.token_spend = 0
    
    async def set_goal(self, condition: str) -> None:
        """Set completion condition"""
        
    async def evaluate_goal(
        self, 
        conversation: list[Message]
    ) -> GoalEvaluation:
        """Check if goal condition met"""
        
    async def execute_turn(self) -> bool:
        """Execute one autonomous turn, return if complete"""

### 6.4 Integration with Existing Systems

**Autonomy System integration:**
```python
# State machine gains new states
class AutonomyState(Enum):
    GOAL_PLANNING = "goal_planning"
    GOAL_EXECUTING = "goal_executing"
    GOAL_EVALUATING = "goal_evaluating"

# Goal decomposer uses MCP tools
class GoalDecomposer:
    def __init__(self, mcp_gateway: MCPGateway):
        self.mcp = mcp_gateway
    
    async def decompose_with_tools(self, goal: str):
        # Use MCP servers for research, analysis
        pass
```

**Swarm integration:**
```python
# Fleet orchestrator uses hooks for coordination
class FleetOrchestrator:
    def __init__(self, hooks_engine: HooksEngine):
        self.hooks = hooks_engine
    
    async def execute_fleet(self, fleet: Fleet):
        # Fire PreFleetExecution hook
        await self.hooks.execute_hooks(
            HookEvent.PRE_FLEET_EXECUTION,
            context
        )
```

**Command system integration:**
```python
# Commands can trigger MCP prompts
class CommandRegistry:
    def __init__(self, mcp_gateway: MCPGateway):
        self.mcp = mcp_gateway
    
    async def discover_mcp_commands(self):
        # Auto-register MCP prompts as commands
        for server in self.mcp.servers:
            prompts = await server.list_prompts()
            for prompt in prompts:
                self.register(Command(
                    name=f"mcp__{server}__{prompt.name}",
                    handler=lambda: self.mcp.call_prompt(...)
                ))
```

---

## 7. Implementation Roadmap

### Phase 1: MCP Foundation (Weeks 1-4)

**Week 1-2: MCP Client Core**
- [ ] Implement stdio transport
- [ ] Implement HTTP transport (streamable)
- [ ] Connection management with reconnection
- [ ] Tool discovery and caching
- [ ] Unit tests (50+ tests)

**Week 3-4: MCP Authentication**
- [ ] OAuth 2.0 flow implementation
- [ ] Token storage in keychain
- [ ] Automatic token refresh
- [ ] Dynamic client registration
- [ ] Pre-configured credentials support
- [ ] Integration tests (30+ tests)

**Deliverables:**
- `lyra-mcp` package
- MCP client supporting stdio and HTTP
- OAuth authentication
- 80+ tests

### Phase 2: Hooks Enhancement (Weeks 5-8)

**Week 5-6: Hook Types**
- [ ] HTTP hook implementation
- [ ] Prompt hook (LLM-based)
- [ ] Agent hook (subagent spawn)
- [ ] MCP tool hook
- [ ] Hook executor with timeout
- [ ] Unit tests (40+ tests)

**Week 7-8: Hook Lifecycle**
- [ ] All 12+ lifecycle events
- [ ] Context injection
- [ ] Decision handling (allow/deny/block)
- [ ] Hook composition
- [ ] Integration tests (30+ tests)

**Deliverables:**
- Enhanced `HooksEngine` with 5 hook types
- All lifecycle events supported
- 70+ tests

### Phase 3: Automation Engine (Weeks 9-12)

**Week 9-10: Goal System**
- [ ] Goal parser and validator
- [ ] Goal evaluator (using small model)
- [ ] Turn orchestration
- [ ] Status tracking
- [ ] Unit tests (30+ tests)

**Week 11-12: Workflow Generation**
- [ ] Dynamic DAG generation
- [ ] Dependency resolution
- [ ] Parallel execution optimization
- [ ] Integration with existing autonomy
- [ ] End-to-end tests (20+ tests)

**Deliverables:**
- `AutomationEngine` with goal support
- Dynamic workflow generation
- 50+ tests

### Phase 4: Integration & Polish (Weeks 13-16)

**Week 13-14: System Integration**
- [ ] MCP gateway in autonomy system
- [ ] Hooks in fleet orchestrator
- [ ] Commands from MCP prompts
- [ ] Credential management
- [ ] Integration tests (40+ tests)

**Week 15-16: Documentation & Testing**
- [ ] User documentation
- [ ] API reference
- [ ] Migration guide
- [ ] Performance benchmarks
- [ ] Security audit

**Deliverables:**
- Fully integrated system
- Complete documentation
- 200+ total tests
- Performance report

### Testing Strategy

**Unit Tests (200+):**
- MCP client: connection, discovery, tool calls
- Hooks engine: registration, execution, decisions
- Automation engine: goal parsing, evaluation, turns
- OAuth: token flow, refresh, storage

**Integration Tests (120+):**
- MCP + Hooks: tool execution with pre/post hooks
- MCP + Commands: prompt discovery and execution
- Hooks + Autonomy: state machine integration
- Goal + Fleet: autonomous swarm execution

**Performance Tests:**
- MCP connection latency
- Hook execution overhead
- Goal evaluation speed
- Concurrent tool calls

**Security Tests:**
- OAuth flow validation
- Token storage security
- Hook sandbox enforcement
- MCP server trust

### Success Metrics

**Functionality:**
- [ ] 3 MCP transports working (stdio, HTTP, SSE)
- [ ] 5 hook types implemented
- [ ] 12+ lifecycle events supported
- [ ] Goal-based automation functional
- [ ] OAuth 2.0 authentication working

**Quality:**
- [ ] 80%+ test coverage
- [ ] 320+ total tests passing
- [ ] Zero critical security issues
- [ ] Performance within 10% of Claude Code

**Integration:**
- [ ] MCP tools usable in autonomy system
- [ ] Hooks firing in fleet orchestrator
- [ ] Commands auto-discovered from MCP
- [ ] Credentials managed securely

---

## 8. Key Insights & Recommendations

### 8.1 Architecture Insights

**1. MCP as Universal Integration Layer**
- Single protocol for all external tools
- Eliminates custom integrations
- Enables marketplace ecosystem
- Supports both local and remote tools

**2. Hooks as Workflow Automation**
- Declarative automation without code
- Composable across lifecycle events
- Enables team-wide standards
- Supports gradual adoption

**3. Goal-Based Autonomy**
- Separate evaluator prevents drift
- Verifiable completion conditions
- Bounded execution (turn/time limits)
- Transparent progress tracking

**4. Commands as Unified Interface**
- Single discovery mechanism (`/`)
- Multiple sources (built-in, skills, MCP)
- Consistent user experience
- Extensible without core changes

### 8.2 Implementation Recommendations

**Priority 1: MCP Client (Critical)**
- Enables external tool ecosystem
- Unblocks marketplace integration
- Required for competitive parity
- **Effort:** 4 weeks, 2 engineers

**Priority 2: Hooks Enhancement (High)**
- Enables workflow automation
- Supports team standards
- Improves reliability
- **Effort:** 4 weeks, 1 engineer

**Priority 3: Automation Engine (Medium)**
- Differentiates from competitors
- Enables autonomous workflows
- Requires MCP + Hooks first
- **Effort:** 4 weeks, 1 engineer

**Priority 4: Integration (Medium)**
- Ties everything together
- Maximizes value of components
- Requires all above complete
- **Effort:** 4 weeks, 2 engineers

### 8.3 Risk Mitigation

**Technical Risks:**
- **MCP protocol changes** - Follow spec closely, version compatibility
- **OAuth complexity** - Use battle-tested libraries (authlib)
- **Hook security** - Sandbox execution, timeout enforcement
- **Performance overhead** - Benchmark early, optimize hot paths

**Integration Risks:**
- **Breaking existing code** - Comprehensive test suite, gradual rollout
- **User confusion** - Clear documentation, migration guide
- **Ecosystem fragmentation** - Standard patterns, examples

**Operational Risks:**
- **Support burden** - Self-service docs, troubleshooting guides
- **Security incidents** - Security audit, penetration testing
- **Scalability** - Load testing, performance monitoring

---

## 9. References

### Official Documentation
- [MCP Specification](https://modelcontextprotocol.io)
- [Claude Code MCP Guide](https://code.claude.com/docs/en/mcp)
- [Hooks Guide](https://code.claude.com/docs/en/hooks)
- [Goal-Based Automation](https://code.claude.com/docs/en/goal)
- [Commands Reference](https://code.claude.com/docs/en/commands)
- [Environment Variables](https://code.claude.com/docs/en/env-vars)

### Research Sources
- [Graph of Algorithms](https://danielmiessler.com/blog/companies-graph-of-algorithms)
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)
- [Claude Code Interactive Mode](https://code.claude.com/docs/en/interactive-mode)

### Lyra Documentation
- [System Overview](../architecture/system-overview.md)
- [Tools System](../architecture/TOOLS-SYSTEM.md)
- [Autonomy System](../architecture/autonomy-system.md)
- [Agent Swarm](../architecture/agent-swarm.md)

---

## Appendix A: MCP Server Examples

### Example 1: GitHub MCP Server
```bash
claude mcp add --transport http github \
  https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer YOUR_GITHUB_PAT"
```

**Capabilities:**
- Review PRs
- Create issues
- List open PRs
- Search code

### Example 2: PostgreSQL MCP Server
```bash
claude mcp add --transport stdio db \
  -- npx -y @bytebase/dbhub \
  --dsn "postgresql://user:pass@host:5432/db"
```

**Capabilities:**
- Query database
- Show schema
- Analyze tables
- Generate reports

### Example 3: Sentry MCP Server
```bash
claude mcp add --transport http sentry \
  https://mcp.sentry.dev/mcp
```

**Capabilities:**
- List errors
- Show stack traces
- Filter by deployment
- Analyze trends

---

## Appendix B: Hook Examples

### Example 1: Auto-format Python
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "if": "*.py",
          "command": "black",
          "args": ["${tool_input.file_path}"]
        }]
      }
    ]
  }
}
```

### Example 2: Require Tests
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "prompt",
          "if": "Bash(git commit)",
          "prompt": "Do all tests pass? Run pytest first.",
          "model": "claude-haiku-4"
        }]
      }
    ]
  }
}
```

### Example 3: Load Project Context
```bash
#!/bin/bash
# .claude/hooks/session-start.sh

BRANCH=$(git branch --show-current)
ISSUE=$(git log -1 --pretty=%B | grep -oP '#\d+' | head -1)

jq -n \
  --arg branch "$BRANCH" \
  --arg issue "$ISSUE" \
  '{
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: "Branch: \($branch)\nIssue: \($issue)",
      sessionTitle: "\($branch)"
    }
  }'
```

---

**Document Status:** Complete  
**Next Steps:** Review with architecture team, prioritize implementation phases  
**Related Documents:** US-007 (Tools Inventory), TOOLS-SYSTEM.md, system-overview.md

---

*Research conducted by: Claude Opus 4.7*  
*Date: 2026-05-29*  
*Version: 1.0*


```




