# Automate Actions with Hooks (code.claude.com/docs/en/hooks-guide)

Source: https://code.claude.com/docs/en/hooks-guide
Author/Org: Anthropic (via code.claude.com developer documentation)
Date: Not explicitly dated; references v2.1.85+ feature gate, suggesting active/current docs

---

## Key Technical Claims

1. **Hooks provide deterministic control** over agent behavior, ensuring certain actions always happen rather than relying on the LLM to choose to run them. This is the core value proposition over skills or prompt instructions.

2. **Five hook types** are available, each filling a different niche: `command` (shell scripts), `http` (POST to URL), `mcp_tool` (call MCP server tool), `prompt` (single-turn LLM evaluation with Haiku), and `agent` (multi-turn subagent verification, experimental).

3. **30+ lifecycle events** from `SessionStart` through `SessionEnd` cover the full agent lifecycle: session lifecycle, tool execution, permission handling, compaction, file monitoring, configuration changes, subagent spawn/stop, MCP elicitation, and more.

4. **Matchers filter by event-specific fields** (tool name, session source, notification type, agent type, etc.), not just regex on arbitrary data. Each event type defines what its matcher operates on, keeping the system predictable.

5. **The `if` field** (v2.1.85+) extends matcher capability to filter by tool name AND arguments simultaneously, using the same permission rule syntax. This avoids spawning a hook process for irrelevant tool calls.

6. **Parallel execution with most-restrictive-wins semantics**: multiple hooks on the same event run in parallel; for `PreToolUse`, `deny` overrides `ask` overrides `allow`. Hooks can tighten restrictions but never loosen what permission rules allow.

7. **Structured JSON output** (versus bare exit codes) provides fine-grained control: `allow`/`deny`/`ask` for permission decisions, `additionalContext` for context injection, `updatedInput` for rewriting tool arguments, and `setMode` for changing permission mode mid-session.

8. **Six configuration scopes**: global (`~/.claude/`), project (`.claude/`), local (`.claude/settings.local.json`), managed (org policy), plugin-bundled, and skill/agent-frontmatter. Managed settings hooks cannot be disabled by the user.

9. **Hooks fire before permission checks**, meaning `PreToolUse` with `permissionDecision: "deny"` blocks even `bypassPermissions` mode. This enforces policy at the harness level that users cannot escape by changing modes.

10. **Security boundary**: hooks returning `"allow"` do NOT override deny rules from settings (including managed settings). Deny deny rules always take precedence over hook approvals.

---

## Architecture/Mechanism Details

### Hook Lifecycle

Hook events fire at specific lifecycle points. The key categories:

- **Session lifecycle**: `SessionStart`, `SessionEnd`, `Setup` (init-only/maintenance), `PreCompact`, `PostCompact`, `Stop`, `StopFailure`
- **Tool execution**: `PreToolUse` (before, can block), `PostToolUse` (after success), `PostToolUseFailure` (after failure), `PostToolBatch` (after batch)
- **User interaction**: `UserPromptSubmit`, `UserPromptExpansion`, `Notification`, `MessageDisplay`
- **Permissions**: `PermissionRequest`, `PermissionDenied`
- **Agent lifecycle**: `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`
- **Configuration**: `ConfigChange`, `InstructionsLoaded`
- **Environment**: `CwdChanged`, `FileChanged`
- **Worktree**: `WorktreeCreate`, `WorktreeRemove`
- **MCP Elicitation**: `Elicitation`, `ElicitationResult`

### Hook Input/Output Protocol

- Input: Event-specific JSON on stdin (common fields: `session_id`, `cwd`, `hook_event_name`; event-specific fields: `tool_name`, `tool_input`, `prompt`, etc.)
- Output via exit codes: 0 = proceed (no objection, normal permission flow applies), 2 = block (with stderr as feedback), other = error
- Output via structured JSON on stdout for fine-grained control:
  - `PreToolUse`: `permissionDecision` (allow/deny/ask), `permissionDecisionReason`, `updatedInput` (rewrite args), `additionalContext`
  - `PermissionRequest`: `decision.behavior` (allow/deny), `updatedPermissions` (setMode)
  - `Stop`/`PostToolUse`: top-level `decision: "block"` with `reason`
  - `UserPromptSubmit`: `additionalContext` (inject text)

### Matcher System

Each event type defines what its `matcher` field filters on:
- Tool events: tool name (`Bash`, `Edit|Write`, `mcp__.*`)
- SessionStart: session source (`startup`, `resume`, `clear`, `compact`)
- Notification: notification type (`permission_prompt`, `idle_prompt`, etc.)
- ConfigChange: config type (`user_settings`, `project_settings`, etc.)
- SessionEnd: exit reason (`clear`, `resume`, `logout`, etc.)
- Some events (UserPromptSubmit, Stop, CwdChanged) have no matcher support

### Hook Types

1. **command** (`"type": "command"`): Runs shell script. Default 10min timeout. Supports shell form and exec form (with `"args": []` to bypass shell quoting).
2. **http** (`"type": "http"`): POSTs event JSON to URL. Supports `headers` with env var interpolation via `allowedEnvVars`.
3. **mcp_tool** (`"type": "mcp_tool"`): Calls a tool on an already-connected MCP server.
4. **prompt** (`"type": "prompt"`): Single-turn LLM call (Haiku default, configurable `model`). Returns `{"ok": true/false, "reason": "..."}`. 30s timeout.
5. **agent** (`"type": "agent"`): Experimental. Spawns subagent with tool access for multi-turn verification. Same `ok`/`reason` format. 60s timeout, up to 50 tool-use turns.

### Hook Resolution Rules

- Multiple hooks on same event run in parallel
- Identical hook commands are deduplicated
- For PreToolUse permission decisions: most restrictive wins (deny > ask > allow)
- `additionalContext` from all hooks is merged and passed to Claude
- Hook approvals cannot override deny rules from settings/managed policies

---

## Numbers & Benchmarks

| Feature | Number |
|---------|--------|
| Lifecycle events | 30+ |
| Hook types | 5 |
| Configuration scopes | 6 |
| Command/http/mcp_tool timeout | 10 minutes (default) |
| UserPromptSubmit hook timeout | 30 seconds |
| MessageDisplay hook timeout | 10 seconds |
| Prompt hook timeout | 30 seconds |
| Agent hook timeout | 60 seconds (default) |
| Agent hook max tool-use turns | 50 |
| Stop hook consecutive block cap | 8 (before override) |
| `if` field min version | v2.1.85 |
| Hook deduplication | Identical commands automatically deduped |
| Hook output modes | 3 (exit code, stdout JSON, stderr) |

---

## Transfer to Lyra

### One Idea: Lifecycle Hooks as Lyra's Plugin Extension Backbone

Claude Code's hook system demonstrates a clean, deterministic, composable pattern for extending agent behavior without modifying core code. Lyra currently lacks a formal plugin system -- behaviors are mostly hard-wired or handled via prompt injection in skills. Adopting a lifecycle-hook architecture would give Lyra:

1. **Deterministic guarantees**: Plugins fire at well-defined lifecycle points regardless of LLM whim, ensuring compliance/audit/safety rules always run.
2. **Matcher-based routing**: Granular filtering reduces unnecessary hook invocations, keeping overhead low.
3. **Composability**: Multiple plugins can react to the same event with predictable resolution semantics.
4. **Configurable scope**: Project vs global vs org-level hooks (maps directly to Lyra's multi-project use case).
5. **Multi-modal extension**: shell scripts for deterministic tasks, prompt/agent hooks for judgment-based decision making.

### Workstream Route: Section 4.5 -- Plugin Architecture / Lifecycle Management

This maps most naturally to the **Plugin System** workstream (§4.5 in the Lyra upgrade plan). The hook system is not just a feature -- it is the architectural backbone for the entire plugin/extensibility model. The specific design patterns to adopt:

- Define a `LyraHooks` event registry with events specific to Lyra's domain (e.g., `before_route`, `after_tool_exec`, `session_start`, `memory_access`, `safety_check`)
- Implement matcher-based filtering using Lyra's existing tool/router naming conventions
- Support `command`, `http`, `prompt`, and `agent` hook types for different plugin use cases
- Enforce most-restrictive-wins semantics for safety-critical hooks (content filtering, permission gates)
- Use the same stdin/stdout protocol pattern for cross-process plugin communication

**Key caveat from source**: "Hooks can tighten restrictions but not loosen them past what permission rules allow" -- Lyra should adopt the same safety property: plugin hooks can add restrictions but never override core safety policies.
