# Multi-Agent System Tradeoffs

**Version:** 1.0  
**Date:** 2026-06-02  
**Status:** Production

---

## Executive Summary

This document analyzes the design decisions, alternatives considered, performance implications, cost considerations, and maintenance trade-offs for Lyra's multi-agent system.

---

## Table of Contents

1. [Design Decisions](#design-decisions)
2. [Alternatives Considered](#alternatives-considered)
3. [Performance Implications](#performance-implications)
4. [Cost Analysis](#cost-analysis)
5. [Maintenance Considerations](#maintenance-considerations)

---

## Design Decisions

### 1. Decentralized Coordination

**Decision:** Agents self-organize through shared state rather than central planner.

**Rationale:**
- Eliminates single point of failure
- Reduces coordination overhead
- Scales better with agent count
- Matches biological swarm behavior

**Trade-offs:**

| Advantage | Disadvantage |
|-----------|--------------|
| Better fault tolerance | Harder to debug |
| Natural load balancing | Potential race conditions |
| Emergent intelligence | Less predictable behavior |
| Horizontal scaling | Requires sophisticated state management |

**Why This Approach:**
Central planners become bottlenecks at >20 agents. Decentralized coordination showed 3× better throughput in AutoScientists paper.

---

### 2. Git Worktree Isolation

**Decision:** Each subagent runs in isolated git worktree.

**Rationale:**
- True filesystem isolation
- Native git merge strategies
- Clean rollback on failure
- Parallel work without conflicts

**Trade-offs:**

| Advantage | Disadvantage |
|-----------|--------------|
| Proven merge strategies | Worktree creation latency (~200ms) |
| Natural parallel execution | Requires git-aware tooling |
| Easy cleanup | Additional I/O overhead |

**Alternatives Rejected:**
- **Docker containers**: Too heavy (300-500ms startup)
- **Chroot jails**: Linux-only, no merge semantics
- **Virtual environments**: Insufficient isolation
- **Namespace-based**: Complex to implement, no native merge

**Why This Approach:**
Git worktrees provide the right balance of isolation, performance, and merge capabilities. The 200ms overhead is acceptable given the typical subagent task duration (10-300s).

---

### 3. SQLite + Redis Hybrid State

**Decision:** SQLite for persistent state, Redis for ephemeral caching.

**Rationale:**
- SQLite: ACID guarantees, zero setup, embedded
- Redis: Sub-millisecond access, pub/sub for events

**Trade-offs:**

| Advantage | Disadvantage |
|-----------|--------------|
| SQLite embedded (no server) | SQLite limited concurrency (<100 writers/s) |
| Redis extremely fast (<1ms) | Redis requires separate process |
| Clear separation of concerns | Consistency challenges between layers |
| Proven reliability | Cache invalidation complexity |

**Performance Data:**

```
Operation              SQLite    Redis    
-----------------------------------------
Read (hot)             0.05ms    0.02ms   
Write (single)         0.8ms     0.03ms   
Write (batch 100)      15ms      2ms      
Range query           2ms       1.5ms    
Transaction           5ms       N/A      
```

**Why This Approach:**
SQLite handles persistence with strong consistency. Redis handles hot paths (team queues, agent status). Together they provide <10ms p99 latency for state operations.

**Alternatives Rejected:**
- **PostgreSQL**: Overkill for local deployment, requires server
- **Redis-only**: No durability guarantees
- **MongoDB**: Too heavy, complex consistency model

---

### 4. Evidence-Based Validation

**Decision:** Require evidence before proposal execution.

**Rationale:**
- Prevents wasted compute on low-quality ideas
- Adversarial validation catches flaws early
- Statistical validation (effect size, CI) ensures significance

**Trade-offs:**

| Advantage | Disadvantage |
|-----------|--------------|
| 30-50% reduction in failed experiments | Added latency per proposal (~2-5s) |
| Higher quality solutions | Risk of false negatives |

**Why This Approach:**
AutoScientists demonstrated 40% reduction in failed experiments with critique-before-execution. The 2-5s validation cost is negligible compared to typical experiment duration (30-600s).

---

### 5. Dynamic Team Formation

**Decision:** Teams form around hypotheses and reorganize when stagnated.

**Rationale:**
- Focuses effort on promising directions
- Prevents teams from getting stuck in local minima
- Allows exploration of multiple approaches in parallel

**Trade-offs:**

| Advantage | Disadvantage |
|-----------|--------------|
| Adaptive resource allocation | Team formation overhead (~3-5s) |
| Automatic exploration-exploitation balance | Context loss during reorganization |
| Resilient to dead-ends | Tuning stagnation thresholds is tricky |
| Cross-pollination of ideas | Potential premature reorganization |

**Stagnation Detection Thresholds:**

```python
# Conservative: Fewer false positives
STAGNATION_THRESHOLD = 0.8  # 80% failure rate
LOOKBACK_WINDOW = 15

# Aggressive: Faster exploration
STAGNATION_THRESHOLD = 0.6  # 60% failure rate
LOOKBACK_WINDOW = 10
```

**Why This Approach:**
Fixed teams get stuck; dynamic teams show 1.5-2× faster convergence in AutoScientists evaluation.

---

## Alternatives Considered

### Central Planning vs Decentralized

**Rejected: Central Task Queue**

```python
# Centralized approach (rejected)
class CentralPlanner:
    def assign_task(self) -> Tuple[Agent, Task]:
        available_agents = [a for a in agents if a.idle]
        best_agent = max(available_agents, 
                        key=lambda a: compute_score(a, task))
        return best_agent, task
```

**Problems:**
- Planner becomes bottleneck at >20 agents
- Single point of failure
- Global optimization is NP-hard

**Chosen: Self-Claiming**

```python
# Decentralized approach (chosen)
class Agent:
    async def claim_task(self):
        tasks = state.get_available_tasks()
        best_match = max(tasks, key=lambda t: self.match_score(t))
        if self.match_score(best_match) > THRESHOLD:
            state.claim(self, best_match)
```

**Benefits:**
- No central bottleneck
- Agents make local decisions
- Natural load balancing

---

### LangGraph vs Custom Orchestration

**Rejected: Custom State Machine**

Building custom orchestration from scratch would require:
- State transition logic (~500 LOC)
- Persistence layer (~300 LOC)
- Error handling and recovery (~200 LOC)
- Debugging and visualization (~400 LOC)

**Chosen: LangGraph**

Provides out-of-the-box:
- Declarative state machine definition
- Built-in persistence
- Visualization tools (LangSmith)
- Active community and examples

**Trade-off:** Dependency on external framework vs implementation flexibility. We chose standardization and velocity.

---

## Performance Implications

### Latency Breakdown

End-to-end task execution latency:

```
Component                     Latency    % of Total
-------------------------------------------------------
Task discovery               5-10ms      <1%
Capability matching          10-20ms     1%
State synchronization        20-50ms     2-3%
Worktree allocation         200-300ms    10-15%
Agent execution (model)      5-20s       80-90%
Result logging               50-100ms     2-3%
Merge back to session        100-200ms    3-5%
-------------------------------------------------------
Total (typical)              ~10-25s     100%
```

**Bottleneck:** LLM inference dominates. Parallelism provides the only meaningful speedup.

### Throughput Analysis

**Single-Agent Baseline:**
- Tasks/hour: 120-180 (sequential)
- Parallelism: None
- Utilization: 100% (saturated)

**Multi-Agent (10 agents):**
- Tasks/hour: 600-900 (5-6× improvement)
- Parallelism: 5-8× (not perfect due to coordination overhead)
- Utilization: 60-80% (some idle time during synchronization)

**Multi-Agent (20 agents):**
- Tasks/hour: 1000-1400 (8-11× improvement)
- Parallelism: 8-12× 
- Utilization: 50-70% (diminishing returns due to coordination)

**Saturation Point:** ~30-40 agents before coordination overhead dominates.

---

## Cost Analysis

### Infrastructure Costs

**Compute (AWS us-east-1 pricing):**

```
Component          Type             Monthly Cost (20 agents)
------------------------------------------------------------
Coordinator        c6i.2xlarge      $245
Agent workers      c6i.xlarge×4     $490
Redis              r6g.large        $122
Storage (SSD)      500GB gp3        $40
Data transfer      100GB/month      $9
------------------------------------------------------------
Total                               ~$906/month
```

**LLM API Costs (assuming GPT-4 pricing):**

```
Usage Pattern              Cost/1M tokens    Monthly (est)
------------------------------------------------------------
Input (prompts)            $10               $2,000
Output (responses)         $30               $1,500
Total LLM costs                              $3,500/month
------------------------------------------------------------
Grand total infrastructure + LLM:            $4,406/month
```

### Cost Optimization Strategies

1. **Model Routing:**
   - Fast slot (deepseek-v4-flash): $0.60/1M tokens
   - Smart slot (deepseek-v4-pro): $2.40/1M tokens
   - Route 80% to fast slot → 75% cost savings

   - Group similar tasks → single model call
   - 30-40% reduction in API calls

3. **Caching:**
   - Cache embeddings and common prompts
   - 20-30% hit rate → 20% cost reduction

**Optimized Monthly Cost:** ~$1,500-2,000 (50-60% savings)

---

## Maintenance Considerations

### Operational Complexity

**Components to Monitor:**
- Agent health and utilization
- State synchronization lag
- Worktree cleanup (prevent disk exhaustion)
- Redis memory usage
- SQLite lock contention
- Team stagnation rates
- Convergence metrics

**Maintenance Overhead:**

| Task | Frequency | Effort |
|------|-----------|--------|
| Monitor dashboards | Daily | 15 min |
| Review failed experiments | Weekly | 1 hour |
| Tune stagnation thresholds | Monthly | 2 hours |
| Update agent capabilities | As needed | 30 min |
| Clean up stale worktrees | Weekly | 10 min (automated) |
| Database maintenance | Monthly | 30 min |

### Debugging Difficulty

**Challenges:**
- Distributed execution makes root cause analysis harder
- Race conditions in shared state
- Emergent behaviors difficult to predict
- Large trace volumes (10-20 agents × traces)

**Mitigation:**
- Comprehensive tracing (OpenTelemetry)
- Deterministic replay from state snapshots
- Agent-level logging with correlation IDs
- Trace visualization tools (Jaeger, LangSmith)

### Technical Debt

**Areas of Concern:**
1. **State consistency:** As agents scale, more sophisticated locking needed
2. **Worktree cleanup:** Manual cleanup if automated fails
3. **Agent specialization:** Generic agents vs specialized (ongoing tuning)
4. **Convergence criteria:** Domain-specific thresholds need empirical tuning

---

## Key Recommendations

### When to Use Multi-Agent

✅ **Good fit:**
- Tasks with natural parallelism (code analysis, testing, research)
- Long-running workflows (hours to days)
- Exploratory work (multiple approaches)
- High-value tasks justifying coordination overhead

❌ **Poor fit:**
- Simple sequential tasks
- Latency-critical operations (<1s requirement)
- Deterministic workflows
- Single-step operations

### Scaling Guidelines

| Agent Count | Use Case | Coordination Overhead |
|-------------|----------|----------------------|
| 1-5 agents | Small teams, simple tasks | Minimal (<5%) |
| 5-15 agents | Standard workflows | Moderate (10-15%) |
| 15-30 agents | Large research tasks | Significant (20-30%) |
| 30+ agents | Distributed systems | High (>30%, diminishing returns) |

---

## Related Documentation

- [Architecture](./architecture.md) - System overview
- [System Design](./system-design.md) - Implementation details
- [Implementation](./implementation.md) - Code examples
- [Evaluation](./evaluation.md) - Performance metrics

---

**Version:** 1.0  
**Last Updated:** 2026-06-02



