# Tools Reference (code.claude.com / Anthropic)

**Source:** https://code.claude.com/docs/en/tools-reference
**Date extracted:** 2026-06-07
**Relevance:** Lyra tool system design, subagent permission model, agent safety architecture

---

## Key Technical Claims

1. **30+ built-in tools** are organized into three categories: read-only (no permission), write/execute (permission required), and specialized orchestration tools. Every tool can be individually allowed, denied, or restricted via pattern-matching rules.

2. **Permission rules follow a uniform `ToolName(specifier)` format** with tool-specific specifier semantics:
   - `Bash(npm run *)` — glob-based command matching
   - `Read(~/.secrets/**)` — gitignore-style path matching
   - `Edit(/src/**)` — path-based write access (also grants read access implicitly)
   - `WebFetch(domain:example.com)` — domain-level allow/deny
   - `Skill(deploy *)` — skill name prefix matching
   - `Agent(Explore)` — subagent type matching

3. **Subagent tool inheritance has four modes** determined by the `tools` and `disallowedTools` frontmatter fields:
   - Neither set: inherit every parent tool
   - `tools` only: restricted to the listed tools
   - `disallowedTools` only: all parent tools except the listed ones
   - Both set: `disallowedTools` takes precedence (a tool in both is removed)

4. **Background subagents auto-deny permission prompts** — they run with permissions already granted in the session and silently skip any tool call that would otherwise prompt. Foreground subagents surface prompts normally.

5. **Edit is exact string replacement** with three preconditions (read-before-edit, exact match, uniqueness) and no regex or fuzzy matching. `replace_all: true` handles multiple identical occurrences.

6. **WebFetch is intentionally lossy** — it runs extraction through a small, fast model rather than returning raw page content. The extraction prompt determines what reaches Claude; a "page does not mention X" result may only mean the prompt did not ask.

7. **WebSearch can issue up to eight internal backend searches** per call, refining queries before returning final results. It returns only titles and URLs (no page content); fetching pages requires a separate WebFetch call.

---

## Architecture / Mechanism Details

### Tool Resolution Hierarchy
Tools are resolved through a layered configuration system:
- `settings.json` → `permissions.allow` / `permissions.deny` arrays
- CLI flags: `--allowedTools` / `--disallowedTools`
- Agent SDK: `allowedTools` / `disallowedTools` options
- Subagent frontmatter: `tools` / `disallowedTools` fields
- Skill frontmatter: `allowed-tools` field
- Hook conditions: `if` field referencing tool names

Each layer accepts the same `ToolName(specifier)` rule format, making tool restriction portable across all configuration surfaces.

### Subagent Isolation Model
- Named subagents spawn in a separate context window; parent sees only the final text result, not intermediate tool calls or outputs.
- Fork mode creates a subagent that inherits the full parent conversation instead of starting fresh, runs in the background, and surfaces permission prompts in the terminal.
- `maxTurns` caps subagent execution duration.
- Subagents started with `isolation: worktree` get separate git worktree directories.

### Bash Environment Semantics
- Each command runs in a fresh process. Working directory changes carry over only if they stay inside the project or explicitly added directories. Subagents never carry over cwd changes.
- Environment variables do NOT persist between commands. Use `CLAUDE_ENV_FILE` or SessionStart hooks for persistence.
- Shell aliases and functions from startup files are captured and applied to every command, but only at session start.
- Default timeout: 2 minutes. Max: 10 minutes (configurable). Output capped at 30K chars default, 150K hard ceiling.
- Virtualenv/conda must be activated before launching Claude Code (not during).

### Edit Safety
- Read-before-edit check runs first (file must have been read in current conversation; file must not have changed on disk since).
- Certain Bash commands (`cat`, `head`, `tail`, `sed -n`, `grep`, `egrep`, `fgrep` on single files) satisfy the read requirement.
- Piped output and other Bash commands do NOT satisfy read-before-edit.

### WebFetch Pipeline
1. URL is fetched (HTTP auto-upgraded to HTTPS)
2. HTML is converted to Markdown (not configurable)
3. A small, fast model processes the content using the extraction prompt
4. Result is cached for 15 minutes
5. Cross-host redirects are NOT followed automatically; Claude must issue a second fetch

### LSP Integration
- Automatically reports type errors and warnings after each file edit, enabling fix-without-build patterns.
- Direct operations: go-to-definition, find-references, hover types, workspace symbol search, call hierarchy, implementation lookup.
- Requires a separately installed language server and code intelligence plugin.

### Monitor Tool (v2.1.98+)
- Claude writes a small watch script, runs it backgrounded, and receives live output lines.
- Use cases: tailing logs for errors, polling CI status, watching directories for changes.
- Stopped by asking Claude to cancel or ending the session.
- Uses the same permission rules as Bash for allow/deny patterns.

---

## Numbers & Benchmarks

| Dimension | Value | Configurable? |
|-----------|-------|---------------|
| Bash default timeout | 2 min | `BASH_DEFAULT_TIMEOUT_MS` |
| Bash max timeout | 10 min | `BASH_MAX_TIMEOUT_MS` |
| Bash default output cap | 30,000 chars | `BASH_MAX_OUTPUT_LENGTH` |
| Bash hard output ceiling | 150,000 chars | (hard-coded) |
| Glob result cap | 100 files | (hard-coded; shows truncation flag) |
| WebFetch cache TTL | 15 min | (hard-coded) |
| WebSearch internal searches | up to 8 per call | (fixed by backend) |
| PDF page limit per Read call | 20 pages | (hard-coded) |
| Image downscaling | large images auto-scaled | (automatic) |
| Monitor min version | v2.1.98 | — |
| TodoWrite deprecation | v2.1.142+ | — |

---

## Transfer to Lyra

### One Transferable Idea: Layered Subagent Tool Permission Model

The Claude Code `ToolName(specifier)` permission model — uniform rule syntax applied through multiple config layers (settings, CLI, SDK, subagent frontmatter, skills, hooks) — is directly transferable to Lyra's subagent safety architecture. Specifically:

**Claude's model:** A subagent's effective tool set is the intersection of:
- The parent session's granted permissions
- The subagent's `tools` allow list (if set)
- Minus the subagent's `disallowedTools` deny list (overrides allow)

Background agents further apply auto-deny: any tool call that *would* prompt for permission is silently skipped. This creates a clean capability gradient: unrestricted foreground → restricted foreground → unrestricted background → restricted background.

**Lyra equivalent:**
- Lyra's subagent spawning code (currently in `src/verification/` and planning documents) should adopt a similar layered permission model where each subagent carries a privilege mask at spawn time.
- The mask is computed as: `(parent_permissions ∩ allowed_tools) \ disallowed_tools`
- Background agents additionally set a `auto_deny_unseen=true` flag that maps to Claude's auto-deny behavior for unapproved tool calls.
- The permission rule format should use lyra-specific specifiers: `FileRead(/projects/**)`, `NetworkAccess(api.lyra.dev)`, `CodeExecution(python *)`, etc.

This matters because Lyra currently lacks a uniform permission system across its subagent types (explore, planner, executor, verifier). Adopting this layered mask model would give Lyra deterministic, auditable subagent capability boundaries without requiring a full sandbox.

### Workstream Route

This maps to **§4.3 Permission & Safety System** in the Lyra architecture document. The subagent tool inheritance model (inherit-all, only-listed, all-except, precedence rules) should be specified in §4.3.2 (Subagent Privilege Model), and the auto-deny behavior for background agents in §4.3.3 (Runtime Safety).

### Ratings

- **Impact:** 7 — A uniform permission model is foundational for safe multi-agent orchestration; Lyra currently lacks this in production subagent spawning.
- **Effort:** 4 — Clean conceptual model; implementation is a matter of adding a permission mask to the subagent spawn path and threading it through tool dispatch.
- **Tier:** T2 (Important — should be designed before Lyra ships multi-tenant subagent execution)
