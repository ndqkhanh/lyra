# Guide: Skills and Evolution

> 📖 Guide — Follow the full skill lifecycle from creation through loading, invocation, and evolution. Understand how Lyra discovers, activates, and self-improves skills.

Skills are the unit of capability in Lyra -- a folder with a `SKILL.md` YAML frontmatter file. This guide walks through the complete lifecycle.

---

## Skill Lifecycle

```
Create -> Discover -> Load (progressive) -> Invoke (trigger match) -> Execute -> Extract -> Curate -> Evolve
```

### 1. Creation

Skills come from two sources:

**Human-written**: Create a folder `~/.lyra/skills/<id>/SKILL.md`:

```yaml
---
id: surgical-changes
name: Surgical Code Changes
description: Make minimal, targeted code changes with no side effects
version: 1.2.0
keywords: [edit this file, modify function, surgical edit]
progressive: true
allowed_tools: [Read, Edit, Glob, Grep]
---
```

**SkillNet-sourced**: Running `lyra skill install <name>` pulls from the SkillNet registry (an open repository of community-contributed skills). See the [Skill Format concept](../concepts/03-skills.md) for the full schema.

### 2. Progressive Loading (3 Levels)

| Level | What Loads | Token Cost |
|---|---|---|
| L0 always | Name + description + keywords | ~10 tokens/skill |
| L1 on trigger | Full SKILL.md body | ~200-500 tokens |
| L2 on access | Referenced files, scripts, assets | Variable |

With 24 shipped packs + ~50 user skills, always-injecting would burn ~20K tokens. Progressive loading cuts this to ~500 tokens (L0) plus activated bodies (600-1800 tokens) -- a 5-10x savings.

### 3. Invocation (Trigger Matching)

The default router tokenizes your query and skill descriptions, applies stopword filtering and synonym expansion (change/modify/update/fix all map to "edit"), and scores by intersecting tokens. Runs in microseconds.

When invoked via `lyra skill invoke <name>`, the full body loads, the permission bridge narrows tools to `allowed_tools`, and the skill content is injected as a system message addendum. Tool scope restores on exit.

### 4. Extraction

After every completed task, the Skill Extractor evaluates the trajectory against six rubric checks:

| Check | Type | Gate |
|---|---|---|
| min_tool_calls >= 4 | HARD | Reject candidate |
| distinct_tools >= 2 | HARD | Reject candidate |
| slug_unique | HARD | Reject if shadowing |
| has_sections | SOFT | Body needs "When to use" + "Tool sequence" |
| no_leaked_secrets | HARD | Regex scan |
| body_length <= 200 lines | SOFT | Quality signal |

Any HARD failure rejects the candidate. Proposals land in `_proposals/` for human review -- the extractor never auto-publishes.

### 5. Curation (The Curator)

A deterministic, no-LLM background grader runs on cron, reading the skill ledger and tiering each skill:

| Tier | Min Utility | Action |
|---|---|---|
| Promote | >= 0.85 | Feature in /help |
| Keep | >= 0.65 | No action |
| Watch | >= 0.40 | Monitor |
| Rewrite | < 0.40 | Flag for evolution |
| Retire | < 0.20 | Move to archive |

The tier logic is a pure function of `(SkillStats, SkillManifest, size, age)`. Runs in <100ms over hundreds of skills.

### 6. Evolution (GEPA Gradient-Free)

When a skill needs improvement, the evolution pipeline activates:

**SkillOpt** (bounded mutations): Each mutation is a single `(old_text, new_text)` pair applied via `str.replace()`. The constraint: `old_text` must appear exactly once. If `new_score <= pre_score`, the mutation reverts. Four mutation strategies: add_example, add_constraint, restructure, add_edge_case.

```python
if new_score > pre_score:
    accept()      # log mutation, promote
else:
    revert()      # restore body_v1, log failure
```

Each round costs `len(scenarios) + 2` LLM calls. The mutation log (`skill_mutations.jsonl`) records every round for full auditability.

**GEPA v2** (parallel multi-agent search): Multiple agents explore the prompt space simultaneously (17x speedup), selecting Pareto-frontier improvements.

**Safety guards**: Every evolution step passes through ARIS 3-stage adversarial review, cross-model testing on >=3 model families, canary deployment (10% traffic, 24h), and auto-rollback.

---

## Related Docs

- [Architecture: Skills System](../architecture/06-skills-system.md) -- full evolution engine comparison
- [Concept: Skills](../concepts/03-skills.md) -- SKILL.md schema, trigger patterns
- [Guide: Agent Execution](01-agent-execution.md) -- how skills interact with the agent loop
- [Guide: Safety and Permissions](05-safety-and-permissions.md) -- Misevolve safety for self-evolution
