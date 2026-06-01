# Continuous Loop System

## Overview

The Continuous Loop System enables persistent, fault-tolerant execution of autonomous tasks with state management, recovery, and adaptive behavior.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Continuous Loop Engine                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ Loop Manager │───▶│ State Store  │───▶│ Recovery Mgr │ │
│  └──────┬───────┘    └──────────────┘    └──────────────┘ │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Iteration Executor                       │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐    │  │
│  │  │ Pre    │─▶│ Execute│─▶│ Post   │─▶│ Verify │    │  │
│  │  │ Hooks  │  │ Task   │  │ Hooks  │  │ Result │    │  │
│  │  └────────┘  └────────┘  └────────┘  └────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Core Concepts

### 1. Iteration Lifecycle

Each iteration follows a strict lifecycle:

```
START → PRE_HOOKS → CHECKPOINT → EXECUTE → POST_HOOKS → VERIFY → HANDOFF → NEXT
                                    ↓
                                  ERROR
                                    ↓
                            CLASSIFY → RETRY/ROLLBACK/STALL
```

### 2. State Persistence

State persists across iterations through multiple mechanisms:

**Shared Memory File** (relay race pattern):
```json
{
  "iteration": 42,
  "handoff_notes": [
    {
      "from_iteration": 41,
      "task": "test_auth_module",
      "status": "partial_success",
      "notes": "Added login tests. Edge case found: null email in signup needs handling.",
      "next_steps": ["Fix null email validation", "Add signup tests"],
      "context": {
        "files_modified": ["src/auth/login.test.ts"],
        "tests_added": 5,
        "coverage_delta": "+3.2%"
      }
    }
  ],
  "accumulated_knowledge": {
    "patterns_discovered": [
      {
        "pattern": "null_input_validation",
        "locations": ["auth/signup", "auth/login", "profile/update"],
        "fix_template": "Add null check before processing"
      }
    ],
    "failed_approaches": [
      {
        "approach": "mock_entire_auth_service",
        "reason": "Too brittle, breaks on implementation changes",
        "alternative": "Mock only external dependencies"
      }
    ]
  }
}
```

**Checkpoint System**:
```python
class Checkpoint:
    """
    Immutable snapshot of system state at a point in time.
    """
    id: str
    iteration: int
    timestamp: datetime
    
    # State components
    shared_memory: dict
    task_graph: TaskGraph
    git_sha: Optional[str]
    file_snapshots: Dict[str, str]  # path -> content
    
    # Metadata
    task_in_progress: Task
    metrics: MetricsSnapshot
    
    def restore(self):
        """
        Restore system to this checkpoint.
        
        Steps:
        1. Restore shared memory
        2. Restore file system
        3. Reset git (if applicable)
        4. Reset task graph state
        5. Reset metrics
        """
        pass
```

### 3. Stop Conditions

Multiple stop conditions evaluated each iteration:

```python
class StopConditions:
    """
    Comprehensive stop condition evaluation.
    """
    
    def should_stop(self, context: LoopContext) -> Tuple[bool, str]:
        """
        Evaluate all stop conditions.
        
        Returns: (should_stop, reason)
        """
        
        # 1. Success: Goal achieved
        if self.check_success_criteria(context):
            return True, "goal_achieved"
        
        # 2. Budget exhausted
        if context.metrics.cost >= context.goal.max_cost:
            return True, "budget_exhausted"
        
        # 3. Time limit reached
        if context.metrics.duration >= context.goal.max_duration:
            return True, "time_limit_reached"
        
        # 4. Iteration limit
        if context.iteration >= context.goal.max_iterations:
            return True, "iteration_limit_reached"
        
        # 5. Consecutive failures
        if context.metrics.consecutive_failures >= context.goal.max_failures:
            return True, "too_many_failures"
        
        # 6. Completion signal detected
        if self.detect_completion_signal(context):
            return True, "completion_signal_detected"
        
        # 7. No more executable tasks
        if not context.task_graph.has_executable_tasks():
            return True, "no_tasks_remaining"
        
        # 8. Stall detected (no progress)
        if self.detect_stall(context):
            return True, "progress_stalled"
        
        # 9. External stop signal (human intervention)
        if self.check_stop_signal():
            return True, "external_stop_signal"
        
        return False, ""
    
    def detect_completion_signal(self, context: LoopContext) -> bool:
        """
        Detect completion through agent output analysis.
        
        Uses configurable completion phrases and threshold.
        Requires N consecutive detections to avoid false positives.
        """
        completion_phrases = context.goal.completion_phrases or [
            "task complete",
            "goal achieved",
            "all tests passing",
            "coverage target met",
            "implementation finished"
        ]
        
        recent_outputs = context.shared_memory.get_recent_outputs(
            count=context.goal.completion_threshold
        )
        
        matches = 0
        for output in recent_outputs:
            output_lower = output.lower()
            if any(phrase in output_lower for phrase in completion_phrases):
                matches += 1
        
        return matches >= context.goal.completion_threshold
    
    def detect_stall(self, context: LoopContext) -> bool:
        """
        Detect when progress has stalled.
        
        Indicators:
        - No metric improvement for N iterations
        - Same task failing repeatedly
        - No new files modified
        - No new tests added
        """
        window = context.goal.stall_detection_window or 5
        recent_iterations = context.get_recent_iterations(window)
        
        # Check metric improvement
        metrics_improving = any(
            self.metrics_improved(recent_iterations[i], recent_iterations[i+1])
            for i in range(len(recent_iterations) - 1)
        )
        
        if not metrics_improving:
            return True
        
        # Check task diversity
        unique_tasks = len(set(it.task.id for it in recent_iterations))
        if unique_tasks == 1:  # Same task over and over
            return True
        
        return False
```

### 4. Error Handling and Recovery

Sophisticated error classification and recovery:

```python
class ErrorHandler:
    """
    Classify errors and determine recovery strategy.
    """
    
    def handle_error(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """
        Classify error and determine recovery action.
        """
        error_type = self.classify_error(error)
        
        if error_type == ErrorType.RATE_LIMIT:
            return self.handle_rate_limit(error, context)
        
        elif error_type == ErrorType.TRANSIENT:
            return self.handle_transient(error, context)
        
        elif error_type == ErrorType.TASK_SPECIFIC:
            return self.handle_task_specific(error, context)
        
        elif error_type == ErrorType.CRITICAL:
            return self.handle_critical(error, context)
        
        else:
            return self.handle_unknown(error, context)
    
    def classify_error(self, error: Exception) -> ErrorType:
        """
        Classify error based on type and message.
        """
        # Rate limit errors
        if isinstance(error, RateLimitError):
            return ErrorType.RATE_LIMIT
        
        if "rate limit" in str(error).lower():
            return ErrorType.RATE_LIMIT
        
        # Transient errors (network, timeout)
        if isinstance(error, (NetworkError, TimeoutError)):
            return ErrorType.TRANSIENT
        
        # Task-specific errors (test failures, build errors)
        if isinstance(error, (TestFailure, BuildError)):
            return ErrorType.TASK_SPECIFIC
        
        # Critical errors (permission denied, disk full)
        if isinstance(error, (PermissionError, OSError)):
            return ErrorType.CRITICAL
        
        return ErrorType.UNKNOWN
    
    def handle_rate_limit(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """
        Handle rate limit with exponential backoff.
        """
        retry_after = self.extract_retry_after(error)
        
        if retry_after:
            delay = retry_after
        else:
            # Exponential backoff
            delay = min(
                context.base_delay * (2 ** context.retry_count),
                context.max_delay
            )
        
        return RecoveryAction(
            action=RecoveryActionType.RETRY,
            delay=delay,
            reason="rate_limit_exceeded"
        )
    
    def handle_transient(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """
        Handle transient errors with retry.
        """
        if context.retry_count >= context.max_retries:
            # Too many retries, escalate
            return RecoveryAction(
                action=RecoveryActionType.SKIP,
                reason="max_retries_exceeded"
            )
        
        return RecoveryAction(
            action=RecoveryActionType.RETRY,
            delay=context.base_delay,
            reason="transient_error"
        )
    
    def handle_task_specific(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """
        Handle task-specific errors with rollback and alternative strategy.
        """
        # Rollback to last checkpoint
        checkpoint_id = context.last_checkpoint
        
        # Select alternative strategy
        alternative = self.select_alternative_strategy(
            context.task,
            context.failed_strategies
        )
        
        if not alternative:
            # No alternatives, skip task
            return RecoveryAction(
                action=RecoveryActionType.SKIP,
                reason="no_alternative_strategy"
            )
        
        return RecoveryAction(
            action=RecoveryActionType.ROLLBACK_AND_RETRY,
            checkpoint_id=checkpoint_id,
            alternative_strategy=alternative,
            reason="task_specific_error"
        )
    
    def handle_critical(self, error: Exception, context: ErrorContext) -> RecoveryAction:
        """
        Handle critical errors with stall and human intervention.
        """
        return RecoveryAction(
            action=RecoveryActionType.STALL,
            reason="critical_error",
            error_details=str(error),
            requires_human=True
        )
```

### 5. Adaptive Sleep and Rate Limiting

Intelligent rate limiting to avoid API throttling:

```python
class RateLimiter:
    """
    Adaptive rate limiting based on provider limits and usage.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.max_calls_per_hour = config.max_calls_per_hour
        self.max_calls_per_minute = config.max_calls_per_minute
        self.call_history: List[datetime] = []
        
    async def wait_if_needed(self):
        """
        Wait if rate limit would be exceeded.
        """
        now = datetime.now()
        
        # Remove old calls from history
        self.call_history = [
            ts for ts in self.call_history
            if now - ts < timedelta(hours=1)
        ]
        
        # Check hourly limit
        if len(self.call_history) >= self.max_calls_per_hour:
            oldest_call = min(self.call_history)
            wait_until = oldest_call + timedelta(hours=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
        
        # Check minute limit
        recent_calls = [
            ts for ts in self.call_history
            if now - ts < timedelta(minutes=1)
        ]
        
        if len(recent_calls) >= self.max_calls_per_minute:
            oldest_recent = min(recent_calls)
            wait_until = oldest_recent + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
        
        # Record this call
        self.call_history.append(now)
    
    def get_available_capacity(self) -> Tuple[int, int]:
        """
        Get available capacity (calls remaining this hour, this minute).
        """
        now = datetime.now()
        
        hour_calls = len([
            ts for ts in self.call_history
            if now - ts < timedelta(hours=1)
        ])
        
        minute_calls = len([
            ts for ts in self.call_history
            if now - ts < timedelta(minutes=1)
        ])
        
        return (
            self.max_calls_per_hour - hour_calls,
            self.max_calls_per_minute - minute_calls
        )
```

## Implementation

### Core Loop Implementation

```python
class ContinuousLoop:
    """
    Main continuous loop implementation.
    """
    
    def __init__(self, config: LoopConfig):
        self.config = config
        self.state = LoopState.IDLE
        self.iteration = 0
        
        # Components
        self.shared_memory = SharedMemory(config.memory_file)
        self.checkpoints = CheckpointManager(config.checkpoint_dir)
        self.hooks = HookSystem()
        self.error_handler = ErrorHandler()
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.stop_conditions = StopConditions()
        self.metrics = MetricsCollector()
        
        # State
        self.task_graph: Optional[TaskGraph] = None
        self.current_task: Optional[Task] = None
        self.last_checkpoint: Optional[str] = None
        
    async def run(self, goal: Goal) -> LoopResult:
        """
        Main execution loop.
        """
        try:
            await self.initialize(goal)
            
            while True:
                # Check stop conditions
                should_stop, reason = self.stop_conditions.should_stop(
                    self.get_context()
                )
                
                if should_stop:
                    return await self.finalize(reason)
                
                # Execute iteration
                await self.execute_iteration()
                
        except Exception as e:
            return await self.handle_fatal_error(e)
    
    async def initialize(self, goal: Goal):
        """
        Initialize loop for goal execution.
        """
        self.state = LoopState.INITIALIZING
        
        # Decompose goal into task graph
        self.task_graph = decompose_goal(goal)
        
        # Initialize shared memory
        self.shared_memory.initialize({
            "goal": goal.to_dict(),
            "started_at": datetime.now().isoformat(),
            "iteration": 0,
            "handoff_notes": [],
            "accumulated_knowledge": {
                "patterns_discovered": [],
                "failed_approaches": []
            }
        })
        
        # Create initial checkpoint
        self.last_checkpoint = self.checkpoints.create(
            iteration=0,
            task=None,
            state=self.shared_memory.read()
        )
        
        # Trigger initialization hooks
        await self.hooks.trigger("initialize", {
            "goal": goal,
            "task_graph": self.task_graph
        })
        
        self.state = LoopState.RUNNING
    
    async def execute_iteration(self):
        """
        Execute single iteration.
        """
        self.iteration += 1
        
        # Pre-iteration hooks
        hook_result = await self.hooks.trigger("pre_iteration", {
            "iteration": self.iteration,
            "state": self.shared_memory.read()
        })
        
        if hook_result == HookResult.CANCEL:
            self.state = LoopState.STOPPED
            return
        
        # Select next task
        self.current_task = self.select_next_task()
        
        if not self.current_task:
            # No executable tasks
            self.state = LoopState.COMPLETE
            return
        
        # Create checkpoint before execution
        self.last_checkpoint = self.checkpoints.create(
            iteration=self.iteration,
            task=self.current_task,
            state=self.shared_memory.read()
        )
        
        # Execute task with error handling
        try:
            result = await self.execute_task_with_retry(self.current_task)
            
            # Update shared memory with handoff
            await self.update_shared_memory(result)
            
            # Update task graph
            self.task_graph.mark_complete(self.current_task, result)
            
            # Post-iteration hooks
            await self.hooks.trigger("post_iteration", {
                "iteration": self.iteration,
                "task": self.current_task,
                "result": result
            })
            
            # Reset consecutive failures on success
            if result.success:
                self.metrics.consecutive_failures = 0
            
        except Exception as e:
            await self.handle_iteration_error(e)
        
        # Adaptive sleep for rate limiting
        await self.rate_limiter.wait_if_needed()
    
    async def execute_task_with_retry(self, task: Task) -> TaskResult:
        """
        Execute task with retry logic.
        """
        retry_count = 0
        
        while retry_count <= self.config.max_retries:
            try:
                result = await self.execute_task(task)
                return result
                
            except Exception as e:
                recovery = self.error_handler.handle_error(e, ErrorContext(
                    task=task,
                    retry_count=retry_count,
                    last_checkpoint=self.last_checkpoint,
                    base_delay=self.config.retry_base_delay,
                    max_delay=self.config.retry_max_delay,
                    max_retries=self.config.max_retries,
                    failed_strategies=task.failed_strategies
                ))
                
                if recovery.action == RecoveryActionType.RETRY:
                    retry_count += 1
                    if recovery.delay:
                        await asyncio.sleep(recovery.delay)
                    continue
                
                elif recovery.action == RecoveryActionType.ROLLBACK_AND_RETRY:
                    self.checkpoints.restore(recovery.checkpoint_id)
                    task.strategy = recovery.alternative_strategy
                    retry_count = 0
                    continue
                
                elif recovery.action == RecoveryActionType.SKIP:
                    return TaskResult(
                        success=False,
                        status=TaskStatus.SKIPPED,
                        reason=recovery.reason
                    )
                
                elif recovery.action == RecoveryActionType.STALL:
                    self.state = LoopState.STALLED
                    if recovery.requires_human:
                        await self.request_human_intervention(e, task)
                    raise
                
                else:
                    raise
        
        # Max retries exceeded
        return TaskResult(
            success=False,
            status=TaskStatus.FAILED,
            reason="max_retries_exceeded"
        )
    
    async def update_shared_memory(self, result: TaskResult):
        """
        Update shared memory with iteration results and handoff notes.
        """
        state = self.shared_memory.read()
        
        # Add handoff note
        handoff = {
            "from_iteration": self.iteration,
            "task": self.current_task.id,
            "status": result.status.value,
            "notes": result.handoff_notes,
            "next_steps": result.suggested_next_steps,
            "context": {
                "files_modified": result.files_modified,
                "tests_added": result.tests_added,
                "coverage_delta": result.coverage_delta
            },
            "timestamp": datetime.now().isoformat()
        }
        
        state["handoff_notes"].append(handoff)
        
        # Update accumulated knowledge
        if result.patterns_discovered:
            state["accumulated_knowledge"]["patterns_discovered"].extend(
                result.patterns_discovered
            )
        
        if result.failed_approaches:
            state["accumulated_knowledge"]["failed_approaches"].extend(
                result.failed_approaches
            )
        
        # Update iteration counter
        state["iteration"] = self.iteration
        
        self.shared_memory.write(state)
    
    def select_next_task(self) -> Optional[Task]:
        """
        Select next task to execute based on priorities and dependencies.
        """
        executable_tasks = self.task_graph.get_executable_tasks()
        
        if not executable_tasks:
            return None
        
        # Prioritize tasks
        prioritized = prioritize_tasks(
            executable_tasks,
            context=self.get_context()
        )
        
        return prioritized[0] if prioritized else None
    
    async def finalize(self, reason: str) -> LoopResult:
        """
        Finalize loop execution.
        """
        self.state = LoopState.FINALIZING
        
        # Trigger stop hooks
        await self.hooks.trigger("stop", {
            "reason": reason,
            "iteration": self.iteration,
            "state": self.shared_memory.read(),
            "metrics": self.metrics.summary()
        })
        
        # Build result
        result = LoopResult(
            success=reason == "goal_achieved",
            reason=reason,
            iterations=self.iteration,
            metrics=self.metrics.summary(),
            final_state=self.shared_memory.read()
        )
        
        self.state = LoopState.STOPPED
        
        return result
```

## Usage Examples

### Example 1: Test Coverage Goal

```python
# Define goal
goal = Goal(
    id="increase-test-coverage",
    description="Achieve 80% test coverage across all modules",
    type=GoalType.CONTINUOUS,
    priority=8,
    constraints=Constraints(
        max_duration=timedelta(hours=4),
        max_cost=50.00,
        max_iterations=100
    ),
    success_criteria=[
        SuccessCriterion(
            metric="coverage_percentage",
            operator=">=",
            value=80
        ),
        SuccessCriterion(
            metric="tests_passing",
            operator="==",
            value=True
        )
    ],
    failure_conditions=FailureConditions(
        max_failures=5
    ),
    completion_phrases=[
        "coverage target achieved",
        "all tests passing at 80%"
    ],
    completion_threshold=3
)

# Configure loop
config = LoopConfig(
    memory_file=".lyra/autonomy/shared_memory.json",
    checkpoint_dir=".lyra/autonomy/checkpoints",
    max_retries=3,
    retry_base_delay=1.0,
    retry_max_delay=60.0,
    rate_limit=RateLimitConfig(
        max_calls_per_hour=100,
        max_calls_per_minute=10
    )
)

# Run loop
loop = ContinuousLoop(config)
result = await loop.run(goal)

print(f"Result: {result.success}")
print(f"Reason: {result.reason}")
print(f"Iterations: {result.iterations}")
print(f"Cost: ${result.metrics.cost_usd:.2f}")
```

### Example 2: Bug Fix Goal

```python
goal = Goal(
    id="fix-auth-bug",
    description="Fix authentication bug causing login failures",
    type=GoalType.ONE_SHOT,
    priority=10,
    constraints=Constraints(
        max_duration=timedelta(hours=2),
        max_cost=20.00,
        max_iterations=50
    ),
    success_criteria=[
        SuccessCriterion(
            metric="bug_fixed",
            operator="==",
            value=True
        ),
        SuccessCriterion(
            metric="tests_passing",
            operator="==",
            value=True
        ),
        SuccessCriterion(
            metric="no_regressions",
            operator="==",
            value=True
        )
    ],
    context={
        "bug_report": "Users unable to login with valid credentials",
        "affected_files": ["src/auth/login.ts"],
        "error_logs": ["AuthError: Invalid token"]
    }
)

result = await loop.run(goal)
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Autonomous Test Coverage

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  autonomous-coverage:
    runs-on: ubuntu-latest
    timeout-minutes: 240  # 4 hours
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Lyra
        run: |
          pip install lyra-cli
          lyra setup
      
      - name: Run Autonomous Loop
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          lyra autonomy run \
            --goal-file .lyra/goals/test-coverage.yaml \
            --max-duration 4h \
            --max-cost 50 \
            --notification-webhook ${{ secrets.SLACK_WEBHOOK }}
      
      - name: Create PR if changes
        if: success()
        run: |
          if [[ -n $(git status -s) ]]; then
            git checkout -b autonomous/test-coverage-$(date +%Y%m%d)
            git add .
            git commit -m "chore: autonomous test coverage improvements"
            git push -u origin HEAD
            gh pr create \
              --title "Autonomous: Test Coverage Improvements" \
              --body "$(cat .lyra/autonomy/summary.md)"
          fi
```

## Performance Considerations

1. **Checkpoint Frequency**: Balance between safety and performance
2. **Memory File Size**: Prune old handoff notes periodically
3. **Rate Limiting**: Respect API limits to avoid throttling
4. **Parallel Execution**: Run independent tasks concurrently
5. **Incremental Progress**: Save work frequently to minimize rework

## Monitoring and Debugging

```python
# Enable detailed logging
loop = ContinuousLoop(config)
loop.enable_debug_logging()

# Monitor progress
@loop.on("iteration_complete")
def log_progress(event):
    print(f"Iteration {event.iteration}: {event.task.id} - {event.result.status}")

# Track metrics
@loop.on("metrics_update")
def log_metrics(event):
    print(f"Cost: ${event.metrics.cost_usd:.2f}")
    print(f"Coverage: {event.metrics.coverage_percentage:.1f}%")
```

## Best Practices

1. **Clear Handoff Notes**: Write detailed notes for next iteration
2. **Checkpoint Before Risky Operations**: Always create checkpoint before destructive changes
3. **Meaningful Success Criteria**: Define measurable, achievable criteria
4. **Reasonable Constraints**: Set realistic time/cost/iteration limits
5. **Monitor Progress**: Track metrics to detect stalls early
6. **Human Oversight**: Enable approval gates for critical operations
7. **Learn from Failures**: Analyze failed iterations to improve strategies

## Troubleshooting

### Loop Stalls

**Symptom**: No progress for multiple iterations

**Solutions**:
1. Check handoff notes for repeated errors
2. Review failed approaches in accumulated knowledge
3. Adjust task priorities
4. Enable human intervention
5. Reduce task complexity

### High Cost

**Symptom**: Budget exhausted quickly

**Solutions**:
1. Reduce max_iterations
2. Increase checkpoint interval
3. Use more efficient strategies
4. Enable cost monitoring hooks
5. Optimize task decomposition

### Frequent Failures

**Symptom**: High consecutive failure rate

**Solutions**:
1. Review error classification
2. Adjust retry strategies
3. Improve error handling
4. Add more checkpoints
5. Enable debug logging

## References

- [Autonomy System](./AUTONOMY-SYSTEM.md)
- [Goal-Based Automation](./GOAL-AUTOMATION.md)
- [Hooks System](./HOOKS-SYSTEM.md)
- [State Management](./STATE-MANAGEMENT.md)
