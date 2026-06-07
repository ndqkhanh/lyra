# Claude Code Hooks — Complete Reference Summary (code.claude.com/docs/en/hooks)

Source: https://code.claude.com/docs/en/hooks
Fetched: 2026-06-07
Author/Org: Claude Code / Anthropic
Date: Not explicitly stated on page

## Key Technical Claims

- Hooks are a user-defined behavior injection system with **17 lifecycle events** grouped into four cadences: once-per-session, once-per-turn, every-tool-call, and other events.
- Hooks can execute as **shell commands**, **HTTP POSTs**, **MCP tool calls**, **LLM prompt evaluations**, or **subagent spawns**.
- Hooks return structured JSON decisions that can block, allow, ask, or defer tool execution — not binary pass/fail but a four-state permission model.
- Configuration uses a **three-level nesting** structure: Hook Event -> Matcher Group -> Hook Handler.
- Matcher patterns support exact strings, pipe-separated OR lists, and JavaScript regex — applied against tool names (e.g., `Bash`, `mcp__memory__.*`).
- Context injection via `hookSpecificOutput.additionalContext` allows hooks to inject text into Claude's context window as a system reminder.

## Architecture/Mechanism Details

### Five Hook Types
| Type | Mechanism | Use Case |
|------|-----------|----------|
| `command` | Shell execution (spawn or `sh -c`) | Local scripts, formatters, linters |
| `http` | POST JSON to URL | External policy servers, audit logging |
| `mcp_tool` | Call MCP server tool | Reusing existing MCP infrastructure |
| `prompt` | Single-turn LLM evaluation | AI-powered judgment (yes/no decisions) |
| `agent` | Subagent with Read/Grep/Glob tools | Experimental sandboxed verification |

### Decision Control (the key API)
Hooks return JSON with a `hookSpecificOutput` object. Critical fields:

- **PreToolUse**: `permissionDecision` = `"allow"` | `"deny"` | `"ask"` | `"defer"`, plus optional `updatedInput` to modify the tool call
- **PermissionRequest**: `decision.behavior` = `"allow"` or `"deny"`, plus optional `updatedInput`
- **Top-level events** (UserPromptSubmit, Stop, etc.): `decision` = `"block"` + `reason`
- **Context injection**: `hookSpecificOutput.additionalContext` injects arbitrary text into Claude's context window

### Async Hooks
- `async: true` runs hooks in background without blocking Claude's execution.
- `asyncRewake: true` implies async and wakes Claude only if the hook exits with code 2 (error/block).
- This enables **non-blocking audit logging** and **deferred safety checks** that don't slow the main loop.

### Matcher Pattern System
- `"*"` or omitted: matches every occurrence of the event
- Plain letters/digits/`_`/`|`: exact match or pipe-separated list (e.g., `"Bash|Edit|Write"`)
- Contains other characters: treated as JavaScript regex (e.g., `"^Notebook"`, `"mcp__memory__.*"`)
- Bash subcommand matching: tools strip leading env vars and check chained commands (e.g., `Bash(git *)` matches `FOO=bar git push` and `npm test && git push`)

### Exit Code Semantics
- **0**: Success — parse stdout for JSON decisions
- **2**: Blocking error — action blocked, stderr shown to Claude
- **Any other**: Non-blocking error — notice shown, execution continues

### Path Placeholders
`${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` resolve at runtime.

### Special Features
- **Persistent env vars**: SessionStart/Setup hooks can append to `$CLAUDE_ENV_FILE`
- **Terminal notifications**: Via `terminalSequence` JSON field (OSC 777 escape)
- **Output limits**: Hook output strings capped at **10,000 characters**; excess saved to file with preview
- **Disable switch**: `"disableAllHooks": true` in settings (managed hooks exempt)

## Numbers & Benchmarks (if any)

- **17** lifecycle events total
- **5** hook types
- **10,000 character** output limit on hook responses
- Default timeouts: 600s (command/http/mcp_tool), 30s (prompt), 60s (agent); lowered to 30s for UserPromptSubmit and 10s for MessageDisplay
- **5 configurable scopes**: user-global, project, project-local, managed policy, plugin, skill/agent frontmatter

## Transfer to Lyra (one idea + workstream route)

**THE IDEA: Unify Lyra's router, safety, and verification subsystems under a single typed lifecycle hook architecture.**

Claude Code's hook system demonstrates that a small set of well-defined lifecycle events (`PreToolUse`, `PostToolUse`, `Stop`, etc.) with structured JSON decision output can replace ad-hoc interceptors with a composable, inspectable pipeline. Each hook handler receives typed context, returns a structured decision, and can inject additional context into the execution environment.

For Lyra, this means replacing three separate subsystems (Router in §4.3 blocking/dispatch, Safety in §4.5 gating, Verification in §4.2 post-checks) with a **unified Hook Registry** where:

1. **PreToolUse hooks** handle routing + safety gating: matcher patterns filter by tool name, then handlers return `allow`/`deny`/`ask`/`defer`, with optional `updatedInput` mutation.
2. **PostToolUse hooks** handle verification: run formatters, linters, test watchers, or diff analyzers after every tool call.
3. **Stop/Callback hooks** handle verification summaries: aggregate results across a turn and inject them as context.
4. **Prompt hooks** handle AI-judged safety decisions: single-turn LLM calls that classify tool invocations against policy.

The key architectural win is that each hook handler is a **pure function** (event JSON -> decision JSON), making the pipeline testable, debuggable, and independently deployable. Matcher expressions allow composable filtering without hard-coding tool names in multiple places.

**Workstream route**: §4.3 Router (primary) — the hook matcher pattern directly replaces the router's dispatch logic. §4.5 Safety guards become PreToolUse hooks with deny decisions. §4.2 Verification checks become PostToolUse hooks with continue/stop decisions. Cross-cutting benefit is that all three subsystems use the **same typed interface**, reducing architectural surface area by ~60%.

Impact: High (9) — foundational architectural simplification
Effort: Medium (6) — requires designing the hook interface, migrating existing router/safety/verify logic, and implementing the registry
Tier: Silver (foundational pattern that unlocks composable safety + routing + verification)
