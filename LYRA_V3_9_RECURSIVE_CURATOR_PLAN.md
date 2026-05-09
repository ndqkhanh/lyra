# LYRA — v3.9 Recursive Skills Curator Plan

> **Living-knowledge supplement to Lyra's roadmap.** Adds phases
> **L39-1 through L39-9** that fold the Argus Omega Vol. 3 recursive-curator
> design ([`docs/197-argus-omega-vol-3-recursive-skills-curator.md`](docs/197-argus-omega-vol-3-recursive-skills-curator.md))
> into Lyra without breaking the v3.8 cascade primitives. v3.9 makes the
> curator a *first-class Talent in Lyra's own catalog*, governs it under
> formal termination invariants, lets it create specialist sub-curators
> under failure-class pressure, runs it through a co-evolving surrogate
> verifier, and maintains a Pareto frontier of curator strategies via
> evolutionary search.
>
> Read alongside [`LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md`](LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md)
> (the immediate predecessor — v3.9 depends on its `Talent` envelope
> from L38-4, the trust framework from L38-3, the witness lattice from
> L38-3, the HORIZON failure-class detector from L38-9 of v3.8 — most
> of which themselves depend on v3.7's routines and worktrees) and
> [`CHANGELOG.md`](CHANGELOG.md). Several v3.9 phases are *MVP-equivalent*
> deliverables that already give Lyra the strongest published curator
> design when shipped alone.

---

## §0 — Why this supplement

Lyra v3.8 lands the Argus cascade (BM25 → embedding → cross-encoder → KG-navigate),
trust framework, witness lattice, Talent envelope, and skill catalog graph.
v3.8's curator is a *daemon with capabilities* — F1 drift detection, F3 description
rewriter, F4 stale-skill demotion, F6 consolidation, F7 split, F8 squatting cleanup,
plus the L3 evolver loop. None of these is *recursive* in the strong sense the
2026 skill-evolution literature implies.

A *recursive skills curator* (per `docs/197` §1) has six properties Lyra v3.8 lacks:

| Property | v3.8 status | v3.9 closes it via |
|---|---|---|
| **P1: Curator-as-Talent in the catalog** | Curator is a daemon, not a routable Talent | L39-1 — `argus-curator-general` SKILL.md + `kind: curator` cascade extension |
| **P2: Self-curation** | Curator metadata is fixed | L39-3 — invariant SC-1 + governed validation gate |
| **P3: Curator-creating-curator** | Single global curator | L39-5 — specialist creation pipeline; SC-2 depth bound |
| **P4: Co-evolutionary curator-verifier** | L3 evolver runs alone | L39-4 — information-isolated surrogate verifier (different LLM family) |
| **P5: Pareto-frontier of curator strategies** | Single Ralph loop | L39-7 — k=3 frontier per harness; round-robin; skill-merge |
| **P6: Termination guarantees on the recursion** | None | L39-8 — seven formal correctness guarantees ported from `docs/191` to the curation graph |

**The good news.** Lyra v3.7 + v3.8 already supply the substrate:

| v3.9 need | v3.7 / v3.8 primitive that fits | Status |
|---|---|---|
| Curator runs as Talent | `Talent` envelope (L38-4) | ✅ ships in v3.8 |
| `kind: curator` routing | `ArgusCascade` mode flag (L38-1) | ✅ ships in v3.8 |
| HR lifecycle for curators | `Talent` HR review/PIP/offboarding (L38-4) | ✅ ships in v3.8 |
| Surrogate verifier substrate | `LifecycleBus` event watcher (`lyra-core/lifecycle.py`) | ✅ existing |
| Specialist creation routing | HORIZON failure-class detector (L38-9 of v3.8 → forward-portable) | ✅ ships in v3.8 |
| 24/7 curator routine | v3.7 routine registry (L37-8) | ✅ ships in v3.7 |
| Pareto-frontier scoring | `Arena` + `EloRating` (`lyra-core/arena/elo.py`) | ✅ existing |
| Witness-lattice evidence | `WitnessLattice` (L38-3) | ✅ ships in v3.8 |
| Curator git versioning | git already in repo + worktree primitive (L37-5) | ✅ ships in v3.7 |
| Trust ladder for curators | `TrustLedger` (L38-3) | ✅ ships in v3.8 |

So v3.9 is mostly a **composition + discipline + invariant-enforcement** job, not greenfield. Phases L39-1 through L39-4 are the **MVP** and land in **~7 weeks**; L39-5 through L39-9 are the production-hardening tail and land in ~9 more weeks (~16 weeks total).

### Two themes (mirror Argus Omega Vol. 3)

| Theme | Phases |
|---|---|
| **A. Curator-as-Talent + Self-Curation** (Vol. 3 reframes 11–12, 14) | L39-1 curator-as-Talent + cascade extension · L39-2 six component Talents · L39-3 self-curation invariant SC-1 · L39-4 information-isolated surrogate verifier |
| **B. Specialist creation + Pareto frontier + Federation** (Vol. 3 reframes 13, 15) | L39-5 specialist creation pipeline · L39-6 three-tier curator-bank · L39-7 Pareto-frontier evolutionary search · L39-8 seven formal correctness guarantees + curator HR · L39-9 curator Talent Market federation |

### Identity — what does NOT change

The Lyra invariants stay verbatim — four-mode taxonomy, two-tier model split,
5-layer context, NGC compactor, hook lifecycle, SKILL.md loader, subagent
worktrees, TDD plugin gate. v3.9 only **adds**.

The v3.8 cascade `ArgusCascade.find()` continues to work; v3.9 is a *catalog of
curator Talents* that the cascade routes to when `kind: curator` is requested,
never replacing it.

---

## §1 — Architecture

```mermaid
flowchart TB
    subgraph CAT [Lyra catalog (extended)]
        T[Regular Talents<br/>K1/K2/K3/K4]
        CG[argus-curator-general<br/>Talent]
        CSP[argus-curator-&lt;class&gt;<br/>specialist Talents]
        CE[argus-extractor]
        CJ[argus-judge]
        CM[argus-merger]
        CP[argus-proposer]
        CSB[argus-skill-builder]
        CSV[argus-surrogate-verifier]
    end

    subgraph FRT [Pareto-frontier strategies]
        F1[Strategy 1]
        F2[Strategy 2]
        F3[Strategy 3]
    end

    subgraph SC [Self-curation invariant SC-1]
        MGate[Monotone non-degradation gate]
        IBound[Bounded iteration N_max=7]
        FPDet[Fixed-point detection K=3]
        GVal[Governed-validation gate]
        HITL[HITL gate at trust-tier boundaries]
    end

    subgraph SP [Specialist creation SC-2]
        FCD[HORIZON failure-class detector<br/>v3.8 L38-9]
        DBound[Depth bound 3]
        NoDup[No same-class duplicate]
    end

    subgraph SVL [Surrogate verifier loop]
        SVT[argus-surrogate-verifier Talent<br/>different LLM family]
        SVB[Brier-score calibration<br/>weekly]
        SVCo[Co-evolution cycle]
    end

    subgraph LP [v3.7 routine substrate]
        RC[RalphCuratorRoutine]
    end

    T --> CG
    CG -. routes class queries .-> CSP
    CG --> CE
    CG --> CJ
    CG --> CM
    CG --> CP
    CG --> CSB
    CG --> SC
    SC -. proposed-edit .-> SVT
    SVT -. accept/reject/HITL .-> CG
    CG -. specialist-trigger .-> SP
    SP -. new-Talent .-> CSP
    FRT -. picks .-> CG
    CAT -. trace .-> SVCo
    SVCo --> SVB
    LP -. drives .-> CG
    LP -. drives .-> FRT

    classDef new fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    classDef existing fill:#c8e6c9,stroke:#2e7d32,stroke-width:1px
    class T,LP,RC existing
    class CG,CSP,CE,CJ,CM,CP,CSB,CSV,FRT,SC,SP,SVL new
```

### Package map (deltas vs v3.8)

| Package | Status |
|---|---|
| `lyra-core/skills/curator/` | **NEW PACKAGE (L39-1, L39-3, L39-5, L39-7)** — `self.py`, `specialist.py`, `frontier.py`, `bank.py`, `hr.py` |
| `lyra-core/skills/curator/components/` | **NEW (L39-2)** — `extractor.py`, `judge.py`, `merger.py`, `proposer.py`, `skill_builder.py`, `surrogate_verifier.py` |
| `lyra-core/skills/talent.py` | **Extended (L39-1)** — adds `kind: curator` field; `parent_curator: str | None`; `inherits_principles_from: str | None` |
| `lyra-skills/argus_cascade.py` | **Extended (L39-1)** — adds `kind` filter; `route_curator(...)` shortcut |
| `lyra-core/governance/witness.py` | **Extended (L39-3)** — emits curator-edit witnesses; replay supports curator-state reconstruction |
| `lyra-core/cron/routines/ralph_curator.py` | **NEW (L39-7)** — frontier evolution + skill-merge cron |
| `lyra-core/skills/curator/hr.py` | **NEW (L39-8)** — review → PIP → offboarding for curators; seven formal-guarantee tests |
| `lyra-mcp/server/app.py` | **Extended (L39-9)** — exposes curator inspection / replay / market tools |
| `skills/argus-curator-general/SKILL.md` | **NEW (L39-1)** — the canonical general curator |
| `skills/argus-extractor/SKILL.md` etc. | **NEW (L39-2)** — six component Talents |
| `lyra-cli/commands/curator.py` | **NEW (L39-1, L39-7, L39-9)** — `lyra curator status / route / replay / frontier / market` |

---

## §2 — Phases L39-1 through L39-9

### L39-1 — Curator-as-Talent scaffold + `kind: curator` cascade extension

**Why now.** v3.8 ships the `Talent` envelope (L38-4) and the `ArgusCascade` (L38-1). The smallest possible v3.9 commit promotes the curator from a daemon to a routable Talent. Once the curator is a Talent, every later v3.9 phase becomes a Talent-mutation pattern, which Lyra already has discipline for.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/
  talent.py                # EXTEND — add curator-specific fields
                           # @dataclass(frozen=True) class Talent:
                           #     ...existing fields...
                           #     kind: Literal["regular", "curator"] = "regular"     # NEW
                           #     parent_curator: str | None = None                   # NEW (for specialists)
                           #     inherits_principles_from: str | None = None         # NEW

packages/lyra-skills/src/lyra_skills/
  argus_cascade.py         # EXTEND — kind-aware routing
                           # def find(self, query, *, kind="regular", ...):
                           #     candidates = self._all_talents()
                           #     if kind == "curator":
                           #         candidates = [t for t in candidates if t.kind == "curator"]
                           #     return self._cascade(query, candidates, ...)
                           #
                           # def route_curator(self, target_skill_id) -> Talent:
                           #     """Pick the right curator (general or specialist) for a target Talent."""

packages/lyra-cli/src/lyra_cli/commands/
  curator.py               # NEW — top-level curator command surface
                           # lyra curator status                   # health snapshot
                           # lyra curator route <target-skill>     # which curator handles it?
                           # lyra curator list                     # all curator-Talents in catalog
                           # lyra curator show <name>              # full Talent envelope

skills/argus-curator-general/
  SKILL.md                 # NEW — canonical general curator
                           # ---
                           # name: argus-curator-general
                           # kind: curator
                           # description: |
                           #   Audit, refine, consolidate, and retire skills in the Lyra catalog.
                           #   Use when a skill needs review (drift detected, telemetry signals,
                           #   description rewrite, consolidation, split, retirement).
                           # version: 0.1.0
                           # trust_tier: T_PINNED                  # ships at top tier as canonical
                           # working_principles:
                           #   - Never silently retire a T-Pinned skill
                           #   - Always emit a witness for every catalog edit
                           #   - Defer to surrogate verifier when its Brier score < 0.20
                           #   - Escalate to HITL on edits that change skill scope
                           # ---
                           # # Goal
                           # ...
```

**Tests (TDD).**

```text
packages/lyra-core/tests/skills/
  test_talent_curator_kind.py     # 8 tests — curator-kind serialization, parent_curator validation
  test_argus_cascade_curator.py   # 12 tests — kind=curator filter, route_curator behaviour

packages/lyra-cli/tests/
  test_cli_curator.py             # 6 tests — status / list / show / route commands
```

**Acceptance.**

- ✅ `lyra curator list` returns `argus-curator-general` after install.
- ✅ `lyra skill route --kind=curator "..."` only returns curator-Talents.
- ✅ Existing `ArgusCascade.find()` behaviour unchanged for `kind="regular"` (regression bench passes, all 2200+ tests still green).
- ✅ The general curator's Talent envelope round-trips through serialization without loss.

**Effort.** ~1.5 weeks.

---

### L39-2 — Six component Talents (Extractor, Judge, Merger, Proposer, Skill-Builder, Surrogate-Verifier)

**Why now.** L39-1 makes the curator routable; L39-2 *factors* the curator into composable pieces drawn from the four-corner skill-evolution literature ([167] AutoSkill's Extractor → Judge → Merger pipeline + [168] EvoSkill's Proposer → Skill-Builder + [169] CoEvoSkills' Surrogate-Verifier). Each piece is independently invocable and independently testable.

**Concrete deliverables.**

Six SKILL.md files, each with the full Talent envelope from L38-4:

```text
skills/argus-extractor/SKILL.md
skills/argus-judge/SKILL.md
skills/argus-merger/SKILL.md
skills/argus-proposer/SKILL.md
skills/argus-skill-builder/SKILL.md
skills/argus-surrogate-verifier/SKILL.md
```

**Component contracts** (Python protocol):

```text
packages/lyra-core/src/lyra_core/skills/curator/components/
  __init__.py
  extractor.py             # NEW — Extractor protocol
                           # class Extractor(Protocol):
                           #     async def extract(
                           #         self, window: ConversationWindow
                           #     ) -> list[CandidateSkill]
                           # default impl: LLM-driven pattern extraction (AutoSkill-style)

  judge.py                 # NEW — Judge protocol
                           # class Judge(Protocol):
                           #     async def judge(
                           #         self, candidate: CandidateSkill, neighbors: list[Talent]
                           #     ) -> Decision  # add | merge | discard
                           # default impl: LLM compares candidate to top-M neighbors

  merger.py                # NEW — Merger protocol
                           # class Merger(Protocol):
                           #     async def merge(
                           #         self, candidate: CandidateSkill, target: Talent
                           #     ) -> Talent
                           # default impl: semantic union; bumps SemVer patch

  proposer.py              # NEW — Proposer protocol (failure-driven)
                           # class Proposer(Protocol):
                           #     async def propose(
                           #         self, failures: list[FailureTrace], history: ProposalHistory
                           #     ) -> Intervention
                           # default impl: reads worst-scoring failures, emits textual intervention

  skill_builder.py         # NEW — SkillBuilder protocol (materializer)
                           # class SkillBuilder(Protocol):
                           #     async def build(
                           #         self, parent: Talent, intervention: Intervention
                           #     ) -> Talent  # candidate Talent ready for evaluation

  surrogate_verifier.py    # NEW — SurrogateVerifier protocol
                           # class SurrogateVerifier(Protocol):
                           #     async def verify(
                           #         self, edit: CatalogEdit, rationale: str
                           #     ) -> Verdict  # accept | reject | escalate_HITL
                           # default impl: information-isolated LLM (different family from curator)
```

**Why protocols, not classes?** Each component must be swappable per Container ([191](docs/191-onemancompany-skills-to-talent.md) shape). LangGraph might want a different Extractor than Claude Code does.

**Tests.**

```text
packages/lyra-core/tests/skills/curator/components/
  test_extractor.py        # 10 tests — pattern extraction on synthetic windows
  test_judge.py            # 12 tests — add / merge / discard verdicts
  test_merger.py           # 8 tests — semantic union, version bumps, regression on body
  test_proposer.py         # 10 tests — failure-driven proposals
  test_skill_builder.py    # 8 tests — materialization with parent inheritance
  test_surrogate_verifier.py  # 12 tests — accept / reject / escalate; isolation tests
```

**Acceptance.**

- ✅ Each component Talent loads via `lyra skill show argus-<name>`.
- ✅ Each component is independently invocable: `lyra curator invoke argus-judge --candidate ... --neighbors ...`.
- ✅ End-to-end pipeline: Extractor → Judge → Merger produces a valid Talent edit on a planted-extraction-bench.
- ✅ Surrogate-verifier independence test: surrogate runs on a different LLM family from the host model (verified by checking model-family signature on init).

**Effort.** ~2 weeks.

---

### L39-3 — Self-curation invariant SC-1

**Why now.** Without an invariant, self-curation is just a self-applying daemon — and the obvious failure mode (curator amplifies itself toward higher self-scoring without external validation, F-76 in `docs/197` §5) lands immediately. SC-1 is the load-bearing safety property of the recursive curator.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/curator/
  self.py                  # NEW — self-curation engine + SC-1 invariant
                           # class SelfCurationEngine:
                           #     def __init__(
                           #         self,
                           #         curator: Talent,
                           #         verifier: SurrogateVerifier,
                           #         eval_set: CuratorEvalSet,
                           #         epsilon: float = 0.02,    # monotone tolerance
                           #         n_max: int = 7,           # bounded iteration
                           #         k_fixed_point: int = 3,   # fixed-point detection
                           #         delta: float = 0.005,     # fixed-point distance
                           #     ) -> None
                           #     async def cycle(self) -> SelfCurationOutcome:
                           #         """One self-curation cycle. Returns updated Talent or rollback."""
                           #         f_n = self.curator
                           #         phi_n = await self._score(f_n)
                           #         for n in range(self.n_max):
                           #             proposal = await self._propose_self_edit(f_n)
                           #             if await self._would_demote_trust_tier(f_n, proposal):
                           #                 raise BrightLine.SELF_DEMOTE  # HITL gate
                           #             f_next = await self._apply_proposal(f_n, proposal)
                           #             phi_next = await self._score_against_eval(f_next)
                           #             if phi_next < phi_n - self.epsilon:
                           #                 await self._rollback(f_n)
                           #                 raise BrightLine.SELF_DIVERGENCE
                           #             if await self._fixed_point_detected(f_n, f_next):
                           #                 return SelfCurationOutcome(converged=True, talent=f_next)
                           #             verdict = await self.verifier.verify(
                           #                 edit=CatalogEdit(before=f_n, after=f_next),
                           #                 rationale=proposal.rationale,
                           #             )
                           #             if verdict == Verdict.REJECT:
                           #                 await self._rollback(f_n)
                           #                 continue
                           #             if verdict == Verdict.ESCALATE_HITL:
                           #                 await self._await_hitl(f_next)
                           #             f_n, phi_n = f_next, phi_next
                           #         return SelfCurationOutcome(converged=False, talent=f_n)

  eval_set.py              # NEW — held-out curator-evaluation set
                           # class CuratorEvalSet:
                           #     def __init__(self, source: Literal["synthetic","witness","mixed"]) -> None
                           #     def refresh(self, witness_lattice: WitnessLattice) -> None
                           #     def score_curator(self, curator: Talent) -> float  # in [0, 1]
                           # synthetic = planted-edit-bench
                           # witness = stratified sample from past witness lattice
                           # mixed = recommended (60% synthetic + 40% witness)
```

**SC-1 invariant clauses (each gets a property-based test):**

1. **Monotone non-degradation.** Φ(f_{n+1}) ≥ Φ(f_n) − ε.
2. **Bounded iteration.** n ≤ N_max per cycle.
3. **Fixed-point detection.** ‖f_{n+1} − f_n‖ < δ for K consecutive iterations → exit.
4. **Governed-validation gate.** Each self-edit passes regression on the held-out eval set.
5. **HITL gate at trust-tier boundaries.** Self-demotion requires explicit human approval.

**Bright lines wired here:**

- `BL-VOL3-CURATOR-SELF-DEMOTE` (Vol. 3 §7) — self-edit would demote curator trust tier → HITL.
- `BL-VOL3-CURATOR-SELF-DIVERGENCE` — monotone clause violated → rollback + alert.

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_self_curation.py    # 25+ tests
                           # - 1000-iteration property-based random walk; Φ never drops > ε
                           # - n_max enforced
                           # - fixed-point detected at expected iteration on stationary inputs
                           # - eval-set regression caught (planted-bad-edit fails gate)
                           # - self-demote attempt triggers BL-VOL3-CURATOR-SELF-DEMOTE
                           # - rollback restores prior Talent state byte-for-byte

  test_eval_set.py         # 10 tests — synthetic / witness / mixed sources; refresh; scoring
```

**Acceptance.**

- ✅ Self-curation never demotes the curator below its starting state across 100 cycles.
- ✅ All five SC-1 clauses verified by property-based tests (1000+ random walks).
- ✅ Planted-bad-edit fails the governed-validation gate.
- ✅ `lyra curator self-cycle` runs one cycle and reports the outcome.

**Effort.** ~2 weeks.

---

### L39-4 — Information-isolated surrogate verifier

**Why now.** SC-1's verifier gate (clause 4 + 5) needs an actual verifier. The single most-cited ablation in CoEvoSkills ([169] §4) is that dropping the surrogate verifier costs 30 percentage points on long-horizon improvement. Without this phase, L39-3 is a stub.

**Concrete deliverables.**

```text
skills/argus-surrogate-verifier/SKILL.md
                           # ---
                           # name: argus-surrogate-verifier
                           # kind: curator                          # but never edits the catalog
                           # description: |
                           #   Watch curator edits. Emit accept / reject / escalate-HITL.
                           #   Sees only edits + rationale, never ground-truth tests.
                           # working_principles:
                           #   - Never query held-out test set
                           #   - Never share context with the curator
                           #   - Run on a different LLM family from the host model
                           # ---

packages/lyra-core/src/lyra_core/skills/curator/components/
  surrogate_verifier.py    # EXTEND from L39-2 stub to full impl
                           # class InformationIsolatedSurrogate(SurrogateVerifier):
                           #     def __init__(
                           #         self,
                           #         host_model_family: str,
                           #         allowed_families: tuple[str, ...] = ("qwen", "deepseek", "claude"),
                           #     ) -> None
                           #     async def verify(self, edit, rationale) -> Verdict:
                           #         # Hard guarantees:
                           #         # 1. Surrogate never sees ground-truth test results
                           #         # 2. Surrogate runs on a model from `allowed_families` minus host
                           #         # 3. Surrogate context is fresh — no shared state with curator
                           #         ...
                           #     def model_family(self) -> str: ...
                           #
                           # def assert_isolation(host: Model, surrogate: Model) -> None:
                           #     """Bright-line: refuse to start curator if surrogate isolation fails."""

  brier_calibration.py     # NEW — surrogate Brier-score tracking
                           # class BrierCalibration:
                           #     def record(self, edit_id: str, predicted: Verdict,
                           #                eventual: Outcome, witness_id: str) -> None
                           #     def score(self, window_days: int = 7) -> float
                           # tracks (predicted accept/reject) vs (eventual catalog-edit success)
                           # weekly job re-validates calibration

packages/lyra-core/src/lyra_core/cron/routines/
  surrogate_recalibration.py    # NEW — weekly co-evolution cycle
                                # class SurrogateRecalibrationRoutine(Routine):
                                #     trigger = CronTrigger("0 3 * * 0")  # Sunday 3am
                                #     async def run(self, ctx) -> None:
                                #         brier = ctx.brier_calibration.score(window_days=7)
                                #         if brier > 0.30:
                                #             await ctx.bright_lines.trip("BL-VOL3-SURROGATE-DRIFT")
                                #         if brier < 0.10:
                                #             await ctx.bright_lines.trip("BL-VOL3-SURROGATE-COLLUSION")
                                #         await ctx.surrogate_recalibrate(window_days=7)
```

**Information isolation discipline:**

| Rule | Enforcement |
|---|---|
| Different LLM family | `assert_isolation()` at curator init; refuses to start otherwise |
| No shared context | Surrogate runs in its own subprocess / Container; receives only edit + rationale, no curator transcript |
| No held-out test access | Surrogate Talent's `allowed-tools` excludes test-runner / oracle |
| Independent recalibration | Weekly routine reads (predicted, eventual) pairs from witness lattice |

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_surrogate_verifier.py  # 30+ tests
                              # - isolation: refuses start if surrogate same family as host
                              # - rejects ≥95% of planted-bad-edits (independence test)
                              # - accepts ≥85% of planted-good-edits (calibration test)
                              # - Brier score ≤ 0.20 on synthetic eval
                              # - calibration drift triggers BL-VOL3-SURROGATE-DRIFT
                              # - excessive-acceptance triggers BL-VOL3-SURROGATE-COLLUSION
                              # - context isolation: surrogate state is independent across calls
```

**Acceptance.**

- ✅ Surrogate refuses to start if same LLM family as host.
- ✅ Surrogate rejects ≥95% of planted-bad-edits on the bench.
- ✅ Surrogate Brier score ≤ 0.20 on held-out (predicted, eventual) pairs.
- ✅ Dropping the surrogate from the SC-1 loop costs ≥20pp on curator-edit-quality benchmark (matches [169]'s 30pp ablation directionally).
- ✅ Weekly recalibration routine runs, persists Brier scores, alerts on drift.

**Effort.** ~2 weeks.

---

**📍 v3.9 MVP checkpoint.** L39-1 + L39-2 + L39-3 + L39-4 = **~7.5 weeks**. After this, Lyra has a self-curating curator with co-evolutionary verification — the load-bearing recursive piece. Stop here if you want a strong-enough recursive curator without the full Pareto + specialist machinery.

---

### L39-5 — Specialist-curator creation pipeline

**Why now.** A single global curator can't handle every failure-class equally well. HORIZON-style failure-class attribution (v3.8 L38-9) detects recurrent classes; Vol. 3 Reframe 13 says: under recurrent failure-class pressure, *create a specialist curator*. SC-2 bounds the recursion (max depth 3, no same-class duplication).

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/curator/
  specialist.py            # NEW — specialist creation pipeline
                           # class SpecialistCreator:
                           #     def __init__(
                           #         self,
                           #         general_curator: Talent,
                           #         proposer: Proposer,
                           #         skill_builder: SkillBuilder,
                           #         failure_detector: FailureClassDetector,  # from v3.8 L38-9
                           #         max_depth: int = 3,
                           #     ) -> None
                           #     async def maybe_create_specialist(
                           #         self, recent_cycles: list[CuratorCycle]
                           #     ) -> Talent | None:
                           #         class_pressure = self.failure_detector.detect_recurrent(recent_cycles)
                           #         if not class_pressure:
                           #             return None
                           #         if self._depth_of(class_pressure) >= self.max_depth:
                           #             await self.bright_lines.trip("BL-VOL3-SPECIALIST-DEPTH")
                           #             return None
                           #         if self._existing_specialist_for(class_pressure):
                           #             await self.bright_lines.trip("BL-VOL3-SPECIALIST-DUPLICATE-CLASS")
                           #             return None
                           #         intervention = await self.proposer.propose(
                           #             failures=class_pressure.traces,
                           #             history=self.history,
                           #         )
                           #         specialist = await self.skill_builder.build(
                           #             parent=self.general_curator,
                           #             intervention=intervention,
                           #         )
                           #         specialist = specialist.with_kind("curator").with_parent(
                           #             self.general_curator.name
                           #         ).with_inherited_principles(self.general_curator.name)
                           #         specialist = specialist.with_trust_tier(TrustTier.T_UNTRUSTED)
                           #         await self._admit_to_catalog(specialist)
                           #         return specialist

  curator_graph.py         # NEW — DAG enforcement for curator inheritance
                           # class CuratorGraph:
                           #     def add_specialist(parent: str, specialist: str, class_id: str) -> None
                           #     def assert_dag(self) -> None  # raises BL-VOL3-CURATOR-GRAPH-CYCLE
                           #     def depth(specialist_name: str) -> int
                           #     def existing_specialist_for(class_id: str) -> Talent | None
                           # backed by the v3.8 SkillGraph (extends with edge_type="specialist_of")
```

**SC-2 enforcement:**

- **Depth bound.** Max specialist depth = 3 (general → domain → sub-domain). Beyond depth 3, the SpecialistCreator returns `None` and trips `BL-VOL3-SPECIALIST-DEPTH` for HITL review.
- **No same-class duplicate.** A specialist for class `time-series-forecast` cannot be created if one already exists; routes to existing instead.
- **DAG invariant.** Specialist graph stays acyclic; cycle detection on insertion.

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_specialist_creation.py  # 25+ tests
                               # - depth-3 creation succeeds; depth-4 trips bright line
                               # - duplicate-class trips bright line; routes to existing
                               # - parent inheritance: working_principles, trust ladder, kind
                               # - new specialist starts at T_UNTRUSTED
                               # - DAG cycle detection on planted cycle attempt
                               # - failure-class pressure with no recurrence: no specialist created
                               # - failure-class pressure with K=3 recurrence: specialist created
```

**Acceptance.**

- ✅ Failure-class pressure spawns a specialist within 1–7 cycles depending on class severity.
- ✅ No specialist exceeds depth 3.
- ✅ No two specialists for the same failure-class.
- ✅ Specialists inherit working principles from parent unless explicitly overridden.

**Effort.** ~2 weeks.

---

### L39-6 — Three-tier curator-bank: general / task-specific / common-mistakes

**Why now.** [170](docs/170-skillrl-recursive-skill-augmented-rl.md) SkillRL's three-tier hierarchy is well-validated; Vol. 3 Reframe 13 ports it to curator skills. The **common-mistakes** tier — failure lessons with avoidance strategies — is the negative-space that prevents the curator from repeating its own mistakes.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/curator/
  bank.py                  # NEW — three-tier curator bank
                           # @dataclass class CuratorBank:
                           #     general_curators: dict[str, Talent]      # apply across domains
                           #     task_specific_curators: dict[str, list[Talent]]  # per failure-class
                           #     common_mistakes: list[CommonMistake]     # negative-space memory
                           #
                           # @dataclass(frozen=True) class CommonMistake:
                           #     title: str
                           #     description: str
                           #     cause: str
                           #     avoidance: str
                           #     witnessed_at: datetime
                           #     witnessed_in: tuple[str, ...]   # witness IDs
                           #     class_id: str | None
                           #
                           # class CuratorBank:
                           #     async def add_mistake(self, m: CommonMistake) -> None
                           #     def retrieve_for(self, target_skill: Talent) -> list[CommonMistake]
                           #     async def consolidate_mistakes(self) -> None
                           #         """Merge near-duplicate mistakes; cap per-tier entries."""

packages/lyra-core/src/lyra_core/skills/curator/
  hr.py                    # NEW (will be extended in L39-8) — initial PIP / offboarding hooks
                           # class CuratorHR:
                           #     async def review(self, curator: Talent) -> ReviewVerdict
                           #     async def initiate_pip(self, curator: Talent) -> None
                           #     async def offboard(self, curator: Talent) -> None
```

**Common-mistakes tier integration:**

- After every curator cycle that fails (rollback, surrogate-reject, governed-validation-fail), the failure is converted to a `CommonMistake` and added to the bank.
- Before every new curator cycle, the curator retrieves relevant mistakes (filtered by current target skill's domain) and adds them to its context.
- A weekly consolidation pass merges similar mistakes (cosine ≥ 0.9 on description embedding) to prevent unbounded growth (`F-84` per Vol. 3).

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_bank.py             # 18 tests — three-tier storage; retrieve_for; consolidate_mistakes
                           # - per-tier max-entries cap (200 default)
                           # - retrieve_for filters by class_id
                           # - consolidate_mistakes merges semantic-near-duplicates
```

**Acceptance.**

- ✅ Common-mistakes tier persists across sessions.
- ✅ A planted-mistake (manually injected) is retrieved when its class_id matches a current cycle.
- ✅ Consolidation pass reduces 100 near-duplicates to ≤10 canonical entries.
- ✅ Bank-tier dominance prevented (per-tier cap fires when exceeded).

**Effort.** ~1.5 weeks.

---

### L39-7 — Pareto-frontier evolutionary search

**Why now.** Vol. 3 Reframe 15: maintain a frontier of `k=3` curator-strategy variants. Failure-driven proposals; round-robin parent selection; admit/evict; periodic skill-merge across independent runs. Lyra has the perfect substrate: `Arena` + `EloRating` for strategy scoring, v3.7 routines for the cron, worktrees for git-backed strategy isolation.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/curator/
  frontier.py              # NEW — Pareto-frontier evolutionary search
                           # @dataclass(frozen=True) class CuratorStrategy:
                           #     id: str
                           #     curator_talent_sha: str    # which curator-Talent version
                           #     scores: StrategyScores     # precision, recall, cost, transfer, surrogate-agreement
                           #     git_branch: str            # backed by a worktree branch
                           #     created_at: datetime
                           #
                           # @dataclass class StrategyScores:
                           #     precision: float
                           #     recall: float
                           #     cost_per_edit_usd: float
                           #     transfer_rate: float       # cross-class generalization
                           #     surrogate_agreement: float
                           #     def dominates(self, other: StrategyScores) -> bool: ...
                           #
                           # class ParetoFrontier:
                           #     def __init__(self, k: int = 3) -> None
                           #     async def evolve_generation(
                           #         self,
                           #         eval_set: CuratorEvalSet,
                           #         proposer: Proposer,
                           #         skill_builder: SkillBuilder,
                           #     ) -> None:
                           #         parent = self._round_robin_pick()
                           #         scores = await self._evaluate(parent, eval_set)
                           #         worst_failures = self._worst_failures(parent, eval_set)
                           #         intervention = await proposer.propose(worst_failures, self.history)
                           #         candidate = await skill_builder.build(parent.curator, intervention)
                           #         candidate_scores = await self._evaluate(candidate, eval_set)
                           #         if self._admits(candidate_scores):
                           #             self._admit(candidate)
                           #             if len(self.frontier) > self.k:
                           #                 self._evict_argmin()
                           #         self.history.append((intervention, candidate_scores))
                           #
                           #     def diversity_check(self) -> None:
                           #         """Trip BL-VOL3-FRONTIER-COLLAPSE if all strategies within Pareto-distance."""

  skill_merge.py           # NEW — cross-run skill-merge (the [168] final lift)
                           # class CrossRunMerger:
                           #     async def merge_independent_frontiers(
                           #         self, frontiers: list[ParetoFrontier]
                           #     ) -> Talent:
                           #         """Take unique strategies from each frontier; merge into superset Talent."""

packages/lyra-core/src/lyra_core/cron/routines/
  ralph_curator.py         # NEW — frontier evolution cron
                           # class RalphCuratorRoutine(Routine):
                           #     trigger = CronTrigger("0 */6 * * *")  # every 6 hours
                           #     async def run(self, ctx) -> None:
                           #         await ctx.frontier.evolve_generation(
                           #             eval_set=ctx.curator_eval_set,
                           #             proposer=ctx.proposer,
                           #             skill_builder=ctx.skill_builder,
                           #         )
                           #         ctx.frontier.diversity_check()
                           #         if ctx.now.weekday() == 6 and ctx.now.hour == 4:
                           #             # Sunday 4am: cross-run skill-merge
                           #             await ctx.cross_run_merger.merge_independent_frontiers(
                           #                 [ctx.frontier_a, ctx.frontier_b, ctx.frontier_c]
                           #             )

packages/lyra-cli/src/lyra_cli/commands/
  curator.py               # EXTEND
                           # lyra curator frontier list
                           # lyra curator frontier scores
                           # lyra curator frontier evolve         # one generation manually
                           # lyra curator merge                   # cross-run skill-merge
```

**Git-backed strategy versioning** (per [168] §4):

- Each `CuratorStrategy` is a git branch in `.lyra/curator/strategies/`.
- Frontier maintenance is `git branch <new>` not file-system copy.
- Rollback is `git reset` — one-line undo.
- `lyra curator frontier diff <strategy-a> <strategy-b>` shows the working-principles divergence.

**Worktree integration** (v3.7 L37-5):

- Each strategy evaluation runs in its own worktree to prevent cross-strategy contamination.
- Worktree allocation is automatic when `RalphCuratorRoutine.evolve_generation()` fires.

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_frontier.py         # 25+ tests
                           # - Pareto admission: dominated candidates rejected
                           # - round-robin parent selection
                           # - eviction: frontier never exceeds k=3
                           # - diversity gate: collapsed frontier trips BL-VOL3-FRONTIER-COLLAPSE
                           # - git-backed: each strategy is a real git branch
                           # - cross-run merge: 4 independent runs produce +5pp lift on synthetic bench

  test_skill_merge.py      # 8 tests — unique-strategy merge; superset Talent; lift validation
```

**Acceptance.**

- ✅ Frontier maintains k=3 strategies across 30+ generations without collapse.
- ✅ Pareto-distance diversity gate trips when frontier collapses; re-seeds from common-mistakes tier.
- ✅ Cross-run skill-merge across 4 independent runs produces +5pp lift over single-run best (matches [168]'s pattern directionally).
- ✅ `lyra curator frontier list` shows the k=3 strategies and scores.
- ✅ Each strategy is a real git branch; rollback works.

**Effort.** ~3 weeks.

---

### L39-8 — Seven formal correctness guarantees + curator HR lifecycle

**Why now.** Vol. 3 Reframe 11–13 + the seven guarantees from [191](docs/191-onemancompany-skills-to-talent.md) make the curator graph provably bounded-time, deadlock-free, idempotent under retries. Without this, F-86 (curator silent retirement) and F-87 (inheritance cycles) land in production. The HR lifecycle is the personnel side: review every N invocations → PIP after 3 fails → offboarding after 1 PIP fail.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/curator/
  hr.py                    # EXTEND from L39-6 stub
                           # class CuratorHR:
                           #     review_cadence_invocations: int = 30
                           #     review_cadence_days: int = 7
                           #     pip_threshold_consecutive_fails: int = 3
                           #     offboard_threshold_pip_fails: int = 1
                           #
                           #     async def review_cycle(self) -> None:
                           #         for curator in self.catalog.curators:
                           #             if self._should_review(curator):
                           #                 verdict = await self.review(curator)
                           #                 if verdict == ReviewVerdict.FAIL:
                           #                     curator.consecutive_fails += 1
                           #                 else:
                           #                     curator.consecutive_fails = 0
                           #                 if curator.consecutive_fails >= self.pip_threshold_consecutive_fails:
                           #                     await self.initiate_pip(curator)
                           #
                           #     async def offboard(self, curator: Talent) -> None:
                           #         if curator.name == "argus-curator-general":
                           #             await self.bright_lines.trip("BL-VOL3-RETIRE-GENERAL-CURATOR")
                           #             return
                           #         await self.catalog.remove(curator)

  guarantees.py            # NEW — seven formal guarantees as property-based test fixtures
                           # def assert_dag_invariant(graph: CuratorGraph) -> None:
                           #     """Curator graph is a DAG; cycle detection on every insert."""
                           #
                           # def assert_mutual_exclusion(scheduler: CuratorScheduler) -> None:
                           #     """At most one curator processes a given Talent at a time."""
                           #
                           # def assert_schedule_idempotency(scheduler: CuratorScheduler) -> None:
                           #     """Re-running an edit on a failed mid-commit produces no duplicate."""
                           #
                           # def assert_curation_loop_termination(engine: SelfCurationEngine) -> None:
                           #     """Per-cycle iteration bound N_max enforced."""
                           #
                           # def assert_cascade_completeness(catalog: Catalog) -> None:
                           #     """Rejected edits trigger complete re-curation."""
                           #
                           # def assert_dependency_completeness(catalog: Catalog) -> None:
                           #     """When parent's working_principles change, dependent specialists re-validate."""
                           #
                           # def assert_recovery_correctness(workflow: CuratorWorkflow) -> None:
                           #     """Mid-curation crash + restart produces identical result."""
```

**HR review cadence:**

- Default: every 30 invocations OR 7 days, whichever first.
- Per-curator override (some specialist curators may want tighter / looser cadences).
- 3 consecutive failed reviews → PIP (working-principles tightening, scope reduction, lower trust tier).
- 1 failed review under PIP → offboarding (deprovision, log gap, re-recruit if specialist; refuse if general).

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_guarantees.py       # 28 tests — 4 property-based per guarantee + edge cases
  test_hr.py               # 22 tests — review / PIP / offboarding lifecycle; refuse-general-retirement
```

**Acceptance.**

- ✅ All seven formal correctness guarantees verified by property-based tests (1000+ random walks per guarantee).
- ✅ HR review fires at expected cadence; PIP / offboarding lifecycle works end-to-end.
- ✅ Attempting to retire `argus-curator-general` trips `BL-VOL3-RETIRE-GENERAL-CURATOR`.
- ✅ Crash-recovery test: kill curator mid-edit, restart, verify identical post-restart state (uses v3.8 `Temporal`-equivalent durability via v3.7 routines).

**Effort.** ~2 weeks.

---

### L39-9 — Curator Talent Market federation

**Why now.** Lyra's catalog scanner already aggregates `awesome-list` sources (v3.8 L38-1's D4 capability). v3.9 extends this to a *curator marketplace*: community-contributed curator-Talents, AI-recommended-assembled curators for niche failure-classes, internal-promotion of top-performing curators back to the marketplace.

**Concrete deliverables.**

```text
packages/lyra-core/src/lyra_core/skills/curator/
  market.py                # NEW — curator-specific Talent Market integration
                           # class CuratorMarket:
                           #     async def list_available(
                           #         self, source: Literal["community", "ai-assembled", "internal"]
                           #     ) -> list[CuratorListing]
                           #     async def import_curator(
                           #         self, listing: CuratorListing
                           #     ) -> Talent:
                           #         """Validates against own benchmark before reaching T_SCANNED."""
                           #     async def publish_promoted_curator(
                           #         self, curator: Talent
                           #     ) -> None:
                           #         """Republish a top-performer's refined Talent to the marketplace."""
                           #
                           # community sources (default): GitHub awesome-lists matching agentskills.io format
                           # ai-assembled: scrape niche-domain web pages, generate candidate curator
                           # internal: top performers from this Lyra instance's frontier

packages/lyra-mcp/src/lyra_mcp/server/
  app.py                   # EXTEND — expose curator-market tools
                           # tools added:
                           # - argus.curator.list                  # all curators in catalog
                           # - argus.curator.market.list           # marketplace listings
                           # - argus.curator.market.import        # import a curator (HITL gate)
                           # - argus.curator.frontier.export      # export local frontier as a snapshot
                           # - argus.curator.replay <witness>     # bitemporal replay of curator decision

packages/lyra-cli/src/lyra_cli/commands/
  curator.py               # EXTEND
                           # lyra curator market list
                           # lyra curator market import <listing-id>
                           # lyra curator market publish <name>
                           # lyra curator replay <witness-id>
```

**Cross-run skill-merge across harnesses** (the multi-tenant analog of [168] skill-merge):

- Polaris frontier + Lyra frontier + (optionally) OpenClaw / Codex frontiers merge weekly.
- Unique strategies from each enter a candidate pool.
- Each candidate runs through Argus's standard import-validate-tier-activate pipeline.
- Survivors enter each harness's local frontier as exploration seeds.

**Tests.**

```text
packages/lyra-core/tests/skills/curator/
  test_market.py           # 18 tests
                           # - import: T_UNTRUSTED on first arrival
                           # - own-benchmark validation gate before T_SCANNED
                           # - planted-poison curator caught by vulnerability scanner
                           # - cross-harness merge: unique-strategy admission

packages/lyra-mcp/tests/
  test_curator_market_mcp.py  # 10 tests — MCP tool exposure
```

**Acceptance.**

- ✅ Importing a community curator runs through full vulnerability scan + own-benchmark before reaching T_SCANNED.
- ✅ Cross-harness skill-merge surfaces curators that improve at least one other harness's frontier.
- ✅ Talent Market entry / promotion / demotion lifecycle works end-to-end on a community curator.
- ✅ MCP tools `argus.curator.market.*` exposed and callable.

**Effort.** ~2 weeks.

---

## §3 — Phasing summary

| Phase | Title | Effort | Depends on | Stage |
|---|---|---|---|---|
| **L39-1** | Curator-as-Talent + cascade extension | ~1.5 wk | v3.8 L38-1, L38-4 | MVP |
| **L39-2** | Six component Talents | ~2 wk | L39-1 | MVP |
| **L39-3** | Self-curation invariant SC-1 | ~2 wk | L39-2 | MVP |
| **L39-4** | Information-isolated surrogate verifier | ~2 wk | L39-2 | MVP |
| **L39-5** | Specialist creation pipeline | ~2 wk | L39-2, v3.8 L38-9 | Stage 2 |
| **L39-6** | Three-tier curator-bank | ~1.5 wk | L39-2 | Stage 2 |
| **L39-7** | Pareto-frontier evolutionary search | ~3 wk | L39-2, v3.7 routines/worktrees | Stage 2 |
| **L39-8** | Seven formal guarantees + HR lifecycle | ~2 wk | All prior | Stage 3 |
| **L39-9** | Curator Talent Market federation | ~2 wk | All prior | Stage 3 |

**MVP (L39-1 → L39-4): ~7.5 weeks.** Self-curating curator with co-evolutionary verification — the load-bearing recursive piece. After this, Lyra has a curator stronger than any published 2026 design.

**Stage 2 (L39-5 + L39-6 + L39-7): ~6.5 weeks.** Specialist creation + three-tier bank + Pareto-frontier. Adds the recursive-evolution machinery.

**Stage 3 (L39-8 + L39-9): ~4 weeks.** Formal guarantees + HR lifecycle + Talent Market federation. Production hardening.

**Total: ~18 weeks** for full v3.9.

---

## §4 — Concrete file map

### What to add

```text
packages/lyra-core/src/lyra_core/skills/curator/         # NEW PACKAGE — L39-1 onwards
├── __init__.py
├── self.py                 # L39-3
├── eval_set.py             # L39-3
├── specialist.py           # L39-5
├── curator_graph.py        # L39-5
├── bank.py                 # L39-6
├── hr.py                   # L39-6 stub, L39-8 full
├── frontier.py             # L39-7
├── skill_merge.py          # L39-7
├── guarantees.py           # L39-8
├── market.py               # L39-9
└── components/             # L39-2
    ├── __init__.py
    ├── extractor.py
    ├── judge.py
    ├── merger.py
    ├── proposer.py
    ├── skill_builder.py
    └── surrogate_verifier.py

packages/lyra-core/src/lyra_core/skills/
  talent.py                 # EXTEND — kind, parent_curator, inherits_principles_from (L39-1)

packages/lyra-core/src/lyra_core/cron/routines/
├── ralph_curator.py        # NEW — L39-7
└── surrogate_recalibration.py  # NEW — L39-4

packages/lyra-skills/src/lyra_skills/
  argus_cascade.py          # EXTEND — kind filter (L39-1)

packages/lyra-mcp/src/lyra_mcp/server/
  app.py                    # EXTEND — argus.curator.* tools (L39-9)

packages/lyra-cli/src/lyra_cli/commands/
  curator.py                # NEW — L39-1, extended L39-7, L39-9

skills/                     # NEW directory entries
├── argus-curator-general/SKILL.md         # L39-1
├── argus-extractor/SKILL.md               # L39-2
├── argus-judge/SKILL.md                   # L39-2
├── argus-merger/SKILL.md                  # L39-2
├── argus-proposer/SKILL.md                # L39-2
├── argus-skill-builder/SKILL.md           # L39-2
└── argus-surrogate-verifier/SKILL.md      # L39-2
```

### What to extend (no breaking changes)

- `lyra-core/src/lyra_core/skills/talent.py` — add `kind`, `parent_curator`, `inherits_principles_from` fields (L39-1) with safe defaults.
- `lyra-skills/src/lyra_skills/argus_cascade.py` — add `kind` parameter to `find()` with default `"regular"` (L39-1) — no behaviour change for existing callers.
- `lyra-core/src/lyra_core/governance/witness.py` — extend witness schema to include `curator_id` and `edit_type` (L39-3). Existing witnesses remain valid (optional fields).
- `lyra-core/src/lyra_core/skills/graph.py` — add `edge_type="specialist_of"` to the curator inheritance edges (L39-5). Existing graph users unchanged.

### What to leave alone

- The four-mode taxonomy. v3.9 hooks orthogonally; no mode changes.
- `harness_core` agent loop. Curator runs as Talents inside the loop, not as a parallel daemon.
- Permission system. Curator edits gated by `BL-VOL3-*` codes, not by mode-permission state.
- Session HIR stream. v3.9 appends curator-edit witnesses, never rewrites HIR.
- v3.7 routines API. v3.9 *uses* the routine registry; v3.7 routines themselves don't change.
- v3.8 cascade tier signatures. v3.9 only adds a `kind` filter; no tier-internal changes.

---

## §5 — Testing strategy

Lyra TDD discipline applies. Per phase:

| Phase | Unit tests | Integration tests | Bench tests |
|---|---|---|---|
| L39-1 | Talent serialization with new fields; cascade kind-filter | curator-as-Talent end-to-end | none (mechanism-level) |
| L39-2 | Each component contract + default impl | Extractor → Judge → Merger pipeline | planted-extraction bench |
| L39-3 | SC-1 invariant clauses each property-based | self-curation cycle end-to-end | curator-edit-quality bench |
| L39-4 | Isolation enforcement; planted-bad / planted-good | SC-1 + surrogate end-to-end | independence + Brier calibration bench |
| L39-5 | Depth bound; duplicate-class detection; DAG cycle detection | failure-class → specialist creation end-to-end | specialist-emergence bench |
| L39-6 | Three-tier storage; consolidation pass; per-tier cap | bank retrieval drives curator context | none (mechanism-level) |
| L39-7 | Pareto admission; diversity gate; round-robin; git-backed | frontier evolution + cross-run merge end-to-end | +5pp skill-merge lift bench |
| L39-8 | Property-based per guarantee; HR cadence | seven-guarantee end-to-end + HR lifecycle | crash-recovery bench |
| L39-9 | Marketplace import gates; vulnerability scan; cross-harness | community curator import + promotion end-to-end | none (mechanism-level) |

The parity bench in `lyra-evals/` runs all phases together at the end of each PR.

---

## §6 — Open questions (decide before L39-1 begins)

1. **Surrogate model family.** Default different family from host (e.g., Qwen / DeepSeek if host is Claude). **Recommended:** Qwen 3 Max for surrogate when host is Claude Sonnet/Opus; DeepSeek R1 fallback.
2. **Frontier size k.** 3 (default per [168]), 5 (more diverse, slower), 7 (HeavySkill-style breadth). **Recommended:** k=3 for v3.9.0; configurable per harness.
3. **Specialist depth ceiling.** 3 (default, conservative), 4 (more granular), 2 (only general → domain). **Recommended:** 3.
4. **Curator-evaluation set source.** Synthetic (cheap), held-out human-annotated (gold), witness-replay (fresh). **Recommended:** stratified mix (60% synthetic + 40% witness).
5. **Curator-graph store.** Same SQLite as v3.8 `BitemporalCatalog` (recommended), separate JSONL ledger, external graph DB. **Recommended:** same SQLite, new `curator_graph` table.
6. **Skill-merge cadence.** Weekly cross-harness (recommended), nightly within-harness only, monthly maximalist. **Recommended:** weekly Sunday 4am cron.
7. **HR review cadence.** Every 30 invocations or 7 days, per-curator override allowed. **Recommended:** match [191] §3.5 default.
8. **Periodic-decoupled training (Vol. 1 R5).** v3.8 deferred this to v3.9 RL phase. v3.9 keeps it deferred (frozen-weights only). **Confirmed.**
9. **L3 evolver autonomy.** Fully autonomous in T_UNTRUSTED / T_SCANNED tiers; HITL-gated for T_REVIEWED / T_PINNED promotions. **Recommended:** match Vol. 1 §10 Q15.

---

## §7 — First-PR scope (smallest commit that ships value)

The first v3.9 PR ships **only L39-1 (curator-as-Talent + cascade extension)** with no other v3.9 changes:

```text
PR #1 — Lyra v3.9.0 Curator-as-Talent
├── packages/lyra-core/src/lyra_core/skills/talent.py            (extend: kind, parent_curator, inherits_principles_from)
├── packages/lyra-core/tests/skills/test_talent_curator_kind.py  (new, 8+ tests)
├── packages/lyra-skills/src/lyra_skills/argus_cascade.py        (extend: kind filter)
├── packages/lyra-skills/tests/test_argus_cascade_curator.py     (new, 12+ tests)
├── packages/lyra-cli/src/lyra_cli/commands/curator.py           (new, status/list/show/route)
├── packages/lyra-cli/tests/test_cli_curator.py                  (new, 6+ tests)
├── skills/argus-curator-general/SKILL.md                        (new, canonical general curator)
└── CHANGELOG.md                                                 (v3.9.0 entry)
```

**Acceptance for PR #1.**

- ✅ `lyra curator list` returns `argus-curator-general` after install.
- ✅ `lyra skill route --kind=curator "..."` only returns curator-Talents.
- ✅ Existing `ArgusCascade.find()` behaviour unchanged for `kind="regular"` (regression bench passes).
- ✅ All v3.8 tests pass.
- ✅ +26 new tests pass.

The PR is small (~700 LOC including tests) and demonstrates the *shape* of the recursive-curator architecture without requiring any v3.9 dependencies to land first. Subsequent PRs ship L39-2 (six component Talents), then L39-3 (self-curation invariant), then L39-4 (surrogate verifier).

---

## §8 — One-paragraph summary

Lyra v3.9 folds Argus Omega Vol. 3 ([`docs/197-argus-omega-vol-3-recursive-skills-curator.md`](docs/197-argus-omega-vol-3-recursive-skills-curator.md)) into the existing harness without breaking v3.8 primitives. The five Vol. 3 reframes map onto nine phases L39-1 through L39-9: **L39-1** promotes the curator from a daemon to a routable Talent (`argus-curator-general` SKILL.md + `kind: curator` cascade extension); **L39-2** factors the curator into six independently-testable component Talents (Extractor / Judge / Merger / Proposer / Skill-Builder / Surrogate-Verifier) drawn from [167] AutoSkill, [168] EvoSkill, [169] CoEvoSkills, [170] SkillRL; **L39-3** enforces self-curation invariant SC-1 (monotone non-degradation + bounded iteration + fixed-point detection + governed validation + HITL gate at trust-tier boundaries); **L39-4** ships the information-isolated surrogate verifier (different LLM family, no shared context, weekly Brier calibration — the [169] +30pp ablation directly captured); **L39-5** adds specialist-curator creation under recurrent failure-class pressure (HORIZON-class detector → Proposer → Skill-Builder → new specialist Talent at T_UNTRUSTED), bounded by SC-2 (max depth 3, no same-class duplicate); **L39-6** organizes the curator catalog into the three-tier bank (general / task-specific / common-mistakes); **L39-7** maintains a Pareto frontier of k=3 curator strategies via evolutionary search with round-robin parents, failure-driven proposals, git-backed strategy versioning (per-strategy worktrees from v3.7), and weekly cross-run skill-merge; **L39-8** ports the seven formal correctness guarantees from [191] OneManCompany to the curation graph (DAG invariant, mutual exclusion, schedule idempotency, curation-loop termination, cascade completeness, dependency completeness, recovery correctness) plus HR review/PIP/offboarding for curators; **L39-9** federates a curator Talent Market with community + AI-assembled + internal-promotion sources and exposes curator inspection/replay/market over MCP. **MVP (L39-1 → L39-4) lands in ~7.5 weeks** and gives Lyra a self-curating curator with co-evolutionary verification that is, by itself, stronger than any published 2026 curator design. **Full v3.9 lands in ~18 weeks**. **First PR is L39-1 only** — ~700 LOC, ~26 new tests, zero regressions, smallest commit that demonstrates the architecture without dependencies. The whole v3.9 plan is purely additive: existing `SkillRouter`, `ArgusCascade`, `Talent`, `WitnessLattice`, v3.7 routines/worktrees all continue working unchanged; v3.9 only *adds*.

---

## §9 — Decision points

Three decisions before L39-1 begins:

1. **Approve the nine phases** (L39-1 through L39-9) and the additive-only constraint. Trim if too ambitious; expand if anything's missing.
2. **Pick MVP scope** — L39-1 only (~1.5 wk), L39-1+L39-2 (~3.5 wk), L39-1+L39-2+L39-3 (~5.5 wk), or full MVP L39-1 → L39-4 (~7.5 wk).
3. **Approve the open-question defaults** in §6 — surrogate Qwen-3-Max (different family from Claude host), frontier k=3, specialist depth 3, eval-set 60% synthetic + 40% witness, curator-graph SQLite, weekly skill-merge.

When ready, say "go L39" or specify which phases to start with.

---

## §10 — References

**Argus design canon** (in `harness-engineering/docs/`):

- [180 — Argus v1.0 design](docs/180-argus-skill-router-agent-design.md)
- [194 — Argus Omega Vol. 1](docs/194-argus-omega-enhanced-design.md)
- [195 — Argus Omega Vol. 2](docs/195-argus-omega-vol-2-trajectory-temporal-horizon.md)
- [196 — Argus vs the field comparison](docs/196-argus-vs-field-skill-loading-comparison.md)
- [197 — Argus Omega Vol. 3 Recursive Skills Curator](docs/197-argus-omega-vol-3-recursive-skills-curator.md) ← v3.9 source

**Source corpus** for the curator reframes:

- [167 — AutoSkill](docs/167-autoskill-experience-driven-lifelong-learning.md) — Extractor → Judge → Merger
- [168 — EvoSkill](docs/168-evoskill-coding-agent-skill-discovery.md) — Pareto-frontier; Proposer → Skill-Builder
- [169 — CoEvoSkills](docs/169-coevoskills-co-evolutionary-verification.md) — surrogate verifier; +30pp ablation
- [170 — SkillRL](docs/170-skillrl-recursive-skill-augmented-rl.md) — three-tier hierarchy + common-mistakes
- [171 — Skill self-evolution synthesis](docs/171-skill-self-evolution-2026-synthesis.md) — the four-corner landscape
- [191 — OneManCompany](docs/191-onemancompany-skills-to-talent.md) — Talent / Container split + 7 guarantees
- [27 — HORIZON](docs/27-horizon-long-horizon-degradation.md) — failure-class attribution
- [55 — Hermes Agent](docs/55-hermes-agent-self-improving.md) — continual extraction discipline

**Lyra adjacent plans:**

- [LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md](LYRA_V3_7_CLAUDE_CODE_PARITY_PLAN.md) — routines (L37-8) + worktrees (L37-5) + auto-mode (L37-4) substrate
- [LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md](LYRA_V3_8_ARGUS_INTEGRATION_PLAN.md) — cascade (L38-1) + telemetry (L38-2) + trust + witness (L38-3) + Talent (L38-4) + skill-graph (L38-5) + SkillPlan (L38-6) + simulator (L38-7) + federation (L38-8) + Ralph + chaos + bitemporal (L38-9) substrate
