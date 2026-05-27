# Lyra Block 08 — SOUL.md (Persona Partition)

The "persona partition" is SemaClaw's most under-appreciated contribution: a separately-maintained, **never-auto-compacted** file that defines the agent's behavioral contract with the user. In Lyra this is `SOUL.md`. It is short, human-editable, always loaded into L2 context, and versioned alongside the repo.

Reference: [SemaClaw SOUL.md](../../../../docs/54-semaclaw-general-purpose-agent.md), OpenClaw's agent templates in [`docs/52`](../../../../docs/52-dive-into-open-claw.md).

## Why a persona partition

Long sessions drift. The model forgets "you prefer functional components", "never commit to main directly", "this codebase uses pytest not unittest". Compaction makes the drift worse: the earliest pinned principles are often the first summaries to lose nuance.

A persona partition:

- Is *always* loaded, never compacted.
- Is *user-editable* — the single source of truth for behavioral expectations.
- Is *small* by design — a cap forces the user to keep it essential.
- Is *diffable* — the user sees exactly what changed in the contract.

It is the simplest solution to the most common long-session failure.

## Size cap

Default: 2,000 tokens (~8 KB of text). Hard cap: 4,000 tokens. A larger SOUL is a smell — either duplicates a skill body or encodes project-specific rules that belong in a skill or hook.

## Structure

```markdown
# SOUL

## Identity
I am Lyra, a CLI-native coding partner. I help ship small, correct changes
traced to user intent. When the optional TDD plugin is enabled, I back every
change with a failing test first; when it isn't, I still favour clear,
test-friendly code but I don't refuse to act without a RED proof.

## Core principles
1. **Think Before Coding.** No mutation until I understand what success looks like.
2. **Simplicity First.** Minimum viable change, then refine.
3. **Surgical Changes.** Touch only what the plan names.
4. **Goal-Driven Execution.** Every line I change traces to a plan item, which traces to a user task. With the TDD plugin enabled, also to a failing test.

## Conventions (this project)
- Test runner: pytest with `-p no:cacheprovider -q -x`.
- Package manager: uv.
- Formatter: ruff format.
- Type checker: mypy --strict for new modules.
- Commits: conventional-commits.

## User preferences
- Prefers explicit over clever.
- Writes comments only when the *why* is non-obvious.
- Never uses `# type: ignore` without reason.

## Hard rules
- Never commit directly to `main`.
- Never add dependencies without user approval.
- Never disable tests to "make the suite green".
```

Sections are conventional but not hard-required. The parser treats SOUL as free-form Markdown; the harness only enforces the size cap and the ban on auto-compaction.

## Default vs repo-level SOUL

Three precedence levels:

1. **Built-in default.** Ships with Lyra in `lyra/assets/soul.default.md` — contains the four Karpathy principles + generic TDD contract.
2. **User-global.** `~/.lyra/memory/SOUL.md` — user's personal SOUL applied to all repos.
3. **Repo-scoped.** `<repo>/.lyra/memory/SOUL.md` — overrides user-global for this repo.

The built-in default (shipped at `lyra/assets/soul.default.md`) was rewritten in v3.0.0 to drop the "TDD-first" framing in favour of language that lights up only when the optional TDD plugin is enabled — see the **Default SOUL (shipped)** snippet below.

Merge: if all three present, rendered as (repo overrides user overrides default). Override granularity is section-level (by H2 headings).

## Editing workflow

```
lyra soul edit                    # opens $EDITOR on the effective SOUL
lyra soul cat                     # prints rendered effective SOUL
lyra soul revert                  # revert to last committed version
lyra soul diff                    # show change since session start
lyra soul --global edit           # edits ~/.lyra/memory/SOUL.md
lyra soul --default               # print the default that ships
```

`soul edit` commits the change to the repo (session-branch) automatically so history is retained.

## Integrity guarantees

1. **Never auto-compacted.** Context Engine's compactor explicitly skips SOUL messages.
2. **Hash pinned at session start.** Session record stores `soul_revision = sha256(rendered_soul)`. If SOUL changes mid-session, a `soul.drift` trace event is emitted and the new hash is recorded; optionally, the user is prompted to confirm.
3. **Diffable.** Every change is a git commit; `lyra soul diff` shows inter-session drift.
4. **Read-only to LLM.** No tool writes to SOUL.md without explicit user action (`soul edit`). The agent may *suggest* edits in conversation but cannot apply them.

## Identity-drift detection

A continuous check (run in the [safety monitor](12-safety-monitor.md) sidecar):

- Sample the agent's recent behaviors from the trace.
- Compare to the SOUL contract using a small classifier (or prompt-based judge).
- On large divergence, emit `soul.drift` span with evidence.

This is not a block (SOUL is advisory for the model), but a diagnostic. High drift triggers the retrospective in `lyra retro` to include a prompt for SOUL review.

## Forcing questions (Karpathy-aligned)

SOUL includes an optional `## Forcing questions` section that the harness injects at key moments:

```markdown
## Forcing questions
When starting a task:
- What is the smallest change that could make a failing test pass?
- Is there already a test for this behavior?
- Am I creating a new abstraction too early?

When about to commit:
- Does every changed line trace to the plan?
- Is my commit message the "why" not the "what"?
```

The planner and evaluator can cite forcing questions in their outputs, creating an explicit link between SOUL principles and runtime behavior.

## Default SOUL (shipped)

```markdown
# SOUL (default)

## Identity
I am a CLI-native coding partner. I prefer correctness, traceability, and simplicity. When the optional TDD plugin is enabled, I write the failing test first; otherwise I still favour test-friendly code but I act on intent rather than proof.

## Core principles
1. Think Before Coding — understand the goal before mutating.
2. Simplicity First — minimum viable code to satisfy the goal.
3. Surgical Changes — touch only files named in the plan.
4. Goal-Driven Execution — every change traces to a plan item; with the TDD plugin enabled, also to a failing acceptance test.

## Forcing questions
- Do I understand the goal? Have I named the smallest change that satisfies it?
- Is this the simplest change? Could it be smaller?
- Does this change a file that was not in the plan? If so, does the plan need updating?
- (TDD plugin on) Is there a failing test justifying this change? If not, write it first.

## Defaults
- Ask before adding dependencies.
- Ask before touching CI config.
- Never commit to main; open a branch.
- Never disable tests or coverage to pass a gate.
```

## Relationship to skills

SOUL says *what I am*; skills say *how to do things*. Do not put procedures in SOUL; do not put persona in skills. If a rule appears in both, SOUL wins (identity is the anchor).

## Failure modes and defenses

| Mode | Defense |
|---|---|
| SOUL grows to thousands of tokens, stealing context budget | Hard cap + warning + suggestion to move content to a skill |
| SOUL contradicts a skill it enables | Lint at load: skills reference SOUL sections; lint fails on contradictions |
| SOUL leaks private info (user names, keys) in export | Redactor checks before `mem export` |
| User edits SOUL mid-session, confusing the agent | `soul.drift` event; optional pause-for-confirm |
| SOUL becomes "magic" — agent appears to not honor it | Identity-drift detector + evaluator considers SOUL-alignment in rubric |
| SOUL unavailable (file deleted) | Harness falls back to default SOUL; warns user |

## Metrics emitted

- `soul.tokens` gauge
- `soul.edits.count` labeled by scope (repo|user)
- `soul.drift.score` gauge
- `soul.drift.flags.total`
- `soul.forcing_questions.injections.total`

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_soul_persistence.py` | Precedence merging, hash pinning |
| Unit `test_soul_cap.py` | Size enforcement |
| Unit `test_soul_drift.py` | Drift detector on sample traces |
| Integration | Long session maintains SOUL untouched under compaction |
| Property | Cap is inclusive; rendering is deterministic |

## Open questions

1. **Multiple personas per session.** e.g. a "security-reviewer" persona for review steps. v2 may support overlay personas.
2. **SOUL diff as retro input.** Should SOUL changes become a retro discussion topic automatically?
3. **Team SOUL.** v2 team mode: workspace-level SOUL overriding user.
4. **Language of SOUL.** Users writing non-English SOUL; model behavior should carry through — needs evaluation.
