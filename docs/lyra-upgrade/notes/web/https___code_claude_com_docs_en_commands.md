# Commands (code.claude.com / Anthropic)

Fetched: 2026-06-07
URL: https://code.claude.com/docs/en/commands

---

## Key Technical Claims

1. **Commands are the primary interaction surface** for Claude Code from inside a session. 80+ commands span the full development lifecycle: project init, task execution, parallel work, code review, shipping, and debugging.

2. **Three kinds of commands**: (a) built-in commands hardcoded into the CLI, (b) **bundled skills** -- prompts handed to Claude that it can also auto-invoke, and (c) **bundled workflows** -- dynamic multi-agent orchestrations that fan work across subagents and run in the background.

3. **MCP servers can register commands** dynamically via the `/mcp__<server>__<prompt>` naming convention, extending the command palette without a CLI patch.

4. **Command architecture**: only recognized at the start of a message; text after the command name is passed as arguments; availability depends on platform, plan, and environment.

---

## Architecture/Mechanism Details

### Commands across a typical workflow

| Phase | Commands |
|-------|----------|
| First session in a repo | `/init`, `/memory`, `/mcp`, `/agents`, `/permissions` |
| During a task | `/plan`, `/model`, `/effort`, `/context`, `/compact`, `/btw` |
| Running work in parallel | `/agents`, `/tasks`, `/background`, `/batch`, `/fork` |
| Before shipping | `/diff`, `/code-review`, `/review`, `/security-review` |
| Between sessions | `/clear`, `/resume`, `/branch`, `/teleport` |
| Troubleshooting | `/rewind`, `/doctor`, `/debug`, `/feedback` |

### Key architectural commands relevant to Lyra

- **`/batch <instruction>`** (Skill): Orchestrates large-scale changes across a codebase in parallel. Researches the codebase, decomposes work into 5-30 independent units, presents a plan for approval. Once approved, spawns one **background subagent per unit** in an **isolated git worktree**. Each subagent implements, runs tests, and opens a PR. Requires a git repo.

- **`/fork <directive>`** (v2.1.161+): Spawns a forked subagent that inherits the **full conversation context** and works on the directive in the background. Results return to the conversation when finished. Contrast with `/branch` which switches *you* into a copy of the conversation.

- **`/background [prompt]`**: Detaches the current session to run as a background agent, freeing the terminal. Monitor with `claude agents`.

- **`/agents`**: Opens a manager for subagent configurations (the detailed subagent management interface).

- **`/ultraplan <prompt>`**: Drafts a plan in an ultraplan cloud session, reviewable in browser, then executed remotely or sent back to the terminal.

- **`/code-review ultra`**: Runs a deep multi-agent code review in a cloud sandbox.

- **`/workflows`**: Progress view to watch, pause, resume, or save running/completed workflows.

- **`/effort [level|auto]`**: Sets model effort level (`low`, `medium`, `high`, `xhigh`, `max`, `ultracode`). `ultracode` combines `xhigh` reasoning with automatic workflow orchestration.

- **`/tasks`**: View and manage all background-running work. Also available as `/bashes`.

- **`/goal [condition|clear]`**: Claude keeps working across turns until the condition is met -- a persistent directive loop.

### MCP Prompts as Commands

MCP servers expose prompts that become dynamically discovered commands using the format `/mcp__<server>__<prompt>`. This creates a plugin architecture where third-party servers extend the CLI command namespace without code changes to the core.

---

## Numbers & Benchmarks

| Detail | Value |
|--------|-------|
| `/batch` decomposition range | 5-30 independent units |
| `/code-review` effort levels | `low`, `medium`, `high`, `xhigh`, `max`, `ultra` |
| `/effort` levels | `low`, `medium`, `high`, `xhigh`, `max`, `ultracode` |
| `/simplify` parallel agents | 4 (reuse, simplification, efficiency, abstraction level) |
| Version gates | simplify v2.1.154+, reload-skills v2.1.152+, fork v2.1.161+ |
| `/ultrareview` free runs | 3 on Pro/Max, then usage credits |

No benchmark numbers (latency, token cost, success rate) for the commands themselves are provided in this reference page.

---

## Transfer to Lyra

### One Idea: Batch decomposition + isolated worktree execution

The `/batch` command embodies the most transferable pattern: a central orchestrator researches a codebase, decomposes a large task into 5-30 independent units, presents a plan for human approval, then spawns **one background subagent per unit in an isolated git worktree**. Each subagent works independently (implement, test, PR) with no cross-contamination. The orchestrator does not micromanage execution -- it delegates fully and only re-engages for plan approval and result collection.

### Workstream Route: Section 4.3 -- Multi-Agent Orchestration / Work Decomposition

This maps directly to **Lyra Section 4.3 (Work Decomposition & Multi-Agent Scheduling)** and **Section 4.4 (Isolated Execution Environments)**:

- **4.3**: Lyra's work decomposer should adopt `/batch`'s pattern of *research-first, then decompose, then present for approval, then fan out*. The 5-30 unit decomposition range gives a concrete target for Lyra's shard sizing. The orchestrator should not execute -- it should plan and delegate.
- **4.4**: The isolated git worktree per subagent is precisely what Lyra needs for safe parallel execution. Each subagent gets a clean branch, runs tests independently, and produces an isolated PR. This eliminates cross-agent interference and makes results reviewable independently.
- **4.5** (incidental): The `/fork` command shows how to pass full conversation context to a subagent -- Lyra's subagent handoff protocol should similarly serialize and transfer relevant context state.

### Impact Assessment

- **Impact: 8/10** -- Work decomposition + isolated execution is a core Lyra mechanism. Getting this right determines whether multi-agent parallelism actually improves throughput or creates coordination overhead.
- **Effort: 7/10** -- Requires an orchestrator agent, worktree management, a plan approval UX, and PR lifecycle management. Significant but well-scoped.
- **Tier: P0** -- Without this, Lyra cannot scale beyond single-agent tasks.
