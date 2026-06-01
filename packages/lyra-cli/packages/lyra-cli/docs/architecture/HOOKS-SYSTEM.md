# Hooks System

## Overview

The Hooks System provides event-driven automation and extensibility through a comprehensive hook lifecycle that enables validation, transformation, monitoring, and automation at every stage of execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hook System                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Hook Registry│───▶│ Event Bus    │───▶│ Hook Chain   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Hook Manager │───▶│ Context Mgr  │───▶│ Result Agg   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Hook Types

### 1. Tool Hooks

Execute around tool invocations:

```python
class ToolHooks:
    """Hooks for tool execution lifecycle."""
    
    # Before tool execution
    @hook("pre_tool_use")
    async def validate_tool_params(context: HookContext) -> HookResult:
        """
        Validate tool parameters before execution.
        
        Can:
        - Modify parameters
        - Cancel execution
        - Add validation errors
        """
        tool_name = context.tool_name
        params = context.params
        
        # Validate required parameters
        if tool_name == "Write":
            if not params.get("file_path"):
                return HookResult.cancel("file_path is required")
            
            # Ensure absolute path
            if not os.path.isabs(params["file_path"]):
                params["file_path"] = os.path.abspath(params["file_path"])
                context.update_params(params)
        
        return HookResult.continue_()
    
    # After tool execution
    @hook("post_tool_use")
    async def auto_format_code(context: HookContext) -> HookResult:
        """
        Auto-format code after Write/Edit operations.
        """
        if context.tool_name in ["Write", "Edit"]:
            file_path = context.params.get("file_path")
            
            if file_path and file_path.endswith((".ts", ".js", ".py")):
                await run_formatter(file_path)
        
        return HookResult.continue_()
    
    @hook("post_tool_use")
    async def verify_tests_pass(context: HookContext) -> HookResult:
        """
        Run tests after code changes.
        """
        if context.tool_name in ["Write", "Edit"]:
            result = await run_tests()
            
            if not result.success:
                return HookResult.retry(
                    reason="tests_failing",
                    context_updates={
                        "test_failures": result.failures
                    }
                )
        
        return HookResult.continue_()
```

### 2. Iteration Hooks

Execute around loop iterations:

```python
class IterationHooks:
    """Hooks for iteration lifecycle."""
    
    @hook("pre_iteration")
    async def check_budget(context: HookContext) -> HookResult:
        """
        Check budget before iteration.
        """
        current_cost = context.metrics.cost_usd
        max_cost = context.goal.constraints.max_cost
        
        if current_cost >= max_cost:
            return HookResult.cancel("budget_exhausted")
        
        # Warn at 80%
        if current_cost >= max_cost * 0.8:
            await notify(f"Budget warning: {current_cost}/{max_cost} USD")
        
        return HookResult.continue_()
    
    @hook("pre_iteration")
    async def load_context(context: HookContext) -> HookResult:
        """
        Load relevant context before iteration.
        """
        # Load handoff notes from previous iteration
        shared_memory = context.shared_memory.read()
        recent_notes = shared_memory["handoff_notes"][-5:]
        
        # Add to context
        context.add_system_message(
            "Recent progress:\n" + 
            "\n".join(note["notes"] for note in recent_notes)
        )
        
        return HookResult.continue_()
    
    @hook("post_iteration")
    async def save_checkpoint(context: HookContext) -> HookResult:
        """
        Save checkpoint after iteration.
        """
        if context.iteration % 10 == 0:  # Every 10 iterations
            await context.checkpoints.create(
                iteration=context.iteration,
                task=context.current_task,
                state=context.shared_memory.read()
            )
        
        return HookResult.continue_()
    
    @hook("post_iteration")
    async def update_metrics(context: HookContext) -> HookResult:
        """
        Update metrics after iteration.
        """
        result = context.iteration_result
        
        context.metrics.update({
            "cost_usd": result.cost,
            "duration_seconds": result.duration.total_seconds(),
            "success": result.success
        })
        
        return HookResult.continue_()
```

### 3. Lifecycle Hooks

Execute at major lifecycle events:

```python
class LifecycleHooks:
    """Hooks for major lifecycle events."""
    
    @hook("initialize")
    async def setup_environment(context: HookContext) -> HookResult:
        """
        Setup environment before execution starts.
        """
        # Create necessary directories
        os.makedirs(".lyra/autonomy", exist_ok=True)
        os.makedirs(".lyra/checkpoints", exist_ok=True)
        
        # Initialize git branch if needed
        if context.config.create_branch:
            branch_name = f"autonomous/{context.goal.id}"
            await git_checkout_branch(branch_name, create=True)
        
        return HookResult.continue_()
    
    @hook("stop")
    async def cleanup(context: HookContext) -> HookResult:
        """
        Cleanup after execution stops.
        """
        # Generate final report
        report = generate_report(context)
        await save_report(report, ".lyra/autonomy/final_report.md")
        
        # Create PR if configured
        if context.config.create_pr and context.has_changes():
            await create_pull_request(context)
        
        # Send notifications
        await notify_completion(context)
        
        return HookResult.continue_()
    
    @hook("on_error")
    async def handle_error(context: HookContext) -> HookResult:
        """
        Handle errors during execution.
        """
        error = context.error
        
        # Log error
        logger.error(f"Error in iteration {context.iteration}: {error}")
        
        # Notify on critical errors
        if isinstance(error, CriticalError):
            await notify_error(error, context)
        
        # Save error context for debugging
        await save_error_context(error, context)
        
        return HookResult.continue_()
    
    @hook("on_stall")
    async def handle_stall(context: HookContext) -> HookResult:
        """
        Handle stalled progress.
        """
        # Analyze stall reason
        analysis = analyze_stall(context)
        
        # Request human guidance
        guidance = await request_guidance(analysis)
        
        # Apply guidance
        if guidance.action == "adjust_strategy":
            context.update_strategy(guidance.new_strategy)
        elif guidance.action == "skip_task":
            context.skip_current_task()
        elif guidance.action == "abort":
            return HookResult.cancel("human_requested_abort")
        
        return HookResult.continue_()
```

### 4. Custom Event Hooks

Execute on custom events:

```python
class CustomHooks:
    """Hooks for custom events."""
    
    @hook("test_failure")
    async def analyze_test_failure(context: HookContext) -> HookResult:
        """
        Analyze test failures and suggest fixes.
        """
        failures = context.test_failures
        
        # Analyze failure patterns
        patterns = analyze_failure_patterns(failures)
        
        # Add suggestions to context
        context.add_suggestions([
            f"Common pattern: {pattern.description}"
            for pattern in patterns
        ])
        
        return HookResult.continue_()
    
    @hook("coverage_improved")
    async def celebrate_progress(context: HookContext) -> HookResult:
        """
        Celebrate coverage improvements.
        """
        old_coverage = context.previous_coverage
        new_coverage = context.current_coverage
        delta = new_coverage - old_coverage
        
        if delta >= 5.0:  # 5% improvement
            await notify(f"🎉 Coverage improved by {delta:.1f}%!")
        
        return HookResult.continue_()
    
    @hook("goal_achieved")
    async def finalize_goal(context: HookContext) -> HookResult:
        """
        Finalize when goal is achieved.
        """
        # Generate success report
        report = generate_success_report(context)
        
        # Create PR
        pr_url = await create_pull_request(context, report)
        
        # Notify team
        await notify_success(context.goal, pr_url)
        
        return HookResult.continue_()
```

## Hook System Implementation

### Hook Registry

```python
class HookRegistry:
    """
    Registry for all hooks in the system.
    """
    
    def __init__(self):
        self.hooks: Dict[str, List[Tuple[int, Hook]]] = defaultdict(list)
        self.hook_metadata: Dict[str, HookMetadata] = {}
    
    def register(
        self,
        event: str,
        hook: Hook,
        priority: int = 0,
        metadata: Optional[HookMetadata] = None
    ):
        """
        Register hook for event.
        
        Args:
            event: Event name (e.g., "pre_tool_use")
            hook: Hook instance
            priority: Execution priority (higher = earlier)
            metadata: Optional metadata about the hook
        """
        self.hooks[event].append((priority, hook))
        self.hooks[event].sort(key=lambda x: x[0], reverse=True)
        
        if metadata:
            self.hook_metadata[hook.id] = metadata
    
    def unregister(self, event: str, hook: Hook):
        """
        Unregister hook from event.
        """
        self.hooks[event] = [
            (p, h) for p, h in self.hooks[event]
            if h.id != hook.id
        ]
    
    def get_hooks(self, event: str) -> List[Hook]:
        """
        Get all hooks for event, sorted by priority.
        """
        return [hook for _, hook in self.hooks[event]]
    
    def list_events(self) -> List[str]:
        """
        List all registered events.
        """
        return list(self.hooks.keys())
```

### Hook Manager

```python
class HookManager:
    """
    Manage hook execution and lifecycle.
    """
    
    def __init__(self, registry: HookRegistry):
        self.registry = registry
        self.context_manager = HookContextManager()
        self.result_aggregator = HookResultAggregator()
    
    async def trigger(
        self,
        event: str,
        context: dict,
        **kwargs
    ) -> HookResult:
        """
        Trigger all hooks for event.
        
        Args:
            event: Event name
            context: Context dictionary
            **kwargs: Additional context
        
        Returns:
            Aggregated hook result
        """
        # Get hooks for event
        hooks = self.registry.get_hooks(event)
        
        if not hooks:
            return HookResult.continue_()
        
        # Create hook context
        hook_context = self.context_manager.create_context(
            event=event,
            context=context,
            **kwargs
        )
        
        # Execute hooks in priority order
        results = []
        
        for hook in hooks:
            try:
                result = await self.execute_hook(hook, hook_context)
                results.append(result)
                
                # Handle immediate cancellation
                if result.status == HookStatus.CANCEL:
                    return result
                
                # Apply context updates
                if result.context_updates:
                    hook_context.update(result.context_updates)
                
            except Exception as e:
                # Hook failures don't stop execution
                logger.error(f"Hook {hook.id} failed: {e}")
                results.append(HookResult.error(str(e)))
        
        # Aggregate results
        return self.result_aggregator.aggregate(results)
    
    async def execute_hook(
        self,
        hook: Hook,
        context: HookContext
    ) -> HookResult:
        """
        Execute single hook with timeout and error handling.
        """
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                hook.execute(context),
                timeout=hook.timeout or 30.0
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Hook {hook.id} timed out")
            return HookResult.continue_()
        
        except Exception as e:
            logger.error(f"Hook {hook.id} failed: {e}")
            return HookResult.error(str(e))
```

### Hook Context

```python
class HookContext:
    """
    Context passed to hooks during execution.
    """
    
    def __init__(self, event: str, **kwargs):
        self.event = event
        self.data = kwargs
        self._updates: Dict[str, Any] = {}
    
    # Tool context
    @property
    def tool_name(self) -> Optional[str]:
        return self.data.get("tool_name")
    
    @property
    def params(self) -> dict:
        return self.data.get("params", {})
    
    def update_params(self, params: dict):
        """Update tool parameters."""
        self._updates["params"] = params
    
    # Iteration context
    @property
    def iteration(self) -> int:
        return self.data.get("iteration", 0)
    
    @property
    def current_task(self) -> Optional[Task]:
        return self.data.get("task")
    
    @property
    def iteration_result(self) -> Optional[TaskResult]:
        return self.data.get("result")
    
    # Goal context
    @property
    def goal(self) -> Optional[Goal]:
        return self.data.get("goal")
    
    @property
    def task_graph(self) -> Optional[TaskGraph]:
        return self.data.get("task_graph")
    
    # State context
    @property
    def shared_memory(self) -> SharedMemory:
        return self.data.get("shared_memory")
    
    @property
    def checkpoints(self) -> CheckpointManager:
        return self.data.get("checkpoints")
    
    @property
    def metrics(self) -> MetricsCollector:
        return self.data.get("metrics")
    
    # Error context
    @property
    def error(self) -> Optional[Exception]:
        return self.data.get("error")
    
    # Configuration
    @property
    def config(self) -> LoopConfig:
        return self.data.get("config")
    
    # Methods
    def update(self, updates: dict):
        """Apply updates to context."""
        self._updates.update(updates)
    
    def get_updates(self) -> dict:
        """Get all context updates."""
        return self._updates.copy()
    
    def add_system_message(self, message: str):
        """Add system message to context."""
        messages = self._updates.get("system_messages", [])
        messages.append(message)
        self._updates["system_messages"] = messages
    
    def add_suggestions(self, suggestions: List[str]):
        """Add suggestions to context."""
        existing = self._updates.get("suggestions", [])
        existing.extend(suggestions)
        self._updates["suggestions"] = existing
```

### Hook Result

```python
class HookStatus(Enum):
    """Hook execution status."""
    CONTINUE = "continue"
    CANCEL = "cancel"
    RETRY = "retry"
    ERROR = "error"

class HookResult:
    """
    Result of hook execution.
    """
    
    def __init__(
        self,
        status: HookStatus,
        reason: Optional[str] = None,
        context_updates: Optional[dict] = None,
        metadata: Optional[dict] = None
    ):
        self.status = status
        self.reason = reason
        self.context_updates = context_updates or {}
        self.metadata = metadata or {}
    
    @classmethod
    def continue_(cls, **updates) -> "HookResult":
        """Continue execution."""
        return cls(HookStatus.CONTINUE, context_updates=updates)
    
    @classmethod
    def cancel(cls, reason: str) -> "HookResult":
        """Cancel execution."""
        return cls(HookStatus.CANCEL, reason=reason)
    
    @classmethod
    def retry(cls, reason: str, **updates) -> "HookResult":
        """Request retry."""
        return cls(HookStatus.RETRY, reason=reason, context_updates=updates)
    
    @classmethod
    def error(cls, error: str) -> "HookResult":
        """Report error."""
        return cls(HookStatus.ERROR, reason=error)
```

## Hook Composition

### Hook Chains

```python
class HookChain:
    """
    Compose multiple hooks into a pipeline.
    """
    
    def __init__(self, name: str, hooks: List[Hook]):
        self.name = name
        self.hooks = hooks
    
    async def execute(self, context: HookContext) -> HookResult:
        """
        Execute all hooks in sequence.
        """
        for hook in self.hooks:
            result = await hook.execute(context)
            
            # Stop on cancel
            if result.status == HookStatus.CANCEL:
                return result
            
            # Apply updates
            if result.context_updates:
                context.update(result.context_updates)
        
        return HookResult.continue_()

# Example: Test verification pipeline
test_pipeline = HookChain("test_verification", [
    RunTestsHook(),
    CheckCoverageHook(),
    LintCodeHook(),
    TypeCheckHook()
])
```

### Conditional Hooks

```python
class ConditionalHook(Hook):
    """
    Hook that executes conditionally.
    """
    
    def __init__(
        self,
        condition: Callable[[HookContext], bool],
        hook: Hook
    ):
        self.condition = condition
        self.hook = hook
    
    async def execute(self, context: HookContext) -> HookResult:
        """
        Execute hook if condition is met.
        """
        if self.condition(context):
            return await self.hook.execute(context)
        
        return HookResult.continue_()

# Example: Only format TypeScript files
format_ts_hook = ConditionalHook(
    condition=lambda ctx: ctx.params.get("file_path", "").endswith(".ts"),
    hook=FormatCodeHook()
)
```

## Built-in Hooks

### Auto-Format Hook

```python
class AutoFormatHook(Hook):
    """
    Automatically format code after Write/Edit.
    """
    
    async def execute(self, context: HookContext) -> HookResult:
        if context.tool_name not in ["Write", "Edit"]:
            return HookResult.continue_()
        
        file_path = context.params.get("file_path")
        if not file_path:
            return HookResult.continue_()
        
        # Determine formatter based on file extension
        ext = os.path.splitext(file_path)[1]
        
        formatters = {
            ".ts": "prettier",
            ".js": "prettier",
            ".py": "black",
            ".go": "gofmt",
            ".rs": "rustfmt"
        }
        
        formatter = formatters.get(ext)
        if formatter:
            await run_formatter(formatter, file_path)
        
        return HookResult.continue_()
```

### Cost Monitor Hook

```python
class CostMonitorHook(Hook):
    """
    Monitor and enforce cost limits.
    """
    
    def __init__(self, warn_threshold: float = 0.8):
        self.warn_threshold = warn_threshold
    
    async def execute(self, context: HookContext) -> HookResult:
        current_cost = context.metrics.cost_usd
        max_cost = context.goal.constraints.max_cost
        
        # Cancel if budget exhausted
        if current_cost >= max_cost:
            return HookResult.cancel("budget_exhausted")
        
        # Warn if approaching limit
        if current_cost >= max_cost * self.warn_threshold:
            await notify(
                f"⚠️ Budget warning: ${current_cost:.2f} / ${max_cost:.2f} used"
            )
        
        return HookResult.continue_()
```

### Test Verification Hook

```python
class TestVerificationHook(Hook):
    """
    Verify tests pass after code changes.
    """
    
    async def execute(self, context: HookContext) -> HookResult:
        if context.tool_name not in ["Write", "Edit"]:
            return HookResult.continue_()
        
        # Run tests
        result = await run_tests()
        
        if not result.success:
            # Request retry with failure context
            return HookResult.retry(
                reason="tests_failing",
                test_failures=result.failures,
                failed_tests=[t.name for t in result.failures]
            )
        
        return HookResult.continue_()
```

## Configuration

### Hook Configuration

```yaml
hooks:
  enabled: true
  
  # Tool hooks
  tool_hooks:
    auto_format:
      enabled: true
      formatters:
        typescript: "prettier"
        python: "black"
        go: "gofmt"
    
    test_verification:
      enabled: true
      run_on: ["Write", "Edit"]
      fail_on_error: true
  
  # Iteration hooks
  iteration_hooks:
    cost_monitor:
      enabled: true
      warn_threshold: 0.8
    
    checkpoint:
      enabled: true
      interval: 10  # Every 10 iterations
  
  # Lifecycle hooks
  lifecycle_hooks:
    create_branch:
      enabled: true
      branch_prefix: "autonomous"
    
    create_pr:
      enabled: true
      auto_merge: false
  
  # Custom hooks
  custom_hooks:
    - event: "test_failure"
      script: "hooks/analyze_test_failure.py"
      priority: 10
```

## Best Practices

1. **Keep Hooks Focused**: Each hook should do one thing well
2. **Handle Errors Gracefully**: Hook failures shouldn't crash the system
3. **Use Priorities**: Order hooks appropriately
4. **Avoid Side Effects**: Hooks should be as pure as possible
5. **Document Behavior**: Clearly document what each hook does
6. **Test Hooks**: Write tests for custom hooks
7. **Monitor Performance**: Track hook execution time

## References

- [Autonomy System](./AUTONOMY-SYSTEM.md)
- [Continuous Loop](./CONTINUOUS-LOOP.md)
- [Event System](./EVENT-SYSTEM.md)
