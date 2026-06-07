# addyosmani/agent-skills -- Deep-Read

## 1. Headline Feature & Mechanism

**Structured engineering workflow skills for AI coding agents.** The repo delivers 23 Markdown-based "skills" that encode the workflows, quality gates, and best practices of senior software engineers. Each skill is a self-contained `SKILL.md` file with YAML frontmatter, following a consistent anatomy: Overview -> When to Use -> Process (numbered steps) -> Common Rationalizations (excuse/rebuttal table) -> Red Flags -> Verification (checklist).

The mechanism is **progressive-disclosure workflow injection**. On session start, a hook (`hooks/session-start.sh`) injects the `using-agent-skills` meta-skill into the agent's context. This meta-skill acts as a decision tree: when a task arrives, the agent follows a flowchart to discover which skill applies, then loads that specific `SKILL.md`. Skills reference one another but do not duplicate content -- references (testing patterns, security checklists, performance checklists) live in a shared `references/` directory and are loaded on demand.

The most distinctive mechanism is the **anti-rationalization table**. Every skill pairs common excuses agents use to skip steps (e.g., "I'll add tests later", "This is simple enough to skip the spec") with documented counter-arguments. This prevents the agent from rationalizing its way out of following the process.

The repo layers three composable constructs:
- **Skills** (`skills/<name>/SKILL.md`) -- workflows with steps and exit criteria. The *how*.
- **Personas** (`agents/<role>.md`) -- roles with a perspective and output format. The *who*.
- **Commands** (`.claude/commands/*.md`) -- user-facing entry points. The *when*.

A governing rule runs throughout: **the user (or a slash command) is the orchestrator. Personas do not invoke other personas.** The only multi-persona orchestration endorsed is parallel fan-out with a merge step (used by `/ship` to run `code-reviewer`, `security-auditor`, and `test-engineer` concurrently).

## 2. Architecture & Core Modules

**Project structure:**
```
agent-skills/
├── skills/                            # 23 skills (22 lifecycle + 1 meta)
│   ├── using-agent-skills/            # Meta-skill: discovery flowchart
│   ├── interview-me/                  # Define: extract user intent
│   ├── idea-refine/                   # Define: divergent/convergent thinking
│   ├── spec-driven-development/       # Define: PRD before code
│   ├── planning-and-task-breakdown/   # Plan: decompose into verifiable tasks
│   ├── incremental-implementation/    # Build: thin vertical slices
│   ├── test-driven-development/       # Build: Red-Green-Refactor
│   ├── context-engineering/           # Build: right context at right time
│   ├── source-driven-development/     # Build: verify against official docs
│   ├── doubt-driven-development/      # Build: adversarial fresh-context review
│   ├── frontend-ui-engineering/       # Build: components, a11y, state
│   ├── api-and-interface-design/      # Build: contract-first
│   ├── browser-testing-with-devtools/ # Verify: Chrome DevTools MCP
│   ├── debugging-and-error-recovery/  # Verify: reproduce-localize-fix-guard
│   ├── code-review-and-quality/       # Review: five-axis review
│   ├── code-simplification/          # Review: Chesterton's Fence
│   ├── security-and-hardening/        # Review: OWASP Top 10
│   ├── performance-optimization/      # Review: measure-first
│   ├── git-workflow-and-versioning/   # Ship: trunk-based, atomic commits
│   ├── ci-cd-and-automation/          # Ship: Shift Left, quality gates
│   ├── deprecation-and-migration/     # Ship: code-as-liability
│   ├── documentation-and-adrs/        # Ship: document the why
│   └── shipping-and-launch/           # Ship: pre-launch checklists
├── agents/                            # 3 specialist personas
│   ├── code-reviewer.md               # Senior Staff Engineer
│   ├── security-auditor.md            # Security Engineer
│   └── test-engineer.md              # QA Engineer
├── references/                        # 4 supplementary checklists
│   ├── testing-patterns.md
│   ├── security-checklist.md
│   ├── performance-checklist.md
│   └── accessibility-checklist.md
├── hooks/                             # Session lifecycle hooks
│   ├── hooks.json                     # Registers session-start hook
│   ├── session-start.sh               # Injects meta-skill into every session
│   ├── sdd-cache-pre.sh / -post.sh    # HTTP cache for source-driven dev (ETag/304)
│   └── simplify-ignore.sh             # Exclusion mechanism for code-simplify
├── .claude/commands/                  # 7 slash commands
├── .gemini/commands/                  # Gemini CLI command ports
└── docs/                              # Setup guides for 7 platforms
```

**Entry points:**
- `hooks/hooks.json` -- SessionStart hook registrations; triggers `session-start.sh`
- `.claude/commands/*.md` -- 7 slash commands (`/spec`, `/plan`, `/build`, `/test`, `/review`, `/code-simplify`, `/ship`)
- `agents/` -- Auto-discovered by Claude Code when repo is installed as a plugin

**Data flow:**
1. Session starts -> `session-start.sh` fires -> meta-skill (`using-agent-skills/SKILL.md`) injected into context as `IMPORTANT` priority system message
2. User makes a request -> agent runs meta-skill decision tree to find matching skill
3. Agent loads that skill's `SKILL.md` -> follows step-by-step workflow -> invokes sub-skills as needed
4. For `/ship`: main agent issues 3 parallel Agent calls (code-reviewer, security-auditor, test-engineer) -> collects reports -> merges into go/no-go + rollback plan
5. For SDD: transparent HTTP cache hooks intercept `WebFetch` calls, sending `If-None-Match`/`If-Modified-Since`; origin `304` responses serve cached content

**Patterns:**
- **Progressive disclosure**: SKILL.md is always <300 lines; supporting references loaded only when needed
- **Process over prose**: numbered steps, checkpoints, exit criteria -- not reference docs
- **Anti-rationalization**: every skill includes an excuse/rebuttal table
- **Verification is non-negotiable**: every skill ends with evidence requirements (tests passing, build output, runtime data)
- **Token-conscious**: descriptions are designed to be injectable into system prompts; every section must justify its inclusion

## 3. Performance/Benchmarks

This is a documentation/skill-definition project with no executable code, so there are no traditional performance benchmarks. Measurable properties:

- **23 skills** across 6 lifecycle phases (Define, Plan, Build, Verify, Review, Ship)
- **~6,450 total lines** of skill content across all `SKILL.md` files
- **~200-390 lines per skill** (mean ~280), fitting under the 500-line budget for single-shot loading
- **4 references** (testing, security, performance, accessibility checklists)
- **3 agent personas** (code-reviewer, security-auditor, test-engineer)
- **7 slash commands** (spec, plan, build, test, review, code-simplify, ship)
- **1 CI workflow** (`.github/workflows/test-plugin-install.yml`)
- **1 hook test** (`hooks/session-start-test.sh`) with 100% coverage of hook behavior

The only measurable performance concern is token budget: each skill is designed so the entire `SKILL.md` fits in one load without exceeding context. The SDD cache hook (`SDD-CACHE.md`) targets a specific token-saving use case (repeated `WebFetch` calls across sessions) with a documented cache-hit rate improvement (no numbers provided, but the mechanism is sound: ETag/304 revalidation avoids re-downloading unchanged docs).

## 4. Trade-offs

**Wins:**
- **Anti-rationalization tables are a genuinely novel contribution.** No other agent skill repo (that I have seen) systematically addresses the problem of agents rationalizing their way out of following instructions. This is directly transferable.
- **Progressive disclosure saves context.** Descriptions are designed for system-prompt injection at 50-100 tokens each; full skills load only when the decision tree matches.
- **Layered architecture prevents scope creep.** Skills, personas, and commands have separate jobs with hard composition rules. The "personas do not invoke other personas" rule prevents the chain-of-orchestrator anti-pattern.
- **Platform-agnostic.** Skills are plain Markdown and work with Claude Code, Cursor, Copilot, Gemini CLI, Windsurf, OpenCode, Kiro, and any agent that accepts instruction files.
- **SDD cache hook is elegant engineering.** HTTP conditional requests (`If-None-Match`/`If-Modified-Since`) guarantee freshness without a TTL -- the origin server decides whether content is stale, not a heuristic.

**Losses / Limitations:**

1. **No executable code in most skills.** The vast majority of skills are pure instruction Markdown. Only hooks and the SDD cache have executable scripts. This means the repo cannot be tested for correctness beyond YAML frontmatter validation and hook smoke tests.

2. **No empirical validation of skill effectiveness.** The README claims skills "encode hard-won engineering judgment" and "bake in best practices from Google's engineering culture," but there are no metrics showing that agents using these skills produce better outcomes than agents without them.

3. **Context injection relies on a specific hook mechanism.** The session-start hook (`hooks/hooks.json` -> `session-start.sh`) injects the meta-skill only on Claude Code. On other platforms (Cursor, Copilot), users must copy files manually. The `.gemini/commands/` directory exists but has limited content.

4. **No build/package system.** There's no `package.json`, `gemfile`, or `Cargo.toml`. The only dependencies are `jq`, `curl`, `shasum`, and Bash 3.2+ (for hooks). This is fine for a doc project but means there is no version management, no dependency audit, and no semantic versioning.

5. **No formal issue tracker or CHANGELOG in the repo.** The README links to GitHub issues, but there is no CHANGELOG.md or release notes. The `CONTRIBUTING.md` references "open an issue if you find..." but there are no documented design decisions or known issues _in the repo_.

6. **SDD cache has a subtle blind spot.** As documented in `SDD-CACHE.md`: "Body is prompt-shaped" -- cached content reflects the first agent's reading of the page with a specific prompt. Reusing it for a different prompt may give misleading results. The cache displays the original prompt as metadata, but cannot auto-invalidate on prompt mismatch.

7. **doubt-driven-development skill cannot run nested.** The skill explicitly warns (in "Loading Constraints") that it cannot operate from inside a subagent context because Claude Code prevents nested subagent spawns. This limits its practical use to top-of-session orchestration.

## 5. Design Rationale

The repo's design is rooted in a specific diagnosis: **"AI coding agents default to the shortest path -- which often means skipping specs, tests, security reviews, and the practices that make software reliable."** Every design decision follows from this.

**Why Markdown, not code:** Skills are instructions for agents, not libraries for humans. Markdown is the lowest-friction format that all coding agents can consume. Writing in code (YAML, JSON, TypeScript) would tie the project to a specific harness or require a build step.

**Why anti-rationalization tables:** The author identified that agents are especially prone to rationalizing away from process steps ("this is simple enough to skip the spec"). The tables directly counter this by pre-loading rebuttals. This is a behavioral design pattern, not a technical one.

**Why the user-is-orchestrator rule:** Preventing personas from invoking other personas avoids the router-agent anti-pattern (which adds latency, token cost, and information loss). The `orchestration-patterns.md` reference explicitly identifies four anti-patterns with documented failure modes (router persona, persona-calls-persona, sequential orchestrator, deep persona trees).

**Why progressive disclosure:** Token budgets are finite. The meta-skill's description (loaded every session) is ~200 words. Full skills (200-390 lines) load only when matched. References load only when the skill references them. This keeps the active context lean.

**Why SDD cache uses ETag/304 instead of TTL:** The `source-driven-development` skill's value is "verify against _current_ official docs." A TTL-based cache would contradict this guarantee by serving potentially stale content. Using HTTP conditional revalidation delegates freshness authority to the origin server -- the same server that published the docs.

**Why /ship uses parallel fan-out:** Three independent perspectives (code quality, security, test coverage) on the same diff produce better results when each perspective has its own context window and no shared state. Parallel execution reduces wall-clock latency vs. sequential. The merge step is small enough to stay in the main context.

**References to Google engineering culture:** The README explicitly cites "Software Engineering at Google" and Google's engineering practices guide. Concepts like Hyrum's Law, the Beyonce Rule, Chesterton's Fence, trunk-based development, and Shift Left are embedded directly into skill steps.

## 6. Transfer to Lyra

**Transferable idea: Anti-rationalization tables for Lyra verification**

The single most transferable pattern from `agent-skills` is the **anti-rationalization table**. Lyra already has a verification system (per plans §3.x and §4.x), but it relies on the agent's good faith to follow verification steps. An anti-rationalization table would pre-emptively block common excuses:

| Rationalization | Reality |
|---|---|
| "I ran the tests locally, they pass" | Local != CI. Trigger the CI pipeline and verify the green check. |
| "The change is too small to need verification" | The smallest changes cause the most production incidents (see: one-character typos, wrong import paths). |
| "I manually checked the output" | Manual checks are not reproducible. Write a test or a script. |
| "The code compiles, it must be right" | Compilation proves syntax, not correctness. A passing test suite is the minimum bar. |

This could be added to Lyra's verification skill as a new section, with zero code changes and minimal token cost (~50-80 lines).

**Secondary transfer: Progressive-disclosure skill loading.** Lyra's skill system (if it evolves one) should follow the same pattern: a lightweight meta-skill for discovery, individual skills for each workflow, references loaded on demand. This avoids the problem of loading all 20+ skills into every session context.

**Tertiary transfer: The SDD cache pattern (HTTP conditional revalidation).** If Lyra fetches external documentation (for source-driven development or similar), an ETag-based cache hook would save repeated fetches without sacrificing freshness. The complete design (including debug logging, freshness rules, and local testing instructions) is documented in `SDD-CACHE.md` and can be adapted directly.

**Workstream route:**
- Primary: **§4.2 Agent behavior & skills system** -- anti-rationalization tables are a natural fit for Lyra's skill/verification architecture
- Secondary: **§4.3 Verification system** -- the verification checklist pattern from every skill (always tests/build/evidence, never "seems right")

**Impact:** Medium -- anti-rationalization tables address a real failure mode (agents skipping verification) with essentially zero implementation cost

**Effort:** Low -- adding an anti-rationalization table to existing Lyra verification plans is a documentation-only change, ~1-2 hours for initial integration, potentially extensible over time

**Tier:** Tier 2 (targeted improvement to an existing subsystem)
