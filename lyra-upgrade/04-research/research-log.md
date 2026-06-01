# Research Log — Lyra Upgrade Deep Research

## Run 7 (2026-05-31) — Deepening Pass

**Agent**: Lead Research-and-Planning Agent  
**Task**: Deepen existing work per iterative-resume mandate

### Deepened Deliverables
- **voice-mode.md**: +320 lines (latency budget, component trade-offs, VI+EN benchmarks, streaming protocol, failure modes)
- **BREAKTHROUGH-ARCHITECTURE.md**: +200 lines (§11 Lyra Advantages, §12 AGI Direction, §13 Open Problems)
- **brainstorm/00-voice-mode.md**: +2 new ideas (Ideas 7-8)
- **brainstorm/02-memory-architecture.md**: +2 new ideas (Ideas 8-9)
- **MASTER-PLAN.md**: Run 7 changelog
- **PROGRESS.md**: Updated to reflect completion
- **review-audit.md**: Updated to Run 7

### Source Coverage (Final)
- Total URLs: 286
- Deep-read: 253 (88.5%)
- Failed: 4 (1.4%)
- Unresolved: 1 (0.3%)
- Todo: 0 (0%)

---

## Original Run — ICLR 2026 MemAgent Workshop Papers

**Date**: 2026-05-31  
**Agent**: general-purpose (a34fd1f6b4e1d98f6)  
**Task**: Research 8 key ICLR 2026 MemAgent Workshop papers

---

## Summary

**Papers Researched**: 8/8 (100%)  
**Papers Failed**: 0/8  
**Findings Rows Added**: 8  
**Source Ledger Updated**: Yes

---

## Papers Processed

### Successfully Researched (8)

1. **ERL (Experiential Reinforcement Learning)** — [hQgSl6kj1W]
   - Tier: HIGH | Impact: 4 | Effort: 3
   - Key: Heuristic abstraction over raw storage

2. **A-MAC (Adaptive Memory Admission Control)** — [mmdqUrEY24]
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 4
   - Key: 5-factor admission control prevents hallucinated content

3. **MemGrad (Memory-Guided Optimization)** — [GeaPE7iw1V]
   - Tier: HIGH | Impact: 4 | Effort: 4
   - Key: Textual gradients for batch feedback abstraction

4. **Cost-Sensitive Store Routing** — [iGRGjdhl9r]
   - Tier: HIGH | Impact: 4 | Effort: 3
   - Key: Query-aware store selection improves efficiency & accuracy

5. **SABER (Small Actions, Big Errors)** — [En2z9dckgP]
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 3
   - Key: Mutating actions are decisive failure points (55-96% odds reduction)

6. **AOI (AI-Oriented Operations)** — [Q16XXJou3O]
   - Tier: HIGH | Impact: 4 | Effort: 4
   - Key: Domain-aware context compression with theoretical guarantees

7. **Memory Transplants** — [AIJsjIqfsp]
   - Tier: MEDIUM | Impact: 3 | Effort: 3
   - Key: Architecture vs content transfer — neither generalizes well

8. **A-MEM (Agentic Memory)** — [FiM0M8gcct]
   - Tier: HIGH | Impact: 4 | Effort: 4
   - Key: Zettelkasten-inspired autonomous memory evolution

### Failed (0)

None — all papers successfully extracted and analyzed.

---

## Key Insights for Lyra

### BREAKTHROUGH Tier (2)
- **A-MAC**: Explicit admission control with interpretable factors prevents memory pollution
- **SABER**: Action-level risk stratification focuses safeguards on critical decision points

### HIGH Tier (5)
- **ERL**: Distilled lessons > raw trajectories for cross-task generalization
- **MemGrad**: Batch feedback → textual gradients → persistent improvements
- **Cost-Sensitive Routing**: Selective store access reduces noise and cost
- **AOI**: Sliding-window compression preserves critical information (92.8%)
- **A-MEM**: Self-evolving memory structure without manual schema

### MEDIUM Tier (1)
- **Memory Transplants**: Warning — evolved architectures may not transfer across domains

---

## Technical Highlights

1. **Admission Control**: A-MAC's 5-factor model (utility, confidence, novelty, recency, type) achieves F1=0.583 with 31% latency reduction

2. **Action Risk**: SABER proves mutating actions reduce success odds by 55-96% per deviation (p<0.001)

3. **Compression**: AOI achieves 72.4% compression ratio while preserving 92.8% critical information

4. **Abstraction**: ERL shows heuristics provide better transfer than few-shot trajectory prompting

5. **Evolution**: A-MEM enables memories to autonomously update existing memory representations

---

## Files Updated

- `findings.md`: Added 8 detailed entries with mechanism, results, limitations, transferable ideas
- `source-ledger.md`: Marked 8 URLs as "read" with "Yes" in Findings Row column
- `research-log.md`: This summary report

---

**Status**: COMPLETE ✓

---
---

# Research Log — Skills Systems & Model Routing

**Date**: 2026-05-31  
**Agent**: general-purpose (adc123d61431dab1d)  
**Task**: Research Skills Systems and Model Router sources for Phase 3

---

## Summary

**Sources Researched**: 9/9 (100%)  
**Sources Failed**: 0  
**Sources Unresolved**: 1 (PDF encoding issue)  
**Findings Rows Added**: 8  
**Source Ledger Updated**: Yes

---

## Sources Processed

### Successfully Researched (9)

**Skills Systems (4)**:

1. **SkillNet** — [GitHub](https://github.com/zjunlp/SkillNet)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 4
   - Key: NPM-like skill marketplace with 500k+ skills, 5-D evaluation, auto-creation from repos/docs/conversations

2. **SkillNet Paper** — [arXiv:2603.04448](https://arxiv.org/pdf/2603.04448)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 4
   - Key: Skill graph with 4 relationship types, evaluated on ALFWorld/WebShop/ScienceWorld

3. **Darwin Gödel Machine** — [GitHub](https://github.com/jennyzzt/dgm)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 5
   - Key: Self-modifying agent with empirical validation, SWE-bench 20%→50%, Polyglot 14.2%→30.7%

4. **DGM Paper** — [arXiv:2505.22954](https://arxiv.org/abs/2505.22954)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 5
   - Key: Archive-based evolution with version tree, Darwinian exploration

5. **Self-Challenging LM Agents** — [arXiv:2506.01716](https://arxiv.org/pdf/2506.01716)
   - Tier: HIGH | Impact: 4 | Effort: 4
   - Key: Propose-agent-evaluator framework, autonomous task generation, removes human bottleneck

6. **claude-skills** — [GitHub](https://github.com/alirezarezvani/claude-skills)
   - Tier: HIGH | Impact: 4 | Effort: 3
   - Key: 338 production-ready skills, SKILL.md standard, security auditor, cross-platform conversion

**Model Routing (4)**:

7. **RouteLLM** — [GitHub](https://github.com/lm-sys/RouteLLM)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 3
   - Key: 85% cost reduction at 95% GPT-4 performance, matrix factorization router

8. **RouteLLM Paper** — [arXiv:2406.18665](https://arxiv.org/abs/2406.18665)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 3
   - Key: Trained routers outperform heuristics, transfer learning across model pairs

9. **BEST-Route** — [arXiv:2506.22716](https://arxiv.org/abs/2506.22716)
   - Tier: BREAKTHROUGH | Impact: 5 | Effort: 4
   - Key: Multi-sampling from weak models, 60% cost reduction with <1% performance drop

10. **FrugalGPT** — [arXiv:2305.05176](https://arxiv.org/abs/2305.05176)
    - Tier: HIGH | Impact: 4 | Effort: 3
    - Key: 98% cost reduction with cascade routing, prompt adaptation per model tier

### Unresolved (1)

1. **Knowledge Access Beats Model Size** — [arXiv:2603.23013](https://arxiv.org/pdf/2603.23013)
   - Status: PDF encoding issue, content not fully extractable
   - Partial Info: Title suggests memory-augmented routing, smaller models + retrieval > large models
   - Action: Marked for manual review, added to findings with available metadata

### Failed (0)

None — all sources accessible

---

## Key Insights for Lyra

### Skills Systems Breakthroughs (3)
- **SkillNet**: Skill-as-package paradigm with semantic search, dependency graphs, 5-D quality gates
- **Darwin Gödel Machine**: Empirical self-improvement through benchmark validation, archive-based evolution
- **Self-Challenging Agents**: Autonomous curriculum generation removes dataset curation bottleneck

### Model Routing Breakthroughs (3)
- **RouteLLM**: Trained routing (matrix factorization) beats heuristics, 85% cost savings
- **BEST-Route**: Multi-sampling from cheap models matches expensive model quality
- **FrugalGPT**: Cascade with early stopping, 98% cost reduction

### Transferable Patterns
1. **Skill Evolution**: Auto-creation from execution traces + quality evaluation + relationship graphs
2. **Self-Improvement**: Empirical validation over formal proofs, version archives enable rollback
3. **Cost Optimization**: Trained routers + multi-sampling + cascade routing for 60-98% savings
4. **Memory-Augmented Routing**: Smaller models + good retrieval can replace larger models

---

## Technical Highlights

1. **SkillNet**: 500k+ skills, one-line install, 5-D evaluation (Safety/Completeness/Executability/Maintainability/Cost)

2. **DGM**: 150% relative improvement on SWE-bench, 116% on Polyglot through self-modification

3. **RouteLLM**: Matrix factorization router achieves >40% cost savings vs commercial solutions

4. **BEST-Route**: Adaptive sampling (1-5 responses) based on query difficulty and confidence

5. **claude-skills**: 338 skills, 533 stdlib-only Python tools, security auditor, 9-tool conversion

---

## Files Updated

- `findings.md`: Added 2 new sections (Skills Systems Research, Model Routing Research) with 8 detailed rows
- `source-ledger.md`: Marked 9 URLs as "read" across §3.5, §3.7, §3.14, §3.18; updated summary to 3.1% coverage (9/286)
- `research-log.md`: This summary report

---

**Status**: COMPLETE ✓
