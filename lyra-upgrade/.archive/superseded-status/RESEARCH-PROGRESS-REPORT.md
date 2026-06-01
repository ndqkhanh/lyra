# Lyra Upgrade Research Progress Report

**Date**: 2026-05-31  
**Session**: Run 2 - Claude Code Documentation Research  
**Status**: In Progress (21 of 38 URLs completed)

## Executive Summary

Successfully researched 21 Claude Code documentation URLs, extracting portable features and architectural patterns for Lyra upgrade. Key discoveries include multi-layer permission systems, MCP Tool Search, hooks architecture, and comprehensive context management strategies.

## Research Coverage

### §3.1 Claude Code Official Docs: 21/38 (55%)

**Completed URLs (21)**:
1. ✅ cli-reference - CLI commands and flags
2. ✅ settings - Settings system with 5-layer precedence
3. ✅ model-config - Model routing, effort levels, aliases
4. ✅ terminal-config - Terminal configuration and setup
5. ✅ glossary - Terminology and core concepts
6. ✅ sub-agents - Subagent architecture with isolated contexts
7. ✅ agent-sdk/tool-search - MCP Tool Search (deferred schema loading)
8. ✅ keybindings - Keybinding customization system
9. ✅ statusline - Custom status line with shell scripts
10. ✅ fullscreen - Fullscreen rendering mode (alternate screen)
11. ✅ output-styles - Output style system (system prompt modification)
12. ✅ fast-mode - Fast mode configuration (2.5x speed)
13. ✅ voice-dictation - Voice input (hold + tap modes)
14. ✅ sandboxing - Sandboxed Bash tool (OS-level isolation)
15. ✅ sandbox-environments - Isolation approaches comparison
16. ✅ security - Security architecture and best practices
17. ✅ monitoring-usage - OpenTelemetry integration
18. ✅ costs - Cost management and optimization
19. ✅ whats-new - Release digest index
20. ✅ whats-new/2026-w20 - Week 20 release notes
21. ✅ whats-new/2026-w19 - Week 19 release notes

**Remaining URLs (17)**:
- skills.md
- platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- platform.claude.com/docs/en/agent-sdk/skills
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

## Key Discoveries

### 1. Multi-Layer Permission System (HIGH PRIORITY)
**Workstream**: §4.16 Safety & Guardrails

Claude Code implements defense-in-depth with three layers:
- **Layer 1**: Permission modes (default, acceptEdits, plan, auto, dontAsk, bypassPermissions)
- **Layer 2**: Permission rules (pattern-based allow/deny/ask with glob matching)
- **Layer 3**: OS-level sandboxing (Seatbelt on macOS, bubblewrap on Linux)

**Port Strategy**: Implement all three layers in Lyra for comprehensive safety.

### 2. MCP Tool Search (HIGH PRIORITY)
**Workstream**: §4.5 Tool Router & Orchestration

Deferred tool schema loading that scales to 10,000 tools:
- Tool names loaded at startup (lightweight)
- Full schemas fetched on-demand when tool is used
- 3-5 most relevant tools loaded per search
- Reduces context consumption by 10-20K tokens for large tool sets

**Port Strategy**: Implement ToolCatalog interface with search capability.

### 3. Hooks System (HIGH PRIORITY)
**Workstream**: §4.4 Skills & Workflows

Lifecycle event handlers with multiple handler types:
- **Events**: PreToolUse, PostToolUse, Stop, ConfigChange, Notification
- **Handlers**: command, http, mcp, llm, subagent
- **Matchers**: Filter by tool name, arguments, patterns

**Port Strategy**: Build event-driven hook system with pluggable handlers.

### 4. Context Management (HIGH PRIORITY)
**Workstream**: §4.2 Memory Architecture

Multi-faceted approach to context optimization:
- **Prompt caching**: System prompt, tools, conversation history
- **Compaction**: Tool outputs cleared first, then conversation summarized
- **Preservation**: CLAUDE.md and auto memory survive compaction
- **MCP Tool Search**: Defers schema loading until needed

**Port Strategy**: Implement CompactionStrategy with preservation rules.

### 5. Subagent Architecture (HIGH PRIORITY)
**Workstream**: §4.13 Agent Swarm & Fleet

Isolated execution contexts for specialized tasks:
- Independent context windows
- Custom system prompts
- Configurable tool access
- Model selection (can use Haiku for cost savings)
- Foreground or background execution

**Port Strategy**: Build SubagentConfig with isolation options.

### 6. Settings Precedence (MEDIUM PRIORITY)
**Workstream**: §4.1 Configuration System

5-layer hierarchy with clear merge semantics:
1. Managed (org policy - highest priority)
2. Command-line arguments
3. Local (.claude/settings.local.json - gitignored)
4. Project (.claude/settings.json - committed)
5. User (~/.claude/settings.json - lowest)

Arrays merge, scalars replace.

**Port Strategy**: Implement SettingsLayer with priority and merge strategy.

### 7. Model Routing with Effort Levels (MEDIUM PRIORITY)
**Workstream**: §4.5 Tool Router & Orchestration

Sophisticated model selection:
- **Aliases**: sonnet, opus, haiku, opusplan, best
- **Effort levels**: low, medium, high, xhigh, max, ultracode
- **Adaptive reasoning**: Model decides thinking budget per task
- **opusplan**: Opus for planning, Sonnet for execution

**Port Strategy**: Add cost-aware routing with fallback chains.

### 8. Voice Dictation (HIGH PRIORITY - P0)
**Workstream**: §4.0 Voice Mode

Two-mode voice input system:
- **Hold mode**: Push-to-talk with key-repeat detection
- **Tap mode**: Toggle recording with single keypress
- Live transcription with coding vocabulary
- 19 language support
- Auto-submit on release (configurable)

**Port Strategy**: Add local STT option (Whisper) alongside cloud provider.

### 9. Fullscreen Rendering (LOW PRIORITY)
**Workstream**: §4.11 UI/UX Enhancements

Alternate screen buffer rendering:
- Mouse support (click, drag, scroll)
- Flat memory usage (only visible messages rendered)
- Search and navigation (less-style)
- No flicker or scroll jumps

**Port Strategy**: Add TUI framework abstraction for render modes.

### 10. OpenTelemetry Integration (MEDIUM PRIORITY)
**Workstream**: §4.17 Observability

Standard observability pattern:
- Metrics (OTLP, Prometheus, console)
- Logs/Events (OTLP, console)
- Traces (beta)
- Configurable export intervals

**Port Strategy**: Use standard OTEL libraries and environment variables.

## Cross-Cutting Insights

### Permission System Philosophy
**Defense in depth**: Layer multiple permission mechanisms rather than relying on a single gate. Each layer catches different threat vectors.

### Context Management Strategy
**Cost and performance optimization**: Context is expensive - defer, cache, and isolate aggressively. Use prompt caching, deferred loading, and subagent isolation.

### Extensibility Architecture
**Multiple extension points**: Provide extension points at multiple abstraction levels (skills, hooks, plugins, MCP, subagents) to support different use cases.

### Settings Management
**Hierarchical configuration**: Configuration precedence must be explicit and predictable. Arrays merge, scalars replace. Managed settings enforce org policy.

### Cost Optimization
**Multiple cost levers**: Provide control at multiple levels (model selection, effort levels, context management, tool search, subagent delegation).

## Feature Parity Analysis

### HIGH PRIORITY Gaps
1. ❌ Permission modes (6 modes)
2. ❌ Permission rules (pattern-based)
3. ❌ OS-level sandboxing
4. ❌ MCP Tool Search
5. ❌ Hooks system (5 events, 5 handlers)
6. ❌ Subagents (isolated contexts)
7. ❌ Prompt caching (multi-layer)
8. ❌ Voice dictation (hold + tap modes)

### MEDIUM PRIORITY Gaps
1. ⚠️ Skills (partial implementation)
2. ❌ Plugins (bundled components)
3. ⚠️ Context compaction (basic implementation)
4. ⚠️ Model routing (basic implementation)
5. ⚠️ Settings layers (2-layer vs 5-layer)
6. ❌ Auto mode (classifier-based)
7. ❌ OpenTelemetry integration
8. ❌ Cost tracking and attribution

### LOW PRIORITY Gaps
1. ❌ Fullscreen mode (alt screen + mouse)
2. ❌ Custom themes
3. ❌ Keybindings remapping

## Implementation Roadmap

### Phase 1: Core Safety (Weeks 1-2)
- Implement permission modes
- Add permission rules with pattern matching
- Integrate OS-level sandboxing
- Build permission UI/prompts

### Phase 2: Context Optimization (Weeks 3-4)
- Implement MCP Tool Search
- Add prompt caching layer
- Build context compaction with preservation
- Add context usage tracking

### Phase 3: Extensibility (Weeks 5-6)
- Implement hooks system
- Add subagent architecture
- Build skills loader
- Create plugin bundling format

### Phase 4: Voice & UX (Weeks 7-8)
- Implement voice dictation
- Add fullscreen rendering mode
- Build custom theme system
- Implement keybindings remapping

### Phase 5: Observability (Weeks 9-10)
- Integrate OpenTelemetry
- Add cost tracking and attribution
- Build usage analytics dashboard
- Implement alerting and monitoring

## Deliverables Created

1. ✅ **claude-code-docs-research.md** - Comprehensive research summary with:
   - Executive summary of architectural patterns
   - Portable features with port strategies
   - Cross-cutting insights
   - Feature parity matrix
   - Implementation recommendations

2. ✅ **source-ledger.md** - Updated with "read" status for 21 URLs

3. ✅ **RESEARCH-PROGRESS-REPORT.md** - This document

## Next Steps

1. **Continue Documentation Research** (17 URLs remaining):
   - skills.md and platform agent-skills docs
   - plugins-reference.md and tools-reference.md
   - goal.md (completion conditions)
   - hooks-guide.md and hooks.md (detailed hook patterns)
   - mcp.md (MCP integration details)
   - interactive-mode.md and commands.md
   - checkpointing.md (rewind/restore)
   - permissions.md (detailed permission rules)
   - agent-teams.md (multi-agent coordination)
   - channels-reference.md (event-driven triggers)
   - env-vars.md (environment configuration)

2. **Update findings.md** with detailed research rows

3. **Create workstream-specific brainstorm files** based on discoveries

4. **Update feature parity matrix** with new findings

5. **Begin §3.2 research** (Comparable Harnesses - 12 repos)

## Research Quality Metrics

- **URLs Researched**: 21/38 (55%)
- **Findings Captured**: Yes (comprehensive summary)
- **Port Strategies Defined**: Yes (for all high-priority features)
- **Workstream Mapping**: Yes (all features mapped to §4.X)
- **Cross-Cutting Insights**: Yes (5 major insights documented)
- **Implementation Roadmap**: Yes (5-phase plan with timeline)

## Conclusion

The Claude Code documentation research has revealed a mature, production-grade agentic harness with sophisticated features across multiple dimensions. The multi-layer permission system, MCP Tool Search, hooks architecture, and context management strategies are particularly valuable for Lyra's upgrade.

Key takeaway: Claude Code's architecture demonstrates that **defense in depth** (permission system), **aggressive optimization** (context management), and **multiple extension points** (skills, hooks, plugins, MCP, subagents) are essential for a production-grade agentic harness.

The remaining 17 URLs will provide additional details on skills, hooks, MCP integration, and agent teams - all critical for completing the feature parity analysis and implementation roadmap.
