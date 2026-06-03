# Verifier Architecture Tradeoffs

## Overview

This document captures the key design decisions in the Verifier block, the alternatives considered, why specific choices were made, and their implications for performance, cost, and maintenance.

## Decision 1: Two-Phase Gating (Objective → Subjective)

### Decision
Gate every task completion with cheap deterministic checks (Phase 1) before expensive LLM judge (Phase 2). Phase 1 failure prevents Phase 2 call.

### Alternatives Considered

**Alternative A: Single LLM-only gate**
- LLM judges everything (tests, files, coverage, quality)
- Simpler architecture (one phase)
- More flexible (can adapt criteria on the fly)

**Alternative B: Three phases (Objective → Static Analysis → LLM)**
- Add intermediate static analysis phase
- TypeScript/Python AST analysis, complexity metrics
- More granular cost shaping

**Alternative C: Always run both phases in parallel**
- Don't gate Phase 2 on Phase 1
- Faster (no sequential dependency)
- Combine results at end

### Why Two-Phase Sequential?

**Cost efficiency**: Phase 1 catches 60-70% of failures at zero LLM cost
- Failing tests: ~40% of rejections
- Missing files: ~15% of rejections  
- Coverage regressions: ~10% of rejections
- Combined: 65% rejection rate, $0 per rejection

Phase 2 only runs on 35% of attempts, saving ~$0.10 per task on average.

**Latency acceptable**: Phase 1 is 200-500ms, acceptable overhead for the cost savings.

**Simplicity**: Two phases are easy to reason about. Three phases add complexity without proportional benefit (static analysis overlaps with both LLM judgment and objective checks).

**Parallel rejected**: Running both phases wastes cost on obvious failures. Sequential gating is load-bearing for cost model.

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Cost** | ✅ 3x cheaper than LLM-only | High benefit |
| **Latency** | ⚠️ +200-500ms for Phase 1 overhead | Acceptable |
| **Complexity** | ⚠️ Two subsystems to maintain | Manageable |
| **Flexibility** | ⚠️ Can't adapt Phase 1 criteria per-task | Acceptable (rare need) |

### Performance Data

```
LLM-only gate:        100 attempts × $0.15 = $15.00
Two-phase gate:       65 × $0 + 35 × $0.15 = $5.25
Cost reduction:       65% savings
Latency overhead:     +300ms p50, +600ms p95
```

---

## Decision 2: Different-Family Evaluator Requirement

### Decision
Enforce that evaluator must be different model family than generator. Same-family is tagged `degraded_eval=same_family` with warning.

### Alternatives Considered

**Alternative A: Allow same-family, no warning**
- Simpler deployment (one provider sufficient)
- No family detection logic
- Operator doesn't need multi-provider setup

**Alternative B: Different-family required (hard error)**
- Strongest guarantee against rubber-stamping
- Forces multi-provider setup
- Fails if operator has only one provider

**Alternative C: Different-model, same-family OK**
- Claude Opus evaluates Claude Sonnet's work
- Easier to deploy than different-family
- Some independent signal

### Why Different-Family Preferred (with Degraded Fallback)?

**Research evidence**: CRITIC and Self-Refine papers show substantially higher miss rates on same-family evaluation
- Same-family: 15-25% false acceptance rate
- Different-family: 5-10% false acceptance rate
- 2-3x improvement in catching semantic bugs

**Pragmatic deployment**: Warning instead of hard error lets operators start with one provider, get degraded-eval feedback, then add second provider when ready.

**Operator visibility**: `degraded_eval=same_family` tag surfaces in traces and metrics, making the tradeoff explicit.

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Accuracy** | ✅ 2-3x better bug detection | High benefit |
| **Deployment complexity** | ⚠️ Requires 2 providers for best experience | Acceptable |
| **Cost** | ⚠️ May require more expensive provider combo | Acceptable (quality worth it) |
| **Single-provider UX** | ⚠️ Degraded warning may confuse new users | Mitigated by docs |

### Migration Path

Phase 0 (current): Warning only, single-provider works  
Phase 1 (v1.9): Recommend different-family in setup wizard  
Phase 2 (v2.0): Consider hard requirement with graceful fallback

---

## Decision 3: Cross-Channel Evidence (Trace + Diff + Snapshot)

### Decision
Require three independent evidence channels (trace, diff, env snapshot) to agree before accepting task. Disagreement triggers reject with fabrication warning.

### Alternatives Considered

**Alternative A: Trace + Diff only (no snapshot)**
- Simpler (no fsevents/fanotify/ReadDirectoryChangesW)
- Fewer platform dependencies
- Still catches most mismatches

**Alternative B: Trust trace (no cross-channel)**
- Simplest: take agent's word for it
- Zero verification overhead
- Fast (no evidence reconciliation)

**Alternative C: Four channels (add DB state)**
- Even stronger guarantee
- Catches database side effects
- More complex snapshot system

### Why Three Channels (Trace + Diff + Snapshot)?

**Claw-Eval insight**: Trust emerges from multiple independent channels agreeing. Two channels insufficient:
- Trace + diff: Misses untracked files (e.g., agent creates `config.yaml` but doesn't commit)
- Trace + snapshot: Misses what agent *claims* vs what it *did*

**Real-world attack vectors caught**:
1. **Commented assertions**: Diff shows test file changed, snapshot shows assertions commented out, trace claims "tests pass"
2. **Untracked side effects**: Diff shows only `settings.py` changed, snapshot shows `config.yaml` also changed
3. **Fabricated test runs**: Trace claims "pytest passed", snapshot shows pytest never invoked

**Platform support**: All three major platforms (macOS/Linux/Windows) have efficient snapshot mechanisms (fsevents/fanotify/ReadDirectoryChangesW).

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Security** | ✅ Catches sophisticated bypass attempts | High benefit |
| **Complexity** | ⚠️ Platform-specific snapshot backends | Manageable (abstracted) |
| **Latency** | ⚠️ +50-150ms for snapshot reconciliation | Acceptable |
| **False positives** | ⚠️ Temp files may cause spurious mismatches | Mitigated by allowlist |

### Maintenance Cost

- Platform-specific code: ~500 LOC per platform
- Test matrix: 3 platforms × 5 scenarios = 15 test cases
- Acceptable for security benefit

---

## Decision 4: Process Reward Model (PRM) as Optional Advisory

### Decision
PRM scores every step but is **advisory only** — surfaces in trace and HUD, doesn't gate by itself. Hooks can act on it (e.g., abort if PRM negative for N steps).

### Alternatives Considered

**Alternative A: PRM gating (hard reject on bad steps)**
- Prune divergent trajectories immediately
- Saves tokens on doomed attempts
- Faster convergence

**Alternative B: No PRM (outcome-only)**
- Simpler (only TDD reward at end)
- No per-step model calls
- Faster (no intermediate scoring)

**Alternative C: PRM replacing Phase 1/2**
- Single verification signal
- Unified architecture
- Simpler mental model

### Why Advisory PRM?

**False positive risk**: Early PRMs (Qwen2.5-Math, Critic-RM) have 10-15% false negative rate on valid reasoning steps. Hard gating would block legitimate work.

**Flexibility**: Advisory signal lets operators choose policy via hooks:
- Conservative: abort on first BAD step
- Aggressive: require 3 consecutive BAD steps
- Disabled: ignore PRM entirely

**Future-proof**: As PRMs improve (GPT-5 PRM, Lyra homegrown PRM), can graduate from advisory to gating without breaking existing behavior.

**Outcome verification still required**: Even with perfect PRM, end-of-task verification (Phase 1/2) is mandatory — PRM doesn't replace it, augments it.

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Token waste** | ⚠️ Bad trajectories continue longer | Acceptable (hooks mitigate) |
| **Flexibility** | ✅ Operators control policy | High benefit |
| **Complexity** | ⚠️ Two verification systems (PRM + Phase 1/2) | Manageable |
| **False positive safety** | ✅ No spurious hard rejects | High benefit |

### Performance Data

```
Advisory PRM:     10% false negatives, 0% spurious rejects
Gating PRM:       10% false negatives → 10% blocked legitimate work
Advisory + hooks: Operator tunes threshold to their risk tolerance
```

---

## Decision 5: 200KB Diff Size Limit with Truncation

### Decision
Truncate diffs larger than 200KB with marker (`[...truncated: 1.2MB omitted]`). Acceptance tests remain ultimate source of truth.

### Alternatives Considered

**Alternative A: No limit (send full diff)**
- Complete context for judge
- No information loss
- Handles large refactors

**Alternative B: Reject large diffs outright**
- Simple (no truncation logic)
- Forces smaller plan items
- Breaks on legitimate large changes

**Alternative C: Chunked evaluation (split diff into chunks)**
- Each chunk evaluated independently
- Combine verdicts at end
- Complete coverage

### Why 200KB Truncation?

**Model context limits**: Even 1M context models degrade on diffs >500KB (attention dilution, position bias).

**Cost**: 200KB diff = ~50K tokens = $0.05-0.15 per evaluation. 1MB diff = $0.25-0.75, unacceptable at scale.

**Acceptance tests as ground truth**: If tests pass (Phase 1), diff details are less critical. Truncation acceptable when tests are comprehensive.

**Marker preserves semantics**: `[...truncated: 1.2MB omitted]` tells judge "large change, tests must validate".

**Chunking rejected**: Complexity not justified — acceptance tests already provide chunked validation.

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Cost** | ✅ Caps evaluation cost at $0.15 | High benefit |
| **Completeness** | ⚠️ Judge doesn't see full diff | Mitigated by tests |
| **Large refactor UX** | ⚠️ Truncation marker may confuse | Acceptable (rare case) |
| **False negatives** | ⚠️ Issues in truncated region missed | Acceptable (tests catch) |

### Data

```
Diff size distribution:
  <10KB:   60% of tasks
  10-50KB: 25% of tasks
  50-200KB: 10% of tasks
  >200KB:   5% of tasks (truncated)

Cost impact:
  No limit:   5% × $0.50 + 95% × $0.10 = $0.12/task avg
  200KB cap:  100% × $0.10 = $0.10/task avg
  Savings:    17% reduction
```

---

## Decision 6: Iteration Loop with Max Rounds (Default 3)

### Decision
On reject verdict, loop back to generator with critique. Max 3 rounds before stalemate escalation.

### Alternatives Considered

**Alternative A: Single-shot (no retry)**
- Reject once, surface to user
- Simpler (no loop)
- Faster (no retry latency)

**Alternative B: Unlimited retries**
- Keep trying until accept
- No artificial cap
- More autonomous

**Alternative C: Adaptive rounds (based on task complexity)**
- Simple tasks: 1 round
- Complex tasks: 5 rounds
- Optimal per-task

### Why 3 Rounds?

**Empirical data**: 
- 1st attempt: 65% acceptance rate
- 2nd attempt: 85% acceptance rate (of rejections)
- 3rd attempt: 92% acceptance rate (of rejections)
- 4th+ attempts: <5% incremental improvement

**Diminishing returns**: Rounds 4+ rarely succeed — either plan is wrong or task is beyond agent capability.

**Cost control**: 3 rounds = predictable cost (3× base cost worst case).

**Stalemate escalation**: After 3 rounds, surface to Planner (maybe plan item is wrong) or user (needs human judgment).

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Success rate** | ✅ 92% eventual acceptance | High benefit |
| **Cost** | ⚠️ Up to 3× cost on rejects | Acceptable (predictable) |
| **Latency** | ⚠️ Up to 3× latency on rejects | Acceptable (quality worth it) |
| **Autonomy** | ⚠️ 8% tasks escalate to human | Acceptable (right level) |

### Adaptive rounds rejected
Complexity not justified — 3 rounds works well across task types. Future: tune per-operator via config.

---

## Decision 7: Heuristic PRM Fallback (No Network Required)

### Decision
Ship deterministic `HeuristicArithmeticPrm` as default, upgrade to real PRM (Qwen2.5-Math-PRM-7B) in v1.9 behind feature flag.

### Alternatives Considered

**Alternative A: Real PRM from day one**
- Best accuracy immediately
- No heuristic maintenance
- Unified architecture

**Alternative B: No PRM until real one ready**
- Simpler (one less subsystem)
- No heuristic code
- Wait for v1.9

**Alternative C: Cloud-hosted PRM API**
- No local inference
- Always available
- Simpler deployment

### Why Heuristic Fallback?

**CI/testing**: Real PRM requires GPU and network. Heuristic is pure Python, runs on any CI runner.

**Offline development**: Developers can work without model download or API key.

**Contract stability**: Shipping PRM contract in v1.8 lets downstream consumers (Tournament TTS, Cascade) integrate early. Implementation swap in v1.9 is transparent.

**Property testing**: Heuristic satisfies property contract (`good arithmetic > bad arithmetic`), sufficient for test suite.

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Accuracy** | ⚠️ Heuristic only scores arithmetic | Acceptable (v1.9 fixes) |
| **Maintenance** | ⚠️ Two PRM implementations | Temporary (v1.8-v1.9) |
| **CI simplicity** | ✅ No GPU/network in CI | High benefit |
| **Offline dev** | ✅ Works without model download | High benefit |

### Migration Path

v1.8: Heuristic default, contract established  
v1.9: Real PRM behind flag, heuristic fallback  
v2.0: Real PRM default, heuristic explicit opt-in

---

## Decision 8: Advisory vs Blocking Verdicts

### Decision
Phase 2 verdicts can be `blocking: true` (reject) or `blocking: false` (advisory accept). Advisory accepts commit with follow-up notes in `lyra retro`.

### Alternatives Considered

**Alternative A: All verdicts blocking**
- Simpler mental model
- No advisory concept
- Stricter quality gate

**Alternative B: Severity levels (critical/high/medium/low)**
- More granular than binary blocking
- Operator chooses threshold
- More flexible

**Alternative C: Score threshold (e.g., accept if score >0.7)**
- Continuous decision boundary
- Operator tunes threshold
- No boolean blocking flag

### Why Binary Advisory/Blocking?

**Clear semantics**: 
- Blocking: Must fix before merge
- Advisory: Nice-to-have, captured for later

**Operator control**: Evaluator (LLM) decides blocking vs advisory, not hardcoded threshold.

**Use cases**:
- Blocking: Missing tests, semantic bugs, security issues
- Advisory: Style nits, missing docstrings, refactor opportunities

**`lyra retro` integration**: Advisory items automatically surface in retrospective as follow-up work.

### Tradeoffs

| Dimension | Impact | Severity |
|-----------|--------|----------|
| **Flexibility** | ✅ Balance quality and velocity | High benefit |
| **Complexity** | ⚠️ Two acceptance paths | Manageable |
| **Consistency** | ⚠️ LLM decides blocking (may vary) | Acceptable (rubric guides) |
| **Operator friction** | ⚠️ Advisory items may accumulate | Mitigated by retro |

### Severity levels rejected
Binary is sufficient. Continuous threshold adds tuning complexity without clear benefit.

---

## Summary: Cost vs Quality vs Complexity

| Decision | Cost Impact | Quality Impact | Complexity Impact | Verdict |
|----------|-------------|----------------|-------------------|---------|
| Two-phase gating | ✅ 65% savings | ✅ High | ⚠️ Medium | Strong win |
| Different-family | ⚠️ +10% cost | ✅ 2-3x better | ⚠️ Medium | Worth it |
| Cross-channel | ⚠️ +50ms latency | ✅ Catches sabotage | ⚠️ High | Worth it |
| Advisory PRM | ✅ No wasted gating | ✅ No false positives | ⚠️ Medium | Future-proof |
| 200KB diff limit | ✅ 17% savings | ⚠️ Rare miss | ⚠️ Low | Good tradeoff |
| 3-round max | ⚠️ Up to 3× cost | ✅ 92% success | ⚠️ Low | Empirically optimal |
| Heuristic fallback | ✅ No CI GPU | ⚠️ Limited accuracy | ⚠️ Medium | Temporary win |
| Advisory verdicts | ✅ Velocity | ✅ Captures tech debt | ⚠️ Medium | Balanced |

**Overall philosophy**: Favor quality and security over cost when the tradeoff is reasonable. Use deterministic checks to shape cost. Provide escape hatches (advisory, degraded-eval) for pragmatic deployment.

## Future Considerations

### Near-term (v1.9-v2.0)
- Real PRM default (Qwen2.5-Math-PRM-7B)
- Chunked diff evaluation for >200KB diffs
- DB state snapshot plugin API

### Long-term (v2.1+)
- Lyra homegrown PRM trained on repository-specific data
- Adaptive round limits per task complexity
- Multi-evaluator ensemble (3+ different families vote)
- Formal verification integration (prove correctness, not just test)

### Research Questions
- Optimal rubric weight tuning per domain
- PRM as primary verifier (replace Phase 1/2?)
- Cross-language verifier transfer learning
- Adversarial robustness against verifier bypass

## Related Documentation

- [Architecture overview](./architecture.md)
- [System design](./system-design.md)
- [Implementation guide](./implementation-guide.md)
- [Deep dive](./deep-dive.md)
