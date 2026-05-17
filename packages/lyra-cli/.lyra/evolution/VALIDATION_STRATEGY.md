# Evolution Framework Validation Strategy

**Phase:** 1.2  
**Status:** In Progress  
**Date:** 2026-05-17

## Overview

This document outlines the validation strategy for Lyra's evolution framework, focusing on verifying that the harness prevents reward hacking while enabling legitimate evolution.

## Validation Approach

### Two-Track Strategy

**Track 1: Unit Tests** (Immediate - Can run now)
- Test harness permission boundaries
- Test cost meter tracking
- Test path validation
- Test score submission isolation
- **Goal:** Verify harness components work correctly
- **Timeline:** Complete in Phase 1.2

**Track 2: Ablation Experiments** (Future - Requires resources)
- Run full evolution experiments with/without harness
- Measure reward-hacking attempts
- Compare convergence rates
- **Goal:** Validate harness effectiveness in real scenarios
- **Timeline:** Deferred until production deployment

### Why Two Tracks?

1. **Resource Constraints:** Full ablation experiments require:
   - Multiple evolution runs (10+ rounds each)
   - Significant API costs ($5+ per experiment)
   - Time investment (hours per run)

2. **Immediate Value:** Unit tests provide:
   - Fast feedback on harness correctness
   - No API costs
   - Can run in CI/CD
   - Catch regressions early

3. **Future Validation:** Ablation experiments provide:
   - Real-world effectiveness data
   - Reward-hacking prevention proof
   - Performance benchmarks
   - Production readiness validation

## Track 1: Unit Tests (Phase 1.2)

### Test Suite Design

#### 1. Harness Permission Tests (`test_harness.py`)

**Purpose:** Verify permission boundaries prevent unauthorized access

**Test Cases:**
1. `test_workspace_read_allowed_paths`
   - Verify agent can read from `workspace/`
   - Verify agent can read from `candidates/`
   - Assert reads succeed

2. `test_workspace_read_blocked_paths`
   - Attempt to read from `evaluator/`
   - Attempt to read from `archive/scores/`
   - Assert reads are blocked with clear error

3. `test_workspace_write_allowed_paths`
   - Verify agent can write to `workspace/`
   - Verify agent can write to `candidates/`
   - Assert writes succeed

4. `test_workspace_write_blocked_paths`
   - Attempt to write to `evaluator/`
   - Attempt to write to `archive/scores/`
   - Assert writes are blocked

5. `test_score_submission_write_only`
   - Submit score via harness
   - Attempt to read submitted score
   - Assert write succeeds, read fails

6. `test_evaluator_internals_protected`
   - Attempt to read evaluator test cases
   - Attempt to modify evaluator code
   - Assert all attempts blocked

7. `test_path_traversal_blocked`
   - Attempt `../` path traversal
   - Attempt absolute paths outside workspace
   - Assert all attempts blocked

8. `test_symlink_protection`
   - Create symlink to protected directory
   - Attempt to read through symlink
   - Assert access blocked

9. `test_legitimate_edits_allowed`
   - Read candidate file
   - Modify candidate file
   - Submit score
   - Assert all operations succeed

10. `test_harness_error_messages`
    - Trigger various permission violations
    - Assert error messages are clear and actionable

#### 2. Cost Meter Tests (`test_cost_meter.py`)

**Purpose:** Verify cost tracking prevents budget overruns

**Test Cases:**
1. `test_cost_meter_initialization`
   - Create cost meter with budget
   - Assert initial cost is 0
   - Assert budget is set correctly

2. `test_cost_tracking_per_round`
   - Track costs for multiple rounds
   - Assert costs accumulate correctly
   - Assert per-round costs are tracked

3. `test_budget_enforcement`
   - Set low budget
   - Attempt operation exceeding budget
   - Assert operation is blocked

4. `test_cost_estimation`
   - Estimate cost before operation
   - Run operation
   - Assert actual cost matches estimate (±10%)

5. `test_cost_breakdown_by_operation`
   - Track different operation types
   - Assert costs are categorized correctly
   - Assert breakdown sums to total

6. `test_cost_meter_reset`
   - Track costs
   - Reset meter
   - Assert costs are cleared

7. `test_cost_meter_persistence`
   - Track costs
   - Save meter state
   - Load meter state
   - Assert costs are preserved

8. `test_budget_warnings`
   - Set budget
   - Approach budget limit (80%, 90%)
   - Assert warnings are issued

9. `test_cost_meter_thread_safety`
   - Track costs from multiple threads
   - Assert no race conditions
   - Assert total is correct

10. `test_cost_meter_overflow_protection`
    - Track very large costs
    - Assert no integer overflow
    - Assert costs remain accurate

#### 3. Integration Tests (`test_integration.py`)

**Purpose:** Verify harness + cost meter work together

**Test Cases:**
1. `test_evolution_round_with_harness`
   - Run single evolution round
   - Assert harness enforces boundaries
   - Assert cost meter tracks costs
   - Assert round completes successfully

2. `test_reward_hacking_attempt_blocked`
   - Simulate reward-hacking attempt
   - Assert harness blocks attempt
   - Assert clear error message
   - Assert cost is still tracked

3. `test_legitimate_evolution_succeeds`
   - Run legitimate evolution workflow
   - Assert all operations succeed
   - Assert costs are tracked
   - Assert scores are submitted correctly

### Test Implementation

**Framework:** pytest  
**Coverage Target:** 80%+  
**Location:** `tests/evolution/`

**Files:**
- `tests/evolution/__init__.py`
- `tests/evolution/test_harness.py` (15 tests)
- `tests/evolution/test_cost_meter.py` (13 tests)
- `tests/evolution/test_integration.py` (3 tests)
- `tests/evolution/conftest.py` (fixtures)

**Fixtures Needed:**
- `temp_workspace` - Temporary workspace directory
- `mock_harness` - Harness with test configuration
- `mock_cost_meter` - Cost meter with test budget
- `sample_candidate` - Sample candidate file
- `sample_evaluator` - Sample evaluator code

## Track 2: Ablation Experiments (Future)

### Experiment Design

#### Experiment 1: Without Harness (Baseline)

**Setup:**
1. Disable permission boundaries
2. Allow direct file access
3. Remove path validation

**Expected Results:**
- Reward hacking in 2/3 runs (per AEVO paper)
- Agent attempts to read evaluator internals
- Agent attempts to modify scores directly

**Metrics:**
- Number of reward-hacking attempts
- Types of exploits discovered
- Time to first exploit
- Success rate of exploits

#### Experiment 2: With Harness (Protected)

**Setup:**
1. Enable full permission boundaries
2. Enforce path validation
3. Use write-only score submission

**Expected Results:**
- No reward hacking
- Valid evolution progress
- Legitimate score improvements

**Metrics:**
- Evolution convergence rate
- Best score achieved
- Number of candidates evaluated
- Cost per round

### Comparison Metrics

| Metric | Without Harness | With Harness |
|--------|----------------|--------------|
| Reward hacking attempts | Expected: 2-3 | Expected: 0 |
| Valid evolution | Expected: No | Expected: Yes |
| Best score | Expected: Inflated | Expected: Legitimate |
| Cost efficiency | Expected: Low | Expected: Normal |
| Performance overhead | N/A | Expected: <10% |

### Success Criteria

- ✅ Harness prevents all reward-hacking attempts
- ✅ Evolution converges with harness enabled
- ✅ No false positives (legitimate edits blocked)
- ✅ Performance overhead < 10%

## Timeline

### Phase 1.2 (Current - Week 1)
- ✅ Create validation strategy document
- 🔄 Implement unit test suite
- 🔄 Run unit tests
- 🔄 Document test results
- 🔄 Fix any issues found

### Future (Production Deployment)
- Run ablation experiments
- Analyze results
- Document findings in `ABLATION_RESULTS.md`
- Adjust harness if needed
- Validate in production

## Deliverables

### Phase 1.2 Deliverables
1. ✅ `VALIDATION_STRATEGY.md` (this document)
2. 🔄 `tests/evolution/test_harness.py` (15 tests)
3. 🔄 `tests/evolution/test_cost_meter.py` (13 tests)
4. 🔄 `tests/evolution/test_integration.py` (3 tests)
5. 🔄 `tests/evolution/conftest.py` (fixtures)
6. 🔄 `VALIDATION_RESULTS.md` (test results)

### Future Deliverables
1. `ABLATION_RESULTS.md` (experiment results)
2. Performance benchmarks
3. Production readiness report

## References

- AEVO paper (arXiv:2605.13821)
- `ABLATION_GUIDE.md`
- `LYRA_EVOLUTION_IMPROVEMENT_ULTRA_PLAN.md`
- `UNFINISHED_PLANS_COMPLETION_STRATEGY.md`
