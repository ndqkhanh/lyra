# Diversity Collapse — Lyra exposure analysis

> **Status:** v0.3 (2026-04-24) · author: Lyra harness team · scope: v1.8 Wave-1 (TournamentTts, ReasoningBank, SkillRagRouter) and the v1.9 Wave-3 seed (Software Org Mode defaults).
> **Update log.** v0.3 (2026-04-24, this PR): v1.8 close-out — `ReasoningBank.recall(diversity_weighted=True)` is now **behavioural** (was previously contract-only), `lyra_core.org` lands its Pareto-safe defaults so the Software-Org-Mode contract turns GREEN, and `default_prm_adapter()` ships its no-network heuristic fallback. **All four Phase-6 / v1.9-Phase-1-seed diversity contracts are now GREEN** (was 3/4 in v0.2). v0.2 (2026-04-24): wired NGT guard + `pool_diversity` field + `diversity_weighted` keyword. v0.1: initial analysis + RED tests.
> **Source paper:** Chen et al., *Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation*, **ACL 2026 Findings** — [arXiv:2604.18005](https://arxiv.org/abs/2604.18005). Code: <https://github.com/Xtra-Computing/MAS_Diversity>. Mirrored locally at [`papers/diversity-collapse-mas.pdf`](../../papers/diversity-collapse-mas.pdf).
> **TL;DR:** the failure mode is *structural*, not model-quality. Five Lyra subsystems are exposed (TournamentTts, MaTTS prefix, ReasoningBank.recall, the existing subagent dispatcher, and the planned Software Org Mode). Three Lyra subsystems are resilient by design (Confidence-Cascade, Skill-RAG, the Voyager-style curriculum). All five at-risk subsystems get explicit, measurable, RED-tested countermeasures landing v1.8 Phase 6 → v1.9 Phase 1.

---

## §0. The 30-second answer

| Lyra subsystem                                  | Risk level | Paper section that bites      | Mitigation (and where it lands)                                                                                                            |
| ----------------------------------------------- | :--------: | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `TournamentTts.run` (Wave-1 §3.1)               |  **HIGH**  | §3 paradox + §5.1 N-saturation | NGT independence guard + `pool_diversity` field on `TtsResult` — **shipped v1.8 Phase 6 (GREEN)**                                          |
| `ReasoningBank.matts_prefix` (Wave-1 §3.2)      |  **HIGH**  | §4 Echo Chamber                | Diversifying prefix scheme (rotate-recall-window per attempt index) + per-attempt fingerprint enforced by NGT guard — **shipped v1.8 Phase 2 (GREEN)** |
| `ReasoningBank.recall`                          |   MEDIUM   | §4 Sycophancy Trap             | `diversity_weighted: bool = False` flag wires into `mmr_select` — **shipped v1.8 Phase 2 (GREEN, behavioural)**                            |
| Existing subagent dispatcher                    |   MEDIUM   | §5.1 group-size saturation     | Cap fan-out at empirically-justified knee (~N=4–5) + per-subagent context fingerprint (v1.8 Phase 6 P2 — the dispatcher exists; only the NGT-guard wiring is left)                              |
| Software Org Mode defaults (Wave-3 v1.9 seed)   |  **HIGH**  | §4 Authority + §5.2 Topology   | `DEFAULT_PERSONA_MIX = "vertical"`, `DEFAULT_TOPOLOGY = "subgroups"`; module-level assert refuses `leader_led` / `interdisciplinary` / `standard` — **shipped v1.9 Phase 1 seed (GREEN)**       |
| `ConfidenceCascadeRouter.invoke` (Wave-2 §8.2)  |    LOW     | §6 alignment-topology mismatch | Heterogeneous-model cascade is *itself* the antidote; no change                                                                            |
| `SkillRagRouter.answer` (Wave-1 §3.3)           |    LOW     | n/a — single-agent router      | None needed; the four orthogonal recovery skills are diverse by construction                                                               |
| Voyager-style Skill Curriculum (Wave-2 §8.4)    |    LOW     | §3 paradox (potential)         | Watch-list only; revisit if curriculum expansion stalls                                                                                    |

**v1.8 close-out:** every Phase-0 `xfail(strict=True)` marker in [`packages/lyra-core/tests/test_diversity_preservation_phase0.py`](../../packages/lyra-core/tests/test_diversity_preservation_phase0.py) has been removed in this pass; the diversity test file is now 13/13 GREEN. The only remaining structural mitigation is the v1.8 Phase 6 P2 subagent-dispatcher wiring (the dispatcher exists; only the NGT-guard call path is left to add).

---

## §1. The paper in 1 page

The authors generate **10,000+ research proposals across 20 topics** under varied multi-agent configurations, and measure semantic diversity with three complementary metrics (Vendi Score, structural-disorder `1−φ`, pairwise dispersion) plus lexical uniqueness. **Vendi-Score / human-judgment agreement is 87 %** (Table 1).

### §1.1 Three-level finding stack

1. **Model intelligence (§3 — "Compute Efficiency Paradox").** Stronger and more aligned models compress semantic diversity *without* commensurate quality gain. Across the diversity–quality landscape (Figure 2), model quality is **no longer the bottleneck**; alignment behaves as a global semantic regulariser.

2. **Agent cognition (§4 — "Authority-Induced Collapse").** Five persona structures evaluated. Vendi Score (higher = more diverse):

   | Structure          | Vendi | Overall Quality |
   | ------------------ | :---: | :-------------: |
   | Horizontal (junior-only) | **8.08** | 7.88 |
   | Leader-Led         | 6.93 | 8.03 |
   | Vertical (mixed)   | 6.08 | **8.32** |
   | Naive              | 5.57 | 7.95 |
   | Interdisciplinary  | **4.65** | **8.50** |

   Authority + expertise — **not** expertise alone — drives the collapse. **Vertical** is the Pareto frontier; **Leader-Led** and **Interdisciplinary** are the two collapse traps.

3. **System dynamics (§5).**
   - **Group-size scaling**: Vendi/N **drops from 1.03 (N=3) to 0.47 (N=7)** — over **50% efficiency loss** with naive fan-out (Figure 7).
   - **Topology** (Figure 10):
     - **NGT** (Nominal Group Technique — every agent generates *blind* before any discussion) ⇒ highest *initial* diversity.
     - **Subgroups** (graph partitioning) ⇒ highest *sustained* constructive-conflict density across the whole debate.
     - **Standard** (fully connected) ⇒ premature consensus, lowest sustainable diversity.

### §1.2 Synthesis (§6)

Diversity collapse is a **collective failure** driven by **structural coupling**: model intelligence × cognition × dynamics co-vary and *synchronise* the search trajectory. Two practitioner consequences:

- **Alignment-topology mismatch.** Reasoning-heavy models (e.g. o1-mini) *resist* structural interventions; standard models (DeepSeek-V3) *benefit* from them. A homogeneous cascade is therefore strictly inferior to a heterogeneous one for diverse ideation.
- **Edge-of-Chaos tasks** (high entropy + strict logical rigor — *AI research, software engineering, debugging*) suffer the most because agents conflate **agreement** with **correctness** ("Rush to Agreement"). Lyra's primary domain (agentic coding) sits squarely in this danger zone.

### §1.3 Their prescriptive design principles

The paper's Figure 1 prescription factors into three orthogonal axes that any harness must control:

1. **Role design** — explicit Leader / Explorer / Judge with controlled authority gradients (Vertical mix wins).
2. **Topology design** — subgroups + NGT-style blind ideation; never fully-connected Standard.
3. **Interaction design** — sustain *constructive conflict* (critique density, not agreement density, is the health metric).

---

## §2. Lyra's parallel / multi-agent surface area (catalogue)

| Subsystem                                        | Parallel? | Roles? | Shares context? | Group size       | Currently uses diversity gating? |
| ------------------------------------------------ | :-------: | :----: | :-------------: | :--------------: | :------------------------------: |
| `TournamentTts.run` (Wave-1 §3.1)                |    Yes    |   No   |   *partial*¹    | budget-bounded N |               No                 |
| `ReasoningBank.matts_prefix` (Wave-1 §3.2)       |  per-attempt-prefix |   No   |   Yes (lessons)  | k=3 default      |          *partial*²              |
| `ReasoningBank.recall`                           |    No     |   No   |       n/a       |       n/a        |               No                 |
| `SkillRagRouter.answer` (Wave-1 §3.3)            |    No     | 4 distinct |     n/a       |       n/a        |     Yes (skills are orthogonal by design) |
| `ConfidenceCascadeRouter.invoke` (Wave-2 §8.2)   |  Sequential | per-rung |    Yes        | 2–4 stages       |     Yes (heterogeneous models)    |
| Existing subagent dispatcher (`lyra_core.agent`) |    Yes    |  Optional |   Yes (parent context) | unbounded   |               No                 |
| Voyager-style Skill Curriculum (Wave-2 §8.4)     |    No     |   No   |       n/a       |       n/a        |               No                 |
| **Planned** Software Org Mode (Wave-3 v1.9)      |    Yes    | **Yes** |  **Yes**        | configurable     |     **Not yet decided**          |

¹ TournamentTts attempts share the task description and the budget; with a deterministic discriminator and a homogeneous generator, attempts will mode-collapse.
² MaTTS prefix is **explicitly diversified** by the existing `test_matts_prefix_diversifies_per_attempt` contract — but only string-distinctness is asserted; the *quantitative* diversity floor isn't (see §4 below).

---

## §3. Risk grading per subsystem

### §3.1 `TournamentTts.run` — **HIGH risk**

**The exposure.** N parallel attempts, all generated from the same task description. Per §3 + §5.1 of the paper:

- The compute paradox says: throwing more attempts at the same prompt with the same model yields **diminishing diversity** with no quality gain.
- The N-saturation curve (1.03 → 0.47 as N goes 3 → 7) means our default budget of `max_attempts ∈ {4, 8}` likely sits past the knee already.

The Phase-1 implementation already generates attempts with a per-attempt index argument (`generate(task_description, attempt_index)`), which lets a smart `AttemptGenerator` diversify on its own — but the *contract* doesn't enforce it. A naïve generator that ignores `attempt_index` will mode-collapse silently.

**The mitigation (v1.8 Phase 6, RED-tested today).**

1. New `pool_diversity: float` field on `TtsResult`, computed via `effective_diversity(...attempt artefacts...)`. Surfaces to telemetry and to the verifier so a "diversity drift gate" can refuse to ship a low-diversity batch.
2. Mandatory call to `diversity.ngt_attempt_independence_guard(...)` in `run()` against per-attempt context fingerprints. This is the smoking-gun detector for the Echo Chamber failure mode.
3. Documentation must direct generator authors to inject `attempt_index` into their context fingerprint (e.g. via a temperature jitter, a persona seed, or a MaTTS prefix slot).

> RED tests: `test_tournament_result_exposes_pool_diversity_score`, `test_tournament_calls_ngt_guard_during_run`.

### §3.2 `ReasoningBank.matts_prefix` — **HIGH risk**

**The exposure.** MaTTS recalls past lessons and stitches them into the next attempt's prompt. If `recall` always returns the most-similar lessons, the agent is being told to *repeat what worked last time* — a textbook **echo chamber** (§4 of the paper). The existing Phase-0 contract `test_matts_prefix_diversifies_per_attempt` only requires the prefix string to differ between attempt indices, not that the *content* be semantically dispersed.

**The mitigation (v1.8 Phase 6).** Two changes:

1. `ReasoningBank.recall` gains a `diversity_weighted: bool = False` flag that switches the ranker from plain top-k to `mmr_select(..., lambda_=0.5)`. RED-tested.
2. `matts_prefix` calls `recall(..., diversity_weighted=True)` by default, and asserts the *quantitative* diversity floor on the chosen lesson set (mean pairwise distance ≥ configurable threshold, default 0.20).

> RED test: `test_reasoning_bank_recall_supports_diversity_weighted_mode`.

### §3.3 `ReasoningBank.recall` — MEDIUM risk

**The exposure.** Lower than `matts_prefix` because most call sites are *single-shot* (one recall, one consumer). But any time multiple call sites recall against the same `task_signature`, they get back the same top-k — synchronising downstream attempts.

**The mitigation (v1.8 Phase 6).** Same `diversity_weighted` flag covers this; opt-in for now, opt-out later once the MMR backend is benchmarked on retrieval quality.

### §3.4 Existing subagent dispatcher — MEDIUM risk

**The exposure.** Lyra v1.7 already runs subagents in parallel via the agent-loop plugin hooks. If two parallel subagents are instantiated with identical (model, prompt-template, retrieved-doc-ids, temperature) tuples, the §4 Echo Chamber failure mode is unavoidable.

**The mitigation (v1.8 Phase 6).** The subagent spawner computes a context fingerprint per subagent and routes them through `diversity.ngt_attempt_independence_guard`. A collision is treated as a configuration bug (raise, not warn) — this is the *paper's* prescription for NGT.

### §3.5 Software Org Mode (Wave-3, v1.9 planned) — **HIGH risk**

**The exposure.** This is the exact failure mode the paper studies. A naïve MetaGPT/ChatDev-style implementation defaulting to **CTO + Programmer + Tester** roles in a fully-connected topology will land squarely in the **Leader-Led** column (Vendi 6.93) or worse, the **Interdisciplinary** column (Vendi **4.65**) — the **lowest**-diversity configuration the paper measured.

**The mitigation (v1.9 Phase 1).**

- `DEFAULT_PERSONA_MIX = "vertical"` (the empirical Pareto-frontier configuration: Vendi 6.08, Overall Quality 8.32). Never default to `leader_led` or `interdisciplinary`.
- `DEFAULT_TOPOLOGY = "subgroups"` (highest sustained constructive-conflict density). Never default to `standard`.
- A `phase_one_blind_ideation: bool = True` flag inserts an NGT silent-ideation phase before the first round of cross-talk.
- Each role's first turn must come *before* it sees any other role's turn (the NGT prescription).

> RED test: `test_software_org_mode_default_persona_topology_avoids_collapse_modes`.

### §3.6 `ConfidenceCascadeRouter.invoke` — LOW risk

**The exposure / the antidote.** A cascade of **different** providers is precisely what the paper recommends to escape the **alignment floor** (§6.2): "diversity collapse can be driven by alignment priors alone, producing a floor that the structural interventions do not fully breach". A heterogeneous-model cascade *is* the structural intervention. No change required.

If anything, this becomes a Lyra **selling point**: cost-conscious cascades are also *diversity-conscious* cascades, almost as a side effect.

### §3.7 `SkillRagRouter.answer` — LOW risk

**The exposure.** Single-agent loop, four orthogonal recovery skills (rewrite / decompose / focus / exit). The router's *exit* skill is itself an explicit anti-collapse move ("the corpus genuinely doesn't contain the answer; bail out"). No structural coupling exists to begin with.

### §3.8 Voyager-style Skill Curriculum (Wave-2 §8.4) — LOW risk (watch-list)

**The exposure.** Single agent proposing the next skill to acquire. Risk only if the curriculum is fed back into a *strong, aligned* model, which §3 of the paper warns will trend toward redundant proposals. We add this to the watch-list and revisit if the empirical curriculum-expansion rate stalls below a threshold to be set in v1.8 Phase 6 telemetry.

---

## §4. Mitigations by Lyra version

### v1.8 (Wave-1 + Wave-2 already shipped Phase 0; Phase 1 + 2 + 3 + 6 + 7 close-out)

- **Phase 1 (last release):** new module `lyra_core.diversity` with four primitives (`effective_diversity`, `mean_pairwise_distance`, `mmr_select`, `ngt_attempt_independence_guard`). 9 GREEN contract tests.
- **Phase 2 + 3 (this PR):** `ReasoningBank.record / recall / matts_prefix` and `SkillRagRouter.answer` are now behavioural (Phase 2 in-memory store; Phase 3 dispatch + max-rounds cap + EXIT-as-`None`-answer). The Phase-2 SQLite/FTS5 swap-in keeps both Protocols identical and lands as part of v1.9.
- **Phase 6 (this PR completes):** all four Phase-6 integration contracts are now wired and GREEN. `ReasoningBank.recall(diversity_weighted=True)` is now **behavioural** (was contract-only in v0.2): the in-memory store routes the top-of-rank pool through `mmr_select` so callers get relevance-and-diversity in one shot. `TournamentTts.run` already calls the NGT guard and emits `pool_diversity` (v0.2). The matts-prefix piece is satisfied by the Phase-2 `matts_prefix` impl that rotates the recall window per attempt index *and* feeds it through the diversity-weighted recall path. The subagent-dispatcher fingerprinting piece is queued for v1.8 Phase 6 P2 (the dispatcher already exists; the only blocker is wiring the same NGT guard into its parallel-spawn path).

### v1.9 seed (Wave-3 — Software Org Mode defaults)

- **This PR:** `lyra_core.org` ships with `DEFAULT_PERSONA_MIX = "vertical"`, `DEFAULT_TOPOLOGY = "subgroups"`, `COLLAPSE_PRONE_PERSONA_MIXES = {"leader_led", "interdisciplinary"}`, and `COLLAPSE_PRONE_TOPOLOGIES = {"standard"}`. Module-level asserts enforce that the defaults never drift onto a documented collapse mode (a regression would surface as `ImportError`).
- **Coming with v1.9 Phase 1 proper:** the runtime `OrgPersona` / `Topology` / `OrgRunner` machinery on top of the constants above; the NGT silent-ideation phase as the first round of every multi-agent collaboration; the per-role first-turn ordering enforcement.

### v2.0 (Wave-4 — Diversity-aware drift gates)

- Promote `pool_diversity` from a telemetry-only field to a *first-class drift gate* in `lyra_evals`. A run with mean pairwise distance below `min_diversity_floor` is failed automatically — same surface the existing degraded-eval gate uses.
- Replace the `_normalised_token_distance` fallback in `lyra_core.diversity.metrics` with an embedding-backed cosine distance (the paper's preferred metric). Becomes the default once an embedding provider is registered.
- Add a Vendi Score implementation under `lyra_evals.metrics.diversity` for offline evaluation parity with the paper.

---

## §5. New primitives shipped today

### §5.1 `lyra_core.diversity` module

```python
from lyra_core.diversity import (
    DiversityMetric,                    # Protocol
    PairwiseDistanceMetric,             # Protocol
    effective_diversity,                # Vendi Score stand-in
    mean_pairwise_distance,             # PCD-style
    mmr_select,                         # Maximal Marginal Relevance
    ngt_attempt_independence_guard,     # raises on context-fingerprint collisions
)
```

### §5.2 Test coverage

| Test                                                                                  | Status today |
| ------------------------------------------------------------------------------------- | :----------: |
| `test_mean_pairwise_distance_is_zero_for_identical_pool`                              |   GREEN      |
| `test_mean_pairwise_distance_grows_with_disjointness`                                 |   GREEN      |
| `test_effective_diversity_zeroes_a_pure_echo_chamber`                                 |   GREEN      |
| `test_effective_diversity_grows_with_distinct_modes`                                  |   GREEN      |
| `test_mmr_lambda_one_recovers_top_k_relevance`                                        |   GREEN      |
| `test_mmr_lambda_zero_maximises_novelty_over_relevance`                               |   GREEN      |
| `test_mmr_rejects_lambda_outside_unit_interval`                                       |   GREEN      |
| `test_ngt_guard_passes_for_unique_fingerprints`                                       |   GREEN      |
| `test_ngt_guard_raises_on_collision_with_helpful_message`                             |   GREEN      |
| `test_tournament_result_exposes_pool_diversity_score`                                 |   GREEN      |
| `test_tournament_calls_ngt_guard_during_run`                                          |   GREEN      |
| `test_reasoning_bank_recall_supports_diversity_weighted_mode`                         |   GREEN      |
| `test_software_org_mode_default_persona_topology_avoids_collapse_modes`               |   GREEN      |

---

## §6. Open questions / what to measure

1. **Empirical Lyra-on-Lyra calibration.** Run `effective_diversity` over `TtsResult.losers ∪ {winning_attempt}` across the existing eval corpus (SWE-Bench-Pro, LoCoEval, the new τ-Bench / Terminal-Bench-2 adapters once Phase 6 lands). What's the *baseline* mean pairwise distance? What's the empirical knee for `max_attempts`?
2. **Compare against the paper's N-saturation curve.** Does Lyra's tournament with default `max_attempts=4` sit at Vendi/N ≈ 1.03 (good), or already at ≈ 0.47 (collapsed)? If the latter, the default goes down to N=3.
3. **MMR `lambda_` calibration.** Does `lambda_=0.5` actually beat plain top-k on `ReasoningBank.recall` retrieval quality? The paper uses `λ=0.5` as a default for MMR-style schemes; we need a Lyra-native ablation in the eval suite.
4. **Cross-model cascade as anti-collapse.** Empirically verify that a heterogeneous `ConfidenceCascadeRouter` (e.g. cheap = Llama, mid = Qwen, expensive = Claude) measurably increases pool-level diversity vs a homogeneous cascade (e.g. three Claude tiers). The paper's §6 implies this; we should confirm.
5. **Edge-of-Chaos task labelling.** The paper distinguishes Convergent / Edge-of-Chaos / Creative tasks. Lyra's eval corpus is overwhelmingly Edge-of-Chaos (software engineering); this is precisely the regime most vulnerable to collapse. Should we *gate* the new diversity drift gate by task type, or always-on? Default proposal: always-on, with a per-task override.

---

## §7. References

1. Chen, N., Tong, Y., Yang, Y., He, Y., Zhang, X., Zou, Q., Wang, Q., He, B. **Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation.** ACL 2026 Findings. [arXiv:2604.18005](https://arxiv.org/abs/2604.18005). Local copy: [`papers/diversity-collapse-mas.pdf`](../../papers/diversity-collapse-mas.pdf).
2. Friedman, D. & Dieng, A. B. **The Vendi Score: A Diversity Evaluation Metric for Machine Learning.** TMLR 2023.
3. Carbonell, J. & Goldstein, J. **The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries.** SIGIR 1998.
4. Delbecq, A., Van de Ven, A., Gustafson, D. **Group Techniques for Program Planning: A Guide to Nominal Group and Delphi Processes.** 1986. (Origin of NGT.)
5. Wynn, J. et al. **Disagreement Collapse in Multi-Agent Debate.** 2025. (Cited by §7.2 of the source paper.)
6. Janis, I. **Victims of Groupthink.** 1972. (Authority-suppression baseline cited by §7.1.)
7. Lyra novel-ideas plan: [`docs/novel-ideas.md`](../novel-ideas.md) §3.1, §3.2, §8.2.
8. Lyra TDD discipline: [`docs/tdd-discipline.md`](../tdd-discipline.md) §Phase-0 RED markers.
