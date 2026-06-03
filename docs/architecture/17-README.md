# Architecture — Navigation Hub

> **Primary docs:** [docs/README.md](../README.md) — 9 synthesized files for everything  
> **Honest baseline:** [lyra-upgrade/BASELINE.md](../lyra-upgrade/BASELINE.md)  
> **Implementation plans:** [lyra-upgrade/plans/](../lyra-upgrade/plans/)

---

## 10 Numbered Deep-Dives

Start with #1 for the big picture, then dive into any topic:

| # | Document | Covers |
|---|----------|--------|
| 01 | [Ultracode Replication](01-ultracode-replication.md) | Effort scale, orchestration toggle, workflow primitives |
| 02 | [Memory Architecture](02-memory-architecture.md) | Graph memory, cost-sensitive routing, field-theoretic consolidation |
| 03 | [Provider Abstraction](03-provider-abstraction.md) | Multi-provider layer, capability matrix, graceful degradation |
| 04 | [Fleet Supervisor](04-fleet-supervisor.md) | Supervisor daemon, fleet view, session lifecycle |
| 05 | [Workflow Engine](05-workflow-engine.md) | Dynamic workflows, agent/parallel/pipeline, adversarial verification |
| 06 | [Skills System](06-skills-system.md) | Progressive disclosure, self-evolving skills |
| 07 | [Voice Pipeline](07-voice-pipeline.md) | Cascaded STT→Agent→TTS, provider-swappable |
| 08 | [Safety & Security](08-safety-security.md) | 5-layer defense-in-depth, collusion detection |
| 09 | [Model Router](09-model-router.md) | 3-tier cascade, memory-augmented routing, effort scale |
| 10 | [Worktree Isolation](10-worktree-isolation.md) | Git-worktree-per-session, COW optimization |

## Supporting Docs

| Document | When to Read |
|----------|-------------|
| [ARCHITECTURE.md](11-architecture-overview.md) | Main overview with full Mermaid diagrams — read this first |
| [commitments.md](12-commitments.md) | Key architectural commitments and their rationales |
| [gap-analysis.md](13-gap-analysis.md) | Current vs target capability gaps |
| [implementation-roadmap.md](14-implementation-roadmap.md) | Development timeline and milestones |
| [topology.md](15-topology.md) | System topology and component dependencies |
| [breakthrough-architectures.md](16-breakthrough-architectures.md) | Novel cross-source combinations |

## Quick Reference

| Question | Read |
|----------|------|
| "How does Lyra work at a high level?" | [ARCHITECTURE.md](11-architecture-overview.md) |
| "How do I add a new LLM provider?" | [03-provider-abstraction.md](03-provider-abstraction.md) |
| "How does memory work across sessions?" | [02-memory-architecture.md](02-memory-architecture.md) |
| "How do agents run in parallel safely?" | [10-worktree-isolation.md](10-worktree-isolation.md) + [04-fleet-supervisor.md](04-fleet-supervisor.md) |
| "How does the workflow engine work?" | [05-workflow-engine.md](05-workflow-engine.md) |
| "How is safety enforced?" | [08-safety-security.md](08-safety-security.md) |
| "What's built vs planned?" | [lyra-upgrade/BASELINE.md](../lyra-upgrade/BASELINE.md) |
| "When will X ship?" | [lyra-upgrade/MASTER-PLAN.md](../lyra-upgrade/MASTER-PLAN.md) |
| "How do I build X?" | [lyra-upgrade/plans/](../lyra-upgrade/plans/) |

## Archived

39 old files (scattered topics, duplicates, stale meta docs) were moved to `_archive/`. See [INDEX.md](INDEX.md) for the mapping.
