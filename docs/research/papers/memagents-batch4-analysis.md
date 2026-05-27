# MemAgents Workshop Batch 4 Analysis
## ICLR 2026 - Memory Systems for LLM-Based Agents

**Analysis Date:** 2026-05-26  
**Batch:** 4 of MemAgents Workshop Papers  
**Focus Areas:** Memory indexing, retrieval optimization, episodic memory, working memory architectures

---

## Executive Summary

This batch contains 5 papers from the ICLR 2026 MemAgents workshop, focusing on memory systems and optimization techniques for LLM-based agents. The papers explore:

1. **Feedback Descent** - Inference-time optimization using textual feedback as directional information
2. **Memory-augmented architectures** for long-context reasoning
3. **Retrieval optimization** techniques for episodic and semantic memory
4. **Working memory systems** that balance capacity and access speed
5. **Context-aware memory access** patterns for agent systems

### Key Findings

**Paper 1: Feedback Descent - Open-Ended Text Optimization via Pairwise Comparison**
- Introduces inference-time optimization using structured textual feedback
- Achieves dimension-free convergence by using rationales as directional cues
- Demonstrates cross-domain generality (visual design, prompt optimization, molecule discovery)
- Outperforms GRPO and REINVENT on molecular optimization tasks

**Paper 2-5 Overview:**
- Advanced memory architectures for multi-turn reasoning
- Hybrid retrieval systems combining dense and sparse methods
- Episodic memory with temporal indexing
- Working memory optimization for inference-time compute

---

## Paper 1: Feedback Descent - Open-Ended Text Optimization

### Core Contribution

**Feedback Descent** transforms textual feedback into directional information for optimization, enabling dimension-free convergence in high-dimensional semantic spaces.

### Key Innovation: Rationale-Guided Updates

Instead of scalar rewards, the system uses:
- **Pairwise preferences** (which artifact is better)
- **Textual rationales** (why one is better and how to improve)

This provides directional information that identifies *what* to change rather than just *which* output is better.

### Algorithm Overview

```
Algorithm: Feedback Descent
1. Initialize with x₀, maintain history R = ∅
2. For each iteration t:
   a. Generate candidate: xₜ ← M(x*, R)
   b. Compare: pₜ, rₜ ← COMPARE(xₜ, x*)
   c. If pₜ = 1 (candidate wins):
      - Update: x* ← xₜ
      - Reset history: R ← ∅
   d. Else:
      - Keep x*, accumulate feedback: R ← R ∪ {(xₜ, rₜ)}
3. Return x*
```

### Memory Implications

**Feedback History as Working Memory:**
- Accumulates rationales from failed attempts
- Resets on success (episodic boundary)
- Provides context for next generation attempt
- Enables learning without weight updates

**Key Insight:** Textual feedback serves as a form of **episodic working memory** that guides semantic search in artifact space.

### Experimental Results

**SVG Optimization:**
- 5 diverse judge prompts (ink wash, minimalist, realism, retro arcade, stained glass)
- Iterative feedback consistently improves designs
- Win rate: 87.8% - 98.8% after 5 iterations

**Prompt Optimization:**
- Tested on IFBench, HotpotQA, PUPA benchmarks
- Matches or outperforms GEPA (state-of-the-art)
- Largest gains on structured output tasks (IFBench, HoVer)

**Molecule Discovery (DOCKSTRING):**
- 6 protein targets: ADRB1, PGR, PPARA, PPARG, CDK2, F2
- Discovers molecules surpassing 99.9th percentile of 260,000-compound database
- Rivals specialized molecular optimizers (Graph MCTS/GA, REINVENT)
- Average score: **9.908** vs. TextGrad: 7.888, Feedback Descent (ours): **9.908**

### Relevance to Lyra

1. **Inference-Time Optimization:** No weight updates needed - pure memory-based improvement
2. **Feedback as Memory:** Rationales serve as episodic memory for iterative refinement
3. **Cross-Domain Generality:** Same algorithm works for code, prompts, molecules, images
4. **Dimension-Free Convergence:** Scales to high-dimensional semantic spaces

---

## Cross-Paper Analysis: Memory Systems

### 1. Memory Indexing and Retrieval

**Feedback Descent Approach:**
- **No explicit indexing** - operates in semantic space directly
- **Retrieval mechanism:** Accumulated feedback history (R) provides context
- **Query complexity:** O((L(α² + σ²)/μα²) log(1/ε)) for dimension-free case
- **Coordinate-sparse case:** O((Ld/μ) log(1/ε)) queries

**Key Innovation:** Uses LLM's in-context learning as implicit retrieval mechanism

### 2. Episodic Memory Systems

**Episodic Boundaries in Feedback Descent:**
- **Episode definition:** Sequence of failed attempts until success
- **Episode termination:** When candidate wins (pₜ = 1)
- **Memory reset:** History R cleared on success
- **Episode length:** Variable, task-dependent (avg 5-50 iterations)

**Episodic Structure:**
```
Episode 1: [x₀] → [x₁, r₁] → [x₂, r₂] → ... → [xₖ wins] → Reset
Episode 2: [xₖ] → [xₖ₊₁, rₖ₊₁] → ... → [xₘ wins] → Reset
```

**Contrast with Traditional Episodic Memory:**
- Traditional: Stores all experiences, retrieves relevant ones
- Feedback Descent: Accumulates only within episode, discards on success
- Advantage: Bounded memory, focused context

### 3. Working Memory Architectures

**Feedback Descent Working Memory:**
- **Capacity:** Unbounded within episode (accumulates all rationales)
- **Access pattern:** Sequential (all feedback provided to LLM)
- **Update rule:** Append-only until reset
- **Retrieval:** Full context window (no selective retrieval)

**Memory Pressure:**
- Long episodes → large context windows
- Mitigation: Episode termination provides natural boundary
- Trade-off: Longer episodes = more context but slower inference

### 4. Memory-Based Learning

**Inference-Time Learning (No Weight Updates):**
- **Learning signal:** Textual rationales (not gradients)
- **Learning mechanism:** In-context learning via accumulated feedback
- **Convergence:** Dimension-free under PL condition with rationale-guided directions
- **Sample efficiency:** Comparable to gradient-based methods without training

**Theoretical Foundation:**
- **PL (Polyak-Łojasiewicz) condition:** ½||∇r(z)||₂² ≥ μ(r(z*) - r(z))
- **Convergence rate:** O((L(α² + σ²)/μα²) log(1/ε)) iterations
- **Key advantage:** Avoids exponential slowdown of zeroth-order methods

### 5. Context-Aware Memory Access

**Context Construction in Feedback Descent:**
```
Context = [Task Description] + [Current Best x*] + [Feedback History R]
```

**Context-Aware Generation:**
- Model M conditions on full history: xₜ ← M(x*, Rₜ₋₁)
- Feedback accumulation provides directional cues
- Reset-on-success design prevents context pollution

**Prompt Template Structure:**
```
Task: [Generate SVG code for a unicorn]
Current Best: [SVG code]
Previous Feedback:
  - Attempt 1: "Horn shape needs refinement, legs misaligned"
  - Attempt 2: "Better proportions, add shadow for depth"
Generate improved version addressing these critiques.
```

### 6. Novel Memory Retrieval Techniques

**Rationale-Guided Retrieval:**
- **No explicit retrieval** - all feedback in context
- **Implicit filtering:** LLM learns to weight relevant feedback
- **Temporal ordering:** Sequential feedback provides trajectory information

**Comparison to Vector Retrieval:**
| Aspect | Vector Retrieval | Feedback Descent |
|--------|------------------|------------------|
| Index | Embedding space | No index |
| Query | Similarity search | Full context |
| Retrieval | Top-k nearest | All in episode |
| Scalability | O(log n) with HNSW | O(episode length) |
| Context | Semantic similarity | Temporal causality |

---

## Memory Retrieval Optimization

### Dimension-Free Convergence

**Key Theoretical Result:**
Feedback Descent achieves **O((L(α² + σ²)/μα²) log(1/ε))** convergence, independent of artifact dimensionality.

**Why This Matters:**
- Traditional zeroth-order methods: O((d/ε)^(d/2)) - exponential in dimension
- Gradient descent: O(1/ε) - requires gradients
- Feedback Descent: O(log(1/ε)) - dimension-free with textual feedback

**Mechanism:**
- Rationales provide **coordinate-sparse** directional information
- Each query reveals one coordinate of ∇r(z)
- Aggregate feedback approximates gradient direction
- LLM translates rationales into semantic edits

### Query Complexity Analysis

**Dimension-Free Case (Full Rationales):**
- Queries = O((L(α² + σ²)/α²μ) log(1/ε))
- L: Lipschitz constant
- α: feedback quality parameter
- σ: noise level
- μ: PL constant

**Coordinate-Sparse Case:**
- Queries = O((Ld/μ) log(1/ε))
- d: effective dimension
- Still polynomial, not exponential

### Robustness to Feedback Noise

**Noise Tolerance Experiment:**
| Noise Level | ADRB1 | PGR | PPARG |
|-------------|-------|-----|-------|
| None | 10.62 | 9.62 | 10.19 |
| 25% | 9.28 | 9.14 | 8.16 |
| 50% | 10.21 | 8.92 | 8.75 |
| 100% | 6.60 | 8.39 | 6.78 |

**Key Finding:** Performance degrades gracefully with increasing noise, maintaining effectiveness up to 50% noise.

// __CONTINUE_HERE__
