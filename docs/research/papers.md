---
title: Reference papers
description: Annotated bibliography of every paper Lyra reads — with the absorption mode and the exact file in Lyra each technique landed in.
---

# Reference papers <span class="lyra-badge reference">reference</span>

Lyra ships a local mirror of the arxiv papers cited across the
codebase under [`papers/`](https://github.com/lyra-contributors/lyra/tree/main/projects/lyra/papers)
(22 PDFs mirrored to date; Wave-4/5 entries not yet bulk-mirrored,
pull them with the script at the bottom). This page is the
**canonical bibliography + absorption matrix** — every paper
referenced anywhere in `docs/`, `CHANGELOG.md`, or the source tree
is listed here with:

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

## Wave 0 — primary sources we cite but don't classify

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
