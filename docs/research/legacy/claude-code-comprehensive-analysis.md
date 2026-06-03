# Claude Code Comprehensive Analysis

**Date**: 2026-05-26  
**Purpose**: Deep analysis of Claude Code architecture for Lyra CLI integration

## Executive Summary

Claude Code is a sophisticated AI-powered development environment built on a multi-layered architecture combining:

1. **Plugin System**: Extensible component architecture for skills, agents, hooks, MCP servers, LSP servers, and monitors
2. **MCP Integration**: Model Context Protocol for external tool/data integration via HTTP, SSE, or stdio transports
3. **Hooks System**: Lifecycle event handlers (PreToolUse, PostToolUse, SessionStart, Stop) for automation
4. **Agent Orchestration**: Subagents for delegation, agent teams for parallel coordination, background agents for long-running tasks
5. **Advanced Tooling**: 40+ built-in tools (Bash, Edit, Read, Write, LSP, WebFetch, WebSearch, etc.)
6. **Permission System**: Fine-grained access control with modes (default, acceptEdits, plan, auto, bypassPermissions)
7. **Session Management**: Checkpointing, rewind, context compaction, session resumption
8. **Goal-Driven Execution**: Autonomous loops with condition evaluation

**Key Innovation**: Separation of concerns between deterministic automation (hooks), LLM-driven decisions (agents/skills), and external integrations (MCP).

---

## 1. Plugin System Architecture

### 1.1 Core Concepts

A **plugin** is a self-contained directory containing:
- Skills (custom commands/workflows)
- Agents (specialized subagents)
- Hooks (lifecycle automation)
- MCP servers (external integrations)
- LSP servers (code intelligence)
- Monitors (background watchers)

### 1.2 Plugin Structure

```
plugin-root/
├── plugin.json              # Metadata and configuration
├── skills/                  # Custom commands
│   └── skill-name/
│       ├── SKILL.md        # Main skill definition
│       └── reference.md    # Optional reference docs
├── commands/               # Simple markdown commands
│   └── command.md
├── agents/                 # Subagent definitions
│   └── agent-name.md
├── hooks/                  # Lifecycle hooks
│   └── hook-script.sh
├── mcp-servers/           # MCP server configs
│   └── server-config.json
└── monitors/              # Background monitors
    └── monitor-config.json
```

### 1.3 Plugin Discovery

**Load Order**:
1. Managed settings (enterprise/MDM)
2. User plugins (`~/.claude/plugins/`)
3. Project plugins (`.claude/plugins/`)
4. Marketplace plugins

**Installation**:
```bash
# From marketplace
/plugin install plugin-name@marketplace

# Local development
/plugin install /path/to/plugin

# List installed
/plugin list
```

### 1.4 Skills System

**Skills** are custom commands that extend Claude's capabilities. They follow the Agent Skills open standard.

**Skill Structure**:
```markdown
---
name: deploy
description: Deploy application to production
triggers:
  - deploy
  - ship to prod
allowed-tools:
  - Bash(npm run build)
  - Bash(git push *)
model: sonnet
---

# Deploy Application

Steps:
1. Run tests
2. Build production bundle
3. Deploy to server
4. Verify deployment
```

**Frontmatter Fields**:
- `name`: Skill identifier
- `description`: What the skill does
- `triggers`: Keywords that auto-invoke
- `allowed-tools`: Tool whitelist
- `disallowed-tools`: Tool blacklist
- `model`: Model to use (opus/sonnet/haiku)
- `isolation`: Run in subagent (none/worktree/container)
- `shell`: Shell for commands (bash/powershell)

**Invocation**:
- Manual: `/skill-name`
- Auto: Claude detects from triggers
- Programmatic: `Skill` tool

### 1.5 Subagents System

**Subagents** are specialized AI assistants for specific tasks, running in isolated contexts.

**Agent Definition**:
```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
model: opus
tools:
  - Read
  - Grep
  - LSP
disallowedTools:
  - Bash
  - Write
  - Edit
isolation: none
---

# Security Review Agent

Focus areas:
- SQL injection vulnerabilities
- XSS attack vectors
- Authentication/authorization flaws
- Secrets in code
- Input validation issues
```

**Isolation Modes**:
- `none`: Same directory as parent
- `worktree`: Separate git worktree
- `container`: Docker container (future)

**Usage Patterns**:
- Research: Explore without polluting main context
- Verification: Check work independently
- Parallel work: Multiple agents on different tasks

---

## 2. Complete Tools Catalog

### 2.1 Core Tools

| Tool | Permission | Purpose | Key Features |
|------|-----------|---------|--------------|
| `Read` | No | Read files | Supports images, PDFs, notebooks |
| `Write` | Yes | Create/overwrite files | Requires prior read for existing files |
| `Edit` | Yes | Targeted edits | Exact string replacement |
| `Bash` | Yes | Execute shell commands | Background tasks, timeout control |
| `PowerShell` | Yes | Windows shell | Native on Windows |
| `Grep` | No | Search file contents | Ripgrep-based, respects .gitignore |
| `Glob` | No | Find files by pattern | Recursive matching |
| `LSP` | No | Code intelligence | Definitions, references, diagnostics |
| `Agent` | No | Spawn subagent | Isolated context |
| `WebFetch` | Yes | Fetch web content | Lossy extraction |
| `WebSearch` | Yes | Search web | Anthropic backend |
| `Monitor` | Yes | Background watcher | React to events |

### 2.2 Session Management Tools

| Tool | Purpose |
|------|---------|
| `EnterPlanMode` | Switch to planning mode |
| `ExitPlanMode` | Exit planning, present plan |
| `EnterWorktree` | Create git worktree |
| `ExitWorktree` | Exit worktree |
| `CronCreate` | Schedule recurring tasks |
| `CronDelete` | Cancel scheduled task |
| `CronList` | List scheduled tasks |

### 2.3 Task Management Tools

| Tool | Purpose |
|------|---------|
| `TaskCreate` | Create new task |
| `TaskGet` | Get task details |
| `TaskList` | List all tasks |
| `TaskUpdate` | Update task status/details |
| `TaskStop` | Kill background task |

### 2.4 Team Coordination Tools

| Tool | Purpose |
|------|---------|
| `TeamCreate` | Create agent team |
| `TeamDelete` | Disband team |
| `SendMessage` | Message teammate |

### 2.5 Tool Permission Patterns

**Bash Patterns**:
```json
{
  "allow": [
    "Bash(npm run *)",
    "Bash(git commit *)",
    "Bash(* --version)"
  ],
  "deny": [
    "Bash(rm -rf *)",
    "Bash(git push *)"
  ]
}
```

**File Patterns** (gitignore syntax):
```json
{
  "allow": [
    "Read(/src/**)",
    "Edit(/docs/**)"
  ],
  "deny": [
    "Read(**/.env)",
    "Edit(//etc/**)"
  ]
}
```

---

## 3. MCP (Model Context Protocol) Integration

### 3.1 Architecture

MCP is an open protocol for AI-tool integrations. Three transport modes:

**1. Remote HTTP Server (Recommended)**:
```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

**2. Local Stdio Server**:
```bash
claude mcp add --transport stdio --env API_KEY=xxx airtable \
  -- npx -y airtable-mcp-server
```

**3. Remote SSE Server (Deprecated)**:
```bash
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

### 3.2 Configuration Scopes

| Scope | Loads In | Shared | File |
|-------|----------|--------|------|
| Local | Current project | No | `~/.claude.json` |
| Project | Current project | Yes (git) | `.mcp.json` |
| User | All projects | No | `~/.claude.json` |

### 3.3 MCP Server Capabilities

**Tools**: Functions Claude can call
**Resources**: Data Claude can reference (@mentions)
**Prompts**: Reusable prompt templates

### 3.4 Tool Search (Scaling)

Defers MCP tool loading until needed to save context:

```bash
# Enable (default)
ENABLE_TOOL_SEARCH=true claude

# Threshold mode (load if <10% of context)
ENABLE_TOOL_SEARCH=auto claude

# Custom threshold (5%)
ENABLE_TOOL_SEARCH=auto:5 claude
```

### 3.5 Authentication Patterns

**OAuth 2.0**:
```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# Then in session: /mcp
```

**Pre-configured OAuth**:
```bash
claude mcp add --transport http \
  --client-id xxx --client-secret --callback-port 8080 \
  server https://mcp.example.com/mcp
```

**Dynamic Headers**:
```json
{
  "mcpServers": {
    "api": {
      "type": "http",
      "url": "https://mcp.example.com",
      "headersHelper": "/opt/bin/get-auth-headers.sh"
    }
  }
}
```

---

## 4. Hooks System

### 4.1 Hook Types

**1. Command Hooks**: Run shell commands
```json
{
  "type": "command",
  "command": "node",
  "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/validate.js"],
  "timeout": 30
}
```

**2. HTTP Hooks**: POST to URL
```json
{
  "type": "http",
  "url": "http://localhost:8080/hooks/validate",
  "headers": {"Authorization": "Bearer $TOKEN"}
}
```

**3. MCP Tool Hooks**: Call MCP server tools
```json
{
  "type": "mcp_tool",
  "server": "my_server",
  "tool": "security_scan",
  "input": {"file_path": "${tool_input.file_path}"}
}
```

**4. Prompt Hooks**: LLM-based decisions
**5. Agent Hooks**: Spawn subagent for verification

### 4.2 Hook Events

| Event | When | Use Case |
|-------|------|----------|
| `SessionStart` | Session begins/resumes | Load context, setup environment |
| `PreToolUse` | Before tool execution | Validate, block, modify calls |
| `PostToolUse` | After tool execution | Auto-format, verify, notify |
| `UserPromptSubmit` | Before Claude processes | Add context, validate |
| `Stop` | Session ends | Cleanup, final verification |
| `TaskCreated` | Task created | Validate task |
| `TaskCompleted` | Task marked complete | Quality gate |
| `TeammateIdle` | Teammate going idle | Keep working or approve |

### 4.3 Exit Codes

- **Exit 0**: Success, parse stdout for JSON
- **Exit 2**: Blocking error, prevent action
- **Other**: Non-blocking error, continue

### 4.4 Hook Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(rm *)",
            "command": "/path/to/block-rm.sh",
            "timeout": 30
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "prettier",
            "args": ["--write", "${tool_input.file_path}"]
          }
        ]
      }
    ]
  }
}
```

---

## 5. Agent Orchestration Patterns

### 5.1 Subagents (Delegation)

**Architecture**: Parent spawns worker, worker returns result

**Use Cases**:
- Research without polluting main context
- Verification in isolated environment
- Focused tasks with specific tool access

**Example**:
```markdown
---
name: explore
description: Research and exploration
model: haiku
tools:
  - Read
  - Grep
  - Glob
  - WebSearch
disallowedTools:
  - Write
  - Edit
  - Bash
---
```

### 5.2 Agent Teams (Collaboration)

**Architecture**: Shared task list, direct messaging between teammates

**Use Cases**:
- Parallel exploration with discussion
- Multi-module features
- Competing hypotheses debugging

**Comparison**:
| | Subagents | Agent Teams |
|---|-----------|-------------|
| Communication | Report to parent only | Direct peer messaging |
| Coordination | Parent manages | Shared task list |
| Context | Own window | Own window |
| Best for | Focused delegation | Collaborative work |

### 5.3 Background Agents

**Architecture**: Detached sessions running independently

**Use Cases**:
- Long-running tasks (overnight builds)
- Monitoring and alerting
- Scheduled maintenance

**Management**:
```bash
# Detach current session
Ctrl+B (or /background)

# List background agents
/agents

# Attach to agent
/agents attach <id>
```

---

## 6. Automation Patterns

### 6.1 Goal-Driven Execution

**Pattern**: Set condition, Claude works until met

```bash
/goal all tests in test/auth pass and lint is clean
```

**Evaluation**: Small fast model checks condition after each turn

**Comparison**:
| Approach | Next turn starts | Stops when |
|----------|------------------|------------|
| `/goal` | Previous turn finishes | Condition met |
| `/loop` | Time interval | Manual stop or Claude decides |
| Stop hook | Previous turn finishes | Custom script/prompt |

### 6.2 Scheduled Tasks

**Cron-style scheduling**:
```bash
# Recurring
/loop 5m check deployment status

# One-shot
/schedule tomorrow 9am run daily standup
```

**Self-paced loops**: Claude chooses interval (1min-1hr)

### 6.3 Channels (Event-Driven)

**Pattern**: External events push into session

**Architecture**:
- MCP server with `claude/channel` capability
- Emits `notifications/claude/channel` events
- Optional reply tool for two-way communication

**Use Cases**:
- CI/CD webhooks
- Chat bridges (Telegram, Discord, iMessage)
- Monitoring alerts
- File watchers

**Example**:
```typescript
const mcp = new Server(
  { name: 'webhook', version: '0.0.1' },
  {
    capabilities: { experimental: { 'claude/channel': {} } },
    instructions: 'Events arrive as <channel source="webhook" ...>'
  }
)

await mcp.notification({
  method: 'notifications/claude/channel',
  params: {
    content: 'build failed on main',
    meta: { severity: 'high', run_id: '1234' }
  }
})
```

---

## 7. Permission System

### 7.1 Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Prompt on first use |
| `acceptEdits` | Auto-accept file edits in working dir |
| `plan` | Read-only, no edits |
| `auto` | Auto-approve with safety checks |
| `dontAsk` | Auto-deny unless pre-approved |
| `bypassPermissions` | Skip all prompts (dangerous) |

### 7.2 Rule Syntax

**Format**: `Tool(specifier)`

**Examples**:
```json
{
  "allow": [
    "Bash(npm run *)",
    "Read(/src/**)",
    "Edit(/docs/**)",
    "WebFetch(domain:github.com)",
    "Agent(Explore)"
  ],
  "deny": [
    "Bash(rm -rf *)",
    "Read(**/.env)",
    "Edit(//etc/**)"
  ]
}
```

### 7.3 Managed Settings

Enterprise controls (cannot be overridden):
- `allowManagedHooksOnly`
- `allowManagedMcpServersOnly`
- `allowManagedPermissionRulesOnly`
- `strictPluginOnlyCustomization`
- `channelsEnabled`
- `forceRemoteSettingsRefresh`

---

## 8. Session Management

### 8.1 Checkpointing

**Automatic tracking**:
- Every user prompt creates checkpoint
- Tracks all file edits
- Persists across sessions
- 30-day retention (configurable)

**Rewind menu** (`/rewind` or `Esc Esc`):
- Restore code and conversation
- Restore conversation only
- Restore code only
- Summarize from/to point

### 8.2 Context Management

**Compaction**: Summarize conversation to free space
**Forking**: Branch session to try alternatives
**Resume**: Continue previous session

### 8.3 Interactive Features

**Keyboard shortcuts**:
- `Ctrl+O`: Toggle transcript viewer
- `Ctrl+T`: Toggle task list
- `Ctrl+B`: Background task
- `Shift+Tab`: Cycle permission modes
- `Alt+P`: Switch model
- `Alt+T`: Toggle extended thinking

**Shell mode**: `!` prefix for direct commands
**Side questions**: `/btw` for ephemeral queries

---

## 9. Applicable Techniques for Lyra

### 9.1 Plugin Architecture

**Apply to Lyra**:
- Modular provider system (similar to MCP servers)
- Declarative configuration (JSON manifests)
- Component discovery and loading
- Marketplace distribution

**Implementation**:
```python
# lyra/plugins/base.py
class LyraPlugin:
    def __init__(self, manifest: dict):
        self.name = manifest['name']
        self.version = manifest['version']
        self.capabilities = manifest['capabilities']
    
    def load_skills(self) -> List[Skill]:
        """Load skill definitions"""
        pass
    
    def load_hooks(self) -> List[Hook]:
        """Load lifecycle hooks"""
        pass
    
    def load_providers(self) -> List[Provider]:
        """Load LLM providers"""
        pass
```

### 9.2 Tool Permission System

**Apply to Lyra**:
- Fine-grained permission rules
- Pattern matching (glob, regex)
- Permission modes (interactive, auto, bypass)
- Managed settings for enterprise

**Implementation**:
```python
# lyra/permissions/rules.py
class PermissionRule:
    def __init__(self, tool: str, pattern: str, action: str):
        self.tool = tool
        self.pattern = pattern  # glob or regex
        self.action = action  # allow/deny/ask
    
    def matches(self, tool_call: ToolCall) -> bool:
        """Check if rule matches tool call"""
        pass
```

### 9.3 Hooks System

**Apply to Lyra**:
- Lifecycle event handlers
- Multiple hook types (command, HTTP, prompt)
- Exit code semantics (0=success, 2=block)
- Async hooks for long operations

**Implementation**:
```python
# lyra/hooks/manager.py
class HookManager:
    def __init__(self):
        self.hooks: Dict[str, List[Hook]] = {}
    
    async def trigger(self, event: str, context: dict) -> HookResult:
        """Execute hooks for event"""
        for hook in self.hooks.get(event, []):
            result = await hook.execute(context)
            if result.should_block:
                return result
        return HookResult(success=True)

# Hook types
class CommandHook(Hook):
    async def execute(self, context: dict) -> HookResult:
        proc = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(
            json.dumps(context).encode()
        )
        return HookResult(
            success=proc.returncode == 0,
            should_block=proc.returncode == 2,
            output=stdout.decode()
        )
```

### 9.4 MCP-Style Provider Integration

**Apply to Lyra**:
- Standardized provider protocol
- Multiple transport modes
- Tool/resource/prompt capabilities
- Dynamic tool loading

**Implementation**:
```python
# lyra/providers/mcp_adapter.py
class MCPProvider:
    def __init__(self, config: dict):
        self.name = config['name']
        self.transport = self._create_transport(config)
        self.capabilities = {}
    
    async def connect(self):
        """Establish connection and discover capabilities"""
        await self.transport.connect()
        self.capabilities = await self.list_capabilities()
    
    async def call_tool(self, name: str, args: dict) -> dict:
        """Call provider tool"""
        return await self.transport.request({
            'method': 'tools/call',
            'params': {'name': name, 'arguments': args}
        })
    
    async def get_resource(self, uri: str) -> str:
        """Fetch provider resource"""
        return await self.transport.request({
            'method': 'resources/read',
            'params': {'uri': uri}
        })
```

### 9.5 Session Management

**Apply to Lyra**:
- Checkpointing and rewind
- Context compaction
- Session persistence
- Resume capability

**Implementation**:
```python
# lyra/session/checkpoint.py
class SessionCheckpoint:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.checkpoints: List[Checkpoint] = []
    
    def create_checkpoint(self, prompt: str, state: dict):
        """Create checkpoint before action"""
        checkpoint = Checkpoint(
            id=uuid.uuid4(),
            timestamp=datetime.now(),
            prompt=prompt,
            state=state,
            file_changes=self._capture_file_state()
        )
        self.checkpoints.append(checkpoint)
    
    def rewind_to(self, checkpoint_id: str):
        """Restore to checkpoint"""
        checkpoint = self._find_checkpoint(checkpoint_id)
        self._restore_files(checkpoint.file_changes)
        return checkpoint.state
```

### 9.6 Agent Orchestration

**Apply to Lyra**:
- Subagent delegation pattern
- Shared task coordination
- Background execution
- Inter-agent messaging

**Implementation**:
```python
# lyra/agents/orchestrator.py
class AgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.task_queue = TaskQueue()
    
    async def spawn_agent(self, config: AgentConfig) -> Agent:
        """Spawn new agent with isolated context"""
        agent = Agent(
            name=config.name,
            model=config.model,
            tools=config.allowed_tools,
            context=IsolatedContext()
        )
        self.agents[agent.id] = agent
        await agent.start()
        return agent
    
    async def delegate_task(self, agent_id: str, task: Task):
        """Delegate task to specific agent"""
        agent = self.agents[agent_id]
        result = await agent.execute(task)
        return result
    
    async def broadcast_message(self, message: str):
        """Send message to all agents"""
        for agent in self.agents.values():
            await agent.receive_message(message)
```

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Core extensibility infrastructure

**Tasks**:
1. Plugin system architecture
   - Plugin manifest schema
   - Component discovery and loading
   - Plugin lifecycle management
2. Permission system
   - Rule engine with pattern matching
   - Permission modes (interactive, auto)
   - Tool-specific rule syntax
3. Basic hooks
   - Hook manager
   - Command hooks
   - PreToolUse/PostToolUse events

**Deliverables**:
- Plugin loader with manifest validation
- Permission rule engine
- Hook execution framework

### Phase 2: Provider Integration (Weeks 3-4)
**Goal**: MCP-style provider system

**Tasks**:
1. Provider protocol
   - Standardized provider interface
   - Transport abstraction (HTTP, stdio)
   - Capability discovery
2. Tool integration
   - Dynamic tool loading
   - Tool permission checking
   - Tool execution pipeline
3. Resource system
   - Resource URI scheme
   - Resource fetching
   - Resource caching

**Deliverables**:
- MCP-compatible provider adapter
- Provider registry
- Tool execution engine

### Phase 3: Session Management (Weeks 5-6)
**Goal**: Persistent sessions with checkpointing

**Tasks**:
1. Checkpointing system
   - File state capture
   - Conversation snapshots
   - Rewind/restore functionality
2. Context management
   - Context compaction
   - Session persistence
   - Resume capability
3. Interactive features
   - Command history
   - Task list UI
   - Progress tracking

**Deliverables**:
- Checkpoint manager
- Session persistence layer
- Interactive CLI enhancements

### Phase 4: Agent Orchestration (Weeks 7-8)
**Goal**: Multi-agent coordination

**Tasks**:
1. Subagent system
   - Agent spawning
   - Isolated contexts
   - Result aggregation
2. Task coordination
   - Shared task queue
   - Task dependencies
   - Status tracking
3. Inter-agent communication
   - Message passing
   - Event broadcasting
   - Coordination protocols

**Deliverables**:
- Agent orchestrator
- Task coordination system
- Message bus

### Phase 5: Automation & Advanced Features (Weeks 9-10)
**Goal**: Goal-driven execution and event handling

**Tasks**:
1. Goal-driven execution
   - Condition evaluation
   - Autonomous loops
   - Progress monitoring
2. Event system
   - Channel protocol
   - Webhook receivers
   - Event routing
3. Advanced hooks
   - HTTP hooks
   - Prompt-based hooks
   - Async hooks

**Deliverables**:
- Goal execution engine
- Channel/event system
- Complete hook types

---

## 11. Key Takeaways

### 11.1 Architecture Principles

1. **Separation of Concerns**:
   - Deterministic automation → Hooks
   - LLM decisions → Agents/Skills
   - External integrations → MCP

2. **Modularity**:
   - Plugin-based extensions
   - Component discovery
   - Declarative configuration

3. **Flexibility**:
   - Multiple permission modes
   - Configurable isolation
   - Extensible tool system

### 11.2 Critical Success Factors

1. **Permission System**:
   - Fine-grained control essential for safety
   - Pattern matching enables flexible rules
   - Multiple modes support different workflows

2. **Hook System**:
   - Lifecycle events enable automation
   - Exit code semantics provide clear control flow
   - Multiple hook types support diverse use cases

3. **MCP Integration**:
   - Open protocol enables ecosystem
   - Multiple transports support different deployment models
   - Tool search scales to large tool sets

4. **Agent Orchestration**:
   - Subagents preserve context
   - Teams enable collaboration
   - Background agents support long-running tasks

### 11.3 Recommended Priorities for Lyra

**High Priority** (Must Have):
1. Plugin system with manifest-based loading
2. Permission system with pattern matching
3. Basic hooks (PreToolUse, PostToolUse)
4. MCP-style provider integration
5. Session checkpointing

**Medium Priority** (Should Have):
6. Subagent delegation
7. Goal-driven execution
8. Advanced hook types (HTTP, prompt)
9. Task coordination
10. Context compaction

**Low Priority** (Nice to Have):
11. Agent teams
12. Channel/event system
13. Background agents
14. Scheduled tasks
15. Interactive UI enhancements

---

## 12. References

- **Claude Code Documentation**: https://code.claude.com/docs/en/
- **MCP Specification**: https://modelcontextprotocol.io
- **Agent Skills Standard**: https://agentskills.io

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-26  
**Author**: Lyra Research Team
