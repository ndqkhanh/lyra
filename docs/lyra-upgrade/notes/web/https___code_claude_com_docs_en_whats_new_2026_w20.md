# Week 20 · May 11–15, 2026 (Claude Code Changelog)

**Source:** https://code.claude.com/docs/en/whats-new/2026-w20  
**Author/Org:** Anthropic / Claude Code  
**Date:** Week of May 11–15, 2026 (Release v2.1.139 → v2.1.142)

---

## Key Technical Claims

1. **Agent view** (`claude agents`) — research preview. A dashboard listing every Claude Code session with status: running, blocked-on-input, completed. Sessions run in background without a terminal attached. Dispatch multiple tasks as independent rows (bug fix, PR review, test investigation). Attach to any row to enter its conversation; `←` returns to the list.

2. **`/goal` command** — Set a verifiable completion condition; Claude loops across turns automatically until the condition holds. After each turn, a fast model re-evaluates the condition. If not met, another turn starts instead of returning control to the user. Clears when satisfied. Works in interactive, `-p` (scripted), and Remote Control modes.

3. **Fast mode on Opus 4.7** — `/fast` now defaults to Opus 4.7 (was 4.6). Same quality at ~2.5x speed. Pricing unchanged at $30/$150 per MTok. Config override: `CLAUDE_CODE_OPUS_4_6_FAST_MODE_OVERRIDE=1`.

---

## Architecture/Mechanism Details

- **Agent view dispatch flags:** `--add-dir`, `--settings`, `--mcp-config`, `--plugin-dir`, `--permission-mode`, `--model`, `--effort`, `--dangerously-skip-permissions`. `--cwd <path>` scopes the session list.
- **`/goal` loop:** Fast evaluator model checks condition post-turn; if false, auto-continues without user prompt. The executor and verifier are decoupled in capability (full model vs. fast model).
- **Hook improvements:** `args: string[]` exec form spawns without a shell (no quoting issues). `continueOnBlock` for PostToolUse hooks feeds rejection reason back to Claude. `terminalSequence` in hook JSON output for desktop notifications, window titles, bells.
- **MCP:** stdio servers receive `CLAUDE_PROJECT_DIR`. Plugin configs can reference `${CLAUDE_PROJECT_DIR}`.
- **Plugin introspection:** `claude plugin details <name>` shows component inventory and projected per-session token cost. `SKILL.md` at root without `skills/` subdirectory is surfaced as a skill.
- **Subagent tool:** `subagent_type` matching is now case- and separator-insensitive.
- **Security boundary:** Remote Control, `/schedule`, Claude.ai MCP connectors, and notification preferences auto-disable when any API key env var is set.

---

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Fast mode speedup (Opus 4.7 vs 4.6 standard) | ~2.5x |
| Opus 4.7 fast mode pricing (input) | $30/MTok |
| Opus 4.7 fast mode pricing (output) | $150/MTok |
| `/goal` evaluator model | Fast (unspecified which, likely Haiku-class) |
| Release range | v2.1.139 → v2.1.142 |
| Release week | May 11–15, 2026 |

---

## Transfer to Lyra

**One idea:** `/goal`'s **self-verifying execution loop** — a fast, cheap evaluator model checks a user-defined completion condition after every turn and auto-continues if unmet. This is the exact architectural pattern Lyra needs for its "execute-until-verified" agent loop.

**How it maps to Lyra:**
- Lyra's agent loop already has a separation between the primary model and verifier. `/goal` formalises this into a tight loop: execute → fast-check → continue-or-halt.
- The key architectural insight is that the *condition evaluator* should be cheaper/stateless than the *executor*, which is how Claude Code achieves zero user-interruption for multi-step tasks.
- Lyra's current loop (brainstorm plan §4.x) re-prompts the user between turns. `/goal` shows how to replace user handoff with an automated verifier check when the end-state is well-defined.

**Workstream route:** §4.1 (Agent loop / execution architecture) — integrate the fast-evaluator check between executor turns, with configurable conditions (compile-clean, test-pass, lint-pass, custom). The agent-view dispatch model also informs §4.6 (Multi-agent orchestration) for Lyra's subagent management UI.

| Dimension | Score |
|-----------|-------|
| Impact | 8 (transforms the core agent loop from user-driven to goal-driven) |
| Effort | 2 (adds a condition-check step between executor turns; minimal net-new code) |
| Tier | 1 (core loop change; affects every Lyra run) |
