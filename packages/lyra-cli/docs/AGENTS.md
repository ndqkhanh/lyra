# Agent System

## Overview

Lyra's agent system provides specialized subagents for domain-specific tasks, enabling efficient delegation and parallel execution of complex workflows.

## Architecture

The agent system consists of three core components:

1. **AgentMetadata**: Data structure for agent definitions
2. **AgentRegistry**: Loads and manages agents from directories
3. **AgentOrchestrator**: Delegates tasks to appropriate agents

## Agent Format

Agents are defined as Markdown files with YAML frontmatter:

```markdown
---
name: agent-name
description: When to use this agent
tools: [Read, Write, Edit, Bash]
model: sonnet  # haiku, sonnet, opus
origin: ECC
---

# Agent Name

Agent documentation here...
```

## Available Agents

### Core Agents (10)

1. **planner** - Implementation planning for complex features
2. **architect** - System design and architectural decisions
3. **tdd-guide** - Test-driven development workflow
4. **code-reviewer** - Code quality and maintainability review
5. **security-reviewer** - Security vulnerability detection
6. **build-error-resolver** - Build and compilation error fixing
7. **refactor-cleaner** - Dead code cleanup and refactoring
8. **doc-updater** - Documentation and codemap updates
9. **python-reviewer** - Python-specific code review
10. **django-reviewer** - Django-specific code review

### Language-Specific Agents (20)

11. **typescript-reviewer** - TypeScript/JavaScript code review specialist
12. **go-reviewer** - Go code review and build resolution
13. **rust-reviewer** - Rust code review and build resolution
14. **kotlin-reviewer** - Kotlin code review and build resolution
15. **cpp-reviewer** - C++ code review and build resolution
16. **java-reviewer** - Java code review and build resolution
17. **swift-reviewer** - Swift code review for iOS/macOS
18. **php-reviewer** - PHP code review for web applications
19. **ruby-reviewer** - Ruby and Rails code review
20. **elixir-reviewer** - Elixir and Phoenix code review
21. **scala-reviewer** - Scala code review for backend
22. **clojure-reviewer** - Clojure code review for backend
23. **haskell-reviewer** - Haskell code review for functional programming
24. **ocaml-reviewer** - OCaml code review for functional programming
25. **fsharp-reviewer** - F# code review for .NET
26. **dart-reviewer** - Dart and Flutter code review
27. **lua-reviewer** - Lua code review for embedded/game development
28. **r-reviewer** - R code review for data analysis
29. **julia-reviewer** - Julia code review for scientific computing
30. **zig-reviewer** - Zig code review for systems programming

### Domain-Specific Agents (15)

31. **database-reviewer** - Database design and query optimization
32. **frontend-patterns** - Frontend architecture and patterns
33. **backend-patterns** - Backend architecture and patterns
34. **api-design** - API design and documentation
35. **devops-specialist** - DevOps practices and automation
36. **cloud-infrastructure** - Cloud infrastructure design and optimization
37. **mobile-development** - Mobile development patterns (iOS/Android)
38. **ml-ai-specialist** - Machine learning and AI development
39. **data-engineering** - Data engineering and pipeline design
40. **security-specialist** - Security engineering and vulnerability analysis
41. **performance-specialist** - Performance optimization and profiling
42. **accessibility-specialist** - Web accessibility and WCAG compliance
43. **i18n-specialist** - Internationalization and localization
44. **testing-specialist** - Testing strategy and quality assurance
45. **documentation-specialist** - Technical documentation and API docs

### Workflow Agents (15)

46. **e2e-runner** - End-to-end test execution (Playwright)
47. **integration-test-runner** - Integration test execution
48. **load-test-runner** - Load and performance testing
49. **benchmark-runner** - Code benchmarking and profiling
50. **migration-specialist** - Database and code migrations
51. **deployment-specialist** - Deployment automation and strategies
52. **monitoring-specialist** - Monitoring and observability setup
53. **incident-response** - Incident response and troubleshooting
54. **code-migration** - Code migration and large-scale refactoring
55. **legacy-modernizer** - Legacy code modernization
56. **tech-debt-analyzer** - Technical debt analysis and prioritization
57. **dependency-updater** - Dependency updates and security patches
58. **license-checker** - License compliance and auditing
59. **code-metrics** - Code metrics and quality analysis
60. **architecture-auditor** - Architecture review and validation

## Usage

### Loading Agents

```python
from pathlib import Path
from lyra_cli.core.agent_registry import AgentRegistry

# Initialize registry with agent directories
registry = AgentRegistry(agent_dirs=[
    Path("src/lyra_cli/agents"),
    Path.home() / ".lyra" / "agents"
])

# Load all agents
agents = registry.load_agents()
```

### Delegating Tasks

```python
from lyra_cli.core.agent_orchestrator import AgentOrchestrator

# Create orchestrator
orchestrator = AgentOrchestrator(registry)

# Delegate to specific agent
result = orchestrator.delegate("planner", "Plan implementation of feature X")

if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

### Searching Agents

```python
# Search by name or description
results = registry.search_agents("review")

for agent in results:
    print(f"{agent.name}: {agent.description}")
```

## Agent Directories

Agents are loaded from multiple directories in priority order:

1. **Built-in**: `src/lyra_cli/agents/` - Core agents shipped with Lyra
2. **User**: `~/.lyra/agents/` - User-defined global agents
3. **Project**: `.lyra/agents/` - Project-specific agents

## Creating Custom Agents

Create a new agent by adding a Markdown file to your agent directory:

```markdown
---
name: my-custom-agent
description: Custom agent for specific task
tools: [Read, Write]
model: sonnet
origin: user
---

# My Custom Agent

## Purpose
What this agent does...

## When to Use
When to invoke this agent...

## Capabilities
What this agent can do...
```

## Model Selection

Choose the appropriate model for your agent:

- **haiku**: Fast, lightweight tasks (90% of Sonnet capability, 3x cost savings)
- **sonnet**: Standard development work (best coding model)
- **opus**: Complex reasoning, architectural decisions

## Best Practices

1. **Delegate Early**: Route work to specialists as soon as task type is clear
2. **Use Specific Agents**: Prefer specialized agents over generic ones
3. **Parallel Execution**: Delegate independent tasks in parallel
4. **Verify Results**: Always check agent results before proceeding
5. **Test Coverage**: Ensure agents maintain 80%+ test coverage

## Testing

Run agent system tests:

```bash
cd packages/lyra-cli
python -m pytest tests/agents/ -v
```

## API Reference

### AgentMetadata

```python
@dataclass
class AgentMetadata:
    name: str
    description: str
    tools: List[str]
    model: str
    origin: str
    file_path: Optional[str] = None
```

### AgentRegistry

```python
class AgentRegistry:
    def load_agents() -> Dict[str, AgentMetadata]
    def get_agent(name: str) -> Optional[AgentMetadata]
    def search_agents(query: str) -> List[AgentMetadata]
    def list_agents() -> List[AgentMetadata]
```

### AgentOrchestrator

```python
class AgentOrchestrator:
    def delegate(agent_name: str, task: str, context: Optional[Dict]) -> AgentResult
    def auto_delegate(task: str, context: Optional[Dict]) -> AgentResult
```

### AgentResult

```python
@dataclass
class AgentResult:
    success: bool
    output: str
    error: Optional[str] = None
```
