# forrestchang/andrej-karpathy-skills -- Deep-Read

**URL:** https://github.com/forrestchang/andrej-karpathy-skills
**Cloned:** 2026-06-07

## 1. Headline Feature & Mechanism

**Headline:** A distributable CLAUDE.md (and Cursor .mdc rule) encoding Andrej Karpathy's 4 anti-failure principles for LLM code generation. It is a single-file behavioral prompt, not a tool or runtime.

**Mechanism (how it really works):** The repo contains exactly 4 pages of instructions (the CLAUDE.md file) that are injected into the LLM's system prompt via Claude Code's plugin marketplace or Cursor's project rules. The mechanism is purely prompt-engineering: it alters the model's priors at inference time toward caution, explicitness, and minimalism. There is no code execution, no enforcement, no verification loop -- the LLM is simply told how to behave and trusted to comply.

The four principles:

1. **Think Before Coding** -- Forces explicit assumption surfacing and ambiguity resolution before emitting code. Targets Karpathy's observation that LLMs "make wrong assumptions on your behalf and just run along."
2. **Simplicity First** -- Bans speculative abstractions, premature flexibility, error-handling for impossible scenarios. Targets the "1000 lines when 100 would do" failure.
3. **Surgical Changes** -- Prohibits touching adjacent code, changing style, or refactoring unrelated code during a task. Each changed line must trace to the user's request. Targets "change/remove code they don't sufficiently understand as side effects."
4. **Goal-Driven Execution** -- Transforms imperative tasks ("fix the bug") into verifiable criteria ("write test that reproduces it, then make it pass"). Exploits the property that LLMs loop effectively when given clear pass/fail signals.

The code examples in EXAMPLES.md (the actual "source code" of the repo) show before/after diffs that are the real deliverable. They demonstrate concretely what each principle looks like in practice.

## 2. Architecture & Core Modules

The repo has no runtime architecture. Its "modules" are distribution formats for the same content:

| Module | Format | Purpose |
|--------|--------|---------|
| `CLAUDE.md` | Markdown | Per-project instruction file (curl into any project root) |
| `.cursor/rules/karpathy-guidelines.mdc` | Markdown + YAML frontmatter | Cursor project rule with `alwaysApply: true` |
| `skills/karpathy-guidelines/SKILL.md` | Markdown + YAML frontmatter | Reusable Cursor skill (copy to `~/.cursor/skills/`) |
| `.claude-plugin/plugin.json` | JSON | Claude Code plugin definition (name, version, license, skill path) |
| `.claude-plugin/marketplace.json` | JSON | Marketplace listing metadata for plugin distribution |
| `EXAMPLES.md` | Markdown | 8 real-world before/after examples (the intellectual core) |
| `CURSOR.md` | Markdown | Cross-editor setup guide |
| `README.md` / `README.zh.md` | Markdown | Project documentation (English + Chinese) |

**Data flow:** README -> user runs `/plugin install andrej-karpathy-skills@karpathy-skills` or copies CLAUDE.md -> content enters LLM context on every request -> principles shape model behavior. That is the entire data path.

**Pattern:** Prompt-as-config. The repo is a "behavioral config" for an LLM, not software. The distribution mechanism (plugin marketplace) is the novel part -- treating prompt files like npm packages.

## 3. Performance/Benchmarks

No quantitative benchmarks exist in this repo. The README lists four qualitative indicators of success:

- Fewer unnecessary changes in diffs
- Fewer rewrites due to overcomplication
- Clarifying questions come before implementation, not after mistakes
- Clean, minimal PRs (no drive-by refactoring)

These are anecdotal, not measured. There are no test suites, no A/B evaluation, no comparison against baseline CLAUDE.md behavior. The repo relies entirely on the persuasiveness of Karpathy's authority and the intrinsic reasonableness of the principles.

## 4. Trade-offs (Wins vs Losses)

**Wins:**

- **Extremely low friction:** 300 words, single file, no dependencies, no API, no build step. Can be adopted in 10 seconds via `curl`.
- **Targets the highest-cost failures:** Assumption blindness, overengineering, and side-effect edits are the most expensive modes of LLM coding failure (wasted context window, wasted review time, regressions).
- **Dual-platform:** Works identically on Claude Code and Cursor, with a distribution path (plugin marketplace) that enables versioning.
- **Composable:** Explicitly designed to merge with project-specific rules.
- **Chinese translation:** README.zh.md doubles the accessible audience.

**Losses:**

- **No enforcement mechanism:** The LLM is told to behave but cannot be compelled. A model that ignores the instructions (or one with weaker instruction-following) gets no benefit.
- **Biased toward caution over speed** (explicitly acknowledged): For trivial tasks, the guidelines introduce overhead. The README tells users to "use judgment" but provides no decision heuristic for when to skip.
- **No tooling:** Unlike Lyra or similar agent frameworks, there is no actual enforcement (no diff-checking tool, no pre-commit hook, no post-generation validation step).
- **No versioning/changelog:** The plugin has version 1.0.0 but no CHANGELOG or release history. The repo has no issues, no PRs, no commit history beyond the initial push.
- **No tests:** The guidelines themselves are untested. There is no way to verify that a given generation conformed to the principles.
- **Single point of truth:** Maintaining sync across CLAUDE.md, .cursor/rules/, and SKILL.md requires manual discipline (noted in CURSOR.md).

## 5. Design Rationale

The design follows directly from Karpathy's diagnosed failure modes. Each principle is a direct countermeasure:

| Failure Mode (Karpathy) | Principle Countermeasure |
|------------------------|------------------------|
| "Make wrong assumptions on your behalf" | Think Before Coding: state assumptions explicitly |
| "Don't present tradeoffs" | Think Before Coding: surface multiple interpretations |
| "Overcomplicate code and APIs" | Simplicity First: ban speculative abstraction |
| "Bloat abstractions" | Simplicity First: no abstractions for single-use |
| "Change/remove code they don't understand" | Surgical Changes: touch only what the task requires |
| "Don't clean up dead code" | Surgical Changes: clean only your own orphans |
| "Good at looping toward goals" | Goal-Driven Execution: exploit this with verifiable criteria |

The key structural decision is **single-file distribution** rather than a tool or framework. This keeps adoption friction at zero. The plugin marketplace distribution is a secondary innovation -- it turns a prompt file into a "package" with version metadata, enabling discovery and installation via `/plugin install`.

The examples in EXAMPLES.md are the real design artifact. They concretize each principle by showing the "overengineered LLM default" versus the "surgical, simple" alternative. This is more effective than abstract rules alone.

## 6. Transfer to Lyra

**Transferable idea:** Inject Karpathy's "Surgical Changes" principle directly into Lyra's self-modification protocol. When Lyra autonomously modifies its own code, it should run a post-generation validation step that checks:

1. Every changed line in the diff traces to the original task description.
2. No adjacent code, comments, or formatting was changed.
3. The diff does not exceed the minimum viable change.
4. Existing style is preserved (no drive-by type-hint additions, etc.).

This addresses a specific risk in Lyra's autonomous self-improvement loop: the tendency for the agent to accrete dead code, refactor things it doesn't fully understand, or introduce style drift that makes the codebase harder to maintain.

**Workstream route: §4.x (Agent Loop / Self-Modification protocol)** -- add a "diff hygiene" validation step in the agent loop after code generation and before the verification step. The check is lightweight (diff analysis, no model call needed if using `git diff --stat` + basic parsing).

**Impact:** 5/10 (moderate -- prevents subtle code quality degradation over many self-modification cycles)
**Effort:** 2/10 (low -- a simple diff-analysis function + a rule in the agent prompt)
**Tier:** Quick Win (high leverage, minimal cost)

**License:** MIT -- fully compatible with Lyra's permissive open-source model. No restrictions on use, modification, or redistribution.
