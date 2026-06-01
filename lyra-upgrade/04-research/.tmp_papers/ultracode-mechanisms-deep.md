# How Claude Code Dynamic Workflows Actually Work -- A Complete Technical Specification

> Based on exhaustive analysis of official docs: code.claude.com, platform.claude.com, and the announcement blog (May 28, 2026).
> Compiled: 2026-06-01 | Research preview (Claude Code v2.1.154+)

---

## Table of Contents

1. [What a Dynamic Workflow Is](#1-what-a-dynamic-workflow-is)
2. [The Runtime Environment](#2-the-runtime-environment)
3. [Script Format and Orchestration Model](#3-script-format-and-orchestration-model)
4. [Subagent Architecture (the Worker Primitive)](#4-subagent-architecture-the-worker-primitive)
5. [Effort Levels and Adaptive Reasoning](#5-effort-levels-and-adaptive-reasoning)
6. [The Effort API (Platform Layer)](#6-the-effort-api-platform-layer)
7. [Entry Points and Activation](#7-entry-points-and-activation)
8. [Permission Model and Approval Flow](#8-permission-model-and-approval-flow)
9. [Hard Limits and Constraints](#9-hard-limits-and-constraints)
10. [Cost Characteristics](#10-cost-characteristics)
11. [Resumability and Session Management](#11-resumability-and-session-management)
12. [Comparison Matrix](#12-comparison-matrix)
13. [Design Rationale](#13-design-rationale)
14. [What Is Explicitly NOT Supported](#14-what-is-explicitly-not-supported)
15. [Adjacent Mechanisms](#15-adjacent-mechanisms)

---

## 1. What a Dynamic Workflow Is

A **dynamic workflow** is a JavaScript script that orchestrates subagents at scale. Claude writes the script for the task you describe, and a runtime executes it in the background while your session stays responsive.

### Core data structures

There is no published JSON schema for the workflow script format. The runtime is described as:

- A **JavaScript script** (not TypeScript, not YAML)
- Executed in an **isolated environment** (sandboxed JS runtime, separate from the conversation)
- No direct filesystem or shell access from the script itself -- agents read, write, and run commands; the script only coordinates the agents

### Phase model

The runtime tracks execution in **phases**. Each phase has:
- An agent count
- A token total
- An elapsed time

Phases are visible in the `/workflows` TUI. Users can drill into any phase to see its agents and what each one found.

### Approval before execution

Before a workflow runs, the CLI shows the **planned phases** and offers these options:

1. **Yes, run it** -- start the run
2. **Yes, and don't ask again for `<name>` in `<path>`** -- start and skip future prompts for this workflow in this project
3. **View raw script** -- read the JS script before deciding
4. **No** -- cancel

`Ctrl+G` opens the script in the user's editor. `Tab` lets the user adjust the prompt before the run starts.

---

## 2. The Runtime Environment

### Execution model

- The workflow script executes in a **sandboxed JavaScript runtime**, isolated from the conversation
- No mid-run user input (only agent permission prompts can pause execution)
- The runtime tracks every agent's result as the run progresses
- Intermediate results stay in **script variables** instead of landing in Claude's context
- Coordination happens **outside the conversation** -- Claude's context holds only the final answer

### Runtime constraints

| Constraint | Value | Rationale |
|---|---|---|
| Max concurrent agents | 16 (fewer on low-CPU machines) | Bounds local resource use |
| Max total agents per run | 1,000 | Prevents runaway loops |
| Agent total limit | Hard ceiling, enforced by runtime | A run exceeding this fails |
| Mid-run user input | None | Only permission prompts can interrupt |
| Script filesystem access | None | Agents handle all I/O |
| Script shell access | None | Agents handle all commands |

### Memory model

- Each agent has its own **fresh, isolated context window**
- Context windows are **independent** -- agents do not share conversation history
- Results accumulate in script-level variables
- The **runtime tracks completed agent results**, enabling resumability
- When a run resumes, already-completed agents return **cached results**; remaining agents run live

---

## 3. Script Format and Orchestration Model

### Who holds the plan

| Aspect | Subagents/Skills | Workflows |
|---|---|---|
| Orchestrator | Claude, turn by turn | The JavaScript script |
| Plan location | Claude's context window | Script variables |
| Repeatability | Worker definition or instructions | The orchestration script itself |
| Scale | A few delegated tasks per turn | Dozens to hundreds of agents per run |

The key architectural insight: **the workflow moves the plan into code**. With subagents and skills, Claude is the orchestrator deciding turn by turn what to spawn next. A workflow script holds the loop, branching, and intermediate results itself.

### How Claude generates the script

When triggered:
1. Claude analyzes the task
2. Claude writes a JavaScript script that implements the orchestration logic
3. The user approves the plan (subject to permission mode)
4. The runtime executes the script
5. Agents spawn, do work, and report back to the script's variable space
6. The script compiles the final answer

### Built-in workflow: `/deep-research`

The only built-in workflow as of v2.1.157:

| Command | What it does |
|---|---|
| `/deep-research <question>` | Fans out web searches across several angles, fetches and cross-checks sources, votes on each claim, returns a cited report with unverified claims filtered out. Requires WebSearch tool |

The deep-research workflow implements an **adversarial verification pattern**:
- Independent agents search from different angles
- Sources are fetched and cross-checked against each other
- Claims are voted on
- Claims that don't survive cross-checking are filtered out

### Saving workflows as commands

Users can save any workflow run's script as a reusable command:
- Type `s` in the `/workflows` view
- Two save locations: `.claude/workflows/` (project, shared via git) or `~/.claude/workflows/` (personal, cross-project)
- Saved workflow becomes `/<name>` in autocomplete
- Project-level workflows override personal ones of the same name

---

## 4. Subagent Architecture (the Worker Primitive)

Workflows orchestrate **subagents**. Every subagent that a workflow spawns is a full Claude Code subagent.

### Subagent context initialization

A non-fork subagent's initial context:

| What loads | Loaded for all? |
|---|---|
| System prompt (agent's own, not full Claude Code system prompt) | Yes |
| Task message (delegation prompt from Claude) | Yes |
| CLAUDE.md and memory (all levels) | Yes, except **Explore** and **Plan** built-ins |
| Git status snapshot (from session start) | Yes, except Explore and Plan |
| Preloaded skills (from `skills` frontmatter) | Yes, if configured |
| Parent conversation history | **No** |

### Subagent frontmatter fields relevant to workflows

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Unique identifier, lowercase letters and hyphens |
| `description` | string | Yes | When Claude should delegate to this subagent |
| `tools` | string[] | No | Tools the subagent can use. Inherits all if omitted |
| `disallowedTools` | string[] | No | Tools to deny from inherited/specified list |
| `model` | string | No | sonnet, opus, haiku, full model ID, or "inherit" (default) |
| `permissionMode` | string | No | default, acceptEdits, auto, dontAsk, bypassPermissions, plan |
| `maxTurns` | integer | No | Max agentic turns before forced stop |
| `skills` | string[] | No | Skills to preload into context at startup |
| `mcpServers` | (string|object)[] | No | MCP servers scoped to this subagent |
| `hooks` | object | No | Lifecycle hooks scoped to this subagent |
| `memory` | string | No | user, project, or local persistent memory scope |
| `background` | boolean | No | Always run as background task (default: false) |
| `effort` | string | No | low, medium, high, xhigh, max (overrides session) |
| `isolation` | string | No | "worktree" for isolated git worktree |
| `color` | string | No | Display color in task list |
| `initialPrompt` | string | No | Auto-submitted as first user turn (for --agent mode) |

### Model resolution order for subagents

1. `CLAUDE_CODE_SUBAGENT_MODEL` env var (highest)
2. Per-invocation `model` parameter
3. Subagent definition's `model` frontmatter
4. Main conversation's model (fallback)

### Permission modes for subagents in workflows

Workflow subagents always run in **`acceptEdits` mode** and inherit the user's tool allowlist, regardless of the session's permission mode. File edits are auto-approved. Shell commands, web fetches, and MCP tools not in the allowlist may still prompt mid-run.

### Tools NOT available to subagents

Even when listed in `tools`, these are denied:
- `Agent` (subagents cannot spawn subagents)
- `AskUserQuestion`
- `EnterPlanMode`
- `ExitPlanMode` (unless permissionMode is `plan`)
- `ScheduleWakeup`
- `WaitForMcpServers`

### What the workflow subagent inherits from the parent

Workflow subagents inherit from the session that launched the workflow:
- The user's **tool allowlist** (from settings)
- The session's **model** (unless overridden per-stage)
- `acceptEdits` mode for file operations
- **No conversation history** (fresh context per agent)

### Auto-compaction

Subagents auto-compact at approximately 95% capacity. Can be overridden with `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`. Compact events are logged with `preTokens` counts in the subagent transcript.

Transcripts persist independently:
- Main conversation compaction does not affect subagent transcripts
- Persist within their session (can resume subagents after restart)
- Cleaned up per `cleanupPeriodDays` (default: 30)

---

## 5. Effort Levels and Adaptive Reasoning

### Available effort levels per model

| Model | Levels |
|---|---|
| Opus 4.8, Opus 4.7 | low, medium, high, xhigh, max |
| Opus 4.6, Sonnet 4.6 | low, medium, high, max |

### Default effort per model

| Model | Default |
|---|---|
| Opus 4.8 | high |
| Opus 4.7 | xhigh |
| Opus 4.6 | high |
| Sonnet 4.6 | high |

### Effort level semantics

| Level | When to use | Token impact |
|---|---|---|
| `low` | Short, scoped, latency-sensitive tasks, not intelligence-sensitive | Minimal |
| `medium` | Cost-sensitive work that can trade off some intelligence | Reduced |
| `high` | Default balance for most coding tasks | Standard |
| `xhigh` | Deeper reasoning for long-horizon agentic work | Meaningfully higher |
| `max` | Absolute maximum capability, no constraints on token spend | Highest |
| `ultracode` | NOT a model effort level -- Claude Code setting combining xhigh + workflow | xhigh + workflow |

The effort scale is **calibrated per model**, so the same level name does not represent the same underlying value across models.

### Effort is a behavioral signal, not a strict token budget

Per the platform docs: "At lower effort levels, Claude will still think on sufficiently difficult problems, but it will think less than it would at higher effort levels for the same problem."

### How effort affects tool use

Lower effort:
- Combines multiple operations into fewer tool calls
- Makes fewer tool calls total
- Proceeds directly to action without preamble
- Uses terse confirmation messages

Higher effort:
- Makes more tool calls
- Explains the plan before acting
- Provides detailed summaries
- Includes more comprehensive code comments

### Adaptive reasoning (Opus 4.7+)

Opus 4.7 and later always use **adaptive reasoning**. Thinking is optional on each step -- the model decides when and how much to think. The effort level controls how frequently and how deeply Claude thinks.

On Opus 4.6 and Sonnet 4.6, `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` reverts to fixed thinking budgets controlled by `MAX_THINKING_TOKENS`.

### `ultracode` -- the entry point to workflows

`ultracode` is a **Claude Code-specific setting**, not an API effort level:

- Sends `xhigh` to the model
- Additionally has Claude orchestrate dynamic workflows for substantive tasks
- Session-only (not persisted across sessions, not settable in settings.json)
- Removed from `/effort` menu when workflows are disabled
- Not part of `effortLevel` setting, `--effort` flag, or `CLAUDE_CODE_EFFORT_LEVEL`

Available to set via:
- `/effort ultracode`
- `"ultracode": true` via `--settings` or Agent SDK control request

Behavior: With ultracode on, a single request can trigger multiple workflows in sequence -- one to understand the code, one to make the change, one to verify it.

### `ultrathink` -- one-off deep reasoning

If a user includes `ultrathink` anywhere in a prompt, Claude adds an in-context instruction for deeper reasoning on that turn. The effort level sent to the API is unchanged. This is a keyword-based instruction, not a config change.

---

## 6. The Effort API (Platform Layer)

The underlying API is `output_config.effort` in the Messages API.

### Wire format

```json
{
    "model": "claude-opus-4-8",
    "max_tokens": 4096,
    "messages": [...],
    "output_config": {
        "effort": "medium"
    }
}
```

Key design choices:
- Effort parameter is in `output_config`, not top-level -- it's an output-side control
- Cannot be set to `ultracode` (ultracode is Claude Code only)
- Default is `high` on all surfaces

### Effort affects ALL tokens

- Text responses and explanations
- Tool calls and function arguments
- Extended thinking (when enabled)

### Advantages cited in platform docs

1. Does not require thinking to be enabled
2. Can affect all token spend including tool calls (lower effort = fewer tool calls)

### Relationship to extended thinking

| Model | Thinking mode | Effort interaction |
|---|---|---|
| Opus 4.8 | Adaptive only (`thinking: {type: "adaptive"}`) | Effort is primary control. Manual `budget_tokens` returns 400 error |
| Opus 4.7 | Adaptive only | Effort is primary control. Manual budget_tokens not supported |
| Opus 4.6 | Adaptive (with deprecated budget_tokens fallback) | Effort recommended. budget_tokens accepted but deprecated |
| Sonnet 4.6 | Adaptive (with deprecated interleaved thinking) | Effort recommended. budget_tokens functional but deprecated |
| Opus 4.5 | Manual only (budget_tokens) | Effort works alongside fixed token budget |

### Recommended max_tokens for xhigh/max

When running at xhigh or max effort: "Starting at 64k tokens and tuning from there is a reasonable default."

---

## 7. Entry Points and Activation

### Three activation patterns

1. **Keyword trigger**: Include the word `workflow` in your prompt. Claude Code highlights it and writes a workflow script instead of working turn-by-turn. Can be suppressed with `alt+w` or toggled off in `/config`.

2. **Ultracode mode**: `/effort ultracode` -- Claude decides when a task warrants a workflow, for every substantive task in the session. A single request can trigger multiple sequential workflows.

3. **Direct command**: Run a bundled workflow (`/deep-research`) or a saved workflow (`/<name>`).

### Availability surfaces

- CLI
- Desktop app
- IDE extensions (VS Code, JetBrains)
- Non-interactive mode (`claude -p`)
- Agent SDK

### Plan availability (pricing tiers)

Marked with: `feature=workflows plans=pro,max,team,enterprise providers=all`

- Pro: Turn on from `/config` Dynamic workflows row
- Max, Team, Enterprise: Available (admin toggle for Enterprise)
- API/Bedrock/Vertex/Foundry: Available

---

## 8. Permission Model and Approval Flow

### Approval per permission mode

| Permission mode | Approval behavior |
|---|---|
| Default, accept edits | Every run, unless "don't ask again" was selected for that workflow in this project |
| Auto | First launch only. Any "Yes" records consent in user settings. Later launches skip prompt. **Skipped entirely when ultracode is on** |
| Bypass, `claude -p`, Agent SDK | Never prompted. Run starts immediately |

### Subagent permissions within workflows

Workflow subagents always run in `acceptEdits` mode regardless of the session's mode. They inherit the user's tool allowlist.

- File edits are auto-approved
- Shell commands, web fetches, MCP tools not in the allowlist can still prompt mid-run
- In `claude -p` and Agent SDK, no interactive prompt exists -- tool calls follow configured permission rules

### Desktop app approval

Shows an approval card with:
- Workflow name
- Phase list
- Token-usage caution
- Actions: Once, Always, Deny

Progress appears in the Background tasks side pane.

---

## 9. Hard Limits and Constraints

### Concurrency

| Limit | Value |
|---|---|
| Max concurrent agents | **16** (fewer on low-CPU machines) |
| Max total agents per run | **1,000** |
| Max tasks per teammate (agent teams, not workflows) | No hard limit, but 5-6 tasks per teammate recommended |
| Agent teams max teams at once | 1 per lead |
| Agent teams max nested teams | 0 (no nested teams allowed) |

### Token budgets

- No explicit per-workflow token budget published
- Costs are a function of (agents * turns * tokens per turn)
- Each subagent auto-compacts at ~95% context capacity
- Runtime has no explicit token cap beyond the 1,000 agent limit
- `xhigh`/`max` effort recommends 64k `max_tokens` starting point

### Resumability limits

- Resume works **only within the same session**
- Exiting Claude Code forces a fresh start (no cross-session resume)
- Completed agents return cached results; remaining agents run live

### File isolation

- Workflow scripts have **no direct filesystem or shell access**
- Subagents inherit `acceptEdits` mode
- Subagent worktrees (`isolation: worktree`) auto-cleanup if no changes made
- Worktrees are cleaned up per `cleanupPeriodDays` (default 30) if no uncommitted changes

### Disable mechanisms

All these **disable workflows entirely**:
- Toggle Dynamic workflows off in `/config`
- `"disableWorkflows": true` in `~/.claude/settings.json`
- `CLAUDE_CODE_DISABLE_WORKFLOWS=1` env var (read at startup)
- Organization-level: managed settings `"disableWorkflows": true` or admin toggle

When disabled:
- Bundled workflow commands unavailable
- `workflow` keyword no longer triggers
- `ultracode` removed from `/effort` menu

---

## 10. Cost Characteristics

### Official guidance

- "A workflow spawns many agents, so a single run can use meaningfully more tokens than working through the same task in conversation"
- "Meaningfully more usage than a typical session"
- "Cost: Runs count toward your plan's usage and rate limits like any other session"

### Cost control mechanisms

1. **Model selection**: Choose cheaper models for stages that don't need strongest reasoning
2. **Stop early**: `/workflows` allows stopping any running agent or the whole workflow
3. **Don't lose completed work**: Stopping preserves completed agent results
4. **Check `/model` before large runs** if you typically switch to smaller models

### Enterprise rate-limit recommendations

| Team size | TPM per user | RPM per user |
|---|---|---|
| 1-5 users | 200k-300k | 5-7 |
| 5-20 users | 100k-150k | 2.5-3.5 |
| 20-50 users | 50k-75k | 1.25-1.75 |
| 50-100 users | 25k-35k | 0.62-0.87 |
| 100-500 users | 15k-20k | 0.37-0.47 |
| 500+ users | 10k-15k | 0.25-0.35 |

Background token usage (non-workflow): Typically under $0.04 per session from summarization and command processing.

### Agent SDK credit model (starting June 15, 2026)

Agent SDK and `claude -p` usage draws from a **new monthly Agent SDK credit**, separate from interactive usage limits.

---

## 11. Resumability and Session Management

### Per-session resumability

- The runtime tracks each agent's result as the run progresses
- This enables resume: completed agents return cached results; remaining agents run live
- Resume works **within the same Claude Code session**
- Exiting Claude Code **starts the workflow fresh** on next session

### The `/workflows` TUI

| Key | Action |
|---|---|
| `up`/`down` | Select a phase or agent |
| `Enter` or `right` | Drill into phase, then into agent (prompt, tool calls, result) |
| `Esc` | Back out one level |
| `j`/`k` | Scroll within agent detail |
| `p` | Pause or resume the run |
| `x` | Stop selected agent, or whole workflow when focused on the run |
| `r` | Restart selected running agent |
| `s` | Save the run's script as a command |

### Progress display

- Task panel below input box shows one-line progress
- Press down arrow to focus, Enter to expand
- Same `/workflows` view works for running and completed runs
- Also visible: Desktop app Background tasks side pane

### Subagent transcript persistence

- Stored in `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`
- Independent of main conversation: compaction does not affect them
- Survive session restart (if the session is resumed)
- Auto-cleaned after `cleanupPeriodDays` (default 30)

---

## 12. Comparison Matrix

### Subagents vs Skills vs Workflows

| Aspect | Subagents | Skills | Workflows |
|---|---|---|---|
| What it is | A worker Claude spawns | Instructions Claude follows | A script the runtime executes |
| Who decides next step | Claude, turn by turn | Claude, following the prompt | The script |
| Where intermediates live | Claude's context window | Claude's context window | Script variables |
| What's repeatable | The worker definition | The instructions | The orchestration itself |
| Scale | A few delegated tasks per turn | Same as subagents | Dozens to hundreds of agents per run |
| Interruption behavior | Restarts the turn | Restarts the turn | Resumable in same session |

### Subagents vs Agent Teams vs Agent View vs Workflows

| Approach | Coordination | Communication | Context | Best for |
|---|---|---|---|---|
| Subagents | Claude delegates | Results to caller only | Own context window | Focused side tasks |
| Agent view | You dispatch | Reports to you | Separate sessions | Independent tasks |
| Agent teams | Lead assigns | Inter-agent messaging | Separate session each | Complex coordination |
| Dynamic workflows | Script orchestrates | Results to script | Own context each | Large audits, migrations |

### Fork (experimental) vs Named Subagent

| Aspect | Fork | Named subagent |
|---|---|---|
| Context | Full conversation history | Fresh context with delegation prompt |
| System prompt & tools | Same as main session | From subagent definition file |
| Model | Same as main session | From subagent's model field |
| Permissions | Prompts surface in terminal | Auto-denied when background |
| Prompt cache | Shared with main session | Separate cache |

### Agent teams token usage

Agent teams use approximately **7x more tokens** than standard sessions when teammates run in plan mode. Each teammate is a separate Claude instance with its own context window.

---

## 13. Design Rationale

### Why a JavaScript script instead of Claude orchestrating turn by turn?

The fundamental insight is that **Claude's context window is the bottleneck** for large-scale coordination. As the workflow docs state: "With subagents and skills, Claude is the orchestrator: it decides turn by turn what to spawn next, and every result lands in Claude's context. A workflow script holds the loop, the branching, and the intermediate results itself, so Claude's context holds only the final answer."

Moving the plan into code enables:
- **Repeatability**: The script can be saved and rerun
- **Scale**: Dozens to hundreds of agents per run (vs. a few per turn)
- **Resumability**: The runtime tracks agent results independently of conversation state
- **Verification patterns**: Independent agents can adversarially review each other's findings

### Why the adversarial/verification pattern?

"With subagents and skills, Claude is the orchestrator: it decides turn by turn what to spawn next... Moving the plan into code also lets a workflow apply a repeatable quality pattern, not just run more agents: it can have independent agents adversarially review each other's findings before they're reported, or draft a plan from several angles and weigh them against each other."

This is the core rationale for the `/deep-research` workflow's architecture: independent searches, cross-checking, vote on claims, filter unverified claims.

### Why a separate runtime instead of in-context execution?

- Isolation: script errors don't corrupt the conversation
- Parallelism: the session stays responsive while agents work
- Progress tracking: the runtime tracks phases, agent counts, token totals independently
- No mid-run user input needed: the script runs without interruption

### Why acceptEdits mode for workflow subagents?

"Your permission mode controls only the launch prompt above. The subagents the workflow spawns always run in `acceptEdits` mode and inherit your tool allowlist, regardless of your session's mode."

This is a deliberate trade-off: file edits proceed without prompting (critical for a script that may spawn hundreds of agents), but shell/web/MCP tools not in the allowlist still prompt. This prevents permission prompts from bottlenecking high-volume file operations while maintaining guardrails on arbitrary command execution.

### Why no cross-session resumability?

"Resume works within the same Claude Code session. If you exit Claude Code while a workflow is running, the next session starts the workflow fresh."

The agent result cache is in-memory and tied to the session lifecycle. There is no persistent checkpoint store for workflow state across sessions. This avoids the complexity of reconciling concurrent workflow state with new session initialization.

---

## 14. What Is Explicitly NOT Supported

### Workflow scripts

- **No direct filesystem access** -- "No direct filesystem or shell access from the workflow itself"
- **No mid-run user input** -- except agent permission prompts
- **No TypeScript** -- scripts are JavaScript
- **No cross-session resumability** -- fresh start on session restart
- **No interactive debugging** -- no step-through or breakpoint support described
- **No workflow chaining from within a workflow** -- not documented or supported
- **No custom bundling/transpilation** -- runtime expects raw JS

### Subagents within workflows

- **No nested subagents** -- "Subagents cannot spawn other subagents" (hard rule)
- **No forking from within a workflow subagent** -- forks are experimental general-purpose subagent replacements
- **No Agent tool** -- "Subagents cannot spawn other subagents" means `Agent` tool is denied
- **No AskUserQuestion** within a subagent -- not available
- **No `hooks` field** in plugin subagents (plugin security boundary)
- **No `mcpServers` field** in plugin subagents
- **No `permissionMode` field** in plugin subagents

### Effort

- **`ultracode` is not an API effort level** -- it is Claude Code only
- **`max` and `ultracode` not settable in `effortLevel` settings file** -- session only
- **`ultracode` not available on models that don't support `xhigh`**
- **Fixed `budget_tokens` deprecated** on Opus 4.6 and Sonnet 4.6
- **Manual thinking not supported** on Opus 4.7+ (adaptive only)
- `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` has **no effect on Opus 4.7+**

### Agent teams (adjacent, not workflow)

- **No session resumption with in-process teammates** -- `/resume` and `/rewind` don't restore teammates
- **Task status can lag** -- teammates sometimes fail to mark tasks as completed
- **Shutdown can be slow** -- teammates finish current request before shutting down
- **One team at a time per lead**
- **No nested teams**
- **Lead is fixed** -- cannot promote teammate to lead
- **Permissions set at spawn time only**
- **Split pane mode** requires tmux or iTerm2 (not VS Code terminal, Windows Terminal, Ghostty)

### Worktrees (isolation mechanism)

- **`.worktreeinclude`** only copies **gitignored** files (not tracked files)
- **No `.worktreeinclude` processing** when using non-git `WorktreeCreate` hooks
- **Worktree base ref** limited to `"fresh"` (origin/HEAD) or `"head"` (local HEAD) -- no arbitrary refs
- **Subagent worktree auto-cleanup** only applies when no changes were made
- **`--worktree` worktrees** are never removed by the periodic sweep

### General

- **No `AGENTS.md` support** -- Claude Code reads `CLAUDE.md` specifically
- **No `defaultEnabled: true` in plugins** without explicit enable
- **`modelOverrides` do not transform** values passed via `ANTHROPIC_MODEL`, `--model`, or `ANTHROPIC_DEFAULT_*_MODEL`
- **`settings.availableModels`** evaluates against Anthropic model ID, not override value
- **Subagent `skills` frontmatter** not applied when definition runs as an agent team teammate
- **Subagent `mcpServers` frontmatter** not applied when definition runs as a teammate

---

## 15. Adjacent Mechanisms

### Agent teams (experimental)

- Enabled by `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Architectural components: Team lead, Teammates, Task list, Mailbox
- Storage: `~/.claude/teams/{name}/config.json` and `~/.claude/tasks/{name}/`
- Tasks have three states: pending, in-progress, completed
- Dependencies supported: tasks can depend on other tasks
- File locking prevents race conditions on task claims
- Hooks: `TeammateIdle`, `TaskCreated`, `TaskCompleted`

### Worktrees

- Created via `--worktree` flag or subagent `isolation: worktree`
- Default branch from `origin/HEAD` (or `head` with `worktree.baseRef: "head"`)
- Support PR-specific worktrees: `--worktree "#1234"`
- `.worktreeinclude` copies gitignored untracked files
- Cleanup: auto-remove if no changes; prompt if changes; `cleanupPeriodDays` sweep for subagent worktrees
- Non-git VCS supported via `WorktreeCreate`/`WorktreeRemove` hooks

### Agent SDK workflow support

- TypeScript Agent SDK v0.3.149+: `Workflow` tool available
- Include `Workflow` in `allowedTools` to auto-approve workflow runs
- Python SDK: no explicit workflow tool mentioned (TS-only as of docs snapshot)
- The SDK's `query()` function can receive `"ultracode": true` via control request

### `/deep-research` workflow

Execution pattern:
1. Fan-out: web searches across several angles
2. Fetch: retrieve and parse sources
3. Cross-check: agents review each other's sources
4. Vote: claims are voted on
5. Synthesize: produce cited report with unverified claims filtered

---

## Summary: Key Architectural Insights

1. **Separation of orchestration from execution**: The JS script holds the plan; the runtime executes it; agents do the work. This three-layer separation is what scales beyond a single conversation.

2. **Context isolation as a scale enabler**: Each subagent has its own context, and the script's intermediate state lives in script variables, not Claude's context. This avoids the context-window bottleneck that limits turn-by-turn orchestration.

3. **Adversarial verification as a first-class pattern**: The built-in `/deep-research` workflow formalizes cross-checking as an architectural pattern -- independent agents trying to refute each other's findings before synthesis.

4. **Permission elevation for workflow agents**: Workflow subagents run in `acceptEdits` mode regardless of parent session mode. This is a deliberate trade-off for throughput at the cost of some safety (mitigated by tool allowlists).

5. **Effort as the unifying control surface**: The effort level controls both per-message reasoning depth and (via ultracode) the decision to use workflows, creating a single knob from token efficiency to multi-agent orchestration.

6. **No persistence across session boundaries**: Workflow state is in-memory and session-scoped. The 1,000-agent cap, 16-concurrency ceiling, and no cross-session resume are the key constraints that bound the system for research preview.

