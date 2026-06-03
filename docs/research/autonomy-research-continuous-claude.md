# Autonomy Research: Continuous Claude

## Source
[continuous-claude](https://github.com/AnandChowdhary/continuous-claude) — 1344 GitHub stars

## Core Mechanism
Simple `while true` loop orchestrating Claude Code with persistent context via shared markdown file (`SHARED_TASK_NOTES.md`). Each iteration:
1. Creates branch
2. Runs Claude with relay-race prompt ("make progress on one thing, leave notes for next iteration")
3. Commits/pushes
4. Creates PR
5. Waits for CI checks
6. Merges on success or discards on failure
7. Pulls main and repeats

Supports multiple stop conditions: max runs, max cost (USD budget), max duration (time-boxed), or completion signal threshold (agents output special phrase when project complete).

## Key Result
Author used it to go from 0% to 80%+ test coverage on hundreds of thousands of lines of code. Enables multi-step projects to complete autonomously "while you sleep." Works with both Claude Code and Codex CLI.

## Limitation
Wasteful on failure (discards entire PR). No sophisticated error recovery beyond retry. Context continuity depends entirely on quality of notes file — verbose logs harm more than help. Requires GitHub CLI and PR-based workflow.

## Transferable Ideas

### 1. Relay-Race Autonomy Pattern
**Explicit instruction**: "You don't need to complete entire goal, just make progress on one thing and pass the baton"

Prevents context exhaustion and enables indefinite operation. Key prompt elements:
- "This is part of a continuous development loop where work happens incrementally across multiple iterations"
- "You don't need to complete the entire goal in one iteration. Just make meaningful progress on one thing, then leave clear notes for the next iteration"
- "Think of it as a relay race where you're passing the baton"

### 2. Shared Notes File as External Memory
Single markdown file (`SHARED_TASK_NOTES.md`) serves as handoff package between iterations, reducing context drift.

Prompts explicitly guide note quality: "stay concise and actionable (like a notes file, not a detailed report)"

Separate `KNOWLEDGE_FILE` (e.g., `CLAUDE.md`) for durable project knowledge vs iteration-specific notes.

### 3. Multi-Dimensional Stop Conditions
Combine multiple limits for flexible control:
- `--max-runs N` — iteration count limit
- `--max-cost $X` — USD budget limit (tracks token costs)
- `--max-duration 2h` — time-boxed execution
- `--completion-signal` + `--completion-threshold` — semantic completion (agents output special phrase when project done, requires N consecutive signals to stop)

Flexible combination: "run max 10 iterations OR $5, whichever comes first"

### 4. CI-Driven Validation Loop
Each iteration creates PR, waits for checks, merges on success.

**Automatic CI failure retry**: if checks fail, runs agent again with CI logs to fix

**Automatic comment review**: if PR has review comments, runs agent to address them

Leverages existing GitHub workflows (code review, preview environments, required checks) without additional tooling.

### 5. Worktree-Based Parallelism
`--worktree <name>` creates isolated git worktree for parallel execution.

Multiple continuous loops can run simultaneously on different tasks. Each worktree maintains independent state, branches, and PRs.

### 6. Reviewer Pass Pattern
`--review-prompt` runs second agent after main iteration.

**Default reviewer**: runs tests/lint, invokes `/simplify` skill, starts dev server, screenshots app, verifies behavior

**Separate provider support**: `--provider claude --review-provider codex` for heterogeneous validation

### 7. Rate Limiting & Throttling
- `--max-calls-per-hour N` throttles provider calls to hourly ceiling
- `--error-threshold N` stops after N consecutive non-rate-limit errors
- `--stall-threshold N` pauses after N consecutive failures, writes diagnostics to notes file for human intervention

### 8. Command Retry with Exponential Backoff
- `--command-retry-max N` retries transient commit/push/PR-create failures
- `--command-retry-base-delay S` sets initial delay, doubles after each failure
- Distinguishes transient failures (network, GitHub API) from persistent failures (code issues)

## Architecture Insights

**Stateless iterations with persistent context**: Each iteration is independent (can be killed/restarted), but shared notes file provides continuity

**Idempotent by design**: If process dies, next run picks up from notes file and continues

**Wasteful but effective**: Discarding failed PRs is acceptable as token costs approach zero; focus on general direction rather than individual iteration success

**Human-in-loop via familiar mechanisms**: PR reviews, CI checks, and merge approvals provide oversight without custom tooling

## Lyra §4.14 Full Autonomy Adoption Path

1. **Implement relay-race prompt pattern** in existing autonomy modes (ralph, ultrawork, autopilot)
2. **Add shared notes file mechanism** to `.omc/state/` for iteration handoffs
3. **Implement multi-dimensional stop conditions** (iterations, cost, duration, semantic completion)
4. **Add worktree-based parallelism** for concurrent autonomous tasks
5. **Integrate reviewer pass pattern** with existing verification agents
6. **Add rate limiting and throttling** to prevent API exhaustion
7. **Implement command retry with exponential backoff** for transient failures

## Impact & Effort
**Impact**: 5 | **Effort**: 3 | **Tier**: BREAKTHROUGH
