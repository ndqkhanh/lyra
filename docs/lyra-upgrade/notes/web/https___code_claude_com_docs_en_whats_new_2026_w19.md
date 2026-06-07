# Week 19 · May 4–8, 2026 (Claude Code Changelog)

**Source:** code.claude.com/docs/en/whats-new/2026-w19
**Org:** Anthropic / Claude Code
**Release range:** v2.1.128 → v2.1.136

---

## Key Technical Claims

1. **Plugins from .zip archives and URLs** — The `--plugin-dir` flag now accepts `.zip` archives directly, and a new `--plugin-url` flag fetches a plugin archive from a remote URL for the current session. This enables ephemeral plugin loading from artifact stores or registries before committing a plugin to a marketplace.

2. **Cross-project history search** — `Ctrl+R` reverse-search now defaults to all prompts across every project (restoring pre-v2.1.124 behavior). `Ctrl+S` narrows to current project/session mid-search.

3. **Auto mode hard deny rules** — A new `settings.autoMode.hard_deny` configuration list blocks matching actions unconditionally in auto mode. These rules override any allow exceptions, providing an absolute safety barrier for actions that should never run automatically.

4. **Worktree base ref control** — New `worktree.baseRef` setting (`fresh` | `head`) controls whether `--worktree`, `EnterWorktree` tool, and agent-isolation worktrees branch from the remote default branch or local HEAD. Default `fresh` prevents unpushed commits from leaking into new worktrees.

5. **Sub-agent prompt cache hit** — Sub-agent progress summaries now hit the prompt cache, reducing `cache_creation` token cost by approximately 3x.

6. **OTEL isolation** — Subprocesses (Bash, hooks, MCP, LSP) no longer inherit `OTEL_*` environment variables, preventing OTEL-instrumented apps from accidentally picking up the CLI's own OTLP endpoint.

7. **Effort level in hooks** — Hooks receive the active effort level via `effort.level` JSON input and `$CLAUDE_EFFORT` environment variable, enabling conditional hook behavior (e.g., skip expensive checks at low effort, enforce strict checks at high effort).

---

## Architecture/Mechanism Details

### Hard Deny Rules (`settings.autoMode.hard_deny`)
- List of action patterns that are unconditionally blocked in auto mode.
- These take precedence over any broader allow rules or exceptions.
- Purpose: a last-resort safety barrier for operations that must never run autonomously, even when the user has configured permissive auto-mode settings.
- **Directly applicable to Lyra's 4.5 (Safety) layer** — Lyra needs analogous "unconditional hard stops" that no agent or workflow can override, regardless of permission level or escalation path.

### Plugin Loading from URLs (`--plugin-url`)
- Enables session-scoped, ephemeral plugin loading without local installation.
- Useful for CI/CD pipelines, internal artifact stores, and try-before-you-buy workflows.
- Lyra could adopt similar "remote plugin" semantics for tool/plugin distribution without requiring git submodules or vendoring.

### Worktree Base Ref (`worktree.baseRef`)
- `fresh` (default): branch from remote default branch. Ensures unpushed local commits stay isolated.
- `head`: branch from local HEAD. Useful when work depends on uncommitted local changes.
- Lyra's `EnterWorktree`-equivalent could use this same dual-mode approach: isolation worktrees start clean, collaborative worktrees inherit local state.

### Sub-agent Prompt Cache
- Progress summaries from sub-agents now reliably hit the prompt cache.
- Claimed 3x reduction in `cache_creation` tokens.
- Key insight: structured, predictable sub-agent output formats make prompt caching effective even in multi-agent orchestration.
- Lyra's orchestrator should enforce strict output schemas for sub-agent summaries specifically to maximize cache hits.

---

## Numbers & Benchmarks

| Metric | Value | Context |
|--------|-------|---------|
| Cache creation cost reduction | ~3x | Sub-agent progress summaries hitting prompt cache |
| Release range | v2.1.128 → v2.1.136 | 9 releases in one week |
| Features this week | 2 major + ~12 minor | Plus bug fixes |

No latency, throughput, or reliability benchmarks were provided beyond the cache cost figure.

---

## Transfer to Lyra

**The one idea:** **Hard Deny Rules for Lyra's Safety Architecture.**

Claude Code's `hard_deny` concept — unconditional deny rules that override any allow exceptions — is directly transferable to Lyra's safety/guardrail system. Lyra currently lacks a mechanism for truly unconditional safety constraints. An agent with broad permissions could theoretically perform any action within those permissions. Adding a `hard_deny` layer would create a two-tier safety model:

- **Soft allow/deny** — normal permission granting, escalation, and override paths (governed by policy, agent role, human approval).
- **Hard deny** — actions that no agent can ever perform, regardless of escalation chain, human override, or role elevation. Examples: `DELETE * FROM users`, `DROP DATABASE`, `rm -rf /`, API calls to production payment endpoints.

This maps to Lyra upgrade **workstream §4.4 (Reliability/Predictability)** — specifically the idea that some safety boundaries must be architecturally enforced, not merely policy-enforced. The Lyra orchestrator should check a `hard_deny` list before any action dispatch, and this check must execute in the orchestrator's own security context, not delegatable to a sub-agent.

**Implementation sketch:**
```python
# Lyra orchestrator pseudo-code
HARD_DENY_PATTERNS = [
    "db:write:users:*",       # no agent can ever write user records
    "fs:delete:/etc/**",      # no agent can ever delete system config
    "api:production:billing", # no agent can ever call prod billing API
]

async def dispatch(action):
    if any(match(action, pattern) for pattern in HARD_DENY_PATTERNS):
        raise UnconditionalDeny(action, pattern)
    # ... proceed to normal allow/deny/ask pipeline
```

**Effort:** Very low — a pattern-matching check in the action dispatch pipeline, plus a configuration file. No new infrastructure.

**Route:** §4.4 (Reliability/Predictability) — hard deny rules make the system's safety guarantees architecturally verifiable, not just policy-dependent.
