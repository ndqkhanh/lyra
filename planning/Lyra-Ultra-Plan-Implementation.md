# Lyra Ultra Plan: Population-Based Reasoning Implementation

## Executive Summary

Based on deep research synthesis, **the single highest-leverage upgrade for Lyra is converting from single-trajectory to population-trajectory reasoning** with execution-grounded selection. This unlocks WIDTH (diverse sampling) to complement existing DEPTH (Reflexion), delivering:

- **+12.3% on AIME** (ParaThinker, 1.5B model, 8 parallel paths)
- **+75% relative gain** over majority voting (A2R synthesizer)
- **Training-free**: No model fine-tuning required
- **Scaffold-dominated gains**: Harness improvements outpace model upgrades in 2025-2026

**Core Insight**: Lyra already has the substrate (worktree forking, checkpoints, HIR, AER traces, 16 providers). The missing pieces are population primitives and verifier-graded selection.

---

## Phase 1: Population Sampling Infrastructure

### 1.1 Population-Mode Spawn
**Goal**: Fork N trajectories on the SAME problem, not N different problems.

**Implementation**:
```typescript
// New /spawn variant
interface PopulationSpawnConfig {
  problem: string;
  n: number;              // Number of parallel trajectories
  diversityStrategy: 'provider' | 'temperature' | 'prefix' | 'hybrid';
  shareCheckpoint?: string; // Common setup checkpoint
}
```

**Diversity Strategies**:
- **Provider diversity**: Route to different LLM providers (GPT-4, Claude, Gemini, etc.)
- **Temperature diversity**: Same model, varied temperature (0.7, 0.9, 1.1)
- **Prefix diversity**: Different reasoning prefixes ("Let's think step by step" vs "First, let's break down...")
- **Hybrid**: Combine multiple strategies

**Key Feature**: Cross-trajectory checkpoint reuse
- Share common setup (project init, dependency install)
- Fork only at divergence points
- Reduces redundant computation

### 1.2 Trajectory State Management
**Extend HIR (Harness Intermediate Representation)**:
```typescript
interface TrajectoryState {
  id: string;
  parentCheckpoint?: string;
  divergencePoint: number;      // Step where this trajectory forked
  reasoning: HIRNode[];
  aer: AERTrace;                // Execution trace
  verificationResults: VerificationResult[];
  score?: number;               // Selector-assigned score
}

interface PopulationState {
  problemId: string;
  trajectories: TrajectoryState[];
  sharedCheckpoints: Map<string, Checkpoint>;
  selectionHistory: SelectionEvent[];
}
```

---

## Phase 2: Verifier-Graded Selection System

### 2.1 Verification Hierarchy
**Critical Finding**: Execution-based verification beats self-consistency and LLM judges for code/math.

**Selector Routing Logic** (preference order):
1. **Hard Verifiers** (deterministic, ground truth)
   - Test execution (pass/fail)
   - Symbolic equivalence (math expressions)
   - Sandbox validation (security, resource limits)

2. **Generated Test Verifiers** (CodeT-style)
   - LLM generates test cases from spec
   - Execute generated tests
   - Higher coverage than human tests alone

3. **Soft Verifiers** (heuristic, probabilistic)
   - Universal Self-Consistency (USC)
   - Cross-provider judge debate
   - Process-level scoring

**Implementation**:
```typescript
interface Selector {
  selectBest(trajectories: TrajectoryState[]): TrajectoryState;
  scoreTrajectory(t: TrajectoryState): Promise<number>;
}

class HierarchicalSelector implements Selector {
  async scoreTrajectory(t: TrajectoryState): Promise<number> {
    // 1. Try hard verifiers first
    if (await this.hasTests(t)) {
      return this.executeTests(t);
    }
    
    if (await this.canSymbolicVerify(t)) {
      return this.symbolicEquivalence(t);
    }
    
    // 2. Generate tests if possible
    if (this.isCodeTask(t)) {
      return this.codeTVerification(t);
    }
    
    // 3. Fall back to soft verifiers
    return this.softVerification(t);
  }
}
```

### 2.2 Symbolic Equivalence Partitioning
**Source**: Cho et al., arXiv 2604.06485
**Gains**: HumanEval+ 0.728 → 0.803, LiveCodeBench 0.516 → 0.604 at N=10

**Algorithm**:
1. Generate N candidate solutions
2. Partition by symbolic equivalence (same behavior, different syntax)
3. Select representative from largest partition
4. No extra LLM calls required

```python
def symbolic_equivalence_partition(candidates: List[Code]) -> Code:
    partitions = defaultdict(list)
    
    for candidate in candidates:
        signature = compute_symbolic_signature(candidate)
        partitions[signature].append(candidate)
    
    # Return representative from largest partition
    largest_partition = max(partitions.values(), key=len)
    return select_representative(largest_partition)
```

### 2.3 CodeT-Style Generated Tests
**Source**: Chen et al., arXiv 2207.10397
**Gains**: HumanEval pass@1 47.0% → 65.8%

**Process**:
1. LLM generates test cases from problem specification
2. Execute all candidates against generated tests
3. Select candidate with highest pass rate
4. Training-free, works with any code model

---

## Phase 3: Width + Depth Integration

### 3.1 Hybrid Sampling Strategy
**Combine population (WIDTH) with Reflexion (DEPTH)**:

```
Problem → Population Spawn (N=8)
  ↓
[Trajectory 1] [Trajectory 2] ... [Trajectory 8]
  ↓              ↓                  ↓
Verify each → Score → Select top-K (K=3)
  ↓
Reflexion refinement on top-K
  ↓
Final verification → Best solution
```

**Key Insight**: Don't apply Reflexion blindly. Only refine trajectories that pass initial verification.

### 3.2 Diversity Operators
**Source**: SE-Agent (arXiv 2508.02085)

**Three operators for trajectory-level manipulation**:
1. **Revision**: Refine a single trajectory with feedback
2. **Recombination**: Merge successful steps from multiple trajectories
3. **Refinement**: Polish the selected solution

```typescript
interface DiversityOperator {
  revise(t: TrajectoryState, feedback: string): TrajectoryState;
  recombine(trajectories: TrajectoryState[]): TrajectoryState;
  refine(t: TrajectoryState): TrajectoryState;
}
```

---

## Phase 4: Advanced Selection Mechanisms

### 4.1 Cross-Provider Judge Debate
**Critical**: Avoid same-family bias (CW-POR, arXiv 2504.00374)

**Protocol**:
1. Generate candidates with Provider A (e.g., GPT-4)
2. Judge with Provider B (e.g., Claude)
3. If disagreement, add Provider C (e.g., Gemini) as tiebreaker

```typescript
async function judgeDebate(
  candidates: TrajectoryState[],
  generatorProvider: string
): Promise<TrajectoryState> {
  const judgeProviders = getAlternativeProviders(generatorProvider);
  
  const scores = await Promise.all(
    judgeProviders.map(p => scoreWithProvider(candidates, p))
  );
  
  // Aggregate scores across judges
  return selectByConsensus(candidates, scores);
}
```

### 4.2 Process-Level Scoring (Training-Free)
**Score intermediate steps, not just final output**:

```typescript
interface ProcessScore {
  stepScores: number[];        // Per-step quality
  executionResults: boolean[]; // Per-step execution success
  compositeScore: number;      // Weighted combination
}

function scoreProcess(trajectory: TrajectoryState): ProcessScore {
  const stepScores = trajectory.reasoning.map(step => 
    judgeStep(step, trajectory.aer)
  );
  
  const executionResults = trajectory.aer.events.map(e => 
    e.status === 'success'
  );
  
  // Combine: 70% execution, 30% judge
  const compositeScore = 
    0.7 * mean(executionResults) + 
    0.3 * mean(stepScores);
  
  return { stepScores, executionResults, compositeScore };
}
```

---

## Phase 5: Optimization & Efficiency

### 5.1 KV-Cache Reuse (Where Possible)
**Challenge**: Multi-provider setup limits KV-cache sharing
**Solution**: Prioritize same-provider diversity when latency-critical

```typescript
interface SamplingConfig {
  prioritizeLatency: boolean;
  
  // If true, use same provider with temp diversity
  // If false, use multi-provider for max diversity
}
```

### 5.2 Adaptive Population Size
**Don't always use N=8. Adapt based on task complexity**:

```typescript
function adaptivePopulationSize(problem: Problem): number {
  if (problem.hasTests) return 4;        // Tests provide strong signal
  if (problem.complexity === 'high') return 8;
  if (problem.complexity === 'low') return 2;
  return 4; // default
}
```

### 5.3 Early Stopping
**Stop generating trajectories once high-confidence solution found**:

```typescript
async function populationSample(
  problem: Problem,
  maxN: number
): Promise<TrajectoryState[]> {
  const trajectories: TrajectoryState[] = [];
  
  for (let i = 0; i < maxN; i++) {
    const t = await generateTrajectory(problem);
    trajectories.push(t);
    
    // Early stop if we have a verified solution
    if (await isVerified(t) && t.score > 0.95) {
      break;
    }
  }
  
  return trajectories;
}
```

---

## Phase 6: Benchmark-Specific Strategies

### 6.1 SWE-bench Pro
**Target**: +5 points over baseline OpenHands

**Strategy**:
- Population size: N=6
- Diversity: Multi-provider (GPT-4, Claude, Gemini)
- Verification: Test execution + symbolic equivalence
- Refinement: Reflexion on top-2 candidates

**Expected Gain**: 68.4% → 73.4%

### 6.2 AIME (Math Reasoning)
**Target**: +12% (ParaThinker benchmark)

**Strategy**:
- Population size: N=8
- Diversity: Temperature + prefix
- Verification: Symbolic equivalence + generated tests
- No Reflexion (math benefits from diversity more than refinement)

### 6.3 ARC-AGI-2
**Target**: 30%+ with frontier models

**Strategy**:
- Population size: N=10
- Diversity: Multi-provider + program synthesis
- Verification: Execution on test cases
- Refinement: Library-based approach (Pang et al.)

**Note**: If <30%, need program-synthesis-style search, not generic sampling

---

## Phase 7: Implementation Roadmap

### Sprint 1: Core Infrastructure (2 weeks)
- [ ] Implement `PopulationSpawnConfig`
- [ ] Extend HIR with `TrajectoryState` and `PopulationState`
- [ ] Build cross-trajectory checkpoint reuse
- [ ] Add diversity strategies (provider, temperature, prefix)

### Sprint 2: Verification System (2 weeks)
- [ ] Implement `HierarchicalSelector`
- [ ] Add test execution verifier
- [ ] Add symbolic equivalence partitioning
- [ ] Add CodeT-style generated tests

### Sprint 3: Width + Depth Integration (1 week)
- [ ] Combine population sampling with Reflexion
- [ ] Implement diversity operators (revision, recombination, refinement)
- [ ] Add adaptive population sizing

### Sprint 4: Advanced Selection (2 weeks)
- [ ] Implement cross-provider judge debate
- [ ] Add process-level scoring
- [ ] Build consensus aggregation

### Sprint 5: Optimization (1 week)
- [ ] Add early stopping
- [ ] Implement adaptive population size
- [ ] Optimize checkpoint sharing

### Sprint 6: Validation (2 weeks)
- [ ] Run SWE-bench Pro evaluation
- [ ] Run AIME evaluation
- [ ] Run ARC-AGI-2 evaluation
- [ ] Compare against baseline OpenHands

---

## Success Metrics

### Primary Metrics
- **SWE-bench Pro**: ≥5 point improvement over baseline
- **AIME**: ≥10% improvement over single-trajectory
- **ARC-AGI-2**: ≥30% with frontier models

### Secondary Metrics
- **Latency overhead**: <10% vs single-trajectory (with KV-cache reuse)
- **Token efficiency**: <8× tokens for N=8 population
- **Verification accuracy**: >90% agreement with ground truth

### Failure Signals
- If population mode doesn't lift SWE-bench Pro by ≥5 points → revisit diversity generation
- If multi-hop verification doesn't lift FRAMES/MuSiQue by ≥10 points → bottleneck is retriever, not harness
- If ARC-AGI-2 <30% → need program synthesis, not generic sampling

---

## Risk Mitigation

### Risk 1: Compute Cost
**Mitigation**: 
- Adaptive population sizing
- Early stopping
- Checkpoint reuse

### Risk 2: Self-Correction Degradation
**Finding**: Self-correction without external feedback can hurt (Huang et al., DeepMind 2023)
**Mitigation**: Only apply Reflexion after verification signal

### Risk 3: LLM Judge Bias
**Finding**: Same-family judges show self-preference (CW-POR)
**Mitigation**: Always use cross-provider judges

### Risk 4: Long-Context SC Degradation
**Finding**: 53/56 model-task pairs show no SC gain in long context (Byerly & Khashabi, TACL 2026)
**Mitigation**: Don't apply SC blindly to long-context tasks

### Risk 5: Benchmark Gaming
**Finding**: UC Berkeley RDI study found 100% exploit rate on major benchmarks
**Mitigation**: 
- Run real validation tasks
- Audit eval harness for prompt injection
- Use standardized scaffolds (vals.ai, official SWE-bench)

---

## Novel Contributions

### What Makes This Plan Unique
1. **First open harness with native population sampling**
   - OpenHands, SWE-agent, Aider, Agentless: all single-trajectory
   - Only Moatless has tree-search, none have GRAM-style selection

2. **Training-free end-to-end**
   - No model fine-tuning
   - No PRM training
   - Pure harness-level improvements

3. **Verifier hierarchy**
   - Execution > symbolic > generated tests > consensus > judge
   - Adaptive routing based on task type

4. **Cross-trajectory checkpoint reuse**
   - Harness analogue of ParaThinker's KV-cache reuse
   - Reduces redundant computation

---

## References

### Key Papers
- **ParaThinker** (Wen et al., arXiv 2509.04475): +12.3% AIME with 8 parallel paths
- **A2R** (Wang et al., arXiv 2509.22044): +75% relative gain with synthesizer
- **SE-Agent** (arXiv 2508.02085): Trajectory revision/recombination/refinement
- **Symbolic Equivalence** (Cho et al., arXiv 2604.06485): HumanEval+ 0.728 → 0.803
- **CodeT** (Chen et al., arXiv 2207.10397): HumanEval 47.0% → 65.8%
- **CW-POR** (arXiv 2504.00374): LLM judge bias documentation
- **Free Process Rewards** (Yuan et al., arXiv 2412.01981): Implicit PRM from outcome labels

### Benchmarks
- **SWE-bench Pro**: Clean alternative to contaminated SWE-bench Verified
- **AIME**: Math reasoning benchmark
- **ARC-AGI-2**: Abstract reasoning benchmark
- **HumanEval+**: Code generation benchmark
- **LiveCodeBench**: Live code generation benchmark

---

## Next Steps

1. **Review this plan** with the Lyra team
2. **Prioritize sprints** based on resource availability
3. **Set up evaluation infrastructure** (SWE-bench Pro, AIME, ARC-AGI-2)
4. **Start Sprint 1**: Core population infrastructure
5. **Establish baseline metrics** before any changes

---

## Appendix: Code Snippets

### A.1 Population Spawn Example
```typescript
// Usage example
const result = await lyra.populationSpawn({
  problem: "Fix the authentication bug in auth.ts",
  n: 6,
  diversityStrategy: 'hybrid',
  shareCheckpoint: 'project-setup'
});

// Returns PopulationState with 6 trajectories
console.log(result.trajectories.length); // 6
```

### A.2 Hierarchical Selection Example
```typescript
const selector = new HierarchicalSelector();
const best = await selector.selectBest(population.trajectories);

console.log(best.score); // 0.92
console.log(best.verificationResults); // [{ type: 'test', passed: true }, ...]
```

### A.3 Diversity Operator Example
```typescript
const operator = new DiversityOperator();

// Revise with feedback
const revised = operator.revise(trajectory, "Add error handling");

// Recombine top-3
const combined = operator.recombine(topTrajectories.slice(0, 3));

// Refine final solution
const polished = operator.refine(combined);
```

---

**End of Lyra Ultra Plan**
