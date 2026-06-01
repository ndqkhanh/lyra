# Phase 1: Feature Parity — Research Checkpoint

**Status**: Research in progress  
**Date**: 2026-05-31  
**Scope**: §4.6 Tools, §4.7 Plugins, §4.8 MCP, §4.9 Commands, §4.10 Hooks, §4.11 Sessions, §4.12 Permissions

---

## Research Strategy

### Phase 1 Goal
Build a **feature-parity matrix** comparing Lyra's current capabilities against:
- Claude Code (official docs)
- Comparable harnesses (Hermes, Kilo, OpenClaw, DeerFlow, etc.)
- Awesome lists (harness engineering, MCP servers, context engineering)

Then produce **7 concrete plans** (one per workstream) specifying what to port, enhance, or skip.

### Sources to Research

#### §3.1 Claude Code Official Docs (Primary)
- ✅ Skills (already covered in Phase 0 context, will deep-dive for §4.4)
- ⏳ Plugins reference
- ⏳ Tools reference
- ⏳ Goals/automation
- ⏳ Hooks guide & reference
- ⏳ MCP integration
- ⏳ Interactive mode
- ⏳ Commands
- ⏳ Checkpointing/sessions
- ⏳ Permissions
- ⏳ Agent teams (swarm) — defer to Phase 4
- ⏳ Channels — defer to Phase 4
- ⏳ Env vars/credentials

#### §3.2 Comparable Harnesses
- ⏳ Hermes Agent
- ⏳ Kilo Code (all-in-one platform)
- ⏳ Kilo Marketplace (skills/MCP/modes)
- ⏳ OpenClaw (BYOK router, SOUL.md personality)
- ⏳ DeerFlow 2.0 (ByteDance SuperAgent)
- ⏳ OpenCode (75+ providers)
- ⏳ Pi (sub-1000-token prompt, lazy-loading skills)
- ⏳ Goose (MCP-native, Recipes)
- ⏳ Cline (Plan/Act, parallel agents)
- ⏳ Aider (git-native, repomap)
- ⏳ Crush (terminal agent)

#### §3.3 Awesome Lists (Clone & Expand)
- ⏳ awesome-harness-engineering
- ⏳ awesome-mcp-servers
- ⏳ awesome-context-engineering (2 repos)

---

## Research Log

### Successfully Researched
(Will be populated as research progresses)

### Failed / Unreachable
(Will be logged here)

### Deferred
(Will be noted here)

---

## Next Steps
1. Fetch Claude Code docs (plugins, tools, hooks, MCP, commands, sessions, permissions)
2. Clone comparable harnesses
3. Clone awesome lists
4. Build feature-parity matrix
5. Produce 7 workstream plans
