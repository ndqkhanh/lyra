# Claude Code Official Documentation -- Deep-Read Findings Report

> **Research Date:** 2026-06-03  
> **Scope:** Agent View, Worktrees, Skills, Dynamic Workflows, Subagents, Effort & Model Config,  
>   Agent Teams, Channels, Permissions, Tools, Hooks, Checkpointing, Plugins, Security,  
>   Sandboxing, MCP, CLI Reference, Settings, Tool Search, Agent SDK Skills  
> **Purpose:** Extract exact mechanisms for Lyra architecture ingestion

---

## 0. Agent View

**URL:** https://code.claude.com/docs/en/agent-view

### Core Mechanism (step-by-step)
1. **Invocation:** `claude agents` opens a TUI dashboard showing all background sessions
2. **Session States:** Sessions are grouped into three columns: "Needs input" (awaiting user reply), "Working" (actively running), "Completed" (done)
3. **Dispatch:** User types a prompt at the bottom to dispatch a new background agent
4. **Context isolation:** Each background session is a full Claude Code conversation -- own context window, own tool execution, own terminal
5. **File edit isolation (v2.1.143+):** By default, background agents are isolated via `worktree.bgIsolation: "worktree"`. This blocks `Edit`/`Write` in the main checkout until the agent calls `EnterWorktree`. Can be set to `"none"` to let background jobs edit the working copy directly
6. **Navigation:** Tab/arrow keys navigate sessions; Enter to focus/interact; Escape to return to agent view

### Key Technical Details
- Requires Claude Code CLI only (not VS Code extension)
- The `claude agents` command can also be invoked with `--bg` to start a background agent from the CLI without entering agent view first
- On-demand supervisor: `claude agents` accepts a prompt argument to dispatch directly
- Configurable via `disableAgentView: true` in settings (typical for managed deployments)
- Env var: `CLAUDE_CODE_DISABLE_AGENT_VIEW=1`

### Trade-offs
- Gains: Parallel task execution from one terminal, context isolation between tasks, visual state management
- Costs: Token usage scales linearly with number of parallel sessions; each session has its own context window

### Design Rationale
- Rather than multiplexing within one context (which degrades quality), each agent gets its own conversation
- File isolation via worktree prevents cross-session edit conflicts
- Visual dashboard replaces terminal multiplexer management

### Transferable Idea for Lyra
- Implement a supervisor/TUI dashboard that shows all active agents grouped by state (needs-input / working / completed)
- File edit isolation should be default for parallel agents, with an opt-out flag

### Gap vs Baseline
- Lyra has no TUI dashboard or file-isolated parallel agent view. This is a feature gap.

---

## 1. Worktrees

**URL:** https://code.claude.com/docs/en/worktrees

### Core Mechanism (step-by-step)
1. **Creation:** `claude --worktree <name>` creates a git worktree at `.claude/worktrees/<name>/` on a new branch `worktree-<name>`
2. **Auto-naming:** If name omitted, generates a random name (e.g., `bright-running-fox`)
3. **Base branch selection:**
   - Default (`"fresh"`): branches from `origin/HEAD` (remote default branch)
   - `"head"` mode (via `worktree.baseRef: "head"` setting): branches from local HEAD, preserving unpushed commits
   - PR mode: `claude --worktree "#1234"` fetches `pull/1234/head` from `origin` and creates worktree at `.claude/worktrees/pr-1234`
4. **Cleanup protocol:**
   - No changes + no untracked files + no new commits: auto-removed on exit (unless session is named, in which case it prompts)
   - Changes exist: prompts to keep or remove
   - Non-interactive (`-p` + `--worktree`): NOT auto-cleaned; manual `git worktree remove` needed
   - Sweep: Orphaned subagent/background worktrees older than `cleanupPeriodDays` (default 30) are auto-removed if clean
5. **Copying gitignored files:** `.worktreeinclude` file in project root (`.gitignore` syntax) -- only gitignored files matching patterns are copied into new worktrees
6. **Subagent worktrees:** `isolation: worktree` in subagent frontmatter gives each subagent a temp worktree, auto-removed when subagent finishes without changes
7. **Non-git VCS:** Provide `WorktreeCreate`/`WorktreeRemove` hooks to replace git worktree logic for SVN, Perforce, etc.

### Key Technical Details
- `worktree.symlinkDirectories: ["node_modules"]` -- symlink dirs from main repo to avoid duplication
- `worktree.sparsePaths: ["src/api"]` -- git sparse-checkout; only listed dirs + root files written to disk
- Must accept workspace trust first (`claude` once in directory) before `--worktree` works
- `EnterWorktree` tool: passes `path` to switch into existing worktree, or no `path` to create new one
- `ExitWorktree` tool: exits worktree session; not available to subagents with `isolation: worktree`

### Trade-offs
- Gains: true filesystem isolation for parallel sessions, branch-per-task workflow
- Costs: disk space (each worktree is a full checkout), git ref overhead, complexity for non-git VCS

### Design Rationale
- git worktrees share the `.git` directory, so no remote needed, no cloning overhead
- `--worktree` CLI flag is zero-config: generates branch, creates worktree, starts session

### Transferable Idea for Lyra
- Implement worktree isolation with the same `.worktreeinclude` pattern for config files
- Support `baseRef: "head"` vs `"fresh"` branching strategies
- Auto-cleanup with configurable TTL

### Gap vs Baseline
- Lyra has worktree support but lacks most of these mechanisms (`.worktreeinclude`, `baseRef` config, auto-cleanup protocol, subagent worktree isolation)

---

## 2. Skills

**URLs:** https://code.claude.com/docs/en/skills | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | https://code.claude.com/docs/en/agent-sdk/skills

### Core Mechanism (step-by-step)

**Architecture (Three-Level Loading):**
1. **Level 1 -- Metadata (always loaded):** YAML frontmatter `name` + `description` (~100 tokens per Skill) loaded into system prompt at session start
2. **Level 2 -- Instructions (loaded when triggered):** When Claude's task matches a Skill's description, Claude uses Bash to read `SKILL.md` from the filesystem. Only then does SKILL.md body enter context (recommended <5K tokens)
3. **Level 3+ -- Resources (loaded as needed):** Additional markdown files, scripts, reference materials. Accessed only when referenced by SKILL.md. Scripts are *executed via bash* (code never enters context -- only output consumes tokens)

**Invocation:**
1. Claude auto-invokes based on task relevance matching against `name` + `description`
2. User can invoke directly with `/skill-name` (via / autocomplete)
3. Skill can have `invoke-control` frontmatter: `"auto"` (Claude-only), `"user"` (user-only), `"any"` (both), `"off"` (banned)
4. Once invoked, Skill content is read via Bash `read` tool and loaded into Claude's context

**Frontmatter fields (Claude Code extension):**
- `invoke-control`: auto / user / any / off (controls who can trigger)
- `allowed-tools`: restrict which tools Skill can use
- `model`: pin Claude version for Skill execution
- `effort`: override effort level when Skill runs
- `shell`: `bash` or `powershell` for inline `!` commands
- `subagent`: run Skill in a subagent context instead of main conversation
- `hooks`: define hook handlers scoped to the Skill's lifetime

**Directory structure:**
```
.claude/skills/<skill-name>/
  SKILL.md           # Required: YAML frontmatter + markdown body
  reference.md       # Optional: loaded on reference
  scripts/           # Optional: executed via bash (code never in context)
```

**Skill discovery:**
- Project: `.claude/skills/` (shared via git)
- User: `~/.claude/skills/` (personal, cross-project)
- Plugin: bundled with installed plugins
- Commands merged: `.claude/commands/` (legacy) works identically to `.claude/skills/`

**Skill settings:**
- `maxSkillDescriptionChars`: cap on `description` + `when_to_use` text Claude sees each turn. Default 1536 chars
- `skillListingBudgetFraction`: fraction of context window reserved for skill listing. Default 0.01 (1%)
- `skillOverrides`: per-skill visibility override (`"on"`/`"name-only"`/`"user-invocable-only"`/`"off"`)

**In SDK:**
- Skills must be filesystem artifacts -- no programmatic API for registration
- Controlled via `skills` option on `query()`: `"all"`, list of names, or `[]` to disable
- Requires `settingSources: ["user", "project"]` for discovery
- `allowed-tools` frontmatter NOT supported in SDK -- use `allowedTools` on `query()`

### Key Technical Details
- `name`: max 64 chars, lowercase + hyphens + digits only, no XML tags, no reserved words ("anthropic", "claude")
- `description`: max 1024 chars, must be non-empty, no XML tags, third-person only
- SKILL.md body: keep under 500 lines; split into separate files beyond that
- References should be one level deep from SKILL.md (Claude may use `head -100` for deeper nesting)
- Script code never enters context -- only script output consumes tokens
- Skills are NOT ZDR-eligible (data retained per standard policy)
- Runtime constraints vary by surface: API has no network access, no runtime package install; Claude Code has full network access

### Trade-offs
- Gains: Zero-cost capability library (metadata only ~100 tokens/skill), on-demand loading, composable, shareable
- Costs: Discovery accuracy depends on description quality; cannot be used programmatically in SDK (must be filesystem artifacts); not ZDR-eligible

### Design Rationale
- Filesystem-based progressive disclosure avoids the "list all tools upfront" problem
- Script execution without loading code into context is more efficient than having Claude generate code each time
- Separate invocation control (auto/user/any/off) prevents unwanted auto-triggering

### Transferable Idea for Lyra
- Adopt the three-level loading architecture: metadata (always in context) -> instructions (loaded on trigger) -> resources/scripts (loaded on reference)
- Implement `skillListingBudgetFraction` to dynamically truncate least-used skill descriptions
- Support `invoke-control`, `allowed-tools`, `model`, `effort` frontmatter in SKILL.md
- Implement script execution from skills without loading code into context

### Gap vs Baseline
- Lyra has skills but lacks: three-level loading architecture, `skillListingBudgetFraction`, `invoke-control`, `allowed-tools` frontmatter, SDK integration, script-outside-context execution, `maxSkillDescriptionChars` budget

---

## 3. Dynamic Workflows

**URLs:** https://code.claude.com/docs/en/workflows | https://claude.com/blog/introducing-dynamic-workflows-in-claude-code | https://code.claude.com/docs/en/sub-agents

### Core Mechanism (step-by-step)
1. **Trigger:** Via explicit keyword "workflow" in prompt, or `/effort ultracode` (autonomous mode), or `/deep-research` bundled command
2. **Script generation:** Claude writes a JavaScript orchestration script that contains the loop, branching, and intermediate result storage
3. **Script structure:** Script holds the plan in code -- not in Claude's context. Claude's context only holds the final answer
4. **Runtime execution:** The workflow runtime executes the script in an isolated environment, separate from the conversation
5. **Agent fan-out:** The script spawns subagents (one per task), up to 16 concurrent agents, 1,000 total per run
6. **Result tracking:** Runtime tracks each agent's result as run progresses; intermediate results stay in script variables
7. **Completion:** When all agents finish, script returns consolidated result to conversation
8. **Resumability:** Stop a run and resume within same session -- completed agents return cached results, uncompleted run live

**Ultracode mechanism:**
- Combines `xhigh` reasoning effort + automatic workflow orchestration
- Claude decides per-task whether a workflow is warranted
- Multiple workflows can execute in sequence (understand -> change -> verify)
- Session-only; resets on new session

**Bundled workflow: `/deep-research`**
1. Fan out web searches across several angles
2. Fetch and cross-check sources
3. Agents adversarially review each other's findings
4. Cross-checked claims filtered; only surviving claims in report
5. One consolidated cited report returned

### Key Technical Details
- **Versions:** Requires Claude Code v2.1.154+; research preview
- **Availability:** Max, Team, Enterprise plans (admin-gated); API/Bedrock/Vertex/Foundry
- **Runtime constraints:**
  - No mid-run user input (only permission prompts can pause)
  - No direct filesystem or shell access from workflow script itself (agents do file ops)
  - Max 16 concurrent agents (fewer on low-CPU machines)
  - Max 1,000 agents total per run
- **Save/reuse:** Press `s` in `/workflows` view to save script to `.claude/workflows/` (project, shared) or `~/.claude/workflows/` (user, local). Saved workflow runs as `/<name>
- **Approval gates:** First-run prompt shows phases; "Yes, and don't ask again" persists; auto mode skips after first approval
- **File persistence:** Every run writes its script to `~/.claude/projects/<session>/`
- **Agent permission mode:** Subagents always run in `acceptEdits` mode regardless of session mode; inherit tool allowlist
- **Disable:** `disableWorkflows: true` in settings, `CLAUDE_CODE_DISABLE_WORKFLOWS=1`, admin settings toggle

### Comparison Table: Subagents vs Skills vs Agent Teams vs Workflows

| Dimension | Subagents | Skills | Agent Teams | Workflows |
|---|---|---|---|---|
| What it is | Worker Claude spawns | Instructions Claude follows | Lead agent supervising peers | Script runtime executes |
| Who decides next | Claude turn-by-turn | Claude following prompt | Lead agent turn-by-turn | The script |
| Where results live | Claude's context window | Claude's context window | Shared task list | Script variables |
| Repeatable | Worker definition | Instructions | Team definition | Orchestration itself |
| Scale | Few per turn | Same as subagents | Handful of long-running peers | Dozens to hundreds |
| Interruption | Restarts turn | Restarts turn | Teammates keep running | Resumable |

### Trade-offs
- Gains: Codified repeatable orchestration; detached from context window; resumable; adversarial verification built in
- Costs: Substantially more tokens than single session; research preview instability; admin must enable

### Design Rationale
- Moving the plan into code means Claude's context holds only the final answer, not intermediate orchestration state
- Script-based orchestration is resumable because runtime persists agent results independently of LLM context

### Transferable Idea for Lyra
- Implement a workflow runtime that executes orchestration scripts (JavaScript/Python) in an isolated environment
- Support script-resident state (intermediate results in script variables, not agent context)
- Implement adversarial verification: independent agents review each other's findings before reporting
- Support resumable runs with cached completed-agent results
- Implement `/ultracode`-like mode that auto-decides when to use workflows

### Gap vs Baseline
- Lyra has no workflow runtime. Orchestration is ad-hoc and context-resident. No resumability. No adversarial verification as a built-in pattern.

---

## 4. Subagents

**URL:** https://code.claude.com/docs/en/sub-agents

### Core Mechanism (step-by-step)
1. **Definition:** Markdown file in `.claude/agents/` with YAML frontmatter specifying name, description, tools, model, etc.
2. **Delegation:** Claude detects task matches subagent description -- spawns subagent via `Agent` tool
3. **Isolation:** Each subagent runs in its own context window with its own system prompt, tool access, and permissions
4. **Execution:** Subagent works autonomously, returns single text result to parent
5. **Cleanup:** Subagent context freed; parent only sees final result (not intermediate tool calls)

### Frontmatter fields:
- `name`, `description`, `model`, `tools`, `disallowedTools` (tool filtering)
- `maxTurns`: cap on subagent turns (prevents runaway loops)
- `isolation`: `"worktree"` gives subagent its own git worktree
- `background`: `true` runs subagent in background (permission prompts shown in foreground parent)
- `subagentTimeout`: max wall-clock time
- `effort`: override effort level
- `hooks`: hook handlers scoped to subagent lifetime

### Foreground vs Background:
- **Foreground:** Parent waits; subagent permission prompts shown inline
- **Background:** Parent stays responsive; subagent auto-denies any tool call that would prompt, keeps going

### Key Technical Details
- Scope: project (`.claude/agents/`), user (`~/.claude/agents/`), plugin (bundled), CLI-defined (`claude --agent <name>`)
- Tool inheritance: no `tools` = inherit parent; `tools` only = get only those; `disallowedTools` only = exclude those; both = disallowedTools wins
- `Agent(AgentName)` permission rules: control which subagents Claude can spawn via `deny` array
- Fork mode: `claude --fork` spawns subagent that inherits full parent conversation instead of starting fresh

### Trade-offs
- Gains: Context isolation, specialist capabilities, cost control (route to Haiku)
- Costs: Subagent result is lossy (only text summary returned), no inter-subagent communication

### Design Rationale
- Context isolation is the key insight: subagent exploration stays out of main conversation context
- Single text result return mirrors functional programming (map/reduce) -- subagent does work, returns value

### Transferable Idea for Lyra
- Implement the same subagent definition format with full frontmatter (tools, model, effort, maxTurns, isolation)
- Support foreground (blocking) and background (non-blocking, auto-deny) execution modes
- Subagent-per-worktree isolation for parallel file edits
- Tool inheritance model (inherit / restrict / exclude)

### Gap vs Baseline
- Lyra has subagents but lacks: `maxTurns`, `subagentTimeout`, worktree isolation, foreground/background modes, tool inheritance model, `Agent()` permission rules

---

## 5. Effort & Model Config

**URLs:** https://code.claude.com/docs/en/model-config | https://platform.claude.com/docs/en/build-with-claude/effort | https://code.claude.com/docs/en/fast-mode

### Core Mechanism (Effort)
1. **Effort levels:** `low`, `medium`, `high` (default), `xhigh`, `max`, `ultracode` (Claude Code specific)
2. **How it works:** The `output_config.effort` parameter controls all tokens (text + tool calls + thinking). Lower effort = fewer tool calls, shorter responses, less thinking
3. **Calibration:** Effort is calibrated per model -- same level name != same token budget across models
4. **Adaptive thinking:** Opus 4.7+ uses adaptive thinking exclusively (no `budget_tokens`). Thinking depth controlled by effort
5. **`ultracode`:** Pairs `xhigh` effort + automatic workflow orchestration + mid-conversation system messages

### Effort Level Guidance:
| Level | Opus 4.7/4.8 | Sonnet 4.6 |
|---|---|---|
| `low` | Short, scoped, latency-sensitive | Simple tasks, max speed |
| `medium` | Cost-sensitive but good results | Recommended default for coding |
| `high` | Balance of quality + tokens | Complex reasoning |
| `xhigh` | Start here for coding/agentic | Falls back to `high` (not supported) |
| `max` | Frontier problems only | Diminishing returns |

### Model Aliases:
- `default`: clears override, uses recommended model for account type
- `best`: currently Opus
- `sonnet`, `opus`, `haiku`: latest versions
- `opusplan`: Opus in plan mode, Sonnet during execution
- `sonnet[1m]`, `opus[1m]`: 1M context window variants

### OpusPlan Mechanism:
1. System detects plan mode activation
2. Routes planning turns through Opus (complex reasoning)
3. On exit from plan mode, automatically switches to Sonnet for code generation
4. Plan-mode Opus phase capped at 200K context (1M upgrade doesn't apply)

### Fast Mode:
- `/fast` toggle: same Opus model, different API config prioritizing speed (up to 2.5x faster)
- Pricing: $10/$50 per MTok (Opus 4.8); $30/$150 (Opus 4.7/4.6)
- Must be on Anthropic API or subscription (not Bedrock/Vertex/Foundry)
- Rate limits separate from standard Opus; auto-fallback to standard speed on limit hit
- `fastModePerSessionOptIn: true` admin setting: prevents persistence across sessions

### Key Technical Details
- `opusplan` not covered by automatic 1M upgrade
- `max` is session-only (except via `CLAUDE_CODE_EFFORT_LEVEL` env var)
- `ultracode` is session-only, not part of `effortLevel` setting or `--effort` flag
- Frontmatter `effort` overrides session level (but not env var)
- `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` only applies to Opus 4.6/Sonnet 4.6 (legacy)
- `MAX_THINKING_TOKENS=0` disables thinking entirely
- `showThinkingSummaries: true` shows full thinking in interactive mode

### Trade-offs
- Gains: Fine-grained cost/quality control; `opusplan` gives best-of-both-worlds; fast mode for latency-sensitive work
- Costs: Effort calibration varies per model (same name != same behavior); `max` can overthink on simple tasks

### Design Rationale
- Adaptive thinking + effort replaces fixed token budgets because fixed budgets waste tokens on simple turns
- OpusPlan exploits the observation that planning benefits from deeper reasoning than code generation

### Transferable Idea for Lyra
- Implement equivalent of `opusplan` (routing: plan -> deep model, execute -> fast model)
- Implement effort levels that control all token spend (text + tool calls + thinking)
- Support frontmatter `effort` override per subagent/skill
- Implement fast-mode equivalent (alternative API config for latency)

### Gap vs Baseline
- Lyra lacks: effort level system, opusplan-style routing, fast mode, per-subagent effort override, adaptive thinking integration

---

## 6. Agent Teams

**URL:** https://code.claude.com/docs/en/agent-teams

### Core Mechanism (step-by-step)
1. **Team lead:** Main Claude Code session creates team, spawns teammates, coordinates work
2. **Teammates:** Separate Claude Code instances with own context windows, spawned as independent sessions
3. **Shared task list:** File-based task coordination (`~/.claude/tasks/<team-name>/`); tasks have states (pending, in-progress, completed) and dependencies
4. **Mailbox:** Inter-agent messaging system; teammates message each other directly by name
5. **Task claiming:** File locking prevents race conditions when multiple teammates claim same task
6. **Auto-notification:** Finished teammates auto-notify lead; messages auto-deliver to recipients
7. **Display modes:** In-process (Shift+Down to cycle), Split panes (tmux/iTerm2)

### Key Technical Details
- Experimental: requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env var
- Requires Claude Code v2.1.32+
- Team config: `~/.claude/teams/<team-name>/config.json` (auto-generated, DO NOT hand-edit)
- Task list: `~/.claude/tasks/<team-name>/`
- No nested teams; one team at a time per lead
- Lead is fixed for team lifetime (cannot promote teammate)
- Subagent definitions can be used as teammate roles (but `skills` and `mcpServers` frontmatter not applied)
- Hooks available: `TeammateIdle`, `TaskCreated`, `TaskCompleted`
- Permission modes set at spawn; can change individual modes after spawn

### Trade-offs
- Gains: Inter-agent communication (unlike subagents); shared task list; self-coordination
- Costs: Significantly more tokens than subagents; no session resumption for in-process teammates; orphaned tmux sessions possible

### Design Rationale
- File-based shared task list is simpler than a coordination server
- Lead-supervises-teammates architecture avoids distributed consensus problems
- Each teammate gets own context -> no context window size limit

### Transferable Idea for Lyra
- Implement shared task list with dependency tracking and file-locking claim mechanism
- Implement inter-agent messaging (mailbox pattern) for direct agent-to-agent communication
- Implement team lead role that coordinates work and synthesizes results
- Support both in-process (same terminal) and split-pane modes

### Gap vs Baseline
- Lyra lacks: agent teams entirely, shared task list, inter-agent messaging, team lead role

---

## 7. Channels

**URL:** https://code.claude.com/docs/en/channels-reference

### Core Mechanism (step-by-step)
1. **Channel server:** MCP server that runs on same machine as Claude Code, communicates over stdio
2. **Capability declaration:** Server must declare `claude/channel` in `capabilities.experimental`
3. **Event push:** Server calls `mcp.notification({ method: 'notifications/claude/channel', params: { content, meta } })`
4. **Context injection:** Event arrives as `<channel source="name" key="value">body</channel>` in Claude's context
5. **One-way or two-way:** One-way pushes events only; two-way adds reply tool + `instructions` telling Claude to use it
6. **Permission relay:** `claude/channel/permission` capability enables remote approval of tool use prompts

### Notification format:
```json
{
  "method": "notifications/claude/channel",
  "params": {
    "content": "build failed on main",
    "meta": { "chat_id": "123", "severity": "high" }
  }
}
```

### Permission relay flow:
1. Claude Code generates short request ID (5 lowercase letters, sans `l`)
2. Sends `notifications/claude/channel/permission_request` to server
3. Server forwards to remote (Telegram, Discord, etc.)
4. User replies "yes <id>" or "no <id>"
5. Server sends `notifications/claude/channel/permission` with `request_id` + `behavior`
6. Local dialog stays open; whichever answer arrives first wins

### Key Technical Details
- Requires Claude Code v2.1.80+; research preview
- Events not acknowledged; `await` resolves on transport write, not processing
- Events queue and process in order; concurrent streams need separate sessions
- Auto-reconnect: HTTP/SSE servers get exponential backoff (5 attempts, 1s doubling)
- Sender gating is critical for prompt injection prevention; gate on sender identity, not chat/room
- Permission relay requires v2.1.81+
- Server instructions string goes into Claude's system prompt

### Trade-offs
- Gains: External event injection into live Claude session; remote approval of tool calls
- Costs: Security surface (prompt injection vector if ungated); research preview; requires custom MCP server

### Design Rationale
- MCP as transport means any MCP server can be a channel -- no new infrastructure
- Permission relay co-opts existing tool approval flow rather than replacing it

### Transferable Idea for Lyra
- Implement channel capability for external event injection (webhooks, CI alerts, chat messages)
- Implement permission relay for remote approval of tool calls
- Implement notification queuing with in-order processing
- Support both one-way and two-way channel modes

### Gap vs Baseline
- Lyra lacks: channel system entirely, external event injection, permission relay

---

## 8. Hooks

**URL:** https://code.claude.com/docs/en/hooks

### Core Mechanism (step-by-step)
1. **Hook event model:** 25+ lifecycle events across three cadences:
   - Once per session: `SessionStart`, `SessionEnd`
   - Once per turn: `UserPromptSubmit`, `Stop`, `StopFailure`
   - Every tool call: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`
2. **Three-level configuration:** Hook Event (lifecycle point) -> Matcher Group (filter) -> Hook Handler (execution unit)
3. **Matcher patterns:**
   - `"*"`/`""`/omitted: match all
   - Only `[A-Za-z0-9_|]`: exact string or `|`-separated list
   - Any other character: JavaScript regex
4. **Handler types:** `command` (shell), `http` (POST), `mcp_tool` (MCP), `prompt` (LLM), `agent` (subagent) -- experimental
5. **Exit code protocol:**
   - 0: success, stdout parsed
   - 2: blocking error (tool blocked, permission denied, etc.)
   - Any other: non-blocking, continues
6. **JSON output fields:** `continue`, `stopReason`, `suppressOutput`, `systemMessage`, `terminalSequence`, `additionalContext`, `decision`/`permissionDecision` (event-specific)
7. **`PreToolUse` permission override:** `hookSpecificOutput.permissionDecision` = `"allow"` | `"deny"` | `"ask"` | `"defer"`

### Config locations (precedence): User (`~/.claude/settings.json`) < Project (`.claude/settings.json`) < Local (`.claude/settings.local.json`) < Managed (policy) < Plugin hooks

### Key Technical Details
- All matching hooks run **in parallel**; identical handlers **deduplicated**
- Timeout defaults: 600s (command/http/mcp), 30s (prompt), 60s (agent); UserPromptSubmit lowered to 30s
- Path placeholders: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`
- `terminalSequence` allowlist for terminal effects (OSC 0/1/2/9/99/777, BEL); CSI/OSC 8/OSC 52 rejected
- `allowManagedHooksOnly`: admin can block all non-managed hooks
- `if` field: uses permission rule syntax; only evaluated on PreToolUse/PostToolUse/PermissionRequest/PermissionDenied
- `additionalContext` >10K chars -> saved to file, Claude receives path + preview
- Hooks in skills/agents: defined in YAML frontmatter; scoped to component lifetime; cleaned up when component finishes

### Trade-offs
- Gains: Extremely flexible lifecycle integration; exit code 2 provides blocking enforcement
- Costs: Complexity (25+ events, 5 handler types, matcher system); hooks can slow down the loop; must handle async edge cases

### Design Rationale
- Command hooks support both shell and exec forms (exec avoids shell injection)
- Exit code 2 for blocking (not 1) prevents accidental blocks from failed commands
- JSON output schema decouples hook output from display

### Transferable Idea for Lyra
- Adopt the same three-level hook model (Event -> Matcher -> Handler)
- Implement the exit code protocol (0 = success, 2 = block, other = non-blocking error)
- Implement the `if` filtering system using permission-rule-style matchers
- Support hot-reloading for hook config changes

### Gap vs Baseline
- Lyra has hooks but lacks: most lifecycle events (25+ vs Lyra's subset), matcher pattern system, exit code 2 protocol, JSON output schema, exec form, HTTP/agent handler types, hook-deduplication, path placeholders

---

## 9. Tool Search

**URL:** https://code.claude.com/docs/en/agent-sdk/tool-search

### Core Mechanism (step-by-step)
1. **Deferred loading:** Tool definitions are withheld from context window at startup
2. **Summary injection:** Agent receives only tool names + server instructions (not full schemas)
3. **On-demand search:** When agent needs a capability not already loaded, it calls `ToolSearch` tool internally
4. **Result loading:** 3-5 most relevant tools loaded into context (by name/description matching)
5. **Persistence:** Discovered tools stay available for subsequent turns
6. **Compaction-aware:** On context compaction, previously discovered tools may be removed; agent searches again as needed
7. **One extra round-trip:** The search step adds one round-trip the first time a tool is discovered

### Threshold mode:
- `ENABLE_TOOL_SEARCH=auto`: load upfront if all tool defs fit within 10% of context window; defer otherwise
- `ENABLE_TOOL_SEARCH=auto:5`: 5% threshold
- `ENABLE_TOOL_SEARCH=true`: always defer
- `ENABLE_TOOL_SEARCH=false`: always load upfront

### Key Technical Details
- Max 10,000 tools in catalog
- Returns 3-5 most relevant per search
- Requires Sonnet 4+ or Opus 4+ (no Haiku)
- Disabled by default on Vertex AI and non-first-party `ANTHROPIC_BASE_URL`
- Tool descriptions/server instructions truncated at 2KB each
- `alwaysLoad: true` on MCP server config exempts it from deferral
- Tool-level `"anthropic/alwaysLoad": true` in `_meta` marks individual tools as always-loaded

### Trade-offs
- Gains: Dramatic context savings (50 tools ~10-20K tokens saved); scales to 10K tools; improves selection accuracy
- Costs: One extra round-trip on first discovery; <~10 tools is faster with upfront loading

### Design Rationale
- Selection accuracy degrades past 30-50 tools loaded at once; tool search solves this
- Names + descriptions as search index is simpler than vector embeddings

### Transferable Idea for Lyra
- Implement deferred tool loading with on-demand search by name/description
- Support threshold-based loading (`auto:N` percent of context window)
- Allow per-server `alwaysLoad` exemption for critical tools
- Implement server instructions that guide tool discovery

### Gap vs Baseline
- Lyra lacks tool search entirely. All tools are loaded upfront, consuming context.

---

## 10. Permissions

**URL:** https://code.claude.com/docs/en/permissions

### Core Mechanism
1. **Three-action system:** `allow` / `ask` / `deny` rules
2. **Evaluation order:** deny -> ask -> allow (first match wins)
3. **Tool-level rules:** `ToolName(specifier)` format
4. **Compound commands:** Claude Code parses `&&`, `||`, `;`, `|`, `&`, newlines -- checks each subcommand independently
5. **Process wrapper stripping:** Strips `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `xargs` (without flags) before matching
6. **Read-only commands:** Built-in set (`ls`, `cat`, `echo`, `pwd`, etc.) runs without prompt in every mode
7. **Symlink handling:** Allow rules check BOTH symlink path AND target; deny rules block if EITHER matches
8. **Fragile argument matching:** Glob patterns on Bash arguments have known limitations (options before URL, redirects, variables)

### Permission Mode Comparison:
| Mode | Description |
|---|---|
| `default` | Prompts on first use of each tool |
| `acceptEdits` | Auto-approves file edits + common filesystem commands in working dir |
| `plan` | Read-only: reads files, read-only shell commands, no edits |
| `auto` | Auto-approves with background safety checks (research preview) |
| `dontAsk` | Auto-denies unless pre-approved |
| `bypassPermissions` | Skips all prompts (except `/` and `~` removal circuit breaker) |

### Key Technical Details
- `disableBypassPermissionsMode: "disable"` in managed settings: prevents bypass mode organization-wide
- `additionalDirectories`: extends file access domain; different from `--add-dir` (which also loads some configuration)
- JSON output capped at 10,000 characters
- HTTP hooks: 2xx+empty=success; 2xx+JSON=processed; non-2xx=non-blocking error
- Deny rules don't evaluate symlink target for file access (only allow rules do)

### Transferable Idea for Lyra
- Implement deny-first permission evaluation with three-action (allow/ask/deny) system
- Implement compound command parsing for grouped permission matching
- Implement process wrapper stripping for permission pattern matching

### Gap vs Baseline
- Lyra has permissions but may lack: deny-first evaluation, compound command parsing, process wrapper stripping, read-only command set, symlink-aware matching

---

## 11. Sandboxing

**URL:** https://code.claude.com/docs/en/sandboxing

### Core Mechanism
1. **OS-level enforcement:** macOS (Seatbelt), Linux/WSL2 (bubblewrap + socat)
2. **Filesystem isolation:**
   - Default write: working directory + subdirs only
   - Default read: entire computer (except configured deny paths)
   - Git worktree: shared `.git` directory allowed (except `hooks/` and `config`)
3. **Network isolation:** Built-in proxy enforces domain allowlist based on hostname
4. **Two modes:** Auto-allow (sandbox boundary replaces per-command prompt) vs Regular permissions (standard flow)
5. **Escape hatch:** `dangerouslyDisableSandbox` parameter retries outside sandbox if command fails in it
6. **Dual-layer enforcement:** Permission rules + sandbox boundaries merged into final configuration

### Sandbox vs Permission Mode complementarity:
- Read/Edit deny rules merge with `sandbox.filesystem` deny/allow paths
- WebFetch allow/deny rules merge with `sandbox.network.allowedDomains`
- `Edit` allow rules double as `sandbox.filesystem.allowWrite`
- Sandbox auto-allow mode is separate from auto permission mode (works independently)

### Key Technical Details
- Linux requires `bubblewrap` + `socat` packages; optional seccomp filter (`npm install -g @anthropic-ai/sandbox-runtime`)
- Ubuntu 24.04+ needs AppArmor profile for bubblewrap user namespaces
- WSL2 supported; WSL1 not supported; native Windows not supported
- `sandbox.failIfUnavailable: true` makes missing deps a hard failure (for managed deployments)
- `allowUnsandboxedCommands: false` disables the escape hatch entirely
- `excludedCommands: ["docker *"]` for incompatible tools
- `enableWeakerNestedSandbox: true` for container-in-container scenarios
- Custom proxy via `sandbox.network.httpProxyPort`/`socksProxyPort`
- No TLS inspection by default; domain fronting possible with broad allowlists
- Settings files auto-protected: sandbox denies write to `settings.json` at all scopes

### Trade-offs
- Gains: Reduces permission prompts; OS-level enforcement harder to bypass than prompts
- Costs: Platform limitations (no native Windows); some tools incompatible; no TLS inspection

### Design Rationale
- OS-level primitives (Seatbelt, bubblewrap) are battle-tested
- Two-layer approach (permission rules + sandbox) provides defense-in-depth

### Transferable Idea for Lyra
- Implement OS-level sandboxing with Seatbelt (macOS) and bubblewrap (Linux)
- Implement proxy-based network isolation with domain allowlisting
- Support auto-allow mode where sandbox boundary replaces per-command prompts

### Gap vs Baseline
- Lyra lacks OS-level sandboxing entirely

---

## 12. Checkpointing

**URL:** https://code.claude.com/docs/en/checkpointing

### Core Mechanism (step-by-step)
1. **Automatic capture:** Every user prompt creates a checkpoint of file state before Claude's edits
2. **Checkpoint granularity:** Per-user-prompt, not per-edit
3. **Session persistence:** Checkpoints survive session boundaries (available in resumed conversations)
4. **Cleanup:** Auto-cleaned after 30 days (configurable via `cleanupPeriodDays`)
5. **Rewind menu:** `/rewind` or double-Esc shows prompt list with five actions:
   - Restore code AND conversation
   - Restore conversation only
   - Restore code only
   - Summarize from here (compress this point forward into summary)
   - Summarize up to here (compress before this point into summary)
6. **Summarization:** AI-generated compression; original messages preserved in transcript for reference

### Key Technical Details
- Bash command changes NOT tracked (only built-in file editing tools)
- External changes NOT tracked (only session's own edits)
- Not a replacement for git version control
- Summarize keeps same session; for branching use `claude --continue --fork-session`
- Restore conversation restores original prompt into input field

### Transferable Idea for Lyra
- Implement per-prompt checkpointing with git-based snapshots
- Support selective restore (code only, conversation only, or both)
- Implement conversation summarization for context window management

### Gap vs Baseline
- Lyra may have checkpointing but likely lacks: per-prompt granularity, selective restore, summarization, survival across session boundaries

---

## 13. Settings System

**URL:** https://code.claude.com/docs/en/settings

### Core Mechanism
1. **Five-tier precedence:**
   - Managed (highest) -> CLI args -> Local (`.claude/settings.local.json`) -> Project (`.claude/settings.json`) -> User (`~/.claude/settings.json`)
2. **Merge behavior for arrays:** Arrays are merged (concatenated + deduplicated) across scopes; scalars use highest-priority source
3. **Managed settings delivery:** Server-managed (Anthropic servers), MDM (plist/registry), file-based (system directory)
4. **Managed drop-in directory (`managed-settings.d/`):** JSON files sorted alphabetically, merged on top of base `managed-settings.json`
5. **Hot-reloading:** Most keys (permissions, hooks, credential helpers) reload without restart; `model` and `outputStyle` require restart

### Managed-only settings:
- `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`
- `strictPluginOnlyCustomization`, `channelsEnabled`, `blockedMarketplaces`
- `forceRemoteSettingsRefresh`, `claudeMd`, `policyHelper`
- `sandbox.filesystem.allowManagedReadPathsOnly`, `sandbox.network.allowManagedDomainsOnly`

### Key Settings:
- `effortLevel`: `low`/`medium`/`high`/`xhigh` (persists; `max`/`ultracode` session-only)
- `availableModels`: restrict model picker (audited via policy settings)
- `modelOverrides`: map Anthropic model IDs to provider-specific deployment names
- `disableWorkflows`, `disableAgentView`, `disableRemoteControl`
- `worktree.baseRef`, `worktree.symlinkDirectories`, `worktree.sparsePaths`
- `skillOverrides`: per-skill visibility without editing SKILL.md
- `maxSkillDescriptionChars`: 1536 default
- `skillListingBudgetFraction`: 0.01 (1%)
- `autoMemoryEnabled`, `autoMemoryDirectory`

### Transferable Idea for Lyra
- Implement the same five-tier settings precedence with array merge semantics
- Support managed settings via file system and admin-deployed config
- Implement hot-reloading for operational config (permissions, hooks)

### Gap vs Baseline
- Lyra's settings system may not have: five-tier precedence, array merge across scopes, managed settings, hot-reload for most keys

---

## 14. MCP (Model Context Protocol) Integration

**URL:** https://code.claude.com/docs/en/mcp

### Core Mechanism
1. **Server types:** stdio (local process), HTTP/streamable-http (remote), SSE (deprecated), WebSocket (persistent bidirectional)
2. **Connection lifecycle:** MCP configuration in `.mcp.json` (project), `.claude.json` (user/local); spawned as subprocess at session start
3. **Tool discovery:** Server advertises capabilities; Claude Code registers tool handlers
4. **Authentication:** OAuth 2.0 for HTTP servers; static headers; `headersHelper` script for custom auth; `apiKeyHelper` for API key
5. **Dynamic tool updates:** `list_changed` notifications -> Claude Code auto-refreshes capabilities without reconnect
6. **Auto-reconnect:** HTTP/SSE get exponential backoff (5 attempts, 1s doubling)
7. **Managed MCP:** `managed-mcp.json` for organization-wide server deployment; `allowedMcpServers`/`deniedMcpServers` for access control

### Installation methods:
- `claude mcp add --transport http <name> <url>` (recommended)
- `claude mcp add --transport stdio <name> -- <command> [args...]`
- `claude mcp add-json <name> '<json>'`
- `.mcp.json` file in project root
- Import from Claude Desktop: `claude mcp add-from-claude-desktop`

### Output management:
- Warning at 10K tokens per tool output
- `MAX_MCP_OUTPUT_TOKENS` env var (default 25K)
- `anthropic/maxResultSizeChars` in tool `_meta`: raises tool-specific limit (up to 500K chars)
- Per-server tool timeout: `timeout` field in `.mcp.json` (ms); hard wall-clock limit

### Transferable Idea for Lyra
- Implement MCP client for tool discovery and invocation
- Support multi-transport (stdio, HTTP, SSE, WebSocket)
- Implement OAuth 2.0 flow for remote MCP servers
- Support managed MCP for enterprise deployments

### Gap vs Baseline
- Lyra likely has MCP client but may lack: multi-transport support, OAuth flow, `list_changed` handling, auto-reconnect, `alwaysLoad`, `anthropic/maxResultSizeChars`

---

## 15. Tools Architecture

**URL:** https://code.claude.com/docs/en/tools-reference

### Core Tool Set (30+ tools):
| Tool | Permission Required | Notes |
|---|---|---|
| BASH | Yes | Separate process per command; env vars don't persist; aliases/functions from shell startup |
| Read | No | Images/PDFs/Jupyter supported; partial view on truncation; offset+limit pagination |
| Edit | Yes | Exact string replacement; read-before-edit check; uniqueness check; NO regex/fuzzy |
| Write | Yes | Full content; read-before-overwrite check for existing files |
| Agent | No | Spawns subagent; maxTurns cap; foreground/background modes |
| WebFetch | Yes | Lossy by design (small model processes HTML); 15-min cache; HTTP->HTTPS upgrade |
| WebSearch | Yes | Up to 8 backend searches per call; domain filters; search backend NOT configurable |
| Glob | No | gitignore-respecting optional; capped at 100 files; sorted by mtime |
| Grep | No | ripgrep-based; files-with-matches/content/count modes; multiline support |
| LSP | No | Code intelligence (goto def, find refs, type info); requires plugin |
| Monitor | Yes | Background process watching; react to changes mid-conversation |
| Workflow | Yes | Orchestration script runner |
| CronCreate | No | Recurring/one-shot prompts within session; session-scoped |
| Skill | Yes | Executes a skill |
| SendMessage | No | Inter-agent communication (teams) |
| ToolSearch | No | Deferred tool discovery |

### Bash Tool Details:
- Separate process per command; working dir carries over (unless `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1`)
- Env vars do NOT persist between commands
- Shell startup file (`~/.zshrc`/`.bashrc`) sourced at session start for aliases/functions
- Timeout: 2 min default; up to 10 min via `timeout` parameter
- Output length: 30K char default; capped at 150K; overflow saved to file with preview
- `run_in_background: true` for long-running processes

### Transferable Idea for Lyra
- Adopt the same tool taxonomy and permission model
- Implement read-before-edit and read-before-overwrite checks
- Implement Bash timeout and output limits with file overflow

### Gap vs Baseline
- Lyra may lack: read-before-edit enforcement, monitor tool, cron scheduling, LSP integration, tool search

---

## 16. CLI Reference

**URL:** https://code.claude.com/docs/en/cli-reference

### Key Commands:
| Command | Purpose |
|---|---|
| `claude` | Start interactive session |
| `claude -p "<prompt>"` | Non-interactive; print mode |
| `claude --model opus` | Launch with specific model |
| `claude --worktree <name>` | Launch in isolated worktree |
| `claude --bg <prompt>` | Launch background agent |
| `claude agents` | Open agent view dashboard |
| `claude mcp add ...` | Add MCP server |
| `claude mcp serve` | Run Claude Code as MCP server |
| `claude --resume` / `--continue` | Resume saved session |
| `claude --fork` | Fork current conversation |
| `claude --agent <name>` | Run as custom subagent |
| `claude --dangerously-skip-permissions` | Bypass all permissions |
| `claude update` | Update to latest version |
| `/effort` | Adjust effort level |
| `/fast` | Toggle fast mode |
| `/rewind` | Open checkpoint rewind menu |
| `/model` | Switch model |
| `/permissions` | View/edit permission rules |
| `/sandbox` | Configure sandbox |
| `/workflows` | View/manage workflow runs |
| `/mcp` | View MCP server status |
| `/hooks` | View configured hooks |
| `/skills` | View/skill overrides menu |

### Transferable Idea for Lyra
- Implement analogous CLI command structure with session management, worktree flags, and model config

### Gap vs Baseline
- Lyra likely has CLI but may lack: agent view, workflow management, sandbox config commands

---

## Synthesis: Architecture Patterns for Lyra

### 1. Progressive Disclosure (Skill Loading)
Core pattern: metadata (~100 tokens each) always in context; body loaded on trigger; resources loaded on reference. This is the zero-cost capability library model.

### 2. Deferred Tool Loading (Tool Search)
Tool definitions withheld from context; agent searches by name+description when needed; 3-5 relevant tools loaded. Scales to 10K tools.

### 3. Script-Based Orchestration (Dynamic Workflows)
Orchestration plan lives in script, not in LLM context. Runtime tracks agent results. Resumable. Up to 1,000 agents per run.

### 4. Three-Action Permission System (Deny/Ask/Allow)
Deny-first evaluation. Compound command parsing. Process wrapper stripping. Read-only command set. Symlink-aware.

### 5. OS-Level Sandboxing
Seatbelt (macOS), bubblewrap (Linux). Proxy-based network isolation. Auto-allow mode replaces per-command prompts.

### 6. Hook Lifecycle (25+ Events)
Three-level config (Event -> Matcher -> Handler). Exit code protocol (0/2/other). JSON output schema. Five handler types. Parallel execution with deduplication.

### 7. Tiered Settings Precedence
Five tiers (Managed > CLI > Local > Project > User). Array merge vs scalar override. Managed-only flags for enterprise control. Hot-reload for operational config.
