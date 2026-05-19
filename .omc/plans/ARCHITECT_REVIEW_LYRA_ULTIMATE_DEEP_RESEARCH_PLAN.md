# Architect Review: Lyra Ultimate Deep Research Plan

**Date:** 2026-05-18  
**Reviewer:** Architect Agent  
**Plan:** LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md  
**Verdict:** ITERATE

---

## Summary

The plan proposes a **multi-agent orchestration architecture** with 6 specialized components (orchestrator, discovery agents, analysis agents, synthesis agents, assurance layer, persistent memory) to transform Lyra into a scalable deep research system. The architecture targets 70-80% context reduction, 3-5x speedup, and 95%+ verification rate through parallel execution, agent isolation, and adversarial review.

**Verdict: ITERATE** — The architecture is fundamentally sound but requires refinement in 3 critical areas.

---

## Architectural Strengths

### 1. Multi-Agent Decomposition (Lines 308-340)

The 6-component architecture cleanly separates concerns:
- **Discovery agents** (parallel) — source-specific isolation prevents cross-contamination
- **Analysis agents** (parallel) — batching by source type is efficient
- **Synthesis agents** (sequential) — correct ordering (taxonomy → contradictions → evidence → falsification)
- **Assurance layer** (adversarial) — heterogeneous model review addresses single-model blind spots
- **Persistent memory** — 4 specialized stores (Zettelkasten, DCI, ReasoningBank, Memento) provide structured knowledge accumulation

### 2. Context Optimization Strategy (Lines 527-699)

The 4-strategy approach is well-grounded:
- **External storage** (SQLite FTS5 + embeddings) — hybrid retrieval is industry standard
- **Selective retrieval** — phase-specific context loading (summaries → abstracts → findings) is pragmatic
- **Compression** (LLMLingua + prompt caching) — 70% compression ratio is realistic
- **Agent isolation** — independent context budgets prevent quadratic blowup

The math checks out: 110x attention cost reduction (10B → 90M operations) is achievable with 10 agents × 3KB context vs. monolithic 100KB.

### 3. Task Graph Execution (Lines 702-899)

Dynamic task decomposition with adaptive refinement is sound:
- Dependency tracking prevents premature execution
- Complexity-based routing (Haiku/Sonnet/Opus) optimizes cost
- Progress checkpointing every 10 minutes enables resumption
- Adaptive graph modification (lines 806-849) handles discovery failures and contradiction-driven deep dives

### 4. Quality Assurance (Lines 469-498, 1052-1248)

3-stage evidence-claim audit + 5-pass editing + adversarial review is comprehensive. The composite quality score (lines 1199-1226) weights verification rate (25%), citation accuracy (20%), and completeness (15%) appropriately.

---

## Critical Concerns

### CONCERN 1: Agent Coordination Overhead (CRITICAL)

**Issue:** The plan underestimates coordination complexity for 10+ agents with dynamic task graphs.

**Evidence:**
- Lines 356-377: `ResearchOrchestrator.research()` shows sequential phases (decompose → execute → synthesize → review → report), but lines 397-404 and 421-436 show parallel execution within phases. The orchestrator must handle:
  - Dependency resolution across 20+ tasks (4 discovery + 5 analysis + 4 synthesis + 1 report + 1 review)
  - Failure propagation (if ArXiv discovery fails, does paper analysis wait or proceed with partial data?)
  - Context budget enforcement across concurrent agents (lines 360, 662-686)
  - Result serialization to shared SQLite (lines 408-410) — concurrent writes risk lock contention

**Missing:**
- No specification for **task retry policy** (exponential backoff mentioned for APIs at line 938, but not for agent failures)
- No **circuit breaker** for cascading failures (if 3/4 discovery agents fail, should synthesis proceed?)
- No **timeout hierarchy** (line 1262 mentions 5-minute task timeout, but what about phase-level timeouts?)

**Impact:** Without robust coordination primitives, the system risks deadlocks (circular dependencies), race conditions (concurrent SQLite writes), or silent failures (missing results not detected).

**Recommendation:**
1. Add explicit **task state machine** (pending → running → completed/failed/timeout)
2. Implement **failure isolation** — synthesis proceeds with partial results if ≥50% of discovery succeeds
3. Use **connection pooling** for SQLite (lines 1364-1370 mention this for corruption mitigation, but not for concurrency)
4. Add **orchestrator health checks** — if any agent hangs for >5 minutes, kill and retry once

### CONCERN 2: Memory Store Scalability (HIGH)

**Issue:** The plan assumes SQLite + local embeddings scale to 100+ sources, but provides no capacity analysis.

**Evidence:**
- Lines 499-525: `MemoryManager` uses 4 SQLite databases (Zettelkasten, DCI, ReasoningBank, Memento) + embedding store (Chroma/FAISS)
- Lines 1329-1341: Risk 6 acknowledges embedding storage cost but dismisses it as "LOW" with mitigation "only embed abstracts"
- Lines 1361-1371: Risk 8 mentions SQLite corruption with WAL mode mitigation

**Missing:**
- No **capacity bounds**: How many sources can SQLite FTS5 handle before query latency degrades? (Typical limit: 1M documents, but with 2KB abstracts = 2GB, which exceeds practical SQLite size for fast queries)
- No **embedding dimensionality analysis**: BGE-small (384 dims) × 1000 sources × 4 bytes = 1.5MB (manageable), but 10K sources = 15MB (still OK). However, lines 519-524 show **reranking over 2k candidates** (k×2 for both FTS and semantic), which requires loading 2k embeddings into memory — at 10K sources, this becomes 4k embeddings = 6MB per query (acceptable, but not analyzed).
- No **memory compaction strategy**: Lines 499-525 show retrieval but no pruning. After 100 research sessions, Zettelkasten could have 10K notes. How is relevance decay handled?

**Impact:** Without capacity planning, the system may degrade gracefully at first (slower queries) but hit hard limits (SQLite lock timeouts, OOM on embedding load) at scale.

**Recommendation:**
1. Add **capacity targets** to ADR (lines 1373-1479): "Support 10K sources, 100K notes, 1K sessions before requiring compaction"
2. Implement **memory compaction** (mentioned at line 1279 but not specified): Archive notes older than 90 days, deduplicate embeddings with cosine similarity >0.95
3. Add **query latency SLOs**: FTS5 search <100ms, embedding search <200ms, reranking <500ms. If exceeded, trigger compaction or switch to approximate search (FAISS IVF).

### CONCERN 3: Adversarial Review Integration (MEDIUM)

**Issue:** The plan specifies adversarial review architecture (lines 469-498) but doesn't clarify **when** and **how** the reviewer model is invoked.

**Evidence:**
- Lines 472-473: `executor_model` (Claude Opus 4.7) vs. `reviewer_model` (GPT-4o)
- Lines 475-489: 3-stage audit (citations, claims, logic) + 5-pass editing
- Lines 1298-1310: Risk 4 acknowledges 2x cost, proposes mitigation "only review final report" and "make optional for deep research"

**Missing:**
- No **reviewer invocation protocol**: Does the reviewer see the full report + all sources (context bloat!), or just report + source IDs with on-demand retrieval?
- No **disagreement resolution**: If executor claims "Model X achieves 95% accuracy" and reviewer flags "citation doesn't support 95%, only 93%", who wins? (Lines 484-489 show `ReviewResult.passed` but no conflict resolution)
- No **cost-benefit analysis**: If adversarial review adds 2x cost but only catches 5% of errors (vs. 95% verification rate without it), is it worth it?

**Impact:** Without clear integration, adversarial review risks becoming a **bolt-on** that either (a) duplicates context (reviewer loads all sources → negates context optimization), or (b) operates blind (reviewer only sees report → misses nuanced citation errors).

**Recommendation:**
1. Specify **reviewer context budget**: Reviewer gets report (5KB) + top-10 cited sources (20KB) + claim-to-source mapping (5KB) = 30KB max
2. Add **disagreement protocol**: If reviewer flags claim, executor must either (a) provide additional citation, (b) soften claim ("may achieve" vs. "achieves"), or (c) remove claim. No silent overrides.
3. Implement **selective review** (mentioned at line 1308): Only review claims with confidence <0.8 (based on citation strength, source quality, claim specificity). This reduces review cost by ~60% while catching high-risk errors.

---

## Root Cause

The plan prioritizes **breadth** (6 components, 4 context strategies, 10+ agents) over **depth** (coordination primitives, capacity bounds, integration protocols). This is a common failure mode in multi-agent system design: the architecture looks elegant on paper but lacks the **operational rigor** needed for production deployment.

Specific gaps:
1. **Coordination**: Task graph is specified (lines 709-761) but failure handling is not
2. **Scalability**: Context optimization math is sound (lines 687-699) but memory store capacity is assumed, not proven
3. **Integration**: Adversarial review is architecturally clean (lines 469-498) but operationally vague (context budget, disagreement resolution)

---

## Recommendations

### 1. Add Coordination Primitives (HIGH PRIORITY, 1 week)

**What:** Extend `TaskGraph` (lines 709-761) with failure handling and timeout policies.

**How:**
```python
class Task:
    status: Literal["pending", "running", "completed", "failed", "timeout"]
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: int = 300  # 5 minutes
    
class TaskGraph:
    def execute_with_resilience(self, task: Task) -> Result:
        for attempt in range(task.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    task.execute(), 
                    timeout=task.timeout_seconds
                )
                return result
            except asyncio.TimeoutError:
                task.status = "timeout"
                if attempt < task.max_retries:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff
                else:
                    raise
            except Exception as e:
                task.status = "failed"
                if attempt < task.max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    # Partial failure: continue if ≥50% of phase tasks succeeded
                    if self.phase_success_rate(task.phase) >= 0.5:
                        return PartialResult(error=e)
                    raise
```

**Impact:** Prevents cascading failures, enables graceful degradation.

**Effort:** Medium (3-4 days implementation + tests)

### 2. Add Memory Capacity Bounds (HIGH PRIORITY, 3 days)

**What:** Specify capacity targets and implement compaction.

**How:**
- Add to ADR (lines 1373-1479):
  ```
  Capacity Targets:
  - Zettelkasten: 100K notes (10MB SQLite)
  - DCI Corpus: 10K sources (2GB full-text)
  - Embeddings: 10K vectors × 384 dims = 15MB
  - Query latency SLOs: FTS5 <100ms, embeddings <200ms
  ```
- Implement compaction (lines 1279):
  ```python
  class MemoryCompactor:
      def compact(self, age_days: int = 90):
          # Archive old notes
          self.zettelkasten.archive_older_than(age_days)
          # Deduplicate embeddings
          self.embeddings.deduplicate(threshold=0.95)
          # Vacuum SQLite
          self.corpus.vacuum()
  ```

**Impact:** Prevents unbounded growth, maintains query performance.

**Effort:** Low (2-3 days implementation + tests)

### 3. Specify Adversarial Review Protocol (MEDIUM PRIORITY, 2 days)

**What:** Define reviewer context budget and disagreement resolution.

**How:**
- Add to lines 469-498:
  ```python
  class AdversarialReviewer:
      def review(self, report: ResearchReport, sources: List[ResearchSource]) -> ReviewResult:
          # Reviewer context budget: 30KB max
          cited_sources = self.extract_cited_sources(report, sources)[:10]
          claim_map = self.build_claim_to_source_map(report, cited_sources)
          
          # Selective review: only claims with confidence <0.8
          low_confidence_claims = [c for c in report.claims if c.confidence < 0.8]
          
          issues = []
          for claim in low_confidence_claims:
              issue = self.reviewer_model.verify_claim(claim, claim_map)
              if issue:
                  # Disagreement resolution: executor must fix
                  fixed_claim = self.executor_model.resolve_issue(claim, issue)
                  issues.append((claim, issue, fixed_claim))
          
          return ReviewResult(issues=issues)
  ```

**Impact:** Reduces review cost by 60%, clarifies integration.

**Effort:** Low (1-2 days specification + implementation)

---

## Trade-offs

| Option | Pros | Cons |
|--------|------|------|
| **A: Full Multi-Agent (as planned)** | 70-80% context reduction, 3-5x speedup, 95%+ verification | 4-6 weeks implementation, coordination complexity, 2x review cost |
| **B: Hybrid (3 agents only)** | 50-60% context reduction, 2x speedup, simpler coordination | Doesn't fully solve context bloat, limited parallelization |
| **C: Monolithic + Compression** | 30-40% context reduction, 1 week implementation, low risk | Doesn't address scalability, single-agent bottleneck remains |

**Tension:** **Speed vs. Complexity**
- Multi-agent delivers 3-5x speedup but requires robust coordination (retry, timeout, failure isolation)
- Monolithic is simpler but doesn't scale to 100+ sources

**Tension:** **Quality vs. Cost**
- Adversarial review achieves 98% verification (ARIS benchmark) but doubles review cost
- Single-model review achieves 85-90% verification at half the cost

**Tension:** **Flexibility vs. Determinism**
- Adaptive task graphs (lines 800-849) handle discovery failures gracefully but introduce non-determinism (different runs produce different task sequences)
- Static task graphs are deterministic but brittle (if ArXiv fails, entire pipeline may stall)

---

## Consensus Addendum

### Antithesis (Steelman)

**Claim:** Multi-agent orchestration is premature optimization. The current monolithic pipeline works (381 tests passing), and context bloat can be solved with **compression alone** (LLMLingua 70% reduction) without the complexity of 10+ agents.

**Evidence:**
- Lines 613-642: Context compression achieves 70% reduction (30% of original size) — same as multi-agent target
- Lines 1395-1406: Alternative 1 (Monolithic Enhancement) preserves tests, lower risk, 2-3 weeks vs. 4-6 weeks
- Industry precedent: Many production research systems (Perplexity, You.com) use monolithic pipelines with compression, not multi-agent

**Counterargument to Antithesis:**
Compression alone doesn't solve **scalability** (100+ sources still accumulate in single context) or **parallelization** (sequential execution remains 5-minute bottleneck). Multi-agent provides:
1. **Parallel speedup** (3-5x) — compression doesn't reduce wall-clock time
2. **Agent isolation** — prevents context drift in long-running sessions (65% of enterprise AI failures, line 1268)
3. **Adversarial review** — heterogeneous models catch errors single-model misses (lines 189-193, 237-248)

**Synthesis:** Start with **3-agent hybrid** (discovery, analysis, synthesis) + compression. This delivers 60% context reduction + 2x speedup with lower coordination complexity. Scale to 10+ agents only if 100+ source research becomes common.

### Tradeoff Tension

**Tension:** **Adversarial Review Cost vs. Quality Gain**

The plan proposes cross-model review (Claude executor + GPT-4o reviewer) to achieve 98% verification rate (ARIS benchmark, line 1072). However:
- **Cost:** 2x model calls (lines 1298-1310)
- **Benefit:** Catches 5-10% of errors that single-model misses (95% → 98% verification)
- **Question:** Is 3% quality improvement worth 100% cost increase?

**Mitigation (from plan):** Make adversarial review optional for "deep" research only (line 1309). But this creates **inconsistent quality** — "quick" research has 85% verification, "deep" has 98%.

**Alternative:** Use **selective review** (line 1308) — only review low-confidence claims (<0.8). This reduces cost by 60% while catching high-risk errors. Combined with single-model self-review for high-confidence claims, this achieves 95% verification at 1.4x cost (vs. 2x for full adversarial review).

### Synthesis (Viable Path Forward)

**Recommendation:** Implement in **2 phases** to balance speed and risk:

**Phase 1 (Weeks 1-4): 3-Agent Hybrid + Compression**
- 3 agents: Discovery (parallel across sources), Analysis (parallel across papers/repos), Synthesis (sequential)
- Context optimization: External storage + selective retrieval + compression (no agent isolation yet)
- Single-model review with selective adversarial review for low-confidence claims
- **Target:** 60% context reduction, 2x speedup, 90% verification rate
- **Risk:** Lower (3 agents easier to coordinate than 10)

**Phase 2 (Weeks 5-7): Full Multi-Agent (if Phase 1 succeeds)**
- Scale to 10+ agents with full isolation
- Add adaptive task graphs
- Full adversarial review for "deep" research
- **Target:** 70-80% context reduction, 3-5x speedup, 95%+ verification rate
- **Trigger:** If Phase 1 shows context drift or quality issues at 50+ sources

**Benefit:** De-risks implementation, delivers value faster (4 weeks vs. 7 weeks), preserves option to scale.

### Principle Violations (Deliberate Mode)

**Violation 1: Complexity Budget**
- **Principle:** "Simplest solution that works" (Occam's Razor)
- **Violation:** 10+ agents with dynamic task graphs is complex for a problem that may be solvable with compression + 3 agents
- **Severity:** MEDIUM — complexity is justified if scalability is critical, but plan doesn't prove monolithic + compression fails
- **Mitigation:** Phase 1 (3-agent hybrid) tests whether simpler solution suffices

**Violation 2: Premature Optimization**
- **Principle:** "Optimize for bottlenecks, not hypotheticals"
- **Violation:** Plan optimizes for 100+ source research (line 23, 537) but doesn't show evidence this is a common use case
- **Severity:** LOW — if 90% of research is <50 sources, multi-agent overhead may not be worth it
- **Mitigation:** Add telemetry to track source count distribution in production

---

## References

- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:308-340` — Multi-agent architecture diagram
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:356-377` — ResearchOrchestrator implementation
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:397-436` — Parallel discovery and analysis patterns
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:469-498` — Adversarial review specification
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:527-699` — Context optimization strategies
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:709-899` — Task graph and adaptive orchestration
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:1052-1248` — Success metrics and quality scoring
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:1250-1371` — Risk analysis
- `.omc/plans/LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md:1373-1479` — Architectural Decision Record
