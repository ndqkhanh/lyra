# AnandChowdhary/continuous-claude -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** A shell-script conductor that runs Claude Code (or Codex CLI) in a continuous loop, autonomously creating PRs, waiting for CI checks, and merging -- so multi-step projects complete without human supervision.

**Mechanism (how the code really works):**

The entire system is a single 3525-line Bash script (`continuous_claude.sh`) plus a ~1400-line PowerShell port (`continuous_claude.ps1`). There is no Python, no package manager, no build step. The script is self-installing via `install.sh` / `install.ps1`.

The core loop (`main_loop()`, line 3408) is:

```
while true:
  1. Parse limits (max-runs, max-cost, max-duration, completion-signal)
  2. execute_single_iteration():
     a. Create a new git branch (e.g., continuous-claude/iteration-1/2025-11-15-be939873)
     b. Assemble enhanced prompt (workflow context + primary goal + SHARED_TASK_NOTES.md + knowledge file)
     c. Run: claude -p "$enhanced_prompt" --dangerously-skip-permissions --output-format stream-json --verbose
     d. Parse JSON stream output for cost, completion signal, result text
     e. Optionally run a second reviewer pass (different provider possible)
     f. Commit changes via another Claude Code call (tell Claude to write commit message)
     g. Push branch, create PR via `gh pr create`
     h. Wait for CI checks via `gh pr checks` (poll 10s, max 180 iterations = 30 min)
     i. Optionally retry CI failures (spawn Claude to inspect `gh run view --log-failed` and fix)
     j. Optionally address PR review comments (spawn Claude to read and respond)
     k. Merge PR via `gh pr merge --squash`
     l. Pull updated main, delete local branch, sleep 1s, repeat
```

**Context continuity** is achieved through `SHARED_TASK_NOTES.md` (configurable via `--notes-file`). The agent is instructed to update this file each iteration as a "relay baton" -- recording what was done, what is next, and any gotchas. A separate `--knowledge-file` (e.g., CLAUDE.md) stores durable project knowledge (conventions, architecture decisions) that persists across all iterations.

**Completion detection** works two ways: (a) agent outputs exact phrase `CONTINUOUS_CLAUDE_PROJECT_COMPLETE` (configurable via `--completion-signal`), or (b) heuristic detection of phrases like "all tasks complete" / "nothing left to do" combined with no pending git changes. Three consecutive signals (configurable via `--completion-threshold`) stop the loop.

## 2. Architecture & Core Modules

**Language:** Bash (main), PowerShell (Windows port), no compiled languages, no package.json/setup.py.

**File layout:**
- `continuous_claude.sh` (3525 lines) -- main conductor script
- `continuous_claude.ps1` (~1400 lines) -- PowerShell port for native Windows
- `install.sh` / `install.ps1` -- installers that download to ~/.local/bin
- `tests/test_continuous_claude.bats` (96KB) -- BATS test suite
- `CHANGELOG.md` -- comprehensive history from v0.0.0 to v0.24.7
- `LICENSE` -- MIT

**Entry point:** `main()` at line 3487:
1. Parse args (30+ flags)
2. Validate args and requirements (gh, jq, claude/codex installed)
3. Auto-detect GitHub owner/repo from git remote
4. Check for updates (auto-update via `gh release view` + checksum-verified download)
5. Optionally set up git worktree for parallel execution
6. Run `main_loop()`
7. Show completion summary
8. Optionally clean up worktree

**Data flow per iteration:**
```
User prompt + SHARED_TASK_NOTES.md + optional knowledge file
  --> Enhanced prompt (workflow context + iteration instructions + context)
    --> claude -p (stream-json) or codex exec
      --> JSON stdout piped through jq for:
          - Real-time display of agent messages (💬)
          - Real-time display of tool calls (emoji + detail)
          - Cost extraction from last JSON record (total_cost_usd)
      --> Branch: claude made changes -> commit via agent -> push -> PR
      --> PR: wait_for_pr_checks (10s polling, 30 min timeout)
        --> On CI failure: spawn agent to inspect and fix (gh run view --log-failed)
        --> On review comments: spawn agent to read and respond
      --> Merge (squash/merge/rebase) -> pull main -> delete branch
```

**Patterns:**
- **Conductor pattern:** The single bash script orchestrates everything, never modifies code itself, delegates all creative work to the AI agent.
- **Polling pattern:** 10-second sleep loop polling `gh pr checks`, max 180 iterations (30 min timeout).
- **Retry with exponential backoff:** Transient git/gh commands retry with doubling delay (5s, 10s, 20s...).
- **Rate limiting:** Optional `--max-calls-per-hour` throttles provider calls using timestamp-based rolling window.
- **Stall detection:** `--stall-threshold N` pauses after N consecutive failures, writes diagnostics to notes file, and waits for human intervention.
- **Zero-cost dry run:** `--dry-run` simulates without making any changes, useful for testing.

**Provider abstraction:** The script abstracts Claude Code and Codex CLI behind `get_agent_command()`, `get_agent_default_flags()`, and parallel `run_claude_provider_iteration()` / `run_codex_provider_iteration()` implementations. Provider can differ for main pass vs. reviewer pass (e.g., Claude for implementation, Codex for review).

## 3. Performance/Benchmarks

The repo does not include formal benchmarks, but the documentation and example output provide real-world data points:

- **Cost per iteration:** $0.042 (from example output in README, for adding unit tests to a single module)
- **30-minute CI wait timeout:** Max 180 polling iterations at 10-second intervals
- **Total cost for a session:** $0.042 for a single successful iteration in the example
- **Throttle ceiling:** Configurable via `--max-calls-per-hour` (default: no limit)
- **Error tolerance:** Default 3 consecutive non-rate-limit errors before exit; configurable via `--error-threshold`
- **Command retry:** Default 3 attempts with 5-second base delay, doubling each attempt
- **Completion threshold:** Default 3 consecutive completion signals to stop
- **Stall threshold:** Optional pause after N consecutive failures

The CHANGELOG shows active development from November 2025 through May 2026 (v0.0.0 to v0.24.7), with 24+ feature releases. Notable version milestones:
- v0.7.0: Completion signal feature (early stop)
- v0.12.0: Duration-based time boxing
- v0.15.0: Reviewer pass functionality
- v0.17.0: Real-time agent output streaming
- v0.18.0: CI failure retries
- v0.22.0: PR comment review before merge
- v0.23.0: Codex CLI provider support
- v0.24.1: Native PowerShell runner for Windows

## 4. Trade-offs

**Wins (what this gets right):**
1. **Extreme simplicity:** A single bash script with zero dependencies beyond standard CLI tools (gh, jq, claude/codex). No npm, no Python, no Docker.
2. **Context continuity via markdown:** The SHARED_TASK_NOTES.md handoff is elegant -- it leverages the AI's own summarization ability rather than building a complex state machine.
3. **API surface = GitHub:** By piggybacking on `gh pr` commands, it inherits all GitHub features (required checks, code owners, branch protection, preview environments) for free.
4. **Provider-agnostic abstraction:** Claude Code and Codex CLI supported with the same loop; reviewer can use a different provider than the main agent.
5. **Fault-tolerant design:** Transient command retries, CI fix retries, rate-limit backoff, stall detection with human intervention, and completion-signal-based early stopping all make the loop resilient.
6. **Parallel execution via git worktrees:** Multiple instances can run simultaneously on the same repo without conflict.
7. **Three stopping conditions:** Max runs, max cost ($USD), max duration (time) -- whichever hits first. Useful for cost control.
8. **Self-updating:** The script checks GitHub releases on startup, verifies SHA256 checksums, and replaces itself atomically.

**Loses (what is sacrificed/limited):**
1. **Bash scalability:** 3525 lines of Bash is at the outer edge of maintainability. Error handling, string manipulation, and JSON parsing via jq become progressively harder to extend.
2. **GitHub-only:** Full PR automation requires GitHub. Self-hosted forges (Gitea, GitLab) are explicitly not supported. Local-only mode exists but loses the core value.
3. **No persistence beyond files:** The only "state" is SHARED_TASK_NOTES.md. If the AI writes bad notes (verbose, missing context, hallucinated), the next iteration starts from a degraded state.
4. **Wasteful on failure:** When an iteration fails CI checks, the PR is closed, the branch is deleted, and all work is discarded. The justification ("with knowledge of test failures, the next attempt can try something different") is sound but expensive.
5. **Cross-platform fragmentation:** Worktree management, self-update, and CI/comment retry workflows are Bash-runner-only. The PowerShell runner is a subset.
6. **No built-in observability:** Cost tracking is a running total with no per-iteration breakdown beyond what is printed to stderr. No dashboard, no persistent log.
7. **--dangerously-skip-permissions by default:** The script passes this flag to Claude Code, accepting the safety trade-off for full automation. Codex similarly uses `--dangerously-bypass-approvals-and-sandbox`.
8. **Fixed 30-minute CI timeout:** `wait_for_pr_checks()` hardcodes 180 iterations * 10 seconds. For projects with long builds, this is insufficient and not configurable.

## 5. Design Rationale

The README narrative reveals the design philosophy: "genius and hilarious" simplicity. The author started with a `while true; do claude ...; sleep 1; done` one-liner and added tooling around it.

**Key design decisions:**

1. **Bash over Python/TypeScript:** Zero-install, universally available on any Unix system. The target audience is developers who already have the Claude Code CLI installed. Adding a language runtime would be a barrier.

2. **PR workflow over local editing:** By creating branches and PRs, the system gets CI checks, code review, and merge validation for free. The human stays in the loop via familiar GitHub mechanisms. Even if the AI produces bad code, the PR can be rejected without polluting main.

3. **Markdown file as external memory:** Rather than building a vector database or structured state store, the author chose the simplest possible persistence: a file the AI itself writes and reads. The relay-race metaphor ("passing the baton") is the key insight -- the AI summarizes its own progress in natural language.

4. **Wasteful-but-effective:** Inspired by statistical mechanics ("radiation of probabilities" -- each run is a random particle, the aggregate direction emerges from the distribution). Failed iterations are not analyzed individually; the system trusts that each failure teaches the next attempt something. This becomes viable as token costs approach zero.

5. **Completion by consensus:** Requiring 3 consecutive completion signals (not 1) reduces false positives from a single overconfident agent. The heuristic fallback (positive phrasing + no pending changes) adds robustness.

6. **Reviewer pass as second opinion:** Optional `-r` flag runs a separate agent on the diff before merging, mimicking human code review. The reviewer can use a different provider, creating a provider-agnostic separation of concerns.

## 6. Transfer to Lyra

**Transferable idea:** The `SHARED_TASK_NOTES.md` handoff protocol for inter-iteration context continuity.

**Why it matters:** Lyra's iterative agent loop currently has no formal mechanism for passing context between iterations. The Markov-chain degradation observed in long-running agents could be mitigated by having each iteration explicitly summarize its state, decisions, and next steps into a rotating markdown file. This is trivial to implement (no dependencies, no infrastructure) and directly addresses the context window exhaustion problem documented in the Lyra corpus.

**Implementation sketch:**
- At the end of each Lyra agent execution, inject a structured prompt instructing the agent to update a `WORKING_NOTES.md` file (or `/workspace/state/relay.md`) with a succinct handoff section.
- At the start of the next iteration, prepend the handoff notes into the system prompt.
- The notes file itself is git-ignored and lives only in the workspace, not in the project repo.
- Optionally, a separate `KNOWLEDGE.md` file for durable project knowledge (architecture decisions, conventions, gotchas) that grows over iterations but is curated (not a dump of all status).

**Workstream route:** This maps to **Section 4.2 (Agent Loop Orchestration)** -- the design space around iteration management, context window budgeting, and multi-turn reliability. Specifically, it addresses the "Context Continuity" subsection of §4.2.

**Impact:** 8/10 -- High. Context degradation across iterations is a known failure mode in Lyra's deep-research workflow. This pattern directly mitigates it with near-zero implementation cost.

**Effort:** 2/10 -- Low. A single prompt addition (instruct the agent to write notes) plus one file read at iteration start. No new infrastructure.

**Tier:** P1 (foundational reliability improvement)

**License:** MIT -- fully compatible with Lyra's licensing model, no restrictions on reuse.
