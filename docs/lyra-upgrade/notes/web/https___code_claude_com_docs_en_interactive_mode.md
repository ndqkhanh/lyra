# Interactive mode (Claude Code official docs, Anthropic)

**Source**: https://code.claude.com/docs/en/interactive-mode
**Author/Org**: Anthropic (official Claude Code documentation)
**Date**: No explicit date; appears to be current as of mid-2025.

## Key Technical Claims

1. Claude Code features a rich interactive mode with layered keyboard shortcuts, vim editing, shell passthrough, background task execution, side questions, and session recaps.
2. The `/btw` mechanism ("side questions") provides a way to query the LLM's existing context without adding to conversation history and without interrupting a running turn -- it is the inverse of a subagent (full context, zero tools).
3. Prompt suggestions are generated from git history and conversation context, running as background requests that reuse the parent conversation's prompt cache for minimal cost.
4. Background bash commands can be spawned asynchronously with unique task IDs; output is written to a file that Claude can retrieve later via the Read tool.
5. Session recaps generate automatically when the terminal is unfocused for 3+ minutes and the session has 3+ turns, providing a one-line summary on return.
6. Task lists persist across context compactions, surviving the window-trimming process.

## Architecture / Mechanism Details

- **Keyboard shortcuts**: General controls (Ctrl+C interrupt/clear, Ctrl+X Ctrl+K kill-all-background, Ctrl+G open editor, Ctrl+O transcript viewer, Ctrl+B background, Ctrl+T task list toggle, Esc interrupt, Esc+Esc rewind menu).
- **Multiline input**: Five methods available -- backslash-Enter, Option+Enter, Shift+Enter, Ctrl+J, or direct paste. Shift+Enter is native in most terminals; VS Code/Cursor etc. need `/terminal-setup`.
- **Quick commands**: `/` for command/skill menu, `!` for raw shell passthrough, `@` for file-path autocomplete.
- **Shell mode (`!` prefix)**: Runs commands directly without Claude interpretation. Output feeds back into conversation context. History-based autocomplete on Tab from previous `!` commands in the project.
- **Background bash**: Ctrl+B backgrounds a running bash tool invocation. Output capped at 5GB. Disable with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`.
- **Prompt suggestions**: Gray placeholder text in empty prompt, drawn from git history and conversation flow. Tab to accept. Skipped when cache is cold. Disable with `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false`.
- **`/btw` side questions**: Ephemeral Q&A overlay. No tool access -- answers only from current context. Full visibility into the conversation. Forkable into a real session with `f` key. Reuses parent prompt cache.
- **Task list**: Up to 5 visible at a time in terminal status area. Persist across compactions. Named session sharing via `CLAUDE_CODE_TASK_LIST_ID`.
- **Session recap**: Background generation after 3 min idle + 3+ turns. On-demand via `/recap`. Skipped in non-interactive mode.
- **PR review status**: Shows clickable PR link with colored underline (green=approved, yellow=pending, red=changes requested, gray=draft). Refreshes every 60s and immediately after `gh pr`/`git push`.

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Background task output cap | 5 GB (auto-terminated with stderr note) |
| PR status refresh interval | 60 seconds |
| Session recap idle threshold | 3 minutes since last completed turn |
| Session recap turn threshold | Minimum 3 turns |
| Task list visible limit | 5 tasks at a time |
| Prompt suggestion cache gate | Skipped when prompt cache is cold |

## Transfer to Lyra

**One idea**: Side questions (`/btw`) as a non-interrupting, ephemeral context query mechanism.

The `/btw` pattern solves a fundamental UX tension: users need quick clarifications mid-workflow, but those questions should not (a) clutter the conversation history, (b) interrupt the current turn, or (c) incur full tool-call latency. Lyra can implement this as a "quick query" mode that reuses the active session's compressed context but bypasses the tool execution pipeline. The inverse architecture (full context, no tools) is deliberately the mirror of a subagent (no context, full tools) -- Lyra already has the subagent abstraction, so adding the inverse is a contained extension.

**Workstream route**: §4.x -- Ephemeral interaction layer / non-interrupting context queries.

This maps to the interactive/UX layer of Lyra. The engineering surface is modest (context reuse without tool dispatch, ephemeral overlay rendering, fork-to-session bridge) but the UX impact is high because it unblocks the "I just need a quick answer" path that currently forces users to either flood the history or open a separate agent.
