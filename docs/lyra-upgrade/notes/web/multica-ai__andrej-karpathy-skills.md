# multica-ai/andrej-karpathy-skills — Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** A single CLAUDE.md file encoding Andrej Karpathy's four behavioral principles for reducing common LLM coding mistakes (overcomplication, silent assumptions, drive-by refactoring, vague success criteria).

**How it really works:** The repo is not a runtime library — it is a **prompt injection** overlay for Claude Code (and Cursor). It ships the same content in four equivalent forms:

- `CLAUDE.md` -- per-project behavioral instructions that Claude Code reads as system context.
- `skills/karpathy-guidelines/SKILL.md` -- a reusable Claude Code skill, installable via the plugin marketplace.
- `.cursor/rules/karpathy-guidelines.mdc` -- a Cursor project rule with `alwaysApply: true`.
- `.claude-plugin/plugin.json` + `marketplace.json` -- packaging for the Claude Code plugin marketplace.

The mechanism is purely behavioral: the four principles live in the agent's system prompt (via CLAUDE.md) and bias its reasoning during every tool call. There is no executable code, no runtime enforcement, no automated checks. It is a **nudge architecture** that relies on the LLM's ability to follow instructions embedded in its context window.

## 2. Architecture & Core Modules

Since this is a prompt-only repository with zero source code, the "modules" are the four canonical files, each carrying the same semantic payload in a different delivery format:

| File | Format | Target Platform | Lines |
|------|--------|-----------------|-------|
| `CLAUDE.md` | Plain Markdown | Claude Code (per-project `CLAUDE.md`) | 65 |
| `skills/karpathy-guidelines/SKILL.md` | YAML-frontmatter Markdown | Claude Code Skill Library | 67 |
| `.cursor/rules/karpathy-guidelines.mdc` | MDC with `alwaysApply: true` | Cursor project rules | 70 |
| `EXAMPLES.md` | Extended Markdown showcase | Human documentation | 522 |
| `.claude-plugin/plugin.json` | JSON | Claude Code plugin marketplace | 12 |
| `.claude-plugin/marketplace.json` | JSON | Plugin listing metadata | 28 |

**Data flow:** There is none. The content is static and read once at agent initialization. The four principles are:

1. **Think Before Coding** -- surface assumptions, present multiple interpretations, push back on bad requests, stop when confused.
2. **Simplicity First** -- minimum code, no speculative features or abstractions, no error handling for impossible scenarios.
3. **Surgical Changes** -- touch only what the user asked for, match existing style, clean up only your own orphans.
4. **Goal-Driven Execution** -- transform imperative tasks into verifiable goals with explicit checkpoints: `[Step] -> verify: [check]`.

**Pattern:** Single-file prompt injection. The entire "architecture" is a flat markdown document that acts as behavioral guardrails. The cross-platform consistency (Claude Code plugin, Cursor rule, standalone skill) is the only structural complexity.

## 3. Performance/Benchmarks

**No quantitative benchmarks exist in this repository.** The repo provides qualitative success signals only:

- "Fewer unnecessary changes in diffs"
- "Fewer rewrites due to overcomplication"
- "Clarifying questions come before implementation, not after mistakes"
- "Clean, minimal PRs"

These are observational heuristics described in the README, not measured metrics. There are no test suites, no CI benchmarks, and no empirical evaluation. The repo's value proposition is asserted from Karpathy's authority and the author's experience, not from controlled experiments.

## 4. Trade-offs

**Wins:**
- Extremely low overhead: a single CLAUDE.md file, ~65 lines, zero dependencies.
- Works cross-platform (Claude Code, Cursor) with no code changes.
- Addresses a real and well-documented failure mode of LLM code generation (overcomplication, silent assumptions).
- The verification-loop pattern in "Goal-Driven Execution" is directly applicable to any agent-loop architecture.
- MIT license means zero friction for adoption.

**Losses:**
- **No enforcement.** The guidelines are purely advisory -- the LLM can ignore them at any time. There is no linter, no compile-time check, no test that proves compliance.
- **No empirical validation.** Every claim about effectiveness is anecdotal. There are no published A/B tests, user studies, or benchmark results.
- **Tradeoff explicitly acknowledged:** bias toward caution over speed. For trivial tasks, the full rigor is unnecessary overhead.
- **Single point of failure.** If the CLAUDE.md is not loaded (e.g., from a different tool, or a corrupted file), the behavioral guardrails disappear entirely.
- **Context window cost.** 65 lines of instructions consume context on every turn, which adds up over long sessions -- though negligible in practice.

**Design decisions visible in code/documentation:**
- The CLAUDE.md is designed to be *merged* (appended to existing CLAUDE.md), not to replace it -- implying composability.
- The four principles are deliberately kept terse (65 lines) to avoid diluting the core message with too much detail.
- EXAMPLES.md is kept separate from CLAUDE.md, meaning the behavioral instructions stay focused while examples are available as reference.

## 5. Design Rationale

The repo is grounded in Andrej Karpathy's public observation (X post, 2025) about three systematic LLM coding failures:
1. Wrong assumptions executed silently.
2. Overcomplication and bloat.
3. Side-effect edits to unrelated code.

The solution treats each failure as a **prompt engineering** problem rather than a **tooling** problem. The reasoning:

- **Prompt over linter.** Rather than building a static analysis tool that detects overcomplication (which is context-dependent and hard to define formally), the approach embeds behavioral norms into the agent's own reasoning loop.
- **Conciseness over completeness.** The CLAUDE.md is only 65 lines because the author wanted it to fit in a single screen and be easily memorized by the LLM. Longer guidelines dilate the effective context.
- **Verification as a first-class concept.** The "Goal-Driven Execution" principle transforms tasks from imperative ("fix the bug") to declarative ("write a test that reproduces it, then make it pass"). This leverages the LLM's strength: looping until a test passes is a well-defined optimization loop.
- **Cross-platform by necessity, not design.** The plugin.json and cursor rules exist because users wanted the guidelines in multiple tools, not because the author set out to build a multi-platform system.

The repo is a **minimal viable prompt** -- it adds exactly the right amount of behavioral structure to make LLM outputs more disciplined, without adding enough overhead to slow down trivial work.

## 6. Transfer to Lyra

**The one idea:** Adopt the **verifiable checkpoint pattern** from Goal-Driven Execution into Lyra's plan step representation. Currently Lyra's plans express tasks as imperative steps ("Add validation", "Fix the bug"). By adding an optional `verify` field to each plan step -- a concrete, machine-checkable goal -- Lyra's executor agent can run autonomously without clarification loops.

Specifically:
```yaml
# Current Lyra plan step (imperative):
- step: Add rate limiting to /api/search

# Lyra plan step with Goal-Driven Execution (declarative):
- step: Add rate limiting to /api/search
  verify: "curl /api/search 11 times in 1s -> first 10 return 200, 11th returns 429"
```

This lets the executor judge its own completion, loop on failure, and escalate only on persistent failure.

**Workstream route:** **§4.1 -- Plan Representation.** Add an optional `verify` string field to Lyra's `PlanStep` schema. The executor checks the verify condition after implementing the step. No runtime changes needed -- the verify field is consumed by the executor's self-verification loop, not the plan compiler.

**Impact: 6** -- Medium-high. Dramatically improves executor autonomy and reduces human-in-the-loop clarifications. Especially valuable for multi-step plans where each step must be independently correct before the next starts.

**Effort: 1** -- Trivial. A schema addition (~20 lines) and executor-side verification logic (~50 lines). No dependency changes, no breaking schema change (verify is optional).

**Tier: Quick Win** -- Can be implemented in a single PR. The conceptual overhead is near zero because the pattern is already in common use informally.

**License:** MIT -- full compatibility with any Lyra license.

---

**File:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/web/multica-ai__andrej-karpathy-skills.md`
