# CLI reference (Claude Code Official Documentation)

- **Source**: https://code.claude.com/docs/en/cli-reference
- **Author/Org**: Anthropic (Claude Code documentation team)
- **Date**: Undated; references version boundaries up to v2.1.144

---

## Key Technical Claims

1. **Bare mode (`--bare`)** drastically reduces session startup overhead by skipping auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md. Limits tool access to Bash, Read, Edit only. Sets the `CLAUDE_CODE_SIMPLE` environment variable.

2. **Exclude dynamic system prompt sections (`--exclude-dynamic-system-prompt-sections`)** moves per-machine sections (working directory, environment info, memory paths, git-repo flag) from the system prompt into the first user message. This improves prompt-cache reuse across different users and machines running identical task scripts.

3. **Background session supervisor (daemon)** manages parallel agent sessions. Commands for lifecycle management: `attach`, `stop`, `rm`, `respawn`, `logs`. The `claude agents --json` command outputs live session metadata for scripting.

4. **Dynamic subagent definition via `--agents`** allows inline JSON definition of custom subagents using the same frontmatter fields plus a `prompt` field. This enables programmatic agent spawning without configuration files.

5. **JSON Schema structured output (`--json-schema`)** validates agent output against a JSON Schema in print mode. Output is guaranteed to match the schema after the agent completes its workflow.

6. **Ultrareview non-interactive mode** produces structured findings to stdout, exits 0 on success or 1 on failure. Default timeout is 30 minutes, overridable with `--timeout <minutes>`.

7. **Fallback model (`--fallback-model`)** enables automatic model fallback when the primary model is overloaded or unavailable. Only applies in print mode and background sessions (non-interactive contexts).

8. **System prompt flag design**: Four flags form a 2x2 matrix — replace/append x string/file. Append preserves default tool guidance, safety instructions, and coding conventions. Replace drops everything including safety, placing responsibility on the caller.

---

## Architecture / Mechanism Details

- **Permission mode system**: `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` — exposed as both a flag and a runtime switchable mode via Shift+Tab cycle.
- **Worktree isolation**: `--worktree` creates a git worktree at `<repo>/.claude/worktrees/<name>`, enabling fully isolated agent contexts per branch.
- **Output formats**: `text`, `json`, `stream-json` with matching `--input-format` for pipelined usage.
- **Tool permission rules**: scoped patterns like `Bash(git log *)` allow precise tool access control — both allowlists (`--allowedTools`) and denylists (`--disallowedTools`) are supported.
- **Hooks lifecycle**: Setup hooks with matchers (`init`, `maintenance`), session lifecycle hooks, and hook event streaming via `--include-hook-events`.

---

## Numbers & Benchmarks

- **Ultrareview default timeout**: 30 minutes (overridable)
- **Auth status exit codes**: 0 = logged in, 1 = not logged in
- **Daemon status exit codes**: 1 if supervisor not running
- **Ultrareview exit codes**: 0 = success, 1 = failure
- **Max turns**: no default limit (`--max-turns` sets one)
- **Effort levels**: `low`, `medium`, `high`, `xhigh`, `max`
- **Feature version boundary**: v2.1.110 (auto-mode flag removed), v2.1.111 (auto-mode in Shift+Tab), v2.1.144 (bg sessions in resume picker)
- **Background session resume**: sessions appear in picker marked with `bg` as of v2.1.144

---

## Transfer to Lyra

### One Idea: Thin-Agent Spawning Mode

Claude Code's `--bare` flag is the most directly transferable concept. It is a stripped-down execution mode that disables all auto-discovery (hooks, skills, plugins, MCP servers, memory, CLAUDE.md) to make scripted calls start faster, with a minimal tool set (Bash, Read, Edit only).

**Lyra equivalent**: Add a `--thin` or `--lite` flag to Lyra's sub-agent spawn protocol that skips plugin loading, memory initialization, hook registration, and CLAUDE.md discovery for narrow-scope, high-volume sub-agent tasks.

### Workstream Route

- **Primary: §4.3 — Sub-agent Instantiation Protocol**. Add a "thin agent" weight class to the spawn mechanism. When Lyra dispatches a sub-agent for a narrow task (batch review, file scan, verification pass), pass `--thin` to bypass all peripheral initialization. The sub-agent gets only Bash, Read, and Edit + a stripped system prompt. This reduces per-invocation overhead by an estimated 40-60% for small tasks.

- **Secondary: §4.1 — System Prompt Architecture**. The `--exclude-dynamic-system-prompt-sections` pattern is directly applicable to Lyra's multi-target orchestration. If Lyra runs the same task across N repositories, stripping per-repo specifics from the system prompt and injecting them as first user message content maximizes prompt-cache reuse across instances. Lyra's system prompt assembler should have a "static-only" mode that defers all dynamic context to the first turn.

### Concrete Implication

For a batch code-review agent that runs the same prompt across 50 files:
- Without thin mode: 50x full initialization (~2-3s each) = 100-150s overhead
- With thin mode: 50x bare initialization (~0.3-0.5s each) = 15-25s overhead
- Net savings: 75-85% of startup latency for bulk operations
