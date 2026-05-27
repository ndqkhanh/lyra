# MemAgents ICLR 2026 Workshop - Batch 5 Analysis

**Analysis Date:** May 26, 2026  
**Workshop:** Memory for LLM-Based Agentic Systems (MemAgents)  
**Conference:** ICLR 2026  
**Total Papers Analyzed:** 70+ accepted papers (15 orals, 55+ posters)

## Executive Summary

This batch represents a comprehensive analysis of the ICLR 2026 MemAgents workshop, covering two deeply analyzed papers plus synthesis of 70+ accepted works. The workshop reveals a paradigm shift from simple retrieval-based memory to sophisticated, multi-tier memory architectures with explicit admission control, thermodynamic consolidation, and neuroscience-inspired designs.

### Key Themes Across Workshop

1. **Memory Admission Control** - Moving from passive storage to active filtering
2. **Thermodynamic Memory Models** - Energy-based consolidation mechanisms
3. **Multi-Tier Architectures** - Hot/cold storage with explicit consolidation
4. **Hallucination Prevention** - Confidence-based filtering at admission time
5. **Benchmark Evolution** - From LoCoMo to AMA-Bench and beyond

### Critical Findings

- **Admission control is the new frontier**: Papers show 15-31% latency reduction with explicit filtering
- **Entropy matters**: Thermodynamic models improve robustness to noise by 15% at 50% distractor rate
- **Content type priors dominate**: Ablation studies identify content classification as most influential factor
- **Memory is reconstructed, not retrieved**: Graph-based and associative models outperform vector stores

---

## Paper 1: Adaptive Memory Admission Control (A-MAC)

**Paper ID:** mmdqUrEY24  
**Authors:** Guilin Zhang, Wei Jiang, Jeffrey Friedman, Xu Chu, Xiejiashan Wang, Amine Anoun, Aisha Behr, Kai Zhao (Workday)  
**Type:** Oral Presentation

### Core Innovation

A-MAC treats memory admission as a **structured decision problem** rather than an implicit byproduct of generation. It decomposes memory value into five interpretable dimensions and learns domain-adaptive policies through cross-validated optimization.

### Five-Dimensional Memory Evaluation

```
S(m) = w₁·U(m) + w₂·C(m) + w₃·N(m) + w₄·R(m) + w₅·T(m)
```

**1. Utility (U)** - Future relevance estimation
- LLM-based semantic judgment of actionable value
- Rates whether information supports likely follow-up questions
- Captures persistent user constraints and preferences
- Single LLM call with temperature=0 for determinism

**2. Confidence (C)** - Factual reliability
- Measures conversational evidence support using ROUGE-L
- **Directly mitigates hallucination propagation**
- Identifies supporting spans from prior turns
- Prevents unsupported claims from entering memory

**3. Novelty (N)** - Semantic redundancy check
- Prevents duplicate storage of similar information
- Uses embedding similarity to existing memories
- Reduces memory bloat and retrieval latency

**4. Recency (R)** - Temporal relevance
- Accounts for temporal decay of information value
- Weights recent observations higher
- Implements forgetting curve principles

**5. Content Type Prior (T)** - Domain-specific persistence
- Encodes which categories warrant long-term storage
- **Ablation studies show this is the most influential factor**
- Examples: user preferences > greetings, facts > acknowledgments

### Architecture & Efficiency

**Hybrid Design:**
- Lightweight rule-based features (C, N, R, T)
- Single LLM call for utility assessment only
- Cross-validated weight optimization for domain adaptation

**Computational Advantage:**
- 31% latency reduction vs. LLM-native systems (A-mem, Mem0)
- Avoids multiple LLM invocations per candidate
- Transparent, auditable decision process

### Benchmark Results (LoCoMo)

| Metric | A-MAC | A-mem | MemoryBank | Improvement |
|--------|-------|-------|------------|-------------|
| F1 Score | 0.583 | 0.521 | 0.487 | +11.9% vs A-mem |
| Precision | High | Medium | Low | Superior tradeoff |
| Recall | High | High | Medium | Maintained |
| Latency | -31% | Baseline | -15% | Fastest |

**Key Finding:** Content type prior (T) is the most influential factor for reliable admission.

### Implementation Insights for Lyra

