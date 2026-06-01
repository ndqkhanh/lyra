# Goal-Based Automation System

## Overview

The Goal-Based Automation System transforms high-level objectives into executable task graphs with intelligent decomposition, prioritization, and progress tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Goal Automation Engine                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Goal Parser  │───▶│ Decomposer   │───▶│ Scheduler    │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Progress     │───▶│ Evaluator    │───▶│ Reporter     │     │
│  │ Tracker      │    │              │    │              │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Goal Specification Language

### YAML Format

```yaml
goal:
  # Identity
  id: "unique-goal-id"
  name: "Human-readable goal name"
  description: "Detailed description of what to achieve"
  
  # Classification
  type: "continuous" | "one-shot" | "scheduled" | "reactive"
  priority: 1-10  # 10 = highest
  category: "testing" | "refactoring" | "feature" | "bugfix" | "research"
  
  # Constraints
  constraints:
    max_duration: "4h" | "2d" | "1w"
    max_cost: 50.00  # USD
    max_iterations: 100
    deadline: "2026-06-01T00:00:00Z"  # Optional
    
  # Success Criteria (ALL must be met)
  success_criteria:
    - metric: "coverage_percentage"
      operator: ">=" | ">" | "==" | "<" | "<="
      value: 80
      
    - metric: "tests_passing"
      operator: "=="
      value: true
      
    - metric: "custom_metric"
      operator: ">="
      value: 100
      evaluator: "path/to/evaluator.py"  # Custom evaluator
  
  # Failure Conditions (ANY triggers failure)
  failure_conditions:
    - metric: "consecutive_failures"
      operator: ">="
      value: 5
      
    - metric: "error_rate"
      operator: ">="
      value: 0.5
  
  # Completion Detection
  completion_detection:
    phrases:
      - "task complete"
      - "goal achieved"
      - "all tests passing"
    threshold: 3  # Consecutive detections required
    
  # Context
  context:
    files: ["src/**/*.ts"]
    exclude: ["**/*.test.ts", "**/*.spec.ts"]
    environment:
      NODE_ENV: "test"
      DEBUG: "true"
    metadata:
      created_by: "user@example.com"
      jira_ticket: "PROJ-123"
  
  # Dependencies
  dependencies:
    - goal_id: "setup-test-environment"
      type: "required" | "optional"
    - goal_id: "install-dependencies"
      type: "required"
  
  # Strategies
  strategies:
    - name: "tdd-approach"
      priority: 1
      description: "Write tests first, then implementation"
      
    - name: "coverage-driven"
      priority: 2
      description: "Focus on uncovered code paths"
  
  # Hooks
  hooks:
    pre_start:
      - "notify_team"
      - "create_branch"
    post_complete:
      - "create_pr"
      - "notify_success"
    on_failure:
      - "notify_failure"
      - "create_incident"
```

### Programmatic API

```python
from lyra.autonomy import Goal, Constraint, SuccessCriterion

goal = Goal(
    id="increase-test-coverage",
    name="Increase Test Coverage",
    description="Achieve 80% test coverage across all modules",
    type=GoalType.CONTINUOUS,
    priority=8,
    category=GoalCategory.TESTING,
    
    constraints=Constraint(
        max_duration=timedelta(hours=4),
        max_cost=50.00,
        max_iterations=100
    ),
    
    success_criteria=[
        SuccessCriterion(
            metric="coverage_percentage",
            operator=Operator.GREATER_EQUAL,
            value=80
        ),
        SuccessCriterion(
            metric="tests_passing",
            operator=Operator.EQUAL,
            value=True
        )
    ],
    
    context={
        "files": ["src/**/*.ts"],
        "exclude": ["**/*.test.ts"]
    }
)
```

## Goal Decomposition

### Decomposition Algorithm

```python
class GoalDecomposer:
    """
    Decompose high-level goals into executable task graphs.
    """
    
    def decompose(self, goal: Goal) -> TaskGraph:
        """
        Main decomposition algorithm.
        
        Steps:
        1. Analyze goal requirements
        2. Identify required capabilities
        3. Generate task hierarchy
        4. Resolve dependencies
        5. Assign priorities
        6. Insert verification checkpoints
        """
        
        # Phase 1: Requirement Analysis
        requirements = self.analyze_requirements(goal)
        
        # Phase 2: Capability Mapping
        capabilities = self.map_capabilities(requirements)
        
        # Phase 3: Task Generation
        tasks = self.generate_tasks(capabilities, goal)
        
        # Phase 4: Dependency Resolution
        graph = self.build_dependency_graph(tasks)
        
        # Phase 5: Priority Assignment
        self.assign_priorities(graph, goal.priority)
        
        # Phase 6: Verification Checkpoints
        self.insert_checkpoints(graph, goal.success_criteria)
        
        return graph
    
    def analyze_requirements(self, goal: Goal) -> Requirements:
        """
        Analyze goal to extract requirements.
        """
        requirements = Requirements()
        
        # Extract from goal type
        if goal.type == GoalType.TESTING:
            requirements.add("test_framework")
            requirements.add("coverage_tool")
            requirements.add("test_runner")
        
        # Extract from success criteria
        for criterion in goal.success_criteria:
            if criterion.metric == "coverage_percentage":
                requirements.add("coverage_measurement")
            elif criterion.metric == "performance_score":
                requirements.add("performance_profiling")
        
        # Extract from context
        if goal.context.get("files"):
            requirements.add("file_analysis")
        
        return requirements
    
    def map_capabilities(self, requirements: Requirements) -> List[Capability]:
        """
        Map requirements to available capabilities.
        """
        capabilities = []
        
        for requirement in requirements:
            # Find capabilities that satisfy requirement
            matching = self.capability_registry.find(requirement)
            
            if not matching:
                raise CapabilityNotFoundError(
                    f"No capability found for requirement: {requirement}"
                )
            
            # Select best capability based on success rate
            best = max(matching, key=lambda c: c.success_rate)
            capabilities.append(best)
        
        return capabilities
    
    def generate_tasks(self, capabilities: List[Capability], goal: Goal) -> List[Task]:
        """
        Generate tasks from capabilities.
        """
        tasks = []
        
        for capability in capabilities:
            # Generate tasks for this capability
            capability_tasks = capability.generate_tasks(goal.context)
            
            # Add metadata
            for task in capability_tasks:
                task.goal_id = goal.id
                task.priority = goal.priority
                task.capability = capability.name
            
            tasks.extend(capability_tasks)
        
        return tasks
    
    def build_dependency_graph(self, tasks: List[Task]) -> TaskGraph:
        """
        Build directed acyclic graph of task dependencies.
        """
        graph = TaskGraph()
        
        # Add all tasks as nodes
        for task in tasks:
            graph.add_node(task)
        
        # Add edges for dependencies
        for task in tasks:
            for dep_id in task.dependencies:
                dep_task = graph.get_task(dep_id)
                if dep_task:
                    graph.add_edge(dep_task, task)
        
        # Verify acyclic
        if graph.has_cycle():
            raise CyclicDependencyError("Task graph contains cycles")
        
        return graph
    
    def assign_priorities(self, graph: TaskGraph, base_priority: int):
        """
        Assign priorities based on critical path and dependencies.
        """
        # Compute critical path
        critical_path = graph.compute_critical_path()
        
        # Assign priorities
        for task in graph.tasks:
            # Base priority from goal
            priority = base_priority
            
            # Boost if on critical path
            if task in critical_path:
                priority += 5
            
            # Boost based on number of dependents
            dependents = graph.get_dependents(task)
            priority += len(dependents)
            
            # Boost based on estimated impact
            impact = self.estimate_impact(task)
            priority += impact
            
            task.priority = min(priority, 10)  # Cap at 10
    
    def insert_checkpoints(self, graph: TaskGraph, criteria: List[SuccessCriterion]):
        """
        Insert verification checkpoint tasks.
        """
        # Group tasks by phase
        phases = graph.identify_phases()
        
        # Insert checkpoint after each phase
        for i, phase in enumerate(phases):
            checkpoint = Task(
                id=f"checkpoint_phase_{i}",
                type=TaskType.VERIFICATION,
                description=f"Verify progress after phase {i}",
                verification_criteria=criteria
            )
            
            # Add dependencies: all tasks in phase must complete
            for task in phase:
                graph.add_edge(task, checkpoint)
            
            graph.add_node(checkpoint)
```

### Task Types

```python
class TaskType(Enum):
    """Types of tasks in the system."""
    
    # Code tasks
    IMPLEMENT = "implement"
    REFACTOR = "refactor"
    FIX_BUG = "fix_bug"
    
    # Testing tasks
    WRITE_TEST = "write_test"
    RUN_TEST = "run_test"
    FIX_TEST = "fix_test"
    
    # Analysis tasks
    ANALYZE_CODE = "analyze_code"
    MEASURE_COVERAGE = "measure_coverage"
    PROFILE_PERFORMANCE = "profile_performance"
    
    # Research tasks
    RESEARCH_APPROACH = "research_approach"
    EVALUATE_OPTIONS = "evaluate_options"
    
    # Verification tasks
    VERIFICATION = "verification"
    VALIDATION = "validation"
    
    # Infrastructure tasks
    SETUP_ENVIRONMENT = "setup_environment"
    INSTALL_DEPENDENCIES = "install_dependencies"

class Task:
    """
    Executable task in the system.
    """
    
    def __init__(
        self,
        id: str,
        type: TaskType,
        description: str,
        **kwargs
    ):
        self.id = id
        self.type = type
        self.description = description
        
        # Metadata
        self.goal_id: Optional[str] = kwargs.get("goal_id")
        self.priority: int = kwargs.get("priority", 5)
        self.capability: Optional[str] = kwargs.get("capability")
        
        # Dependencies
        self.dependencies: List[str] = kwargs.get("dependencies", [])
        self.dependents: List[str] = []
        
        # Execution
        self.status: TaskStatus = TaskStatus.PENDING
        self.strategy: Optional[str] = kwargs.get("strategy")
        self.retry_count: int = 0
        self.failed_strategies: List[str] = []
        
        # Context
        self.context: dict = kwargs.get("context", {})
        self.affected_files: List[str] = kwargs.get("affected_files", [])
        
        # Estimation
        self.estimated_duration: Optional[timedelta] = kwargs.get("estimated_duration")
        self.estimated_cost: Optional[float] = kwargs.get("estimated_cost")
        self.estimated_impact: float = kwargs.get("estimated_impact", 0.5)
        
        # Results
        self.result: Optional[TaskResult] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
```

## Task Prioritization

### Multi-Factor Prioritization

```python
class TaskPrioritizer:
    """
    Prioritize tasks using multiple factors.
    """
    
    def prioritize(self, tasks: List[Task], context: ExecutionContext) -> List[Task]:
        """
        Prioritize tasks based on multiple factors.
        
        Factors:
        1. Goal priority (weight: 10)
        2. Dependency blocking (weight: 5)
        3. Estimated impact (weight: 3)
        4. Resource availability (weight: 8)
        5. Historical success rate (weight: 2)
        6. Deadline urgency (weight: 7)
        """
        
        scores = []
        
        for task in tasks:
            score = self.calculate_score(task, context)
            scores.append((score, task))
        
        # Sort by score (descending)
        scores.sort(key=lambda x: x[0], reverse=True)
        
        return [task for _, task in scores]
    
    def calculate_score(self, task: Task, context: ExecutionContext) -> float:
        """
        Calculate priority score for task.
        """
        score = 0.0
        
        # Factor 1: Goal priority
        score += task.priority * 10
        
        # Factor 2: Dependency blocking
        dependents = context.task_graph.get_dependents(task)
        score += len(dependents) * 5
        
        # Factor 3: Estimated impact
        score += task.estimated_impact * 3
        
        # Factor 4: Resource availability
        if self.resources_available(task, context):
            score += 8
        
        # Factor 5: Historical success rate
        success_rate = self.get_historical_success_rate(task)
        score += success_rate * 2
        
        # Factor 6: Deadline urgency
        if task.deadline:
            urgency = self.calculate_urgency(task.deadline)
            score += urgency * 7
        
        return score
    
    def resources_available(self, task: Task, context: ExecutionContext) -> bool:
        """
        Check if resources are available to execute task.
        """
        # Check budget
        if context.remaining_budget < task.estimated_cost:
            return False
        
        # Check time
        if context.remaining_time < task.estimated_duration:
            return False
        
        # Check dependencies
        for dep_id in task.dependencies:
            dep = context.task_graph.get_task(dep_id)
            if dep.status != TaskStatus.COMPLETE:
                return False
        
        return True
    
    def get_historical_success_rate(self, task: Task) -> float:
        """
        Get historical success rate for similar tasks.
        """
        similar_tasks = self.history.find_similar(task)
        
        if not similar_tasks:
            return 0.5  # Default
        
        successes = sum(1 for t in similar_tasks if t.result.success)
        return successes / len(similar_tasks)
    
    def calculate_urgency(self, deadline: datetime) -> float:
        """
        Calculate urgency based on deadline proximity.
        
        Returns: 0.0 (far future) to 1.0 (imminent)
        """
        now = datetime.now()
        time_remaining = deadline - now
        
        if time_remaining.total_seconds() <= 0:
            return 1.0  # Past deadline
        
        # Normalize to 0-1 scale (1 week = 0.0, 0 = 1.0)
        week_seconds = 7 * 24 * 3600
        urgency = 1.0 - min(time_remaining.total_seconds() / week_seconds, 1.0)
        
        return urgency
```

## Progress Tracking

### Progress Metrics

```python
class ProgressTracker:
    """
    Track progress toward goal completion.
    """
    
    def __init__(self, goal: Goal, task_graph: TaskGraph):
        self.goal = goal
        self.task_graph = task_graph
        self.metrics = ProgressMetrics()
    
    def update(self, task: Task, result: TaskResult):
        """
        Update progress after task completion.
        """
        # Update task counts
        self.metrics.tasks_completed += 1
        self.metrics.tasks_remaining = len(
            self.task_graph.get_pending_tasks()
        )
        
        # Update success rate
        if result.success:
            self.metrics.successful_tasks += 1
        else:
            self.metrics.failed_tasks += 1
        
        self.metrics.success_rate = (
            self.metrics.successful_tasks /
            self.metrics.tasks_completed
        )
        
        # Update resource usage
        self.metrics.cost_usd += result.cost
        self.metrics.duration_seconds += result.duration.total_seconds()
        
        # Update goal-specific metrics
        self.update_goal_metrics(result)
        
        # Calculate progress percentage
        self.metrics.progress_percentage = self.calculate_progress()
    
    def update_goal_metrics(self, result: TaskResult):
        """
        Update metrics specific to goal success criteria.
        """
        for criterion in self.goal.success_criteria:
            metric_name = criterion.metric
            
            if metric_name in result.metrics:
                self.metrics.goal_metrics[metric_name] = result.metrics[metric_name]
    
    def calculate_progress(self) -> float:
        """
        Calculate overall progress percentage.
        
        Combines:
        - Task completion percentage (40%)
        - Goal metric progress (60%)
        """
        # Task completion
        total_tasks = len(self.task_graph.tasks)
        task_progress = self.metrics.tasks_completed / total_tasks
        
        # Goal metrics
        metric_progress = self.calculate_metric_progress()
        
        # Weighted average
        progress = (task_progress * 0.4) + (metric_progress * 0.6)
        
        return min(progress * 100, 100.0)
    
    def calculate_metric_progress(self) -> float:
        """
        Calculate progress toward goal metrics.
        """
        if not self.goal.success_criteria:
            return 1.0
        
        total_progress = 0.0
        
        for criterion in self.goal.success_criteria:
            metric_name = criterion.metric
            current_value = self.metrics.goal_metrics.get(metric_name, 0)
            target_value = criterion.value
            
            # Calculate progress for this metric
            if criterion.operator in [Operator.GREATER_EQUAL, Operator.GREATER]:
                progress = min(current_value / target_value, 1.0)
            elif criterion.operator == Operator.EQUAL:
                progress = 1.0 if current_value == target_value else 0.0
            else:
                progress = 0.5  # Unknown operator
            
            total_progress += progress
        
        return total_progress / len(self.goal.success_criteria)
    
    def get_summary(self) -> dict:
        """
        Get progress summary.
        """
        return {
            "progress_percentage": self.metrics.progress_percentage,
            "tasks_completed": self.metrics.tasks_completed,
            "tasks_remaining": self.metrics.tasks_remaining,
            "success_rate": self.metrics.success_rate,
            "cost_usd": self.metrics.cost_usd,
            "duration_seconds": self.metrics.duration_seconds,
            "goal_metrics": self.metrics.goal_metrics,
            "estimated_completion": self.estimate_completion()
        }
    
    def estimate_completion(self) -> Optional[datetime]:
        """
        Estimate completion time based on current progress.
        """
        if self.metrics.tasks_completed == 0:
            return None
        
        # Calculate average time per task
        avg_time_per_task = (
            self.metrics.duration_seconds /
            self.metrics.tasks_completed
        )
        
        # Estimate remaining time
        remaining_time = avg_time_per_task * self.metrics.tasks_remaining
        
        # Add current time
        estimated = datetime.now() + timedelta(seconds=remaining_time)
        
        return estimated
```

## Success Evaluation

### Criterion Evaluator

```python
class SuccessEvaluator:
    """
    Evaluate success criteria to determine goal completion.
    """
    
    def evaluate(self, goal: Goal, metrics: ProgressMetrics) -> EvaluationResult:
        """
        Evaluate all success criteria.
        """
        results = []
        
        for criterion in goal.success_criteria:
            result = self.evaluate_criterion(criterion, metrics)
            results.append(result)
        
        # All criteria must be met
        all_met = all(r.met for r in results)
        
        return EvaluationResult(
            success=all_met,
            criteria_results=results,
            summary=self.generate_summary(results)
        )
    
    def evaluate_criterion(
        self,
        criterion: SuccessCriterion,
        metrics: ProgressMetrics
    ) -> CriterionResult:
        """
        Evaluate single criterion.
        """
        metric_name = criterion.metric
        current_value = metrics.goal_metrics.get(metric_name)
        
        if current_value is None:
            return CriterionResult(
                criterion=criterion,
                met=False,
                reason="metric_not_available"
            )
        
        # Use custom evaluator if provided
        if criterion.evaluator:
            return self.evaluate_custom(criterion, current_value)
        
        # Standard evaluation
        met = self.compare_values(
            current_value,
            criterion.operator,
            criterion.value
        )
        
        return CriterionResult(
            criterion=criterion,
            met=met,
            current_value=current_value,
            target_value=criterion.value
        )
    
    def compare_values(self, current: Any, operator: Operator, target: Any) -> bool:
        """
        Compare values using operator.
        """
        if operator == Operator.EQUAL:
            return current == target
        elif operator == Operator.GREATER:
            return current > target
        elif operator == Operator.GREATER_EQUAL:
            return current >= target
        elif operator == Operator.LESS:
            return current < target
        elif operator == Operator.LESS_EQUAL:
            return current <= target
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    def evaluate_custom(
        self,
        criterion: SuccessCriterion,
        current_value: Any
    ) -> CriterionResult:
        """
        Evaluate using custom evaluator script.
        """
        # Load evaluator
        evaluator = self.load_evaluator(criterion.evaluator)
        
        # Execute
        result = evaluator.evaluate(current_value, criterion.value)
        
        return CriterionResult(
            criterion=criterion,
            met=result.success,
            current_value=current_value,
            target_value=criterion.value,
            custom_message=result.message
        )
```

## Scheduling

### Task Scheduler

```python
class TaskScheduler:
    """
    Schedule task execution based on priorities and resources.
    """
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self.queue: PriorityQueue[Task] = PriorityQueue()
        self.running: Set[Task] = set()
        self.completed: Set[Task] = set()
    
    def schedule(self, task_graph: TaskGraph) -> Schedule:
        """
        Create execution schedule for task graph.
        """
        schedule = Schedule()
        
        # Get executable tasks (no pending dependencies)
        executable = task_graph.get_executable_tasks()
        
        # Add to priority queue
        for task in executable:
            self.queue.put((-task.priority, task))  # Negative for max-heap
        
        # Generate schedule
        while not self.queue.empty():
            _, task = self.queue.get()
            
            # Determine execution time
            start_time = self.calculate_start_time(task, schedule)
            end_time = start_time + task.estimated_duration
            
            # Add to schedule
            schedule.add_task(task, start_time, end_time)
            
            # Mark as scheduled
            self.completed.add(task)
            
            # Check if new tasks became executable
            for dependent in task_graph.get_dependents(task):
                if self.is_executable(dependent, task_graph):
                    self.queue.put((-dependent.priority, dependent))
        
        return schedule
    
    def calculate_start_time(self, task: Task, schedule: Schedule) -> datetime:
        """
        Calculate earliest start time for task.
        """
        # Start time is max of:
        # 1. Current time
        # 2. Completion time of all dependencies
        
        start_time = datetime.now()
        
        for dep_id in task.dependencies:
            dep_end_time = schedule.get_end_time(dep_id)
            if dep_end_time and dep_end_time > start_time:
                start_time = dep_end_time
        
        return start_time
    
    def is_executable(self, task: Task, graph: TaskGraph) -> bool:
        """
        Check if task is executable (all dependencies complete).
        """
        for dep_id in task.dependencies:
            dep = graph.get_task(dep_id)
            if dep not in self.completed:
                return False
        
        return True
```

## Reporting

### Progress Reporter

```python
class ProgressReporter:
    """
    Generate progress reports for goals.
    """
    
    def generate_report(
        self,
        goal: Goal,
        tracker: ProgressTracker,
        evaluator: SuccessEvaluator
    ) -> Report:
        """
        Generate comprehensive progress report.
        """
        summary = tracker.get_summary()
        evaluation = evaluator.evaluate(goal, tracker.metrics)
        
        report = Report(
            goal=goal,
            timestamp=datetime.now(),
            
            # Progress
            progress_percentage=summary["progress_percentage"],
            tasks_completed=summary["tasks_completed"],
            tasks_remaining=summary["tasks_remaining"],
            
            # Success
            success=evaluation.success,
            criteria_met=sum(1 for r in evaluation.criteria_results if r.met),
            criteria_total=len(goal.success_criteria),
            
            # Resources
            cost_usd=summary["cost_usd"],
            duration=timedelta(seconds=summary["duration_seconds"]),
            
            # Estimates
            estimated_completion=summary["estimated_completion"],
            estimated_remaining_cost=self.estimate_remaining_cost(tracker),
            
            # Details
            goal_metrics=summary["goal_metrics"],
            criteria_details=evaluation.criteria_results
        )
        
        return report
    
    def format_markdown(self, report: Report) -> str:
        """
        Format report as markdown.
        """
        md = f"""# Goal Progress Report

## Goal: {report.goal.name}

**Description**: {report.goal.description}

**Status**: {'✅ Complete' if report.success else '🔄 In Progress'}

## Progress

- **Overall**: {report.progress_percentage:.1f}%
- **Tasks**: {report.tasks_completed} / {report.tasks_completed + report.tasks_remaining} complete
- **Success Rate**: {report.success_rate:.1%}

## Success Criteria

"""
        
        for result in report.criteria_details:
            status = "✅" if result.met else "❌"
            md += f"- {status} **{result.criterion.metric}**: "
            md += f"{result.current_value} {result.criterion.operator} {result.target_value}\n"
        
        md += f"""
## Resources

- **Cost**: ${report.cost_usd:.2f}
- **Duration**: {report.duration}
- **Estimated Completion**: {report.estimated_completion}

## Goal Metrics

"""
        
        for metric, value in report.goal_metrics.items():
            md += f"- **{metric}**: {value}\n"
        
        return md
```

## Usage Examples

### Example 1: Test Coverage Goal

```python
# Define goal
goal = Goal.from_yaml("goals/test-coverage.yaml")

# Decompose into tasks
decomposer = GoalDecomposer()
task_graph = decomposer.decompose(goal)

# Create tracker
tracker = ProgressTracker(goal, task_graph)

# Create evaluator
evaluator = SuccessEvaluator()

# Execute tasks
for task in task_graph.get_executable_tasks():
    result = await execute_task(task)
    tracker.update(task, result)
    
    # Check if goal achieved
    evaluation = evaluator.evaluate(goal, tracker.metrics)
    if evaluation.success:
        print("Goal achieved!")
        break

# Generate report
reporter = ProgressReporter()
report = reporter.generate_report(goal, tracker, evaluator)
print(reporter.format_markdown(report))
```

### Example 2: Multi-Goal Coordination

```python
# Define multiple goals
goals = [
    Goal.from_yaml("goals/test-coverage.yaml"),
    Goal.from_yaml("goals/refactor-auth.yaml"),
    Goal.from_yaml("goals/fix-performance.yaml")
]

# Prioritize goals
prioritized = sorted(goals, key=lambda g: g.priority, reverse=True)

# Execute in priority order
for goal in prioritized:
    result = await execute_goal(goal)
    if not result.success:
        print(f"Goal {goal.name} failed: {result.reason}")
```

## Best Practices

1. **Clear Success Criteria**: Define measurable, achievable criteria
2. **Realistic Constraints**: Set reasonable time/cost/iteration limits
3. **Meaningful Metrics**: Track metrics that matter for the goal
4. **Proper Dependencies**: Specify task dependencies accurately
5. **Incremental Goals**: Break large goals into smaller sub-goals
6. **Regular Evaluation**: Check progress frequently
7. **Adaptive Strategies**: Be ready to adjust approach based on progress

## References

- [Autonomy System](./AUTONOMY-SYSTEM.md)
- [Continuous Loop](./CONTINUOUS-LOOP.md)
- [Task Graph](./TASK-GRAPH.md)
- [Progress Tracking](./PROGRESS-TRACKING.md)
