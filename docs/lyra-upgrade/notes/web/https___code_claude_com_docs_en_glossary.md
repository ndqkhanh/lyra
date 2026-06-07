# Claude Code Glossary (code.claude.com/docs)

Official product glossary for Claude Code. Defines 30+ terms covering agentic loop, compaction, hooks, subagents, MCP, skills, settings layers, verification loop, worktree isolation, and more. Each entry links to a dedicated deep-dive page.

No author listed. No single publication date; the page is the canonical live glossary for the current version of the product.

---

## Key Technical Claims

1. **Agentic harness vs. model** -- "Claude Code is the harness; Claude is the model inside it." The harness supplies file access, shell execution, permission gating, memory loading, and the agentic loop. This is the clearest articulation of the harness/model boundary in product docs.

2. **Agentic loop** -- The cycle "gather context, take action, verify results, and repeat until done." All extension points (hooks, skills, MCP) plug into specific phases of this loop.

3. **Compaction** -- Automatic conversation summarization when context window approaches limit. Project-root CLAUDE.md and auto memory survive compaction and reload from disk. Instructions given only in conversation may be lost.

4. **MCP Tool Search** -- A context-saving mechanism that defers MCP tool schemas until needed. Only tool names load at startup; Claude fetches the full schema on demand when it decides to use a specific tool. Keeps idle MCP servers from consuming much context.

5. **Verification loop** -- "How a session knows the work is actually done rather than just plausible." Claude iterates until a check passes instead of stopping after one attempt. Called "the prerequisite for `/goal`, unattended runs, and dynamic workflows."

6. **Settings layers** -- Precedence: managed policy > CLI args > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. Arrays merge; scalars override.

7. **Hook configuration** -- Three tiers: hook event (lifecycle point), matcher (filters which events fire it), hook handler (what runs). Handlers can be shell, HTTP, MCP, LLM prompt, or subagent. Hooks are deterministic (always fire at fixed points).

---

## Architecture/Mechanism Details

- **Auto memory**: Notes Claude writes for itself stored per-repo under `~/.claude/projects/`. First 200 lines or 25 KB of MEMORY.md loads at start of every session. All worktrees of one repo share a single auto memory directory.

- **Subagents**: Run in their own context window with a custom system prompt, specific tool access, and independent permissions. Unlike agent teams (full independent sessions you talk to directly).

- **Skills (SKILL.md)**: Loaded automatically when relevant or invoked directly. Successor to custom commands. `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way.

- **MCP Channel**: A server that pushes events into a running session for reactivity (Telegram, Discord, iMessage in research preview).

- **Auto mode permission**: Separate classifier reviews each action in background. Never sees tool results, so injected instructions cannot influence its approval decisions.

- **Project trust**: Directory acceptance dialog before Claude loads config. Trust gates auto-installation of marketplace plugins and execution of project hooks.

- **Worktree isolation**: Runs Claude in a separate git worktree under `.claude/worktrees/`. Changes on separate branch/directory so parallel agents don't overwrite.

---

## Numbers & Benchmarks

- Auto memory: first **200 lines** or **25 KB** of MEMORY.md loads at session start.
- Compaction: triggers when context window approaches its **200K token** limit (Opus).
- CLAUDE.md: loaded as a **user message** after system prompt, between **16K and 25K** conceptual context share (not independently benchmarked here).
- Settings layers: **5 layers** of precedence from managed policy down to user settings.
- Hook configuration: **3 tiers** (event, matcher, handler).
- Bundled skills: includes `/batch`, `/code-review`, `/debug`, `/loop`.

---

## Transfer to Lyra

### One Idea: Verification Loop as a First-Class Protocol

The glossary formalizes the **verification loop** as the essential prerequisite for unattended agent runs: "without one, the only thing deciding the agent is finished is the agent itself."

Lyra's architecture already has a `VerificationHarness` capability. This glossary entry confirms that verification should be elevated from an optional post-processing step to a **mandatory, architecturally enforced loop** at the workstream level. Every workstream step must define a verifiable check (test pass, build success, diff inspection) and iterate until it passes before the next step begins.

**How Lyra differs**: Claude Code's verification loop is session-scoped (one conversation). Lyra operates across multiple subagents, workstreams, and research iterations. The Lyra adaptation should enforce verification at the **workstream transition boundary**: Step A must emit its verification check, Step B must confirm it before starting. This creates a chain of verified handoffs rather than a single loop.

### Workstream Route: $4.4 Workstream Orchestration -- Verified Handoffs

Add a "Verification Contract" subsection to the workstream orchestration design:

- Each workstream step declares a verification predicate (type: assertion, test-run, lsp-diag, build-check).
- The orchestrator blocks step transition until the predicate passes.
- Failed predicates trigger a retry loop (max N attempts, escalating to human).

### Effort Assessment

| Dimension | Value | Notes |
|-----------|-------|-------|
| Impact | 8/10 | Prevents garbage-in-garbage-out across multi-step workstreams |
| Effort | 3/10 | Low code cost -- orchestrator already exists, just needs predicate enforcement |
| Tier | Tier 1 | Foundational safety mechanism; prerequisite for unattended execution |

### Cross-Reference

- **lyra-verification-workflow.js** -- the existing verification workflow already has the loop mechanism; needs workstream-level sequencing.
- **docs/lyra-upgrade/plans/16-reliability.md** -- reliability plan touches verification but scopes it to output quality, not workstream handoff.
