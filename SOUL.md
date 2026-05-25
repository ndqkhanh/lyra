# SOUL — Project Persona

> This file defines how Lyra operates. It is read at the start of every session.
> Keep it short, durable, and reviewed in PRs.

## Operating Principles

1. **Tests First.** Every code change starts with a failing test. No test exists for the behavior you're about to change? Write one first.
2. **Evidence Over Assertion.** Run the command before claiming the fix. Verify before declaring success. Cross-model adversarial verification for all self-modifying operations.
3. **Minimum Viable Diff.** The smaller the diff that makes the test pass, the easier the review. Three similar lines beats a premature abstraction.
4. **Transparent Failure.** On error, print the specific blocked path or missing precondition; do not swallow. Persist failures to the error DB for cross-run evolution.
5. **Immutable State.** Create new objects, never mutate. Pydantic models with `frozen=True` throughout.
6. **Provider Agnostic.** The kernel has zero network dependencies. All provider clients live in `lyra-cli`.
7. **Package Isolation.** Each package has its own `pyproject.toml`, tests, and README. Compose, don't inherit.
8. **Safety by Separation.** Reasoning and execution run in structurally separated contexts. No reasoning context can directly invoke tools. Every execution plan must pass an independent verification agent from a different model family.
9. **Self-Evolution with Guardrails.** The harness can optimize itself, but every self-modification must pass adversarial review (ARIS 3-stage), cross-model generalization testing, and a canary deployment before full rollout. Auto-rollback on regression.
10. **Memory as a First-Class Citizen.** Every session contributes to a growing knowledge base via Dream 4-phase consolidation (Orient→Gather→Consolidate→Prune). ADD-only extraction prevents knowledge overwrite. Ebbinghaus forgetting curves govern retention.

## Project Context

- **Language(s):** Python 3.11+ (primary), TypeScript 5.3+ (UI layer)
- **Package Manager:** pip (Python), npm (TypeScript/Node)
- **Test Runner:** pytest (Python), Jest/Vitest (TypeScript)
- **Lint / Format:** ruff + black + mypy (Python), ESLint + Prettier (TypeScript)
- **CI:** GitHub Actions (.github/workflows/ci.yml)
- **Deploy Target:** CLI application (pip install), optional TUI (npm)

## Repository Layout

```
src/                  # Core Python library (agents, memory, hooks, rules, skills, security)
packages/             # 135+ subpackages in 3 tiers (Foundation → Breakthrough → AGI Ascent)
  lyra-core/          # Kernel: AgentLoop, TDD gate, permissions, HIR observability, Pivot/Refine
  lyra-cli/           # CLI application: Typer, prompt_toolkit REPL, 16 LLM providers
  lyra-*/             # Domain packages (reasoning, research, memory, evolution, safety, audio, etc.)
  ui-*/               # TypeScript UI packages (core state, Ink terminal, transport)
harness_core/         # Shared harness primitives (tools, permissions, evals, verifier)
tests/                # Integration and system tests
docs/                 # MkDocs documentation site (architecture, contributing, guides)
```

## Branch & Commit Policy

- **Main branch:** `main` — protected, CI must pass
- **Feature branches:** `feat/<name>`, `fix/<name>`, `refactor/<name>`
- **Commit style:** [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`

## Conventions

- **Python:** PEP 8, type annotations on all function signatures, `black` formatting (line-length=100), `ruff` linting
- **TypeScript:** Strict mode, React JSX, bundler module resolution
- **File size:** 200-400 lines typical, 800 max
- **Function size:** <50 lines
- **Nesting:** Max 4 levels, prefer early returns
- **Imports:** `isort` ordering, absolute imports preferred within `src/`
- **Naming:** snake_case (Python), camelCase (TypeScript)
- **Docstrings:** One-line summary for public API. Full Google-style only when non-obvious.

## Innovation Lineage

Lyra is downstream of a substantial research ecosystem. Every novel technique traces to its source:

### Reasoning & Planning
- **Tournament TTS**: [Scaling Test-Time Compute (Meta, 2026)](https://arxiv.org/abs/2604.16529) → `lyra_core/tts/tournament.py`
- **SR2AM Self-Regulated Planning**: [SR2AM (2026)](https://arxiv.org/abs/2605.22138) → `lyra_reasoning/sr2am/` — System I/II/III architecture, 8B matching 1T
- **ReasoningBank**: [Google Research (2025)](https://arxiv.org/abs/2509.25140) → `lyra_core/memory/reasoning_bank.py`
- **Reasoning Graphs**: [ACL 2026] → `lyra_reasoning/reasoning_graph.py` — Persist CoT as structured graph edges
- **Pivot/Refine Recovery**: [AutoResearchClaw (2026)](https://arxiv.org/abs/2605.20025) → `lyra_core/loop/pivot_refine.py`

### Memory & Context
- **Dream 4-Phase Consolidation**: Claude Code Dream system, [Mem0](https://github.com/mem0ai/mem0) (91.6 LoCoMo, 93.4 LongMemEval) → `lyra_memory/dream_consolidator.py`
- **Skill-RAG Recovery**: [UMich/UPenn (2026)](https://arxiv.org/abs/2604.15771) → `lyra_core/retrieval/skill_rag.py`
- **Neural Garbage Collection**: [NGC (Stanford, 2026)](https://arxiv.org/abs/2604.18002) → `lyra_core/context/compactor.py`
- **Symbolic STM**: [TencentDB-Agent-Memory](https://github.com/Tencent/TencentDB-Agent-Memory) → `lyra_memory/symbolic_stm.py`
- **Progressive Disclosure**: [claude-mem](https://github.com/thedotmack/claude-mem) → Memory + Skills retrieval (L1→L2→L3)
- **DCI Zero-Index Retrieval**: [DCI-Agent-Lite](https://github.com/DCI-Agent/DCI-Agent-Lite) → `lyra_research/zero_index.py`
- **Pre-Indexed KG**: [CodeGraph](https://github.com/colbymchenry/codegraph) → `lyra_knowledge_graph/`
- **Verbatim-First Retrieval**: [MemPalace](https://github.com/MemPalace/mempalace) → Memory retrieval strategy
- **Skills as Memory**: [Acontext](https://github.com/memodb-io/Acontext) → Skill-memory equivalence

### Self-Evolution & Learning
- **GEPA v2 Multi-Agent Optimizer**: [GEPA (ICLR 2026 Oral)](https://arxiv.org/abs/2310.03714), [Combee](https://arxiv.org/abs/2604.15771) → `lyra_evolution/gepa_v2.py`
- **Meta-Harness Optimization**: [Meta-Harness (2026)](https://arxiv.org/abs/2603.28052) → `lyra_meta_evolution/harness_opt.py` — +7.7pts, 4x fewer tokens
- **AEvo Meta-Editing**: [AEvo (2026)](https://arxiv.org/abs/2605.13821) → `lyra_meta_evolution/aevo_meta.py` — 26% relative improvement
- **PRISM Drift Detection**: [PRISM (2026)](https://arxiv.org/abs/2605.14454) → `lyra_evolution/drift_detector.py`
- **Trace2Skill**: [Trace2Skill (2026)](https://arxiv.org/abs/2605.21810) → `lyra_skills/` auto-extraction pipeline
- **Skill Weaving**: [Voyager (NVIDIA, TMLR 2024)](https://arxiv.org/abs/2305.16291) → Composite skill creation

### Agent Communication & Coordination
- **RecursiveLink Latent Comms**: [RecursiveMAS (2026)](https://arxiv.org/abs/2604.25917) → `lyra_recursive_link/` — 75.6% token reduction, 1.2-2.4x speedup
- **Cascade Router**: [FrugalGPT (Stanford, 2023)](https://arxiv.org/abs/2305.05176) → `lyra_core/routing/cascade.py`
- **Confidence Escalation**: [RouteLLM (Berkeley, 2024)](https://arxiv.org/abs/2406.18665) → `lyra_core/routing/cascade.py`
- **SOP Role Topology**: [MetaGPT (ICLR 2024)](https://arxiv.org/abs/2308.00352) → `lyra_core/teams/`
- **DAG Teams**: [SemaClaw (Midea, 2026)](https://arxiv.org/abs/2604.11548) → `lyra_core/adapters/dag_teams.py`
- **Progressive Tool Discovery**: Claude Code Tool Search → `lyra_core/tools/tool_search.py` — 85% context savings

### Safety & Verification
- **Cognitive-Executive Separation**: [Parallax (2026)](https://arxiv.org/abs/2604.12986) → `lyra_safety/parallax.py` — 98.9% block rate
- **ARIS Adversarial Review**: [ARIS (2026)](https://arxiv.org/abs/2605.03042) → `lyra_verification/adversarial.py` — 3-stage: integrity → claim → audit
- **Tool-Call Verification**: [Knowing-Doing Gap (2026)](https://arxiv.org/abs/2605.14038) → `lyra_core/verifier/tool_audit.py`
- **TDD Reward Gate**: [KnowRL (ZJU, 2025)](https://arxiv.org/abs/2506.19807) → `lyra_core/verifier/tdd_reward.py`
- **PRM Verifier**: [Qwen PRM (2025)](https://arxiv.org/abs/2501.07301) → `lyra_core/verifier/prm.py`
- **Intent-Based Security**: Radware Intent-Based Security → `lyra_safety/intent_monitor.py`

### Audio & Voice
- **CESP v1.0**: Cross-Environment Sound Protocol → `lyra_audio/cesp_engine.py` — 12 event categories, 6-layer pack hierarchy
- **Audio Suppression**: Silent hours, meeting detection, spam throttling → `lyra_audio/audio_suppression.py`

See [`docs/research/papers.md`](docs/research/papers.md) for the complete 38+ paper absorption matrix.
See [`docs/research/repos.md`](docs/research/repos.md) for the 45+ repository absorption matrix.

## Plans

Lyra's AGI breakthrough is planned across 8 ultra plans:

| Plan | Focus |
|------|-------|
| [Plan 6](plans/LYRA_ULTRA_PLAN_6_OMNI_AGI_BREAKTHROUGH.md) | Master — 16 dimensions, 52-week roadmap |
| [Plan 7](plans/LYRA_ULTRA_PLAN_7_SKILLS_ECOSYSTEM.md) | Skills — 80+ domain skills, curator, learner, evolver |
| [Plan 8](plans/LYRA_ULTRA_PLAN_8_VOICE_AUDIO_SYSTEM.md) | Voice — fantasy packs, CESP pipeline, dictation |
| [Plan 9](plans/LYRA_ULTRA_PLAN_9_TOOLS_UNIVERSE.md) | Tools — 200+ tools across 20 toolsets |
| [Plan 10](plans/LYRA_ULTRA_PLAN_10_MODEL_ROUTER_V2.md) | Router — 5-layer intelligent cascading |
| [Plan 11](plans/LYRA_ULTRA_PLAN_11_AUTONOMOUS_SYSTEMS.md) | Autonomous — goals, continuous mode, hooks |
| [Plan 12](plans/LYRA_ULTRA_PLAN_12_AGENT_FLEET_SWARM.md) | Fleet — parallel fan-out, squads, colony, federation |
| [**Plan 13**](plans/LYRA_ULTRA_PLAN_13_BREAKTHROUGH_SYNTHESIS.md) | **Breakthrough — 6 AGI gaps, meta-evolution, Parallax safety, Dream memory, SR2AM planning** |

## Dangerous Operations

The following must never run without explicit human approval:

- `git push --force` on `main`
- `DROP TABLE`, `DELETE FROM` without a `WHERE` clause
- Any command that rewrites `.git/objects/*`
- Deployment commands to production environments
- `rm -rf` outside of build artifacts
- Modifying `.github/workflows/ci.yml` without review
- Autonomous agent operations exceeding `max_budget_usd` without confirmation
- Fleet operations targeting production infrastructure
- **Self-modification of harness code** without ARIS 3-stage adversarial review + cross-model generalization testing
- **Disabling cognitive-executive separation** without multi-agent consensus
- **Bypassing Dream consolidation** (risks permanent knowledge loss)
