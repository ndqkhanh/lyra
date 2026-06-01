---
title: Reference papers
description: Annotated bibliography of every paper Lyra reads — with the absorption mode and the exact file in Lyra each technique landed in.
---

# Reference papers <span class="lyra-badge reference">reference</span>

Lyra ships a local mirror of the arxiv papers cited across the
codebase under [`papers/`](https://github.com/lyra-contributors/lyra/tree/main/projects/lyra/papers)
(22 PDFs mirrored to date; Wave-4/5/7 entries not yet bulk-mirrored,
pull them with the script at the bottom). This page is the
**canonical bibliography + absorption matrix** — all 79 papers
referenced anywhere in `docs/`, `CHANGELOG.md`, or the source tree
are listed here with:

- **Lyra absorption mode** — what we did with the idea
- **Lyra implementation** — the exact file (or planned slot)
  the technique landed in

The companion [Reference repositories](repos.md) page does the same
job for every GitHub repo we cite. For the *why* of how a paper got
absorbed (what we deliberately didn't take, when we'll revisit),
read the per-paper design memo linked from each row.

## Absorption legend

| Symbol | Mode | Meaning |
|:--:|---|---|
| 🟢 | **Adopted** | Full or substantial integration; technique runs in production |
| 🟡 | **Pattern-mined** | Idea reshaped into a Lyra-native module; no vendoring |
| ⚪ | **Reference only** | Cited as benchmark / corpus / motivation; no Lyra code derives from it |
| 🔴 | **Studied & rejected** | Considered, deliberately not adopted (with reasoning recorded) |

> The legend used to include 🔵 "Forward-compat shim" and 🟠
> "Planned" rows. Those modes were retired in v3.5.5 — see the
> [CHANGELOG](https://github.com/lyra-contributors/lyra/blob/main/projects/lyra/CHANGELOG.md)
> for the rationale ("if we can't ship it, we don't claim it").
> Future-version slots now live in [Roadmap v1.5 → v2](../roadmap-v1.5-v2.md),
> not in this matrix.

## Wave 1 — original eight selling points

The capabilities core of Lyra v1.8. Cited in §3 of
[`docs/novel-ideas.md`](../novel-ideas.md).

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 1 | [**Scaling Test-Time Compute for Agentic Coding**](https://arxiv.org/abs/2604.16529) — Kim, Yang, Niu, Zhang, Zhu, Helenowski, Silva, Chen, Iyer, Zaheer, Fried, Hajishirzi, Arora, Synnaeve, Salakhutdinov, Goyal — Meta SI Labs / UW / NYU / DeepMind / CMU / Princeton<br/>`papers/meta-tts-agentic-coding.pdf` | 2026 | 🟢 | **Tournament-distilled TTS.** Recursive Tournament Voting + Parallel-Distill-Refine on parallel coding attempts. → [`lyra_core/tts/tournament.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts/tournament.py) |
| 2 | [**ReasoningBank — Scaling Agent Self-Evolving with Reasoning Memory + MaTTS**](https://arxiv.org/abs/2509.25140) — Google Research<br/>`papers/reasoningbank-mattS.pdf` | 2025 | 🟢 | **Lessons memory + memory-aware TTS.** Distills successes *and* failures into structured `Lesson`s; rotates slices per attempt index. → [`lyra_core/memory/reasoning_bank.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank.py), [`reasoning_bank_store.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank_store.py), [`distillers.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/distillers.py) · concept: [ReasoningBank](../concepts/reasoning-bank.md) |
| 3 | [**Skill-RAG — Hidden-State Probing + 4-skill Recovery Router**](https://arxiv.org/abs/2604.15771) — Univ. Michigan / UPenn<br/>`papers/skill-rag.pdf` | 2026 | 🟢 | **Introspective recovery router.** Hidden-state confidence probe → one of four recovery actions (Query Rewrite / Question Decomposition / Evidence Focus / Exit). → [`lyra_core/retrieval/skill_rag.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/retrieval/skill_rag.py), [`lyra_core/skills/router.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills/router.py) |
| 4 | [**KnowRL: Knowledgeable Reinforcement Learning for Factuality**](https://arxiv.org/abs/2506.19807) — Zhejiang Univ<br/>`papers/knowrl.pdf` | 2025 | 🟡 | **TDD-as-numeric-reward.** We can't fine-tune; the *signal shape* (give a step a numeric reward only when its citations verify) is reused at inference as the TDD reward gate. → [`lyra_core/verifier/tdd_reward.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/tdd_reward.py) · concept: [Verifier](../concepts/verifier.md) |
| 5 | [**Neural Garbage Collection: Learning to Forget while Learning to Reason**](https://arxiv.org/abs/2604.18002) — Li, Hamid, Fox, Goodman — Stanford<br/>`papers/ngc-neural-garbage-collection.pdf` | 2026 | 🟡 | **Grow-then-evict context compaction.** Block-level eviction at cadence δ, budget-aware interoception in the system prompt, LLM-driven rerank with full audit (no policy training in v1.7). → [`lyra_core/context/compactor.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/context/compactor.py) · roadmap: [v1.7 Phase 23](../roadmap-v1.5-v2.md) |
| 6 | [**PoisonedRAG: Knowledge Corruption Attacks to RAG**](https://arxiv.org/abs/2402.07867) (USENIX Security 2025)<br/>`papers/poisonedrag.pdf` | 2024 | ⚪ | **Threat-model citation only.** Five malicious docs in 2.6 M = 97 % attack success. The paper is the canonical citation for *why* Lyra refuses to ship a default RAG corpus without provenance, but **no Lyra code defends against PoisonedRAG today** — the planned `rag_provenance.py` slot was removed in v3.5.5 (it requires real sigstore engineering that doesn't fit the current scope). Tracked in [Roadmap v1.5 → v2](../roadmap-v1.5-v2.md). |
| 7 | [**SemaClaw: A Step Towards General-Purpose Personal AI Agents through Harness Engineering**](https://arxiv.org/abs/2604.11548) — Midea AIRC<br/>`papers/semaclaw-midea-airc.pdf` | 2026 | 🟢 | **Validation of the harness-engineering thesis.** Their DAG-Teams + PermissionBridge mirror Lyra's. We adopt their TwoPhasePlanner shape. → [`lyra_core/adapters/dag_teams.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/adapters/dag_teams.py), [`lyra_core/permissions/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/permissions) |

## Wave 2 — performance edges

The performance/cost/scale levers. Cited in §9 of
[`docs/novel-ideas.md`](../novel-ideas.md).

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 8 | [**SWE-Search: Enhancing Software Agents with MCTS and Iterative Refinement**](https://arxiv.org/abs/2410.20285) (ICLR 2025) — Antoniades et al.<br/>`papers/swe-search-mcts.pdf` | 2024–25 | 🟡 | **Intra-attempt MCTS pattern.** Inspires the `TournamentTts` bracket structure but with deterministic pairwise rounds instead of MCTS rollouts (cost-aware). → [`lyra_core/tts/tournament.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts/tournament.py) |
| 9 | [**AlphaEvolve: A coding agent for scientific and algorithmic discovery**](https://arxiv.org/abs/2506.13131) — Novikov et al. — DeepMind<br/>`papers/alphaevolve.pdf` | 2025 | 🟡 | **Sample-and-rank-with-verifier.** Pattern adopted in `lyra_core.evolve` as GEPA-style evolver. → [`lyra_core/evolve/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/evolve) |
| 10 | [**FrugalGPT: How to Use LLMs While Reducing Cost and Improving Performance**](https://arxiv.org/abs/2305.05176) — Chen, Zaharia, Zou — Stanford<br/>`papers/frugalgpt.pdf` | 2023 | 🟢 | **Cost-aware cascading routing.** Foundation of the cascade router. → [`lyra_core/routing/cascade.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/routing/cascade.py) · concept: [Two-tier routing](../concepts/two-tier-routing.md) |
| 11 | [**RouteLLM: Learning to Route LLMs with Preference Data**](https://arxiv.org/abs/2406.18665) — Ong et al. — UC Berkeley / LMSYS<br/>`papers/routellm.pdf` | 2024 | 🟢 | **Fast/smart slot routing with preference data.** Replaced FrugalGPT's static thresholds with preference-data-trained routers. → [`lyra_core/routing/cascade.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/routing/cascade.py) |
| 12 | [**Confidence-Driven LLM Router**](https://arxiv.org/abs/2502.11021) (2025 follow-up to RouteLLM)<br/>`papers/confidence-driven-llm-router.pdf` | 2025 | 🟢 | **Confidence-thresholded escalation.** Latest iteration of the cascade pattern; informs the smart-slot escalation logic. → [`lyra_core/routing/cascade.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/routing/cascade.py) |
| 13 | [**Voyager: An Open-Ended Embodied Agent with Large Language Models**](https://arxiv.org/abs/2305.16291) (TMLR 2024) — Wang et al. — NVIDIA / Caltech / UT Austin<br/>`papers/voyager.pdf` | 2023–24 | 🟡 | **Skill library pattern.** SKILL.md library + extractor + curriculum auto-proposer all trace to Voyager's skill-library design. → [`lyra_core/memory/procedural.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/procedural.py), `packages/lyra-skills/` · concept: [Skills](../concepts/skills.md) |
| 14 | [**Reflexion: Language Agents with Verbal Reinforcement Learning**](https://arxiv.org/abs/2303.11366) (NeurIPS 2023) — Shinn et al. — Northeastern / MIT<br/>`papers/reflexion.pdf` | 2023 | 🟢 | **Verbal-RL retrospective loop.** When an attempt fails, generate a verbal lesson and inject into the next attempt. → [`lyra_core/loop/reflexion.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/loop/reflexion.py) · CLI: `/reflect` |
| 15 | [**MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework**](https://arxiv.org/abs/2308.00352) (ICLR 2024 oral) — Hong et al.<br/>`papers/metagpt.pdf` | 2023–24 | 🟢 | **SOP-driven role topology.** PM/Architect/Engineer/Reviewer/QA roles + role-typed handoffs. → [`lyra_core/teams/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/teams) · CLI: `/team` |
| 16 | [**ChatDev: Communicative Agents for Software Development**](https://arxiv.org/abs/2307.07924) — Qian et al. — Tsinghua / OpenBMB<br/>`papers/chatdev.pdf` | 2023–24 | 🟡 | **Waterfall multi-agent SDLC.** Inspires the optional waterfall preset of the team scheduler. → [`lyra_core/teams/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/teams) |
| 17 | [**DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines**](https://arxiv.org/abs/2310.03714) (ICLR 2024) — Khattab et al. — Stanford<br/>`papers/dspy.pdf` | 2023–24 | 🟡 | **GEPA-style prompt evolver.** Pattern reused in the evolver (no DSPy import; reimplemented stdlib-only). → [`lyra_core/evolve/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/evolve) · CLI: `lyra evolve` |
| 18 | [**EAGLE-3: Scaling up Inference Acceleration of LLMs via Training-Time Test**](https://arxiv.org/abs/2503.01840) — Li et al.<br/>`papers/eagle3-spec-decoding.pdf` | 2025 | ⚪ | **Reference only.** Up to ×6.5 throughput on Llama 3.3 70B speculative decoding. Lyra is hosted-API-first and does not own the inference path; an EAGLE-3 absorption only makes sense alongside a self-hosted Lyra profile, which doesn't ship today. Tracked in [Roadmap v1.5 → v2](../roadmap-v1.5-v2.md). |
| 19 | [**OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments**](https://arxiv.org/abs/2404.07972) (NeurIPS 2024) — Xie et al.<br/>`papers/osworld.pdf` | 2024 | ⚪ | **Reference benchmark.** 12% best-agent vs 72% human; cited as the headroom signal for v2.x browser/computer-use. → tracking only |
| 20 | [**GDPval: Evaluating AI Model Performance on Real-World Economically Valuable Tasks**](https://arxiv.org/abs/2510.04374) — OpenAI<br/>`papers/gdpval.pdf` | 2025 | ⚪ | **Reference benchmark.** Model-quality bar for the v1.5 → v2 release notes. → tracking only |
| 21 | [**The Lessons of Developing Process Reward Models in Mathematical Reasoning**](https://arxiv.org/abs/2501.07301) — Qwen team<br/>`papers/qwen-process-reward-lessons.pdf` | 2025 | 🟢 | **PRM design lessons.** Avoids the "step-label noise" trap; informs the verifier's PRM phase. → [`lyra_core/verifier/prm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/prm.py) |
| 22 | [**Codex: Evaluating Large Language Models Trained on Code**](https://arxiv.org/abs/2107.03374) — Chen et al. — OpenAI<br/>*(not mirrored locally)* | 2021 | 🟢 | **`pass@k` unbiased estimator (eq. 1).** The bias-corrected combinatorial form Lyra uses to score eval runs. → [`lyra_core/eval/passk.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/passk.py) · how-to: [Run an eval](../howto/run-eval.md#passk) |

## Wave 3 — diversity-collapse hardening

Multi-agent monoculture defence. Cited in §10A of
[`docs/novel-ideas.md`](../novel-ideas.md).

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 23 | [**Diversity Collapse in Multi-Agent LLM Systems**](https://arxiv.org/abs/2604.18005) (ACL 2026 Findings) — Chen, Tong, Yang, He, Zhang, Zou, Wang, He — NUS / CUHK-Shenzhen<br/>`papers/diversity-collapse-mas.pdf` | 2026 | 🟢 | **Family-disjoint judges + MMR diversity-weighted recall + diversity guard.** Tournament-TTS uses different-family judges; ReasoningBank `recall(diversify=True)` re-ranks via MMR; `tts/diversity_guard.py` raises with a remediation hint pointing to §5.2. → [`lyra_core/tts/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts), [`reasoning_bank.py::recall`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank.py) · memo: [Diversity collapse analysis](diversity-collapse-analysis.md) |

## Wave 4 — multi-agent cache sharing + long-horizon eval

Hosted-API cost optimisation and the long-horizon eval driver.

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 24 | [**PolyKV: A Shared Asymmetrically-Compressed KV Cache Pool for Multi-Agent LLM Inference**](https://arxiv.org/abs/2604.24971) — Patel, Joshi — Independent<br/>`papers/polykv-shared-kv-pool.pdf` *(pull with the script below)* | 2026 | 🟢 | **`PromptCacheCoordinator` (hosted-API absorption).** The PolyKV mechanism (KV-cache memory sharing under self-hosted vLLM) doesn't reach a hosted-API harness, but its *architectural insight* — "one prefill, many reads" — does. Lyra translates it into a sibling-subagent prompt-cache coordinator: one cache write per `(provider, sha256(shared_text))`, `N − 1` hits, against Anthropic / OpenAI / DeepSeek / Gemini cache discounts. The forward-compat `SharedKVPoolProvider` Protocol shim was removed in v3.5.5 (no upstream existed). → [`lyra_core/providers/prompt_cache.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/providers/prompt_cache.py), [`subagent/cache_prewarm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/subagent/cache_prewarm.py) · memo: [PolyKV evaluation](polykv-evaluation.md) · concept: [Prompt-cache coordination](../concepts/prompt-cache-coordination.md) |
| 25 | [**Continuous Autoregressive Language Models (CALM)**](https://arxiv.org/abs/2604.24026) — Tencent + Tsinghua<br/>`papers/calm-continuous-autoregressive.pdf` *(pull with the script below)* | 2026 | 🔴 | **Studied & rejected for hosted-API Lyra.** CALM is a modelling-side change (continuous next-vector prediction with K-token blocks); a *harness* doesn't own training compute, the loss function, or the tokenizer. The earlier `BlockStreamingProvider` Protocol and `BrierLM` calibration scorer were forward-compat shims awaiting a hosted block-streaming provider; **no such provider has emerged**, so both were deleted in v3.5.5. The memo records the analysis for any future contributor who wants to revisit. → no Lyra code derives from CALM; memo: [CALM evaluation](calm-evaluation.md) |
| 29 | [**LoCoEval: A Scalable Benchmark for Repository-Oriented Long-Horizon Conversational Context Management**](https://arxiv.org/abs/2603.06358)<br/>*(not yet mirrored)* | 2026 | 🟢 | **Long-horizon eval adapter.** 50-turn driver with per-turn token-budget enforcement and set-based requirement-coverage scorer; bring-your-own LoCoEval JSONL per the published corpus license. → [`lyra-evals/adapters/loco_eval.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters/loco_eval.py), CLI: `lyra evals --suite loco-eval --tasks-path <jsonl>` |

## Wave 5a — validation papers (insights absorbed, no new module)

These papers Lyra has read and absorbed *operationally* — their
ideas live elsewhere in the tree (no dedicated module to point at).
Listed for citation integrity.

| # | Paper | Year | Mode | Where the insight lives in Lyra |
|---|---|:--:|:--:|---|
| 32 | [**Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols, and Harness Engineering**](https://arxiv.org/abs/2604.08224) — Zhou et al.<br/>*(not yet mirrored)* | 2026 | 🟢 | **Validates the Lyra thesis.** The survey's three-axis framing (memory / skills / protocols) is what [`docs/architecture/index.md`](../architecture/index.md) and the [14 building blocks](../reference/blocks-index.md) follow. No code derives from it directly. |
| 34 | [**Memento: Read-Write Reflective Learning**](https://arxiv.org/abs/2603.18743)<br/>*(not yet mirrored)* | 2026 | 🟢 | **Per-skill utility scoring + dream-daemon equivalent.** Filtered through Lyra's CLI-first / stdlib-only / leaf-package-first architecture (rejected the GUI shell, multi-IM gateway, separate vector store, fine-tuning loop). → [`lyra_core/skills/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills) extractor + curator · memo: [Memento-Skills](memento-skills.md) |
| 35 | [**Production Agent Gaps Survey**](https://arxiv.org/abs/2604.14228) — survey of 2025–26 fleet failure modes<br/>*(not yet mirrored)* | 2026 | 🟢 | **`pass^k` reliability metric (§12.1) + Reflexion gap (§12.3).** The survey told us *which* gaps in the 2025–26 fleet are systemic vs incidental. → [`lyra_core/eval/passk.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/passk.py), [`lyra_core/loop/reflexion.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/loop/reflexion.py) · memo: [Phase-J synthesis](../research-synthesis-phase-j.md) |

## Wave 5b — research backlog (NOT shipped in v3.5)

> **Honest scope marker.** The papers below are **not part of
> v3.5**. There is no Lyra code that absorbs them. They are listed
> here so a future contributor reading the codebase can find the
> design lineage if and when work begins, but **no row in this
> section corresponds to a feature you can invoke**. For things
> Lyra ships today, see [Features catalogue](../features.md) and
> [Use cases](../use-cases.md).
>
> Future versions are tracked in [Roadmap v1.5 → v2](../roadmap-v1.5-v2.md);
> these papers seed candidate slots, nothing more.

| # | Paper | Year | Mode | Notes |
|---|---|:--:|:--:|---|
| 26 | [**Meta-Harness: End-to-End Optimization of Model Harnesses**](https://arxiv.org/abs/2603.28052) — Lee, Nair, Zhang, Lee, Khattab, Finn<br/>*(not yet mirrored)* | 2026 | ⚪ | Candidate v2 headliner: a coding-agent proposer that searches over harness code itself. No code yet. |
| 27 | [**SWE-TRACE: Optimizing Long-Horizon SWE Agents through Rubric Process Reward Models and Heuristic Test-Time Scaling**](https://arxiv.org/abs/2604.14820) — Han et al.<br/>*(not yet mirrored)* | 2026 | ⚪ | Possible v1.5 verifier upgrade (rubric PRM scores). No code yet. |
| 28 | [**KLong: Training LLM Agent for Extremely Long-horizon Tasks**](https://arxiv.org/abs/2602.17547)<br/>*(not yet mirrored)* | 2026 | ⚪ | Long-horizon RL training; only the *checkpoint envelope* analogue ships today as [`lyra_core/klong/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/klong) (importable Python API), not the training side. |
| 30 | [**BACM-RL: Budget-Aware Context Management for Long-Horizon Search Agents**](https://arxiv.org/abs/2604.01664)<br/>*(not yet mirrored)* | 2026 | ⚪ | Bandit policy over compression strategies. No code yet. |
| 31 | [**Refute-or-Promote: Adversarial Stage-Gated Multi-Agent Review**](https://arxiv.org/abs/2604.19049)<br/>*(not yet mirrored)* | 2026 | ⚪ | Possible verifier upgrade (Phase-3 refute step). No code yet. |
| 33 | [**VeRO: An Evaluation Harness for Agents to Optimize Agents**](https://arxiv.org/abs/2602.22480)<br/>*(not yet mirrored)* | 2026 | ⚪ | Versioned harness snapshots + budget-controlled eval. The snapshot dataclass alone ships today as [`lyra_evals.snapshot`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/snapshot.py); the outer evaluation loop is unbuilt. |
| 36 | [**Agentless: 3-stage pipeline for software-issue resolution**](https://arxiv.org/abs/2405.15793)<br/>*(not yet mirrored)* | 2024 | ⚪ | Cost-sensitive Localize → Repair → Validate pipeline without an agent loop. No code yet. |
| 37 | [**Atomic Skills — Joint RL over 5 atomic skills for scaling coding agents**](https://arxiv.org/abs/2604.05013)<br/>*(not yet mirrored)* | 2026 | 🔴 | **Studied & rejected for v1.x.** Joint RL over atomic skills requires fine-tune access we don't have; revisit at v2 contingent on stable Meta-Harness baselines + open-weight candidates. → [`docs/architecture-tradeoff.md` §B.18](../architecture-tradeoff.md), [`docs/blocks/09-skill-engine-and-extractor.md`](../blocks/09-skill-engine-and-extractor.md) |

## Wave 6 — skills, evolution, safety & autonomy breakthroughs (May 2026 deep research)

New papers discovered during the 6-stream deep research initiative (2026-05-25/26). These
papers drive ULTRA PLANS 21–26 and represent the next frontier of Lyra's AGI ascent.

### 6a — Skills optimization & evolution

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 38 | [**SkillOpt: Executive Strategy for Self-Evolving Agent Skills**](https://arxiv.org/abs/2605.23904) — Yang et al. — Microsoft Research<br/>*(not yet mirrored)* | 2026 | 🟢 | **Text-space skill optimizer.** 8-step per-epoch loop (rollout→reflection→merge→LR-budget→validate→buffer→slow→meta). 52/52 benchmark cells won; +23.5pts avg gain. Separate optimizer/target model architecture. → `packages/lyra-cli/src/lyra_cli/skills/optimizer/skill_opt.py` (ULTRA PLAN 21) |
| 39 | [**AEvo: Harnessing Agentic Evolution**](https://arxiv.org/abs/2605.13821) — *(not yet mirrored)* | 2026 | 🟢 | **Meta-editing evolution.** Two-phase: meta-agent edits optimization procedure, harnessed segment runs candidates. +26% relative improvement. Drift prevention via harness-isolated evaluator + coarse-grained intervention. → `packages/lyra-cli/src/lyra_cli/skills/meta_evolution/` (ULTRA PLAN 21) |
| 40 | [**SkillOS: A Scalable Skill Management System for LLM Agents**](https://arxiv.org/abs/2605.06614) — *(not yet mirrored)* | 2026 | 🟡 | **RL-based skill curation.** GRPO-trained curator with composite reward (task outcome + function validity + content quality + compression). BM25 retrieval + LLM gate. → `packages/lyra-cli/src/lyra_cli/skills/lifecycle/curator.py` (ULTRA PLAN 21) |
| 41 | [**Ratchet: Outcome-Driven Skill Management for AI Agents**](https://arxiv.org/abs/2605.22148) — *(not yet mirrored)* | 2026 | 🟢 | **Lifecycle management with non-divergence guarantees.** Contribution scoring c(s), bounded active-cap C=50, rollback on regression, meta-skill authoring prior. Worst-case floor: E[p0] − 0.35. → `packages/lyra-cli/src/lyra_cli/skills/lifecycle/` (ULTRA PLAN 21) |
| 42 | [**SkillGen: Contrastive Skill Induction from Agent Trajectories**](https://arxiv.org/abs/2605.10999) — *(not yet mirrored)* | 2026 | 🟡 | **Paired intervention testing.** Embed and cluster failures vs successes, compare nearest neighbors, extract corrective rules. Gate threshold with g_abs + g_rel*m. → `packages/lyra-cli/src/lyra_cli/skills/lifecycle/synthesizer.py` (ULTRA PLAN 21) |
| 43 | [**MIND-Skill: Multi-Agent Induction of Reusable Agent Skills**](https://arxiv.org/abs/2605.08670) — *(not yet mirrored)* | 2026 | 🟡 | **3 textual losses jointly optimized.** Induction agent abstracts skills; deduction agent reconstructs trajectories to verify. Jointly optimized with TextGrad. → `packages/lyra-cli/src/lyra_cli/skills/optimizer/reflection.py` (ULTRA PLAN 21) |
| 44 | [**SkillForge: Automated Generation of Agent Skills**](https://arxiv.org/abs/2604.08618) — *(not yet mirrored)* | 2026 | 🟡 | **Automated skill generation pipeline.** → `packages/lyra-cli/src/lyra_cli/skills/lifecycle/synthesizer.py` (ULTRA PLAN 21) |
| 45 | [**SkillX: Hierarchical Skill Framework for LLM Agents**](https://arxiv.org/abs/2604.04804) — *(not yet mirrored)* | 2026 | 🟡 | **Three-tier hierarchy**: strategic plans → functional skills → atomic skills. → skill directory structure (ULTRA PLAN 21) |
| 46 | [**CoEvoSkills: Co-Evolution of Agent Skills and Environments**](https://arxiv.org/abs/2604.01687) — *(not yet mirrored)* | 2026 | ⚪ | Reference for co-evolution dynamics. → tracking only |
| 47 | [**Skills-Coach: Personalized Skill Recommendation for AI Agents**](https://arxiv.org/abs/2604.27488) — *(not yet mirrored)* | 2026 | ⚪ | Reference for skill recommendation. → tracking only |
| 48 | [**SkillMaster: Benchmarking Skill Management for LLM Agents**](https://arxiv.org/abs/2605.08693) — *(not yet mirrored)* | 2026 | ⚪ | Reference benchmark for skill management evaluation. → tracking only |
| 49 | [**Skill-R1: Reinforcement Learning for Skill Discovery in LLM Agents**](https://arxiv.org/abs/2605.09359) — *(not yet mirrored)* | 2026 | ⚪ | RL-based skill discovery. Requires fine-tune access. → tracking only |
| 50 | [**SkillClaw: Collective Skill Learning Across Multi-User Agent Ecosystems**](https://arxiv.org/abs/2604.08377) — *(not yet mirrored)* | 2026 | 🟡 | **Cross-user trajectory aggregation.** Multi-user skill ecosystem patterns. → `packages/lyra-cli/src/lyra_cli/skills/lifecycle/compactor.py` (ULTRA PLAN 21) |

### 6b — Safety, verification & adversarial robustness

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 51 | [**Knowing-Doing Gap: Why Agents Fail to Execute What They Know**](https://arxiv.org/abs/2605.14038) — *(not yet mirrored)* | 2026 | 🟢 | **Hidden-state confidence probing bridges 26-54% tool-use gap.** Agents frequently "know" the right action but don't execute it. → `packages/lyra-core/src/lyra_core/verifier/tool_audit.py` upgrade (ULTRA PLAN 25) |
| 52 | [**ARIS: Adversarial Review for Integrity and Safety**](https://arxiv.org/abs/2605.03042) — *(not yet mirrored)* | 2026 | 🟢 | **3-stage adversarial verification** (integrity→claim→audit). Already in lyra_verification/adversarial.py. Upgraded with MAVEN integration. → `packages/lyra-verification/src/lyra_verification/adversarial.py` (ULTRA PLAN 25) |
| 53 | [**Parallax: Cognitive-Executive Separation for Safe AI Agents**](https://arxiv.org/abs/2604.12986) — *(not yet mirrored)* | 2026 | 🟢 | **98.9% block rate.** Reasoning and execution in structurally separated contexts. → `packages/lyra-safety/src/lyra_safety/parallax.py` |
| 54 | [**RecursiveMAS: Latent-Space Multi-Agent Communication**](https://arxiv.org/abs/2604.25917) — *(not yet mirrored)* | 2026 | 🟢 | **75.6% token reduction, 1.2-2.4x speedup.** Latent-space inter-agent communication. → `packages/lyra-recursive-link/src/lyra_recursive_link/` |
| 55 | [**AutoResearchClaw: Self-Improving Research Agents**](https://arxiv.org/abs/2605.20025) — *(not yet mirrored)* | 2026 | 🟢 | **54.7% better than AI Scientist v2.** Pivot/Refine recovery + error database. → `packages/lyra-core/src/lyra_core/loop/pivot_refine.py` |
| 56 | [**PRISM: Prompt Drift Detection and Auto-Repair**](https://arxiv.org/abs/2605.14454) — *(not yet mirrored)* | 2026 | 🟢 | **Drift detection with auto-repair.** → `packages/lyra-evolution/src/lyra_evolution/drift_detector.py` |
| 57 | [**SR2AM: Self-Regulated Reasoning and Action Model**](https://arxiv.org/abs/2605.22138) — *(not yet mirrored)* | 2026 | 🟢 | **System I/II/III architecture, 8B matching 1T systems.** → `packages/lyra-reasoning/src/lyra_reasoning/sr2am/` |

### 6c — Agent autonomy & federation

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 58 | [**Tournament Test-Time Compute for Agentic Coding**](https://arxiv.org/abs/2604.16529) — Meta SI Labs et al. — already in Wave 1 as #1 | 2026 | 🟢 | Recursive Tournament Voting → `lyra_core/tts/tournament.py` |
| 59 | [**SemaClaw: General-Purpose Personal AI Agents**](https://arxiv.org/abs/2604.11548) — Midea AIRC — already in Wave 1 as #7 | 2026 | 🟢 | DAG teams + PermissionBridge → `lyra_core/adapters/dag_teams.py` |

> **Note**: Meta-Harness (#26 in Wave 5b) is promoted from ⚪ research backlog to 🟢 adopted
> in ULTRA PLAN 21. The agentic proposer over harness code achieves +7.7pts with 4x fewer
> tokens via filesystem-based history (500-5000x richer than text optimizers).

## Wave 7 — MemAgent Workshop (ICLR 2026) — Breakthrough Memory Architecture

20 papers from the ICLR 2026 Workshop on Memory for Agents (MemAgent), deep-read and synthesized
into [ULTRA PLAN 27](../../plans/LYRA_ULTRA_PLAN_27_MEMAGENT_BREAKTHROUGH_MEMORY.md) — an
8-layer cognitive memory stack that transforms Lyra's memory from passive storage-retrieval to
active, self-optimizing, neuroscience-grounded cognition.

### 7a — Memory Organization & Retrieval

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 60 | [**A-Mem: Agentic Memory for LLM Agents**](https://openreview.net/forum?id=FiM0M8gcct) — Rutgers / AIOS Foundation — MemAgent Workshop | 2026 | 🟢 | **Zettelkasten-inspired self-organizing notes.** 7-field note structure, autonomous link generation, memory evolution on write. Ranked #1 across 6 foundation models on LoCoMo. 93.6% token reduction vs MemGPT (2,520 vs 16,977). → `packages/lyra_memory/agentic/` (ULTRA PLAN 27.1) |
| 61 | [**MRAgent: Memory is Reconstructed, Not Retrieved**](https://openreview.net/forum?id=YPoHy6lgKP) — NUS — MemAgent Workshop | 2026 | 🟢 | **Active reconstruction via Cue-Tag-Content graph.** Iterative beam-search exploration with LLM-driven routing. Proof: H_passive ⊊ H_active (active strictly more expressive than passive). Up to 23% improvement on LoCoMo/LongMemEval. → `packages/lyra_memory/reconstruction/` (ULTRA PLAN 27.2) |
| 62 | [**LP-RAG: Link Prediction-based RAG**](https://openreview.net/forum?id=Y8Txo8vaH7) — Federal University of Ceará / USP — MemAgent Workshop | 2026 | 🟡 | **Retrieval as inductive link prediction.** Chunk-query graph with GNN-based link predictors supervised by synthetic queries. Consistently outperforms HippoRAG, GFM-RAG, NodeRAG. Model-agnostic. → `packages/lyra_memory/routing/lp_rag_retriever.py` (ULTRA PLAN 27.5) |
| 63 | [**Cost-Sensitive Store Routing**](https://openreview.net/forum?id=iGRGjdhl9r) — Independent — MemAgent Workshop | 2026 | 🟢 | **Store selection as routing problem.** 4 stores (STM/Summary/LTM/Episodic) with coverage/exact match/waste metrics. Oracle routing 86.7% accuracy with 62% fewer tokens (299 vs 787). Long context amplifies over-retrieval penalty. → `packages/lyra_memory/routing/` (ULTRA PLAN 27.5) |

### 7b — Cognitive Architecture & Neuroscience

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 64 | [**Human-Like Lifelong Memory**](https://openreview.net/forum?id=QufkvHbQs7) — Universidad de Guanajuato — MemAgent Workshop | 2026 | 🟢 | **Neuroscience-grounded architecture.** Valence vectors (5 components: emotional, associative, contextual, density, precision), thalamic gateway (6-channel salience: relevance, emotion, urgency, novelty, trust, goal affinity), System 1/2 router, CBT belief hierarchy (core→intermediate→automatic thoughts), cathartic update mechanism. → `packages/lyra_memory/cognitive/` (ULTRA PLAN 27.3) |
| 65 | [**CraniMem: Cranial-Inspired Gated & Bounded Memory**](https://openreview.net/forum?id=Tts94WVw40) — MemAgent Workshop | 2026 | 🟢 | **Dual-store (episodic buffer + KG) with RAS-inspired gating.** Utility-tagged scheduled consolidation replays high-utility traces into KG, prunes low-utility items. Noise drop of only 0.011 vs 0.027 (Vanilla RAG) and 0.036 (Mem0) on HotpotQA multi-hop. → `packages/lyra_memory/consolidation/` (ULTRA PLAN 27.8) |

### 7c — Optimization & Meta-Learning

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 66 | [**MemGrad: Memory-Guided Optimization via Abstracted Textual Gradients**](https://openreview.net/forum?id=GeaPE7iw1V) — TCS Research — MemAgent Workshop | 2026 | 🟢 | **Textual gradient descent on prompts via feedback abstraction.** Batch feedback → TextGradDecomposer → Role-Based Clustering → RoleBasedAbstractor → Retrospective (failure patterns) + Prospective (corrective intentions) dual memory. Applied to AgileCoder multi-agent development. → `packages/lyra_memory/optimization/` (ULTRA PLAN 27.4) |
| 67 | [**Feedback Descent: Open-Ended Text Optimization**](https://openreview.net/forum?id=Uw5G3H26ps) — MemAgent Workshop | 2026 | 🟡 | **Pairwise comparison with textual rationales.** Dimension-free convergence under idealized assumptions. Cross-domain: SVG design, prompt optimization, molecule discovery. Matches GEPA in prompt optimization, outperforms GRPO/REINVENT. → `packages/lyra_memory/optimization/feedback_descent.py` (ULTRA PLAN 27.4) |
| 68 | [**ERL: Experiential Reflective Learning**](https://openreview.net/forum?id=hQgSl6kj1W) — Illuin Technology — MemAgent Workshop | 2026 | 🟡 | **Heuristic generation from single-attempt trajectories.** No retries needed. LLM-based retrieval scoring at test time. +7.8% over ReAct baseline on Gaia2. Failure heuristics help Search, success heuristics help Execution. → `packages/lyra_memory/heuristics/` (ULTRA PLAN 27.8) |
| 69 | [**Curriculum Curation: Learning What to Learn**](https://openreview.net/forum?id=Qr5bhBbBOb) — MemAgent Workshop | 2026 | 🟡 | **Strategic task selection and ordering for test-time learning.** ~30% of training tasks match full-dataset performance. Hard→Easy ordering best for Test-Challenge, Random best for Test-Normal. ACE framework on AppWorld. → `packages/lyra_memory/curriculum/` (ULTRA PLAN 27.8) |

### 7d — Efficiency & Compression

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 70 | [**CoMem: Context Management with Decoupled Long-Context Model**](https://openreview.net/forum?id=tc9GAKlxQC) — MemAgent Workshop | 2026 | 🟢 | **k-step-off asynchronous pipeline.** Smaller memory model compresses history in background while agent decodes. GRPO-trained with functional equivalence reward. 1.4x latency improvement on SWE-Bench-Verified. → `packages/lyra_memory/async_pipeline/` (ULTRA PLAN 27.6) |
| 71 | [**Modular Compression: Agentic Memory Should Localize Compression**](https://openreview.net/forum?id=ztmwHisqJ4) — KAIST — MemAgent Workshop | 2026 | 🟢 | **Formal interference framework.** Δ_t(Q) ≤ ρ_t ε_t bound. Corollary: monolithic memory (K=1) → ρ_t≈1, unavoidable interference. 3 requirements: local compression, sparse routing, explicit composition. → `packages/lyra_memory/modular/` (ULTRA PLAN 27.7) |
| 72 | [**R-KVHash: KV Cache Compression via SimHash**](https://openreview.net/forum?id=UTRuEFJ57H) — MemAgent Workshop | 2026 | 🟡 | **Locality-sensitive hashing replaces Gram matrix.** O(n²d) → O(bn) complexity reduction. 2× higher decoding throughput than R-KV. Competitive on MATH500/GSM8K for DeepSeek-R1-Distill-Qwen. → `packages/lyra_memory/kv_cache/` (ULTRA PLAN 27.6) |
| 73 | [**Norm-Guided KV-Cache Eviction**](https://openreview.net/forum?id=xOW2jXDKG3) — MemAgent Workshop | 2026 | 🟡 | **Gradient-free l2-norm scoring.** Hybrid retention: 80% heavy-hitter pool + 20% recency pool. Identifies minimum viable budget effect. At budget 256 (87.5% reduction), sliding window outperforms norm-based on GSM8K. → `packages/lyra_memory/kv_cache/` (ULTRA PLAN 27.6) |
| 74 | [**LAR: Latent Action Reparameterization**](https://openreview.net/forum?id=nmFfyHEs76) — Multi-institution (Sydney, Montréal, Chicago, Fudan, Yale, Stanford) — MemAgent Workshop | 2026 | 🟡 | **Compact latent action space.** Each latent action = multi-step semantic behavior. Transition equivalence defines executable latent actions. Performance collapse threshold at abstraction boundary. → `packages/lyra_memory/abstraction/` (ULTRA PLAN 27.8) |

### 7e — Safety, Cross-Domain & Operations

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 75 | [**SABER: Safeguarding Mutating Steps**](https://openreview.net/forum?id=En2z9dckgP) — Amazon AGI — MemAgent Workshop | 2026 | 🟢 | **Mutating actions = 14-18% of steps but dominate failure.** Each additional mutating deviation reduces success odds by 55-96%. 3 mechanisms: Mutation-Gated User Verification, Targeted Reflection, Block-Based Context Cleaning. +28% relative on Airline, +11% on Retail (Qwen3-Thinking). Released τ-Bench Verified. → `packages/lyra_memory/safety/` (ULTRA PLAN 27.8) |
| 76 | [**Memory Transplants**](https://openreview.net/forum?id=AIJsjIqfsp) — UCSD / AIXC — MemAgent Workshop | 2026 | 🟡 | **Disentangles architecture from content.** 2×2 factorial design, 7 transplant conditions across code→math domain shift. Weaker models gain up to +15pp vs +7pp for stronger. 6 validation gates. → `packages/lyra_memory/transplant/` (ULTRA PLAN 27.8) |
| 77 | [**AOI: Multi-Agent Collaborative IT Operations**](https://openreview.net/forum?id=Q16XXJou3O) — MemAgent Workshop | 2026 | ⚪ | **3-agent architecture (Observer, Probe, Executor).** 3-layer memory: Raw (24h), Task Queue, Compressed Cache (7d). 72.4% context compression preserving 92.8% critical info. 94.2% task success rate, 34.4% MTTR reduction. → `packages/lyra_memory/operations/` (ULTRA PLAN 27.8) |

### 7f — Framework & Survey

| # | Paper | Year | Mode | Lyra implementation |
|---|---|:--:|:--:|---|
| 78 | [**From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms**](https://openreview.net/forum?id=l9Ly41xxPb) — MemAgent Workshop | 2026 | 🟢 | **3-stage evolutionary framework: Storage → Reflection → Experience.** Formal trajectory equation definitions. Active exploration and cross-trajectory abstraction as transformative mechanisms. Future directions: active memory perception, working memory organization, experience benchmarks, distributed shared memory, multimodal memory. → Framework for entire ULTRA PLAN 27 architecture |

> **Note**: One paper (um6VpjcOtj) could not be analyzed — the PDF returned corrupt/missing data
> from the OpenReview source. Its contribution remains unassessed.

> **Note**: Papers #60–78 correspond to the ICLR 2026 MemAgent Workshop. All 19 analyzable papers
> are mapped to specific Lyra modules and phases in ULTRA PLAN 27. The plan synthesizes these into
> an 8-layer cognitive memory stack with formal interference guarantees (Δ_t ≤ ρ_t ε_t),
> active reconstruction (H_passive ⊊ H_active), and neuroscience-grounded cognitive architecture.

These are talks, model-card releases, and industry signals that
inform the design but don't have a single "Lyra implementation"
file. They live here so any code citation can link back.

- **Harness Engineering talk** — Ryan Leopo (OpenAI), 2026 — *"Code is Free / scarce resources are Human Time, Attention, Context Window"*. The manifesto in [`docs/novel-ideas.md` §0](../novel-ideas.md). Mode: 🟢 — quoted as the v1.x opening thesis.
- **OpenAI GPT-5.5** — 82.7% on Terminal-Bench 2.0, 84.9% on GDPval. Mode: ⚪ — used as the smart-slot default candidate in [`lyra_cli/llm_factory.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/llm_factory.py).
- **Z.AI GLM-5.1** — 754 B open-weight, SOTA on SWE-bench Pro, 8-hour autonomous execution. Mode: ⚪ — open-weight benchmark for the v2 self-hosted profile.
- **OSS coding-agent stars (April 2026)** — Cline ~58 k, Aider ~39 k, OpenHands ~65 k. Mode: ⚪ — context for [`docs/community-ecosystem.md`](../community-ecosystem.md) market sizing.

## How to read this matrix

Three angles:

1. **"What papers does Lyra read?"** → walk the table top-to-bottom; every paper cited *anywhere* in `docs/`, `CHANGELOG.md`, or the source tree is here.
2. **"How does Lyra use Paper X?"** → find the row, read the *Lyra implementation* / *Notes* column. For the *why*, click the linked design memo if one exists.
3. **"What's the gap between research and code?"** → scan the *Mode* column. 🟢 = shipped, 🟡 = pattern adopted, ⚪ = reference / motivation only, 🔴 = rejected with reasoning. Anything in §"Wave 5b — research backlog" or §Wave 5a marked ⚪ has **no code in v3.5** — it's there for citation integrity, not as a feature claim.

## How citations work in Lyra

Every paper above is cited inline somewhere:

| Citation surface | Example |
|---|---|
| Module docstring | [`lyra_core/memory/reasoning_bank.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/reasoning_bank.py) opens with the `arXiv:2509.25140` ref |
| Concept page | [`docs/concepts/reasoning-bank.md`](../concepts/reasoning-bank.md) links the paper + PDF + this index |
| Block spec | [`docs/blocks/07-memory-three-tier.md`](../blocks/07-memory-three-tier.md) references the paper for the L3 design |
| `novel-ideas.md` | Section-by-section traceability table |
| `roadmap-v1.5-v2.md` | Future-version anchors |
| `THIRD_PARTY_NOTICES.md` | License attribution for vendored / pattern-mined code |

If you find an unattributed idea in the source, that's a bug — please
file an issue against [`lyra-contributors/lyra`](https://github.com/lyra-contributors/lyra).

## Companion: reference repositories

For the parallel matrix of every **GitHub repo** Lyra references —
community ecosystem, paper reference implementations, model weights,
adjacent infrastructure — see [Reference repositories](repos.md).

## Reproducing the local PDF mirror

Waves 1–3 are mirrored locally; Wave 4 + Wave 5 (validation + backlog)
are listed but not yet bulk-pulled. Re-run with:

```bash
mkdir -p projects/lyra/papers && cd projects/lyra/papers
ids=(
  # Wave 1 — capabilities core
  "2604.16529:meta-tts-agentic-coding"
  "2604.18002:ngc-neural-garbage-collection"
  "2604.15771:skill-rag"
  "2506.19807:knowrl"
  "2509.25140:reasoningbank-mattS"
  "2402.07867:poisonedrag"
  "2604.11548:semaclaw-midea-airc"
  # Wave 2 — performance edges
  "2410.20285:swe-search-mcts"
  "2506.13131:alphaevolve"
  "2305.05176:frugalgpt"
  "2406.18665:routellm"
  "2502.11021:confidence-driven-llm-router"
  "2305.16291:voyager"
  "2303.11366:reflexion"
  "2308.00352:metagpt"
  "2307.07924:chatdev"
  "2310.03714:dspy"
  "2503.01840:eagle3-spec-decoding"
  "2404.07972:osworld"
  "2510.04374:gdpval"
  "2501.07301:qwen-process-reward-lessons"
  "2107.03374:codex-evaluating-llm-trained-on-code"
  # Wave 3 — diversity-collapse hardening
  "2604.18005:diversity-collapse-mas"
  # Wave 4 — multi-agent cache sharing + long-horizon eval
  "2604.24971:polykv-shared-kv-pool"
  "2604.24026:calm-continuous-autoregressive"
  "2603.06358:locoeval"
  # Wave 5a — validation papers (insights absorbed elsewhere)
  "2604.08224:externalization-survey"
  "2603.18743:memento-rwrl"
  "2604.14228:production-agent-gaps-survey"
  # Wave 5b — research backlog (NOT shipped in v3.5)
  "2603.28052:meta-harness"
  "2604.14820:swe-trace"
  "2602.17547:klong"
  "2604.01664:bacm-rl"
  "2604.19049:refute-or-promote"
  "2602.22480:vero"
  "2405.15793:agentless"
  "2604.05013:atomic-skills-scaling-coding-agents"
)
for pair in "${ids[@]}"; do
  id="${pair%%:*}"; name="${pair##*:}"
  curl -fsSL "https://arxiv.org/pdf/${id}" -o "${name}.pdf"
done
```

## Suggested reading order

For the full design narrative, walk the waves in order:

### Wave 1 — capabilities

1. **SemaClaw** (#7) — the harness-engineering frame (validates Lyra's bet).
2. **Meta TTS for Agentic Coding** (#1) — the test-time-scaling story.
3. **ReasoningBank + MaTTS** (#2) — the memory side of the same coin.
   ([Lyra concept page →](../concepts/reasoning-bank.md))
4. **Skill-RAG** (#3) — failure-aware retrieval routing.
5. **NGC** (#5) — what to forget while reasoning.
6. **KnowRL** (#4) — factuality reward for reasoning steps.
7. **PoisonedRAG** (#6) — the attack surface every harness has to defend.

### Wave 2 — performance edges

8. **SWE-Search** (#8) — intra-attempt MCTS, +23 % SWE-bench across 5 models.
9. **FrugalGPT → RouteLLM → Confidence-Driven Router** (#10–12) — three-step evolution of the cascade-routing idea.
   ([Lyra concept page →](../concepts/two-tier-routing.md))
10. **MetaGPT** (#15) then **ChatDev** (#16) — assembly-line and waterfall multi-agent SDLC for the Org Mode.
11. **Voyager** (#13) — automatic curriculum + skill library; the missing planner on top of Skill-Creator v2.
12. **Codex pass@k** (#22) + **Qwen PRM lessons** (#21) — eval mechanics.
13. **OSWorld** (#19) — what a real computer-use benchmark looks like (12% best agent vs. 72% human — wide-open headroom).
14. **GDPval** (#20) — the OpenAI economic-value benchmark; the new bar.
15. **EAGLE-3** (#18) — speculative decoding; the silent ×6 speedup for self-host profiles.

### Wave 3 — cross-cutting hardening

16. **Diversity Collapse in Multi-Agent LLM Systems** (#23) — ACL 2026 Findings; the failure mode every multi-agent harness has to defend, and the structural prescription (NGT + Subgroups + Vertical persona mix) Lyra adopts as a default.
    ([Lyra companion analysis →](diversity-collapse-analysis.md))

### Wave 4 — multi-agent cache sharing + long-horizon eval

17. **PolyKV** (#24) — *architectural insight* absorbed as the hosted-API `PromptCacheCoordinator`. The literal mechanism (self-hosted KV-pool sharing) doesn't reach a hosted-API harness; the forward-compat shim was deleted in v3.5.5.
    ([Lyra evaluation memo →](polykv-evaluation.md))
18. **CALM** (#25) — studied and rejected. Modelling-side change with no harness-side seam; the earlier `BlockStreamingProvider` and `BrierLM` shims were deleted in v3.5.5 because no upstream emerged.
    ([Lyra evaluation memo →](calm-evaluation.md))
19. **LoCoEval** (#29) — long-horizon repo-conversation driver shipped as the `lyra evals --suite loco-eval` adapter.

### Wave 5a — validation papers (insights live elsewhere)

20. **Externalization survey** (#32) — the meta-frame that says "harness IS the integration layer"; informs the architecture index and the 14-blocks taxonomy.
21. **Memento RWRL** (#34) — per-skill utility scoring + dream-daemon-equivalent absorbed into the skills extractor + curator. ([memo](memento-skills.md))
22. **Production agent gaps survey** (#35) — meta-frame for Phase J's `pass^k` and Reflexion adoption.

### Wave 5b — research backlog (not shipped, listed for citation only)

23. **Meta-Harness** (#26), **SWE-TRACE** (#27), **Refute-or-Promote** (#31), **KLong** (#28), **BACM-RL** (#30), **VeRO** (#33), **Agentless** (#36) — papers Lyra has read whose absorption is **not part of v3.5**. They seed candidate slots in [Roadmap v1.5 → v2](../roadmap-v1.5-v2.md); none have code in this release.
24. **Atomic Skills** (#37) — studied, rejected for v1.x, revisit at v2.

### Stretch / context

27. **Reflexion** (#14) — the verbal-RL ancestor of ReasoningBank.
28. **DSPy** (#17) — programmatic LM-pipeline compilation (§11.2 stretch).
29. **AlphaEvolve** (#9) — DeepMind's evolutionary coding agent; long-tail inspiration for sample-and-rank-with-verifier.
