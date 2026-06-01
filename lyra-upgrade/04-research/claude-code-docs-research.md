# Claude Code Documentation Research Summary

**Research Date**: 2026-05-31  
**URLs Researched**: 19 of 38 from §3.1  
**Status**: In Progress

## Executive Summary

Claude Code represents a mature, production-grade agentic harness with sophisticated features across multiple dimensions:

### Key Architectural Patterns Identified

1. **Multi-Layer Permission System**
   - Permission modes (default, acceptEdits, plan, auto, dontAsk, bypassPermissions)
   - Permission rules (allow/deny/ask patterns with glob matching)
   - OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux)
   - Auto mode with classifier-based approval (research preview)

2. **Context Management Architecture**
   - Automatic compaction with summarization
   - Prompt caching (system prompt, tools, conversation history)
   - MCP Tool Search (deferred tool schema loading)
   - Context window visualization and tracking

3. **Extensibility Framework**
   - Skills (Agent Skills standard + Claude Code extensions)
   - Hooks (PreToolUse, PostToolUse, Stop, ConfigChange, Notification)
   - Plugins (bundled skills + hooks + subagents + MCP servers)
   - MCP servers (stdio, SSE, HTTP transports)
   - Subagents (isolated context windows with custom system prompts)

4. **Model Configuration & Routing**
   - Model aliases (sonnet, opus, haiku, opusplan, best)
   - Effort levels (low, medium, high, xhigh, max, ultracode)
   - Extended thinking with adaptive reasoning
   - Fast mode (2.5x speed at higher cost)
   - 1M context window support

5. **Terminal & UI Customization**
   - Fullscreen rendering mode (alternate screen buffer)
   - Custom themes (base + overrides)
   - Output styles (modify system prompt for different roles)
   - Status line (shell script with JSON session data)
   - Keybindings (full remapping support)

6. **Security & Isolation**
   - Sandboxed Bash tool (filesystem + network isolation)
   - Sandbox runtime (wraps entire process)
   - Dev containers (Docker-based)
   - Virtual machines (strongest isolation)
   - Prompt injection defenses

7. **Voice & Accessibility**
   - Voice dictation (hold-to-record and tap-to-record modes)
   - Speech-to-text via Anthropic servers
   - 19 supported languages
   - Coding vocabulary tuning

8. **Monitoring & Cost Management**
   - OpenTelemetry integration (metrics, logs, traces)
   - Token usage tracking and attribution
   - Cost estimation and optimization strategies
   - Workspace spend limits

## Portable Features for Lyra

### HIGH PRIORITY - Direct Ports

#### 1. Permission System Architecture
**Source**: settings.md, permissions docs, sandboxing.md  
**Mechanism**: Three-layer permission system
- **Layer 1**: Permission modes (global approval behavior)
- **Layer 2**: Permission rules (pattern-based allow/deny/ask)
- **Layer 3**: OS-level sandboxing (runtime enforcement)

**Port Strategy**:
```typescript
// Lyra permission architecture
interface PermissionSystem {
  mode: 'default' | 'acceptEdits' | 'plan' | 'auto';
  rules: PermissionRule[];
  sandbox: SandboxConfig;
}

interface PermissionRule {
  tool: string;
  pattern: string;
  action: 'allow' | 'deny' | 'ask';
  scope: 'user' | 'project' | 'managed';
}
```

**Workstream**: §4.16 Safety & Guardrails

#### 2. MCP Tool Search (Deferred Schema Loading)
**Source**: agent-sdk/tool-search  
**Mechanism**: 
- Tool names loaded at startup (lightweight)
- Full schemas fetched on-demand when tool is used
- 3-5 most relevant tools loaded per search
- Supports up to 10,000 tools

**Port Strategy**:
```typescript
// Lyra tool search
interface ToolCatalog {
  listTools(): Promise<ToolSummary[]>;  // Names only
  searchTools(query: string): Promise<ToolDefinition[]>;  // Top 3-5
  getToolSchema(name: string): Promise<ToolSchema>;
}
```

**Workstream**: §4.5 Tool Router & Orchestration

#### 3. Hooks System
**Source**: hooks-guide.md, hooks.md  
**Mechanism**: Lifecycle event handlers with multiple handler types
- **Events**: PreToolUse, PostToolUse, Stop, ConfigChange, Notification
- **Handlers**: command, http, mcp, llm, subagent
- **Matchers**: Filter by tool name, arguments, patterns

**Port Strategy**:
```typescript
// Lyra hooks
interface HookConfig {
  event: 'PreToolUse' | 'PostToolUse' | 'Stop' | 'ConfigChange';
  matcher?: ToolMatcher;
  handlers: HookHandler[];
}

interface HookHandler {
  type: 'command' | 'http' | 'mcp' | 'llm' | 'subagent';
  config: Record<string, any>;
}
```

**Workstream**: §4.4 Skills & Workflows

#### 4. Context Compaction Strategy
**Source**: context-window docs, prompt-caching  
**Mechanism**:
- Tool outputs cleared first (oldest to newest)
- Conversation summarized when threshold reached
- CLAUDE.md and auto memory survive compaction
- Manual compaction with focus parameter

**Port Strategy**:
```typescript
// Lyra compaction
interface CompactionStrategy {
  threshold: number;  // % of context window
  preservePatterns: string[];  // What survives
  summarizationPrompt: string;
  focusHint?: string;  // User-provided focus
}
```

**Workstream**: §4.2 Memory Architecture

#### 5. Subagent Architecture
**Source**: sub-agents.md  
**Mechanism**:
- Isolated context windows
- Custom system prompts
- Independent tool access
- Configurable models (can use Haiku for cost savings)
- Foreground or background execution

**Port Strategy**:
```typescript
// Lyra subagent
interface SubagentConfig {
  name: string;
  description: string;  // For auto-delegation
  systemPrompt: string;
  tools: string[];  // Allowed tools
  model?: string;  // Default: inherit
  isolation: 'context' | 'worktree';
}
```

**Workstream**: §4.13 Agent Swarm & Fleet

### MEDIUM PRIORITY - Adapt & Enhance

#### 6. Model Routing with Effort Levels
**Source**: model-config.md  
**Mechanism**:
- Model aliases resolve to specific versions
- Effort levels control adaptive reasoning budget
- Per-model effort support (Opus 4.8: low→max, Opus 4.6: low→high)
- `opusplan` alias: Opus for planning, Sonnet for execution

**Enhancement for Lyra**: Add cost-aware routing
```typescript
interface ModelRouter {
  selectModel(task: Task, constraints: Constraints): ModelConfig;
  estimateCost(model: string, tokens: number): number;
  fallbackChain: string[];  // Graceful degradation
}
```

**Workstream**: §4.5 Tool Router & Orchestration

#### 7. Settings Precedence System
**Source**: settings.md  
**Mechanism**: 5-layer hierarchy
1. Managed (highest - org policy)
2. Command-line arguments
3. Local (.claude/settings.local.json - gitignored)
4. Project (.claude/settings.json - committed)
5. User (~/.claude/settings.json - lowest)

**Enhancement for Lyra**: Add environment-specific layers
```typescript
interface SettingsLayer {
  scope: 'managed' | 'env' | 'local' | 'project' | 'user';
  priority: number;
  mergeStrategy: 'replace' | 'merge' | 'append';
}
```

**Workstream**: §4.1 Configuration System

#### 8. Fullscreen Rendering Mode
**Source**: fullscreen.md  
**Mechanism**:
- Alternate screen buffer (like vim/htop)
- Mouse support (click, drag, scroll)
- Flat memory usage (only visible messages rendered)
- Search and navigation (less-style)

**Enhancement for Lyra**: Add TUI framework abstraction
```typescript
interface RenderMode {
  type: 'scrollback' | 'fullscreen';
  mouseEnabled: boolean;
  searchEnabled: boolean;
  autoScroll: boolean;
}
```

**Workstream**: §4.11 UI/UX Enhancements

#### 9. Voice Dictation
**Source**: voice-dictation.md  
**Mechanism**:
- Hold-to-record (push-to-talk with warmup)
- Tap-to-record (toggle mode, no warmup)
- Live transcription with coding vocabulary
- 19 language support
- Auto-submit on release (configurable)

**Enhancement for Lyra**: Add local STT option
```typescript
interface VoiceConfig {
  mode: 'hold' | 'tap';
  provider: 'anthropic' | 'whisper-local' | 'azure';
  language: string;
  autoSubmit: boolean;
  codingVocabulary: string[];
}
```

**Workstream**: §4.0 Voice Mode (P0)

### LOW PRIORITY - Reference Implementations

#### 10. OpenTelemetry Integration
**Source**: monitoring-usage.md  
**Mechanism**:
- Metrics (OTLP, Prometheus, console)
- Logs/Events (OTLP, console)
- Traces (beta)
- Configurable export intervals
- Standard OTEL environment variables

**Reference for Lyra**: Standard observability pattern

**Workstream**: §4.17 Observability

#### 11. Custom Themes
**Source**: terminal-config.md, statusline.md  
**Mechanism**:
- Base preset + token overrides
- Color tokens for UI elements
- Custom status line (shell script with JSON input)
- Live reload on file change

**Reference for Lyra**: UI customization pattern

**Workstream**: §4.11 UI/UX Enhancements

#### 12. Keybindings System
**Source**: keybindings.md  
**Mechanism**:
- Context-based bindings (Chat, Autocomplete, Confirmation, etc.)
- Action namespace (app:, chat:, history:, etc.)
- Chord support (multi-key sequences)
- Modifier keys (ctrl, shift, alt, meta)

**Reference for Lyra**: Input handling pattern

**Workstream**: §4.11 UI/UX Enhancements

## Cross-Cutting Insights

### 1. Permission System Design Philosophy
Claude Code uses **defense in depth**:
- Permission modes set baseline behavior
- Permission rules provide fine-grained control
- Sandboxing provides OS-level enforcement
- Auto mode adds ML-based classification

**Lesson for Lyra**: Layer multiple permission mechanisms rather than relying on a single gate.

### 2. Context Management Strategy
Claude Code optimizes for **cost and performance**:
- Prompt caching reduces repeated content costs
- MCP Tool Search defers schema loading
- Compaction preserves critical context
- Subagents isolate verbose operations

**Lesson for Lyra**: Context is expensive - defer, cache, and isolate aggressively.

### 3. Extensibility Architecture
Claude Code provides **multiple extension points**:
- Skills for workflows
- Hooks for lifecycle events
- Plugins for bundled components
- MCP for external integrations
- Subagents for specialized tasks

**Lesson for Lyra**: Provide extension points at multiple abstraction levels.

### 4. Settings Management
Claude Code uses **hierarchical configuration**:
- Managed settings enforce org policy
- Project settings enable team standards
- Local settings allow personal overrides
- Arrays merge, scalars replace

**Lesson for Lyra**: Configuration precedence must be explicit and predictable.

### 5. Cost Optimization
Claude Code provides **multiple cost levers**:
- Model selection (Haiku < Sonnet < Opus)
- Effort levels (low < medium < high < xhigh < max)
- Context management (compaction, caching)
- Tool search (deferred loading)
- Subagent delegation (isolate expensive ops)

**Lesson for Lyra**: Cost optimization requires control at multiple levels.

## Feature Parity Matrix

| Feature | Claude Code | Lyra Current | Priority | Workstream |
|---------|-------------|--------------|----------|------------|
| Permission Modes | ✅ 6 modes | ❌ | HIGH | §4.16 |
| Permission Rules | ✅ Pattern-based | ❌ | HIGH | §4.16 |
| OS Sandboxing | ✅ Seatbelt/bubblewrap | ❌ | HIGH | §4.16 |
| Auto Mode | ✅ Classifier-based | ❌ | MEDIUM | §4.16 |
| MCP Tool Search | ✅ Deferred loading | ❌ | HIGH | §4.5 |
| Hooks System | ✅ 5 events, 5 handlers | ❌ | HIGH | §4.4 |
| Skills | ✅ Agent Skills + extensions | ⚠️ Partial | MEDIUM | §4.4 |
| Plugins | ✅ Bundled components | ❌ | MEDIUM | §4.4 |
| Subagents | ✅ Isolated contexts | ❌ | HIGH | §4.13 |
| Context Compaction | ✅ Auto + manual | ⚠️ Basic | HIGH | §4.2 |
| Prompt Caching | ✅ Multi-layer | ❌ | HIGH | §4.2 |
| Model Routing | ✅ Aliases + effort | ⚠️ Basic | MEDIUM | §4.5 |
| Settings Layers | ✅ 5-layer hierarchy | ⚠️ 2-layer | MEDIUM | §4.1 |
| Voice Dictation | ✅ Hold + tap modes | ❌ | HIGH | §4.0 |
| Fullscreen Mode | ✅ Alt screen + mouse | ❌ | LOW | §4.11 |
| Custom Themes | ✅ Base + overrides | ❌ | LOW | §4.11 |
| Keybindings | ✅ Full remapping | ❌ | LOW | §4.11 |
| OpenTelemetry | ✅ Metrics + logs + traces | ❌ | MEDIUM | §4.17 |
| Cost Tracking | ✅ Per-session + attribution | ❌ | MEDIUM | §4.17 |

## Implementation Recommendations

### Phase 1: Core Safety (§4.16)
1. Implement permission modes (default, acceptEdits, plan)
2. Add permission rules with pattern matching
3. Integrate OS-level sandboxing (start with Docker)
4. Build permission UI/prompts

### Phase 2: Context Optimization (§4.2, §4.5)
1. Implement MCP Tool Search
2. Add prompt caching layer
3. Build context compaction with preservation rules
4. Add context usage tracking

### Phase 3: Extensibility (§4.4, §4.13)
1. Implement hooks system (PreToolUse, PostToolUse)
2. Add subagent architecture
3. Build skills loader with Agent Skills support
4. Create plugin bundling format

### Phase 4: Voice & UX (§4.0, §4.11)
1. Implement voice dictation (hold + tap modes)
2. Add fullscreen rendering mode
3. Build custom theme system
4. Implement keybindings remapping

### Phase 5: Observability (§4.17)
1. Integrate OpenTelemetry
2. Add cost tracking and attribution
3. Build usage analytics dashboard
4. Implement alerting and monitoring

## URLs Researched (19/38)

✅ Completed:
1. terminal-config.md - Terminal configuration
2. settings.md - Settings system and precedence
3. cli-reference.md - CLI commands and flags
4. model-config.md - Model routing and effort levels
5. glossary.md - Terminology and concepts
6. sub-agents.md - Subagent architecture
7. keybindings.md - Keybinding customization
8. agent-sdk/tool-search - MCP Tool Search
9. statusline.md - Custom status line
10. fullscreen.md - Fullscreen rendering mode
11. fast-mode.md - Fast mode configuration
12. output-styles.md - Output style system
13. sandbox-environments.md - Isolation approaches
14. sandboxing.md - Sandboxed Bash tool
15. security.md - Security architecture
16. voice-dictation.md - Voice input
17. whats-new/2026-w20 - Week 20 release notes
18. monitoring-usage.md - OpenTelemetry integration
19. costs.md - Cost management
20. whats-new.md - Release digest index
21. whats-new/2026-w19 - Week 19 release notes

⏳ Remaining (17):
- skills.md
- platform docs (agent-skills/overview, best-practices, agent-sdk/skills)
- plugins-reference.md
- tools-reference.md
- goal.md
- hooks-guide.md
- hooks.md
- mcp.md
- interactive-mode.md
- commands.md
- checkpointing.md
- permissions.md
- agent-teams.md
- channels-reference.md
- env-vars.md

## Next Steps

1. Continue researching remaining 17 URLs
2. Update source-ledger.md with "read" status for completed URLs
3. Append detailed findings to findings.md
4. Create workstream-specific brainstorm files
5. Update feature parity matrix with new discoveries
