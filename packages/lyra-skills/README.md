# lyra-skills

The **skill engine** for Lyra: loader, router, extractor, and the
shipped skill packs. Current as of **v2.7.1** (2026-04-27).

A *skill* is a `SKILL.md` file plus its companion artifacts (templates,
scripts, fixtures). Skills are the unit of *capability* — Lyra teaches
itself by writing them, the user grows the library by curating them,
and the agent loop routes to them by description match. Format is
compatible with Claude Code / OpenClaw skills so packs port both ways.

## What's in here

```
src/lyra_skills/
    loader.py              # discovery from skills/, ~/.lyra/skills/, workspace
    router.py              # description-based routing with confidence gating
    extractor/
        candidate.py       # post-task: is this trajectory worth extracting?
        refiner.py         # Hermes-style refine using outcome signal
        builder.py         # lint + lay out the SKILL.md folder
        promoter.py        # gated promotion to the user library
    packs/
        atomic-skills/     # the five primitives (localize / edit / test-gen / reproduce / review)
        tdd-sprint/        # the seven-phase TDD workflow
        karpathy/          # think-before-coding / simplicity-first / surgical-changes / goal-driven-execution
        safety/            # injection-triage / secrets-triage
```

## Shipped packs (v2.7.1)

| Pack              | Skills                                                                                  |
|-------------------|-----------------------------------------------------------------------------------------|
| `atomic-skills`   | `localize`, `edit`, `test-gen`, `reproduce`, `review`                                   |
| `tdd-sprint`      | `7-phase` (red → focused-test → green → refactor → ship cycle)                           |
| `karpathy`        | `think-before-coding`, `simplicity-first`, `surgical-changes`, `goal-driven-execution`  |
| `safety`          | `injection-triage`, `secrets-triage`                                                    |

Run `lyra skills list` to see everything that's been discovered for
your repo (workspace pack ⊕ user pack ⊕ shipped packs); `lyra skills
show <name>` prints the full SKILL.md.

## Loader / router

Discovery walks three roots in this order (later wins):

1. shipped packs inside the `lyra_skills` wheel;
2. `~/.lyra/skills/` (user-scope, available across repos);
3. `<repo>/skills/` (workspace scope, version-controlled with the repo).

The router uses **description-based matching** (not function-calling
selection) — the SKILL.md frontmatter's `description` field is what
decides which skill loads. v1.7's hybrid router added BM25 + dense
embeddings (BGE-small) on top, with explicit `NO_MATCH` /
`AMBIGUOUS` verdicts when the agent should pause and ask.

```bash
lyra skills route --explain "reproduce issue #234"
# → matches reproduce-skill at confidence 0.83
# → reasoning: BM25 score 12.4, dense 0.71, description-match 0.91
```

## Extractor (post-task self-improvement)

After every completed task, the extractor decides whether the
trajectory should:

* become a **new skill** (novel pattern + good outcome),
* **augment an existing skill** (small refinement),
* be **discarded** (one-off, poor signal, or already covered).

Promotion to the user library is **always gated on user review** —
the extractor opens a PR-shaped `SKILL.md` candidate the user
approves with `lyra skills review`. This is the lesson from
[`docs/04-skills.md`](../../../../docs/04-skills.md#failure-modes):
auto-promote without review is the canonical "skill-spam" failure
mode.

## Testing

```bash
# from projects/lyra/packages/lyra-skills/
uv run pytest -q
```

## See also

* [`projects/lyra/docs/blocks/09-skill-engine-and-extractor.md`](../../docs/blocks/09-skill-engine-and-extractor.md) — the skill-engine contract.
* [`projects/lyra/CHANGELOG.md`](../../CHANGELOG.md) — release log.
