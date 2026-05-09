---
title: Reference repositories
description: Canonical absorption matrix for every GitHub repository Lyra references — Claude-Code ecosystem, paper reference impls, adjacent infrastructure, model weights, and benchmark corpora.
---

# Reference repositories <span class="lyra-badge reference">reference</span>

Lyra is downstream of a substantial open-source ecosystem. This page
is the **canonical absorption matrix** for every GitHub repository
referenced anywhere in Lyra's `docs/`, `CHANGELOG.md`, or source
tree. For each repo we list:

- **License** (so the vendoring policy is unambiguous)
- **Lyra absorption mode** (what we did with it)
- **Lyra implementation** (the exact file or planned slot the
  technique landed in)

The companion [Reference papers](papers.md) page does the same job
for every paper. The companion [Community ecosystem](../community-ecosystem.md)
page documents the *vendoring policy* (the three integration tiers
and license gates); this page documents the *data* (which specific
repos sit at which tier).

## Absorption legend

| Symbol | Mode | Meaning |
|:--:|---|---|
| 🟢 | **Vendored** | Files copied into `packages/lyra-skills/.../packs/community/<repo>/` with per-file license header preserved + `THIRD_PARTY_NOTICES.md` attribution |
| 🟡 | **Pattern-mined** | Read upstream docs / `SKILL.md`, distilled the *idea*, re-implemented Lyra-native; no code copy |
| 🔵 | **Optional integration** | Wrapped behind a small shim; user installs upstream separately and Lyra calls it via subprocess |
| 🟠 | **Tracked** | No integration yet; on the watch list for a specific future version |
| ⚪ | **Reference only** | Cited as paper reference impl, benchmark corpus, model weight, or industry signal — we read it, don't run it |
| 🔴 | **Studied & rejected** | Considered; deliberately not adopted (reasoning recorded in the link target) |

License gates: `MIT`, `Apache-2.0`, `BSD-2`, `BSD-3`, `ISC` are the
default allowlist. `AGPL`, source-available, or `Mixed` repos are
**pattern-mine only** (Tier 1) — never vendored. See
[`docs/community-ecosystem.md` § License gates](../community-ecosystem.md#license-gates).

## A. Claude-Code / coding-agent ecosystem

The 13-repo verdict matrix from the v3.5 community pass. These are
the repos a Lyra user might compare us against or want to combine
with us.

| # | Repo | Claimed ★ | License | Mode | Lyra implementation |
|---|------|----------:|---------|:--:|---|
| A1 | [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 153k | MIT | 🟡 | Curated link list — patterns harvested for [`docs/community-ecosystem.md`](../community-ecosystem.md). |
| A2 | [obra/superpowers](https://github.com/obra/superpowers) | 148k | MIT | 🟢 | Selected skills under `packages/lyra-skills/src/lyra_skills/packs/community/superpowers/` (per-skill license check). |
| A3 | [anthropics/skills](https://github.com/anthropics/skills) | 117k | **Mixed** | 🟢 | MIT skills only vendored under `packs/community/anthropics/`; **DO NOT vendor** docx/pdf/pptx/xlsx packs (source-available, not OSS). Skill-Creator v2 pattern → [v1.7 Phases 19–22](../roadmap-v1.5-v2.md). |
| A4 | [dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | 73k | MIT | 🟡 | Patterns folded into the 4-mode prompt enrichment (CoT, ReAct, self-consistency, prompt chaining). → [`docs/start/four-modes.md`](../start/four-modes.md). |
| A5 | [VonHoltenCodes/get-shit-done](https://github.com/VonHoltenCodes/get-shit-done) | 51k | MIT | 🟡 | Workflow patterns mined; one skill (`gsd-spec-loop`) candidate for vendoring. |
| A6 | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | 49k | **AGPL-3.0** | 🔵 | Hard-reject for code import; documented as optional companion (run upstream + read its DB via shim). → planned: `docs/integrations/claude-mem.md`. |
| A7 | [chuanqi-shi/awesome-design-md](https://github.com/chuanqi-shi/awesome-design-md) | 45k | MIT | ⚪ | Reference-only link in the lyra-skills docs (design.md format study, not skills). |
| A8 | [ArtemKulakov/claude-code-best-practice](https://github.com/ArtemKulakov/claude-code-best-practice) | 38k | MIT | 🟡 | Patterns folded into the 4-mode prompt enrichment. |
| A9 | [yamadashy/repomix](https://github.com/yamadashy/repomix) | 23k | MIT | 🔵 | Wrapped as `lyra pack` shim that calls the upstream binary. → planned: `docs/integrations/repomix.md`. |
| A10 | karpathy-skills *(repo URL unverified)* | 19k | unverified | 🟠 | Pending license inspection; if MIT, vendor selectively under `packs/community/karpathy/`. |
| A11 | [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) | 17k | MIT | 🟢 | Selected subagent presets under `packs/community/voltagent/`. → [`lyra_core/subagent/presets.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/subagent/presets.py). |
| A12 | [jarrodwatts/claude-hud](https://github.com/jarrodwatts/claude-hud) | — | MIT | 🟡 | Pattern-mined for `lyra hud`; do NOT run upstream (deep Claude Code stdin/transcript dependency). → [`lyra_cli/hud/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/hud), how-to: [Customize the HUD](../howto/customize-hud.md). |

> **Star counts caveat:** the user-supplied numbers above are
> mostly inflated 10×–100× vs. GitHub-API ground truth (May 2026
> verification). Treat them as relative ordering, not absolute.
> See [`docs/community-ecosystem.md` § Star-count caveat](../community-ecosystem.md#star-count-caveat).

## B. Paper reference implementations

Repos that are the canonical implementation of a paper Lyra cites.
Most are reference-only (we read them to understand the paper, then
re-implement Lyra-native).

| Repo | License | Paper | Mode | Lyra implementation |
|------|---------|-------|:--:|---|
| [aorwall/moatless-tree-search](https://github.com/aorwall/moatless-tree-search) | Apache-2.0 | [SWE-Search #8](papers.md#wave-2--performance-edges) | 🟡 | Studied; intra-attempt MCTS pattern reshaped into deterministic tournament rounds. → [`lyra_core/tts/tournament.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/tts/tournament.py) |
| [aorwall/moatless-tools](https://github.com/aorwall/moatless-tools) | Apache-2.0 | (companion to moatless-tree-search) | ⚪ | Minimal-context / symbol-level retrieval — reference for [`docs/roadmap-v1.5-v2.md`](../roadmap-v1.5-v2.md) v1.7 Phase 17. |
| [facebookresearch/swe-rl](https://github.com/facebookresearch/swe-rl) | (NeurIPS 2025) | RL on software-evolution with rule-based rewards | ⚪ | Reference-only; informs the verifier's TDD-reward signal shape. → [`lyra_core/verifier/tdd_reward.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/tdd_reward.py) |
| [MineDojo/Voyager](https://github.com/MineDojo/Voyager) | MIT | [Voyager #13](papers.md#wave-2--performance-edges) | 🟡 | Skill-library pattern + automatic curriculum + iterative prompting. → [`lyra_core/memory/procedural.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/memory/procedural.py), `packages/lyra-skills/`, concept: [Skills](../concepts/skills.md). |
| [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) | MIT | [DSPy #17](papers.md#wave-2--performance-edges) | 🟡 | GEPA-style optimiser pattern reused; no DSPy import (stdlib-only re-impl). → [`lyra_core/evolve/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/evolve), CLI: `lyra evolve`. |
| [geekan/MetaGPT](https://github.com/geekan/MetaGPT) | MIT | [MetaGPT #15](papers.md#wave-2--performance-edges) | 🟡 | SOP-driven role topology (PM/Architect/Engineer/Reviewer/QA). → [`lyra_core/teams/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/teams), CLI: `/team`. |
| [OpenBMB/ChatDev](https://github.com/OpenBMB/ChatDev) | Apache-2.0 | [ChatDev #16](papers.md#wave-2--performance-edges) | 🟡 | Waterfall multi-agent SDLC pattern; optional waterfall preset of the team scheduler. → [`lyra_core/teams/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/teams). |
| [Xtra-Computing/MAS_Diversity](https://github.com/Xtra-Computing/MAS_Diversity) | (research code) | [Diversity Collapse #23](papers.md#wave-3--diversity-collapse-hardening) | ⚪ | Reference impl read for the Wave-3 hardening pass. → memo: [Diversity collapse analysis](diversity-collapse-analysis.md). |
| [Memento-Teams/Memento-Skills](https://github.com/Memento-Teams/Memento-Skills) | (mixed) | [Memento RWRL #34](papers.md#wave-5a--validation-papers-insights-absorbed-no-new-module) | 🟡 | Filtered through Lyra's CLI-first / stdlib-only architecture (rejected the GUI shell, multi-IM gateway, separate vector store). Read-Write Reflective Learning loop adopted. → [`lyra_core/skills/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills), memo: [Memento-Skills](memento-skills.md). |

## C. Adjacent infrastructure

OSS projects that deliver pieces of the same agent-stack as Lyra,
without being a competing harness.

| Repo | License | Role | Mode | Lyra implementation |
|------|---------|------|:--:|---|
| [TencentCloud/CubeSandbox](https://github.com/TencentCloud/CubeSandbox) | Apache-2.0 (April 2026, v0.1.0) | RustVMM + KVM microVM, sub-60 ms cold start, < 5 MB RAM/instance, eBPF egress; drop-in E2B SDK | 🟠 | **v1.9 MicroVM execution backend.** Tencent-tested at 100 K+ instances. Slot reserved in [`docs/novel-ideas.md` §3.5](../novel-ideas.md). |
| [ghostwright/phantom](https://github.com/ghostwright/phantom) | Apache-2.0 (~1.3 k ★) | Persistent autonomous AI co-worker on a dedicated VM; 17+ MCP tools; self-evolution loop | 🟠 | **v2.5 stretch — `lyra serve --watch` daemon.** Pattern reference for the persistent-worker mode. |
| [eric-tramel/moraine](https://github.com/eric-tramel/moraine) | OSS (~31 ★, early but the *interface* is right) | "Unified realtime agent trace database & search MCP" | 🟠 | **v2.5 cross-harness trace federation.** Reads any HIR-compatible trace and exposes search/recall as MCP tools across harness boundaries. → [`docs/novel-ideas.md` §3.8](../novel-ideas.md). |
| [midea-ai/SemaClaw](https://github.com/midea-ai/SemaClaw) | TS reference impl | Reference TypeScript impl of the [SemaClaw paper #7](papers.md#wave-1--original-eight-selling-points) | ⚪ | Read; their DAG-Teams + PermissionBridge mirror Lyra's. → [`lyra_core/adapters/dag_teams.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/adapters/dag_teams.py). |
| [garrytan/gbrain](https://github.com/garrytan/gbrain) *(closed-source for now)* | (closed) | Self-wiring knowledge graph (April 2026) — stated +5% precision / +11% recall / +28% graph search / −53% noise | 🟡 | **`lyra brain` brain bundles.** Adopt the *pattern* (not the code; closed-source). → [`lyra_core/brains/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/brains), CLI: `lyra brain list|show|install`. |
| [withseismic/claude-mem](https://github.com/withseismic/claude-mem) | (per-repo) | Claude Code memory daemon — different repo than [`thedotmack/claude-mem`](https://github.com/thedotmack/claude-mem) above | 🟡 | Pattern-mined for the L1 working memory + SOUL.md context layer design. → [`lyra_core/context/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/context), concept: [Context engine](../concepts/context-engine.md). |
| [lyra-contributors/gnomon-hir](https://github.com/lyra-contributors/gnomon-hir) | MIT (Lyra-internal) | Reference impl of the HIR (Harness Interaction Records) trace schema | 🟢 | **HIR trace schema + emitter.** Lyra's observability layer is the canonical Gnomon-HIR consumer. → [`lyra_core/hir/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/hir), [`lyra_core/observability/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability), concept: [Observability and HIR](../concepts/observability.md). |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | (per-repo) | Hermes Agent — lifecycle hooks, skill curator, ContextVars for concurrent tools | 🟡 | **Pattern-mined extensively** (v1.7 Phase-4a absorption). → [`lyra_core/concurrency.py::submit_with_context`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/concurrency.py), [`lyra_core/skills/curator.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills/curator.py). |
| [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch) *(repo URL TBD)* | (per-repo) | GEPA-style self-evolution arena | 🟡 | **`lyra evolve` GEPA-style evolver** (Pareto-filtered score↑ vs length↓). → [`lyra_core/evolve/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/evolve), CLI: `lyra evolve`. |

## D. Skills + MCP ecosystem

Repos that supply skills, skill registries, or MCP-protocol pieces.

| Repo | License | Role | Mode | Lyra implementation |
|------|---------|------|:--:|---|
| [anthropics/skills](https://github.com/anthropics/skills) | Mixed | Anthropic's official skill packs (incl. Skill-Creator v2 meta-skill, 121K ★ / 176K installs) | 🟢 | **Skill-Creator v2 4-agent loop** (Executor / Grader / Comparator / Analyzer). → [`lyra_core/skills/curator.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/skills/curator.py), [v1.7 Phases 19–22](../roadmap-v1.5-v2.md). MIT skills only vendored. |
| [skills-mcp/skills-mcp](https://github.com/skills-mcp/skills-mcp) | (per-repo) | MCP-portable skill registry pattern | 🟡 | Pattern reference for the federated skill registry (v2 Phase 26). → [`lyra_core/skills/federation.py`](https://github.com/lyra-contributors/lyra/) (planned). |
| [Memento-Teams/Memento-Skills](https://github.com/Memento-Teams/Memento-Skills) | (mixed) | Read-Write Reflective Learning + per-skill utility scoring + dream-daemon | 🟡 | See § B above. |

## E. Model weights + benchmark corpora

Read for benchmarking, eval, or as the smart-slot routing target.

| Resource | License / Source | Role | Mode | Lyra implementation |
|------|---------|------|:--:|---|
| [openai/SWELancer-Benchmark](https://github.com/openai/SWELancer-Benchmark) | (OAI) | $1M of real Upwork tasks; Diamond split ($500K) is open-source | ⚪ | Reference benchmark for the v2 release notes. → tracked in [`docs/benchmarks.md`](../benchmarks.md). |
| [sierra-research/tau2-bench](https://github.com/sierra-research/tau2-bench) | (per-repo) | τ-bench / τ³-bench — airline / retail / telecom / banking / voice; even GPT-4 < 50% pass-1, ~25% pass-8 | 🟢 | **τ-Bench JSONL adapter** (Phase 6 of v1.8). → [`lyra-evals/adapters/tau_bench.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters/tau_bench.py). The `pass^k` reliability metric is from τ-bench's `yao2024taubench`. → [`lyra_core/eval/passk.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/eval/passk.py). |
| [harbor-framework/terminal-bench-2](https://github.com/harbor-framework/terminal-bench-2) ([t-bench.com](https://t-bench.com/)) | (per-repo) | Terminal-Bench 2.0 — 89 hard CLI tasks, used by every frontier lab | 🟢 | **Terminal-Bench 2.0 JSONL adapter + submission writer** (Phase 7 of v1.8). → [`lyra-evals/adapters/terminal_bench.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-evals/src/lyra_evals/adapters/terminal_bench.py). |
| [openai/prm800k](https://github.com/openai/prm800k) | (OAI) | 800k step-level correctness labels for PRM training | ⚪ | Reference dataset; informs the design of [`lyra_core/verifier/prm.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/verifier/prm.py). |
| [deepseek-ai/DeepSeek-R1](https://github.com/deepseek-ai/DeepSeek-R1) | MIT | RL-trained reasoning model, MIT-licensed weights | ⚪ | Reference smart-slot candidate. → [`lyra_cli/llm_factory.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/llm_factory.py). |
| `yuhuili/EAGLE3-LLaMA3.3-Instruct-70B` (HuggingFace) | (HF model card) | Validated EAGLE-3 draft head for Llama 3.3 70B | 🟠 | **Reserved for v2.x self-hosted speculative-decoding adapter.** → [paper #18](papers.md#wave-2--performance-edges). |
| [`dair-ai/Prompt-Engineering-Guide`](https://github.com/dair-ai/Prompt-Engineering-Guide) | MIT | Prompting bible (also in §A above) | 🟡 | (See A4.) |

## F. Industry signals (model releases, talks, market)

Cited but not vendored, not benchmarked, not pattern-mined — kept
for context only.

| Signal | Where it lands | Mode |
|------|---|:--:|
| **Harness Engineering talk** — Ryan Leopo (OpenAI), 2026 — *"Code is Free / scarce resources are Human Time, Attention, Context Window"* | The opening manifesto in [`docs/novel-ideas.md` §0](../novel-ideas.md). | ⚪ |
| **OpenAI GPT-5.5** — 82.7% on Terminal-Bench 2.0, 84.9% on GDPval | Smart-slot default candidate in [`lyra_cli/llm_factory.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-cli/src/lyra_cli/llm_factory.py). | ⚪ |
| **Z.AI GLM-5.1** — 754 B open-weight, SOTA on SWE-bench Pro, 8-hour autonomous execution | Open-weight benchmark for v2 self-hosted profile. | ⚪ |
| **OSS coding-agent stars (April 2026)** — Cline ~58 k, Aider ~39 k, OpenHands ~65 k | Market sizing context for [`docs/community-ecosystem.md`](../community-ecosystem.md). | ⚪ |

## How to read this matrix

Three angles:

1. **"What repos does Lyra read?"** → walk top-to-bottom; every
   repo cited *anywhere* in `docs/`, `CHANGELOG.md`, or the source
   tree is here.
2. **"What did we do with Repo X?"** → find the row, read the
   *Mode* + *Lyra implementation* columns. 🟢 = files in our tree,
   🟡 = idea reused without copy, 🔵 = optional companion via shim,
   🟠 = future-version slot reserved, ⚪ = reference-only,
   🔴 = studied & rejected.
3. **"Which OSS license rules govern this?"** → see the *License*
   column + [`docs/community-ecosystem.md` § License gates](../community-ecosystem.md#license-gates) + [`THIRD_PARTY_NOTICES.md`](https://github.com/lyra-contributors/lyra/blob/main/THIRD_PARTY_NOTICES.md).

## Companion: reference papers

For the parallel matrix of every **arxiv paper** Lyra references
(37 papers across Waves 1–5), see [Reference papers](papers.md).

## How to add a new repo to this matrix

When evaluating a new community repo:

1. Verify its star count via `gh api repos/<owner>/<repo>`.
2. Check the license — `gh api repos/<owner>/<repo>/license`.
3. Pick the correct section (A–F) based on what the repo *is*.
4. If MIT/Apache/BSD: skim 5–10 SKILL.md files for quality; pick
   1–3 to vendor under `packs/community/<repo>/`.
5. If AGPL or source-available: pattern-mine only; document the
   *idea* under the relevant `docs/research/<topic>.md` design memo.
6. Add a row above with verdict + a paragraph below if the repo
   warrants explanation.
7. Append the appropriate attribution to
   [`THIRD_PARTY_NOTICES.md`](https://github.com/lyra-contributors/lyra/blob/main/THIRD_PARTY_NOTICES.md).

## See also

- [Reference papers](papers.md) — the same shape for arxiv papers.
- [Community ecosystem](../community-ecosystem.md) — the policy and
  process layer (vendoring tiers, license gates) that backs this
  matrix.
- [`THIRD_PARTY_NOTICES.md`](https://github.com/lyra-contributors/lyra/blob/main/THIRD_PARTY_NOTICES.md) — per-vendored-file licenses + attribution.
- [`packages/lyra-skills/src/lyra_skills/installer.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-skills/src/lyra_skills/installer.py) — `LICENSE_ALLOWLIST` enforcement.
- [`CONTRIBUTING.md`](https://github.com/lyra-contributors/lyra/blob/main/CONTRIBUTING.md) § "Skills (SKILL.md)" — author-facing rules.
