# OpenClaw TUI Architecture Analysis

**Generated:** 2026-05-27  
**Source:** oh-my-openagent repository (batch2/oh-my-openagent)  
**Focus:** Multi-channel integration, extensibility patterns, and bidirectional communication

---

## Executive Summary

OpenClaw (part of oh-my-openagent) implements a **bidirectional external integration system** that enables:
- **Outbound**: Session event notifications to Discord/Telegram/HTTP webhooks/shell commands
- **Inbound**: Reply handling via daemon that polls chat apps and injects responses into tmux sessions

The architecture is named "claw" because it "reaches out from OpenCode and pulls replies back in."

**Key Innovation**: Unlike traditional notification systems, OpenClaw maintains a **session registry** that correlates message IDs with tmux panes, enabling true bidirectional communication.

---

## Architecture Overview

### 1. Bidirectional Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    OUTBOUND FLOW                             │
│  OpenCode Event → runtime-dispatch → dispatcher → Gateway   │
│                         ↓                                     │
│              session-registry (record correlation)           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    INBOUND FLOW                              │
│  Discord/Telegram → reply-listener daemon (poll every 3s)   │
│         ↓                                                     │
│  session-registry (lookup tmux pane)                         │
│         ↓                                                     │
│  reply-listener-injection (send-keys to tmux)               │
└─────────────────────────────────────────────────────────────┘
```

### 2. Core Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **index.ts** | Main entry point | `wakeOpenClaw()`, `initializeOpenClaw()` |
| **dispatcher.ts** | Gateway execution | HTTP POST, shell command with variable interpolation |
| **session-registry.ts** | Message correlation | JSONL file with file-locking, message ID ↔ session ↔ pane |
| **reply-listener.ts** | Daemon lifecycle | Start/stop, poll loop, state persistence |
| **reply-listener-discord.ts** | Discord integration | API polling, rate limiting, authorized users |
| **reply-listener-telegram.ts** | Telegram integration | API polling, reply-to-message detection |
| **reply-listener-injection.ts** | Tmux injection | Rate-limited send-keys to tmux panes |
| **runtime-dispatch.ts** | Event mapping | Maps OpenCode events to OpenClaw events |
| **config.ts** | Configuration | Gateway resolution, URL validation (HTTPS required) |

---

## Multi-Channel Gateway System

### Gateway Types

OpenClaw supports two gateway types:

#### 1. HTTP Webhook Gateway
```typescript
{
  type: "http",
  url: "https://api.example.com/webhook",
  method: "POST",
  headers: {
    "Authorization": "Bearer token",
    "Content-Type": "application/json"
  },
  timeout: 10000
}
```

#### 2. Shell Command Gateway
```typescript
{
  type: "command",
  command: "notify-send 'Session {{sessionId}}' '{{instruction}}'",
  timeout: 5000
}
```

**Key Features:**
- Variable interpolation with `{{variable}}` syntax
- Shell escaping for security
- Configurable timeouts
- Environment variable support

### Payload Variables

Available for interpolation in instructions and commands:

```typescript
{
  sessionId: string
  projectPath: string
  projectName: string
  tmuxSession: string
  tmuxTail: string        // Last 15 lines of tmux pane
  prompt: string
  contextSummary: string
  reasoning: string
  question: string
  event: string           // session-start, session-end, stop
  timestamp: string       // ISO 8601
  replyChannel: string
  replyTarget: string
  replyThread: string
}
```

### Configuration Schema

```typescript
interface OpenClawConfig {
  enabled: boolean
  
  // Outbound Configuration
  gateways: Record<string, OpenClawGateway>
  hooks: Record<string, OpenClawHook>
  
  // Inbound Configuration
  replyListener?: {
    discordBotToken?: string
    discordChannelId?: string
    authorizedDiscordUserIds: string[]
    
    telegramBotToken?: string
    telegramChatId?: string
    
    pollIntervalMs: number          // Default: 3000
    rateLimitPerMinute: number      // Default: 10
    maxMessageLength: number        // Default: 500
    includePrefix: boolean          // Default: true
  }
}
```

---

## Session Registry Architecture

### Purpose
Correlates external message IDs with internal tmux sessions to enable bidirectional communication.

### Implementation

**File Format:** JSONL (JSON Lines) with file-locking for concurrent access

```typescript
interface SessionMapping {
  sessionId: string
  tmuxSession: string
  tmuxPaneId: string
  projectPath: string
  platform: string        // "discord-bot", "telegram"
  messageId: string
  channelId?: string
  threadId?: string
  createdAt: string
}
```

### File Locking Strategy

```typescript
// Atomic lock acquisition with stale lock detection
function acquireRegistryLock(): LockHandle | null {
  // 1. Try to create exclusive lock file
  // 2. If exists, check if process is alive
  // 3. If stale (>10s and process dead), remove and retry
  // 4. Timeout after 2s
}

// Lock handle includes PID and unique token
interface LockHandle {
  fd: number
  token: string  // UUID for verification
}
```

**Key Features:**
- **Atomic operations**: Uses `O_CREAT | O_EXCL` for lock creation
- **Stale lock detection**: Checks if lock owner process is alive
- **Token verification**: Prevents accidental lock removal
- **Secure permissions**: 0o600 (owner read/write only)

### Registry Operations

```typescript
// Register new message correlation
registerMessage(mapping: SessionMapping): boolean

// Lookup by message ID
lookupByMessageId(platform: string, messageId: string): SessionMapping | null

// Cleanup operations
removeSession(sessionId: string): void
removeMessagesByPane(paneId: string): void
pruneStale(): void  // Remove entries older than 24h
```

---

## Reply Listener Daemon

### Architecture

The reply listener runs as a **detached Bun process** that polls chat platforms and injects replies into tmux sessions.

### Lifecycle

```typescript
// 1. Initialization
initializeOpenClaw(config)
  → Check if daemon already running
  → Write config to state directory
  → Spawn daemon.ts as detached process
  → Write PID file
  → Wait for daemon to become ready (startup token verification)

// 2. Poll Loop
pollLoop()
  → Read daemon config
  → Create rate limiter
  → Poll Discord (if configured)
  → Poll Telegram (if configured)
  → Prune stale registry entries (every 1h)
  → Sleep for pollIntervalMs (default: 3s)

// 3. Shutdown
stopReplyListener()
  → Send SIGTERM to daemon process
  → Remove PID file
  → Mark state as stopped
```

### State Management

```typescript
interface ReplyListenerDaemonState {
  isRunning: boolean
  pid: number | null
  startupToken: string
  configSignature: string  // JSON hash for config change detection
  
  // Discord state
  discordLastMessageId?: string
  
  // Telegram state
  telegramLastUpdateId?: number
  
  // Statistics
  messagesInjected: number
  errors: number
  lastError?: string
  lastPollAt?: string
}
```

**State Persistence:**
- Written to `.opencode/openclaw/reply-listener-state.json`
- Updated after each poll cycle
- Used for daemon health monitoring

### Discord Integration

```typescript
async function pollDiscordReplies(
  config: OpenClawConfig,
  state: ReplyListenerDaemonState,
  rateLimiter: ReplyListenerRateLimiter
): Promise<void>
```

**Features:**
- Polls `/channels/{channelId}/messages?after={lastMessageId}&limit=10`
- Respects Discord rate limits (checks `x-ratelimit-remaining` header)
- Filters by authorized user IDs
- Detects reply-to-message references
- Acknowledges successful injection with ✅ reaction

**Rate Limit Handling:**
```typescript
if (remaining < 2) {
  const resetTime = parseFloat(reset) * 1000
  discordBackoffUntil = resetTime
  // Skip polling until reset time
}
```

### Telegram Integration

```typescript
async function pollTelegramReplies(
  config: OpenClawConfig,
  state: ReplyListenerDaemonState,
  rateLimiter: ReplyListenerRateLimiter
): Promise<void>
```

**Features:**
- Polls `/bot{token}/getUpdates?offset={lastUpdateId}&timeout=0`
- Detects `reply_to_message` field
- Filters by chat ID
- Sends confirmation message after successful injection

### Reply Injection

```typescript
async function injectReplyIntoPane(
  paneId: string,
  text: string,
  platform: string,
  config: OpenClawConfig
): Promise<boolean>
```

**Implementation:**
```typescript
// 1. Validate tmux pane exists
const paneExists = await checkTmuxPane(paneId)

// 2. Apply rate limiting
if (!rateLimiter.canProceed()) {
  return false
}

// 3. Truncate message if needed
const truncated = text.slice(0, config.maxMessageLength)

// 4. Add prefix if enabled
const prefixed = config.includePrefix 
  ? `[${platform}] ${truncated}` 
  : truncated

// 5. Inject via tmux send-keys
await tmux.sendKeys(paneId, prefixed)
```

**Rate Limiting:**
- Token bucket algorithm
- Default: 10 messages per minute per pane
- Prevents spam and tmux overload

---

## Skills Registry System

### Architecture

OpenClaw integrates with oh-my-openagent's **hierarchical skills system** that discovers and merges skills from multiple sources.

### Skill Discovery Hierarchy

```typescript
// Priority order (later sources override earlier ones)
1. Built-in skills (plugin-provided)
2. Config source skills (from settings.json)
3. User Claude skills (~/.claude/skills/)
4. Global OpenCode skills (~/.opencode/skills/)
5. Project Claude skills (.claude/skills/)
6. OpenCode project skills (.opencode/skills/)
7. Project agents skills (agents/*/skills/)
8. Global agents skills (~/.opencode/agents/*/skills/)
```

### Skill Context Creation

```typescript
interface SkillContext {
  mergedSkills: LoadedSkill[]
  availableSkills: AvailableSkill[]
  browserProvider: BrowserAutomationProvider
  disabledSkills: Set<string>
}

async function createSkillContext(args: {
  directory: string
  pluginConfig: OhMyOpenCodeConfig
}): Promise<SkillContext>
```

**Process:**
1. Discover skills from all sources in parallel
2. Filter provider-gated skills (e.g., playwright vs agent-browser)
3. Merge skills with priority resolution
4. Filter out disabled skills
5. Filter out MCP-provided skills (avoid duplicates)

### Skill Definition

```typescript
interface LoadedSkill {
  name: string
  scope: SkillScope  // "user" | "project" | "opencode" | "opencode-project" | "plugin"
  definition: {
    description: string
    triggers?: string[]
    tags?: string[]
    content: string
  }
  mcpConfig?: Record<string, McpServerConfig>
}
```

### Skill Path Resolution

```typescript
// Resolves @-prefixed paths in skill content
function resolveSkillPathReferences(
  content: string, 
  basePath: string
): string

// Example:
// "@agents/planner/prompt.md" → "/absolute/path/to/agents/planner/prompt.md"
```

---

## Plugin System Architecture

### Plugin Interface

OpenClaw implements a **hook-based plugin system** that intercepts various lifecycle events:

```typescript
interface PluginInterface {
  tool: ToolsRecord
  
  // Chat lifecycle hooks
  "chat.params": (input: unknown, output: unknown) => Promise<void>
  "chat.headers": (input: unknown, output: unknown) => void
  "chat.message": (input: unknown, output: unknown) => Promise<void>
  
  // Message transformation hooks
  "experimental.chat.messages.transform": (input: unknown, output: unknown) => Promise<void>
  "experimental.chat.system.transform": (input: unknown, output: unknown) => void
  
  // Command hooks
  "command.execute.before": (input: unknown, output: unknown) => Promise<void>
  
  // Tool hooks
  "tool.definition": (input: unknown, output: unknown) => void
  "tool.execute.before": (input: unknown, output: unknown) => Promise<void>
  "tool.execute.after": (input: unknown, output: unknown) => Promise<void>
  
  // Configuration and events
  config: ConfigHandler
  event: EventHandler
}
```

### Event System

```typescript
interface EventHandler {
  "session.created": (context: SessionContext) => Promise<void>
  "session.deleted": (context: SessionContext) => Promise<void>
  "session.idle": (context: SessionContext) => Promise<void>
}

// Runtime dispatch maps events to OpenClaw events
function mapRawEventToOpenClawEvents(rawEvent: string): string[] {
  const aliases = {
    "session.created": "session-start",
    "session.deleted": "session-end",
    "session.idle": "stop"
  }
  return [rawEvent, aliases[rawEvent]].filter(Boolean)
}
```

### Hook Execution Flow

```
User Input → chat.message hook
    ↓
Message Transform hooks
    ↓
Tool Definition hook (if tool call)
    ↓
Tool Execute Before hook
    ↓
Tool Execution
    ↓
Tool Execute After hook
    ↓
Response to User
```

---

## Security Architecture

### URL Validation

```typescript
function validateGatewayUrl(url: string): boolean {
  // HTTPS required except for localhost
  if (url.startsWith('http://')) {
    const localhostPatterns = [
      'http://localhost',
      'http://127.0.0.1',
      'http://[::1]'
    ]
    return localhostPatterns.some(pattern => url.startsWith(pattern))
  }
  return url.startsWith('https://')
}
```

### Authorization

**Discord:**
- Authorized user ID whitelist
- Only replies from authorized users are injected
- Bot token stored securely in config

**Telegram:**
- Chat ID filtering
- Reply-to-message validation
- Bot token stored securely in config

### Shell Command Security

```typescript
function shellEscapeArg(value: string): string {
  return "'" + value.replace(/'/g, "'\\''") + "'"
}

// Variables are escaped before interpolation
const interpolated = command.replace(/\{\{(\w+)\}\}/g, (match, key) => {
  const value = variables[key]
  if (value === undefined) return match
  return shellEscapeArg(value)
})
```

### File Permissions

```typescript
const SECURE_FILE_MODE = 0o600  // Owner read/write only

// Applied to:
// - Session registry file
// - Lock files
// - State files
```

### Rate Limiting

```typescript
class ReplyListenerRateLimiter {
  private tokens: number
  private lastRefill: number
  private readonly maxTokens: number
  private readonly refillRate: number  // tokens per minute
  
  canProceed(): boolean {
    this.refillTokens()
    if (this.tokens >= 1) {
      this.tokens -= 1
      return true
    }
    return false
  }
}
```

---

## Extensibility Patterns

### 1. Gateway Extensibility

**Adding New Gateway Types:**

```typescript
// Current: HTTP and Command
// Extensible via type field

interface OpenClawGateway {
  type: "http" | "command" | "custom"  // Easy to extend
  // Type-specific fields
  url?: string
  command?: string
  // Shared fields
  timeout?: number
}
```

### 2. Platform Extensibility

**Adding New Chat Platforms:**

```typescript
// Pattern: Create new reply-listener-{platform}.ts

async function pollNewPlatformReplies(
  config: OpenClawConfig,
  state: ReplyListenerDaemonState,
  rateLimiter: ReplyListenerRateLimiter
): Promise<void> {
  // 1. Poll platform API
  // 2. Detect replies to registered messages
  // 3. Lookup session in registry
  // 4. Inject reply into tmux pane
  // 5. Update state
}

// Add to poll loop in reply-listener.ts
await pollDiscordReplies(config, state, rateLimiter)
await pollTelegramReplies(config, state, rateLimiter)
await pollNewPlatformReplies(config, state, rateLimiter)  // New
```

### 3. Event Extensibility

**Adding New Events:**

```typescript
// 1. Define event in runtime-dispatch.ts
const aliases: Record<string, string> = {
  "session.created": "session-start",
  "session.deleted": "session-end",
  "session.idle": "stop",
  "session.error": "error",  // New event
}

// 2. Dispatch from appropriate location
await dispatchOpenClawEvent({
  config,
  rawEvent: "session.error",
  context: { sessionId, error }
})
```

### 4. Variable Extensibility

**Adding New Payload Variables:**

```typescript
// In index.ts wakeOpenClaw()
const variables: Record<string, string | undefined> = {
  // Existing variables
  sessionId: context.sessionId,
  projectPath: context.projectPath,
  // Add new variables
  customField: context.customField,
}

// Available in all gateways and instructions
```

---

## Key Implementation Details

### Dispatcher Implementation

```typescript
export async function wakeGateway(
  gatewayName: string,
  gatewayConfig: OpenClawGateway,
  payload: unknown
): Promise<WakeResult> {
  // 1. Validate URL (HTTPS required)
  if (!validateGatewayUrl(gatewayConfig.url)) {
    return { gateway: gatewayName, success: false, error: "Invalid URL" }
  }
  
  // 2. Set timeout
  const timeout = gatewayConfig.timeout ?? 10_000
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  // 3. Execute HTTP request
  const response = await fetch(gatewayConfig.url, {
    method: gatewayConfig.method || "POST",
    headers: { "Content-Type": "application/json", ...gatewayConfig.headers },
    body: JSON.stringify(payload),
    signal: controller.signal
  }).finally(() => clearTimeout(timeoutId))
  
  // 4. Parse response for metadata
  const metadata = parseWakeMetadata(await response.text())
  
  return { 
    gateway: gatewayName, 
    success: response.ok, 
    statusCode: response.status,
    ...metadata  // messageId, platform, channelId, threadId
  }
}
```

### Command Gateway Implementation

```typescript
export async function wakeCommandGateway(
  gatewayName: string,
  gatewayConfig: OpenClawGateway,
  variables: Record<string, string | undefined>
): Promise<WakeResult> {
  // 1. Interpolate and escape variables
  const interpolated = gatewayConfig.command.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    const value = variables[key]
    return value !== undefined ? shellEscapeArg(value) : match
  })
  
  // 2. Spawn shell process
  const proc = spawn(["sh", "-c", interpolated], {
    stdout: "pipe",
    stderr: "ignore",
    detached: process.platform !== "win32"
  })
  
  // 3. Wait with timeout
  const timeout = resolveCommandTimeoutMs(gatewayConfig.timeout)
  await Promise.race([proc.exited, timeoutPromise(timeout)])
  
  // 4. Parse stdout for metadata
  const metadata = parseWakeMetadata(await stdoutPromise)
  
  return { gateway: gatewayName, success: true, ...metadata }
}
```

### Metadata Extraction

```typescript
function parseWakeMetadata(raw: string): Pick<WakeResult, "messageId" | "platform" | "channelId" | "threadId"> {
  const trimmed = raw.trim()
  if (!trimmed) return {}
  
  try {
    // Try JSON parsing first
    const payload = JSON.parse(trimmed)
    return extractWakeMetadata(payload)
  } catch {
    // Fallback to regex parsing
    const messageId = trimmed.match(/message\s+id:\s*([^\s]+)/i)?.[1]
    const platform = trimmed.match(/sent\s+via\s+([a-z0-9_-]+)/i)?.[1]?.toLowerCase()
    return { messageId, platform }
  }
}
```

**Key Feature:** Flexible metadata extraction supports multiple response formats from different gateway implementations.

---

## Tmux Integration

### Tmux Utilities

```typescript
// Get current tmux session name
export function getCurrentTmuxSession(): string | null {
  const tmuxEnv = process.env.TMUX
  if (!tmuxEnv) return null
  
  const sessionName = tmuxEnv.split(',')[0]?.split('/').pop()
  return sessionName || null
}

// Capture pane content
export async function captureTmuxPane(
  paneId: string, 
  lines: number
): Promise<string | null> {
  const result = await spawn([
    "tmux", "capture-pane", 
    "-t", paneId, 
    "-p", "-S", `-${lines}`
  ])
  
  return result.exitCode === 0 ? result.stdout : null
}

// Send keys to pane
export async function sendToPane(
  paneId: string, 
  text: string
): Promise<boolean> {
  const result = await spawn([
    "tmux", "send-keys",
    "-t", paneId,
    "-l", text
  ])
  
  return result.exitCode === 0
}
```

---

## Recommendations for Lyra

### 1. Adopt Multi-Channel Gateway Pattern

**Implementation:**
- Create `packages/lyra-gateway/` package
- Support HTTP webhooks and shell commands
- Variable interpolation system
- Metadata extraction from responses

**Benefits:**
- Extensible notification system
- Support for Discord, Telegram, Slack, custom webhooks
- Bidirectional communication capability

### 2. Implement Session Registry

**Implementation:**
- JSONL file with file-locking
- Correlate external message IDs with sessions
- Enable reply injection from external platforms

**Benefits:**
- True bidirectional communication
- Multi-user collaboration support
- Remote control capabilities

### 3. Adopt Hierarchical Skills System

**Implementation:**
- Discover skills from multiple sources
- Priority-based merging
- Path resolution for skill references

**Benefits:**
- User-level and project-level skills
- Plugin-provided skills
- Easy skill sharing and distribution

### 4. Implement Reply Listener Daemon

**Implementation:**
- Detached process for polling
- State persistence
- Rate limiting
- Platform-specific adapters

**Benefits:**
- Real-time reply handling
- No blocking of main process
- Graceful restart on config changes

### 5. Security Best Practices

**Adopt:**
- HTTPS-only for webhooks (localhost exception)
- Shell command escaping
- File permission restrictions (0o600)
- Authorized user whitelists
- Rate limiting

---

## Code Examples for Lyra Integration

### Gateway Configuration

```typescript
// packages/lyra-cli/config/gateway.ts
interface GatewayConfig {
  enabled: boolean
  gateways: Record<string, Gateway>
  hooks: Record<string, Hook>
}

interface Gateway {
  type: "http" | "command"
  url?: string
  command?: string
  timeout?: number
  headers?: Record<string, string>
}

interface Hook {
  enabled: boolean
  gateway: string
  instruction: string
}
```

### Session Registry Implementation

```typescript
// packages/lyra-cli/registry/session-registry.ts
interface SessionMapping {
  sessionId: string
  tmuxPaneId: string
  platform: string
  messageId: string
  channelId?: string
  threadId?: string
  createdAt: string
}

export function registerMessage(mapping: SessionMapping): boolean
export function lookupByMessageId(platform: string, messageId: string): SessionMapping | null
export function removeSession(sessionId: string): void
export function pruneStale(): void
```

### Skills Discovery

```typescript
// packages/lyra-cli/skills/discovery.ts
export async function discoverSkills(directory: string): Promise<LoadedSkill[]> {
  const [userSkills, projectSkills, pluginSkills] = await Promise.all([
    discoverUserSkills(),
    discoverProjectSkills(directory),
    discoverPluginSkills()
  ])
  
  return mergeSkills(pluginSkills, userSkills, projectSkills)
}
```

---

## Conclusion

OpenClaw demonstrates a **production-ready bidirectional integration system** with:

1. **Multi-channel gateway architecture** supporting HTTP and shell commands
2. **Session registry** enabling message correlation and reply injection
3. **Hierarchical skills system** with priority-based merging
4. **Daemon-based reply listener** for real-time external communication
5. **Comprehensive security** with HTTPS enforcement, shell escaping, and rate limiting

**Key Takeaway:** The bidirectional flow (outbound notifications + inbound replies) is the most innovative aspect, enabling true multi-user collaboration and remote control capabilities.

**Recommended for Lyra:**
- Adopt the gateway pattern for extensible notifications
- Implement session registry for bidirectional communication
- Use hierarchical skills discovery
- Apply security best practices throughout

---

**Analysis Complete:** 2026-05-27  
**Source Files Analyzed:** 18 core files + configuration schemas  
**Total Lines of Code Reviewed:** ~3,500 lines
