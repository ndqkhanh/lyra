# §4.14 Implementation Plan: Full Autonomy Mode

**Status**: PLAN  
**Priority**: HIGH×MED (P1)  
**Effort**: 2-3 weeks  
**Dependencies**: §4.13 (Swarm Fleet), lyra-core state management

---

## 1. Overview

Implement continuous autonomous operation mode combining:
- **Continuous-claude loop pattern** for sustained execution
- **Relay-race handoffs** via shared memory files
- **Goal-driven execution** with early stopping signals
- **Failure recovery** with stall detection and diagnostics
- **Budget controls** for cost/time/iteration limits

**Target Capabilities**:
- Run autonomously for hours/days without human intervention
- Maintain context across iterations via shared memory
- Detect and recover from failures automatically
- Stop when goal achieved or budget exhausted
- Resume from checkpoint after interruption

---

## 2. Architecture

### 2.1 Autonomy Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    Autonomy Controller                       │
│  - Goal tracking                                             │
│  - Budget monitoring                                         │
│  - Iteration orchestration                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Iteration Loop  │
                    │  while (!done)   │
                    └──────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Plan    │  │ Execute  │  │  Review  │
        │  Phase   │  │  Phase   │  │  Phase   │
        └──────────┘  └──────────┘  └──────────┘
                │             │             │
                └─────────────┼─────────────┘
                              ▼
                    ┌──────────────────┐
                    │  Shared Memory   │
                    │  - Progress      │
                    │  - Learnings     │
                    │  - Next steps    │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Decision Gate   │
                    │  - Continue?     │
                    │  - Pivot?        │
                    │  - Complete?     │
                    └──────────────────┘
```

### 2.2 Shared Memory Format

**File**: `.lyra/autonomy/shared-memory.md`

```markdown
# Lyra Autonomy Shared Memory

## Goal
[Original goal statement]

## Current Status
- Iteration: 5/20
- Progress: 65%
- Last action: Implemented user authentication
- Confidence: HIGH

## Completed Tasks
- [x] Set up project structure
- [x] Implement database schema
- [x] Add user authentication
- [ ] Add authorization middleware
- [ ] Write integration tests

## Learnings
- JWT tokens work better than sessions for this use case
- bcrypt rounds should be 12 for good security/performance balance
- Database connection pooling improved performance by 3x

## Blockers
- None currently

## Next Iteration Plan
1. Implement role-based authorization middleware
2. Add unit tests for auth module
3. Update API documentation

## Dead Ends (Don't Retry)
- Tried OAuth2 but too complex for MVP
- Attempted Redis sessions but added unnecessary dependency

## Signals
- CONTINUE (confidence: HIGH)
- Budget remaining: $15.50 / $50.00
- Time remaining: 2.5 hours / 4 hours
```

### 2.3 State Machine

```typescript
type AutonomyState = 
  | 'INITIALIZING'
  | 'PLANNING'
  | 'EXECUTING'
  | 'REVIEWING'
  | 'DECIDING'
  | 'STALLED'
  | 'COMPLETED'
  | 'FAILED'
  | 'BUDGET_EXHAUSTED';

interface AutonomyContext {
  goal: string;
  iteration: number;
  maxIterations: number;
  budget: BudgetConfig;
  spent: BudgetSpent;
  sharedMemory: SharedMemory;
  state: AutonomyState;
  confidence: 'LOW' | 'MEDIUM' | 'HIGH';
  consecutiveFailures: number;
  consecutiveCompletionSignals: number;
}
```

---

## 3. Implementation Phases

### Phase 1: Autonomy Controller (Week 1)

**Tasks**:
1. Implement `AutonomyController` class with state machine
2. Add shared memory file management
3. Implement budget tracking (cost, time, iterations)
4. Add goal tracking and progress estimation
5. Write unit tests

**Deliverables**:
- `packages/lyra-core/src/autonomy/controller.ts`
- `packages/lyra-core/src/autonomy/shared-memory.ts`
- `packages/lyra-core/src/autonomy/budget.ts`
- Unit tests

**Acceptance Criteria**:
- State machine transitions correctly
- Shared memory persists across iterations
- Budget tracking accurate within 5%
- Progress estimation reasonable

### Phase 2: Iteration Loop (Week 1-2)

**Tasks**:
1. Implement plan-execute-review cycle
2. Add relay-race handoff logic
3. Implement decision gate (continue/pivot/complete)
4. Add failure detection and recovery
5. Write integration tests

**Deliverables**:
- `packages/lyra-core/src/autonomy/iteration-loop.ts`
- `packages/lyra-core/src/autonomy/decision-gate.ts`
- Integration tests

**Acceptance Criteria**:
- Iterations execute sequentially without manual intervention
- Handoffs preserve context between iterations
- Decision gate makes reasonable continue/stop decisions
- Failures trigger recovery attempts

### Phase 3: Failure Recovery (Week 2)

**Tasks**:
1. Implement stall detection (consecutive failures)
2. Add diagnostic generation for human intervention
3. Implement retry logic with exponential backoff
4. Add checkpoint/resume capability
5. Write failure scenario tests

**Deliverables**:
- `packages/lyra-core/src/autonomy/failure-recovery.ts`
- `packages/lyra-core/src/autonomy/checkpoint.ts`
- Failure scenario tests

**Acceptance Criteria**:
- Stall detection triggers after N consecutive failures
- Diagnostics provide actionable information
- Retry logic prevents infinite loops
- Checkpoint/resume works across process restarts

### Phase 4: CLI Integration (Week 3)

**Tasks**:
1. Add `lyra autonomy` command to CLI
2. Implement real-time progress display
3. Add interactive controls (pause, resume, stop)
4. Implement log streaming
5. Write CLI integration tests

**Deliverables**:
- `packages/lyra-cli/src/commands/autonomy.ts`
- CLI integration tests
- User documentation

**Acceptance Criteria**:
- CLI starts autonomy mode successfully
- Progress display updates in real-time
- Interactive controls work correctly
- Logs stream to terminal

---

## 4. API Design

### 4.1 Starting Autonomy Mode

```typescript
import { AutonomyController } from '@lyra/core/autonomy';

const controller = new AutonomyController({
  goal: 'Build a REST API for user management with authentication',
  maxIterations: 20,
  budget: {
    maxCost: 50.00,        // USD
    maxDuration: 14400000, // 4 hours in ms
    maxCallsPerHour: 100,
  },
  reviewProvider: 'claude-sonnet-4.6', // Optional reviewer
  stallThreshold: 3,       // Consecutive failures before stall
  completionThreshold: 3,  // Consecutive completion signals to stop
});

await controller.start();
```

### 4.2 Monitoring Progress

```typescript
// Subscribe to progress updates
controller.on('iteration-start', (iteration) => {
  console.log(`Starting iteration ${iteration}`);
});

controller.on('iteration-complete', (result) => {
  console.log(`Iteration complete: ${result.status}`);
  console.log(`Progress: ${result.progress}%`);
  console.log(`Budget spent: $${result.spent.cost}`);
});

controller.on('stalled', (diagnostics) => {
  console.error('Autonomy stalled:', diagnostics);
  // Human intervention needed
});

controller.on('completed', (summary) => {
  console.log('Goal achieved!');
  console.log(`Total iterations: ${summary.iterations}`);
  console.log(`Total cost: $${summary.cost}`);
  console.log(`Duration: ${summary.duration}ms`);
});
```

### 4.3 Interactive Control

```typescript
// Pause autonomy (finish current iteration, then pause)
await controller.pause();

// Resume from pause
await controller.resume();

// Stop autonomy (graceful shutdown)
await controller.stop();

// Emergency stop (immediate termination)
await controller.emergencyStop();
```

### 4.4 Checkpoint/Resume

```typescript
// Save checkpoint
await controller.checkpoint('.lyra/autonomy/checkpoint.json');

// Resume from checkpoint
const controller = await AutonomyController.resume(
  '.lyra/autonomy/checkpoint.json'
);
await controller.start();
```

---

## 5. Iteration Cycle Details

### 5.1 Plan Phase

**Responsibilities**:
1. Read shared memory from previous iteration
2. Analyze progress and learnings
3. Identify next steps
4. Generate plan for current iteration
5. Write plan to shared memory

**Implementation**:
```typescript
async function planPhase(context: AutonomyContext): Promise<Plan> {
  // Read shared memory
  const memory = await readSharedMemory(context);
  
  // Analyze progress
  const progress = analyzeProgress(memory);
  
  // Generate plan
  const plan = await generatePlan({
    goal: context.goal,
    progress,
    learnings: memory.learnings,
    deadEnds: memory.deadEnds,
  });
  
  // Write to shared memory
  await updateSharedMemory(context, {
    nextIterationPlan: plan.steps,
  });
  
  return plan;
}
```

### 5.2 Execute Phase

**Responsibilities**:
1. Execute plan steps sequentially
2. Track progress and metrics
3. Handle errors and retries
4. Log results to shared memory
5. Update budget tracking

**Implementation**:
```typescript
async function executePhase(
  context: AutonomyContext,
  plan: Plan
): Promise<ExecutionResult> {
  const results: StepResult[] = [];
  
  for (const step of plan.steps) {
    try {
      const result = await executeStep(step, context);
      results.push(result);
      
      // Update shared memory with progress
      await updateSharedMemory(context, {
        completedTasks: [...memory.completedTasks, step.description],
        learnings: [...memory.learnings, ...result.learnings],
      });
      
      // Update budget
      context.spent.cost += result.cost;
      context.spent.calls += result.calls;
      
    } catch (error) {
      // Log failure
      await updateSharedMemory(context, {
        deadEnds: [...memory.deadEnds, step.approach],
      });
      
      results.push({ step, status: 'failed', error });
    }
  }
  
  return { results, success: results.every(r => r.status === 'success') };
}
```

### 5.3 Review Phase

**Responsibilities**:
1. Evaluate execution results
2. Run optional reviewer agent
3. Assess progress toward goal
4. Update confidence level
5. Generate recommendations

**Implementation**:
```typescript
async function reviewPhase(
  context: AutonomyContext,
  execution: ExecutionResult
): Promise<Review> {
  // Self-assessment
  const selfReview = assessProgress(context, execution);
  
  // Optional external reviewer
  let externalReview = null;
  if (context.reviewProvider) {
    externalReview = await runReviewer(context, execution);
  }
  
  // Combine reviews
  const review = combineReviews(selfReview, externalReview);
  
  // Update confidence
  context.confidence = review.confidence;
  
  // Write to shared memory
  await updateSharedMemory(context, {
    currentStatus: review.status,
    confidence: review.confidence,
  });
  
  return review;
}
```

### 5.4 Decision Gate

**Responsibilities**:
1. Check budget constraints
2. Evaluate completion signals
3. Detect stalls
4. Decide: CONTINUE, PIVOT, COMPLETE, STALL, BUDGET_EXHAUSTED

**Implementation**:
```typescript
async function decisionGate(
  context: AutonomyContext,
  review: Review
): Promise<Decision> {
  // Check budget
  if (context.spent.cost >= context.budget.maxCost) {
    return { action: 'STOP', reason: 'BUDGET_EXHAUSTED' };
  }
  
  if (context.spent.duration >= context.budget.maxDuration) {
    return { action: 'STOP', reason: 'TIME_EXHAUSTED' };
  }
  
  if (context.iteration >= context.maxIterations) {
    return { action: 'STOP', reason: 'MAX_ITERATIONS' };
  }
  
  // Check completion signals
  if (review.signal === 'COMPLETE') {
    context.consecutiveCompletionSignals++;
    if (context.consecutiveCompletionSignals >= context.completionThreshold) {
      return { action: 'STOP', reason: 'GOAL_ACHIEVED' };
    }
  } else {
    context.consecutiveCompletionSignals = 0;
  }
  
  // Check stalls
  if (review.signal === 'FAILED') {
    context.consecutiveFailures++;
    if (context.consecutiveFailures >= context.stallThreshold) {
      return { action: 'STALL', reason: 'CONSECUTIVE_FAILURES' };
    }
  } else {
    context.consecutiveFailures = 0;
  }
  
  // Check pivot signals
  if (review.signal === 'PIVOT') {
    return { action: 'PIVOT', reason: 'APPROACH_NOT_WORKING' };
  }
  
  // Default: continue
  return { action: 'CONTINUE', reason: 'MAKING_PROGRESS' };
}
```

---

## 6. Failure Recovery Strategies

### 6.1 Stall Detection

**Triggers**:
- N consecutive failed iterations (default: 3)
- No progress for M iterations (default: 5)
- Confidence drops to LOW for K iterations (default: 3)

**Response**:
1. Generate diagnostic report
2. Pause autonomy
3. Notify human operator
4. Wait for intervention or timeout
5. Resume with modified approach

### 6.2 Retry Logic

**Strategy**: Exponential backoff with jitter

```typescript
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
      
      const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
      const jitter = Math.random() * 1000;
      await sleep(delay + jitter);
    }
  }
  throw new Error('Max retries exceeded');
}
```

### 6.3 Checkpoint Strategy

**Checkpoint Frequency**:
- After each successful iteration
- Before expensive operations
- On pause/stop signals
- Every N minutes (default: 15)

**Checkpoint Contents**:
```typescript
interface Checkpoint {
  version: string;
  timestamp: number;
  context: AutonomyContext;
  sharedMemory: SharedMemory;
  executionHistory: IterationResult[];
}
```

---

## 7. Budget Management

### 7.1 Cost Tracking

**Components**:
- API calls (per model, per token)
- Tool usage (search, code execution, etc.)
- Infrastructure (compute, storage)

**Implementation**:
```typescript
class BudgetTracker {
  private spent: BudgetSpent = {
    cost: 0,
    calls: 0,
    duration: 0,
  };
  
  trackApiCall(model: string, tokens: number): void {
    const cost = calculateCost(model, tokens);
    this.spent.cost += cost;
    this.spent.calls++;
  }
  
  trackToolUsage(tool: string, cost: number): void {
    this.spent.cost += cost;
  }
  
  isWithinBudget(budget: BudgetConfig): boolean {
    return (
      this.spent.cost < budget.maxCost &&
      this.spent.duration < budget.maxDuration &&
      this.spent.calls < budget.maxCallsPerHour * (this.spent.duration / 3600000)
    );
  }
}
```

### 7.2 Budget Alerts

**Thresholds**:
- 50% budget consumed → INFO
- 75% budget consumed → WARNING
- 90% budget consumed → CRITICAL
- 100% budget consumed → STOP

---

## 8. CLI Interface

### 8.1 Start Command

```bash
# Basic usage
lyra autonomy start "Build a REST API for user management"

# With options
lyra autonomy start "Build a REST API" \
  --max-iterations 20 \
  --max-cost 50 \
  --max-duration 4h \
  --reviewer claude-sonnet-4.6 \
  --stall-threshold 3 \
  --completion-threshold 3

# Resume from checkpoint
lyra autonomy resume .lyra/autonomy/checkpoint.json
```

### 8.2 Interactive Controls

```bash
# Pause (finish current iteration, then pause)
lyra autonomy pause

# Resume
lyra autonomy resume

# Stop (graceful shutdown)
lyra autonomy stop

# Emergency stop
lyra autonomy stop --force

# Status
lyra autonomy status
```

### 8.3 Progress Display

```
┌─────────────────────────────────────────────────────────────┐
│ Lyra Autonomy Mode                                          │
├─────────────────────────────────────────────────────────────┤
│ Goal: Build a REST API for user management                 │
│ Status: EXECUTING (iteration 5/20)                         │
│ Progress: ████████████░░░░░░░░ 65%                         │
│ Confidence: HIGH                                            │
├─────────────────────────────────────────────────────────────┤
│ Budget:                                                     │
│   Cost: $12.50 / $50.00 (25%)                              │
│   Time: 1.5h / 4h (38%)                                    │
│   Calls: 45 / 400 (11%)                                    │
├─────────────────────────────────────────────────────────────┤
│ Current Task: Implementing authorization middleware        │
│ Last Completed: Added user authentication                  │
│ Next: Write integration tests                              │
├─────────────────────────────────────────────────────────────┤
│ Controls: [P]ause [S]top [L]ogs [H]elp                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

- State machine transitions
- Shared memory read/write
- Budget tracking accuracy
- Decision gate logic
- Retry logic with backoff

### 9.2 Integration Tests

- Full iteration cycle (plan → execute → review → decide)
- Checkpoint/resume across process restarts
- Stall detection and recovery
- Budget exhaustion handling
- Completion signal detection

### 9.3 End-to-End Tests

- Complete autonomy run with simple goal (e.g., "Create a hello world API")
- Autonomy run with intentional failures to test recovery
- Budget-constrained run to test early stopping
- Long-running autonomy (hours) to test stability

---

## 10. Security Considerations

1. **Sandbox execution**: All code execution in isolated environment
2. **Budget limits**: Hard caps prevent runaway costs
3. **Human oversight**: Stall detection requires human intervention
4. **Audit trail**: All iterations logged for forensic analysis
5. **Credential isolation**: API keys never written to shared memory

---

## 11. Monitoring & Observability

**Metrics**:
- Iterations per hour
- Success rate per iteration
- Average cost per iteration
- Time to completion
- Stall frequency
- Budget utilization

**Logging**:
- Iteration start/end (info)
- Decision gate outcomes (info)
- Failures and retries (warning)
- Stalls and budget exhaustion (error)

**Alerts**:
- Stall detected
- Budget threshold exceeded (50%, 75%, 90%)
- Consecutive failures
- Unexpected errors

---

## 12. Success Criteria

- [ ] Autonomy controller runs for 4+ hours without manual intervention
- [ ] Shared memory preserves context across iterations
- [ ] Budget tracking accurate within 5%
- [ ] Stall detection triggers after N consecutive failures
- [ ] Checkpoint/resume works across process restarts
- [ ] CLI provides real-time progress display
- [ ] Integration tests pass for all scenarios
- [ ] Documentation complete with examples

---

## 13. References

- Continuous-claude: Loop architecture, relay-race handoffs, budget controls
- Anthropic multi-agent research: Stateful execution, failure recovery
- AutoResearchClaw: SmartPause, confidence-driven pausing, cost guardrails
