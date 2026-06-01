# Lyra Upgrade — Comprehensive Test Plan

**Version**: 1.0  
**Date**: 2026-05-31  
**Status**: Ready for Execution  
**Test Environment**: DeepSeek API (from `~/.claude/settings.json`)

---

## Executive Summary

This test plan provides comprehensive coverage for all research and workflow capabilities in the Lyra upgrade project. It covers:

- **Deep Research**: Multi-hop research, adversarial hypothesis testing, citation tracking
- **Auto Research**: Autonomous research loops with adaptive depth
- **Scientist Research**: Self-organizing research teams (AutoScientists pattern)
- **Workflow Orchestration**: Dynamic workflows, fan-out coordination, resumable long runs
- **Integration Tests**: Memory + Router, Skills + Swarm, Voice + Agent interaction
- **Performance Benchmarks**: SWE-bench, τ-bench, GAIA, Terminal-Bench, custom Lyra benchmarks

**Execution Strategy**:
- **Automated tests**: 70% (unit, integration, performance)
- **Manual tests**: 30% (UX, edge cases, adversarial scenarios)
- **Test execution**: Continuous (CI/CD) + milestone-based (pre-release)
- **Pass criteria**: 80%+ automated pass rate, zero critical failures

---

## Test Environment Setup

### Prerequisites

1. **API Keys** (from `~/.claude/settings.json`):
   ```json
   {
     "DEEPSEEK_API_KEY": "sk-...",
     "ANTHROPIC_API_KEY": "sk-ant-...",
     "OPENAI_API_KEY": "sk-..."
   }
   ```

2. **Test Data**:
   - Research queries corpus: `test/fixtures/research-queries.json`
   - Expected outputs: `test/fixtures/expected-outputs/`
   - Benchmark datasets: `test/benchmarks/`

3. **Infrastructure**:
   - Local SQLite for memory tests
   - Redis for shared context tests (optional)
   - File system for artifact storage

### Test Execution Commands

```bash
# Run all tests
npm test

# Run specific test suites
npm test -- --grep "Deep Research"
npm test -- --grep "Auto Research"
npm test -- --grep "Scientist Research"
npm test -- --grep "Workflow"

# Run with coverage
npm test -- --coverage

# Run benchmarks
npm run benchmark
```

---

## Test Categories

### 1. Deep Research Tests

Deep research capabilities test multi-hop queries, adversarial hypothesis testing, and citation tracking.

#### Test 1.1: Multi-Hop Research Query

**Objective**: Verify Lyra can follow citation chains across multiple sources.

**Input**:
```json
{
  "query": "What are the latest advances in agent memory architectures from ICLR 2026?",
  "depth": "complex",
  "expectedHops": 3
}
```

**Expected Output**:
- Finds ICLR 2026 MemAgent workshop papers
- Follows citations to related work
- Synthesizes findings across ≥3 papers
- Provides citation graph showing relationships

**Pass Criteria**:
- ✅ Retrieves ≥5 relevant papers
- ✅ Citation chain depth ≥3 hops
- ✅ All citations properly formatted
- ✅ Synthesis coherent and accurate
- ✅ Confidence score ≥0.8

**Edge Cases**:
- Dead links (404 errors)
- Paywalled papers
- Conflicting information across sources

---

#### Test 1.2: Adversarial Hypothesis Testing

**Objective**: Verify competing hypotheses are generated and tested adversarially.

**Input**:
```json
{
  "query": "What is the best memory architecture for long-term agent memory?",
  "complexity": "complex",
  "enableAdversarial": true
}
```

**Expected Output**:
- Generates 3+ competing hypotheses
- Each hypothesis has supporting evidence
- Adversarial critic attacks each hypothesis
- Socratic refinement of weak hypotheses
- Convergence on strongest hypothesis

**Pass Criteria**:
- ✅ ≥3 hypotheses generated
- ✅ Each hypothesis has ≥3 evidence items
- ✅ Adversarial critiques identify weaknesses
- ✅ Final hypothesis has highest evidence/critique ratio
- ✅ Mind-Map graph shows hypothesis evolution

**Edge Cases**:
- Tie between hypotheses (equal evidence)
- No convergence after max iterations
- All hypotheses equally weak

---

#### Test 1.3: Citation Tracking and Provenance

**Objective**: Verify all claims are properly cited with provenance.

**Input**:
```json
{
  "query": "Summarize the A-MAC memory admission control paper",
  "requireCitations": true
}
```

**Expected Output**:
- Summary with inline citations
- Citation list with URLs
- Provenance metadata (retrieval method, timestamp)

**Pass Criteria**:
- ✅ Every factual claim has citation
- ✅ Citations link to correct sources
- ✅ Provenance metadata complete
- ✅ No hallucinated citations

**Edge Cases**:
- Source unavailable during verification
- Multiple sources for same claim
- Conflicting information across sources

---

#### Test 1.4: Iterative Research with Adaptive Depth

**Objective**: Verify research depth adapts to query complexity.

**Test Cases**:

| Query Complexity | Expected Iterations | Max Cost |
|------------------|---------------------|----------|
| Simple: "What is Lyra?" | 1 | $0.10 |
| Medium: "Compare Lyra vs Claude Code" | 2-3 | $0.50 |
| Complex: "Design breakthrough memory architecture" | 5-10+ | $5.00 |

**Pass Criteria**:
- ✅ Simple queries complete in 1 iteration
- ✅ Complex queries run ≥5 iterations
- ✅ Diminishing returns detection works (<10% new info stops)
- ✅ Cost stays within budget

**Edge Cases**:
- Query misclassified (simple marked as complex)
- Infinite loop (never reaches diminishing returns)
- Early stop (stops before sufficient depth)

---

### 2. Auto Research Tests

Autonomous research loops with self-directed exploration.

#### Test 2.1: Autonomous Research Loop

**Objective**: Verify Lyra can conduct research autonomously without human intervention.

**Input**:
```json
{
  "query": "Research the latest agent swarm coordination patterns",
  "autonomyLevel": "conditional",
  "maxIterations": 5,
  "budget": 2.00
}
```

**Expected Output**:
- Autonomous query refinement
- Self-directed source discovery
- Automatic assumption making (documented)
- Progress reports at each iteration
- Final report with confidence scores

**Pass Criteria**:
- ✅ Completes without human intervention
- ✅ Makes reasonable assumptions (confidence ≥0.7)
- ✅ Documents all assumptions
- ✅ Stays within budget
- ✅ Final report quality ≥0.8

**Edge Cases**:
- Ambiguous query (requires clarification)
- No sources found
- Budget exhausted mid-research
- Conflicting assumptions

---

#### Test 2.2: Error Recovery in Auto Research

**Objective**: Verify autonomous error recovery without escalation.

**Test Scenarios**:

1. **API Rate Limit**:
   - Input: Trigger rate limit during research
   - Expected: Automatic backoff and retry
   - Pass: Recovers within 3 retries

2. **Source Unavailable**:
   - Input: Primary source returns 404
   - Expected: Finds alternative sources
   - Pass: Continues research with alternatives

3. **Parsing Failure**:
   - Input: Malformed response from source
   - Expected: Skips source, logs error
   - Pass: Completes research with remaining sources

**Pass Criteria**:
- ✅ 80%+ automatic recovery rate
- ✅ No cascading failures
- ✅ Escalates only critical errors
- ✅ All errors logged with context

---

#### Test 2.3: Autonomous Clarification

**Objective**: Verify Lyra makes reasonable assumptions for ambiguous queries.

**Input**:
```json
{
  "query": "Research memory systems",
  "autonomyLevel": "conditional",
  "assumptionMode": "reasonable"
}
```

**Expected Output**:
- Detects ambiguity ("memory systems" = agent memory? computer memory? human memory?)
- Makes reasonable assumption (agent memory, given context)
- Documents assumption with reasoning
- Proceeds with research

**Pass Criteria**:
- ✅ Ambiguity detected
- ✅ Assumption documented
- ✅ Assumption reasonable (validated post-hoc)
- ✅ Research quality not degraded

**Edge Cases**:
- Multiple valid interpretations
- Assumption turns out wrong
- User provides clarification mid-research

---

### 3. Scientist Research Tests

Self-organizing research teams (AutoScientists pattern).

#### Test 3.1: Self-Organizing Research Team

**Objective**: Verify agents self-organize into research teams.

**Input**:
```json
{
  "query": "Design a breakthrough context optimization system",
  "teamSize": 3,
  "roles": ["hypothesis-generator", "evidence-gatherer", "critic"]
}
```

**Expected Output**:
- 3 agents spawn automatically
- Each agent takes a role
- Agents coordinate via shared memory
- Shared success/failure log
- Convergence on solution

**Pass Criteria**:
- ✅ Team forms automatically
- ✅ Roles assigned correctly
- ✅ Coordination via shared memory works
- ✅ No duplicate work
- ✅ Convergence within 10 iterations

**Edge Cases**:
- Agent failure mid-research
- Coordination deadlock
- No convergence (agents disagree)

---

#### Test 3.2: Shared Success/Failure Log

**Objective**: Verify agents learn from shared experience.

**Input**:
```json
{
  "query": "Optimize memory retrieval latency",
  "teamSize": 3,
  "enableSharedLog": true
}
```

**Expected Output**:
- Agents log successes and failures
- Agents read log before attempting strategies
- No redundant failed strategies
- Faster convergence than without log

**Pass Criteria**:
- ✅ All outcomes logged
- ✅ Agents check log before acting
- ✅ Zero redundant failures
- ✅ 30%+ faster convergence vs no-log baseline

**Edge Cases**:
- Log corruption
- Conflicting log entries
- Log grows unbounded

---

#### Test 3.3: Adversarial Critique Before Execution

**Objective**: Verify critic agents review proposals before execution.

**Input**:
```json
{
  "query": "Implement a new memory compression algorithm",
  "enableAdversarial": true,
  "criticsCount": 4
}
```

**Expected Output**:
- Proposer agent suggests implementation
- 4 critics review (security, performance, correctness, cost)
- Consensus required for approval
- Rejected proposals revised

**Pass Criteria**:
- ✅ All proposals reviewed by 4 critics
- ✅ High-risk proposals blocked
- ✅ Approved proposals have ≥75% consensus
- ✅ Revision loop works (proposer addresses critiques)

**Edge Cases**:
- Critics disagree (2 approve, 2 reject)
- All critics reject
- Proposer cannot address critiques

---

### 4. Workflow Orchestration Tests

Dynamic workflows with fan-out coordination and resumable long runs.

#### Test 4.1: Dynamic Workflow Fan-Out

**Objective**: Verify Lyra can spawn parallel agents dynamically.

**Input**:
```json
{
  "task": "Analyze codebase for security vulnerabilities",
  "workflow": "dynamic",
  "maxAgents": 10
}
```

**Expected Output**:
- Orchestrator analyzes task
- Spawns N agents (1 per file/module)
- Agents work in parallel
- Results aggregated by orchestrator

**Pass Criteria**:
- ✅ Correct number of agents spawned
- ✅ No duplicate work
- ✅ Parallel execution (not sequential)
- ✅ Results properly aggregated
- ✅ Completion time <50% of sequential baseline

**Edge Cases**:
- Agent limit reached (maxAgents)
- Agent failure mid-execution
- Aggregation conflicts

---

#### Test 4.2: Resumable Long Runs

**Objective**: Verify workflows can pause and resume.

**Test Scenario**:
1. Start long-running workflow (expected 30+ minutes)
2. Interrupt after 10 minutes
3. Resume from checkpoint
4. Verify no duplicate work

**Pass Criteria**:
- ✅ Checkpoint saved correctly
- ✅ Resume from exact point
- ✅ No duplicate work after resume
- ✅ Final result identical to uninterrupted run

**Edge Cases**:
- Checkpoint corruption
- State changed between pause/resume
- Multiple resume attempts

---

#### Test 4.3: Code-Driven Workflow Execution

**Objective**: Verify workflows defined in code (not orchestrator messages).

**Input**:
```javascript
// workflow.js
module.exports = {
  name: "security-audit",
  steps: [
    { agent: "scanner", task: "scan-dependencies" },
    { agent: "analyzer", task: "analyze-code", dependsOn: ["scanner"] },
    { agent: "reporter", task: "generate-report", dependsOn: ["analyzer"] }
  ]
};
```

**Expected Output**:
- Workflow executes in correct order
- Dependencies respected
- No orchestrator message overhead

**Pass Criteria**:
- ✅ Steps execute in dependency order
- ✅ Parallel steps run concurrently
- ✅ 50%+ token reduction vs message-based orchestration

**Edge Cases**:
- Circular dependencies
- Missing dependency
- Step failure mid-workflow

---

#### Test 4.4: Adversarial Verification Loop

**Objective**: Verify multiple agents attack solution until convergence.

**Input**:
```json
{
  "task": "Design API authentication system",
  "workflow": "adversarial",
  "convergenceThreshold": 0.9
}
```

**Expected Output**:
- Proposer designs system
- Attackers find vulnerabilities
- Proposer fixes vulnerabilities
- Loop continues until convergence (no new vulnerabilities)

**Pass Criteria**:
- ✅ ≥3 attack rounds
- ✅ Vulnerabilities decrease each round
- ✅ Convergence reached (confidence ≥0.9)
- ✅ Final design passes security review

**Edge Cases**:
- No convergence (always finding new issues)
- False positives from attackers
- Proposer cannot fix vulnerabilities

---

### 5. Integration Tests

Cross-workstream integration tests.

#### Test 5.1: Memory + Router Integration

**Objective**: Verify memory-augmented routing reduces cost.

**Test Scenario**:
1. Run 100 queries (40 exact repeats, 40 similar, 20 novel)
2. Measure cost with and without memory

**Expected Results**:

| Query Type | Without Memory | With Memory | Savings |
|------------|----------------|-------------|---------|
| Exact repeat | $1.00 | $0.00 | 100% |
| Similar | $1.00 | $0.10 | 90% |
| Novel | $1.00 | $1.00 | 0% |
| **Overall** | **$100** | **$52** | **48%** |

**Pass Criteria**:
- ✅ Exact matches cost $0 (cached)
- ✅ Similar queries use cheap model
- ✅ Overall cost reduction ≥40%
- ✅ Quality maintained (≥95% accuracy)

**Edge Cases**:
- Cache miss (should have hit)
- Cache hit (should have missed)
- Memory corruption

---

#### Test 5.2: Skills + Swarm Coordination

**Objective**: Verify skills work correctly in multi-agent swarm.

**Input**:
```json
{
  "task": "Refactor authentication module",
  "agents": [
    { "role": "analyzer", "skill": "code-review" },
    { "role": "refactorer", "skill": "refactor-clean" },
    { "role": "tester", "skill": "tdd-guide" }
  ]
}
```

**Expected Output**:
- Each agent loads correct skill
- Skills execute in agent context
- Agents coordinate via shared memory
- Final result passes all tests

**Pass Criteria**:
- ✅ All skills loaded correctly
- ✅ No skill conflicts
- ✅ Coordination works
- ✅ Final code quality ≥0.9

**Edge Cases**:
- Skill not found
- Skill version mismatch
- Skill dependency conflict

---

#### Test 5.3: Voice + Agent Interaction

**Objective**: Verify voice mode works with agent workflows.

**Test Scenario**:
1. User speaks: "Research agent memory architectures"
2. Lyra transcribes (STT)
3. Research agent executes
4. Lyra reads back summary (TTS)

**Pass Criteria**:
- ✅ STT accuracy ≥95% (WER <5%)
- ✅ Agent executes correctly
- ✅ TTS quality ≥4/5 (MOS score)
- ✅ End-to-end latency <5 seconds

**Edge Cases**:
- Background noise during STT
- User interrupts TTS
- Agent takes >30 seconds (long response)

---

