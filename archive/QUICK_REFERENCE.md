# 🚀 Lyra Quick Reference Guide

**Version**: 4.0.0 | **Phase**: 1 Complete | **Status**: Production Ready

---

## 📦 Installation

```bash
cd projects/lyra
pip install -e .
```

---

## 🎯 Quick Start (30 seconds)

```python
import asyncio
from src.agents import PrimaryAgent, CodeAgent, ResearchAgent

async def main():
    # Create and setup
    primary = PrimaryAgent()
    primary.register_specialist(CodeAgent())
    primary.register_specialist(ResearchAgent())
    
    # Execute a task
    response = await primary.handle_request(
        "Implement a function to calculate fibonacci numbers"
    )
    print(response)

asyncio.run(main())
```

---

## 🤖 Available Agents

| Agent | Purpose | Capabilities |
|-------|---------|--------------|
| **PrimaryAgent** | Orchestrator | Request analysis, task routing, delegation |
| **CodeAgent** | Code tasks | Analysis, generation, refactoring, review |
| **ResearchAgent** | Research | Web search, document analysis, synthesis |
| **TestAgent** | Testing | Test generation, execution, coverage |
| **ReviewAgent** | Quality | Code review, security scan, quality check |

---

## 📋 Task Types

```python
from src.core.task import TaskType

TaskType.CODE_GENERATION    # Generate new code
TaskType.CODE_ANALYSIS      # Analyze existing code
TaskType.CODE_REFACTORING   # Refactor code
TaskType.CODE_REVIEW        # Review code quality
TaskType.RESEARCH           # Research information
TaskType.WEB_SEARCH         # Search the web
TaskType.DOCUMENT_ANALYSIS  # Analyze documents
TaskType.TEST_GENERATION    # Generate tests
TaskType.TEST_EXECUTION     # Run tests
TaskType.SECURITY_SCAN      # Security scanning
```

---

## 💡 Common Patterns

### Pattern 1: Simple Task Execution

```python
from src.core.task import Task, TaskType

task = Task(
    type=TaskType.CODE_GENERATION,
    description="Create a sorting function",
    params={"language": "python"}
)

result = await primary.execute(task)
print(result.data)
```

### Pattern 2: Parallel Execution

```python
tasks = [
    Task(type=TaskType.CODE_GENERATION, description="Task 1"),
    Task(type=TaskType.RESEARCH, description="Task 2"),
    Task(type=TaskType.TEST_GENERATION, description="Task 3"),
]

results = await primary.execute_parallel(tasks)
for result in results:
    print(f"{result.agent_id}: {result.success}")
```

### Pattern 3: Custom Agent

```python
from src.agents.base import Agent, AgentCapability
from src.core.task import Task, Result

class CustomAgent(Agent):
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="custom_task",
                description="Custom capability",
                task_types=[TaskType.GENERIC],
                confidence=0.9
            )
        ]
        super().__init__("custom_agent", capabilities)
    
    async def execute(self, task: Task) -> Result:
        # Your implementation
        return Result(
            task_id=task.task_id,
            success=True,
            data="result",
            agent_id=self.agent_id
        )
    
    def can_handle(self, task: Task) -> float:
        return 0.9 if task.type == TaskType.GENERIC else 0.0
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_primary_agent.py -v

# Run demo
python demo.py
```

---

## 📊 Monitoring

### Get Statistics

```python
stats = primary.get_statistics()
print(f"Total executions: {stats['total_executions']}")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Specialists: {stats['specialists']}")
```

### Check Agent Performance

```python
for agent in [code_agent, research_agent]:
    print(f"{agent.agent_id}:")
    print(f"  Executions: {len(agent.execution_history)}")
    print(f"  Success rate: {agent.get_success_rate():.1%}")
```

---

## 🔧 Configuration

### Environment Variables

```bash
# .env file
LYRA_LOG_LEVEL=INFO
LYRA_AGENT_TIMEOUT=300
LYRA_MAX_PARALLEL_TASKS=10
```

### Agent Configuration

```python
# Configure agent
agent = CodeAgent(agent_id="custom_code_agent")
agent.metadata["max_retries"] = 3
agent.metadata["timeout"] = 60
```

---

## 🐛 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Agent Status

```python
print(f"Status: {agent.status}")
print(f"Current task: {agent.current_task}")
print(f"History: {len(agent.execution_history)} executions")
```

### Inspect Task

```python
print(f"Task ID: {task.task_id}")
print(f"Type: {task.type}")
print(f"Status: {task.status}")
print(f"Assigned to: {task.assigned_to}")
```

---

## 📚 API Reference

### PrimaryAgent

```python
primary = PrimaryAgent()

# Register specialist
primary.register_specialist(agent)

# Unregister specialist
primary.unregister_specialist("agent_id")

# Handle request (high-level)
response = await primary.handle_request("Do something")

# Execute task (low-level)
result = await primary.execute(task)

# Parallel execution
results = await primary.execute_parallel(tasks)

# Get statistics
stats = primary.get_statistics()
```

### Agent Base

```python
agent = CustomAgent()

# Execute task
result = await agent.execute(task)

# Check if can handle
confidence = agent.can_handle(task)

# Get capability
capability = agent.get_capability(TaskType.CODE_GENERATION)

# Report progress
await agent.report_progress(0.5, "Working...")

# Get success rate
rate = agent.get_success_rate()
```

### Task

```python
task = Task(
    type=TaskType.CODE_GENERATION,
    description="Generate code",
    priority=TaskPriority.HIGH,
    params={"key": "value"}
)

# Lifecycle
task.assign_to("agent_id")
task.start()
task.complete()
task.fail()
task.cancel()
```

---

## 🎓 Best Practices

1. **Always use async/await** - The system is async-first
2. **Register specialists early** - Before executing tasks
3. **Use specific task types** - Better routing than GENERIC
4. **Handle errors gracefully** - Check result.success
5. **Monitor performance** - Track success rates
6. **Use parallel execution** - For independent tasks
7. **Provide clear descriptions** - Helps with routing

---

## 🔗 Resources

- **README**: Complete documentation
- **Demo**: `python demo.py`
- **Tests**: `pytest tests/`
- **Plans**: See `plans/` directory
- **Docs**: See `docs/` directory

---

## 🆘 Troubleshooting

### Issue: Agent not found
```python
# Check registered agents
print(primary.specialists.keys())
```

### Issue: Task fails
```python
# Check result
if not result.success:
    print(f"Error: {result.error}")
```

### Issue: Low success rate
```python
# Check execution history
for result in agent.execution_history[-10:]:
    print(f"{result.task_id}: {result.success}")
```

---

## 📞 Support

- **Issues**: GitHub Issues
- **Docs**: See `docs/` directory
- **Tests**: See `tests/` directory

---

**Built with ❤️ | Ready for Production | Phase 1 Complete ✅**
