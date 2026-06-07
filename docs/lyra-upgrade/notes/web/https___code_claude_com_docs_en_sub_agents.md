# Create Custom Subagents (code.claude.com/docs -- Anthropic/Claude Code Documentation)

**URL**: https://code.claude.com/docs/en/sub-agents
**Source**: Anthropic -- official Claude Code product documentation
**Date**: Undated (current as of Claude Code v2.1.153+)

---

## Key Technical Claims

1. **Isolated context is the primary value proposition.** Subagents run in their own context window with a custom system prompt, specific tool access, and independent permissions. The parent conversation receives only the summary, keeping exploration/logs/search results out of the main context.

2. **Five scope layers with defined priority.** Subagent definitions resolve in this order: managed settings (org-wide) > CLI `--agents` flag (session-only) > `.claude/agents/` (project) > `~/.claude/agents/` (user) > plugin `agents/` directory. Plugins cannot define `hooks`, `mcpServers`, or `permissionMode`.

3. **Subagents cannot nest.** Subagents cannot spawn other subagents. For nested delegation, the parent conversation must chain them sequentially or use Skills that run in the main context.

4. **Forks inherit vs named subagents start fresh.** A fork copies the full conversation history, system prompt, tools, and model from the parent. A named subagent starts from its definition file with a fresh context. Forks share the parent's prompt cache, making them cheaper for context-heavy tasks.

5. **Background subagents auto-deny permission prompts.** Running concurrently with the main conversation, they use already-granted permissions. Any tool call that would trigger a prompt is auto-denied; the subagent continues. This is explicit design, not a limitation.

6. **Persistent memory with auto-curated MEMORY.md.** Three scopes: `user` (~/.claude/agent-memory/), `project` (.claude/agent-memory/), `local` (.claude/agent-memory-local/). The subagent's system prompt includes the first 200 lines or 25KB of MEMORY.md, with instructions to curate it if it exceeds that limit. Read/Write/Edit tools are auto-enabled for memory maintenance.

---

## Architecture/Mechanism Details

### Subagent Definition Format
Markdown file with YAML frontmatter + body (system prompt). The body replaces the full Claude Code system prompt -- subagents receive only their own prompt plus basic environment details (working directory), not the parent's full system prompt.

### 20+ Supported Frontmatter Fields
`name` (required), `description` (required), `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`.

### Built-in Subagents
| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| Explore | Haiku | Read-only | Codebase search/analysis |
| Plan | Inherits parent | Read-only | Codebase research during plan mode |
| General-purpose | Inherits parent | All tools | Complex multi-step tasks |
| statusline-setup | Sonnet | -- | /statusline configuration |
| claude-code-guide | Haiku | -- | Questions about Claude Code features |

### Tool Restriction Mechanics
- `tools` field: allowlist (only listed tools available)
- `disallowedTools` field: denylist (removes from inherited set)
- If both set: `disallowedTools` applied first, then `tools` resolves against remaining pool. A tool in both is removed.
- `Agent(agent_type_name)` syntax limits which subagents a main-thread agent can spawn.

### Context Loading at Startup (non-fork)
1. System prompt (agent's own prompt + env details)
2. Task message (Claude's delegation prompt)
3. CLAUDE.md and memory (all levels of memory hierarchy -- skipped by Explore and Plan)
4. Git status snapshot (skipped by Explore and Plan)
5. Preloaded skills (full content of any skill in `skills` field)

### Hook Integration
- Frontmatter-hooks: `PreToolUse`, `PostToolUse`, `Stop` (converted to `SubagentStop`) -- scoped to that subagent.
- Settings-hooks: `SubagentStart`, `SubagentStop` -- project-level lifecycle hooks in `settings.json`.
- Hook scripts receive tool input as JSON via stdin; exit code 2 blocks the operation.

### MCP Server Scoping
Inline MCP server definitions in `mcpServers` field connect at subagent start and disconnect on finish. The parent conversation never sees those tools -- keeps context clean.

### Auto-Compaction
Triggers at ~95% capacity by default. Overridable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. Compaction events logged in subagent transcript files with `preTokens` value.

### Fork (Conversation Inheritance)
- Requires v2.1.117+ (default since v2.1.161).
- Enabled via `CLAUDE_CODE_FORK_SUBAGENT=1` or `/fork` command.
- Fork replaces the general-purpose subagent's spawn behavior.
- Forks inherit: full conversation history, same system prompt + tools + model, shared prompt cache.
- Forks can receive `isolation: worktree` for isolated file edits.
- Fork panel: `↑/↓` to navigate rows, `Enter` to open transcript and send follow-ups, `x` to dismiss/stop.

---

## Numbers & Benchmarks

- **Memory MEMORY.md limit**: First 200 lines or 25KB (whichever comes first) injected into subagent system prompt.
- **Auto-compaction threshold**: ~95% context capacity by default.
- **Transcript cleanup**: Default 30 days (`cleanupPeriodDays` setting).
- **Model resolution priority**:
  1. `CLAUDE_CODE_SUBAGENT_MODEL` env var
  2. Per-invocation `model` parameter
  3. Subagent definition's `model` frontmatter
  4. Main conversation's model
- **Plugin subfolder scoping**: `agents/review/security.md` in a plugin registers as `my-plugin:review:security`.

---

## Transfer to Lyra

### One Idea: Forked-Context Agent Handoff (Warm-Start Subagents)

The most transferable concept is the **fork mechanism** -- allowing a subagent to inherit the parent conversation's full history instead of starting cold. In Lyra's current architecture, every spawned agent starts from scratch: it receives a task description but has no awareness of the conversation context that produced that task. This forces the orchestrator to re-explain situational context in every task prompt, consuming token budget on context reconstruction.

Lyra could implement a **`warm_start` flag** on agent spawn requests. When `true`, the spawned agent inherits a compressed digest of the parent conversation (last N turns or a vector-summarized context snapshot), similar to Claude Code's fork behavior. This would reduce:
- Token waste on re-explaining task context
- Orchestrator prompt engineering burden
- Latency from context re-acquisition

The mechanism already exists in the ecosystem: Claude Code's `/fork` and `CLAUDE_CODE_FORK_SUBAGENT=1` implement this at the platform level. Lyra would need to expose this as a spawn-time configuration parameter on its Agent tool abstraction.

### Workstream Route

**§4.3 -- Context Architecture** (Primary)
- Add a `warm_start: bool | { max_turns: number }` field to Lyra's agent spawn schema.
- When warm_start is true, the spawned agent's initial context includes a compressed summary of the parent conversation's last N turns, rather than only the task message.
- The orchestrator can still provide task-specific instructions that take priority over inherited context.
- This does not replace the cold-start default; it adds an option for sub-tasks that need situational awareness (e.g., "continue debugging this specific function" where the error context is already in the conversation).

**§4.4 -- Agent Router** (Secondary)
- The router could use a heuristic: if the parent has N>5 turns of context related to the target domain, suggest warm_start. If the task is fully self-contained (e.g., "run tests on module X"), keep cold-start default.
