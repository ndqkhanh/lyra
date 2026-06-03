# Agent Loop Architecture Tradeoffs

**Block:** 01 — Agent Loop  
**Status:** Production  
**Version:** 2.7.1

---

## Overview

This document explains the key design decisions in the agent loop architecture, the alternatives considered, and the rationale for each choice. Every tradeoff involves tension between competing values: simplicity vs flexibility, performance vs observability, safety vs autonomy.

## Core Design Decisions

### 1. Small Kernel Philosophy

**Decision:** Keep the core loop under 200 lines

**Rationale:**

- **Reviewability:** A human can hold the entire execution model in their head
- **Debuggability:** Fewer paths through the code mean fewer failure modes
- **Testability:** Small surface area enables exhaustive branch coverage
- **Maintainability:** Changes have bounded blast radius

**Alternatives Considered:**

1. **Monolithic loop with all features inline**
   - Would grow to 2000+ lines with hooks, safety, verification
   - Multiple maintainers would conflict on changes
   - Testing would require complex mocking

2. **Microkernel with everything as extensions**
   - Would add indirection and dynamic loading complexity
   - Performance overhead from plugin boundaries
   - Harder to reason about control flow

**Tradeoff:**

| Aspect | Gain | Cost |
|--------|------|------|
| **Simplicity** | ✅ Single file to review | ❌ Must coordinate with 6+ integration points |
| **Performance** | ✅ Direct calls, no indirection | ❌ Can't optimize cross-boundary patterns |
| **Extensibility** | ❌ New features must be designed carefully | ✅ Forces clean abstractions |
| **Testing** | ✅ 100% branch coverage achievable | ❌ Integration tests span multiple packages |

**Why This Wins:**

The gains in cognitive load reduction outweigh the coordination cost. The loop runs millions of times per day across all sessions — keeping it simple prevents subtle bugs from accumulating.

---

### 2. Sequential Tool Execution

**Decision:** Execute tool calls one at a time, in order

**Rationale:**

- **Determinism:** Tool call order is reproducible in traces
- **Causality:** Later tool calls can depend on earlier results
- **Observation attribution:** Clear mapping between call and result
- **Safety:** Easier to halt execution mid-batch on violation

**Alternatives Considered:**

1. **Parallel tool execution**
   - Would improve latency for independent calls
   - Requires dependency analysis to preserve causality
   - Race conditions between file operations
   - Complex error handling (partial success scenarios)

2. **Batched execution with dependency graph**
   - Would enable optimal parallelism
   - Requires static analysis of tool parameters
   - Models don't reliably annotate dependencies
   - Much higher implementation complexity

**Tradeoff:**

| Aspect | Sequential | Parallel | Batched DAG |
|--------|-----------|----------|-------------|
| **Latency** | ❌ Sum of all tools | ✅ Max of any tool | ✅ Critical path only |
| **Throughput** | ❌ Bound by serial | ✅ Limited by cores | ✅ Near-optimal |
| **Complexity** | ✅ 50 LOC | ❌ 300 LOC | ❌ 800+ LOC |
| **Safety** | ✅ Easy to abort | ⚠️ Partial state issues | ⚠️ Rollback complexity |
| **Debuggability** | ✅ Linear trace | ❌ Interleaved events | ❌ DAG visualization needed |

**Why This Wins:**

Most tool calls are fast (<100ms). The median turn has 2-3 tool calls, making parallel overhead not worth the complexity. For heavy parallelism, use fleet orchestration at a higher level.

---

### 3. Observation Reduction

**Decision:** Truncate large tool outputs and offload to artifacts

**Rationale:**

- **Context management:** Raw outputs blow out transcript size
- **Cost control:** Reduces input tokens on every subsequent turn
- **Memory efficiency:** Keeps in-memory transcript bounded
- **Semantic focus:** Full output rarely needed by the model

**Alternatives Considered:**

1. **Always include full output**
   - Would exhaust context window in 10-20 turns
   - High cost (every turn pays for all previous outputs)
   - Models rarely use beyond first/last 100 lines

2. **Semantic summarization via LLM**
   - Would add LLM call per tool output
   - Latency increase (200-500ms per tool)
   - Risk of lossy summarization (key details dropped)
   - Cost multiplier: 2-3x per session

**Tradeoff:**

| Strategy | Cost | Latency | Fidelity | Complexity |
|----------|------|---------|----------|------------|
| **Full output** | ❌ 10x tokens | ✅ No overhead | ✅ Perfect | ✅ Trivial |
| **Truncate + offload** | ✅ ~2x tokens | ✅ <10ms | ⚠️ Lossy edges | ✅ Simple |
| **LLM summarization** | ❌ 3x tokens | ❌ 300ms | ⚠️ Unpredictable | ❌ Complex |

**Why This Wins:**

Truncation with head + tail + middle-elided marker gives the model enough context to decide if full content is needed. The `View` tool fetches artifacts on demand. This balances cost, latency, and fidelity without LLM overhead.

**Current Heuristics:**

```python
# Observation reduction thresholds
MAX_OBSERVATION_TOKENS = 2000
HEAD_LINES = 50
TAIL_LINES = 20

# Reduction by type
LONG_TEXT: head + tail + "... middle elided ..."
BINARY: byte_count + MIME + hash_reference
ERROR_TRACE: top_N_frames + file:line anchors
GIT_DIFF: summary + file_list + first_N_hunks
TEST_OUTPUT: pass/fail + first_failure_block
```

---

### 4. Compaction Trigger at 85%

**Decision:** Trigger context compaction at 85% of max tokens

**Rationale:**

- **Safety margin:** 15% buffer prevents hard context exhaustion
- **Amortization:** Compaction cost (~500ms) amortized over multiple steps
- **Retention:** Preserves 3-5 recent turns after compaction
- **User experience:** Rarely interrupts mid-thought

**Alternatives Considered:**

1. **Hard limit at 100%**
   - Would cause mid-turn failures
   - No room for model to finish response
   - Poor UX (abrupt termination)

2. **Eager compaction at 50%**
   - Would compact too frequently
   - Higher latency (more LLM calls for summarization)
   - Loss of context that model still actively uses

3. **Dynamic threshold based on task**
   - Would require task classification
   - More complex heuristics
   - Risk of miscalibration

**Tradeoff:**

| Threshold | Compaction Frequency | Context Retention | Failure Risk |
|-----------|---------------------|-------------------|--------------|
| **50%** | ❌ Every 10 steps | ✅ High | ✅ Very low |
| **70%** | ⚠️ Every 20 steps | ✅ Medium-high | ✅ Low |
| **85%** | ✅ Every 40 steps | ⚠️ Medium | ✅ Low |
| **95%** | ✅ Every 80 steps | ❌ Low | ❌ High |
| **100%** | ✅ Rare | ❌ None | ❌ Guaranteed failure |

**Why This Wins:**

85% hits the sweet spot: compact infrequently enough to avoid latency spikes, but early enough to preserve working context. Empirically, 3-5 recent turns is sufficient for most tasks.

---

### 5. Repeat Detection with Bloom Filter

**Decision:** Use bloom filter with recency weighting to detect repeat tool calls

**Rationale:**

- **Space efficiency:** O(1) memory per call (vs O(N) for exact set)
- **False positives acceptable:** Over-suppression is safe; under-suppression is dangerous
- **Recency bias:** Recent repeats matter more than distant ones
- **Tunable threshold:** 3 repeats in 16-call window catches pathology without over-triggering

**Alternatives Considered:**

1. **Exact set tracking**
   - Would guarantee no false positives
   - O(N) memory grows unbounded
   - Hash collisions on complex args

2. **No repeat detection**
   - Would allow infinite loops
   - Models reliably fall into "read same file forever" pattern
   - Session costs spiral

3. **Static threshold (e.g., "never repeat")**
   - Too aggressive: legitimate retries blocked
   - Models often need 2-3 attempts to fix issues
   - Poor UX (false blocks)

**Tradeoff:**

| Strategy | Memory | False Positive Rate | False Negative Rate | Complexity |
|----------|--------|---------------------|---------------------|------------|
| **Bloom filter** | ✅ O(1) | ⚠️ <1% | ✅ 0% | ✅ Simple |
| **Exact set** | ❌ O(N) | ✅ 0% | ✅ 0% | ⚠️ Moderate |
| **No detection** | ✅ O(1) | ✅ 0% | ❌ 100% | ✅ Trivial |

**Why This Wins:**

Bloom filter with threshold=3 allows legitimate retries (test, fix, re-test) while catching infinite loops. The <1% false positive rate is acceptable because the suppression is soft (injects nudge message, doesn't hard-block).

---

### 6. Model Routing: Two-Slot Architecture

**Decision:** Map all roles to either "fast" or "smart" slot

**Rationale:**

- **Simplicity:** Two slots easier to reason about than N slots
- **Cost optimization:** Fast slot for high-frequency calls, smart slot for complex work
- **Configuration:** Easy to tune (two knobs vs many)
- **Provider flexibility:** Can change underlying models without app changes

**Alternatives Considered:**

1. **Single universal model**
   - Would waste budget on simple tasks (using Opus for typo fixes)
   - Or under-provision complex tasks (using Haiku for architecture decisions)
   - No cost optimization

2. **Per-role model (generator, planner, evaluator, safety, ...)**
   - Would offer fine-grained control
   - But 90% of decisions collapse to "fast vs smart"
   - Configuration complexity explodes
   - Hard to communicate to users

3. **Dynamic routing per request**
   - Would optimize each call individually
   - Adds routing overhead (50-100ms)
   - Risk of miscalibration
   - Unpredictable costs

**Tradeoff:**

| Architecture | Cost Optimization | Complexity | Flexibility |
|--------------|-------------------|------------|-------------|
| **Single model** | ❌ Poor | ✅ Trivial | ❌ None |
| **Two slots** | ✅ Good | ✅ Simple | ✅ Good |
| **Per-role slots** | ✅ Good | ❌ Complex | ⚠️ Too much |
| **Dynamic routing** | ✅ Optimal | ❌ Complex | ✅ Maximum |

**Why This Wins:**

Two slots capture 95% of cost optimization while staying conceptually simple. Users understand "fast for iteration, smart for hard problems". Future: intelligent router can sit behind the slots without changing the interface.

**Empirical Data:**

```yaml
Cost Distribution (30-day sample):
  fast_slot (deepseek-v4-flash): 73% of calls, 22% of cost
  smart_slot (deepseek-v4-pro): 27% of calls, 78% of cost

Average Latency:
  fast_slot: 1.2s (P95: 2.5s)
  smart_slot: 3.8s (P95: 8.0s)
```

---

### 7. Synchronous Hook Execution

**Decision:** Execute hooks synchronously in the main loop thread

**Rationale:**

- **Determinism:** Hook order and timing is predictable
- **Error handling:** Hook failures are catchable in loop
- **Simplicity:** No async coordination or race conditions
- **Blocking semantics:** PreToolUse hook can block execution

**Alternatives Considered:**

1. **Async hooks with callbacks**
   - Would allow parallel hook execution
   - But most hooks are fast (<10ms)
   - Race conditions between hooks
   - Complex error handling (partial hook failures)

2. **Event queue with background processing**
   - Would decouple loop from hook latency
   - But lose ability to block on PreToolUse
   - Eventual consistency issues
   - Complex state synchronization

**Tradeoff:**

| Strategy | Latency | Determinism | Blocking Capability | Complexity |
|----------|---------|-------------|---------------------|------------|
| **Sync** | ⚠️ Sum of hooks | ✅ Perfect | ✅ Yes | ✅ Simple |
| **Async** | ✅ Max of hooks | ❌ Non-deterministic | ❌ No | ❌ Complex |
| **Queue** | ✅ Decoupled | ❌ Eventual | ❌ No | ❌ Very complex |

**Why This Wins:**

Hooks are fast (P95 <100ms) and order matters (TDD gate must block before execution). The latency cost is acceptable given the simplicity gain. For expensive operations (test runs, linting), hooks spawn background processes and poll results.

**Benchmark Data:**

```yaml
Hook Latency (P95):
  secret_scanner: 8ms
  tdd_gate: 50ms (cached), 2s (test run)
  destructive_pattern: 5ms
  cost_estimator: 3ms
  safety_monitor: 200ms (LLM-based)
```

---

## Cost vs Performance Tradeoffs

### 8. Prompt Caching Strategy

**Decision:** Three-level cache with breakpoints at system, SOUL+plan, and recent

**Rationale:**

- **L1 (system + tools):** Rarely changes, high hit rate (>95%)
- **L2 (SOUL + plan):** Stable within session, medium hit rate (~80%)
- **L3 (recent turns):** Changes every step, low hit rate (<20%)

**Measured Impact:**

```yaml
Cache Hit Rates (30-day sample):
  L1_hit_rate: 96.2%
  L2_hit_rate: 78.4%
  L3_hit_rate: 12.1%

Cost Savings:
  With caching: $0.42/session (avg)
  Without caching: $1.87/session (avg)
  Savings: 77.5%

Latency Impact:
  Cache hit: -30% latency (warm cache read)
  Cache miss: +5% latency (cache write overhead)
  Net: -25% avg latency
```

**Why This Wins:**

77% cost reduction with 25% latency improvement is a clear win. The three-level structure aligns with natural prompt boundaries.

---

### 9. State Persistence Frequency

**Decision:** Persist state every step (recent.jsonl + STATE.md)

**Rationale:**

- **Crash recovery:** Can resume from any step
- **Audit trail:** Full history for debugging
- **Cost:** Only ~20ms overhead per step (JSONL append)

**Alternatives Considered:**

1. **Persist on session end only**
   - Would lose data on crash
   - No recovery path
   - Unacceptable for long sessions

2. **Persist every N steps**
   - Would trade recovery granularity for performance
   - But 20ms is already negligible (<1% of step time)
   - No meaningful performance gain

**Why This Wins:**

20ms is cheap insurance for full crash recovery. Long-running sessions (hours) would lose significant work without per-step persistence.

---

## Safety vs Autonomy Tradeoffs

### 10. Permission Bridge Modes

**Decision:** Three modes (plan, auto-edit, bypass) with per-tool granularity

**Rationale:**

- **plan:** Safe default for new users
- **auto-edit:** Balanced for experienced users (common ops approved, destructive ops ask)
- **bypass:** Testing and automation only

**Measured Usage:**

```yaml
Mode Distribution (30-day sample):
  plan: 18% of sessions
  auto-edit: 76% of sessions
  bypass: 6% of sessions

User Satisfaction:
  plan: "Too many prompts" (27% of feedback)
  auto-edit: "Good balance" (89% of feedback)
  bypass: "Use for CI only" (91% of feedback)
```

**Why This Wins:**

Auto-edit mode hits the productivity/safety sweet spot for 76% of users. Plan mode is there for safety-critical work, bypass mode for automation.

---

### 11. Safety Monitor Sampling

**Decision:** Check every 10 steps (not every step)

**Rationale:**

- **Cost:** Each check costs ~$0.02 (LLM-based verification)
- **Latency:** 200ms per check
- **Coverage:** Every 10 steps catches drift before significant damage

**Measured Impact:**

```yaml
Safety Violations Detected:
  Every step: 2.3 per 1000 sessions
  Every 10 steps: 2.1 per 1000 sessions
  Every 50 steps: 1.4 per 1000 sessions

Cost per Session:
  Every step: +$0.80 avg
  Every 10 steps: +$0.08 avg
  Every 50 steps: +$0.02 avg
```

**Why This Wins:**

Every-10-steps sampling catches 91% of violations at 10% of the cost. The 9% miss rate is acceptable given the low base rate of violations.

---

## Scalability Considerations

### 12. Concurrent Session Limit

**Current:** 100 sessions per instance (soft limit)

**Bottlenecks:**

1. **Memory:** ~50 MB per session → 5 GB at 100 sessions
2. **LLM API rate limits:** Provider-dependent
3. **Disk I/O:** JSONL append contention at >200 sessions

**Scaling Strategy:**

```yaml
Vertical:
  - Scale to 32 GB RAM → 400 sessions
  - SSD I/O → 1000 sessions

Horizontal:
  - Session affinity routing
  - Shared state in Redis
  - Distributed trace collection
```

**Future Work:**

- Streaming compaction (incremental vs batch)
- Memory-mapped transcript storage
- Read-only session replicas for analytics

---

## Related Documentation

- [Architecture](./architecture.md)
- [System Design](./system-design.md)
- [Implementation Guide](./implementation-guide.md)
- [Deep Dive](./deep-dive.md)

---

**Next:** [System Design](./system-design.md)
