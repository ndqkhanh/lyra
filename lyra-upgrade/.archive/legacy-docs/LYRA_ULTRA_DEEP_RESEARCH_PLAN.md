# Lyra Ultra Deep Research Plan
## Comparative Analysis & Enhancement Strategy

**Created:** 2026-05-19  
**Status:** Strategic Planning  
**Foundation:** Academic Research Skills (Imbad0202) + Lyra Current Capabilities

---

## Executive Summary

This plan integrates best practices from the academic-research-skills repository (42 agents, PRISMA compliance, multi-layer citation verification) with Lyra's existing deep research infrastructure (7+ sources, 4 memory stores, 381 tests) to create a world-class research agent.

**Key Enhancements:**
1. **Mandatory Integrity Gates** - Cannot skip validation checkpoints
2. **Multi-Layer Citation Verification** - 3-layer anchors with cross-index triangulation
3. **PRISMA Systematic Review** - 17-item compliance for academic rigor
4. **Socratic Questioning Mode** - State-Challenge-Reflect protocol
5. **Temporal Verification** - Detect anachronistic citations
6. **Writing Quality Checks** - AI slop detection (25 high-frequency terms)
7. **Cross-Model Adversarial Review** - Heterogeneous verification

---

## Part 1: Comparative Analysis

### Academic Research Skills Repository Strengths

#### 1. Pipeline Architecture
- **10-Stage Orchestrator** with adaptive checkpoints (FULL/SLIM/MANDATORY)
- **Mandatory Integrity Gates** at stages 2.5 and 4.5 (cannot be skipped)
- **Human-in-the-Loop** design: "AI is your copilot, not the pilot"
- **Observer Agent** runs at FULL/SLIM but NOT at MANDATORY gates

#### 2. Agent System (42 Total)
- **Deep Research Module** (13 agents, 7 modes):
  - systematic-review, socratic, fact-check, exploratory, comparative, trend-analysis, replication
- **Academic Paper Module** (12 agents, 10 modes):
  - plan, draft, revision-coach, disclosure, style-calibration
- **Paper Reviewer Module** (7 agents, 6 modes):
  - 0-100 quality rubrics, calibration protocol (FNR<0.15, FPR<0.10)
- **Pipeline Orchestrator** (4 agents):
  - collaboration_depth_agent, checkpoint_manager

#### 3. Citation Verification (Multi-Layer)
- **Three-Layer Anchors**: `<!--anchor:<kind>:<value>-->` where kind ∈ {quote, page, section, paragraph, none}
- **Cross-Index Triangulation**: Semantic Scholar + OpenAlex + Crossref
- **Claim-Faithfulness Audit**: `ARS_CLAIM_AUDIT=1` judges whether cited sources support claims
- **Five HIGH-WARN Violation Classes**: Gate-refuse output on critical violations
- **Post-Publication Audit**: Found 21 issues (31% error rate) in initial implementation

#### 4. Anti-Hallucination Measures
- **No AI Memory Verification**: Mandatory WebSearch audit trail
- **Contamination Detection**: Signals for `preprint_post_llm_inflection` and `semantic_scholar_unmatched`
- **Motivation**: Zhao et al. found 146,932 hallucinated citations for 2025 alone

#### 5. Socratic Method Integration
- **Intent-Based Activation**: Detects exploratory vs goal-oriented intent
- **State-Challenge-Reflect (SCR) Protocol**: Commitment gates and certainty-triggered contradictions
- **Devil's Advocate Protocol**: Concession Threshold (1-5 scoring), no consecutive concessions, frame-lock detection

#### 6. Quality Assurance
- **PRISMA-trAIce Compliance**: 17 items for systematic review
- **Risk-of-Bias Assessment**: Integrated into review protocol
- **Writing Quality Check**: Detects 25 AI high-frequency terms, punctuation patterns, throat-clearing openers
- **Temporal Verification**: 5 failure modes (retrospective arithmetic, anachronistic citation, comparator unmaterialized, causal inversion, deictic present)

#### 7. Material Passport System
- **13 Schemas** for cross-session handoff
- **Input Ports**: `literature_corpus[]` for user-owned literature
- **Ledgers**: `reset_boundary[]` for cross-session resume
- **Metadata**: `contamination_signals`, `citation_provenance`
- **Repro Lock**: Optional block for configuration documentation

#### 8. Cross-Model Verification
- **Optional Flag**: `ARS_CROSS_MODEL` enables GPT-5.4 Pro or Gemini 3.1 Pro
- **Use Cases**: Integrity verification sample cross-checks, independent DA critique

---

### Lyra Current Capabilities

#### 1. Discovery Engine (Strong)
- **7+ Sources**: ArXiv, Semantic Scholar, GitHub, OpenReview, HuggingFace, Papers with Code, ACL Anthology
- **Citation Traversal**: Forward/backward citations, snowball sampling
- **Quality Scoring**: Multi-factor (citations × recency × venue × relevance × stars)
- **381 Passing Tests**: Production-ready foundation

#### 2. Memory Architecture (Strong)
- **Zettelkasten**: Research notes with links (A-Mem style)
- **DCI Corpus**: Local paper store with SQLite FTS5
- **ReasoningBank**: Strategy memory (successful/failed patterns)
- **Memento**: Session case bank (episodic memory)

#### 3. Intelligence Components (Partial)
- **VerifiableChecklistGenerator**: Rule-based (no LLM)
- **EvidenceAudit**: Claim extraction and verification
- **ContradictionDetector**: Numerical conflicts, outperformance claims
- **GapAnalyzer**: Explicit gap mentions, coverage analysis
- **FalsificationChecker**: Counter-evidence search

#### 4. Multi-Agent Infrastructure (Ready)
- **lyra-evolution**: Self-improvement framework
- **lyra-skills**: Reusable capabilities
- **10-Step Pipeline**: Clarify → Plan → Search → Filter → Fetch → Analyze → Audit → Synthesize → Report → Memorize

---

### Critical Gaps: Lyra vs Academic Research Skills

| Feature | Academic Research Skills | Lyra Current | Gap Severity |
|---------|-------------------------|--------------|--------------|
| **Mandatory Integrity Gates** | ✅ Stages 2.5, 4.5 cannot skip | ❌ Optional validation | CRITICAL |
| **Multi-Layer Citation Verification** | ✅ 3-layer anchors + cross-index | ❌ Pattern-based only | CRITICAL |
| **PRISMA Systematic Review** | ✅ 17-item compliance | ❌ Not implemented | HIGH |
| **Socratic Questioning** | ✅ SCR protocol | ❌ Not implemented | MEDIUM |
| **Temporal Verification** | ✅ 5 failure modes | ❌ Not implemented | HIGH |
| **Contamination Detection** | ✅ LLM-inflection signals | ❌ Not implemented | MEDIUM |
| **Writing Quality Checks** | ✅ 25 AI term detection | ❌ Not implemented | MEDIUM |
| **Cross-Model Verification** | ✅ Optional GPT/Gemini | ❌ Single-model only | HIGH |
| **Material Passport** | ✅ 13 schemas | ❌ Not implemented | LOW |
| **Dialogue Health Checks** | ✅ Every 5 turns | ❌ Not implemented | LOW |

---

## Part 2: Ultra Enhancement Plan

### Phase 0: Foundation Hardening (Week 1)

**Goal**: Implement mandatory integrity gates and multi-layer citation verification

#### Deliverable 1: Mandatory Integrity Gates
```python
class IntegrityGate:
    """Cannot-skip validation checkpoint"""
    
    def __init__(self, stage: str, validators: List[Validator]):
        self.stage = stage  # "2.5" or "4.5"
        self.validators = validators
        self.can_skip = False  # HARD-CODED: cannot be overridden
    
    def validate(self, research_state: ResearchState) -> GateResult:
        """Run all validators, block if any fail"""
        results = [v.validate(research_state) for v in self.validators]
        
        if any(r.severity == "CRITICAL" for r in results):
            return GateResult(
                passed=False,
                blocking_issues=[r for r in results if r.severity == "CRITICAL"],
                message="CRITICAL issues detected. Cannot proceed."
            )
        
        return GateResult(passed=True, issues=results)

# Stage 2.5: Post-Discovery Integrity Gate
stage_2_5_gate = IntegrityGate(
    stage="2.5",
    validators=[
        MinimumSourceCountValidator(min_sources=10),
        SourceDiversityValidator(min_source_types=3),
        CitationAccessibilityValidator(),  # All sources accessible
        DuplicationDetector(max_duplicate_ratio=0.3),
    ]
)

# Stage 4.5: Pre-Report Integrity Gate
stage_4_5_gate = IntegrityGate(
    stage="4.5",
    validators=[
        CitationFidelityValidator(min_fidelity=1.0),  # 100% valid citations
        ClaimVerificationValidator(min_verification=0.95),  # 95% claims backed
        TemporalConsistencyValidator(),  # No anachronistic citations
        ContradictionDetector(),  # Flag unresolved contradictions
        CompletenessValidator(min_completion=0.90),  # 90% checklist items
    ]
)
```

**Success Criteria:**
- ✅ Integrity gates block progression on CRITICAL issues
- ✅ 100% citation fidelity (all citations verified in 2+ indexes)
- ✅ 95%+ claim-faithfulness (citations support claims)
- ✅ Zero temporal violations in reports
- ✅ All 381 existing tests still pass

---

### Phase 1: PRISMA Systematic Review (Week 2)

**Goal**: Implement PRISMA-trAIce 17-item compliance for systematic reviews

**Success Criteria:**
- ✅ PRISMA compliance ≥85% for systematic reviews
- ✅ Risk-of-bias assessment for all included studies
- ✅ Systematic review mode available via `/research --mode=systematic`

---

### Phase 2: Socratic Questioning Mode (Week 3)

**Goal**: Implement State-Challenge-Reflect protocol for exploratory research

**Success Criteria:**
- ✅ Socratic mode available via `/research --mode=socratic`
- ✅ Intent detection accuracy ≥80%
- ✅ Devil's advocate protocol prevents frame-lock
- ✅ User satisfaction with exploratory research

---

### Phase 3: Writing Quality Checks (Week 4)

**Goal**: Detect AI-generated content patterns and improve writing quality

**Success Criteria:**
- ✅ AI slop detection accuracy ≥85%
- ✅ Reports pass all 5 editing passes
- ✅ Writing quality score ≥0.90
- ✅ Zero throat-clearing openers in final reports

---

### Phase 4: Cross-Model Adversarial Review (Week 5)

**Goal**: Implement heterogeneous model verification (Claude + GPT-4o)

**Success Criteria:**
- ✅ Cross-model review catches 80%+ unsupported claims
- ✅ Verification rate improves from 90% → 95%+
- ✅ Reviewer context budget ≤30KB
- ✅ Cost per review ≤$0.005

---

## Part 3: Implementation Roadmap

### Timeline: 5 Weeks

**Week 1: Foundation Hardening**
- Mandatory integrity gates (stages 2.5, 4.5)
- Multi-layer citation verification (3 layers)
- Temporal verification (5 failure modes)
- Tests: 50+ new tests

**Week 2: PRISMA Systematic Review**
- PRISMA-trAIce 17-item compliance
- Risk-of-bias assessment
- Systematic review mode
- Tests: 30+ new tests

**Week 3: Socratic Questioning**
- State-Challenge-Reflect protocol
- Intent detection
- Devil's advocate protocol
- Tests: 40+ new tests

**Week 4: Writing Quality**
- AI slop detector (25 terms)
- 5-pass editing pipeline
- Burstiness analysis
- Tests: 30+ new tests

**Week 5: Cross-Model Review**
- Heterogeneous verification
- GPT-4o integration
- Disagreement resolution
- Tests: 40+ new tests

**Total: 190+ new tests, 381 existing tests = 571 tests**

---

## Part 4: Success Metrics

### Quantitative Targets

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Verification Rate** | 85% | 95%+ | +10% |
| **Citation Fidelity** | 95% | 100% | +5% |
| **Temporal Violations** | Unknown | 0 | N/A |
| **PRISMA Compliance** | N/A | 85%+ | New |
| **AI Slop Detection** | N/A | 85%+ | New |
| **Cross-Model Catch Rate** | N/A | 80%+ | New |

### Qualitative Targets

- ✅ Reports pass mandatory integrity gates
- ✅ Citations verified in 2+ independent indexes
- ✅ No anachronistic citations
- ✅ PRISMA-compliant systematic reviews
- ✅ Socratic mode for exploratory research
- ✅ Writing quality indistinguishable from human experts
- ✅ Cross-model review eliminates plausible unsupported claims

---

## Part 5: Integration with Existing Plans

### Relationship to LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md

**This Ultra Plan is ADDITIVE to the existing plan:**

| Existing Plan Component | Ultra Plan Enhancement |
|------------------------|------------------------|
| **Phase 1: 3-Agent Hybrid** | + Mandatory integrity gates |
| **Phase 2: 10+ Agents** | + PRISMA systematic review mode |
| **Adversarial Review** | + Cross-model verification (GPT-4o) |
| **Context Optimization** | + Material passport system |
| **Memory Stores** | + Contamination detection |
| **Quality Metrics** | + Temporal verification, AI slop detection |

**Combined Timeline:**
- **Weeks 1-4**: Existing Phase 1 (3-agent hybrid) + Ultra Phase 0-1 (integrity gates, PRISMA)
- **Week 5**: Ultra Phase 2-4 (Socratic, writing quality, cross-model)
- **Weeks 6-8**: Existing Phase 2 (10+ agents, if needed)

**Total: 8 weeks for complete integration**

---

## Part 6: Key Differentiators

### Lyra Ultra vs. Academic Research Skills

**What Lyra Gains:**
1. ✅ Mandatory integrity gates (cannot skip validation)
2. ✅ Multi-layer citation verification (3-layer anchors)
3. ✅ PRISMA systematic review compliance
4. ✅ Socratic questioning mode
5. ✅ Temporal verification (5 failure modes)
6. ✅ AI slop detection (25 high-frequency terms)
7. ✅ Cross-model adversarial review

**What Lyra Already Has (Advantages):**
1. ✅ 7+ discovery sources (vs. unclear in ARS)
2. ✅ 4 specialized memory stores
3. ✅ 381 production-ready tests
4. ✅ Multi-agent infrastructure (lyra-evolution, lyra-skills)
5. ✅ Citation graph traversal
6. ✅ GitHub repository analysis

**Combined Strengths:**
- **Discovery**: 7+ sources + citation traversal + GitHub analysis
- **Verification**: 3-layer citation + cross-model review + temporal checks
- **Quality**: PRISMA compliance + AI slop detection + 5-pass editing
- **Modes**: Standard + Systematic + Socratic + Deep-dive
- **Memory**: 4 stores + contamination detection + material passport

---

## Part 7: Cost-Benefit Analysis

### Implementation Costs

**Development Time:**
- Week 1: Foundation hardening (50 hours)
- Week 2: PRISMA implementation (40 hours)
- Week 3: Socratic mode (40 hours)
- Week 4: Writing quality (30 hours)
- Week 5: Cross-model review (40 hours)
- **Total: 200 hours (~5 weeks)**

**Operational Costs:**
- Cross-model review: ~$0.005 per review (GPT-4o-mini)
- Additional API calls: ~$0.01 per research session
- **Total: ~$0.015 per research session**

### Benefits

**Quality Improvements:**
- Verification rate: 85% → 95% (+10%)
- Citation fidelity: 95% → 100% (+5%)
- Temporal violations: Unknown → 0
- PRISMA compliance: 0% → 85%+

**User Value:**
- Publication-quality reports (no manual editing needed)
- Zero hallucinated citations (trust in results)
- Systematic review capability (academic rigor)
- Exploratory research mode (Socratic questioning)

**ROI Calculation:**
- Manual review cost: ~15 min × $50/hr = $12.50 per report
- Automated review cost: $0.015 per report
- **Savings: $12.48 per report**
- **ROI: 832x**

---

## Conclusion

This Ultra Plan transforms Lyra into a world-class research agent by integrating:

1. **Academic Research Skills best practices** (42 agents, PRISMA, multi-layer verification)
2. **Lyra's existing strengths** (7+ sources, 4 memory stores, 381 tests)
3. **Novel enhancements** (mandatory integrity gates, cross-model review, temporal verification)

**Timeline**: 5 weeks standalone, 8 weeks integrated with existing plan

**Expected Outcome**: 
- 95%+ verification rate
- 100% citation fidelity
- Zero temporal violations
- PRISMA-compliant systematic reviews
- Publication-quality reports indistinguishable from human experts

**Next Steps:**
1. Review and approve this ultra plan
2. Integrate with existing LYRA_ULTIMATE_DEEP_RESEARCH_PLAN.md
3. Begin Week 1 implementation (mandatory integrity gates)
4. Track metrics and adjust as needed

---

**Ready to proceed?**
- "proceed" - Begin implementation
- "adjust [X]" - Modify specific component
- "integrate" - Show detailed integration with existing plan
