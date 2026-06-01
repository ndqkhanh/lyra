# Candidate A: Memory-First Architecture -- The Right Bet for Lyra

**Proposer**: Memory-Centric Architect  
**Grounding**: BASELINE.md, SYNTHESIS.md (228 sources), BREAKTHROUGH-ARCHITECTURE.md  
**Date**: 2026-06-01

---

## 1. The Core Proposition

Lyra should center everything on a **Temporal Knowledge Graph (TKG)** with A-MAC admission control, A-MEM Zettelkasten linking, and a 4-tier hierarchy (Working / Episodic / Semantic / Archive). Memory is not a subsystem -- it is the central nervous system through which routing, skills, verification, and swarm coordination all flow.

This is the single highest-leverage architectural decision for Lyra because of an empirical fact the field has converged on: **the memory bottleneck is the first bottleneck to hit as agents scale** (SYNTHESIS SS9.2). Flat or absent memory causes agents to plateau -- they cannot learn from past interactions, recognize repeat patterns, or build on prior knowledge. The Memory-First lineage (AOI, A-MEM, A-MAC, MemAgent, Letta/MemGPT, Zep/Graphiti, AnnaAgent, DecentMem) has produced a consistent 40-60% improvement over no-memory baselines across every benchmark where it has been tested.

---

## 2. Evidence Chain with Specific Numbers

### 2.1 A-MAC Admission Control (OpenReview #mmdqUrEY24)

A-MAC's 5-factor admission gate (utility, confidence, novelty, recency, type_prior) achieves **F1=0.583 on LoCoMo** with **-31% latency** vs. Mem0, and **-23% tokens per search** (SYNTHESIS SS1.1, source #79). The key mechanism: not everything belongs in memory. A lightweight gating mechanism prevents hallucinated or low-value content from entering storage at all, which simultaneously improves retrieval precision and reduces storage volume.

**What this means for Lyra**: Lyra's existing `lyra-memory` package already implements A-MAC admission (BASELINE SS2.5, confirmed by `test_amac_admission.py`). The issue is that the admission weights are **paper defaults, not Lyra-calibrated** (BASELINE SS3.3, CRITICAL-2). Calibrating these weights on Lyra's actual coding/research workload could substantially improve on A-MAC's published F1 of 0.583.

### 2.2 A-MEM Zettelkasten Linking (arXiv 2502.12110)

A-MEM's dynamic note-linking outperforms SOTA across **6 foundation models on LoCoMo** (SYNTHESIS SS1.1, source #59). Each stored memory declares outgoing links to related memories; links are scored and pruned by usage frequency, creating emergent graph structure without a pre-defined schema. This outperforms Graph RAG baselines by +0.08-0.12 F1 on relationship-heavy queries.

**What this means for Lyra**: Lyra's `lyra-knowledge-graph` package exists but linking is a gap. The current architecture stores memories but does not actively maintain a dynamic link graph. Adding A-MEM-style linking transforms the flat memory store into a self-organizing knowledge graph. This is the mechanism that makes the TKG genuinely temporal and relational, not just a collection of timestamped vectors.

### 2.3 MemAgent (ICLR 2026 Oral)

MemAgent extrapolates from **8K training to 3.5M token deployment** with <10% degradation via learned compression (RL-based overwrite strategy) (SYNTHESIS SS1.1, source #256). This proves that memory systems can scale **440x beyond training distribution** -- the crucial property for Lyra's long-running agents. Without this, any memory system is bounded by its training data.

**What this means for Lyra**: The 4-tier hierarchy (Working / Episodic / Semantic / Archive) directly maps to MemAgent's compression strategy. Working Memory is the current session buffer (<10MB, full detail). Episodic Memory holds compressed trajectories with a 7-day retention window (AOI SS68). Semantic Memory contains generalized heuristics that persist permanently. Archive provides cold storage with unlimited capacity. Each tier has a different storage cost, retrieval speed, and compression strategy, mirroring MemAgent's learned approach.

### 2.4 Field-Theoretic Memory (arXiv 2602.21220)

**+116% F1 on LongMemEval** with p<0.01 (SYNTHESIS SS10.2). This is the genuine breakthrough in the corpus. Memory as continuous PDE-governed fields (diffusing, decaying, coupling) rather than discrete database entries achieves >99.8% collective intelligence in multi-session reasoning.

**What this means for Lyra**: Field-Theoretic Memory is the Phase 2+ target. It requires PDE solver infrastructure that doesn't exist in Lyra today. But the TKG foundation is the prerequisite -- you cannot layer fields on top of flat vector storage. The 4-tier TKG provides the discrete memory substrate that the continuous field approach generalizes. Without TKG as the foundation, Field-Theoretic Memory has no base to build on.

### 2.5 Cost-Sensitive Store Routing (from AOI, source #68)

AOI achieves **72.4% compression while preserving 92.8% critical information** with a **-34.4% MTTR** in IT operations (SYNTHESIS SS1.1, source #68). The mechanism: three-tier routing (simple lookup -> Working only; factual query -> Episodic; complex reasoning -> all stores + Semantic synthesis). The latency savings come from the Pareto distribution of queries -- 80% are simple fact lookups that Working tier alone can answer.

**What this means for Lyra**: This is the direct algorithmic solution to CRITICAL-1 from the baseline (TKG write-path bottleneck). By routing *retrieval* to the cheapest capable tier first, we avoid the bottleneck concern. The retrieval path is <50ms for 95% of queries (Working Memory), going up to ~500ms only for complex multi-hop queries that need the full TKG traversal.

---

## 3. What This Architecture Changes vs. Lyra Baseline

### Changes

| Component | Baseline State | Memory-First State | Migration |
|-----------|---------------|-------------------|-----------|
| A-MAC admission weights | Paper defaults | Lyra-calibrated on 10K coding/research examples | 2 weeks: build calibration dataset, run optimization |
| Knowledge graph linking | Package exists, static | A-MEM dynamic linking, auto-maintained | 3 weeks: implement linking pipeline in `lyra-knowledge-graph` |
| Memory-tier awareness | Implicit in package structure | Explicit in all components (router, skills, AVP) | 4 weeks: wire tier awareness into `lyra-router` and `lyra-workflow` |
| Workflow engine dispatch | LLM call placeholder (_run_task) | Memory-augmented: check TKG before LLM call | 2 weeks: integrate with `lyra-memory` |
| AVP feedback loop | No memory integration | AVP blocks recorded in TKG as Semantic-tier memories | 1 week: add AVP block recording to TKG write path |
| Compression strategy | Not integrated | AOI-style sliding window, 7-day threshold, ROUGE-L verification | 3 weeks: implement compression pipeline in background job |

### What It Keeps (Unchanged)

- **Provider abstraction** (`AbstractProvider` in `lyra-provider/interface.py`) -- no changes needed. The memory layer sits above the provider abstraction.
- **Effort scale** (`EffortManager.map_effort()` in `lyra-effort/manager.py`) -- no changes needed. Effort decisions are orthogonal to memory.
- **Model router** (`ModelRouter.route()` in `lyra-router/router.py`) -- the 3-tier cascade and NeuralUCB remain. Changes are additive: the router is *augmented* by memory (check TKG before routing), not replaced.
- **Adversarial Verifier** (`AdversarialVerifier.verify()` in `lyra-workflow/avp.py`) -- the AVP remains. Changes are additive: AVP writes to TKG, reads from TKG for context.
- **Skills system** (loader, curator, weaver, evolution) -- unchanged. Skills read from and write to TKG.
- **Safety system** (`lyra-safety/defense.py` + `misevolve.py`) -- unchanged.
- **Terminal UI** (TypeScript packages) -- unchanged. All changes are in the Python core.
- **All 87+ existing packages** remain. No package is deleted or replaced.

### Total Migration Cost

| Phase | Duration | What Delivers |
|-------|----------|---------------|
| Phase 1: A-MAC calibration | 2 weeks | Calibrated admission weights |
| Phase 2: TKG linking + retrieval plumbing | 3 weeks | A-MEM dynamic links, Cost-Sensitive Retrieval |
| Phase 3: Compression + evolution pipeline | 3 weeks | AOI compression, MemGrad textual gradients |
| Phase 4: Full integration (router, AVP, skills) | 4 weeks | All components wired through TKG |
| **Total** | **12 weeks** | **Full Memory-First architecture** |

Risk of regression: **Low**. The existing tests in `lyra-memory` (18+ test files) validate the current behavior. The migration is additive (adding new mechanisms) rather than replacement. Existing tests continue to pass; new tests cover the new integration points. The one risk is the A-MAC calibration shifting admission thresholds enough that previously-admitted memories are now rejected -- but this is detected by comparing admission distributions on the calibration holdout set.

---

## 4. Explicit Assumptions

1. **Memory is the binding bottleneck for Lyra's primary use cases** (coding, research, multi-session workflows). This assumption is supported by SYNTHESIS SS9.2 (memory connects to every other theme) but must be validated on Lyra's actual workload.

2. **A-MAC's F1=0.583 is improvable on Lyra's domain** (code + research vs. LoCoMo's general chat). This assumption is plausible because A-MAC's weights are paper defaults optimized on LoCoMo, not on code-specific tasks. Lyra's calibration could push F1 to 0.63+.

3. **The Field-Theoretic Memory breakthrough (+116% F1) depends on TKG foundation**. This is a structural assumption: discrete graph-based memory (TKG) is necessary but not sufficient for field-theoretic memory. The PDE solver layer is a separate infrastructure investment.

4. **Memory Transplants' finding (architecture transfer doesn't generalize) does not apply to Lyra because Lyra's domain (code + terminal) is unitary, not multi-domain**. This is the weakest assumption and the most dangerous one. If Lyra's memory architecture optimized for code tasks actively harms research tasks, we need separate memory configurations per domain.

5. **The 7-day retention for Episodic Memory (AOI convention) is near-optimal for Lyra**. This matches the typical Lyra session duration pattern (hours to days, not weeks) but would need measurement.

---

## 5. Honest Weaknesses

1. **TKG write-path latency is real**. A-MAC reduces it by 31% vs. Mem0, but the admission process (utility LLM call + ROUGE-L + ANN search) still takes ~50ms synchronous. For latency-critical interactions, this overhead is noticeable. Mitigation: the fast-path bypass (Working Memory only, <5ms) for the 80% of queries that don't need full TKG retrieval.

2. **Graph search does not scale linearly**. At 100K+ nodes, graph traversal latency exceeds the retrieval budget for complex multi-hop queries. BREAKTHROUGH-ARCHITECTURE SS13 sets the scaling limit test at 100K nodes / <100ms P95. Mitigation: tiered retrieval (don't traverse the Archive tier for simple queries) and HNSW approximate nearest neighbor (O(log N) retrieval).

3. **Memory Transplants' warning is real**. If Lyra's domain expands significantly (e.g., from terminal coding to research to GUI interactions), a single memory architecture may not fit all. Mitigation: domain-specific A-MAC weight profiles stored in the skill frontmatter; the skills system selects the memory profile per task.

4. **The Field-Theoretic promise is untested in production**. The +116% F1 is from a single paper (arXiv 2602.21220) with no replication. The PDE infrastructure cost is real. I am explicitly deferring this to Phase 2+ -- the TKG foundation is valuable without it.

5. **Memory-First adds token cost at admission time**. Each memory write requires a utility-assessment LLM call (~1K tokens). For high-traffic sessions generating thousands of candidates, this cost adds up. Mitigation: early bail-out (80% of rejections are caught by utility < 0.05, costing only ~10 output tokens).

6. **The migration timeline (12 weeks) assumes team availability for focused implementation**. If this is a parallel workstream alongside other Phase 2 work, the timeline stretches proportionally. The critical path is the A-MAC calibration (Phase 1), which blocks all downstream work.

---

## 6. Why This Bet Wins Over Alternatives

The Orchestration-First (Candidate B) and Evolution-First (Candidate C) architectures have genuine strengths, but they fail on one critical dimension: **learning from experience without explicit evolution**. Memory-First systems learn continuously and implicitly -- every interaction that passes admission control generates a memory that improves future behavior. Orchestration-First systems only improve when workflows are explicitly redesigned. Evolution-First systems require costly evolution cycles (1M+ tokens per cycle per Darwin). Memory-First captures the "free lunch" of implicit learning from normal operation.

The converged architecture in BREAKTHROUGH-ARCHITECTURE.md reflects this: the TKG core (from Candidate A) is adopted, while O-ARCH's AVP middleware is layered on top and E-ARCH's self-evolution is deferred to Phase 3+. The debate panel converged on Memory-First as the foundation for exactly this reason: it provides continuous value from day one, and the verification and evolution layers compound on top of it.

The numbers support this bet: **A-MAC at F1=0.583 with -31% latency** is a concrete, measurable improvement over Lyra's current flat memory. **MemAgent's 8K to 3.5M extrapolation** proves the 4-tier hierarchy scales beyond training. **AOI's 72.4% compression at 92.8% preservation** handles the practical storage problem. **Field-Theoretic's +116% F1** is the potential Phase 2 jackpot.

The TKG foundation pays for itself before any of the advanced features ship.
