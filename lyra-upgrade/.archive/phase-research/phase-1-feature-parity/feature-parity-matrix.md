# Feature Parity Matrix — Lyra vs Leading Harnesses

**Purpose**: Compare Lyra's current capabilities against Claude Code, Hermes, Kilo, DeerFlow, and others to identify gaps and opportunities.

**Legend**:
- ✅ Full support
- 🟡 Partial support
- ❌ Missing
- 🔵 Lyra-unique (not in others)

---

## Core Tools (§4.6)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| **File Operations** |
| Read | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| Write | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| Edit (diff-based) | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| Glob (gitignore-aware) | 🟡 | ✅ | ✅ | ✅ | ✅ | P0 |
| Grep (semantic search) | 🟡 | ✅ | ✅ | ✅ | ✅ | P0 |
| NotebookEdit (Jupyter) | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| **Execution** |
| Bash | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| PowerShell | ❌ | ✅ | ❌ | ✅ | ❌ | P2 |
| Monitor (watch logs) | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Background execution | 🟡 | ✅ | ✅ | ✅ | ✅ | P0 |
| **Code Intelligence** |
| LSP integration | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Auto type-check | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Go-to-definition | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| Find references | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| **Web** |
| WebFetch (extraction) | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| WebSearch | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| **Agent Orchestration** |
| Spawn subagents | 🟡 | ✅ | ✅ | ✅ | ✅ | P0 |
| SendMessage | ❌ | ✅ | ❌ | ❌ | ✅ | P1 |
| TeamCreate/Delete | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| **Task Management** |
| TaskCreate/Update | ❌ | ✅ | ❌ | ✅ | ✅ | P1 |
| TaskList/Get | ❌ | ✅ | ❌ | ✅ | ✅ | P1 |
| **Session Control** |
| EnterPlanMode | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| EnterWorktree | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **Scheduling** |
| CronCreate/Delete | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| ScheduleWakeup | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **User Interaction** |
| AskUserQuestion | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| PushNotification | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |

---

## Plugin System (§4.7)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| Plugin discovery | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Hot-reload | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| Persistent data dir | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| Marketplace integration | ❌ | ✅ | ❌ | ✅ | ❌ | P2 |
| Multi-component (skills+hooks+MCP) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Managed plugins (enterprise) | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |

---

## MCP Integration (§4.8)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| **Transports** |
| Stdio | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| HTTP | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| SSE | ❌ | 🟡 (deprecated) | ❌ | ❌ | ❌ | P2 |
| WebSocket | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **Features** |
| Tool search (lazy load) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Resource mentions (@mcp:) | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Prompts as commands | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| OAuth 2.0 | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| Header-based auth | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| Dynamic updates (list_changed) | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Auto-reconnect | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| **Scopes** |
| Local (project-only) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Project (.mcp.json) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| User (global) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Plugin-provided | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |

---

## Commands & Interactive Mode (§4.9)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| Slash commands (/) | 🟡 | ✅ | ✅ | ✅ | ✅ | P0 |
| Shell mode (!) | ❌ | ✅ | ✅ | ✅ | ❌ | P1 |
| File mentions (@) | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| Voice input (Space) | ❌ | ✅ | ❌ | ❌ | ❌ | P0 (Phase 0) |
| Keyboard shortcuts | 🟡 | ✅ | ✅ | ✅ | ✅ | P1 |
| Vim mode | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| Command history (Ctrl+R) | ❌ | ✅ | ✅ | ✅ | ✅ | P1 |
| Transcript viewer (Ctrl+O) | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Image paste (Ctrl+V) | ❌ | ✅ | ❌ | ✅ | ❌ | P2 |

---

## Hooks & Automation (§4.10)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| **Hook Types** |
| PreToolUse | ❌ | ✅ | ❌ | ❌ | ❌ | P0 |
| PostToolUse | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Stop | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| SessionStart | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| UserPromptSubmit | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **Execution Modes** |
| Command hooks (shell) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Prompt-based hooks (LLM) | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Agent-based hooks | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| Async hooks | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **Features** |
| Matcher patterns (glob) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| JSON I/O | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Permission integration | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Managed hooks (enterprise) | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |

---

## Sessions & Checkpointing (§4.11)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| Automatic checkpoints | ❌ | ✅ | ❌ | ✅ | ✅ | P0 |
| Rewind menu | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Restore code + conversation | ❌ | ✅ | ❌ | ✅ | ✅ | P0 |
| Restore conversation only | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Restore code only | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Summarize from/to checkpoint | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| Session forking | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| /resume | ❌ | ✅ | ❌ | ✅ | ✅ | P0 |
| /clear | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| /recap | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |

---

## Permissions & Credentials (§4.12)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| **Permission System** |
| 3-tier (read/command/edit) | 🟡 | ✅ | ✅ | ✅ | ✅ | P0 |
| Rule engine (glob patterns) | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Wildcard matching | ❌ | ✅ | ❌ | ✅ | ❌ | P0 |
| Domain restrictions | ❌ | ✅ | ❌ | ❌ | ❌ | P1 |
| **Permission Modes** |
| default | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| acceptEdits | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| plan (read-only) | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| auto (with safety checks) | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| bypass (dangerous) | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **Credential Management** |
| Environment variables | ✅ | ✅ | ✅ | ✅ | ✅ | P0 |
| System keychain | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| OAuth token refresh | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| Encrypted file storage | ❌ | ✅ | ❌ | ✅ | ❌ | P1 |
| **Enterprise** |
| Managed settings | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| MDM/OS policies | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |

---

## UI/UX (§4.1)

| Feature | Lyra | Claude Code | Hermes | Kilo | DeerFlow | Priority |
|---------|------|-------------|--------|------|----------|----------|
| **Themes** |
| Multiple color themes | 🟡 | ✅ | ✅ | ✅ | ✅ | P1 |
| Custom themes | ❌ | ✅ | ✅ | ✅ | ❌ | P2 |
| **Keybindings** |
| Customizable shortcuts | 🟡 | ✅ | ✅ | ✅ | ✅ | P1 |
| Chord bindings | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |
| **Display** |
| Statusline | 🟡 | ✅ | ✅ | ✅ | ✅ | P1 |
| Fullscreen mode | ❌ | ✅ | ✅ | ✅ | ❌ | P2 |
| Output styles | 🟡 | ✅ | ✅ | ✅ | ✅ | P1 |
| Fast mode toggle | ❌ | ✅ | ❌ | ❌ | ❌ | P2 |

---

## Summary

### Lyra's Current State
- **Strong**: Basic file operations, Bash execution, multi-provider LLM support
- **Weak**: LSP, MCP, hooks, sessions, permissions, UI polish
- **Missing**: Plugin system, advanced tools (Monitor, WebFetch), enterprise features

### Priority Gaps (P0 - Must Fix)
1. **LSP integration** — Code intelligence is table stakes
2. **MCP stdio + HTTP** — Tool ecosystem access
3. **Hooks (Pre/Post/Stop)** — Automation foundation
4. **Permission system** — Security + UX
5. **Session checkpointing** — Undo/resume capability
6. **Plugin discovery** — Extensibility
7. **Tool search** — Scale to 100+ MCP servers
8. **Background execution** — Long-running tasks

### High-Value Differentiators (P1)
1. **Monitor tool** — Watch logs/files, react mid-conversation
2. **OAuth 2.0 for MCP** — Cloud connector access
3. **Rewind menu** — Best-in-class session management
4. **NotebookEdit** — Jupyter support
5. **WebFetch/WebSearch** — Research capabilities

### Lyra-Unique Opportunities (🔵)
1. **Voice Mode** (Phase 0) — First multi-agent harness with full voice
2. **Multi-provider abstraction** — Works across Claude/DeepSeek/Qwen/GPT/open-weights
3. **Breakthrough memory** (Phase 2) — Multi-layer cross-session recall
4. **Intelligent routing** (Phase 3) — Cost-optimized model selection
5. **Self-improving skills** (Phase 3) — Skills that learn from experience

---

## Next Steps

1. ✅ Complete this matrix
2. ⏳ Produce 7 workstream plans (§4.6–§4.12)
3. ⏳ Add UI/UX plan (§4.1)
4. ⏳ Wait for Phase 2-5 agents to complete
5. ⏳ Synthesize final deliverables

---

**Last Updated**: 2026-05-31
