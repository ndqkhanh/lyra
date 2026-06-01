---
title: Lyra — Skills (evolution wired into existing lyra-skills)
description: EvoSkill + CoEvoSkills evolution loop layered over the existing lyra-skills extractor / curator / loader.
---

# Lyra — Skills (evolution layered over `lyra-skills`)

Lyra already ships a substantial `lyra-skills` package (extractor, curator,
loader, activation, installer, router, review, packs). This integration adds
**EvoSkill-style failure-driven evolution** + **CoEvoSkills-style multi-file
packages** without disturbing the existing surface.

## Corner of the design space

| Axis | Value |
|---|---|
| Feedback signal | Ground-truth (verifier cross-channel rejection) |
| Skill artifact | SKILL.md folder + scripts (CoEvoSkills-shape) |
| Parameter access | Frozen weights |
| Reference papers | [EvoSkill](../../../docs/168-evoskill-coding-agent-skill-discovery.md), [CoEvoSkills](../../../docs/169-coevoskills-co-evolutionary-verification.md) |

## Adapter

A new module `lyra_skills.evolution` (sibling to the existing
`lyra_skills.extractor`) wires `harness_skills.extract.FailureExtractor`
into Lyra's verifier rejection stream and uses `lyra-skills.installer`'s
existing git-worktree-per-subagent mechanism as the EvoSkill frontier.

## Bright-lines

- `BL-LYRA-SKILL-PROMOTE` — held-out eval gate + HITL.
- `BL-LYRA-SKILL-COST` — per-program budget envelope on evolution loops.

## Seed skill (new)

- `verifier-aware-edit` — when the verifier rejects, fold the diagnostic
  into the next attempt as an explicit constraint.
