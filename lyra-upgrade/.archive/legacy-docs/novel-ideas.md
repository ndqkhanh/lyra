# Lyra — Novel Ideas Plan ("Beyond Test-Time Scaling")

> **Status:** living document, v0.6 snapshot 2026-04-24 (**v1.8 close-out**: `ReasoningBank.record/recall/matts_prefix` and `SkillRagRouter.answer` are now behavioural; `lyra_core.org` ships its Pareto-safe defaults; `default_prm_adapter()` ships its no-network heuristic fallback; **all 9 v1.8 Phase-0 RED tests are now GREEN — 0 strict-xfail remaining**). v0.5 (2026-04-24): Wave 2 added; Wave-3 diversity-collapse hardening folded in; Phase 6 diversity wiring landed for `TournamentTts` + `ReasoningBank.recall`; **τ-Bench (Phase 6) and Terminal-Bench 2.0 (Phase 7) JSONL adapters landed** — both loaders + submission writers.
> **Companion to** [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md). The existing roadmap closes the **April-2026 parity gaps** (v1.5), ships the **Self-Creating Harness** (v1.7), and builds the **Self-Evolving Harness** (v2). This document proposes **eight Wave-1 selling points** (§3), **seven Wave-2 performance edges** (§8), and a **Wave-3 cross-cutting hardening** (§10) against multi-agent diversity collapse — sixteen net-new commitments in total, each *beyond* what the existing roadmap or any of {Claude Code, OpenClaw, Hermes, ARIA} ships today.
> **Papers cited here are mirrored under** [`../papers/`](../papers/) (22 PDFs, ~145 MB).
> **House rules:** every feature is RED-tested before code; one milestone per 4–6 weeks; the repo stays usable at every phase boundary; we dogfood each feature inside Lyra itself before shipping.
> **See also:** [`research/diversity-collapse-analysis.md`](research/diversity-collapse-analysis.md) — the full mapping of every Lyra parallel/multi-agent subsystem against [arXiv:2604.18005](https://arxiv.org/abs/2604.18005) (Chen et al., ACL 2026 Findings).

---

## TL;DR — eight features, each beats one of {Claude Code, OpenClaw, Hermes, ARIA} on a specific axis

| # | Feature | Beats… on… | Inspiration | Slot |
|---|---|---|---|---|
| 1 | **Tournament-Distilled Test-Time Scaling** for coding tasks | Claude Code (sequential only), Hermes (no parallel TTS), ARIA (no TTS) | Kim et al., Meta SI Labs — [2604.16529](https://arxiv.org/abs/2604.16529) | v1.8 |
| 2 | **ReasoningBank with failure distillation + MaTTS** | Hermes (success-only memory), OpenClaw (skills are user-authored), Claude Code (no persistent reasoning memory) | Google Research — [2509.25140](https://arxiv.org/abs/2509.25140) | v1.8 |
| 3 | **Skill-RAG: Hidden-State Prober + 4-skill Recovery Router** | All routers (keyword / embedding / BM25) — none detect "I don't know" before retrying | Univ. Michigan / UPenn — [2604.15771](https://arxiv.org/abs/2604.15771) | v1.8 (extends v1.7 Phase 20) |
| 4 | **TDD-Reward Inference Signal** (KnowRL-for-coding) | All harnesses that have TDD as a *soft prompt* — Lyra makes it a *numeric reward* gate | Zhejiang Univ — [2506.19807](https://arxiv.org/abs/2506.19807) | v1.8 |
| 5 | **MicroVM Execution Backend** (CubeSandbox-compatible, E2B-drop-in) | Every Docker-based sandbox: 60 ms cold start, <5 MB RAM/instance, kernel-level isolation | Tencent Cloud — [`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox) | v1.9 |
| 6 | **Verifiable RAG Corpus + PoisonedRAG defense** | Every RAG-shipping harness — the 97 %-with-5-docs attack works against all of them today | Zou et al. (USENIX Sec'25) — [2402.07867](https://arxiv.org/abs/2402.07867) | v1.9 |
| 7 | **Self-Wiring Knowledge Graph** for procedural memory | Flat-text memory in Claude Code, OpenClaw, Hermes; +5 % precision / +11 % recall / +28 % graph search reported by GBrain v0.12 | Garry Tan / GBrain v0.12 (April 2026) | v1.9 |
| 8 | **Cross-Harness Trace Federation** | All single-harness memories — Lyra reads other harnesses' traces and answers across boundaries | Tramel — [`eric-tramel/moraine`](https://github.com/eric-tramel/moraine) | v2.5 |

Stretch (no fixed slot, post-v2.5): **Persistent Autonomous Worker Mode** (Phantom-inspired) — `lyra serve --watch` daemon that lives on a VM, opens PRs against failing CI, posts to Slack.

---

## 0. Manifesto — "Code is Free; judgment is the bottleneck"

Ryan Leopo (OpenAI, 2026) calls 2026 the **Code is Free** era: with frontier models writing 70 %+ of net-new code at top tech companies (Google's CEO confirmed the 25 % → 75 % shift in ~18 months — see also [Yahoo Finance](https://finance.yahoo.com/news/google-ceo-says-more-25-181500580.html), [Business Insider](https://www.businessinsider.com/google-ai-generated-code-pichai-2024-10)), the cost of *creating* a line of code has collapsed. The new scarce resources are:

1. **Human time** — engineers should spend it on planning and judgment, not boilerplate.
2. **Attention** — the system must surface the right context at the right moment.
3. **Context window** — the codebase has to be organisable in tokens the agent can actually consume.

Lyra's existing thesis (TDD-as-runtime-invariant, harness-as-product) fits this frame exactly. The eight ideas below extend it along three concrete axes:

| Axis | What v1.5–v2 already does | What this doc adds |
|---|---|---|
| **Compute** | DAG-Teams (different tasks in parallel) | **Tournament-Distilled TTS** (different *attempts* on the same task), **MicroVM** so we can spawn 1000s |
| **Memory** | Three-tier (working / SOUL / RAG) + Skill-Creator v2 + NGC-style compaction | **ReasoningBank failure-distillation**, **Skill-RAG router**, **self-wiring graph** |
| **Trust** | Two-phase verifier + cross-channel evidence + sigstore-signed skills (v2) | **TDD-reward inference signal**, **PoisonedRAG defense**, **cross-harness federation** |

We are not chasing more raw model power. We are buying leverage on the three things that are still expensive: *better attempts, better memories, better proofs*.

---

## 1. Landscape — April 2026

### 1.1 Head-to-head feature matrix

Extends [`feature-parity.md`](feature-parity.md) with an **ARIA** column and the eight novel features (★).

Legend: ✓ shipped, ◐ partial / behind a flag, ✗ not present.

| # | feature | CC | OC | HA | ARIA | Lyra v1.7 | Lyra v1.8★ | Lyra v1.9★ | Lyra v2.5★ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Recursive Tournament Voting on parallel coding attempts | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✓ | ✓ |
| 2 | Failure-distilled reasoning memory (MaTTS) | ✗ | ✗ | ◐ (success-only) | ✗ | ◐ (extractor) | **✓** | ✓ | ✓ |
| 3 | Hidden-state prober + 4-skill router | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✓ | ✓ |
| 4 | TDD-reward inference signal | ✗ | ✗ | ✗ | ✗ | ◐ (TDD gate, not reward) | **✓** | ✓ | ✓ |
| 5 | MicroVM (KVM/firecracker-class) sandbox | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** | ✓ |
| 6 | Sigstore-signed RAG corpus + k-of-n quorum | ✗ | ✗ | ✗ | ✗ | ◐ (skills only, v2) | ✗ | **✓** | ✓ |
| 7 | Self-wiring knowledge graph for procedural memory | ✗ | ◐ (Devin-Wiki) | ✗ | ✗ | ✗ | ✗ | **✓** | ✓ |
| 8 | Cross-harness trace federation (read CC/OC traces) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| — | Default kernel-isolated sandbox | ◐ (rootless container) | ◐ | ✗ | ✗ | ◐ (worktree + fs sandbox) | ◐ | ✓ | ✓ |
| — | Persistent autonomous worker daemon | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ◐ (stretch) |

**Reading the matrix.** Eight cells in the ★ columns are novel **net-new** capabilities not shipped by any of the four reference harnesses today. The four "—" rows are existing parity items where v1.9 / v2.5 raise our bar from "partial" to "default-on" (these are documented in [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md), repeated here for context only).

### 1.2 New papers that change the game

| Paper | One-line | Why it's novel for harnesses |
|---|---|---|
| **Scaling Test-Time Compute for Agentic Coding** — Kim, Yang, Niu, Zhang, Zhu, Helenowski, Silva, Chen, Iyer, Zaheer, Fried, Hajishirzi, Arora, Synnaeve, Salakhutdinov, Goyal (Meta SI Labs / UW / NYU / DeepMind / CMU / Princeton, 2026, [2604.16529](https://arxiv.org/abs/2604.16529)) | Compress each coding attempt into a *structured trajectory summary*. Use **Recursive Tournament Voting** to pick winners from parallel candidates, and **Parallel-Distill-Refine** to seed the next iteration with distilled insight. | Replaces "best-of-N + majority vote" with a memory-aware tournament that actually *understands* what each attempt did. The first credible TTS recipe for long-horizon coding. |
| **ReasoningBank — Scaling Agent Self-Evolving with Reasoning Memory** + **Memory-aware Test-Time Scaling (MaTTS)** — Google Research, 2025, [2509.25140](https://arxiv.org/abs/2509.25140) | Distill *generalisable* reasoning strategies from the agent's own self-judged successful **and failed** experiences. Memory and TTS reinforce each other. | Hermes' skill loop only learns from wins; ReasoningBank explicitly captures lessons from failures. The MaTTS half closes the loop with TTS. |
| **Skill-RAG** — Univ. Michigan / UPenn, 2026, [2604.15771](https://arxiv.org/abs/2604.15771) | A **Hidden-State Prober** reads the LM's own residual stream to detect "I don't actually know this" before another retrieval round. A **Skill Router** then chooses one of four recovery actions: Query Rewriting, Question Decomposition, Evidence Focusing, Exit. +6.1 pp on MuSiQue, +13.6 pp on 2WikiMultiHopQA. | All retrieval routers today are blind to the LM's own confidence. Probing the residual stream to gate retrieval failure recovery is the first *introspective* router we've seen. |
| **KnowRL: Knowledgeable RL for Factuality** — Zhejiang Univ, 2025, [2506.19807](https://arxiv.org/abs/2506.19807) | Inject a **factuality reward** (knowledge-verification-based) into the RL loop so slow-thinking models learn to stay inside their knowledge boundaries while reasoning. | We can't fine-tune frontier models, but the *signal shape* — "give the reasoning step a numeric reward only when its citations verify" — is reusable as an inference-time selector. For coding, "knowledge" = the test suite. |
| **Neural Garbage Collection** — Li, Hamid, Fox, Goodman (Stanford, 2026, [2604.18002](https://arxiv.org/abs/2604.18002)) — *already adopted in v1.7 Phase 23, repeated here for cross-reference.* | Joint policy over reasoning *and* eviction; outcome reward shapes both. 2–3× KV compression with strong accuracy. | Already on the v1.7 roadmap; we mention it because the failure-distillation idea (#2) and the TDD-reward (#4) share its outcome-only training-signal philosophy. |
| **PoisonedRAG: Knowledge Corruption Attacks to RAG** — Zou et al., USENIX Security 2025, [2402.07867](https://arxiv.org/abs/2402.07867) | Five malicious documents in a 2.6 M-doc corpus achieve a **97 % attack success rate** against GPT-4 / PaLM 2. Every standard defense (paraphrasing, perplexity, dedup, top-k expansion) fails. | OWASP added LLM08:2025 *Vector and Embedding Weaknesses* as a top-10 category. No competitor ships a defense in their RAG layer today. This is a wide-open differentiator. |
| **SemaClaw — Harness Engineering for Personal AI Agents** — Midea AIRC, 2026, [2604.11548](https://arxiv.org/abs/2604.11548) | Validates the *harness-engineering* thesis Lyra was built on. Their DAG-Teams and PermissionBridge mirror Lyra's, which is excellent third-party validation. | Doesn't introduce a new feature for us, but the paper's framing of "as model capability converges, the harness layer is the primary site of architectural differentiation" is exactly the message the v1.8 / v1.9 / v2.5 milestones below are built on. |

### 1.3 New OSS infrastructure that changes the game

| Project | What it gives us | License / state |
|---|---|---|
| [`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox) | RustVMM + KVM microVM, sub-60 ms cold start, <5 MB RAM/instance, eBPF-based egress (CubeVS), **drop-in E2B SDK**. Battle-tested at Tencent (100 K+ instances). | Apache-2.0, v0.1.0 April 2026 |
| [`ghostwright/phantom`](https://github.com/ghostwright/phantom) | Persistent AI co-worker on a dedicated VM. 17+ MCP tools. Self-evolution loop: "Day 30 is nothing like Day 1". | Apache-2.0, ~1.3 k stars |
| [`eric-tramel/moraine`](https://github.com/eric-tramel/moraine) | "Unified realtime agent trace database & search MCP." Reads any HIR-compatible trace and exposes search/recall as MCP tools across harness boundaries. | OSS, 31 stars (early but the *interface* is the right idea) |
| **GBrain v0.12** (Garry Tan, April 2026) | Self-wiring knowledge graph: stated +5 % precision, +11 % recall, +28 % graph search, −53 % noise on knowledge workflows. | Closed-source for now; we adopt the *pattern* not the code |

---

## 2. Where Lyra already wins (don't break these)

These are the moats v1.5–v1.7 already build. Every new feature in §3 must compose with them, not bypass them.

1. **TDD as runtime invariant** — green tests are not advisory, they're the gate. The two-phase verifier with cross-channel evidence is unique among the reference harnesses.
2. **DAG-Teams + worktree subagents** — independent task parallelism with hermetic worktrees and a permission bridge. SemaClaw's recent paper validates this exact pattern.
3. **Three-tier memory + SOUL** — durable persona pinned to PRs, working memory compacted by NGC-style cadence (v1.7).
4. **Skill-Creator v2** (v1.7) — the 4-agent loop (Executor / Grader / Comparator / Analyzer), with trigger-eval corpus and description optimizer.
5. **HIR (Harness Interaction Records)** — structured event log that any external agent can read; this is what makes federation (#8) feasible.
6. **TDD-style RED-tests-first development** — *every* feature in this doc is gated on a failing test before any implementation lands.

If any feature in §3 fights with one of these, the feature gets redesigned, not the moat.

---

## 3. Eight novel selling points

For each feature: *inspiration → selling point → why it beats the four references → contracts (modules + APIs) → RED tests → trade-offs and risks → milestone slot.*

> **v1.8 close-out status (2026-04-24).** All four Wave-1 features in §§3.1–3.4 are now **GREEN end-to-end**: §3.1 Tournament TTS shipped Phase 1 (full bracket + diversity primitives); §3.2 ReasoningBank shipped Phase 2 (in-memory `record / recall / matts_prefix`, MMR-backed `diversity_weighted=True`); §3.3 Skill-RAG shipped Phase 3 (router dispatch + EXIT-as-`None`-answer + `max_rounds` cap); §3.4 TDD-Reward shipped Phase 1 (`compute_tdd_reward` weighted-average). The Phase-2 SQLite/FTS5 swap-in for ReasoningBank is the only remaining v1.8 implementation work; everything else is now in maintenance + telemetry mode.

### 3.1 Tournament-Distilled Test-Time Scaling

**Inspiration.** *Scaling Test-Time Compute for Agentic Coding* — Kim et al., Meta SI Labs 2026, [2604.16529](https://arxiv.org/abs/2604.16529). Each attempt is summarised into `{idea, what_worked, what_failed, why}`; weak attempts are eliminated via **Recursive Tournament Voting**; future attempts are seeded with distilled insight via **Parallel-Distill-Refine**.

**Selling point.** *"Lyra is the first OSS coding harness that turns parallel attempts into a knowledge-distilled tournament — the agent doesn't just try N times, it learns from the previous N attempts within the same task."*

**Why it beats the references.**
- **Claude Code:** sequential single-attempt loop with no inter-attempt distillation.
- **OpenClaw:** parallel agent slots exist but vote naively; no compressed trajectory summaries.
- **Hermes Agent:** has a memory of *past sessions* but no within-session tournament.
- **ARIA:** no test-time scaling primitive at all.

**Contracts.** New module `lyra_core.tts.tournament`:

```python
class AttemptSummary(TypedDict):
    attempt_id: str
    idea: str            # 1-3 sentences: what the agent tried
    what_worked: list[str]
    what_failed: list[str]
    why: str             # postmortem reasoning, ≤ 200 tokens
    test_evidence: VerifierReport     # link to TDD verifier
    cost_tokens: int

class Tournament:
    def round(self, attempts: list[AttemptSummary]) -> list[AttemptSummary]: ...
    def winner(self, attempts: list[AttemptSummary]) -> AttemptSummary: ...

class ParallelDistillRefine:
    def seed_next(self, prior: list[AttemptSummary], task: Task) -> Prompt: ...
```

CLI: `lyra run --tts tournament --candidates 8 --rounds 3`.

**RED tests** (must exist *before* implementation).
- `test_tournament_eliminates_weakest_attempt` — given 4 attempts with synthetic verifier scores `[0.1, 0.4, 0.7, 0.9]` and equal token cost, after one tournament round only the top-2 survive.
- `test_summary_compresses_trajectory` — a 50-event HIR trajectory compresses to a `≤ 600` token `AttemptSummary` and the summary is sufficient to seed a refine attempt that scores ≥ 80 % of the original.
- `test_distill_then_refine_beats_naive_n_plus_1` — on a 10-task corpus, `--tts tournament --candidates 4 --rounds 2` beats `--tts naive --candidates 8` (same total compute) by ≥ 5 pp pass-rate. (Smoke test, model-key-gated; budget cap enforced.)
- `test_no_tournament_default` — without `--tts`, the run is byte-for-byte identical to v1.7. *Adopting this feature is opt-in.*

**Trade-offs.**
- Token-expensive: 4 candidates × 3 rounds is ~12× single-attempt cost. Mitigation: surface in `lyra doctor` budget estimate; default OFF.
- Distillation quality depends on the LM's own self-judgment, which can be over-confident on its own failures. Mitigation: use the TDD verifier as the *ground-truth* `test_evidence` field, never the LM's self-rating.

**Slot.** v1.8 — "Tournament" milestone, headline feature.

---

### 3.2 ReasoningBank with Failure-Distillation + MaTTS

**Inspiration.** *ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory* — Google Research 2025, [2509.25140](https://arxiv.org/abs/2509.25140). Two halves:
1. Distill **generalisable** reasoning strategies from both successful and **failed** trajectories (Hermes only learns from wins).
2. Memory-aware test-time scaling (**MaTTS**) — more compute per task → richer experiences → higher-quality distilled memory → better next attempt. Memory and TTS reinforce each other.

**Selling point.** *"Lyra extracts strategies from your wins **and** your losses — every regression becomes a teachable moment, and that memory powers a virtuous cycle with the tournament TTS in §3.1."*

**Why it beats the references.**
- **Hermes Agent:** post-session skill extraction is success-only — failed sessions evaporate.
- **Claude Code:** no persistent reasoning memory across sessions; every session starts cold.
- **OpenClaw:** skills are user-authored; no automatic extraction.
- **ARIA:** no equivalent.

**Contracts.** Extend `lyra_skills.skill_extractor` (v1.7) with two new analyzers:

```python
class SuccessAnalyzer(SkillAnalyzer):
    """Existing v1.7 path — distil strategies from PASS trajectories."""

class FailureAnalyzer(SkillAnalyzer):
    """NEW. Distil 'do not do this' patterns from FAIL trajectories.
    Output: an anti-skill (negative example) attached to the relevant skill."""

class MaTTS:
    """Allocate extra TTS budget when the task class has a thin memory.
    Closes the loop with §3.1 by feeding the new AttemptSummaries back
    through both analyzers."""
```

Memory schema additions:
- `skills/<slug>/anti-examples/*.md` — failure cases linked to a skill, surfaced to the LM via the same hint mechanism.
- `skills/<slug>/maTTS-budget.json` — per-skill recommended `--candidates` / `--rounds` derived from observed memory thinness.

CLI: `lyra retro --analyze failures` (new), and `lyra run --maTTS adaptive` (auto-tunes TTS budget per task class).

**RED tests.**
- `test_failure_analyzer_emits_anti_skill_on_red_test` — a failed attempt where the agent edited the wrong file produces an anti-skill containing `wrong-file-pattern` as the cited mistake.
- `test_anti_skill_surfaces_on_similar_task` — re-running a similar task pulls the anti-skill into context and the agent does not repeat the mistake.
- `test_maTTS_increases_budget_for_thin_skill` — a task class with `< 3` distilled experiences gets `--candidates 6` automatically; a class with `> 20` experiences uses `--candidates 2` (efficient).
- `test_failure_analyzer_respects_pii_masking` — anti-examples are scrubbed by the v1.5 PII masker before being written to disk.

**Trade-offs.**
- Storing failure patterns increases the surface area for skill drift (the agent might over-index on a fluke failure). Mitigation: anti-skills require a `quorum >= 2` of independent failure trajectories before being promoted from `proposed` to `active`.
- Privacy: failed trajectories often contain user secrets (typo'd passwords in CLI invocations). PII masking is mandatory before storage.

**Slot.** v1.8 — landing alongside #3.1; the two features compose into the loop the ReasoningBank paper actually demonstrates.

---

### 3.3 Skill-RAG: Hidden-State Prober + 4-skill Recovery Router

**Inspiration.** *Skill-RAG* — Univ. Michigan / UPenn 2026, [2604.15771](https://arxiv.org/abs/2604.15771). Two pieces:
1. **Hidden-State Prober** — a small classifier head over the LM's residual stream that detects "I don't actually know how to answer this" *before* another retrieval round.
2. **Skill Router** — when the prober fires, choose one of four recovery skills: **Query Rewriting**, **Question Decomposition**, **Evidence Focusing**, **Exit**.

**Selling point.** *"Lyra's router doesn't blindly retry on a miss. It probes the LM's own confidence, names the failure mode, and applies the right repair skill — saving tokens and ending fruitless loops cleanly."*

**Why it beats the references.**
- All four (CC, OC, HA, ARIA) use static retrieval with embedding similarity + top-k. None of them detect retrieval failure; they retry blindly until the budget runs out.
- v1.7 Phase 20 (already on the existing roadmap) gives Lyra hybrid BM25 + dense + description match with `NO_MATCH` / `AMBIGUOUS` verdicts. **Skill-RAG is the natural next step**: instead of just *flagging* `NO_MATCH`, route to a *repair skill*.

**Contracts.** New module `lyra_skills.router.skill_rag`:

```python
class HiddenStateProber:
    """For local models: hook the residual stream and run a small classifier.
    For closed models (Anthropic, OpenAI): use a calibrated proxy
    (token-level log-prob entropy + self-consistency vote) as the signal."""
    def confidence(self, prompt: str, response: str) -> float: ...

class RecoverySkill(Enum):
    QUERY_REWRITE = "rewrite"      # simplify or rephrase
    QUESTION_DECOMPOSE = "decompose"  # split into sub-queries
    EVIDENCE_FOCUS = "focus"       # narrow to a smaller corpus slice
    EXIT = "exit"                  # admit defeat, free the budget

class SkillRagRouter:
    def route(self, conf: float, query: Query, ctx: RetrievalCtx) -> RecoverySkill: ...
```

The Exit verdict is critical for `lyra doctor` to surface unanswerable tasks as a *finished* outcome, not a budget overrun.

**RED tests.**
- `test_prober_proxy_calibrates_on_known_unanswerables` — given 50 questions where the gold answer is "unknown", the proxy confidence is `< 0.4` for ≥ 40 of them.
- `test_router_picks_decompose_on_multi_hop` — a multi-hop question with low prober confidence routes to `QUESTION_DECOMPOSE` (not `QUERY_REWRITE`).
- `test_router_exits_within_budget_on_unanswerable` — an unanswerable task closes within 30 % of the budget (no infinite retry).
- `test_skill_rag_zero_regression_on_easy` — on the existing 100-task golden corpus, where the v1.7 router already returns `OK`, Skill-RAG never overrides — no regression on the easy path.

**Trade-offs.**
- We can't access hidden states for closed models. Mitigation: a calibrated proxy (log-prob entropy + cross-sample voting) is well-attested for confidence estimation; we ship that as the default and the true probe as a `--local-llm` opt-in.
- Risk of over-decomposition: easy questions get split into too many sub-queries. Mitigation: the router has a recursion depth cap (`max_depth=2`) configurable in `policy.yaml`.

**Slot.** v1.8 — extends the v1.7 Phase 20 router rather than replacing it. Phase 20 gives us `NO_MATCH`; Skill-RAG turns `NO_MATCH` into one of four named recoveries.

---

### 3.4 TDD-Reward Inference Signal (KnowRL for coding)

**Inspiration.** *KnowRL* — Zhejiang Univ 2025, [2506.19807](https://arxiv.org/abs/2506.19807). Inject a **factuality reward** based on knowledge verification into the RL loop so the model learns to stay inside its knowledge boundaries while reasoning. The result: less hallucination, same reasoning ability.

**Why it works for Lyra without RL training.** We can't fine-tune Anthropic / OpenAI models. But the *signal shape* is reusable as an **inference-time selector**: at every reasoning step where the agent cites a code fact, run a cheap test/coverage probe and use the probe's pass/fail as a numeric reward. Use the reward to:
1. **Re-rank candidate next-actions** in the tournament TTS (#3.1) — actions whose citations verify get a multiplicative boost.
2. **Gate skill admission** (#3.2) — a strategy is only distilled into ReasoningBank if its citations verified above a threshold.
3. **Annotate the HIR** with a per-step `factuality` field — surfaced in `lyra retro` and the canvas UI.

**For coding, "knowledge" = the test suite + the codebase itself.** A reasoning step that cites function `foo` in `bar.py` either resolves to a real symbol (verifiable via Grep / LSP) or it's a hallucination.

**Selling point.** *"In Lyra, every reasoning step that names code is checked. Hallucinated symbols, stale imports, fictional test names — all caught at the step boundary, not after the patch is applied."*

**Why it beats the references.**
- All four reference harnesses have TDD as a *soft prompt* ("write tests first") or, at best, a post-hoc gate (run the suite at the end). None turn TDD into a *per-step* numeric reward.
- The MCP-tools layer in CC/OC could in principle do this, but no shipped MCP server we've seen reads the LSP / coverage state at sub-action granularity.

**Contracts.** New module `lyra_core.inference.tdd_reward`:

```python
class TddReward(TypedDict):
    step_id: str
    citations: list[CodeCitation]    # symbols, files, test names the step claims
    verified: list[bool]
    factuality: float                # ratio verified / cited; null if no citations
    evidence: list[VerifierEvidence] # links to LSP / Grep / coverage probes

def score_step(step: AgentStep, ctx: VerifierCtx) -> TddReward: ...
```

Plug-in points:
- `Tournament.round()` — multiplies attempt scores by `mean(factuality)` over all steps.
- `SkillExtractor` — a strategy with `mean(factuality) < 0.6` is rejected.
- `HIR` — every step gets a `tdd_reward` field.

CLI: `lyra run --tdd-reward strict|relaxed|off` (default `relaxed`).

**RED tests.**
- `test_factuality_zero_for_hallucinated_symbol` — a reasoning step that cites `nonexistent_function` produces `factuality == 0.0`.
- `test_factuality_one_for_real_symbol` — a step citing a Grep-verifiable symbol produces `factuality == 1.0`.
- `test_strict_mode_aborts_on_first_hallucination` — `--tdd-reward strict` halts the run as soon as a step has `factuality < 1.0` and reports the offending citation.
- `test_relaxed_mode_only_logs` — `--tdd-reward relaxed` only annotates the HIR, never aborts.
- `test_tournament_uses_factuality_in_ranking` — given two attempts with equal verifier-pass-rate but `factuality {0.4, 0.95}`, the tournament picks the second.

**Trade-offs.**
- The verifier probe (LSP + Grep + coverage) costs ~50–200 ms per step. For a 100-step session that's ~10 s of overhead. Mitigation: probes run async on the worktree subagent, results joined at step-boundary.
- False negatives if the codebase has dynamic dispatch (e.g., reflection, runtime `getattr`). Mitigation: `relaxed` mode is the default; `strict` is opt-in for repos with known static structure.

**Slot.** v1.8 — landing alongside #3.1 because the tournament needs a high-fidelity scoring signal beyond "did the test suite pass at the end".

---

### 3.5 MicroVM Execution Backend (CubeSandbox-compatible, E2B drop-in)

**Inspiration.** [`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox), Apache-2.0. RustVMM + KVM. Sub-60 ms cold start, <5 MB RAM/instance, eBPF-based egress (CubeVS), drop-in E2B SDK compatibility. Battle-tested at Tencent (100 K+ instances).

**Selling point.** *"Lyra is the first OSS coding harness whose default sandbox is **kernel-isolated** with sub-100 ms cold starts. Spin up 1000 parallel agents per box. Container-escape attacks become impossible by construction."*

**Why it beats the references.**
- **Claude Code:** rootless container.
- **OpenClaw:** container-based.
- **Hermes Agent:** no sandbox by default.
- **ARIA:** no sandbox.

All four share the host kernel. None can credibly run untrusted AI-generated code without a layered host firewall the user has to configure. Lyra's microVM backend removes that burden.

**Contracts.** Lyra already has a sandbox abstraction (`lyra_core.sandbox`). Add a backend:

```python
class SandboxBackend(Protocol):
    def spawn(self, image: str, mounts: list[Mount]) -> SandboxHandle: ...
    def exec(self, handle: SandboxHandle, cmd: list[str]) -> ExecResult: ...
    def snapshot(self, handle: SandboxHandle) -> SnapshotId: ...
    def restore(self, snap: SnapshotId) -> SandboxHandle: ...
    def stop(self, handle: SandboxHandle) -> None: ...

class CubeSandboxBackend(SandboxBackend):
    """Connects to a CubeSandbox cluster via E2B-compatible HTTP API.
    Single env var swap from any E2B-using project."""

class FsSandboxBackend(SandboxBackend):
    """Existing v1 path — kept as default on dev machines without KVM."""
```

CLI: `lyra config sandbox.backend = cubesandbox|local-fs|local-firecracker`. `lyra doctor` detects KVM availability and recommends.

The `snapshot` / `restore` pair enables **fork-from-state** for the tournament TTS in §3.1: each attempt forks from the same project state at sub-second latency.

**RED tests.**
- `test_microvm_spawn_under_200ms_p95` — over 50 spawns, p95 < 200 ms. (We allow more headroom than CubeSandbox's 90 ms because we go through the SDK adapter.)
- `test_microvm_isolation_blocks_host_socket` — a sandbox cannot connect to a port on the host outside an allowlist.
- `test_e2b_compatibility_mode` — pointing the existing `lyra-evals` at a CubeSandbox URL via env var alone produces the same output as the local backend.
- `test_snapshot_restore_round_trip_preserves_fs` — write a file in sandbox A, snapshot, restore in sandbox B, file is readable.
- `test_local_fs_remains_default_no_kvm` — on a machine without `/dev/kvm`, the backend silently falls back to `local-fs` and `lyra doctor` warns once.

**Trade-offs.**
- macOS has no native KVM. Mitigation: managed CubeSandbox cluster (HTTP API works from anywhere) is the recommended path on Mac; `local-fs` remains the dev default.
- Operational overhead — running a CubeSandbox cluster adds an Ops layer. Mitigation: ship a one-liner `docker compose up cubesandbox` as the canonical local-cluster recipe in `docs/microvm-setup.md`.
- Compatibility surface: E2B SDK changes break us. Mitigation: pin the E2B contract to a tested version in `pyproject.toml` and CI an E2B compatibility job nightly.

**Slot.** v1.9 — "Substrate" milestone; this is the foundation that makes #3.1 cheap enough to run by default.

---

### 3.6 Verifiable RAG Corpus + PoisonedRAG Defense

**Inspiration.** *PoisonedRAG* — Zou et al., USENIX Security 2025, [2402.07867](https://arxiv.org/abs/2402.07867). Five malicious docs in a 2.6 M-doc corpus → 97 % attack success rate against GPT-4 / PaLM 2. Every standard defense (paraphrasing, perplexity, dedup, top-k expansion) **fails**. OWASP added LLM08:2025 *Vector and Embedding Weaknesses* as a top-10 category in 2025.

**The threat model.** Attacker can't see the model, retriever, or DB internals. They just write a document the retriever might one day index. That's enough.

**Selling point.** *"Lyra is the first OSS coding harness where every document the agent reads carries a sigstore-signed provenance record, and no answer is grounded in fewer than `k` independent sources. PoisonedRAG against Lyra is a multi-attacker problem, not a single-attacker problem."*

**Why it beats the references.**
- **Claude Code, OpenClaw, Hermes, ARIA:** all ship plain RAG. None require provenance, none enforce k-of-n consensus, none surface the trust path to the user.
- v1.5 introduces sigstore signing for *skills*; v1.9 extends the same trust kernel to the *RAG corpus*.

**Contracts.** Three new sub-modules under `lyra_core.rag.trust`:

```python
class CorpusEntry(TypedDict):
    id: str
    text: str
    embedding: bytes
    source_url: str
    fetched_at: datetime
    sigstore_bundle: str    # in-toto attestation, signed at ingest time
    publisher: str           # signer identity (DID / OIDC)

class QuorumRetriever:
    def retrieve(self, query: str, k: int = 5, quorum: int = 2) -> list[CorpusEntry]:
        """Returns top-k AND requires that >= `quorum` of the top-k come from
        DISTINCT publishers before the result is passed to the LM. Otherwise
        returns NO_QUORUM and the SkillRagRouter (#3.3) is invoked."""

class PoisonProbe:
    """Heuristic defense layer that runs at ingest time:
    * cluster-novel anomaly score (PoisonedRAG documents are near-duplicates of crafted prompts)
    * conflict detector vs. existing top-k for the inferred query class
    Tagged outputs are quarantined for human review, not silently dropped."""
```

Operational pieces:
- Sigstore signing at ingest, verified at retrieval (already used for skills in v1.5; we reuse the same trust kernel).
- `policy.yaml` adds `rag.quorum: 2`, `rag.publishers.allowlist: [...]`, `rag.signature.required: true`.
- `lyra rag status` lists corpus health, signing coverage, and quarantined entries.

**RED tests.**
- `test_unsigned_entry_refused_at_ingest` — an unsigned doc is rejected with a clear error.
- `test_quorum_one_publisher_is_no_quorum` — five top-k results from a single publisher → `NO_QUORUM`.
- `test_quorum_two_distinct_publishers_passes` — five top-k with two distinct publishers → ok.
- `test_poisoned_rag_synthetic_attack_blocked` — the canonical PoisonedRAG attack pattern (5 cluster-near-duplicate docs targeting one question) is blocked at ingest by the `PoisonProbe`. (Test fixture: a small synthetic corpus + the published attack template.)
- `test_no_quorum_routes_to_skill_rag_recovery` — `NO_QUORUM` invokes `SkillRagRouter` (#3.3) and the agent either rewrites the query or exits cleanly — never silently uses unverified content.

**Trade-offs.**
- Signing every doc has an Ops cost. Mitigation: bulk signing per publisher; OSS publishers get a free sigstore identity via OIDC.
- Quorum hurts recall on niche topics where only one trusted publisher has coverage. Mitigation: per-domain quorum override in `policy.yaml`, audit trail for waivers.
- Doesn't defend against a *trusted* publisher going bad. Mitigation: revocation list in the trust kernel; published as a transparency log entry.

**Slot.** v1.9 — pairs with #3.5; both are "Substrate" milestone items.

---

### 3.7 Self-Wiring Knowledge Graph for Procedural Memory

**Inspiration.** **GBrain v0.12** (Garry Tan, April 2026) — self-wiring knowledge graph. Stated wins: +5 % precision, +11 % recall, +28 % graph search performance, −53 % noise. Combined with the *Externalization in LLM Agents* survey (Zhou et al., [2604.08224](https://arxiv.org/abs/2604.08224)) which frames memory as one of three externalisation axes.

**Selling point.** *"Lyra's procedural memory is a graph that wires itself from the HIR. Asking 'how did we last fix this kind of bug' returns the *path* through prior sessions — files, symbols, tests, decisions — not just a flat-text snippet."*

**Why it beats the references.**
- **Claude Code:** flat-text Memory Bank.
- **OpenClaw:** Devin-Wiki style auto-indexed docs (closer, but still document-scoped, not graph-scoped).
- **Hermes Agent:** flat-text skills.
- **ARIA:** sqlite-vec embeddings, flat.

The graph captures relations the flat formats miss: *which test surfaced which bug, which skill applied to which file, which decision invalidated which earlier decision.*

**Contracts.** New module `lyra_core.memory.graph` complementing the v1 SQLite FTS5 + Chroma:

```python
class MemoryGraph:
    def upsert_node(self, node: MemoryNode) -> NodeId: ...
    def upsert_edge(self, src: NodeId, dst: NodeId, kind: EdgeKind, weight: float) -> None: ...
    def query(self, seed: NodeId, depth: int = 2, edge_filter: list[EdgeKind] | None = None) -> Subgraph: ...

class HirGraphIndexer:
    """Streaming indexer: every HIR event becomes one or more graph upserts.
    File node, symbol node, test node, decision node, skill node, session node.
    Edges: REFERENCES, FIXES, REGRESSED_BY, APPLIED_TO, INVALIDATES."""
```

The graph backs a new tool `recall_path(from, to)` exposed to the agent (and via MCP), so the LM can ask "what's the chain that connects test X to commit Y?".

**RED tests.**
- `test_indexer_creates_file_symbol_test_nodes` — given a 20-event HIR fixture, the indexer creates the expected node and edge counts.
- `test_recall_path_returns_path_not_snippet` — `recall_path(test_xyz, commit_abc)` returns a 3-step path with intermediate nodes, not a flat document.
- `test_invalidates_edge_buries_outdated_decisions` — adding an `INVALIDATES` edge from decision D2 to D1 makes `query(seed=D1)` rank D2 above D1 by default.
- `test_graph_falls_back_to_flat_search_on_miss` — if the graph has no path, search falls back to FTS5 / Chroma transparently.

**Trade-offs.**
- Storage overhead: ~10–20 % over the existing FTS5 index for typical repos. Acceptable.
- The graph can drift if the HIR is re-edited; we guard with append-only HIR events and a periodic graph compaction.
- Graph queries can blow up combinatorially. Mitigation: hard depth cap (default 3), query budget enforced at the resolver.

**Slot.** v1.9 — "Substrate" milestone, paired with #3.5 / #3.6 because all three are about *what the agent stands on*.

---

### 3.8 Cross-Harness Trace Federation

**Inspiration.** [`eric-tramel/moraine`](https://github.com/eric-tramel/moraine) — "unified realtime agent trace database & search MCP." Reads any HIR-compatible trace and exposes search/recall as MCP tools across harness boundaries.

**Selling point.** *"Switched harnesses last week? Ran something in Claude Code yesterday? Lyra reads it. `lyra recall --harness all` answers across every HIR-compatible session you've ever had — Claude Code, OpenClaw, Hermes, Lyra — with a single query."*

**Why it beats the references.**
- All four reference harnesses confine memory to their own session log.
- The HIR contract (already shipped in Lyra v1) is harness-agnostic; we just need adapters and a federated query layer.
- Positions Lyra as the "harness of harnesses" — even if a user prefers another tool for daily work, Lyra becomes their cross-harness *memory* and *audit* layer.

**Contracts.** New module `lyra_core.federation`:

```python
class HarnessAdapter(Protocol):
    name: str   # "claude-code", "openclaw", "hermes", "moraine"
    def list_sessions(self) -> list[SessionRef]: ...
    def load_hir(self, ref: SessionRef) -> Iterable[HirEvent]: ...

class FederatedRecall:
    def search(self, query: str, harnesses: list[str] | None = None) -> list[RecallHit]: ...
    def cross_check(self, claim: str) -> CrossCheckReport:
        """For a claim like 'we changed the auth header format last Tuesday',
        scan every harness's traces and return a confidence score plus
        per-harness evidence."""
```

Adapters ship as plugins:
- `lyra-fed-claude-code` — reads `~/.claude/sessions/*.jsonl` (well-documented format).
- `lyra-fed-openclaw` — reads `~/.openclaw/sessions/*`.
- `lyra-fed-moraine` — connects to Moraine's MCP server (zero adapter work since Moraine already aggregates).

CLI: `lyra recall "auth header bug" --harness all` and `lyra cross-check "we deleted the legacy webhook last week"`.

**RED tests.**
- `test_adapter_reads_claude_code_format` — given a fixture `claude.jsonl`, the adapter yields HIR events with the expected fields.
- `test_federated_search_dedup_across_harnesses` — the same logical event appearing in two harnesses returns a single `RecallHit` with both sources cited.
- `test_cross_check_disagreement_surfaces_evidence` — when CC says "we did X" and OpenClaw says "we did NOT do X", `cross_check` returns `INCONSISTENT` with both evidence pointers.
- `test_no_harness_data_clean_empty_response` — querying with no adapter installed returns an empty list, not a crash.
- `test_adapter_respects_user_consent` — federation is OFF by default; turning it on requires `policy.yaml` opt-in and `lyra doctor` shows which harness paths are read.

**Trade-offs.**
- Privacy: federation crosses session boundaries originally chosen by the user. Mitigation: opt-in only, doctor-visible, audit-logged in the Lyra HIR.
- Format drift: CC / OC change their session format without notice. Mitigation: adapters version against a tested format; a failing adapter falls back to "no data" rather than crashing.
- Could be perceived as "spying" on other tools. Mitigation: clear UX about what's read, where it's stored, and a single `lyra fed disable` to turn everything off.

**Slot.** v2.5 — "Federation" milestone. Comes after v2's Meta-Harness because federation querying becomes much more powerful when the meta-harness can include cross-harness data in its training signal.

---

### Stretch — Persistent Autonomous Worker Mode (Phantom-inspired)

**Inspiration.** [`ghostwright/phantom`](https://github.com/ghostwright/phantom) — persistent AI co-worker on a dedicated VM with self-evolution loop and 17+ MCP tools. "Day 30 is nothing like Day 1."

**Selling point** (if we ship it). *"`lyra serve --watch` runs Lyra as a 24/7 daemon. It watches CI for failures, opens draft PRs with proposed fixes, posts daily status to Slack, and learns from each interaction. The first OSS coding harness with a Phantom-class always-on mode."*

**Why this is a stretch.** Persistent operation is a different operational shape (process supervision, secret rotation, on-call) that we should only take on after v2's self-evolving harness is proven. We list it here so the architecture in v1.9 / v2 doesn't accidentally close the door on it.

**Architecture seed.** Reuse the v1.9 microVM backend as the long-running agent's substrate. The HIR + federation layer becomes the audit log. Self-evolution is the v2 Meta-Harness running on a `cron`.

**RED tests** to write *before* this phase even gets scheduled.
- `test_serve_watch_recovers_after_restart` — a daemon restart preserves the per-task state via the microVM snapshot in §3.5.
- `test_serve_watch_respects_dangerous_ops_policy` — daemon never runs anything in `SOUL.md`'s dangerous-ops list without human approval.
- `test_serve_watch_emits_audit_log_per_action` — every autonomous action lands in HIR with a daemon identity tag.

---

## 4. Phased rollout

### v1.8 "Tournament" (≈ 6 weeks, target `v0.4.0`)

| Phase | Item | Owner contracts | RED tests file |
|---|---|---|---|
| 24 | Tournament TTS skeleton | `lyra_core.tts.tournament` | `tests/tts/test_tournament.py` |
| 25 | ReasoningBank failure analyzer + MaTTS | `lyra_skills.reasoningbank` | `tests/skills/test_failure_analyzer.py` |
| 26 | Skill-RAG router (extends v1.7 Phase 20) | `lyra_skills.router.skill_rag` | `tests/skills/test_skill_rag_router.py` |
| 27 | TDD-reward inference signal | `lyra_core.inference.tdd_reward` | `tests/inference/test_tdd_reward.py` |
| 28 | Wire-through: tournament uses factuality + ReasoningBank seeds + Skill-RAG recoveries | integration | `tests/integration/test_v1_8_loop.py` |

**Meta-DoD for v1.8.**
- `lyra run --tts tournament --candidates 4 --rounds 2` end-to-end succeeds on the existing 100-task golden corpus, beating naive `--candidates 8` by ≥ 5 pp at equal token cost.
- ReasoningBank stores both success and failure analyses with sigstore-signed entries. `lyra retro --analyze failures` runs cleanly.
- Skill-RAG router routes `NO_MATCH` to one of four named recoveries; no regressions on the v1.7 routing tests.
- Every step in the HIR carries a `tdd_reward.factuality` field. `lyra retro` surfaces hallucination rate per session.
- Test count target: ≥ 700 passing (from current 609).

### v1.9 "Substrate" (≈ 6 weeks, target `v0.5.0`)

| Phase | Item | Contracts | RED tests file |
|---|---|---|---|
| 29 | MicroVM SandboxBackend abstraction + CubeSandbox adapter | `lyra_core.sandbox.microvm` | `tests/sandbox/test_microvm_backend.py` |
| 30 | Verifiable RAG: sigstore-signed entries + quorum retriever | `lyra_core.rag.trust` | `tests/rag/test_quorum_and_signing.py` |
| 31 | PoisonProbe ingest layer + synthetic-attack regression | `lyra_core.rag.trust.probe` | `tests/rag/test_poisoned_rag_attack.py` |
| 32 | Self-wiring knowledge graph + HIR indexer + `recall_path` tool | `lyra_core.memory.graph` | `tests/memory/test_graph_indexer.py` |
| 33 | Wire-through: tournament forks state via microVM snapshots; agent uses `recall_path` natively | integration | `tests/integration/test_v1_9_substrate.py` |

**Meta-DoD for v1.9.**
- `lyra config sandbox.backend = cubesandbox` works against either a local Docker-Compose CubeSandbox cluster *or* a managed instance. `lyra doctor` validates KVM, CubeSandbox API, and certificate chain.
- Every doc in the RAG corpus has a sigstore signature and named publisher. `lyra rag status` shows 100 % signing coverage on the OSS corpora we ship.
- The synthetic PoisonedRAG attack (≤ 5 cluster-near-duplicate docs) is **blocked at ingest** with explanation surfaced in `lyra doctor`.
- The HIR indexer keeps up with a 50 events/s stream without falling behind. `recall_path` returns within 200 ms p95 for depth-3 queries on a 100 K-event graph.
- Test count target: ≥ 800 passing.

### v2.0 "Self-Evolving Harness" (already on the roadmap, integration touchpoints noted here)

The existing v2 Meta-Harness outer loop (see [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md)) gains two new training signals from this doc:
- ReasoningBank failure-distillations (#3.2) become candidate harness mutations: "previous harness consistently failed on multi-hop tasks; propose a routing change".
- The TDD-reward (#3.4) and the factuality field in HIR are dense-enough signals to use as Meta-Harness rewards instead of binary task pass/fail.

No phase-renumbering needed; we just ensure the v2 phase reading the training corpus knows about the new fields.

### v2.5 "Federation" (≈ 6 weeks, target `v0.7.0`)

| Phase | Item | Contracts | RED tests file |
|---|---|---|---|
| 40 | HarnessAdapter abstraction + Claude Code adapter | `lyra_core.federation.adapters.claude_code` | `tests/federation/test_cc_adapter.py` |
| 41 | OpenClaw + Hermes adapters | `lyra_core.federation.adapters.{openclaw,hermes}` | `tests/federation/test_oc_ha_adapters.py` |
| 42 | Moraine MCP adapter (zero-adapter path) | `lyra_core.federation.adapters.moraine` | `tests/federation/test_moraine_mcp.py` |
| 43 | FederatedRecall + cross-check + opt-in policy | `lyra_core.federation.recall` | `tests/federation/test_recall_and_cross_check.py` |
| 44 | `lyra recall --harness all` UX + audit log | CLI + UX | `tests/cli/test_federated_recall_cli.py` |

**Meta-DoD for v2.5.** `lyra recall "<query>" --harness all` returns deduplicated hits across at least three reference harnesses (CC + OC + HA). `lyra cross-check` surfaces inconsistencies with per-harness evidence. Federation is OFF by default; turning it on writes a one-line audit entry to HIR.

---

## 5. Acceptance metrics (top-line, public)

We measure each milestone against the same five public knobs:

1. **SWE-bench Pro pass-rate** (50-task subset, vendor-key-gated) — v1.8 target +5 pp over v1.7 with tournament TTS at equal token cost.
2. **LoCoEval requirement coverage** — v1.8 target ≥ 50 % on a 20-sample subset (v1.7 target was 40 %).
3. **Hallucinated-citation rate** — v1.8 introduces this metric via the TDD-reward; v1.8 target < 3 % hallucinated citations per session.
4. **PoisonedRAG attack success rate** — v1.9 target < 5 % (vs. published 97 % against undefended frontier models).
5. **MicroVM cold-start p95** — v1.9 target < 200 ms with our SDK adapter (CubeSandbox base is 90 ms).

Each metric is reported in [`benchmarks.md`](benchmarks.md) and gated in CI via the existing `lyra evals` snapshot mechanism (VeRO-style, see v1.5 Phase 12).

---

## 6. Open research questions (worth a paper)

These are explicit "we don't yet know" items — surfacing them so the team doesn't accidentally over-claim and so external collaborators see where to plug in.

1. **What's the right granularity for trajectory summaries?** Kim et al. compress per-attempt; ReasoningBank goes per-strategy. We probably want both (attempt-level inside the tournament, strategy-level for cross-session memory) but the right schema is not obvious. RED test idea: ablate at token budgets `{200, 600, 2000}` and measure tournament win-rate.
2. **Can the calibrated proxy (token-log-prob entropy + self-consistency vote) match a true hidden-state probe?** Skill-RAG's gain depends on the prober quality; a closed-model proxy may underperform. Concrete experiment: run on the same set of MuSiQue / 2WikiMultiHopQA fixtures with both a local LLaMA probe and the proxy on Claude Sonnet, compare F1 on "knows / doesn't know".
3. **Does failure-distillation interact poorly with non-stationary repos?** Anti-skills extracted from a failed `requirements.txt` upgrade may misfire after the upgrade succeeds. Time-decay on anti-skills is one obvious fix; better is to tag anti-skills with the codebase commit SHA and only surface them when the relevant subtree hasn't changed.
4. **Is sigstore signing economically viable for community RAG corpora?** OIDC-based signing is technically free but Ops cost is real. We may need a "publisher group key" model where a community vouches for a corpus collectively.
5. **MaTTS budget allocation policy.** The paper allocates by hand. We propose a thinness-driven heuristic in §3.2; a learned policy is probably better long-term and is a natural Meta-Harness training task in v2.

---

## 7. Things we explicitly are *not* doing

To keep the milestones tight:

- **No fine-tuning frontier models.** Every "reward" in this doc is an *inference-time selector* signal, not a gradient. We only use RL framing as motivation.
- **No new UI primitive in v1.8 / v1.9.** The interactive REPL is fixed at v1.7 quality. Federation in v2.5 introduces one new CLI surface (`lyra recall --harness all`) and that's it.
- **No replacement of the SQLite session store.** The graph in §3.7 augments, never replaces, FTS5 / Chroma. Adapter pattern, additive only.
- **No drop of the worktree backend.** The microVM in §3.5 is a *new option*, not a replacement; `local-fs` stays the default for dev-loop ergonomics.
- **No Phantom-style daemon in v1.8 / v1.9 / v2.** Persistence is a v2.5+ stretch; we just keep the door open.

---

## 8. Wave 2 — Performance Edges (Sept 2025 – April 2026)

Wave 1 (§3) was about *new capabilities*. Wave 2 is about **raw performance** — features that make Lyra demonstrably faster, cheaper, more accurate, and more robust on the public scoreboards. Each one is grounded in a paper or production OSS with measured wins (cited inline).

The April-2026 reality check: GPT-5.5 hit **82.7 % on Terminal-Bench 2.0** and **84.9 % on GDPval** ([MarkTechPost coverage](https://www.marktechpost.com/2026/04/23/openai-releases-gpt-5-5-a-fully-retrained-agentic-model-that-scores-82-7-on-terminal-bench-2-0-and-84-9-on-gdpval/)). Z.AI's **GLM-5.1** (754 B open-weight) reached SOTA on SWE-bench Pro with **8-hour autonomous execution** ([MarkTechPost coverage](https://www.marktechpost.com/2026/04/08/z-ai-introduces-glm-5-1-an-open-weight-754b-agentic-model-that-achieves-sota-on-swe-bench-pro-and-sustains-8-hour-autonomous-execution/)). Open-source coding-agent stars (Cline 58 k, Aider 39 k, OpenHands 65 k) confirm self-host is mainstream. The bar for "best performance" moved.

Wave-2 ideas, ranked by leverage × novelty × feasibility:

| #  | Feature | Beats … on … | Inspiration | Slot |
|----|---|---|---|---|
| 9  | **Intra-attempt MCTS** for coding (cross-attempt tournament + intra-attempt search) | Wave 1 #1 has *cross-attempt* search; this adds *intra-attempt* MCTS for +23 % rel. SWE-bench gain | Antoniades et al., ICLR 2025 — [arXiv:2410.20285](https://arxiv.org/abs/2410.20285), [`aorwall/moatless-tree-search`](https://github.com/aorwall/moatless-tree-search) | v2.0 |
| 10 | **Confidence-Cascade Routing** (FrugalGPT / RouteLLM / Confidence-Driven) | Up to 98 % cost reduction at GPT-4 quality on the original benchmark, 2× cost reduction with no quality loss on RouteLLM | Chen et al. — [arXiv:2305.05176](https://arxiv.org/abs/2305.05176); Ong et al. — [arXiv:2406.18665](https://arxiv.org/abs/2406.18665); Confidence-Driven Router — [arXiv:2502.11021](https://arxiv.org/abs/2502.11021) | v1.8 |
| 11 | **Software Org Mode** — first-class Roles + SOPs (PM / Architect / Engineer / Reviewer / QA / Doc-Writer) on top of DAG-Teams | More structured than CC's free-form subagents and OC's plain plugins | Hong et al. — [arXiv:2308.00352](https://arxiv.org/abs/2308.00352); Qian et al. — [arXiv:2307.07924](https://arxiv.org/abs/2307.07924) | v1.9 |
| 12 | **Voyager-style Skill Curriculum** (auto-pick the next skill to acquire) | Lyra v1.7 *creates* skills on demand; this *plans* skill acquisition. 3.3× more items / 15.3× faster tech-tree on the original Minecraft benchmark | Wang et al., TMLR 2024 — [arXiv:2305.16291](https://arxiv.org/abs/2305.16291) | v1.9 |
| 13 | **Process Reward Model (PRM) adapter** | Replaces heuristic verifier scores with real PRMs (Qwen2.5-Math-PRM-7B/72B, Critic-RM, RLHFlow) — pairs with Wave 1 #4 TDD-Reward | Lightman et al. *Let's Verify Step by Step* (PRM800K, [`openai/prm800k`](https://github.com/openai/prm800k)); Math-Shepherd; Qwen2.5-Math-PRM lessons — [arXiv:2501.07301](https://arxiv.org/abs/2501.07301) | v1.8 |
| 14 | **Computer-Use Browser Sandbox** (first-class web agent inside the v1.9 microVM) | None of CC / OC / HA / ARIA ship a sandboxed browser agent today. OSWorld: humans 72.4 %, best LLM 12.2 % — wide-open headroom | Anthropic Computer Use; OpenAI Operator; Xie et al. (NeurIPS 2024) — [arXiv:2404.07972](https://arxiv.org/abs/2404.07972) | v2.0 |
| 15 | **EAGLE-3 Speculative Decoding profile** (when running on local OSS models) | Up to **6.5× speedup** on chat / reasoning models, 1.4× over EAGLE-2; 1.38× SGLang throughput at batch 64 | Li et al. — [arXiv:2503.01840](https://arxiv.org/abs/2503.01840) | v1.9 |

Plus a **benchmark-adapter pack** (§9) and two **post-v2.5 stretches** (§10).

---

### 9.1 Intra-attempt MCTS (SWE-Search)

**Inspiration.** *SWE-Search: Enhancing Software Agents with Monte Carlo Tree Search and Iterative Refinement* — Antoniades et al., ICLR 2025, [arXiv:2410.20285](https://arxiv.org/abs/2410.20285). Code: [`aorwall/moatless-tree-search`](https://github.com/aorwall/moatless-tree-search), Apache-2.0.

**Selling point.** *"Wave 1 #1 explores across attempts; Wave 2 #9 explores **inside** each attempt. The agent walks a tree of next-actions, scored by an LLM-as-value-function with multi-agent debate, and recovers from local minima without restarting from scratch."*

**Why it beats the references.** Reported **+23 % relative SWE-bench improvement across five models** without retraining. None of CC / OC / HA / ARIA ship MCTS as an option today; SWE-Search is the only open implementation that ports cleanly to the Lyra agent loop.

**How it composes with Wave 1.** Tournament TTS (#1) is best-of-N across attempts; MCTS is best-path inside one attempt. Together they form a two-level search: at the leaf, MCTS finds the strongest single trajectory; at the root, the tournament picks across leaves. Both feed the ReasoningBank (#2) — successful nodes become memory, dead branches become anti-skills.

**Contracts.** New module `lyra_core.tts.mcts`:

```python
class TreeSearchPolicy(Protocol):
    def expand(self, node: Node) -> list[Action]: ...
    def value(self, node: Node) -> float                # LLM-as-value head
    def select(self, root: Node) -> Path                # UCB1 / UCT
    def discriminate(self, paths: list[Path]) -> Path   # multi-agent debate

class SweSearch:
    def search(self, task: Task, budget: SearchBudget) -> Trajectory: ...
```

CLI: `lyra run --tts mcts --max-nodes 64 --budget tokens=200000`. Composes with `--tts tournament` as `--tts tournament+mcts`.

**RED tests.**
- `test_mcts_recovers_from_local_min` — a synthetic task with a known shortcut behind a 3-step detour: MCTS finds it within 32 nodes; greedy ablation does not.
- `test_value_head_calibration` — on a 50-trajectory fixture with known final-score outcomes, the value head's pearson correlation ≥ 0.5.
- `test_mcts_plus_tournament_strictly_dominates` — same total token budget: `tournament+mcts` ≥ `tournament` ≥ `mcts` ≥ `naive` on a 20-task pilot subset.
- `test_budget_cap_honoured` — `--budget tokens=200000` halts cleanly when the cap is hit, surfaces the best path so far.

**Trade-offs.** Token-expensive; tree explosion risk. Mitigations: hard depth + branching caps; LLM-as-value-function uses the cheapest profile from the cascade router (§8.2); failed branches still feed ReasoningBank (§3.2) so cost is not wasted.

**Slot.** v2.0 — paired with Meta-Harness so the outer loop can also tune MCTS hyper-params per repo.

---

### 9.2 Confidence-Cascade Routing (FrugalGPT × RouteLLM × Confidence-Driven)

**Inspiration.** Three converging lines of work:
- *FrugalGPT* — Chen et al., 2023, [arXiv:2305.05176](https://arxiv.org/abs/2305.05176). Cascade of cheap → expensive models with a learned scorer. Up to **98 % cost reduction at GPT-4 quality**, or **+4 % accuracy at GPT-4 cost**.
- *RouteLLM* — Ong et al., 2024, [arXiv:2406.18665](https://arxiv.org/abs/2406.18665). Preference-data-trained router. **2× cost reduction with no quality loss** on the published benchmarks.
- *Confidence-Driven LLM Router* — 2025, [arXiv:2502.11021](https://arxiv.org/abs/2502.11021). Uncertainty + LLM-as-judge confidence beats preference data on MT-Bench / GSM8K / MMLU.

**Selling point.** *"Lyra spends GPT-5-class money only when GPT-5-class judgment is required. Every step gets the cheapest model whose hidden-state confidence (Wave 1 #3) clears a per-task threshold; expensive models only escalate when the cheap one says 'I'm not sure'."*

**Why it beats the references.** All four reference harnesses pick one model per session and pay full freight for every token. None of them have a per-step cascade with confidence-gated escalation.

**How it composes.** The Skill-RAG hidden-state prober (#3) already produces a confidence score; the cascade reuses it as the routing signal. No separate classifier needed for closed models; for local models, EAGLE-3 (#15) makes the cheap tier even cheaper.

**Contracts.** New module `lyra_core.routing.cascade`:

```python
class CascadeStep(TypedDict):
    profile: str        # "haiku-4.5", "sonnet-4.6", "opus-4.6", "local-qwen2.5-coder-32b"
    cost_per_mtok: float
    confidence_threshold: float

class CascadeRouter:
    def __init__(self, ladder: list[CascadeStep]): ...
    def route(self, prompt: Prompt, ctx: RoutingCtx) -> ModelResponse:
        """Try cheapest first; escalate up the ladder until prober.confidence >= threshold."""
```

`policy.yaml` gets a new top-level `routing.cascade.ladder` with sensible defaults per provider.

**RED tests.**
- `test_easy_question_stays_on_cheap_tier` — a fixture of "easy" questions (canonical math facts, well-known APIs) never escalates past `haiku-4.5`.
- `test_hard_question_escalates_to_top` — a fixture of multi-hop reasoning questions reaches `opus-4.6` ≥ 80 % of the time.
- `test_cascade_at_equal_quality_is_strictly_cheaper` — on a 100-task subset, `cascade` matches `single opus-4.6` quality at ≤ 50 % cost. (Smoke test, key-gated.)
- `test_no_cascade_default_byte_for_byte` — without `routing.cascade`, the run is identical to v1.7. Cascade is opt-in.

**Trade-offs.** Latency: a worst-case cascade walks the ladder, which costs a round-trip per tier. Mitigations: parallel speculative call to the next tier when confidence is borderline; latency-budget cap in `policy.yaml`. Provider lock-in: the ladder hardcodes vendor names. Mitigation: vendor-agnostic abstraction with provider plug-ins.

**Slot.** v1.8 — pairs with Wave 1 #3 (Skill-RAG prober) and Wave 1 #4 (TDD-Reward) so we have all three confidence signals consolidated.

---

### 9.3 Software Org Mode — Roles + SOPs (MetaGPT × ChatDev)

**Inspiration.**
- *MetaGPT* — Hong et al., 2023-2024, [arXiv:2308.00352](https://arxiv.org/abs/2308.00352). Standardized Operating Procedures (SOPs) compiled into prompt sequences; assembly-line role assignment.
- *ChatDev* — Qian et al., 2023-2024, [arXiv:2307.07924](https://arxiv.org/abs/2307.07924). Communicative agents (CTO / Programmer / Tester) following a waterfall lifecycle, with a "communicative dehallucination" protocol.

**Selling point.** *"Lyra's DAG-Teams already runs different tasks in parallel. Org Mode adds first-class **roles** (PM, Architect, Engineer, Reviewer, QA, Doc-Writer) with explicit **SOPs** (intent → spec → code → review → test → docs). Multi-agent for software engineering, not multi-agent for its own sake."*

**Why it beats the references.** Claude Code's subagents are free-form; OpenClaw plugins are role-agnostic; Hermes Agent has skills, not roles. None bundle SOPs as a contract.

**How it composes.** Roles map onto DAG-Teams nodes; each role has a curated tool whitelist (Reviewer can read but not edit; Engineer can edit but not deploy; QA owns the test runner). The PermissionBridge (already in v0.1) enforces this at runtime, so role escalation is auditable.

**Contracts.** New module `lyra_core.org`:

```python
class Role(TypedDict):
    name: str                 # "engineer", "reviewer", ...
    persona: str              # SOUL.md fragment
    tools: list[str]          # whitelist
    inputs: list[ArtifactKind]
    outputs: list[ArtifactKind]
    sop: SopId                # references a procedure in `org/sops/*.yaml`

class Sop(TypedDict):
    id: SopId
    steps: list[SopStep]      # ordered or DAG; each step pins a Role
    handoff: HandoffPolicy    # blocking artifact contract between steps

class OrgRunner:
    def execute(self, intent: str, sop: SopId) -> Run: ...
```

CLI: `lyra org run "build CSV exporter" --sop waterfall-small`. Org definitions live in `.lyra/org/{roles,sops}/`.

**RED tests.**
- `test_role_tool_whitelist_blocks_unauthorized` — Reviewer attempting `Edit` is blocked at the PermissionBridge with a clean error.
- `test_sop_handoff_artifact_contract` — Engineer cannot start until Architect produces the spec artifact; the contract is enforced.
- `test_communicative_dehallucination_round_trip` — when Reviewer flags a fictional symbol, Engineer revises and the loop terminates without infinite ping-pong (ChatDev's failure mode).
- `test_org_mode_off_by_default` — without `--sop`, behaviour is identical to v1.7 DAG-Teams.

**Trade-offs.** SOPs add latency (more handoffs). Mitigation: a pareto profile (`--sop micro`) collapses adjacent roles when budget is tight. Risk of rigid waterfall; for that, the SOP DSL allows feedback edges (cyclic graphs with termination guards).

**Slot.** v1.9 — pairs with v1.9 #6 (RAG trust) so Reviewer can refuse to sign off when an answer cites unverified sources.

---

### 9.4 Voyager-style Skill Curriculum

**Inspiration.** *Voyager: An Open-Ended Embodied Agent with Large Language Models* — Wang et al., TMLR 2024, [arXiv:2305.16291](https://arxiv.org/abs/2305.16291), code: [`MineDojo/Voyager`](https://github.com/MineDojo/Voyager). Three pieces: automatic curriculum, ever-growing skill library, iterative prompting with execution feedback. **3.3× more unique items, 2.3× longer distances, 15.3× faster tech-tree milestones** vs prior SOTA on the Minecraft benchmark.

**Selling point.** *"Lyra's v1.7 Skill-Creator builds skills **on demand**. Voyager Mode plans skill acquisition: 'we have 12 skills for HTTP work, 0 for streaming JSON parsing — propose 3 candidate skills to learn before the next session.' Curriculum, not just creator."*

**Why it beats the references.** Skill-Creator v2 (Anthropic, already adopted in v1.7) is reactive — the user or the repetition-detector triggers it. Voyager is proactive: an inner loop maximises skill-coverage of an explicit "knowledge frontier" map.

**How it composes.** Coverage map = the existing skill graph (§3.7) + ReasoningBank failure-distillations (§3.2). The curriculum picks the next skill by maximising expected reduction in failure-pattern density.

**Contracts.** New module `lyra_skills.curriculum`:

```python
class FrontierMap:
    """Sparse coverage of {task_class -> available_skills} from HIR + ReasoningBank."""
    def gaps(self, k: int = 3) -> list[Gap]: ...

class CurriculumPlanner:
    def propose(self, frontier: FrontierMap) -> list[SkillCandidate]: ...
    def schedule(self, candidates: list[SkillCandidate]) -> Plan: ...
```

CLI: `lyra curriculum status` (prints the frontier map), `lyra curriculum plan` (proposes 3 skills), `lyra curriculum acquire <skill>` (drives Skill-Creator v2 to land it).

**RED tests.**
- `test_frontier_identifies_known_gap` — on a fixture HIR with 10 failed `parse-json` tasks and 0 skills tagged `parse-json`, `gaps()` returns `parse-json` first.
- `test_planner_proposes_distinct_skills` — three proposals never overlap on `(intent, when_to_use)` signature.
- `test_acquisition_loop_terminates` — `acquire` runs Skill-Creator v2 to a `benchmark.json` artifact and stops; no infinite loop.
- `test_curriculum_off_by_default` — without explicit invocation, no background acquisition runs.

**Trade-offs.** Acquisition burns tokens between user sessions. Mitigation: per-day budget cap; user-approval gate on each `acquire`. False frontiers — the planner may "see" gaps that are actually fine. Mitigation: any proposal with `< 3` distilled failure patterns is downranked.

**Slot.** v1.9 — pairs with §3.7 (knowledge graph) which gives the frontier map a real backing store.

---

### 9.5 Process Reward Model (PRM) Adapter

**Inspiration.**
- *Let's Verify Step by Step* / **PRM800K** — Lightman et al. (OpenAI), [`openai/prm800k`](https://github.com/openai/prm800k). 800 k step-level correctness labels.
- *Math-Shepherd* — automatic process supervision via continuation sampling.
- *The Lessons of Developing Process Reward Models in Mathematical Reasoning* — Qwen team, 2025, [arXiv:2501.07301](https://arxiv.org/abs/2501.07301), shipping **Qwen2.5-Math-PRM-7B / 72B** with **LLM-as-judge consensus filtering** (their headline lesson: MC estimation alone is inferior).

**Selling point.** *"Lyra's TDD-Reward (Wave 1 #4) gives every step a numeric grade based on test/coverage citations. The PRM Adapter plugs in a real PRM (Qwen2.5-Math-PRM, Critic-RM, custom) so the grade includes **reasoning quality**, not just citation correctness."*

**Why it beats the references.** None of the reference harnesses ship a pluggable PRM. Adopting the Qwen consensus-filtering recipe gives Lyra a step-grading head that is comparable to frontier-lab internal infra.

**How it composes.** A PRM is a step-graded score function; Lyra already has the step boundary (HIR event), the citation extractor (TDD-Reward), and the verifier (Phase 11 cross-channel). The adapter just plumbs the score into:
- `Tournament.round()` (§3.1) — multiply attempt scores by mean PRM grade.
- `MCTS.value()` (§8.1) — use PRM as the leaf-value estimator.
- `SkillExtractor` (§3.2) — admit only steps whose PRM grade ≥ threshold into ReasoningBank.

**Contracts.** New module `lyra_core.verifier.prm`:

```python
class ProcessRewardModel(Protocol):
    name: str
    def grade_step(self, prefix: list[Step], step: Step) -> StepReward: ...

class StepReward(TypedDict):
    score: float           # [0,1]
    confidence: float
    rationale: str | None  # if the PRM is generative

class PrmAdapter(ProcessRewardModel):
    """Wraps any HuggingFace-hosted PRM (Qwen2.5-Math-PRM, Critic-RM, …) or a
    private endpoint."""
```

`policy.yaml`: `verifier.prm.endpoint: "qwen2.5-math-prm-7b@hf"` (default unset — opt-in).

**RED tests.**
- `test_prm_higher_score_for_correct_step` — given a known-correct step and a known-incorrect step on the same prefix, PRM scores the former higher.
- `test_prm_pearson_with_outcome` — over a 100-trajectory fixture, mean step PRM correlates with final outcome at ρ ≥ 0.4 (matches published Qwen2.5-Math-PRM-7B baselines).
- `test_prm_default_off` — without the `verifier.prm.endpoint` config, no PRM call happens.
- `test_prm_failure_falls_back_to_tdd_reward` — if the PRM endpoint times out, the loop continues with TDD-Reward only and an HIR warning is emitted.

**Trade-offs.** Latency per step (~50–200 ms for 7 B PRM, more for 72 B). Mitigation: PRM runs async on a worktree subagent; results join at step boundary or are dropped after a budget cap. Provider lock-in to the Qwen ecosystem if we ship that as default. Mitigation: adapter is plug-in; we ship the adapter, the user picks the PRM.

**Slot.** v1.8 — pairs with Wave 1 #4 (TDD-Reward); together they form a complete step-grading layer for #1 / #9 / #11 to consume.

---

### 9.6 Computer-Use Browser Sandbox

**Inspiration.**
- **Anthropic Computer Use** ([docs](https://docs.anthropic.com/en/docs/agents-and-tools/computer-use)) — Claude takes screenshots and emits mouse/keyboard actions.
- **OpenAI Operator** — autonomous web agent (Pro tier).
- *OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments* — Xie et al., NeurIPS 2024, [arXiv:2404.07972](https://arxiv.org/abs/2404.07972). 369 real computer tasks; **humans 72.4 %, best LLM 12.2 %**. OSWorld-Verified (July 2025) reduced eval time to <1 hr on AWS.

**Selling point.** *"Real engineering tasks require the web — read this Notion page, file this Linear ticket, look up the Stripe API change. Lyra v2.0 ships a first-class browser agent inside the v1.9 microVM, with Anthropic Computer Use as the default provider and a Playwright fallback for OSS models."*

**Why it beats the references.** Claude Code, OpenClaw, Hermes Agent, and ARIA do not ship sandboxed browser agents. Anthropic / OpenAI ship the *capability* but not a sandbox-by-default contract. Lyra would ship both.

**How it composes.** Browser session runs inside a CubeSandbox microVM (§3.5) → kernel-isolated, sub-100 ms cold start, eBPF egress filtering. The PermissionBridge gates which domains the browser may visit. Each browser action is an HIR event, so the cross-harness federation (§3.8) can replay it.

**Contracts.** New module `lyra_core.tools.computer_use`:

```python
class BrowserAction(TypedDict):
    kind: Literal["click", "type", "scroll", "screenshot", "url"]
    target: str | tuple[int, int]   # CSS selector or (x, y)
    value: str | None

class BrowserSession:
    def open(self, url: str) -> SessionId: ...
    def step(self, action: BrowserAction) -> StepResult: ...
    def screenshot(self) -> bytes: ...
    def close(self) -> None: ...

class ComputerUseProvider(Protocol):
    name: str        # "anthropic", "playwright-fallback"
    def plan(self, goal: str, ctx: PageCtx) -> list[BrowserAction]: ...
```

CLI: `lyra browse "find the latest Stripe webhook signature spec"` — opens a sandboxed browser, runs the plan, returns a structured summary plus screenshots.

**RED tests.**
- `test_browser_runs_inside_microvm` — assert the browser process is in a CubeSandbox VM, not on the host.
- `test_egress_allowlist_blocks_unauthorized_domain` — a navigation to a non-allowlisted domain raises a clean PermissionBridge denial.
- `test_browser_actions_appear_in_hir` — every click / type / scroll lands as an HIR event with the screenshot hash.
- `test_playwright_fallback_when_no_anthropic_key` — without `ANTHROPIC_API_KEY`, the system falls back to Playwright + a local model and `lyra doctor` warns once.
- `test_osworld_smoke_subset` — 10-task OSWorld subset runs end-to-end; no requirement to beat a specific number, but no infinite loops.

**Trade-offs.** Browser cost is real (Computer Use is currently slower than text). Mitigation: the cascade router (§8.2) sends easy steps to the cheap text-only path; only "I need to interact with the page" steps invoke the browser. Privacy: screenshots can leak secrets. Mitigation: PII masker (v1.5) runs over screenshot OCR before storage.

**Slot.** v2.0 — pairs with v1.9 §3.5 (microVM). The web is the dominant non-CLI surface; this closes the gap.

---

### 9.7 EAGLE-3 Speculative Decoding profile

**Inspiration.** *EAGLE-3: Scaling up Inference Acceleration of LLMs via Training-Time Test* — Li et al., 2025, [arXiv:2503.01840](https://arxiv.org/abs/2503.01840). Drops the EAGLE feature-prediction constraint, switches to direct token prediction with multi-layer feature fusion. **Up to 6.5× speedup on chat / reasoning models, 1.4× over EAGLE-2, 1.38× SGLang throughput at batch 64.**

**Selling point.** *"On the local-OSS profile (Qwen 2.5 Coder 32 B, DeepSeek R1 distill 70 B, Llama 3.3 70 B), Lyra ships EAGLE-3 wired into the inference path. A 6× speedup means a 6× cheaper agent — the same skills, the same TDD gate, the same HIR, but the inner loop runs at draft speed."*

**Why it beats the references.** None of CC / OC / HA / ARIA wire speculative decoding into the agent loop. They use the provider's defaults. For users self-hosting on RTX 3090 / M3 Max (the same audience the 2026 OSS-coding agents survey calls "mainstream now"), this is the difference between "feels alive" and "feels slow".

**How it composes.** EAGLE-3 is purely an inference-time accelerator; it is invisible to the agent loop. The cascade router (§8.2) just gets a faster cheap-tier. Tournament TTS (§3.1) becomes affordable to default-on for the OSS profile. MCTS (§8.1) gets a tractable branch budget.

**Contracts.** New module `lyra_core.inference.eagle3`:

```python
class Eagle3Profile:
    """Wraps a SGLang/vLLM/llama.cpp endpoint with EAGLE-3 draft head loaded.
    Validated draft heads ship as HF models: yuhuili/EAGLE3-LLaMA3.3-Instruct-70B etc."""
    def chat(self, messages: list[Message], **kw) -> Response: ...
```

`policy.yaml` adds `inference.profile.local-eagle3: { backend: "sglang", draft: "yuhuili/EAGLE3-LLaMA3.3-Instruct-70B", target: "meta-llama/Llama-3.3-70B-Instruct" }`.

**RED tests.**
- `test_eagle3_speedup_over_baseline` — same prompt, same target model: EAGLE-3 wall-clock ≤ 70 % of vanilla decode (lenient — the paper claims much better, we just verify a positive delta).
- `test_eagle3_quality_parity` — over a 50-prompt fixture, EAGLE-3 outputs are byte-identical to vanilla decode (speculative decoding is exact, not lossy — this is a regression guard).
- `test_eagle3_only_for_compatible_models` — pointing the profile at a model with no EAGLE-3 draft head raises a clean error.
- `test_default_decode_unchanged` — without `inference.profile.local-eagle3`, behaviour is unchanged.

**Trade-offs.** Setup complexity: needs a draft head matched to the target. Mitigation: ship a curated mapping of target → draft head in `lyra doctor`, and the doctor downloads on first use. macOS without GPU has no path. Mitigation: profile is a no-op on Mac; cascade router (§8.2) handles fallback.

**Slot.** v1.9 — pairs with §3.5 (microVM substrate). Both are about *making the same agent cheaper to run*.

---

## 9. Benchmark expansion — measure on every public scoreboard

The existing v1.5 plan ships **SWE-bench Pro** and **LoCoEval** adapters. Wave 2 adds the four 2025-2026 benchmarks the field has converged on, so Lyra has a number on every public scoreboard:

| Benchmark | What it measures | Adapter | Slot |
|---|---|---|---|
| **GDPval** ([arXiv:2510.04374](https://arxiv.org/abs/2510.04374), [openai.com/research/gdpval](https://openai.com/research/gdpval)) | 1,320 economically valuable real-work tasks across 44 occupations; 220-task gold subset open. GPT-5.5 hit 84.9 %. | `lyra_evals/adapters/gdpval.py` | v1.5 carry-over |
| **SWE-Lancer** ([`openai/SWELancer-Benchmark`](https://github.com/openai/SWELancer-Benchmark)) | $1 M of real Upwork tasks. Diamond split is public ($500 K). Best frontier model earned $186 K. | `lyra_evals/adapters/swe_lancer.py` | v1.5 carry-over |
| **τ-Bench / τ³-Bench** (Sierra, [`sierra-research/tau2-bench`](https://github.com/sierra-research/tau2-bench)) | Multi-domain (airline / retail / telecom / banking) tool-use; pass-1 vs pass-8 reliability. | `lyra_evals/adapters/tau_bench.py` | **v1.8 (loader + writer ✅)** |
| **Terminal-Bench 2.0** ([t-bench.com](https://t-bench.com/), [`harbor-framework/terminal-bench-2`](https://github.com/harbor-framework/terminal-bench-2)) | 89 hard CLI tasks; frontier <65 %; 1 k+ stars; used by all frontier labs. | `lyra_evals/adapters/terminal_bench_v2.py` | **v1.8 (loader + writer ✅)** |

**Status (this PR).** Both adapters' JSONL loader + submission writer are now GREEN with strict-schema validation: required keys raise `ValueError` with the offending **line number**, optional keys default sensibly (`allow_partial_credit=False`, `allowed_network=False`). `--budget N` is honoured. The loaders mirror `lyra_evals.adapters.swe_bench_pro.load_swe_bench_pro` 1:1.

**RED tests.** One per adapter: smoke-load a single fixture task, run end-to-end on the local `--llm mock`, assert the adapter emits a verdict in the canonical format the upstream harness expects. Snapshot pinning via VeRO (v1.5 Phase 12) applies.

**Acceptance metric.** A single command — `lyra evals --corpus all` — produces one signed report covering Lyra-internal goldens + SWE-bench Pro + LoCoEval + GDPval gold + SWE-Lancer Diamond + τ-Bench + Terminal-Bench 2.0. Drift gate ≥ 5 % on any corpus turns the CI red.

---

## 10. Stretch — beyond v2.5

These are explicit "we don't intend to ship soon, but the architecture must not foreclose them" items.

### 11.1 8-hour Continuous Autonomous Run profile

**Inspiration.** Z.AI's **GLM-5.1** (754 B open-weight, April 2026) sustains 8-hour autonomous execution on SWE-bench Pro — a different shape from KLong's resume-across-models. This is one continuous run with internal milestones, snapshotted state, and a daemon supervisor.

**Why it's a stretch.** Different operational shape (process supervision, on-call, escalation policy). Pairs with the Phantom-style daemon mentioned in §3 stretch.

**Architecture seed.** Reuse v1.9 §3.5 microVM snapshots as the checkpoint substrate; reuse §3.8 federation as the audit log; reuse §9 GDPval / SWE-Lancer as the evaluation surface so we can publish a number.

### 11.2 DSPy-compiled skill bodies

**Inspiration.** *DSPy: Compiling Declarative Language Model Calls into State-of-the-Art Pipelines* — Khattab et al., ICLR 2024, [arXiv:2310.03714](https://arxiv.org/abs/2310.03714), [`stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy). Treats LLM pipelines as text-transformation graphs that a compiler optimises against a metric.

**Why it's a stretch.** v1.7 Phase 21 already optimises skill **descriptions** (trigger pass-rate). DSPy would optimise the skill **body** too. This is a powerful next move once the trigger-eval corpus is dense enough to serve as the held-out compile target. Best as a v2.5+ add-on.

**Architecture seed.** A skill becomes a `dspy.Module`; compilation runs against the `benchmark.json` already produced by Skill-Creator v2; the compiler output is a versioned skill body that supersedes the previous one (with rollback via the existing skill registry).

### 11.3 SWE-RL-style outcome-RL training corpus

**Inspiration.** *SWE-RL* — Facebook Research, NeurIPS 2025, [`facebookresearch/swe-rl`](https://github.com/facebookresearch/swe-rl). The first published RL framework using open-source software-evolution data with rule-based rewards (sequence-similarity reward functions: `calculate_search_replace_reward`, `calculate_reward_unidiff`).

**Why it's a stretch.** We do not train frontier models, but our HIR + TDD-Reward (§3.4) + PRM (§8.5) produce a perfect SWE-RL-format training corpus. The harness becomes a *data factory* even if the training is downstream. v2 already exports a training corpus; this stretch defines the SWE-RL-compatible schema explicitly.

---

## 10A. Wave-3 — Diversity-Collapse Hardening (cross-cutting)

> **Source paper:** Chen et al., *Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation*, **ACL 2026 Findings**, [arXiv:2604.18005](https://arxiv.org/abs/2604.18005). Mirrored at [`../papers/diversity-collapse-mas.pdf`](../papers/diversity-collapse-mas.pdf). **Code:** <https://github.com/Xtra-Computing/MAS_Diversity>.
> **Full mapping:** [`research/diversity-collapse-analysis.md`](research/diversity-collapse-analysis.md) — every Lyra subsystem graded by exposure (5 HIGH/MEDIUM, 3 LOW) with concrete countermeasures per Lyra version.

The paper finds that **multi-agent systems for open-ended ideation suffer structural diversity collapse** even when each agent is high-quality: alignment + hierarchy + dense topology synchronise the search trajectory and **lose >50 % of theoretical search efficiency** as group size scales (Vendi/N drops from 1.03 to 0.47 over N=3→7). Software engineering sits at the paper's "Edge of Chaos" — high entropy + strict logic — which is the *most vulnerable* regime.

This Wave is **cross-cutting**: it does not introduce a single new feature; it adds quantitative **diversity contracts** to every existing parallel/multi-agent surface. Five Lyra subsystems are exposed; three are resilient by design; **four RED tests** are already on file.

### 10A.1 Already shipped (v1.8 close-out)

- `lyra_core.diversity` module — four primitives (`effective_diversity`, `mean_pairwise_distance`, `mmr_select`, `ngt_attempt_independence_guard`).
- **13/13 GREEN** in [`packages/lyra-core/tests/test_diversity_preservation_phase0.py`](../packages/lyra-core/tests/test_diversity_preservation_phase0.py): 9 primitive contracts + 3 Phase-6 wiring contracts + **the v1.9-seed Software-Org-Mode default contract is now GREEN too**.
- `TtsResult.pool_diversity: float` field, `TournamentTts.run` NGT guard call, `ReasoningBank.recall(diversity_weighted=...)` (now **behavioural**, MMR-backed), `lyra_core.org.DEFAULT_PERSONA_MIX/DEFAULT_TOPOLOGY` constants — all wired and GREEN.

### 10A.2 v1.8 Phase 6 — wire primitives into Tournament TTS + ReasoningBank

| Contract                                                      | Status                      | Notes                                                                              |
| ------------------------------------------------------------- | :-------------------------: | ---------------------------------------------------------------------------------- |
| `test_tournament_result_exposes_pool_diversity_score`         | ✅ GREEN                    | `TtsResult` carries `pool_diversity: float = 0.0`; populated by `effective_diversity` over the attempt-artefact pool |
| `test_tournament_calls_ngt_guard_during_run`                  | ✅ GREEN                    | `TournamentTts.run` reads `Attempt.metadata["context_fingerprint"]` (falls back to `Attempt.id`) and calls `lyra_core.diversity.ngt_attempt_independence_guard(...)` via the *module attribute* (so test spies and telemetry hooks can patch in one place) before any discriminator pairing |
| `test_reasoning_bank_recall_supports_diversity_weighted_mode` | ✅ GREEN (**behavioural**)  | `ReasoningBank.recall(..., diversity_weighted: bool = False)` is now **wired through `mmr_select`** over the in-memory store; relevance-and-distinctness in one shot. Phase-2 swap to SQLite/FTS5 keeps the same surface. |
| MaTTS prefix diversification per attempt                      | ✅ GREEN (Phase 2)          | `ReasoningBank.matts_prefix` rotates the recall window by `attempt_index` so attempt-N reads a different lesson slice than attempt-(N−1) |
| Subagent dispatcher fingerprinting (Phase 6 P2)               | ⏳ v1.8 Phase 6 P2          | Same `ngt_attempt_independence_guard` plumbing; the dispatcher already exists, only the guard wiring is left |

**Acceptance.** **Four of four** Phase-6 contracts now flip GREEN; pool-diversity floor of `0.20` (mean pairwise distance) is computed and surfaced today, enforced as a soft warning in Phase 6 P2, and promoted to a hard drift gate in v2.0. Heterogeneous Confidence-Cascade is documented as the canonical anti-collapse pattern.

### 10A.3 v1.9 Phase 1 seed — Software Org Mode default safety

| Contract                                                                      | Status                                                                                                  |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `test_software_org_mode_default_persona_topology_avoids_collapse_modes`       | ✅ GREEN — `lyra_core.org` ships `DEFAULT_PERSONA_MIX = "vertical"`, `DEFAULT_TOPOLOGY = "subgroups"`; module-level asserts refuse `leader_led` / `interdisciplinary` / `standard` |

**Acceptance.** The Pareto-safe defaults are committed *now*, ahead of the runtime `OrgPersona` / `Topology` / `OrgRunner` machinery (which lands with v1.9 Phase 1 proper). When Software Org Mode (§8.3) becomes runnable, its default config sits on the paper's **Pareto frontier** (Vertical persona × Subgroups topology, Vendi 6.08 + Overall Quality 8.32) — *not* the two collapse traps (Vendi 4.65–6.93). Configurable to other modes for ablation, but **never** the default; the v1.9 NGT silent-ideation phase is the next contract to file.

### 10A.4 v2.0 Wave-4 — Diversity-aware drift gates (promotion)

- Promote `pool_diversity` from telemetry to a first-class `lyra_evals` drift gate. Mean pairwise distance below `min_diversity_floor` fails the run automatically — same UX as the existing degraded-eval gate.
- Replace `_normalised_token_distance` fallback with embedding-backed cosine distance.
- Add a real Vendi Score implementation under `lyra_evals.metrics.diversity` for offline parity with the source paper's measurement protocol.

### 10A.5 Why this matters for Lyra's pitch

Most coding harnesses don't even talk about diversity collapse — and the paper proves they probably *should*. Lyra is the first harness with:

1. an **explicit, RED-tested** anti-collapse contract on every parallel surface,
2. a **public mapping** of which subsystems are exposed and why ([`research/diversity-collapse-analysis.md`](research/diversity-collapse-analysis.md)),
3. a **drift gate** that fails low-diversity runs before they ship.

This becomes a Lyra **reliability selling point** independent of raw benchmark numbers. (Benchmarks measure the median; this guards the tail.)

---

## 11. Updated rollup — all 15 features at a glance

| Wave | # | Feature | Slot | Source |
|---|---|---|---|---|
| 1 | 1 | Tournament-Distilled TTS | v1.8 | Meta SI Labs [2604.16529](https://arxiv.org/abs/2604.16529) |
| 1 | 2 | ReasoningBank failure-distillation + MaTTS | v1.8 | Google Research [2509.25140](https://arxiv.org/abs/2509.25140) |
| 1 | 3 | Skill-RAG hidden-state prober + 4-skill router | v1.8 | Univ. Michigan / UPenn [2604.15771](https://arxiv.org/abs/2604.15771) |
| 1 | 4 | TDD-Reward inference signal | v1.8 | Zhejiang Univ [2506.19807](https://arxiv.org/abs/2506.19807) |
| 1 | 5 | MicroVM execution backend | v1.9 | [`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox) |
| 1 | 6 | Verifiable RAG corpus + PoisonedRAG defense | v1.9 | USENIX Sec'25 [2402.07867](https://arxiv.org/abs/2402.07867) |
| 1 | 7 | Self-wiring knowledge graph | v1.9 | GBrain v0.12 |
| 1 | 8 | Cross-harness trace federation | v2.5 | [`eric-tramel/moraine`](https://github.com/eric-tramel/moraine) |
| 2 | 9 | Intra-attempt MCTS (SWE-Search) | v2.0 | ICLR 2025 [2410.20285](https://arxiv.org/abs/2410.20285) |
| 2 | 10 | Confidence-Cascade Routing | v1.8 | [2305.05176](https://arxiv.org/abs/2305.05176) + [2406.18665](https://arxiv.org/abs/2406.18665) + [2502.11021](https://arxiv.org/abs/2502.11021) |
| 2 | 11 | Software Org Mode (Roles + SOPs) | v1.9 | [2308.00352](https://arxiv.org/abs/2308.00352) + [2307.07924](https://arxiv.org/abs/2307.07924) |
| 2 | 12 | Voyager skill curriculum | v1.9 | TMLR 2024 [2305.16291](https://arxiv.org/abs/2305.16291) |
| 2 | 13 | Process Reward Model adapter | v1.8 | PRM800K + Qwen [2501.07301](https://arxiv.org/abs/2501.07301) |
| 2 | 14 | Computer-Use browser sandbox | v2.0 | OSWorld [2404.07972](https://arxiv.org/abs/2404.07972) + Anthropic CU |
| 2 | 15 | EAGLE-3 speculative decoding profile | v1.9 | [2503.01840](https://arxiv.org/abs/2503.01840) |
| Bench | — | GDPval / SWE-Lancer / τ-Bench / Terminal-Bench 2.0 adapters | v1.5 + v1.8 | see §9 |
| Stretch | — | 8-hour autonomous run, DSPy bodies, SWE-RL corpus | post-v2.5 | see §10 |
| **Wave-3** | — | **Diversity-Collapse Hardening** (`pool_diversity`, NGT guard, MMR recall, Vertical+Subgroups defaults, drift gate) | **v1.8 Phase 6 → v2.0** | **§10A**; ACL 2026 [2604.18005](https://arxiv.org/abs/2604.18005) |

---

## 12. References

Papers (mirrored under [`../papers/`](../papers/)):

- Kim, Yang, Niu, Zhang, Zhu, Helenowski, Silva, Chen, Iyer, Zaheer, Fried, Hajishirzi, Arora, Synnaeve, Salakhutdinov, Goyal — *Scaling Test-Time Compute for Agentic Coding*, 2026, [arXiv:2604.16529](https://arxiv.org/abs/2604.16529).
- Li, Hamid, Fox, Goodman — *Neural Garbage Collection: Learning to Forget while Learning to Reason*, Stanford, 2026, [arXiv:2604.18002](https://arxiv.org/abs/2604.18002).
- *Skill-RAG*, Univ. Michigan / UPenn, 2026, [arXiv:2604.15771](https://arxiv.org/abs/2604.15771).
- *KnowRL: Exploring Knowledgeable Reinforcement Learning for Factuality*, Zhejiang Univ, 2025, [arXiv:2506.19807](https://arxiv.org/abs/2506.19807).
- *ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory*, Google Research, 2025, [arXiv:2509.25140](https://arxiv.org/abs/2509.25140).
- Zou et al. — *PoisonedRAG: Knowledge Corruption Attacks to RAG of LLMs*, USENIX Security 2025, [arXiv:2402.07867](https://arxiv.org/abs/2402.07867).
- Midea AIRC — *SemaClaw: A Step Towards General-Purpose Personal AI Agents through Harness Engineering*, 2026, [arXiv:2604.11548](https://arxiv.org/abs/2604.11548).

Wave 2 papers (mirrored under [`../papers/`](../papers/)):

- Antoniades et al. — *SWE-Search: Enhancing Software Agents with Monte Carlo Tree Search and Iterative Refinement*, ICLR 2025, [arXiv:2410.20285](https://arxiv.org/abs/2410.20285).
- Novikov et al. (Google DeepMind) — *AlphaEvolve: A coding agent for scientific and algorithmic discovery*, June 2025, [arXiv:2506.13131](https://arxiv.org/abs/2506.13131).
- Chen et al. — *FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance*, 2023, [arXiv:2305.05176](https://arxiv.org/abs/2305.05176).
- Ong et al. — *RouteLLM: Learning to Route LLMs with Preference Data*, 2024, [arXiv:2406.18665](https://arxiv.org/abs/2406.18665).
- *Confidence-Driven LLM Router*, 2025, [arXiv:2502.11021](https://arxiv.org/abs/2502.11021).
- Wang et al. — *Voyager: An Open-Ended Embodied Agent with Large Language Models*, TMLR 2024, [arXiv:2305.16291](https://arxiv.org/abs/2305.16291).
- Shinn et al. — *Reflexion: Language Agents with Verbal Reinforcement Learning*, NeurIPS 2023, [arXiv:2303.11366](https://arxiv.org/abs/2303.11366).
- Hong et al. — *MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework*, 2023-2024, [arXiv:2308.00352](https://arxiv.org/abs/2308.00352).
- Qian et al. — *ChatDev: Communicative Agents for Software Development*, 2023-2024, [arXiv:2307.07924](https://arxiv.org/abs/2307.07924).
- Khattab et al. — *DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines*, ICLR 2024, [arXiv:2310.03714](https://arxiv.org/abs/2310.03714).
- Li et al. — *EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test*, 2025, [arXiv:2503.01840](https://arxiv.org/abs/2503.01840).
- Xie et al. — *OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments*, NeurIPS 2024, [arXiv:2404.07972](https://arxiv.org/abs/2404.07972).
- OpenAI — *GDPval: Evaluating AI Model Performance on Real-World Economically Valuable Tasks*, 2025, [arXiv:2510.04374](https://arxiv.org/abs/2510.04374).
- Zhang et al. (Qwen team) — *The Lessons of Developing Process Reward Models in Mathematical Reasoning*, 2025, [arXiv:2501.07301](https://arxiv.org/abs/2501.07301).

Wave-3 papers (mirrored under [`../papers/`](../papers/)):

- Chen, N., Tong, Y., Yang, Y., He, Y., Zhang, X., Zou, Q., Wang, Q., He, B. — *Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation*, **ACL 2026 Findings**, [arXiv:2604.18005](https://arxiv.org/abs/2604.18005). Code: [`Xtra-Computing/MAS_Diversity`](https://github.com/Xtra-Computing/MAS_Diversity).

OSS projects:

- [`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox) — Apache-2.0 microVM sandbox.
- [`ghostwright/phantom`](https://github.com/ghostwright/phantom) — Apache-2.0 persistent autonomous AI co-worker.
- [`eric-tramel/moraine`](https://github.com/eric-tramel/moraine) — cross-harness trace MCP.
- [`midea-ai/SemaClaw`](https://github.com/midea-ai/SemaClaw) — companion code for the SemaClaw paper.
- [`aorwall/moatless-tree-search`](https://github.com/aorwall/moatless-tree-search) — Apache-2.0 reference implementation of SWE-Search MCTS.
- [`facebookresearch/swe-rl`](https://github.com/facebookresearch/swe-rl) — NeurIPS 2025 RL-on-software-evolution framework (stretch §10.3).
- [`MineDojo/Voyager`](https://github.com/MineDojo/Voyager) — open-source code for the Voyager curriculum / skill library.
- [`stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy) — DSPy compiler for LM pipelines (stretch §10.2).
- [`anthropics/skills`](https://github.com/anthropics/skills) and [`skills-mcp/skills-mcp`](https://github.com/skills-mcp/skills-mcp) — MCP-portable skill registry pattern Lyra mirrors.
- [`openai/SWELancer-Benchmark`](https://github.com/openai/SWELancer-Benchmark) — $1 M Upwork-task benchmark (Diamond split is public).
- [`sierra-research/tau2-bench`](https://github.com/sierra-research/tau2-bench) — τ³-Bench (airline, retail, telecom, banking, voice).
- [`harbor-framework/terminal-bench-2`](https://github.com/harbor-framework/terminal-bench-2) — Terminal-Bench 2.0 task suite.
- [`openai/prm800k`](https://github.com/openai/prm800k) — 800 k step-level correctness labels (PRM training data).
- [`deepseek-ai/DeepSeek-R1`](https://github.com/deepseek-ai/DeepSeek-R1) — MIT-licensed reasoning model (671 B / 37 B active) used as a default profile in the cascade router.

Industry framing:

- Ryan Leopo (OpenAI), 2026 — *Harness Engineering* talk: "Code is Free; the new scarce resources are Human Time, Attention, Context Window."
- Sundar Pichai, 2024-10 — Google AI-assisted code share grew from ~25 % to ~75 % in ~18 months.
- OWASP Top 10 for LLMs (2025) — *LLM08:2025 Vector and Embedding Weaknesses* (formal recognition of PoisonedRAG-class attacks).
- OpenAI, 2026-04 — GPT-5.5 release: 82.7 % on Terminal-Bench 2.0, 84.9 % on GDPval ([summary](https://www.marktechpost.com/2026/04/23/openai-releases-gpt-5-5-a-fully-retrained-agentic-model-that-scores-82-7-on-terminal-bench-2-0-and-84-9-on-gdpval/)).
- Z.AI, 2026-04 — GLM-5.1 (754 B open-weight) sustains 8-hour autonomous execution on SWE-bench Pro ([summary](https://www.marktechpost.com/2026/04/08/z-ai-introduces-glm-5-1-an-open-weight-754b-agentic-model-that-achieves-sota-on-swe-bench-pro-and-sustains-8-hour-autonomous-execution/)).

Internal:

- [`roadmap-v1.5-v2.md`](roadmap-v1.5-v2.md) — the existing milestone plan this doc supplements.
- [`feature-parity.md`](feature-parity.md) — the Claude-Code / OpenClaw / Hermes parity matrix this doc extends with an ARIA column and the eight ★ rows.
- [`tdd-discipline.md`](tdd-discipline.md) — the RED-test-first discipline every section above relies on.
- [`threat-model.md`](threat-model.md) — already covers sandbox + permission threats; v1.9 §3.6 extends it with the RAG poisoning chapter.
- [`architecture.md`](architecture.md) — block diagram each new module slots into.
