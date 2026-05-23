# Lyra + ECC Examples

Practical examples for using Lyra with ECC integration.

## Example 1: Parallel Code Review

Review multiple files in parallel:

```python
from lyra_cli.multi_agent import MultiAgentOrchestrator, AgentTask

orchestrator = MultiAgentOrchestrator()

files = ["app.py", "utils.py", "models.py"]

tasks = [
    AgentTask(f"reviewer-{i}", f"Review {file}", {"file": file})
    for i, file in enumerate(files)
]

results = orchestrator.execute_parallel(tasks)

for result in results:
    print(f"{result.agent_id}: {result.status}")
    if result.output:
        print(f"  Issues: {result.output.get('issues', 0)}")
```

## Example 2: Automated Testing Pipeline

Sequential pipeline for testing:

```python
from lyra_cli.loops import SequentialPipeline

pipeline = SequentialPipeline([
    "Install dependencies",
    "Run linter",
    "Run unit tests",
    "Run integration tests",
    "Generate coverage report",
    "Upload results"
])

success = pipeline.execute()

if success:
    print("✅ All tests passed!")
else:
    print("❌ Pipeline failed")
```

## Example 3: Learning from Code Reviews

Capture and learn from review patterns:

```python
from lyra_cli.learning import (
    ObservationCapture,
    InstinctExtractor,
    EvolutionPipeline
)

# Capture observations
capture = ObservationCapture()
observations = capture.get_observations(project_id="my-project", limit=100)

# Extract patterns
extractor = InstinctExtractor()
instincts = extractor.extract_from_observations(observations)

# Evolve high-confidence instincts to skills
pipeline = EvolutionPipeline()

for instinct in instincts:
    if instinct.confidence > 0.8:
        skill_file = pipeline.evolve_to_skill(
            instinct,
            f"auto-{instinct.domain}-{instinct.id[:8]}"
        )
        print(f"✅ Created skill: {skill_file.name}")
```

## Example 4: MCP-Powered Web Automation

Use Playwright MCP server for testing:

```python
from lyra_cli.mcp import MCPManager

manager = MCPManager()
playwright = manager.get_server("playwright")

# In practice, this would execute via MCP protocol
print(f"Using {playwright.name}: {playwright.description}")
print(f"Command: {playwright.command} {' '.join(playwright.args)}")
```

## Example 5: Continuous Monitoring Loop

Monitor and respond to changes:

```python
from lyra_cli.loops import ContinuousLoop
import time

def monitor_task():
    # Check for changes
    print(f"Checking at {time.strftime('%H:%M:%S')}")
    
    # Perform checks
    # - Check git status
    # - Check test results
    # - Check deployment status
    
    return True

loop = ContinuousLoop(monitor_task, interval=300)  # 5 minutes

# Run for 1 hour (12 iterations)
loop.start(max_iterations=12)
```

## Example 6: Hook-Based Code Formatting

Auto-format code after edits:

```python
from lyra_cli.hooks import HookManager, Hook
import subprocess

def format_code(context):
    if context.get("tool_name") == "Edit":
        file_path = context.get("file_path")
        if file_path and file_path.endswith(".py"):
            subprocess.run(["black", file_path])
            print(f"✅ Formatted {file_path}")

manager = HookManager()
hook = Hook("PostToolUse:Edit", format_code)
manager.register_hook(hook)
```

## Example 7: Skill-Based Code Generation

Use skills for common tasks:

```python
from lyra_cli.skills import SkillRegistry, Skill

registry = SkillRegistry()

def generate_test(context):
    file_path = context.get("file_path")
    # Generate test file
    test_path = file_path.replace(".py", "_test.py")
    # ... test generation logic ...
    return {"test_file": test_path}

skill = Skill(
    name="generate-test",
    description="Generate test file for Python module",
    triggers=["test", "generate test"],
    handler=generate_test,
    category="testing"
)

registry.register(skill)

# Use skill
result = skill.execute({"file_path": "app.py"})
print(f"Generated: {result['test_file']}")
```

## Example 8: Multi-Agent Feature Development

Coordinate multiple agents for feature development:

```python
from lyra_cli.multi_agent import MultiAgentOrchestrator, AgentTask

orchestrator = MultiAgentOrchestrator()

# Phase 1: Planning
planning_tasks = [
    AgentTask("architect", "Design system architecture", {"feature": "auth"}),
    AgentTask("analyst", "Analyze requirements", {"feature": "auth"}),
]

planning_results = orchestrator.execute_parallel(planning_tasks)

# Phase 2: Implementation
impl_tasks = [
    AgentTask("backend-dev", "Implement backend", {"design": planning_results[0].output}),
    AgentTask("frontend-dev", "Implement frontend", {"design": planning_results[0].output}),
    AgentTask("test-engineer", "Write tests", {"design": planning_results[0].output}),
]

impl_results = orchestrator.execute_parallel(impl_tasks)

# Phase 3: Review
review_tasks = [
    AgentTask("code-reviewer", "Review code", {"files": impl_results}),
    AgentTask("security-reviewer", "Security review", {"files": impl_results}),
]

review_results = orchestrator.execute_parallel(review_tasks)

print("✅ Feature development complete!")
```

## Example 9: Command Execution

Execute commands programmatically:

```python
from lyra_cli.commands import get_registry

registry = get_registry()

# List all planning commands
planning_cmds = registry.list(category="planning")

for cmd in planning_cmds:
    print(f"{cmd.name}: {cmd.description}")

# Execute a command
plan_cmd = registry.get("plan")
if plan_cmd:
    plan_cmd.handler()  # Execute
```

## Example 10: Complete Workflow

End-to-end workflow combining all features:

```python
from lyra_cli.multi_agent import MultiAgentOrchestrator, AgentTask
from lyra_cli.hooks import HookManager, Hook
from lyra_cli.loops import SequentialPipeline
from lyra_cli.learning import ObservationCapture

# Setup hooks
hook_manager = HookManager()
capture = ObservationCapture()

def capture_observation(context):
    # Capture for learning
    capture.capture_from_hook(context, session_id="workflow-1")

hook = Hook("PostToolUse", capture_observation)
hook_manager.register_hook(hook)

# Define workflow
pipeline = SequentialPipeline([
    "Analyze requirements",
    "Design architecture",
    "Implement features",
    "Write tests",
    "Run tests",
    "Create PR"
])

# Execute
success = pipeline.execute()

if success:
    # Learn from execution
    observations = capture.get_observations(limit=50)
    print(f"✅ Workflow complete! Captured {len(observations)} observations")
```

---

For more examples, see the [ECC Integration Guide](ECC_INTEGRATION.md).
