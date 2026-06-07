# `/goal` — Persistent Goal Evaluation (code.claude.com / Anthropic)

Fetched: 2026-06-07
URL: https://code.claude.com/docs/en/goal

---

## Key Technical Claims

1. **`/goal` sets a completion condition** and Claude keeps working across turns until the condition is met, without the user prompting each step. After each turn, a small fast model checks whether the condition holds. If not, Claude starts another turn instead of returning control. The goal clears automatically once the condition is met.

2. **Three approaches to keep a session running** are compared: `/goal` (next turn starts when previous finishes, stops when condition is met), `/loop` (next turn starts on a time interval, stops when you stop it), and Stop hooks (next turn starts when previous finishes, stops when your own script/prompt decides). `/goal` and Stop hooks both fire after every turn.

3. **The evaluator judges from the conversation transcript** -- it does not run commands or read files independently. The condition must be written as something Claude's own output can demonstrate (e.g., "All tests in `test/auth` pass" works because Claude runs the tests and the result lands in the transcript).

4. **An effective condition has** one measurable end state (a test result, build exit code, file count, empty queue), a stated check (how Claude should prove it), and constraints that must not change on the way there.

5. **Complementary with Auto mode**: auto mode removes per-tool prompts (approves tool calls automatically), `/goal` removes per-turn prompts (starts the next turn automatically). Together they enable fully unattended multi-turn sessions.

---

## Architecture/Mechanism Details

### How Evaluation Works

`/goal` is a wrapper around a session-scoped **prompt-based Stop hook**. Each time Claude finishes a turn, the condition and the conversation so far are sent to the configured small fast model (default: Haiku). The model returns a yes-or-no decision and a short reason:

- **"no"**: tells Claude to keep working and includes the reason as guidance for the next turn
- **"yes"**: clears the goal and records an achieved entry in the transcript

The evaluator runs on whichever provider the session is configured for. It does not call tools -- it can only judge what Claude has already surfaced in the conversation.

### Condition Format

- Up to **4,000 characters**
- To bound runtime, include a turn or time clause: `or stop after 20 turns`
- Claude reports progress against that clause each turn

### Status & Lifecycle

- `◎ /goal active` indicator shows how long the goal has been running
- `/goal` with no arguments shows: condition, duration, turn count, token spend, evaluator's most recent reason
- `/goal clear` (or `stop`/`off`/`reset`/`none`/`cancel`) removes an active goal
- An active goal is **restored on session resume** (`--resume`, `--continue`), but turn count, timer, and token-spend baseline reset
- An achieved or cleared goal is **not** restored on resume

### Requirements

- Requires Claude Code v2.1.139 or later
- Runs only in workspaces where the trust dialog has been accepted (evaluator is part of the hooks system)
- Unavailable when `disableAllHooks` is set at any settings level
- Unavailable when `allowManagedHooksOnly` is set in managed settings

### Non-Interactive Operation

Works in non-interactive mode (`-p`), desktop app, and through Remote Control. Setting a goal with `-p` runs the loop to completion in a single invocation. Interrupt with Ctrl+C.

```bash
claude -p "/goal CHANGELOG.md has an entry for every PR merged this week"
```

---

## Numbers & Benchmarks

| Detail | Value |
|--------|-------|
| Minimum version | Claude Code v2.1.139+ |
| Condition max length | 4,000 characters |
| Evaluator default model | Haiku (user-configurable small fast model) |
| Evaluation token cost | "Typically negligible compared to main-turn spend" |
| Evaluator capability | Read-only -- no tool calls, judges from conversation transcript only |
| Goal restoration on resume | Active goals only (not achieved/cleared); counters reset |

No latency or success-rate benchmarks are provided for the evaluator itself.

---

## Transfer to Lyra

### One Idea: Persistent turn-level evaluator loop for unattended fleet operation

The `/goal` mechanism is the most transferable pattern: a **separate, cheap evaluator model** (Haiku) that checks a condition after every turn and decides whether to continue or stop. This is precisely what Lyra's Phase 3 supervisor daemon needs for unattended multi-turn workflows.

Concretely: Lyra's fleet daemon should implement a `lyra goal` command that accepts a completion condition, then loops across subagent turns with Haiku-level evaluations. When the condition is met (e.g., "all 5 PRs have CI green and no merge conflicts"), the fleet shuts down the relevant sessions. When not met, the evaluator's short reason becomes the next subagent's directive -- exactly the same loop Anthropic uses for `/goal`.

### Workstream Route

- **Primary: §4.7 Autonomy & Self-Knowledge** -- The persistent evaluator loop is the core mechanism for Lyra's sequenced autonomy gates. Phase 2 "idle autonomy" and Phase 3 "background research" both need this pattern: a cheap evaluator that checks whether the autonomous work is complete and decides whether to continue.
- **Secondary: §4.19 Verification** -- Using a *different* model (Haiku) to judge the main agent's output aligns with Lyra's bias-corrected adversarial verification philosophy. The evaluator never shares the main agent's blind spots because it uses a separate, smaller model with different parameters.
- **Also informs: §4.2 Workflow Engine** -- The Stop-hook-based architecture (/goal as a wrapper around prompt-based Stop hooks) is a lightweight alternative to a full workflow engine for simple "keep doing X until Y" loops.

### Scoring

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Impact | 7/10 | Enables truly unattended multi-turn operation for Lyra fleet -- eliminates the human bottleneck in every turn. Directly unblocks Phase 3 autonomy. |
| Effort | 4/10 | Low to moderate -- the infrastructure already exists (Lyra's hooks system, model router for cheap evaluator). The evaluator prompt template and loop orchestration are the main implementation items. |
| **Tier** | **Tier 2 (Phase 3)** | Needed for unattended fleet operation. Phase 1 (spine) doesn't need it; Phase 2 (workflows) benefits but can use simpler loops. Tier 2 because it's a force multiplier for fleet autonomy, not a core research breakthrough. |
