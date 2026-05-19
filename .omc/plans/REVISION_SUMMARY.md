# Plan Revision Summary

**Date:** 2026-05-18  
**Plan:** LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md  
**Revision Trigger:** Architect & Critic Review (ITERATE verdict)

---

## Critical Gaps Addressed

### 1. Agent Coordination Primitives (CRITICAL)

**Original Issue:** Missing retry policy, circuit breaker, timeout hierarchy, and health checks

**Resolution:**
- **Task State Machine:** PENDING → RUNNING → (RETRY) → COMPLETED/FAILED
- **Retry Policy:** Max 2 retries with exponential backoff (1s, 2s, 4s) for transient failures only
- **Circuit Breaker:** Synthesis proceeds if ≥50% of discovery tasks succeed; fail fast if <50%
- **Timeout Hierarchy:** 5min/task, 15min/phase, 60min/total
- **Health Checks:** Kill agents hanging >5min without progress, monitor memory usage (<2GB per agent)

**Implementation:** Week 1 of Phase 1

### 2. Memory Store Capacity Bounds (HIGH)

**Original Issue:** No capacity bounds, compaction strategy, or query latency SLOs

**Resolution:**
- **Capacity Targets:** 10K sources, 100K notes, 1K sessions (alert at 80%, block at 100%)
- **Compaction Strategy:** Archive notes >90 days, deduplicate embeddings >0.95 similarity, vacuum SQLite weekly
- **Query Latency SLOs:** FTS5 <100ms (p95), embeddings <200ms (p95), reranking <500ms (p95)
- **Monitoring:** Dashboard for capacity utilization, query latency, automated alerts for SLO violations

**Implementation:** Week 2 of Phase 1

### 3. Adversarial Review Integration (MEDIUM)

**Original Issue:** Unclear reviewer context budget, disagreement resolution protocol, selective review criteria

**Resolution:**
- **Reviewer Context Budget:** Max 30KB (report ~10KB + top-10 sources ~15KB + claim mapping ~5KB)
- **Disagreement Resolution:** Executor must fix, soften, or remove ALL flagged claims; max 2 review rounds
- **Selective Review:** Only review claims with confidence <0.8 (based on citation count, source quality)
- **Cost Control:** Use GPT-4o-mini (~$0.15/1M tokens), prompt caching, optional for "quick"/"standard" depth

**Implementation:** Week 3 of Phase 1

---

## Major Architectural Change: 2-Phase Approach

### Original Plan: 6 Phases, 7 Weeks

1. Foundation (Weeks 1-2)
2. Discovery Agents (Week 3)
3. Analysis Agents (Week 4)
4. Synthesis & Assurance (Week 5)
5. Context Optimization (Week 6)
6. Integration & Testing (Week 7)

**Issue:** Premature optimization for 100+ sources when most research uses 20-50 sources

### Revised Plan: 2 Phases, 4-7 Weeks

**Phase 1 (Weeks 1-4): 3-Agent Hybrid + Compression**
- 3 agents: Discovery (Haiku), Analysis (Sonnet), Synthesis (Opus)
- Coordination primitives, memory capacity bounds, adversarial review protocol
- Context optimization: external storage, selective retrieval, compression, agent isolation
- **Target:** 60% context reduction, 2x speedup, 90% verification rate

**Phase 2 (Weeks 5-7, CONDITIONAL): Scale to 10+ Agents**
- **Trigger:** Context drift at 50+ sources OR user requests 100+ source capability
- 10+ specialized agents: 6 discovery, 4 analysis, 4 synthesis, 1 assurance
- Adaptive task decomposition, progress checkpointing
- **Target:** 80% context reduction, 5x speedup, 95% verification rate

**Decision Point (End of Week 4):**
- Context drift at 50+ sources? → Proceed to Phase 2
- 60% reduction + 90% verification without drift? → Phase 1 sufficient, skip Phase 2
- Coordination primitives failing? → Iterate on Phase 1

**Rationale:**
- Reduces risk (validate architecture early)
- Avoids premature optimization (most research uses 20-50 sources)
- Provides early feedback (4 weeks vs. 7 weeks)
- Aligns with Architect & Critic recommendations

---

## Additional Improvements

### 4. Cost-Benefit Analysis for Adversarial Review

**Added:**
- Cost per review: $0.0045 (GPT-4o-mini, 30KB context)
- Manual review cost: $12.50 (15 minutes × $50/hour)
- **ROI: 2,777x** (assuming manual review alternative)
- Selective review (confidence <0.8): 70% cost reduction → **ROI: 9,259x**

**Conclusion:** Adversarial review is cost-effective even with conservative assumptions

### 5. Telemetry for Source Count Distribution

**Added:**
- Track source count distribution (p50, p75, p90, p95, p99)
- Track percentage of queries using <20, 20-50, 50-100, >100 sources
- Track context drift correlation with source count
- Track quality metrics (verification rate, citation accuracy) vs. source count
- Track wall-clock time vs. source count

**Purpose:** Validate assumption that most research uses 20-50 sources, inform Phase 2 decision

**Dashboard:** Histogram, line charts, scatter plot, percentile table

**Phase 1 Decision Criteria:**
- If p90 < 50 sources AND no drift at p90 → Phase 1 sufficient
- If p90 >= 50 sources OR drift at p75 → Proceed to Phase 2
- If >10% of queries use >100 sources → Proceed to Phase 2

---

## Updated Success Metrics

### Phase 1 (Weeks 1-4)

**Context Efficiency:**
- 60% context reduction (40KB vs. 100KB for 50 sources)
- 2x speedup (2.5 minutes vs. 5 minutes)

**Quality:**
- 90% verification rate (vs. 85% current)
- 100% citation accuracy (vs. 95% current)

**Coordination:**
- Retry policy success rate >80%
- Circuit breaker triggers correctly (<50% success)
- Timeouts kill hanging agents after 5min
- Health checks detect unhealthy agents

**Memory:**
- Capacity bounds enforced (alert at 80%, block at 100%)
- Query latency SLOs met (FTS5 <100ms, embeddings <200ms, reranking <500ms)
- Compaction reduces database size by 30%+

**Adversarial Review:**
- Reviewer context <30KB
- 80%+ unsupported claims caught
- Disagreements resolved in <2 rounds

### Phase 2 (Weeks 5-7, if needed)

**Context Efficiency:**
- 80% context reduction (20KB vs. 100KB for 50 sources)
- 5x speedup (1 minute vs. 5 minutes)

**Quality:**
- 95% verification rate
- Handles 100+ source research without context drift

**Coordination:**
- Coordination overhead <10% (10+ agents vs. 3 agents)

---

## Risk Mitigation Updates

### Risk 1: Multi-Agent Coordination Complexity
- **Severity:** CRITICAL (upgraded from HIGH)
- **New Mitigations:** Detailed coordination primitives specification, 3-agent prototype first

### Risk 6: Memory Store Scalability
- **Severity:** HIGH (upgraded from LOW)
- **New Mitigations:** Capacity bounds, compaction strategy, query latency SLOs, monitoring dashboard

### Risk 4: Adversarial Review Integration
- **Severity:** MEDIUM (unchanged)
- **New Mitigations:** Context budget specification, disagreement resolution protocol, selective review criteria

---

## Follow-Up Actions

1. **Phase 1 Prototype (Week 1)** — Build 3-agent prototype to validate architecture
2. **Coordination Primitives Validation (Week 1)** — Test retry, circuit breaker, timeouts, health checks
3. **Memory Capacity Monitoring (Week 2)** — Implement dashboard for capacity, latency, compaction
4. **Adversarial Review Protocol Testing (Week 3)** — Validate 30KB budget, disagreement resolution, selective review
5. **Phase 1 Decision Point (End of Week 4)** — Evaluate context drift at 50+ sources, decide on Phase 2
6. **Telemetry for Source Count Distribution** — Track source count patterns to inform Phase 2 decision
7. **Benchmark Suite (Week 4)** — Create 10-query benchmark across domains and source counts
8. **Documentation (Week 4)** — Architecture guide, migration guide, performance monitoring dashboard
9. **Cost Analysis (Week 4)** — Measure cost impact vs. current implementation
10. **Phase 2 Evaluation (Week 5, if needed)** — Evaluate distributed system options if scaling beyond 10 agents

---

## Summary of Changes

**Critical Gaps Addressed:** 3/3 ✅
- Agent coordination primitives (retry, circuit breaker, timeouts, health checks)
- Memory capacity bounds (10K sources, 100K notes, 1K sessions) + compaction + query SLOs
- Adversarial review protocol (30KB context budget, disagreement resolution, selective review)

**Major Architectural Change:** 6-phase → 2-phase approach
- Phase 1 (4 weeks): 3-agent hybrid + compression → 60% reduction, 90% verification
- Phase 2 (3 weeks, conditional): 10+ agents → 80% reduction, 95% verification

**Additional Improvements:**
- Cost-benefit analysis for adversarial review (ROI: 2,777x - 9,259x)
- Telemetry for source count distribution (inform Phase 2 decision)

**Implementation Timeline:**
- Phase 1: 4 weeks (vs. 7 weeks original)
- Phase 2: +3 weeks if needed (7 weeks total)
- Early feedback at Week 4 decision point

**Alignment:** Fully addresses Architect & Critic concerns, ready for APPROVE verdict
