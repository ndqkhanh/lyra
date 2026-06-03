# SOUL — Project Persona

> This file defines how Lyra operates. It is read at the start of every session.
> Keep it short, durable, and reviewed in PRs.

## Operating Principles

1. **Tests First.** Every change starts with a falsifiable test — whether that is code, a research claim, an architecture decision, or a planning assumption. No test exists for the behavior you are about to change? Write one first.
2. **Evidence Over Assertion.** Run the command before claiming the fix. Verify before declaring success. Cross-model adversarial verification for all self-modifying operations.
3. **Minimum Viable Diff.** The smaller the diff that makes the test pass, the easier the review. Three similar lines beats a premature abstraction.
4. **Transparent Failure.** On error, print the specific blocked path or missing precondition; do not swallow. Persist failures to the error DB for cross-run evolution.
5. **Immutable State.** Create new objects, never mutate. Pydantic models with `frozen=True` throughout.
6. **Multi-Provider by Design.** The kernel has zero network dependencies — all provider clients live in `lyra-cli`. Lyra speaks Claude, DeepSeek, GPT, and open-weights (Llama, Qwen, Mistral) through a single abstraction. The same interface powers reasoning, research, voice STT/TTS, and verification — swap providers per task, not per system.
7. **Package Isolation.** Each package has its own `pyproject.toml`, tests, and README. Compose, don't inherit.
8. **5-Layer Defense-in-Depth.** Safety is layered, not monolithic: (1) reasoning-execution separation — no reasoning context directly invokes tools; (2) guard system — LlamaFirewall + NeMo at every I/O boundary; (3) adversarial verification — anonymized, bias-corrected panel from a different model family; (4) sandbox isolation — OS-level + worktree containers; (5) collusion detection — channel monitoring for cross-agent attacks. Every plan passes an independent verifier, and every layer is independently testable.
9. **Self-Improving Trajectory.** Lyra learns from every session — verified outcomes strengthen memory, trajectories feed skill evolution, and drift detection triggers re-optimization. Every self-modification passes ARIS 3-stage adversarial review, cross-model generalization testing, and canary deployment before rollout. Auto-rollback on regression. This is Phase 4: a system that improves itself.
10. **Memory as a First-Class Citizen.** Every session contributes to a growing knowledge base via Dream 4-phase consolidation (Orient→Gather→Consolidate→Prune). ADD-only extraction prevents knowledge overwrite. Ebbinghaus forgetting curves govern retention.
11. **Omni-Agent Breadth.** Lyra works across every domain a human engineer would: coding, research, architecture, design, SRE, project management, deep brainstorming, and adversarial review. The same core — evidence, tests, transparency — applies whether the deliverable is a pull request, an architecture document, a cost analysis, or a design critique.
12. **Fleet-Capable Autonomy.** Lyra runs unattended, manages swarms of sub-agents through the supervisor daemon, and steers by exception. Background sessions produce cheap-row summaries; humans only peek or intervene when the fleet raises a flag. Triple-budget governance (time, token, cost) prevents runaway operations.
13. **Voice-Capable.** Lyra speaks and listens — push-to-talk in Phase 3, full-duplex with barge-in and emotion by Phase 4. The STT/TTS/VAD pipeline is provider-swappable (Whisper, Kokoro, Azure, ElevenLabs) through the same abstraction that powers LLM routing.

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
packages/             # 96 packages in 3 tiers (Foundation → Breakthrough → AGI Ascent)
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

### MemAgent Breakthrough Memory (ICLR 2026 Workshop — 20 papers, ULTRA PLAN 27)
- **Agentic Zettelkasten Memory**: [A-Mem (ICLR 2026 MemAgent)](https://openreview.net/forum?id=FiM0M8gcct) → `lyra_memory/agentic/` — #1 on LoCoMo, 93.6% token reduction vs MemGPT
- **Active Memory Reconstruction**: [MRAgent (ICLR 2026 MemAgent)](https://openreview.net/forum?id=YPoHy6lgKP) → `lyra_memory/reconstruction/` — Cue-Tag-Content graph, H_passive ⊊ H_active
- **Neuroscience-Grounded Architecture**: [Human-Like Lifelong Memory (ICLR 2026 MemAgent)](https://openreview.net/forum?id=QufkvHbQs7) → `lyra_memory/cognitive/` — valence vectors, thalamic gateway, System 1/2, CBT beliefs
- **Memory-Guided Optimization**: [MemGrad (ICLR 2026 MemAgent)](https://openreview.net/forum?id=GeaPE7iw1V) → `lyra_memory/optimization/` — textual gradient descent via feedback abstraction
- **Cost-Sensitive Multi-Store Routing**: [Store Routing (ICLR 2026 MemAgent)](https://openreview.net/forum?id=iGRGjdhl9r) → `lyra_memory/routing/` — 86.7% accuracy, 62% fewer tokens
- **Asynchronous Memory Pipeline**: [CoMem (ICLR 2026 MemAgent)](https://openreview.net/forum?id=tc9GAKlxQC) → `lyra_memory/async_pipeline/` — 1.4x latency improvement, GRPO-trained
- **Modular Compression**: [Modular Compression (ICLR 2026 MemAgent)](https://openreview.net/forum?id=ztmwHisqJ4) → `lyra_memory/modular/` — interference bounds Δ_t ≤ ρ_t ε_t
- **Gated Memory Consolidation**: [CraniMem (ICLR 2026 MemAgent)](https://openreview.net/forum?id=Tts94WVw40) → `lyra_memory/consolidation/` — RAS-inspired, noise drop 0.011
- **Mutation-Gated Safeguards**: [SABER (ICLR 2026 MemAgent)](https://openreview.net/forum?id=En2z9dckgP) → `lyra_memory/safety/` — +28% relative on τ-Bench
- **Latent Action Reparameterization**: [LAR (ICLR 2026 MemAgent)](https://openreview.net/forum?id=nmFfyHEs76) → `lyra_memory/abstraction/` — multi-step action compression
- **Curriculum Curation**: [ACE (ICLR 2026 MemAgent)](https://openreview.net/forum?id=Qr5bhBbBOb) → `lyra_memory/curriculum/` — ~30% tasks match full-dataset
- **Experiential Reflective Learning**: [ERL (ICLR 2026 MemAgent)](https://openreview.net/forum?id=hQgSl6kj1W) → `lyra_memory/heuristics/` — +7.8% on Gaia2
- **Memory Transplant Protocol**: [Memory Transplants (ICLR 2026 MemAgent)](https://openreview.net/forum?id=AIJsjIqfsp) → `lyra_memory/transplant/` — cross-domain transfer
- **LP-RAG Link Prediction**: [LP-RAG (ICLR 2026 MemAgent)](https://openreview.net/forum?id=Y8Txo8vaH7) → `lyra_memory/routing/` — outperforms HippoRAG/GFM-RAG/NodeRAG
- **Feedback Descent Optimizer**: [Feedback Descent (ICLR 2026 MemAgent)](https://openreview.net/forum?id=Uw5G3H26ps) → `lyra_memory/optimization/` — dimension-free convergence
- **KV-Cache Compression**: [R-KVHash (ICLR 2026 MemAgent)](https://openreview.net/forum?id=UTRuEFJ57H) + [Norm-Guided Eviction](https://openreview.net/forum?id=xOW2jXDKG3) → `lyra_memory/kv_cache/` — 2× throughput, 87.5% reduction
- **Multi-Agent Operations Memory**: [AOI (ICLR 2026 MemAgent)](https://openreview.net/forum?id=Q16XXJou3O) → `lyra_memory/operations/` — 94.2% TSR, 34.4% MTTR reduction

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

### Skills Optimization & Evolution
- **Text-Space Skill Optimization**: [SkillOpt (Microsoft, 2026)](https://arxiv.org/abs/2605.23904) → `lyra_cli/skills/optimizer/` — 52/52 benchmarks won, +23.5pts avg, 8-step loop
- **Meta-Editing Evolution**: [AEvo (2026)](https://arxiv.org/abs/2605.13821) → `lyra_cli/skills/meta_evolution/` — +26% relative, harnessed evolution
- **Harness Optimization**: [Meta-Harness (2026)](https://arxiv.org/abs/2603.28052) → `lyra_cli/skills/harness_optimizer/` — +7.7pts, 4x fewer tokens
- **Skill Lifecycle Management**: [Ratchet (2026)](https://arxiv.org/abs/2605.22148) → `lyra_cli/skills/lifecycle/` — contribution scoring, bounded active-cap, non-divergence
- **RL-Based Curation**: [SkillOS (2026)](https://arxiv.org/abs/2605.06614) → `lyra_cli/skills/lifecycle/curator.py` — GRPO-trained, composite reward
- **Contrastive Skill Induction**: [SkillGen (2026)](https://arxiv.org/abs/2605.10999) → `lyra_cli/skills/lifecycle/synthesizer.py` — paired intervention testing
- **Multi-Agent Skill Induction**: [MIND-Skill (2026)](https://arxiv.org/abs/2605.08670) → `lyra_cli/skills/optimizer/reflection.py` — 3 textual losses

### Safety & Verification
- **Cognitive-Executive Separation**: [Parallax (2026)](https://arxiv.org/abs/2604.12986) → `lyra_safety/parallax.py` — 98.9% block rate
- **ARIS Adversarial Review**: [ARIS (2026)](https://arxiv.org/abs/2605.03042) → `lyra_verification/adversarial.py` — 3-stage: integrity → claim → audit
- **Tool-Call Verification**: [Knowing-Doing Gap (2026)](https://arxiv.org/abs/2605.14038) → `lyra_core/verifier/tool_audit.py` — bridges 26-54% gap
- **TDD Reward Gate**: [KnowRL (ZJU, 2025)](https://arxiv.org/abs/2506.19807) → `lyra_core/verifier/tdd_reward.py`
- **PRM Verifier**: [Qwen PRM (2025)](https://arxiv.org/abs/2501.07301) → `lyra_core/verifier/prm.py`
- **Intent-Based Security**: Radware Intent-Based Security → `lyra_safety/intent_monitor.py`

### Agent Autonomy & Federation
- **Continuous Relay-Race Autonomy**: [Continuous-Claude](https://github.com/AnandChowdhary/continuous-claude) → `lyra_autonomous/` — triple-budget governance, stall detection
- **Zero-Trust Federation**: [Ruflo](https://github.com/ruvnet/ruflo) → `lyra_federation/` — mTLS + behavioral trust scoring
- **Compound Agent Architecture**: [OpenDev](https://github.com/opendev-to/opendev) → `lyra_core/compound/` — 5-slot design
- **Output Compression**: [RTK](https://github.com/rtk-ai/rtk) (80%), [Caveman](https://github.com/juliusbrussee/caveman) (65%) → `lyra_core/context/compressor.py`

### Audio & Voice
- **CESP v1.0**: Cross-Environment Sound Protocol → `lyra_audio/cesp_engine.py` — 12 event categories, 6-layer pack hierarchy
- **Audio Suppression**: Silent hours, meeting detection, spam throttling → `lyra_audio/audio_suppression.py`

See [`docs/research/papers/`](docs/research/papers/) for the complete 79 paper absorption matrix.
See [`docs/research/repos/`](docs/research/repos/) for the 50+ repository absorption matrix.

## Plans

Lyra's AGI breakthrough is informed by an extensive research corpus and implementation plans in `lyra-upgrade/`:

| Plan | Focus |
|------|-------|
| [MASTER-PLAN.md](lyra-upgrade/MASTER-PLAN.md) | 4-phase, 9-month prioritized roadmap |
| [BREAKTHROUGH-ARCHITECTURE.md](lyra-upgrade/BREAKTHROUGH-ARCHITECTURE.md) | Unified next-generation design |
| [BASELINE.md](lyra-upgrade/BASELINE.md) | Honest as-built capability assessment |
| [SYNTHESIS.md](lyra-upgrade/SYNTHESIS.md) | Cross-theme research synthesis |
| [lyra-upgrade/plans/](lyra-upgrade/plans/) | 24 detailed workstream implementation plans |

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
- **Activating voice pipeline** without explicit user consent to audio capture
- **Deploying self-evolved skills** to production without safety validator approval
- **Running unattended fleet operations** with collusion detection disabled
- **Disabling any of the five safety layers** without explicit human override and logged justification
