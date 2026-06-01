# Lyra Autonomy System Architecture

## Executive Summary

The Lyra Autonomy System enables full autonomous operation with minimal human intervention through a layered architecture combining goal decomposition, continuous execution loops, self-monitoring, and adaptive learning.

## Core Principles

1. **Radiation of Probabilities**: Individual iterations may fail, but aggregate progress emerges from the distribution
2. **Fault-Tolerant by Design**: Failures are learning opportunities, not blockers
3. **Human-in-the-Loop Integration**: Autonomy with oversight, not replacement
4. **State Persistence**: Context survives across iterations and sessions
5. **Adaptive Behavior**: Learn from outcomes and optimize strategies

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Autonomy Orchestrator                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Goal Manager │  │ Loop Engine  │  │ Hook System  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Goal Decomposer │  │ State Manager   │  │ Event Bus       │
│                 │  │                 │  │                 │
│ • Parse goals   │  │ • Shared memory │  │ • Pre-hooks     │
│ • Create tasks  │  │ • Checkpoints   │  │ • Post-hooks    │
│ • Prioritize    │  │ • Recovery      │  │ • Stop-hooks    │
│ • Track progress│  │ • Handoffs      │  │ • Triggers      │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                     │
         └────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Execution Engine │
                    │                  │
                    │ • Task executor  │
                    │ • Retry logic    │
                    │ • Verification   │
                    │ • Rollback       │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Research Engine │  │ Learning System │  │ Monitor/Correct │
│                 │  │                 │  │                 │
│ • Multi-hop     │  │ • Pattern recog │  │ • Health checks │
│ • Deep analysis │  │ • Adaptation    │  │ • Anomaly detect│
│ • Synthesis     │  │ • Meta-learning │  │ • Auto-correct  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Component Details

### 1. Goal Manager

**Responsibility**: Transform high-level objectives into executable task graphs.

**Goal Specification Language**:
```yaml
goal:
  id: "increase-test-coverage"
  description: "Achieve 80% test coverage across all modules"
  type: "continuous" | "one-shot" | "scheduled"
  priority: 1-10
  constraints:
    max_duration: "4h"
    max_cost: 50.00
    max_iterations: 100
  success_criteria:
    - metric: "coverage_percentage"
      operator: ">="
      value: 80
    - metric: "tests_passing"
      operator: "=="
      value: true
  failure_conditions:
    - metric: "consecutive_failures"
      operator: ">="
      value: 5
  dependencies: []
  context:
    files: ["src/**/*.ts"]
    exclude: ["**/*.test.ts"]
```

**Goal Decomposition Algorithm**:
```python
def decompose_goal(goal: Goal) -> TaskGraph:
    """
    Decompose high-level goal into executable task DAG.
    
    Algorithm:
    1. Analyze goal type and constraints
    2. Identify required capabilities (testing, refactoring, research)
    3. Generate task nodes with dependencies
    4. Assign priorities based on critical path
    5. Estimate resource requirements per task
    6. Create checkpoint nodes for verification
    """
    
    # Phase 1: Capability Analysis
    capabilities = analyze_required_capabilities(goal)
    
    # Phase 2: Task Generation
    tasks = []
    for capability in capabilities:
        subtasks = generate_subtasks(capability, goal.context)
        tasks.extend(subtasks)
    
    # Phase 3: Dependency Resolution
    graph = build_dependency_graph(tasks)
    
    # Phase 4: Priority Assignment
    critical_path = compute_critical_path(graph)
    assign_priorities(graph, critical_path)
    
    # Phase 5: Checkpoint Insertion
    insert_verification_checkpoints(graph, goal.success_criteria)
    
    return graph
```

**Task Prioritization**:
```python
def prioritize_tasks(tasks: List[Task], context: ExecutionContext) -> List[Task]:
    """
    Multi-factor prioritization:
    1. Goal priority (1-10)
    2. Dependency blocking (how many tasks depend on this)
    3. Estimated impact (potential progress toward goal)
    4. Resource availability (can we execute now?)
    5. Historical success rate (have similar tasks succeeded?)
    """
    
    scores = []
    for task in tasks:
        score = (
            task.goal_priority * 10 +
            count_dependent_tasks(task) * 5 +
            estimate_impact(task, context) * 3 +
            (1 if resources_available(task) else 0) * 8 +
            get_historical_success_rate(task) * 2
        )
        scores.append((score, task))
    
    return [task for _, task in sorted(scores, reverse=True)]
```

### 2. Loop Engine

**Responsibility**: Execute continuous iteration loops with state management and recovery.

**Loop State Machine**:
```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ start()
     ▼
┌─────────┐     ┌──────────┐
│ RUNNING │────▶│ PAUSED   │
└────┬────┘     └────┬─────┘
     │               │ resume()
     │ error         │
     ▼               ▼
┌─────────┐     ┌──────────┐
│ STALLED │────▶│ RECOVERY │
└────┬────┘     └────┬─────┘
     │               │
     │ max_retries   │ recovered
     ▼               ▼
┌─────────┐     ┌──────────┐
│ FAILED  │     │ COMPLETE │
└─────────┘     └──────────┘
```

**Core Loop Implementation**:
```python
class ContinuousLoop:
    """
    Persistent execution loop with state management.
    
    Inspired by continuous-claude but enhanced with:
    - Richer state persistence
    - Multi-goal support
    - Adaptive retry strategies
    - Checkpoint/rollback
    """
    
    def __init__(self, config: LoopConfig):
        self.config = config
        self.state = LoopState.IDLE
        self.iteration = 0
        self.shared_memory = SharedMemory(config.memory_file)
        self.checkpoints = CheckpointManager(config.checkpoint_dir)
        self.metrics = MetricsCollector()
        
    async def run(self, goal: Goal) -> LoopResult:
        """
        Main execution loop.
        """
        self.state = LoopState.RUNNING
        task_graph = decompose_goal(goal)
        
        while not self.should_stop(goal, task_graph):
            self.iteration += 1
            
            # Pre-iteration hooks
            await self.hooks.trigger("pre_iteration", {
                "iteration": self.iteration,
                "goal": goal,
                "state": self.shared_memory.read()
            })
            
            # Select next task
            task = self.select_next_task(task_graph)
            if not task:
                break  # No executable tasks remaining
            
            # Create checkpoint before execution
            checkpoint_id = self.checkpoints.create(
                iteration=self.iteration,
                task=task,
                state=self.shared_memory.read()
            )
            
            try:
                # Execute task
                result = await self.execute_task(task)
                
                # Update shared memory with handoff notes
                self.shared_memory.append({
                    "iteration": self.iteration,
                    "task": task.id,
                    "result": result.status,
                    "notes": result.handoff_notes,
                    "timestamp": datetime.now()
                })
                
                # Update task graph
                task_graph.mark_complete(task, result)
                
                # Post-iteration hooks
                await self.hooks.trigger("post_iteration", {
                    "iteration": self.iteration,
                    "task": task,
                    "result": result
                })
                
                # Verify progress
                if not self.verify_progress(goal, task_graph):
                    self.handle_stall(checkpoint_id)
                
            except Exception as e:
                # Error handling
                await self.handle_error(e, task, checkpoint_id)
            
            # Adaptive sleep based on rate limits
            await self.adaptive_sleep()
        
        # Stop hooks
        await self.hooks.trigger("stop", {
            "goal": goal,
            "final_state": self.shared_memory.read(),
            "metrics": self.metrics.summary()
        })
        
        return self.build_result(goal, task_graph)
    
    def should_stop(self, goal: Goal, graph: TaskGraph) -> bool:
        """
        Multi-condition stop logic.
        """
        # Success: All tasks complete and criteria met
        if graph.is_complete() and self.check_success_criteria(goal):
            return True
        
        # Budget exhausted
        if self.metrics.cost >= goal.constraints.max_cost:
            return True
        
        # Time limit reached
        if self.metrics.duration >= goal.constraints.max_duration:
            return True
        
        # Iteration limit
        if self.iteration >= goal.constraints.max_iterations:
            return True
        
        # Consecutive failures threshold
        if self.metrics.consecutive_failures >= goal.failure_conditions.max_failures:
            return True
        
        # Completion signal detected
        if self.detect_completion_signal(goal):
            return True
        
        return False
    
    def detect_completion_signal(self, goal: Goal) -> bool:
        """
        Detect completion through agent output analysis.
        
        Looks for phrases like:
        - "Task complete"
        - "All tests passing"
        - "Coverage target achieved"
        
        Requires N consecutive detections to avoid false positives.
        """
        recent_outputs = self.shared_memory.get_recent_outputs(
            count=goal.completion_threshold
        )
        
        completion_phrases = [
            "task complete",
            "goal achieved",
            "all tests passing",
            "coverage target met"
        ]
        
        matches = sum(
            1 for output in recent_outputs
            if any(phrase in output.lower() for phrase in completion_phrases)
        )
        
        return matches >= goal.completion_threshold
    
    async def handle_error(self, error: Exception, task: Task, checkpoint_id: str):
        """
        Intelligent error handling with retry strategies.
        """
        self.metrics.consecutive_failures += 1
        
        # Classify error
        error_type = classify_error(error)
        
        if error_type == ErrorType.RATE_LIMIT:
            # Exponential backoff for rate limits
            await self.exponential_backoff()
            return  # Retry same task
        
        elif error_type == ErrorType.TRANSIENT:
            # Retry with same strategy
            if task.retry_count < self.config.max_retries:
                task.retry_count += 1
                return
        
        elif error_type == ErrorType.TASK_SPECIFIC:
            # Rollback to checkpoint and try alternative approach
            self.checkpoints.restore(checkpoint_id)
            task.strategy = self.select_alternative_strategy(task)
            task.retry_count = 0
            return
        
        elif error_type == ErrorType.CRITICAL:
            # Stall and request human intervention
            self.state = LoopState.STALLED
            await self.request_human_intervention(error, task)
        
        # Log error for learning
        self.shared_memory.append({
            "type": "error",
            "task": task.id,
            "error": str(error),
            "error_type": error_type,
            "iteration": self.iteration
        })
```

### 3. State Manager

**Responsibility**: Persist context across iterations and enable recovery.

**Shared Memory Format**:
```json
{
  "goal": {
    "id": "increase-test-coverage",
    "description": "Achieve 80% test coverage",
    "started_at": "2026-05-28T10:00:00Z"
  },
  "current_state": {
    "iteration": 42,
    "tasks_completed": 15,
    "tasks_remaining": 8,
    "coverage_percentage": 72.5,
    "last_checkpoint": "checkpoint_42"
  },
  "handoff_notes": [
    {
      "iteration": 41,
      "from": "task_test_auth",
      "notes": "Added tests for login flow. Edge case: null email needs handling in signup.",
      "timestamp": "2026-05-28T10:15:00Z"
    },
    {
      "iteration": 42,
      "from": "task_test_signup",
      "notes": "Fixed null email edge case. All auth tests passing. Next: test password reset.",
      "timestamp": "2026-05-28T10:20:00Z"
    }
  ],
  "metrics": {
    "cost_usd": 12.50,
    "duration_seconds": 1200,
    "consecutive_failures": 0,
    "success_rate": 0.85
  },
  "learned_patterns": [
    {
      "pattern": "null_input_validation",
      "success_rate": 0.95,
      "contexts": ["auth", "forms", "api"]
    }
  ]
}
```

**Checkpoint Strategy**:
```python
class CheckpointManager:
    """
    Manage execution checkpoints for rollback and recovery.
    """
    
    def create(self, iteration: int, task: Task, state: dict) -> str:
        """
        Create checkpoint before risky operations.
        
        Checkpoint includes:
        - Full shared memory state
        - Git commit SHA (if applicable)
        - File system snapshot (changed files only)
        - Task graph state
        """
        checkpoint_id = f"checkpoint_{iteration}_{task.id}"
        
        checkpoint = {
            "id": checkpoint_id,
            "iteration": iteration,
            "task": task.to_dict(),
            "state": state,
            "git_sha": self.get_git_sha(),
            "files": self.snapshot_files(task.affected_files),
            "timestamp": datetime.now()
        }
        
        self.save(checkpoint_id, checkpoint)
        
        # Prune old checkpoints (keep last N)
        self.prune_old_checkpoints(keep=10)
        
        return checkpoint_id
    
    def restore(self, checkpoint_id: str):
        """
        Restore system state to checkpoint.
        """
        checkpoint = self.load(checkpoint_id)
        
        # Restore shared memory
        self.shared_memory.restore(checkpoint["state"])
        
        # Restore file system
        for file_path, content in checkpoint["files"].items():
            write_file(file_path, content)
        
        # Restore git state (if applicable)
        if checkpoint["git_sha"]:
            git_reset_hard(checkpoint["git_sha"])
```

### 4. Hook System

**Responsibility**: Enable event-driven automation and extensibility.

**Hook Types**:

1. **PreToolUse**: Before any tool execution
2. **PostToolUse**: After tool execution
3. **PreIteration**: Before each loop iteration
4. **PostIteration**: After each iteration
5. **Stop**: When loop terminates
6. **OnError**: When errors occur
7. **OnStall**: When progress stalls
8. **OnSuccess**: When goals achieved

**Hook Implementation**:
```python
class HookSystem:
    """
    Event-driven hook system for automation.
    """
    
    def __init__(self):
        self.hooks: Dict[str, List[Hook]] = defaultdict(list)
        self.hook_chain = HookChain()
    
    def register(self, event: str, hook: Hook, priority: int = 0):
        """
        Register hook for event.
        
        Priority determines execution order (higher = earlier).
        """
        self.hooks[event].append((priority, hook))
        self.hooks[event].sort(key=lambda x: x[0], reverse=True)
    
    async def trigger(self, event: str, context: dict) -> HookResult:
        """
        Trigger all hooks for event.
        
        Hooks can:
        - Modify context (passed to next hook)
        - Cancel execution (return HookResult.CANCEL)
        - Request retry (return HookResult.RETRY)
        """
        result = HookResult.CONTINUE
        
        for priority, hook in self.hooks[event]:
            try:
                hook_result = await hook.execute(context)
                
                if hook_result.status == HookStatus.CANCEL:
                    return HookResult.CANCEL
                
                if hook_result.status == HookStatus.RETRY:
                    result = HookResult.RETRY
                
                # Merge context modifications
                context.update(hook_result.context_updates)
                
            except Exception as e:
                # Hook failures don't stop execution
                log_hook_error(hook, e)
        
        return result

# Example hooks
class AutoFormatHook(Hook):
    """Post-execution hook to auto-format code."""
    
    async def execute(self, context: dict) -> HookResult:
        if context.get("tool") == "Write" or context.get("tool") == "Edit":
            file_path = context["file_path"]
            await run_formatter(file_path)
        
        return HookResult.CONTINUE

class TestVerificationHook(Hook):
    """Post-iteration hook to verify tests pass."""
    
    async def execute(self, context: dict) -> HookResult:
        result = await run_tests()
        
        if not result.success:
            # Request retry with error context
            return HookResult(
                status=HookStatus.RETRY,
                context_updates={
                    "test_failures": result.failures,
                    "retry_reason": "tests_failing"
                }
            )
        
        return HookResult.CONTINUE

class CostMonitorHook(Hook):
    """Pre-iteration hook to check budget."""
    
    async def execute(self, context: dict) -> HookResult:
        current_cost = context["metrics"]["cost_usd"]
        max_cost = context["goal"]["constraints"]["max_cost"]
        
        if current_cost >= max_cost:
            return HookResult(
                status=HookStatus.CANCEL,
                reason="budget_exhausted"
            )
        
        # Warn at 80% budget
        if current_cost >= max_cost * 0.8:
            await send_notification(
                f"Budget warning: {current_cost}/{max_cost} USD used"
            )
        
        return HookResult.CONTINUE
```

**Hook Composition**:
```python
class HookChain:
    """
    Compose multiple hooks into pipelines.
    """
    
    def create_pipeline(self, name: str, hooks: List[Hook]) -> Pipeline:
        """
        Create named hook pipeline.
        
        Example:
        test_pipeline = create_pipeline("test_verification", [
            RunTestsHook(),
            CheckCoverageHook(),
            LintCodeHook(),
            TypeCheckHook()
        ])
        """
        return Pipeline(name, hooks)
    
    def compose(self, *pipelines: Pipeline) -> Pipeline:
        """
        Compose multiple pipelines into one.
        """
        all_hooks = []
        for pipeline in pipelines:
            all_hooks.extend(pipeline.hooks)
        
        return Pipeline("composed", all_hooks)
```

### 5. Human-in-the-Loop Integration

**Intervention Points**:

1. **Approval Gates**: Require human approval before risky operations
2. **Stall Recovery**: Request guidance when stuck
3. **Quality Review**: Human review of completed work
4. **Goal Refinement**: Adjust goals based on progress
5. **Emergency Stop**: Human can halt execution anytime

**Implementation**:
```python
class HumanInteraction:
    """
    Manage human-in-the-loop interactions.
    """
    
    async def request_approval(self, operation: Operation) -> bool:
        """
        Request human approval for risky operation.
        """
        if operation.risk_level < RiskLevel.HIGH:
            return True  # Auto-approve low-risk
        
        notification = {
            "type": "approval_request",
            "operation": operation.description,
            "risk_level": operation.risk_level,
            "impact": operation.estimated_impact,
            "reversible": operation.is_reversible
        }
        
        # Send notification (Slack, email, UI, etc.)
        await self.notify(notification)
        
        # Wait for response (with timeout)
        response = await self.wait_for_response(
            timeout=operation.approval_timeout
        )
        
        return response.approved
    
    async def request_guidance(self, stall: StallContext) -> Guidance:
        """
        Request human guidance when stuck.
        """
        summary = {
            "goal": stall.goal.description,
            "progress": stall.progress_percentage,
            "stuck_on": stall.current_task.description,
            "attempts": stall.retry_count,
            "errors": stall.recent_errors,
            "suggestions": self.generate_suggestions(stall)
        }
        
        await self.notify({
            "type": "guidance_request",
            "summary": summary
        })
        
        guidance = await self.wait_for_guidance(timeout="24h")
        
        return guidance
```

## Integration with Existing Lyra Components

### Memory Integration

```python
# lyra-memory-stack integration
from lyra.memory import MemoryStack

class AutonomyMemoryBridge:
    """
    Bridge autonomy system with Lyra memory stack.
    """
    
    def __init__(self, memory_stack: MemoryStack):
        self.memory = memory_stack
    
    async def store_iteration(self, iteration: IterationResult):
        """
        Store iteration results in memory for learning.
        """
        await self.memory.store({
            "type": "autonomy_iteration",
            "iteration": iteration.number,
            "task": iteration.task,
            "result": iteration.result,
            "duration": iteration.duration,
            "cost": iteration.cost,
            "success": iteration.success
        })
    
    async def retrieve_similar_tasks(self, task: Task) -> List[IterationResult]:
        """
        Retrieve similar past tasks for learning.
        """
        return await self.memory.search({
            "type": "autonomy_iteration",
            "task_type": task.type,
            "similarity_threshold": 0.8
        })
```

### Skill Integration

```python
# lyra-skills integration
from lyra.skills import SkillRegistry

class AutonomySkillBridge:
    """
    Enable autonomy system to discover and use skills.
    """
    
    def __init__(self, skill_registry: SkillRegistry):
        self.skills = skill_registry
    
    async def select_skill_for_task(self, task: Task) -> Optional[Skill]:
        """
        Select best skill for task based on capabilities.
        """
        candidates = await self.skills.search({
            "capabilities": task.required_capabilities,
            "context": task.context
        })
        
        if not candidates:
            return None
        
        # Score candidates based on historical success
        scored = []
        for skill in candidates:
            success_rate = await self.get_skill_success_rate(skill, task)
            scored.append((success_rate, skill))
        
        return max(scored, key=lambda x: x[0])[1]
```

### Observability Integration

```python
# lyra-observability integration
from lyra.observability import Tracer

class AutonomyTracer:
    """
    Trace autonomy execution for debugging and optimization.
    """
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
    
    async def trace_iteration(self, iteration: int, task: Task):
        """
        Create trace span for iteration.
        """
        with self.tracer.span("autonomy.iteration") as span:
            span.set_attribute("iteration", iteration)
            span.set_attribute("task.id", task.id)
            span.set_attribute("task.type", task.type)
            
            # Trace task execution
            result = await self.execute_task(task)
            
            span.set_attribute("result.status", result.status)
            span.set_attribute("result.duration", result.duration)
            span.set_attribute("result.cost", result.cost)
            
            return result
```

## Deployment Modes

### 1. Local Development Mode
- Single machine execution
- Interactive approval gates
- Full logging and debugging
- Manual stop control

### 2. CI/CD Mode
- GitHub Actions integration
- Automated PR creation/merging
- Budget and time limits enforced
- Notification on completion/failure

### 3. Production Mode
- Distributed execution
- High availability
- Automatic recovery
- Comprehensive monitoring

### 4. Research Mode
- Exploratory execution
- Hypothesis testing
- Data collection
- Experiment tracking

## Configuration

```yaml
# autonomy.config.yaml
autonomy:
  mode: "local" | "ci" | "production" | "research"
  
  loop:
    max_iterations: 100
    max_duration: "4h"
    max_cost: 50.00
    checkpoint_interval: 10
    
  retry:
    max_retries: 3
    base_delay: 1.0
    max_delay: 60.0
    exponential_base: 2.0
    
  stall:
    detection_threshold: 5
    recovery_strategy: "human" | "alternative" | "skip"
    
  human_interaction:
    approval_required: true
    approval_timeout: "1h"
    notification_channels: ["slack", "email"]
    
  hooks:
    enabled: true
    auto_format: true
    auto_test: true
    cost_monitoring: true
    
  memory:
    shared_memory_file: ".lyra/autonomy/shared_memory.json"
    checkpoint_dir: ".lyra/autonomy/checkpoints"
    max_checkpoints: 10
    
  observability:
    tracing_enabled: true
    metrics_enabled: true
    log_level: "info"
```

## Security Considerations

1. **Sandboxing**: Execute tasks in isolated environments
2. **Permission System**: Require approval for sensitive operations
3. **Audit Logging**: Track all autonomous actions
4. **Rollback Capability**: Undo harmful changes
5. **Rate Limiting**: Prevent resource exhaustion
6. **Secret Management**: Never expose credentials in logs/memory

## Performance Optimization

1. **Parallel Execution**: Run independent tasks concurrently
2. **Caching**: Reuse results from similar tasks
3. **Incremental Progress**: Save work frequently
4. **Resource Pooling**: Share expensive resources
5. **Adaptive Strategies**: Learn optimal approaches over time

## Monitoring and Metrics

```python
class AutonomyMetrics:
    """
    Track autonomy system performance.
    """
    
    # Efficiency metrics
    iterations_per_hour: float
    cost_per_iteration: float
    success_rate: float
    
    # Progress metrics
    tasks_completed: int
    tasks_remaining: int
    goal_progress_percentage: float
    
    # Quality metrics
    test_coverage: float
    code_quality_score: float
    bug_introduction_rate: float
    
    # Resource metrics
    total_cost_usd: float
    total_duration_seconds: float
    api_calls_count: int
    
    # Learning metrics
    pattern_recognition_accuracy: float
    strategy_adaptation_rate: float
    human_intervention_frequency: float
```

## Future Enhancements

1. **Multi-Agent Coordination**: Multiple autonomous agents working together
2. **Hierarchical Goals**: Nested goal structures with sub-goals
3. **Predictive Planning**: Anticipate future tasks based on patterns
4. **Collaborative Learning**: Share learned patterns across instances
5. **Natural Language Goals**: Accept goals in plain English
6. **Visual Progress Tracking**: Real-time dashboard of autonomy status
7. **Automated Testing**: Generate and run tests autonomously
8. **Self-Optimization**: Tune parameters based on performance data

## References

- [Continuous Loop System](./CONTINUOUS-LOOP.md)
- [Goal-Based Automation](./GOAL-AUTOMATION.md)
- [Hooks System](./HOOKS-SYSTEM.md)
- [Multi-Hop Research](./MULTI-HOP-RESEARCH.md)
- [Deep Research](./DEEP-RESEARCH.md)
- [Self-Evolution](./SELF-EVOLUTION.md)
