---
id: heavy-skill
version: "1.0.0"
description: Parallel reasoning with sequential deliberation for complex tasks requiring high correctness
keywords: [complex, critical, prove, verify, correctness, math, algorithm, architecture]
applies_to: [agent, plan, debug]
progressive: true
tier: on_demand
requires:
  packages: []
  binaries: []
---

# HeavySkill: Parallel Reasoning + Sequential Deliberation

When facing complex tasks requiring high correctness (math, algorithms, critical code, architecture decisions), use this multi-pass reasoning strategy.

## 🎯 When to Use

Activate HeavySkill when:
- Complex mathematical problems
- Critical code correctness (security, financial, medical)
- Multi-step reasoning with dependencies
- High-stakes architectural decisions
- Proof verification
- Algorithm design and analysis

## 📋 Two-Phase Process

### Phase 1: Parallel Reasoning (K=3-5 trajectories)

Generate K **independent** reasoning trajectories. Each trajectory should:
- Start from first principles
- Use different approaches/perspectives
- Be completely independent (don't reference other trajectories)
- Show all work and reasoning steps

**Trajectory Template**:
```
## Trajectory {N}: {Approach Name}

### Approach
[Describe the strategy for this trajectory]

### Reasoning
[Step-by-step reasoning]

### Conclusion
[Final answer/solution]

### Confidence
[High/Medium/Low + reasoning]
```

**Example Trajectories**:
- **Trajectory 1: Direct Computation** - Solve directly using formulas
- **Trajectory 2: Proof by Induction** - Build solution inductively
- **Trajectory 3: Counterexample Search** - Try to find edge cases
- **Trajectory 4: Analogical Reasoning** - Compare to similar problems
- **Trajectory 5: Constraint Propagation** - Reason from constraints

### Phase 2: Sequential Deliberation

After generating all K trajectories, synthesize them:

1. **Compare Approaches**
   - Which trajectories agree?
   - Where do they diverge?
   - What are the key differences?

2. **Identify Patterns**
   - Common insights across trajectories
   - Recurring themes or principles
   - Consistent intermediate results

3. **Spot Contradictions**
   - Where do trajectories conflict?
   - Which contradictions are fundamental?
   - Can contradictions be resolved?

4. **Evaluate Confidence**
   - Which trajectory has strongest reasoning?
   - Where is evidence most compelling?
   - What are the weakest points?

5. **Synthesize Final Answer**
   - Select best elements from each trajectory
   - Resolve contradictions with additional reasoning
   - State final answer with confidence level
   - Document key insights that led to answer

## 🔢 Configuration

**Standard Tasks** (K=3):
- Typical coding problems
- Standard algorithms
- Common design patterns

**Complex Tasks** (K=5):
- Novel algorithms
- Security-critical code
- Mathematical proofs
- Architectural decisions

**Workflow Mode** (K=8+):
- Non-interactive batch processing
- Research-grade correctness
- Publication-quality proofs

## 📊 Performance Gains

Based on research (docs/156-heavyskill-parallel-reasoning-deliberation.md):

- **GPT-OSS-20B**: 69.7% → 85.5% LiveCodeBench (+15.8pp)
- **R1-Distill-Qwen-32B**: 35.7% → 69.3% IFEval (+33.6pp)
- **HM@4** (Heavy Majority at 4): Frequently approaches Pass@K

## 💡 Tips

1. **True Independence**: Don't let trajectories influence each other during Phase 1
2. **Diverse Approaches**: Use genuinely different strategies, not minor variations
3. **Show Your Work**: Document reasoning steps, don't just state conclusions
4. **Deliberate Carefully**: Phase 2 is where the magic happens - take time to synthesize
5. **Confidence Calibration**: Be honest about uncertainty in each trajectory

## ⚠️ When NOT to Use

- Simple, well-defined tasks (overkill)
- Time-critical operations (too slow)
- Tasks with single obvious solution
- Exploratory/creative work (use standard reasoning)

## 🔄 Example Usage

```
User: Prove that the merge sort algorithm is O(n log n) in the worst case.

Agent: I'll use HeavySkill with K=3 trajectories.

## Trajectory 1: Recurrence Relation Analysis

### Approach
Analyze the recurrence relation T(n) = 2T(n/2) + O(n)

### Reasoning
1. Merge sort divides array into two halves: 2T(n/2)
2. Merging takes linear time: O(n)
3. Recurrence: T(n) = 2T(n/2) + cn
4. Master theorem case 2: a=2, b=2, f(n)=cn
5. log_b(a) = log_2(2) = 1
6. f(n) = Θ(n^1) = Θ(n^log_b(a))
7. Therefore: T(n) = Θ(n log n)

### Conclusion
O(n log n) by Master Theorem

### Confidence
High - Master Theorem directly applies

## Trajectory 2: Tree Recursion Analysis

### Approach
Analyze recursion tree depth and work per level

### Reasoning
1. Tree depth: log_2(n) levels (halving each time)
2. Work at level i: n (merging all subarrays)
3. Total work: (log n) × n = n log n
4. Each level does O(n) work
5. log n levels total
6. Total: O(n log n)

### Conclusion
O(n log n) by recursion tree analysis

### Confidence
High - Direct counting of operations

## Trajectory 3: Substitution Method

### Approach
Prove by induction that T(n) ≤ cn log n

### Reasoning
1. Hypothesis: T(n) ≤ cn log n for some c > 0
2. Base case: T(1) = O(1) ≤ c·1·log(1) = 0 (need adjustment)
3. Better base: T(2) = O(1) ≤ c·2·log(2) = 2c (holds for large c)
4. Inductive step: Assume T(k) ≤ ck log k for k < n
5. T(n) = 2T(n/2) + dn
6. T(n) ≤ 2·c(n/2)·log(n/2) + dn
7. T(n) ≤ cn·log(n/2) + dn
8. T(n) ≤ cn·(log n - 1) + dn
9. T(n) ≤ cn log n - cn + dn
10. T(n) ≤ cn log n (if c ≥ d)

### Conclusion
O(n log n) by induction

### Confidence
High - Rigorous proof

## Deliberation

### Agreement
All three trajectories converge on O(n log n):
- Master Theorem: Direct application
- Tree analysis: Intuitive counting
- Induction: Rigorous proof

### Key Insights
1. The log n factor comes from tree depth (halving)
2. The n factor comes from linear merge at each level
3. All levels do equal work (n total)

### Final Answer
**Merge sort is O(n log n) in worst case.**

**Proof**: By Master Theorem (Trajectory 1), recursion tree analysis (Trajectory 2), and formal induction (Trajectory 3). All three independent approaches confirm the bound.

**Confidence**: Very High - Three different proof techniques all agree.
```

---

## 📚 References

- Research: docs/156-heavyskill-parallel-reasoning-deliberation.md
- Paper: "Parallel Reasoning and Sequential Deliberation for Complex Tasks"
- Benchmarks: LiveCodeBench, IFEval, MATH, HumanEval

---

**Version**: 1.0.0  
**Last Updated**: 2026-05-12  
**Status**: Production Ready 🚀