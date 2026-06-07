# obra/superpowers -- Deep-Read

Repository: https://github.com/obra/superpowers
Author: Jesse Vincent (Prime Radiant)
Version: 5.1.0 (2026-04-30)
Language: Markdown (skills), Shell (hooks), JavaScript (brainstorm server, plugin bootstrap)

## 1. Headline Feature & Mechanism

Superpowers is a complete software-development methodology packaged as a zero-dependency plugin for AI coding agents. It replaces ad-hoc agent behavior with a mandatory, composable pipeline of "skills" -- markdown documents with YAML frontmatter that shape agent behavior like code.

The pipeline is: **brainstorming -> writing-plans -> subagent-driven-development (with TDD + two-stage review) -> finishing-a-development-branch.** Each skill auto-triggers via its description field when the agent encounters a matching scenario, and the description says ONLY when to trigger -- never summarizes the workflow. This "Description Trap" discovery is critical: if the description summarizes what the skill does, the agent reads the 50-word shortcut instead of the 500-word authority.

The mechanism is a **SessionStart hook** (shell script) that injects the `using-superpowers` bootstrap into every conversation via JSON `hookSpecificOutput.additionalContext`. This bootstrap teaches agents: invoke the Skill tool before any response, check even if 1% chance a skill applies, and follow the embedded DOT/GraphViz flowcharts which are the authoritative process definition (prose is secondary). Skills contain checklists that get converted to TodoWrite tasks, rationalization tables that pre-empt agent shortcuts, and hard gates that block implementation skills until design is approved.

Subagent-driven development dispatches a fresh subagent per task with isolated context (no history bleed), runs two-stage review (spec compliance then code quality), and uses review loops (fix, re-review, repeat until approved). The controller never reads plan files on behalf of subagents -- it provides full task text upfront.

## 2. Architecture & Core Modules

### Entry Points & Configuration

- **`hooks/session-start`** -- Bash script, the single entry point. Fires on `startup|clear|compact`, reads `skills/using-superpowers/SKILL.md`, escapes it for JSON, and injects it into conversation context. Platform-aware: detects Claude Code (hookSpecificOutput.additionalContext), Cursor (additional_context), Copilot CLI/Gemini (additionalContext SDK standard).
- **`hooks/hooks.json`** -- Plugin hook manifest, calls `run-hook.cmd session-start` synchronously.
- **`package.json`** -- Contains `"type": "module"`, names the `.opencode/plugins/superpowers.js` as main for OpenCode integration.
- **`.claude-plugin/plugin.json`** -- Claude Code plugin manifest, declares name/version/license/homepage.
- **`.cursor-plugin/plugin.json`**, **`.codex-plugin/plugin.json`**, **`gemini-extension.json`** -- Platform-specific manifests.

### Skills Library (14 composable skills)

Each is a directory with `SKILL.md` + optional supporting files:

| Skill | Purpose | Key Mechanism |
|-------|---------|---------------|
| `using-superpowers` | Bootstrap: skill discovery, invocation, priority | DOT flowchart, Red Flags table, Rationalizations table, Instruction Priority hierarchy |
| `brainstorming` | Socratic design refinement before coding | 9-item checklist with TodoWrite, DOT process flow, `<HARD-GATE>` blocking implementation skills, visual companion, spec self-review |
| `writing-plans` | Detailed implementation plans with 2-5 min tasks | File structure mapping, bite-sized granularity, "No Placeholders" section, self-review checklist, execution handoff (subagent vs inline) |
| `subagent-driven-development` | Per-task subagent dispatch with two-stage review | DOT process flow per-task (implementer -> spec reviewer -> code quality reviewer -> loop), model selection guidance, status protocol (DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT) |
| `test-driven-development` | RED-GREEN-REFACTOR enforcement | Hard gate: "No production code without failing test first," DOT TDD cycle, rationalization table, verification checklist |
| `requesting-code-review` | Subagent code review dispatch | `code-reviewer.md` template with Critical/Important/Minor severity, git SHA range review, output format with Strengths/Issues/Assessment |
| `systematic-debugging` | 4-phase root cause investigation | Iron law: "No fixes without root cause investigation first," multi-component diagnostic instrumentation, 3-fix architectural threshold |
| `using-git-worktrees` | Isolated workspace management | Step 0: detect existing isolation, native tool preference (Step 1a), git worktree fallback (Step 1b), `.gitignore` verification |
| `finishing-a-development-branch` | Branch completion workflow | 4-option menu (merge/PR/keep/discard), provenance-based cleanup, detached HEAD handling |
| `verification-before-completion` | Evidence-before-claims enforcement | Gate function: identify -> run -> read -> verify -> claim, Red Flags for rationalization |
| `writing-skills` | TDD for documentation/skill creation | No skill without failing test first, The Description Trap documentation, rationalization table patterns |
| `dispatching-parallel-agents` | Parallel subagent dispatch | Independent problem domain identification, focused agent tasks |
| `executing-plans` | Inline execution with checkpoints | Alternative to subagent-driven, batch execution for non-subagent-capable harnesses |
| `receiving-code-review` | Responding to code review feedback | How to engage with reviewer feedback |

### Architecture Pattern

**Skill-Based Behavior Shaping (documentation-as-code).** The pattern is:
1. YAML frontmatter with `name` and `description` (trigger conditions only, no workflow summary)
2. DOT/GraphViz flowchart as the authoritative process definition
3. Checklist items that map to TodoWrite tasks for progress tracking
4. Red Flags tables pre-empting common agent rationalizations
5. Rationalization tables ("Excuse | Reality") addressing known evasion patterns
6. Hard gates (`<HARD-GATE>`, `<EXTREMELY-IMPORTANT>`, `<SUBAGENT-STOP>`) enforcing mandatory steps
7. Subagent prompt templates (`implementer-prompt.md`, `spec-reviewer-prompt.md`, `code-quality-reviewer-prompt.md`) for Task tool dispatch

Dependencies: **Zero.** No npm packages, no Python libraries, no runtime dependencies. The brainstorm server uses Node.js built-in modules only (http, fs, crypto, ws from scratch). Platform hooks are pure bash/POSIX shell.

## 3. Performance/Benchmarks

### Token & Cost Benchmarks (from integration tests)

A full subagent-driven development session (2 tasks, 2 reviewers each, 1 final review):

| Metric | Value |
|--------|-------|
| Total cost | $4.67 |
| Total messages | 41 |
| Total input tokens (incl. cache) | 1,515,639 |
| Total output tokens | 8,419 |
| Cache creation tokens | 132,742 |
| Cache read tokens | 1,382,835 |
| Per-subagent cost | $0.07-$0.09 |
| Coordinator (main session) | $4.09 of $4.67 total |
| Integration test runtime | 10-30 minutes |

### Methodology Benchmarks (from release notes)

- **Self-review vs subagent review**: Self-review catches 3-5 real bugs in ~30 seconds vs ~25 minutes for subagent review loop, with "comparable defect rates" (v5.0.6, tested across 5 versions with 5 trials each)
- **Systematic debugging**: 15-30 min systematic fix vs 2-3 hours random-thrashing fixes. Claimed 95% first-time fix rate vs 40%. Near-zero new bugs introduced.
- **Spec/plan review iterations**: Reduced from max 5 to max 3 (v5.0.4); calibration section added to prevent false positives
- **Subagent context isolation**: Prevents context window pollution -- each subagent gets only the task context, not the full session history

### Operational Benchmarks

- **SessionStart hook**: POSIX-safe, works on macOS/Linux/Windows (Git Bash/msys2/cmd.exe). O(n^2) `escape_for_json` fixed to O(n) with bash parameter substitution (60+ seconds -> near-instant on Windows Git Bash)
- **Node.js plugin bootstrap**: OpenCode bootstrap `getBootstrapContent()` cached at module level -- was calling `fs.existsSync` + `fs.readFileSync` on every agent step; now read-once, cached for session lifetime

## 4. Trade-offs

### Wins

- **Zero dependencies.** Plugin works immediately on clone. No npm install, no vendored deps, no runtime requirements. The brainstorm server is the only exception (Node.js built-ins only, no npm).
- **Cross-platform.** Works on 8 harnesses: Claude Code, Codex CLI, Codex App, Cursor, Gemini CLI, GitHub Copilot CLI, OpenCode, Factory Droid. Each gets the same skill pipeline.
- **Self-review beats subagent review.** V5.0.6 regression testing showed self-review (inline, ~30s) catches as many defects as subagent review loop (~25 min). This is a validated empirical finding: field-testing across 5 versions x 5 trials showed identical quality scores.
- **Token-efficient architecture.** Description fields never summarize workflow (agents follow the shortcut instead of reading the skill). Bootstrap cached at module level. Subagents get only needed context.
- **Behavior-shaping rigor.** Red Flags tables, rationalization tables, hard gates, "spirit vs letter" closures -- all battle-tested against real agent rationalization patterns.
- **Provenance-based cleanup.** Worktree cleanup checks path prefixes before deleting -- won't touch harness-managed workspaces.
- **Flowcharts as executable specs.** DOT diagrams are the authoritative process definition; prose is supporting content. This prevents agents from skimming prose and skipping steps.

### Loses

- **No quantitative benchmark suite.** Impossible to measure "how much better" the methodology makes agents. Only evaluable via adversarial pressure testing (qualitative, expert-judgment-based).
- **94% PR rejection rate.** The repo's own stats show nearly all AI-generated PRs are rejected as slop. This means the system is brittle to external contribution -- only the maintainer can safely evolve it.
- **Cross-platform fragility.** Windows-specific bugs in hooks execution (CRLF, `bash` auto-prepend, cmd.exe quoting, WSL PID visibility, MSYS2 process reaping) consumed significant maintenance effort across multiple releases.
- **Bash version regressions.** Bash 5.3+ heredoc hang on macOS, dash "Bad substitution" on Ubuntu. Each shell regression requires workarounds.
- **Brainstorm server has Node.js dependency.** While zero-dependency within Node.js, it requires Node to be installed -- the only non-zero-runtime-cost component.
- **OpenCode bootstrap caching bug.** `getBootstrapContent()` was calling disk I/O on every agent step before being fixed.
- **PID lifecycle false positives.** Cross-user PIDs (Tailscale SSH) and WSL short-lived grandparent PIDs caused false server shutdowns.
- **Subagent review loop removed.** After discovering it provided no quality benefit over self-review, the entire subagent review loop was removed. This was a significant architecture sunk-cost: designed, implemented, tested across releases, then deleted.
- **No integration tests for skills.** Skills are tested via adversarial pressure sessions (which are qualitative, require expert judgment, and can't be CI-automated easily). The integration tests that exist test subagent-driven infrastructure, not individual skill effectiveness.
- **No model-specific tuning.** Skills treat all models equally, but Claude Haiku vs Opus vs Gemini-2.5-Pro have vastly different tendencies to rationalize, follow flowcharts, or skip steps.

## 5. Design Rationale

**Skills Are Code, Not Prose.** The single most important design principle. A skill document is a behavior-shaping program for an AI agent. It uses frontmatter (trigger conditions), flowcharts (process), tables (anti-patterns), and hard gates (enforcement) -- not narrative writing. Changes require adversarial pressure testing, just like code changes require unit tests.

**The Description Trap.** When descriptions summarize workflow, agents follow the 50-word shortcut instead of reading the 500-word authority. This was discovered empirically: changing descriptions from "Code review between tasks" (with workflow summary) to "Use when executing implementation plans with independent tasks" (trigger-only) caused agents to actually read the flowchart and follow two-stage review.

**TDD for Documentation (The Iron Law).** "No skill without a failing test first" -- every skill must be developed by: (1) running a pressure scenario WITHOUT the skill to establish baseline failure, (2) writing the skill to address those specific failures, (3) re-running to verify compliance, (4) refactoring to close loopholes. This prevents speculative content that doesn't address real agent behavior.

**Agent Rationalization Resistance.** Skills anticipate and pre-empt agent shortcuts through: Red Flags tables (what agent might think -> why it's wrong), Rationalization tables (excuse -> reality), Hard gates (block until condition met), and Spirit-vs-Letter closures ("Violating the letter is violating the spirit"). These evolved through real adversarial testing: each release notes agent rationalization patterns observed in testing and the counter-measures added.

**Subagent Context Isolation.** Subagents never inherit the coordinator's session history. The controller constructs exactly the context each subagent needs (full task text, architectural context, relevant files). This prevents context window pollution, keeps subagent focus narrow, and preserves the coordinator's context for orchestration work.

**Flowcharts Over Prose.** DOT/GraphViz diagrams are the authoritative process definition. Prose exists to support the diagrams, not the other way around. Testing revealed that agents follow flowcharts more reliably than checklists or prose descriptions. The DOT graphs are embedded directly in SKILL.md files and rendered to SVG with `render-graphs.js` for human consumption.

**"Human Partner" Framing.** Deliberate language choice over "the user." This sets a collaboration dynamic rather than a service dynamic. Changing this phrasing would break the carefully-tuned social contract between agent and human.

**Progressive Discovery Over Monolith.** The bootstrap (`using-superpowers`) is lean -- it teaches skill invocation rules and trigger conditions, not the full content of every skill. Skills load on demand when triggered. Reference files and supporting techniques are in subdirectories, not inline. This keeps the always-loaded context tiny.

**Empirical Over Dogmatic.** The v5.0.6 removal of the subagent review loop is the best evidence: 5 versions x 5 trials of regression testing showed self-review (30s) matched subagent review (25 min) in defect detection. When data contradicted design, the design changed. This is a repo that tracks its own effectiveness and adapts.

## 6. Transfer to Lyra

### Transferable Idea: "Skills as Code" -- Auto-Triggering Behavior Modules

Superpowers demonstrates that AI agent behavior can be reliably shaped through a system of auto-triggering, composable skill documents with: (1) trigger-only descriptions that avoid the "Description Trap," (2) flowcharts as executable process definitions, (3) rationalization-resistant enforcement (Red Flags, hard gates, tables), (4) checklist-to-TodoWrite tracking, and (5) adversarial pressure testing for validation. This is a proven methodology across 8 agent harnesses and 5 major versions.

For Lyra, this means packaging each subsystem's behavior logic (memory, context management, routing, safety checks, reliability patterns) as a self-contained "skill" that auto-triggers when the agent encounters a matching scenario. Each skill would contain its own flowchart, anti-rationalization table, and test suite. The SessionStart hook pattern (injecting bootstrap context at conversation start) maps directly to Lyra's need for consistent agent instruction injection.

### Workstream Route

**Lyra SS4.3 -- Skill-Based Orchestration.** Superpowers' skill pipeline (brainstorm -> plan -> subagent-drive -> review -> finish) is the most mature example of agent skill-based orchestration in the open-source ecosystem. Lyra's existing work on skill routing and plugin architecture in SS4.3 can directly adopt: the DOT flowchart-as-executable-spec pattern, the Red Flags/Rationalization table anti-pattern systems, and the "description is trigger-only" constraint.

**Alternate route: SS4.5 -- Agentic Behavior Engineering.** The adversarial testing methodology (pressure scenarios with subagents, baseline without skill vs compliance with skill) is directly applicable to Lyra's agent behavior verification pipeline. The "iron law" -- no skill without a failing pressure scenario first -- would give Lyra a test-driven approach to crafting agent instructions.

### Impact

8/10 -- High. Adopting Superpowers' methodology would give Lyra a proven framework for shaping agent behavior that has been field-tested across 8 platforms, 5 major versions, and hundreds of real sessions. The key insights (Description Trap, flowcharts over prose, rationalization resistance, self-review over subagent review) are directly applicable to Lyra's skill system design.

### Effort

6/10 -- Medium-High. Requires converting each Lyra subsystem's behavior specifications into the Superpowers skill format: writing trigger-only descriptions, embedding DOT flowcharts, building rationalization tables, and running adversarial pressure testing for each skill. The format is lightweight (pure markdown + shell + optional Node.js) but the testing methodology is labor-intensive.

### Tier

**Core.** This is a foundational architecture decision for how Lyra agents are instructed and orchestrated. It affects every subsystem that shapes agent behavior, which is essentially all of them.

### LICENSE

MIT License -- Copyright (c) 2025 Jesse Vincent. Free to use, modify, distribute, sublicense. No attribution requirements beyond the license notice. Compatible with Lyra's licensing.
