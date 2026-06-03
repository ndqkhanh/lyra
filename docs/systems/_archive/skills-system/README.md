# Skills System -- Learning Path

> **Phase:** 4 | **Composes blocks:** Skill Engine & Extractor, MCP Adapter, Memory (Three-Tier), Hooks & TDD Gate | **Architecture doc:** [06-skills-system.md](../../architecture/06-skills-system.md)

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 🟢 Beginner | What & Why | [architecture.md](architecture.md) | System purpose -- self-evolving skill lifecycle: authoring (SKILL.md), discovery (tiered loader from 4 source roots), routing (token overlap / Argus 5-tier cascade), activation (progressive disclosure, max 6 skills), outcome ledger, deterministic curation (5-tier), extraction from trajectories, evolution (Escher-Loop RSI / GEAR-Evolve / Council Mode) |
| 🟡 Intermediate | Design | [system-design.md](system-design.md) | 5-tier routing cascade (keyword -> BM25 -> semantic -> cross-encoder -> telemetry), 5-tier grading system (promote/keep/watch/rewrite/retire), 5-tier loading (frontmatter -> body -> references), Pareto-frontier skill evolution, GEAR-Evolve mutation strategies |
| 🟠 Advanced | Implementation | [implementation.md](implementation.md) | Loader patterns with YAML frontmatter parsing, Argus bridge (bidirectional SkillManifest translation), provider bridge (per-provider trigger strategies + Claude-only field stripping), AEVO loop integration, skill extraction rubric (6 criteria with secret scanning) |
| 🔴 Expert | Deep Dive | [tradeoffs.md](tradeoffs.md) | Token overlap vs semantic routing, curator determinism vs LLM grading, Escher-Loop RSI vs Council Mode evolution, bounded edit constraints for mutation safety |
| 🔬 Evaluation | Benchmarks | [evaluation.md](evaluation.md) | 50ms load for 100 skills, 5ms token overlap routing, <100ms curator run for 200 skills, optimizer cost analysis (110 LLM calls per optimization round) |

## In 30 Seconds

The Skills System implements a complete self-evolving skill lifecycle: skills are authored as structured Markdown (SKILL.md with YAML frontmatter), discovered by a tiered loader from 4 source roots (project-local, user-global, shipped packs, Claude Code), matched to user intents via multi-stage routing (token overlap to semantic search at 5 tiers), activated with progressive disclosure (description-only until needed), tracked via outcome ledger with utility scoring (range -1.0 to +1.0 with recency boost), graded by a deterministic 5-tier curator (zero LLM calls), extracted from successful trajectories through a 6-criteria rubric, and evolved across generations via bounded-edit mutations with Pareto-frontier search.

## What This System Composes

| Block | Role |
|-------|------|
| [Skill Engine & Extractor](../../blocks/09-skill-engine-and-extractor.md) | Core skill loading, routing (token overlap + Argus cascade), extraction, curation, and evolution |
| [MCP Adapter](../../blocks/mcp-adapter/) | Argus cascade integration for skill catalog bridging and keyword/semantic/synonym expansion |
| [Memory (Three-Tier)](../../blocks/memory/) | Ledger persistence, outcome history, mutation log storage |
| [Hooks & TDD Gate](../../blocks/hooks-tdd/) | Pre/post-activation hooks, provider bridge injection, Claude-only field stripping |

## Quick Reference

- **When you need this:** Building an extensible skill system, implementing self-improving agent capabilities, managing a growing catalog of LLM-guided behaviors
- **Related architecture doc:** [06-skills-system.md](../../architecture/06-skills-system.md)
- **Upgrade plans:** [19-self-knowledge.md](../../lyra-upgrade/plans/19-self-knowledge.md), [27-rl-optimizer.md](../../lyra-upgrade/plans/27-rl-optimizer.md)
- **Concept doc:** [skills.md](../../concepts/skills.md)
- **Key packages:** `packages/lyra-skills/` (production runtime), `packages/lyra-evolution/` (research evolution layer)

## Reading Path by Role

| Role | Read |
|------|------|
| System user | architecture.md |
| Integrator | architecture.md + system-design.md |
| Builder | All 5 docs |
