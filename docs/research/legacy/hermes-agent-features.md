# Hermes-Agent Deep Research - Complete Feature Inventory

## Executive Summary

Hermes-Agent is a self-improving AI agent with persistent memory, multi-platform messaging, and autonomous skill creation. Built by NousResearch.

---

## KEY FEATURES SUMMARY

### 1. TOOLS (70+)
- **Browser Tools** (~12) — Navigation, clicking, typing, CDP commands
- **File Management** (4) — read_file, search_files, patch, write_file
- **Code & Execution** (2) — execute_code, process management
- **Home Automation** (4) — Device control, Home Assistant
- **RL** (10) — Model training, environment config
- **Communication** — Platform messaging, Discord, TTS
- **Music** (7) — Spotify integration
- **Memory & Context** — memory, session_search, todo
- **Specialized** — Image generation, video analysis, web search, vision, skill management, delegation, cronjobs

### 2. TOOLSETS SYSTEM ⭐
- **Core Toolsets** — file, terminal, web, browser, vision, memory, delegation
- **Composite Toolsets** — debugging, research, automation
- **Platform Toolsets** — hermes-cli, hermes-telegram, hermes-discord
- **Configuration** — Per-session, per-platform, interactive, custom, dynamic

### 3. SKILLS SYSTEM
- Markdown with YAML frontmatter in `~/.hermes/skills/`
- Platform-specific restrictions
- Conditional activation
- Compatible with agentskills.io standard
- **Progressive Disclosure** — 3 levels to minimize tokens
- **Autonomous Creation** ⭐ — Agent creates skills after complex workflows
- **Hub Integration** — Browse/search from multiple sources
- **Custom Taps** — Team-published collections

### 4. MEMORY SYSTEMS ⭐
**Two-File Model** (`~/.hermes/memories/`):
- **MEMORY.md** (2,200 chars) — Environment facts, conventions
- **USER.md** (1,375 chars) — User profile, preferences
- **Frozen-snapshot pattern** — Loaded at session start, preserves cache
- **Session search** — SQLite + Gemini Flash summarization

### 5. CONTEXT MANAGEMENT ⭐
**Dual-Layer Compression**:
- Gateway Session Hygiene (85% threshold)
- Agent ContextCompressor (50% threshold)

**Four-Phase Algorithm**:
1. Prune Tool Results
2. Determine Boundaries
3. Generate Structured Summary
4. Assemble Compressed Messages

**Context Engine Plugins** — Replace default compression

### 6. MULTI-AGENT ORCHESTRATION
**Profiles** ⭐ — Multiple independent agents:
- Separate home directories
- Independent config, memory, sessions, skills
- Command aliases, independent gateways
- No centralized orchestration

**Child Agent Delegation**:
- Full AIAgent instances in ThreadPoolExecutor
- Depth limits, concurrent caps
- Interrupt handling
- Six terminal backends

**Specialization Patterns**:
- Role-based teams
- Mixture of agents (parallel queries)

### 7. MESSAGING GATEWAY ⭐
**20+ Platforms**:
- Telegram, Discord, Slack, WhatsApp, Signal
- SMS, Email, Google Chat, LINE
- Microsoft Teams, Mattermost, Matrix
- DingTalk, Feishu/Lark, WeCom, WeChat
- BlueBubbles, QQ Bot, Yuanbao
- Home Assistant, Open WebUI, Webhooks

**Single Background Process** — All platforms simultaneously

### 8. PERSONALITY & SOUL.MD
- `~/.hermes/SOUL.md` — Agent identity foundation
- First slot in system prompt
- Defines communication style
- Persists across sessions
- `/personality` for temporary overlays

### 9. LEARNING LOOP ⭐
**Self-Improvement Cycle**:
- Task → Solve → Document → Store → Improve → Next Task (Faster)
- Runs autonomously every ~15 tasks
- Cache-aware memory architecture
- Identifies patterns, writes skills
- Refines skills during use

### 10. PLUGIN ARCHITECTURE
**Extension Points**:
- User and project-level plugins
- Memory plugins
- Context engine plugins
- Provider plugins
- Platform adapters

**Auto-Discovery** — `plugins/<type>/<name>/`

### 11. MCP INTEGRATION
- Discovers MCP servers at startup
- Registers tools with auto-prefixing
- Stdio and HTTP servers
- Tool filtering & security
- Dynamic updates
- Resources and prompts support

### 12. TERMINAL BACKENDS (6)
1. Local (default)
2. Docker
3. SSH
4. Singularity
5. Modal (serverless)
6. Daytona (serverless dev environments)

### 13. ARCHITECTURE
**Core Components**:
- AIAgent (run_agent.py) — Central orchestration
- Prompt System — Assembly, compression, caching
- Provider Resolution — 18+ providers with OAuth
- Tool System — 70+ tools, 28 toolsets, 7 backends

**Supporting Infrastructure**:
- Session Persistence — SQLite with FTS
- Messaging Gateway — 20 platform adapters
- Plugin System — User/project plugins

**Design Principles**:
- Prompt stability
- Observable execution
- Loose coupling

---

## KEY GAPS TO STEAL

### High Priority
1. **Learning Loop** ⭐ — Autonomous skill creation
2. **Messaging Gateway** ⭐ — 20+ platforms
3. **SOUL.md** ⭐ — Agent personality
4. **Four-Phase Compression** ⭐ — Advanced context management
5. **Profiles** ⭐ — Multiple independent agents
6. **70+ Tools** — Comprehensive toolkit
7. **28 Toolsets** — Organized tool bundles
8. **6 Terminal Backends** — Flexible execution

### Medium Priority
1. **Context Engine Plugins** — Pluggable compression
2. **Memory Plugins** — Custom memory backends
3. **Hub Integration** — Skill marketplace
4. **Custom Taps** — Team skill collections
5. **Progressive Disclosure** — 3-level skill loading
6. **Frozen-Snapshot Memory** — Cache-aware
7. **Session Search** — SQLite + LLM summarization
8. **Platform Adapters** — Messaging integrations

### Low Priority
1. **Home Automation** — Home Assistant integration
2. **RL Tools** — Reinforcement learning
3. **Music Tools** — Spotify integration
4. **Mixture of Agents** — Parallel model queries

---

## UNIQUE VS. CLAUDE CODE

**Hermes-Agent**:
- Single agent that improves over time
- Persistent across sessions
- Multi-platform messaging (20+)
- Multiple terminal backends (6)
- Profile-based multi-instance
- Self-improving through learning loop
- Cache-aware memory

**Claude Code**:
- IDE-centric, repository-focused
- Multi-agent orchestration
- Git worktree isolation
- TypeScript-based
- Distributed tracing
- Compile-time provider abstraction

---

## SOURCES

- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs/)
- [Features Overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/overview)
- [Built-in Tools Reference](https://hermes-agent.nousresearch.com/docs/reference/tools-reference)
- [Toolsets Reference](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference/)
- [Personality & SOUL.md](https://hermes-agent.nousresearch.com/docs/user-guide/features/personality)
- [Profiles: Running Multiple Agents](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)
- [MCP Integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/)
- [Context Compression](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching/)
- [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
- [NousResearch/hermes-agent GitHub](https://github.com/NousResearch/hermes-agent)

---

**Research Completed**: 2026-05-11
**Agent**: Explore (Hermes-Agent)
**Status**: ✅ Complete
