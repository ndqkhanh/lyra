# Lyra Block 09 — Skill Engine and Extractor

Lyra's skill engine has three roles: **Loader** (discover + index), **Router** (select by description), **Extractor** (promote successful trajectories into skills and refine existing ones). The extractor is the engine of continual learning, lifted from [Hermes Agent](../../../../docs/55-hermes-agent-self-improving.md) with coding-specific tuning.

Other references: [SKILL.md format (Claude Code)](../../../../docs/04-skills.md), [Voyager-style skill libraries](../../../../docs/19-voyager-skill-libraries.md), [Atomic Skills arXiv:2604.05013](../../../../docs/68-atomic-skills-scaling-coding-agents.md).

## Responsibility

1. Discover skills at session start from repo/user/global scopes.
2. Present each skill's *name + description* in L2 context (never the body unless invoked).
3. On invocation, load the body + companion files, narrow tool allowlist to `allowed-tools`.
4. After a completed task, evaluate the trajectory for skill-worthiness and either:
    - Create a new skill, or
    - Refine an existing skill with outcome signal (success / partial / fail), or
    - Record a feedback entry without code change.
5. Run a self-evaluation every N completed tasks that prunes stale or underperforming skills.

## Skill format (SKILL.md)

```markdown
---
name: test-gen
description: |
  Use when the user or plan asks to generate unit tests, integration tests,
  or acceptance tests for an existing function/module/component.
allowed-tools: [Read, Grep, Glob, Write, Bash]
author: lyra-atomic
version: 1.2.0
languages: [python, typescript, go]
companion_files: []
introspection:
  examples: 22
  success_rate: 0.88
  last_refined: 2026-04-18
disable-model-invocation: false
---

# Steps

1. Read the target function/module; confirm signature and side effects.
2. Identify the testing framework in use (pytest / vitest / go test / jest).
3. Draft 3–7 tests covering: happy path, edge cases, error paths, idempotency if relevant.
4. Write tests to `tests/` mirroring the source structure.
5. Run the focused test subset; if any fail unexpectedly, report and stop.

## Anti-patterns
- Do not disable existing tests to make new ones pass.
- Do not add dependencies (libraries) without asking.
- Do not over-mock; prefer real integration where cheap.

## Cross-references
- See SOUL: Simplicity First principle for test complexity.
- Failed attempts: skills/../feedback/test-gen.md (entries #3, #7)
```

Format is the standard `SKILL.md` convention used in Claude Code, Multica, gstack, OpenClaw. `introspection` block is Lyra-specific and auto-maintained.

## Discovery

On session start, Loader scans (in precedence order):

1. Repo-scoped: `.lyra/skills/*/SKILL.md`
2. User-global: `~/.lyra/skills/*/SKILL.md`
3. Plugin-bundled: `lyra_plugins/*/*/SKILL.md`

Collisions resolved by narrower scope winning. Each skill is indexed by name → description. Router builds a prompt-visible list:

```
Available skills:
  - test-gen: Use when the user or plan asks to generate unit tests…
  - localize: Use when needing to identify call sites / referencing code…
  - red: TDD red phase: write a failing test before implementation.
  - review: Senior-engineer code review; flag issues; do not propose code.
  - …
```

## Invocation

The `Skill` tool:

```python
@tool(name="Skill", writes=False, risk="low")
def invoke_skill(name: str, args: dict = {}) -> str: ...
```

On invocation:

1. Loader fetches body + companion files.
2. PermissionBridge narrows allowed tools to the skill's `allowed-tools` for the duration.
3. Body injected as a system message addendum; agent resumes reasoning within that scope.
4. On skill completion (agent returns to higher-level plan), the allowlist restores, and the skill body is evicted (stays in transcript as a summary reference).

Skill-invoked-by-slash-command bypasses the routing decision: `/test-gen authenticate.ts` forcibly invokes the skill with those args.

## Shipped skill packs (v1)

### `atomic-skills/` (5 skills; Atomic Skills paper alignment)

1. **`localize`** — find call sites, trace definitions, map dependency graphs.
2. **`edit`** — apply surgical edits; unique-match `Edit` discipline.
3. **`test-gen`** — write unit / integration / behavior tests.
4. **`reproduce`** — produce a minimal failing repro for reported issues.
5. **`review`** — identify issues without proposing fixes; structured verdict.

### `tdd-sprint/` (7 skills; gstack 7-phase sprint inspired)

`think` → `plan` → `red` → `green` → `refactor` → `ship` → `retro`. Each step's invariants enforced by the permission-mode transition it induces.

### `karpathy/` (1 skill)

One SKILL.md containing the four principles as forcing questions, invoked when SOUL indicates use.

### `safety/` (2 skills)

- `cso`: OWASP Top 10 + STRIDE sweep of recent changes.
- `red-team`: LaStraj-style adversarial prompt construction for testing own guards.

## Skill extractor loop (Hermes pattern)

Triggered on `SESSION_END` with status `completed`:

```python
def extract_skills(session: Session):
    trajectory = load_trajectory(session)
    candidate = skill_candidate_classifier.analyze(trajectory)
    if not candidate.is_skill_worthy:
        return

    existing = skills.search_by_description(candidate.description)
    if existing:
        refiner.apply_feedback(existing, outcome=candidate.outcome,
                               trajectory_delta=candidate.delta_notes)
        tracer.event("skill.refined", hir="skill_invocation",
                     skill=existing.name, outcome=candidate.outcome)
    else:
        new_skill = builder.synthesize(candidate)
        skills.write(new_skill, scope="user")
        tracer.event("skill.created", hir="skill_invocation",
                     skill=new_skill.name)
```

### Candidate classifier

Fast heuristic + LLM prompt:

- Trajectory length within range (3-20 steps).
- Outcome was success (evaluator accept, no regressions).
- Actions cohere into a recognizable pattern (not one-off).
- Description has a plausible trigger shape.

Users can ask to promote manually: `lyra skills promote --session <id>`.

### Refiner

Reads existing skill + outcome + delta notes. Produces a patch to the SKILL.md body using the skill refinement prompt: *"What worked this time that wasn't in the body? What went wrong that we should warn about?"*. Emits a diff the user can review via `lyra learn review`.

### Builder

For new skills, the builder synthesizes name, description, allowed-tools, steps, and anti-patterns from the trajectory narrative. It runs a linter on the output (description must be a "use when" statement; allowed-tools must be minimal; no global `*`).

## Self-evaluation (every 15 tasks)

A heavier audit runs after N completed tasks (configurable, default 15):

1. For each skill with ≥ 5 invocations:
    - Compute success rate.
    - Compute average tokens / cost.
    - Compute median critique density in trajectories where the skill was invoked.
2. Rank skills; tag bottom deciles `stale` or `low-value`.
3. Present audit in `lyra learn review`; user can keep/refine/delete.

This is the Voyager + Hermes synthesis: skill library grows *and* prunes.

## Feedback store

Every skill's invocations accumulate feedback in `.lyra/memory/feedback/<skill-name>.md`:

```markdown
# Feedback: test-gen

## 2026-04-18 — session 01HX…  (success)
Trajectory: 9 steps. Coverage +4.2%. No regressions.
Notes: Skill worked well for pure functions; mocked DB per SOUL convention.

## 2026-04-17 — session 01HY…  (partial)
Trajectory: 15 steps. Coverage +1.1%.
Notes: Skill added a test that never ran (wrong test discovery pattern). Remedy: skill should run pytest collect-only first.

## 2026-04-14 — session 01HZ…  (fail)
Trajectory: 22 steps. Reject by evaluator.
Notes: Skill mocked too aggressively; tests passed but behavior unchanged.
```

Refiner reads these entries when proposing patches.

## Router description-based invocation

The agent's system prompt includes:

> Skills are available. To invoke: `Skill(name=..., args={...})`. Choose a skill when its description matches the situation; otherwise proceed with core tools.

On ambiguity (two skill descriptions match), the agent is prompted to disambiguate via reasoning; telemetry tracks ambiguity events.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Skill description too vague → over-invoked | Skill linter enforces "use when" phrasing + specificity audit |
| Skill description too narrow → never invoked | Self-eval flags; builder prompted to generalize |
| Two skills overlap | Router emits ambiguity event; self-eval pairs them for merge |
| Skill grants `allowed-tools: [*]` | Linter rejects; builder refuses to emit |
| Extractor promotes every session (skill explosion) | Classifier threshold tuned; cardinality cap + warning |
| Refiner introduces regression | Refined skill is A/B-tested in next N invocations before becoming default |
| Stale skill keeps being invoked | Self-eval `stale` tag + router de-prioritization |
| Skill body drifts from SOUL conventions | Linter cross-references SOUL sections; fail on contradiction |

## Metrics emitted

- `skill.invocations.total` labeled by name, mode, outcome
- `skill.invocations.latency_ms` histogram
- `skill.extractor.promotions.total` labeled by new|refined|noop
- `skill.library.cardinality` gauge
- `skill.self_eval.stale_count` gauge
- `skill.ambiguity_events.total`
- `skill.body.tokens` histogram

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_skill_loader.py` | Scope precedence, YAML parsing, lint |
| Unit `test_skill_router.py` | Description matching, ambiguity detection |
| Unit `test_skill_extractor.py` | Candidate classifier, builder output shape |
| Unit `test_skill_refiner.py` | Patch diff correctness + A/B mechanism |
| Unit `test_self_eval.py` | Ranking, tagging, pruning |
| Integration | End-to-end: session → extraction → refinement → next-session invocation |
| Property | Refiner's patches do not widen `allowed-tools` |

## Open questions

1. **Skill marketplace.** v1: share by git URL + install. v2: may add index/search, but governance is hard.
2. **Embedded RL on skills.** Atomic-Skills paper shows joint RL lifts shared policy; Lyra is API-first, so RL is v2 optional.
3. **Cross-user skill aggregation.** Anonymized skill usage metrics contributed to a community index could boost quality. Privacy-sensitive.
4. **Skill composition.** A skill that invokes another skill: allowed, but with recursion guard; design not yet finalized.
5. **Skill safety classification.** Some skills should be labeled "destructive" (e.g. a database migration skill). Needs a safety taxonomy.
