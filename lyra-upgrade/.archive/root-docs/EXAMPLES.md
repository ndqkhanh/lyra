# Examples

Practical code examples using Lyra's Python API.

## Example 1: Multi-Agent Orchestration

```python
from src.agents import PrimaryAgent, CodeAgent, TestAgent, ReviewAgent
from src.core.task import Task, TaskType

# Setup orchestration
primary = PrimaryAgent()
code = CodeAgent("code-1")
test = TestAgent("test-1")
review = ReviewAgent("review-1")

primary.register_specialist(code)
primary.register_specialist(test)
primary.register_specialist(review)

# Execute a task - PrimaryAgent auto-routes to the right specialist
response = await primary.handle_request(
    "Implement a Redis cache wrapper for the user service"
)
print(response)
```

## Example 2: Task Coordination with Dependencies

```python
from src.coordination import (
    TaskAllocator, DependencyManager, LoadBalancer,
    AllocationStrategy, DependencyType
)
from src.agents import PrimaryAgent, CodeAgent, TestAgent
from src.core.task import Task, TaskType

# Setup
primary = PrimaryAgent()
code_agent = CodeAgent("code-1")
test_agent = TestAgent("test-1")
primary.register_specialist(code_agent)
primary.register_specialist(test_agent)

allocator = TaskAllocator(strategy=AllocationStrategy.CAPABILITY_BASED)
dep_manager = DependencyManager()
balancer = LoadBalancer()

# Create dependent tasks
task_code = Task(type=TaskType.CODE_GENERATION, description="Write auth middleware")
task_test = Task(type=TaskType.TEST_GENERATION, description="Test auth middleware")

# Task test depends on task code
dep_manager.add_dependency(
    task_test.task_id, task_code.task_id, DependencyType.REQUIRES
)

# Get execution order (topological sort)
order = dep_manager.get_execution_order()
print(f"Execution batches: {order}")

# Execute in order
for batch in order:
    results = await primary.execute_parallel(batch)
    for r in results:
        print(f"  {r.task_id}: {'✓' if r.success else '✗'}")
```

## Example 3: Hook System

```python
from src.hooks import HookEngine, Hook, HookType, HookResult, HookContext

def secrets_scan(context: HookContext) -> HookResult:
    """PreToolUse hook that scans for hardcoded secrets."""
    if context.tool_name in ("Write", "Edit"):
        content = context.tool_args.get("content", "")
        if "API_KEY" in content or "password" in content:
            return HookResult.fail("Hardcoded secret detected")
    return HookResult.ok()

# Register hook
engine = HookEngine()
hook = Hook(
    hook_id="secrets-scan",
    hook_type=HookType.PRE_TOOL_USE,
    handler=secrets_scan,
    description="Block writes containing secrets",
    priority=0,
    metadata={"critical": True},
)
engine.registry.register(hook)

# Fire hooks before tool use
results = await engine.fire(
    hook_type=HookType.PRE_TOOL_USE,
    tool_name="Write",
    tool_args={"file_path": "config.py", "content": 'API_KEY = "sk-abc123"'},
)

for result in results:
    if not result.success:
        print(f"Blocked: {result.error}")
```

## Example 4: Memory System

```python
from src.memory import (
    MemoryStore, ShortTermMemory, LongTermMemory,
    MemoryRetriever, MemoryConsolidator, RetrievalStrategy
)

# Initialize memory hierarchy
stm = ShortTermMemory(capacity=10)
ltm = LongTermMemory()
retriever = MemoryRetriever()
consolidator = MemoryConsolidator()

# Add conversation turns to STM
stm.add_turn(role="user", content="I prefer pytest over unittest")
stm.add_turn(role="assistant", content="Noted. I'll use pytest for all test generation.")
stm.add_turn(role="user", content="Also, use factory_boy for test fixtures")

# Consolidate STM to LTM (extracts patterns)
result = consolidator.consolidate(stm, ltm)
print(f"Created {result.memories_created} LTM entries")
print(f"Extracted {len(result.patterns_extracted)} patterns")

# Retrieve relevant memories
memories = retriever.retrieve(
    query="testing framework",
    strategy=RetrievalStrategy.HYBRID,
    stm=stm,
    ltm=ltm,
)
for m in memories:
    print(f"  [{m.score:.2f}] {m.memory.content}")
```

## Example 5: Skill System

```python
from src.skills import SkillRegistry, SkillParser, Skill, SkillCategory

# Initialize registry
registry = SkillRegistry()

# Register skills with trigger patterns
skill = Skill(
    name="pytest-fixture",
    description="Generate pytest fixtures with proper teardown",
    content="Use @pytest.fixture with yield for cleanup...",
    category=SkillCategory.TDD_TESTING,
    trigger_patterns=["test fixture", "pytest fixture", "setup teardown"],
    tags={"python", "testing", "pytest"},
    language="python",
)
registry.register(skill)

# Find skill by trigger
results = registry.find_by_trigger("I need a test fixture for the database")
for r in results:
    print(f"  {r.skill.name} (score: {r.score:.2f}) — {r.match_reason}")

# Search with filters
results = registry.search(
    query="python testing",
    tags={"pytest"},
    language="python",
)
for r in results:
    print(f"  {r.skill.name}: {r.skill.description}")
```

## Example 6: Security Scanning

```python
from src.security import AgentShield, SecuritySeverity

shield = AgentShield()

# Scan code for vulnerabilities
code = """
import os
password = "admin123"
query = "SELECT * FROM users WHERE id = " + user_input
os.system("rm -rf " + user_path)
"""

report = shield.scan_code(code)
print(f"Scan passed: {report.passed}")
print(f"Issues found: {report.total_count}")

for issue in report.issues:
    icon = "🔴" if issue.severity == SecuritySeverity.CRITICAL else "🟡"
    print(f"  {icon} [{issue.severity.value}] {issue.message}")
    if issue.remediation:
        print(f"     Fix: {issue.remediation}")

# Scan a tool call
report = shield.scan_tool_call(
    tool_name="Bash",
    args={"command": "cat /etc/passwd | grep root > /tmp/out"},
)
print(f"\nTool call safe: {report.passed}")
```

## Example 7: Token Usage Analysis

```python
from src.monitoring import TokenObservatory
from pathlib import Path

observatory = TokenObservatory()

# Analyze a session log
report = observatory.analyze_session(Path(".lyra/sessions/events.jsonl"))

print(f"Session: {report.session_id}")
print(f"Tokens: {report.total_tokens:,} | Cost: ${report.total_cost:.4f}")
print(f"One-shot rate: {report.one_shot_rate:.1%}")
print(f"Retries: {report.retry_count}")
print()

# Activity breakdown
print("Activities:")
for activity in report.activities:
    pct = activity.tokens / report.total_tokens * 100
    print(f"  {activity.category.value:20s} {activity.tokens:>8,} tokens ({pct:5.1f}%)")

# Model breakdown
print("\nModel usage:")
for model, usage in report.model_breakdown.items():
    print(f"  {model:30s} {usage['tokens']:>10,} tokens | ${usage['cost']:.4f}")

# Waste analysis
if report.waste_patterns:
    total_waste = sum(w.wasted_cost for w in report.waste_patterns)
    print(f"\nWaste detected: ${total_waste:.4f}")
    for w in report.waste_patterns:
        print(f"  • {w.pattern.value}: {w.description}")
        print(f"    Recommendation: {w.recommendation}")
```

## Example 8: Rule Engine

```python
from src.rules import RuleEngine, Rule, RuleCategory, RuleSeverity

engine = RuleEngine()

# Register custom rules
no_todo_rule = Rule(
    rule_id="no-todo-comments",
    category=RuleCategory.CODING_STYLE,
    title="No TODO Comments",
    description="TODO comments should be converted to tracked issues",
    severity=RuleSeverity.WARNING,
    language="python",
    file_patterns=["*.py"],
)
engine.registry.register(no_todo_rule)

# Check a file
violations = engine.check_file("src/agents/primary.py")
print(f"Found {len(violations)} violations:")

for v in violations:
    print(f"  [{v.severity.value.upper()}] {v.rule_id}: {v.message}")
    if v.file_path:
        print(f"    File: {v.file_path}")

# Get statistics
stats = engine.get_statistics()
print(f"\nTotal violations: {stats['total_violations']}")
print(f"Files with violations: {stats['files_with_violations']}")
```

## Example 9: End-to-End Workflow

```python
import asyncio
from src.agents import PrimaryAgent, CodeAgent, TestAgent, ReviewAgent
from src.hooks import HookEngine, Hook, HookType
from src.memory import ShortTermMemory, MemoryConsolidator
from src.security import AgentShield

async def feature_workflow(request: str):
    # Setup
    primary = PrimaryAgent()
    primary.register_specialist(CodeAgent("code-1"))
    primary.register_specialist(TestAgent("test-1"))
    primary.register_specialist(ReviewAgent("review-1"))

    # Security gate
    shield = AgentShield()
    report = shield.scan_tool_call("Bash", {"command": request})
    if not report.passed:
        return f"Security blocked: {report.issues[0].message}"

    # Execute
    response = await primary.handle_request(request)

    # Consolidate learnings
    consolidator = MemoryConsolidator()
    stm = primary.short_term_memory
    ltm = primary.long_term_memory
    result = consolidator.consolidate(stm, ltm)
    print(f"Learned {result.memories_created} new patterns")

    stats = primary.get_statistics()
    print(f"Success rate: {stats['success_rate']:.1%}")
    print(f"Specialists: {', '.join(stats['specialists'])}")

    return response

# Run
result = asyncio.run(feature_workflow(
    "Add input validation to the user registration endpoint"
))
print(result)
```

## Example 10: ECC Agent Import

```python
from src.agents import ECCAgentImporter, UnifiedAgentRegistry
from pathlib import Path

# Initialize
registry = UnifiedAgentRegistry()
importer = ECCAgentImporter(registry)

# Import ECC agents from markdown files
result = importer.import_directory(Path(".ecc/agents/"))

print(f"Imported: {result.imported} agents")
print(f"Skipped: {result.skipped}")
print(f"Errors: {result.errors}")

# Query registered agents
agents = registry.list_agents()
for agent in agents:
    print(f"  {agent.agent_id}: {agent.capabilities}")

# Find agents for a specific task
candidates = registry.find_candidates(
    task_type="code_review",
    language="python",
)
print(f"\nPython code reviewers: {len(candidates)}")
for c in candidates:
    print(f"  {c.agent_id} (priority: {c.priority})")

# Dispatch best agent
best = registry.dispatch(
    task_type="code_review",
    language="python",
)
if best:
    print(f"\nDispatched: {best.agent_id}")
```

---

For more examples, see individual package READMEs in [`packages/`](packages/).
