# Open-Claw Deep Research - Complete Feature Inventory

## Executive Summary

Open-Claw encompasses two distinct projects:
1. **claw-code** (ultraworkers/claw-code) - Rust reimplementation of Claude Code
2. **OpenClaw** (openclaw/openclaw) - Multi-channel AI assistant framework

---

## 1. CLAW-CODE (Rust Reimplementation)

### Tech Stack
- **Language**: Rust (96.5%) with Python reference
- **Build System**: Cargo workspace
- **Design**: High-performance, local-first, safe execution
- **API Support**: Anthropic, OpenAI, xAI, OpenAI-compatible, DashScope

### Core Components
- CLI Agent Harness
- Session Management (`.claw/sessions/`)
- Health Diagnostics (`claw doctor`)
- Permission System (read-only, workspace-write, danger-full-access)
- Configuration (`.claude.json`, `.claude/settings.local.json`)

### Interactive REPL Commands
- `/ultraplan` — Task decomposition with extended reasoning
- `/teleport` — Symbol/file navigation
- `/bughunter` — Code pattern analysis
- `/help`, `/status`, `/cost`, `/config`, `/session`, `/model`, `/permissions`, `/export`

### Operational Commands
- `doctor` — Setup and diagnostics
- `status` — Workspace inspection
- `sandbox` — Environment testing
- `agents` — Agent management
- `mcp` — Model Context Protocol
- `skills` — Skill management
- `system-prompt` — Prompt inspection

**Lyra Comparison**:
- ⚠️ Different: Rust vs Python
- ✅ Similar: Session management
- ✅ Similar: Permission system
- ❌ Missing: `/ultraplan`, `/teleport`, `/bughunter`

---

## 2. OPENCLAW (Multi-Channel Framework)

### Three-Layer Architecture
1. **Connector Layer** — 20+ messaging platforms
2. **Gateway Controller** — Session-aware memory
3. **Agent Runtime** — Pi Agent Core

### Gateway System
- **Port**: 18789 (WebSocket)
- **Concurrency**: Single Node.js process with async
- **Queue**: Lane-aware FIFO
- **Heartbeat**: Periodic agent turns (30 min default)

### Communication Channels (20+)
- WhatsApp, Telegram, Slack, Discord, Signal
- Email (Gmail Pub/Sub), Webhooks
- CLI, Web interface
- Voice (macOS/iOS/Android)
- Mattermost, custom integrations

**Lyra Comparison**:
- ❌ Missing: Multi-channel support (only CLI)
- ❌ Missing: Gateway system
- ❌ Missing: Voice interface
- ❌ Missing: 20+ messaging platforms

---

## 3. TOOLS INVENTORY

### Claw-Code Tools
- File Operations: read, write, edit, apply_patch
- System Execution: bash/exec, process management
- Search & Navigation: glob, grep
- API Integration: web_search, web_fetch
- Session Management: persistence and resume

### OpenClaw Built-in Tools (25+)
- `exec` / `process` — Shell commands, background processes
- `code_execution` — Sandboxed Python
- `browser` — Chromium automation
- `web_search` / `x_search` / `web_fetch` — Web and X
- `read` / `write` / `edit` — File operations
- `apply_patch` — Multi-hunk patches
- `message` — Cross-channel messaging
- `nodes` — Device discovery
- `cron` / `gateway` — Job scheduling
- `image` / `image_generate` — Image analysis/generation
- `music_generate` — Music generation
- `video_generate` — Video generation
- `tts` — Text-to-speech
- `sessions_*` / `subagents` — Session orchestration
- `session_status` — Status readback

### Tool Configuration Profiles
- **full** — All tools
- **coding** — Filesystem, runtime, web, sessions, media
- **messaging** — Channel-focused
- **minimal** — `session_status` only

### Tool Groups
- `group:fs` — Filesystem
- `group:runtime` — Code execution
- `group:web` — Web access
- `group:media` — Media generation

**Lyra Comparison**:
- ✅ Has most core tools
- ❌ Missing: Media generation (music, video)
- ❌ Missing: Cross-channel messaging
- ❌ Missing: Device discovery (`nodes`)
- ❌ Missing: Tool configuration profiles

---

## 4. SKILLS SYSTEM

### Skill Architecture
- Markdown-based instruction files
- Not code—declarative workflows

### Skill Structure
- **SKILL.md** — Core skill definition
- **AGENTS.md** — Agent-specific guidance
- **SOUL.md** — Agent personality
- **TOOLS.md** — Tool-specific constraints

### Skill Levels
1. **Bundled Skills** — Shipped with OpenClaw
2. **Managed Skills** — Community-maintained via ClawHub
3. **Workspace Skills** — User-defined in `~/.openclaw/workspace/skills/`

### ClawHub Registry ⭐
- **3,000+ Community Skills** — Public marketplace
- **Categories**: coding-agent, memory-tools, subagent-orchestrator
- **Security Model**: Markdown (not sandboxed code)
- **Malware Risk**: 14+ malicious skills detected in early 2026

### Notable Skills
- `coding-agent` — Core coding workflow
- `memory-tools` — Agent-controlled memory
- `subagent-orchestrator` — Multi-agent routing
- `canvas` — Agent-driven visual rendering

**Lyra Comparison**:
- ✅ Has skill system
- ❌ Missing: ClawHub registry (3,000+ skills)
- ❌ Missing: SOUL.md personality
- ❌ Missing: TOOLS.md constraints
- ⚠️ Different: Uses custom format

---

## 5. PLUGINS & EXTENSIBILITY

### Plugin System
- Register new capabilities: tools, channels, providers, media handlers

### Plugin Types
1. **Tool Providers** — Custom tools
2. **Channel Adapters** — Messaging platforms
3. **Model Providers** — LLM backends
4. **Media Handlers** — Image/video/audio

### Extension Ecosystem
- Skills + Hooks + Plugins trinity
- Hooks for automated behaviors
- Settings.json for configuration

### Community Plugins
- Browser automation
- Custom API integrations
- Database connectors
- Webhook handlers
- MCP servers

**Lyra Comparison**:
- ✅ Has plugin system
- ❌ Missing: Channel adapters
- ❌ Missing: Media handlers
- ⚠️ Different: Simpler plugin system

---

## 6. AGENTS & ORCHESTRATION

### Pi Agent Core ⭐
**Minimal 4-Tool Agent**:
- Tools: Read, Write, Edit, Bash
- Shortest system prompt of any framework
- Extensible via skills and plugins
- All reasoning inside Pi

### Agent Loop
1. Intake — Message arrives
2. Context Assembly — Load memory, skills, tools
3. Model Inference — LLM reasoning
4. Tool Execution — Execute tools
5. Streaming Replies — Stream output
6. Persistence — Save state

### Multi-Agent Orchestration

**Sessions** — Backbone of concurrency
- Every conversation gets own session
- DMs, group chats, Telegram topics, cron jobs, sub-agents
- Session-aware memory and state

**Sub-Agents** — Parallel execution
- Spawn for parallel work
- Each uses primary model
- Orchestrated via `subagent-orchestrator` skill
- Enable complex workflows

**Multi-Agent Routing**
- Multiple isolated agents
- Multiple channel accounts
- Inbound routed via bindings
- Orchestrator-worker pattern

**Agent Isolation**
- Separate workspaces per agent
- Per-agent sessions
- Sandboxing via Docker, SSH, OpenShell
- Tool access control per environment

**Lyra Comparison**:
- ✅ Has multi-agent orchestration
- ✅ Has subagents
- ❌ Missing: Pi Agent Core (minimal 4-tool design)
- ❌ Missing: Multi-channel routing
- ❌ Missing: Orchestrator-worker pattern
- ⚠️ Different: More complex agent system

---

## 7. MEMORY SYSTEMS

### Claw-Code Memory
- Project Memory: `.claude.json`
- User Memory: `.claude/settings.local.json`
- Session Memory: `.claw/sessions/`
- Auto-Memory: Learns preferences

### OpenClaw Memory Architecture

**Heartbeat System** ⭐
- Periodic context refresh (30 min default)
- Agent replies with `HEARTBEAT_OK` or alerts
- Optional `HEARTBEAT.md` checklist
- Cost optimization via `isolatedSession` and `lightContext`

**Memory Skills**
- `memory-tools` skill — Agent-controlled memory
- Selective storage, retrieval, decay
- Confidence scoring and semantic search
- Persistent markdown files (no vector DB)

**Session-Based Memory**
- Per-session context isolation
- Cross-session memory via heartbeat
- Lightweight local markdown
- No heavy vector database

**Multi-Layer Memory**
1. Project Rules — Shared across sessions
2. User Preferences — Machine-specific
3. Feedback Loop — Learning from corrections
4. Auto-Memory — Implicit pattern learning

**Lyra Comparison**:
- ✅ Has session memory
- ✅ Has project memory
- ✅ Has auto-memory
- ❌ Missing: Heartbeat system
- ❌ Missing: `memory-tools` skill
- ⚠️ Different: Uses JSON, not markdown

---

## 8. CONTEXT MANAGEMENT

### Context Assembly Pipeline
1. Channel Context — Message source
2. Session Context — Conversation history
3. Memory Context — CLAUDE.md, SOUL.md, AGENTS.md
4. Tool Context — Available tools
5. Skill Context — Injected instructions

### Lane-Aware Queue System
- FIFO message queue
- Prevents message reordering
- Handles concurrent sessions
- Single Node.js process

### Concurrency Model
- Async/await promises
- Lane-aware routing
- Retry control and backoff
- Graceful degradation

**Lyra Comparison**:
- ✅ Has context assembly
- ❌ Missing: Lane-aware queue
- ❌ Missing: Multi-channel context
- ⚠️ Different: Simpler concurrency

---

## 9. UNIQUE FEATURES

### Claw-Code Innovations
1. **Clean-Room Rewrite** — Rust from scratch
2. **Multi-Provider Support** — Anthropic, OpenAI, xAI, DashScope
3. **Permission Modes** — Granular control
4. **Health Diagnostics** — `claw doctor`
5. **Session Persistence** — Resume work
6. **Model Aliases** — Built-in shortcuts

### OpenClaw Innovations ⭐
1. **A2UI Canvas System** — Agent-driven visual rendering
2. **Heartbeat Automation** — Proactive agent turns
3. **Multi-Channel Inbox** — 20+ platforms
4. **Voice Wake & Talk** — macOS/iOS/Android
5. **Webhook Automation** — Event-driven triggers
6. **Cron Scheduling** — node-cron based
7. **Pairing System** — Secure credential injection
8. **Sandboxing** — Docker/SSH/OpenShell
9. **A2A Protocol** — Agent-to-Agent communication
10. **Live Canvas** — Real-time visual workspace

### Security & Isolation
- Permission Model — Least-privilege
- Sandboxing — Isolated containers
- Tool Access Control — Per-environment
- Skill Vetting — Community reviewed
- Pairing — Secure credentials

**Lyra Comparison**:
- ❌ Missing: A2UI Canvas System
- ❌ Missing: Multi-channel inbox
- ❌ Missing: Voice interface
- ❌ Missing: Webhook automation
- ❌ Missing: A2A Protocol
- ❌ Missing: Live Canvas
- ✅ Has: Permission model
- ✅ Has: Session persistence

---

## 10. OPEN SOURCE & COMMUNITY

### Claw-Code Ecosystem
- **Primary Repo**: ultraworkers/claw-code (100K+ stars)
- Community forks
- MCP servers integration
- Claude Code plugins

### OpenClaw Ecosystem
- **Main Repo**: openclaw/openclaw (145K+ stars)
- **ClawHub Registry**: 3,000+ skills
- **Companion Projects**:
  - OpenClaw Office — Visual monitoring
  - Mission Control — Multi-agent coordination
  - OpenClaw-RL — Personalization
- **Integrations**: Mattermost, Kubernetes, Raspberry Pi, BLE

### Extensibility Patterns
1. Skill Development — Write SKILL.md
2. Plugin Creation — Register tools/channels/providers
3. MCP Integration — Model Context Protocol
4. Custom APIs — REST/CLI/SaaS
5. Webhook Handlers — Event-driven

**Lyra Comparison**:
- ❌ Missing: 145K+ stars community
- ❌ Missing: ClawHub registry
- ❌ Missing: Companion projects
- ❌ Missing: Raspberry Pi/BLE integrations
- ⚠️ Different: Smaller community

---

## KEY GAPS TO STEAL

### High Priority
1. **ClawHub Registry** — 3,000+ community skills
2. **Multi-Channel Support** — 20+ messaging platforms
3. **Heartbeat System** — Proactive agent turns
4. **A2UI Canvas System** — Visual rendering
5. **Voice Interface** — macOS/iOS/Android
6. **Pi Agent Core** — Minimal 4-tool design
7. **Webhook Automation** — Event-driven triggers
8. **A2A Protocol** — Agent-to-Agent communication

### Medium Priority
1. **Live Canvas** — Real-time workspace
2. **Pairing System** — Secure credentials
3. **Cron Scheduling** — node-cron based
4. **Device Discovery** — `nodes` tool
5. **Media Generation** — Music, video
6. **Tool Configuration Profiles** — full/coding/messaging/minimal
7. **SOUL.md** — Agent personality
8. **TOOLS.md** — Tool constraints

### Low Priority
1. **Rust Rewrite** — Performance boost
2. **145K+ stars** — Community size
3. **OpenClaw Office** — Visual monitoring
4. **Mission Control** — Multi-agent coordination
5. **OpenClaw-RL** — Personalization

---

## SOURCES

- [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code)
- [openclaw/openclaw](https://github.com/openclaw/openclaw)
- [OpenClaw Tools Documentation](https://github.com/openclaw/openclaw/blob/main/docs/tools/index.md)
- [OpenClaw Heartbeat System](https://github.com/openclaw/openclaw/blob/main/docs/gateway/heartbeat.md)
- [ClawHub Skill Registry](https://github.com/openclaw/clawhub)
- [What Are OpenClaw Tools and Skills? Complete Guide](http://apidog.com/blog/openclaw-tools-skills-guide/)
- [Agent Pi: How 4 Tools Coding Agent Power OpenClaw](https://shivamagarwal7.medium.com/agentic-ai-pi-anatomy-of-a-minimal-coding-agent-powering-openclaw-5ecd4dd6b440)
- [Architecture, Agent Loop, and What Makes It Tick](https://www.chattergo.com/blog/openclaw-deep-dive-architecture-agent-loop)
- [Inside OpenClaw: Sessions, Sub-Agents, and Multi-Agent Orchestration](https://avasdream.com/blog/openclaw-sessions-multiagent-deep-dive)
- [OpenClaw Security & Privacy Guide](https://anotherwrapper.com/blog/openclaw-security-privacy)
- [How Anthropic Redefined AI Coding Tool Extensibility](https://www.myaiexp.com/en/blog/claude-code-extensibility)
- [OpenClaw Skills Ecosystem and Practical Production Picks](https://glukhov.org/ai-systems/openclaw/skills/)
- [claw-code vs Claude Code: What's Actually Different?](https://wavespeed.ai/blog/posts/claw-code-vs-claude-code/)
- [Open-Source Claude Code Alternative in Rust](https://computingforgeeks.com/claw-code-open-source-claude-code-alternative/)

---

**Research Completed**: 2026-05-11
**Agent**: Explore (Open-Claw)
**Status**: ✅ Complete
