# 🚀 Lyra - Autonomous Team Orchestration AI System

**Version 4.0.0** | Multi-Agent AI Orchestration Platform

Lyra is a sophisticated multi-agent AI system that coordinates specialized agents to work together like a high-performing human team. It implements autonomous task decomposition, intelligent delegation, and adaptive learning.

---

## ✨ Features

### 🎯 Core Capabilities

- **Multi-Agent Orchestration**: Primary agent coordinates specialist agents
- **Intelligent Task Routing**: Automatic capability matching and delegation
- **Parallel Execution**: Execute multiple tasks concurrently
- **Progress Tracking**: Real-time progress reporting and monitoring
- **Adaptive Learning**: Agents learn from execution history
- **Inter-Agent Communication**: Message-based coordination

### 🤖 Specialist Agents

1. **Code Agent** - Code analysis, generation, refactoring, and review
2. **Research Agent** - Web search, document analysis, information synthesis
3. **Test Agent** - Test generation, execution, and coverage analysis
4. **Review Agent** - Code review, security scanning, quality assessment

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Primary Agent                         │
│              (Orchestrator & Coordinator)                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┐
        │            │            │            │
   ┌────▼───┐  ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
   │  Code  │  │Research│  │  Test  │  │ Review │
   │ Agent  │  │ Agent  │  │ Agent  │  │ Agent  │
   └────────┘  └────────┘  └────────┘  └────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                     │
        ┌────────────▼────────────────────────┐
        │      Coordination Layer             │
        │  • Task Allocator                   │
        │  • Load Balancer                    │
        │  • Dependency Manager               │
        │  • Conflict Resolver                │
        └─────────────────────────────────────┘
```

### Key Components

**Phase 1: Agent System**
- **Agent Base Classes**: Abstract interfaces for all agents
- **Task System**: Structured task definitions and results
- **Capability Matching**: Confidence-based agent selection
- **Message Queue**: Asynchronous inter-agent communication
- **Execution History**: Performance tracking and learning

**Phase 2: Coordination Layer**
- **Task Allocator**: Intelligent task routing with multiple strategies
- **Load Balancer**: Workload distribution and monitoring
- **Dependency Manager**: Task ordering and graph analysis
- **Conflict Resolver**: Resource management and deadlock prevention

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
cd projects/lyra

# Install dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Basic Usage

```python
import asyncio
from src.agents import PrimaryAgent, CodeAgent, ResearchAgent

async def main():
    # Create primary agent
    primary = PrimaryAgent()
    
    # Register specialists
    primary.register_specialist(CodeAgent())
    primary.register_specialist(ResearchAgent())
    
    # Handle a request
    response = await primary.handle_request(
        "Implement a function to calculate fibonacci numbers"
    )
    print(response)

asyncio.run(main())
```

### Run Demo

```bash
# Run the interactive demo
python demo.py
```

---

## 📖 Usage Examples

### Example 1: Code Generation

```python
from src.agents import PrimaryAgent, CodeAgent
from src.core.task import Task, TaskType

primary = PrimaryAgent()
primary.register_specialist(CodeAgent())

task = Task(
    type=TaskType.CODE_GENERATION,
    description="Generate a sorting algorithm",
    params={"language": "python"}
)

result = await primary.execute(task)
print(result.data)
```

### Example 2: Research Task

```python
from src.agents import PrimaryAgent, ResearchAgent

primary = PrimaryAgent()
primary.register_specialist(ResearchAgent())

response = await primary.handle_request(
    "Research best practices for async Python programming"
)
print(response)
```

### Example 3: Parallel Execution

```python
from src.core.task import Task, TaskType

tasks = [
    Task(type=TaskType.CODE_GENERATION, description="Implement auth"),
    Task(type=TaskType.RESEARCH, description="Research OAuth 2.0"),
    Task(type=TaskType.TEST_GENERATION, description="Generate tests"),
]

results = await primary.execute_parallel(tasks)
for result in results:
    print(f"{result.agent_id}: {result.success}")
```

---


## 🧬 AGI Architecture (5 Plans, 19 Packages)

Lyra's AGI implementation is organized into 5 breakthrough plans spanning 19 new packages + 9 upgrade modules.

### The 5 Plans

| Plan | Code Name | What It Does | Packages |
|------|-----------|-------------|----------|
| 🏰 | **Citadel** | Maximum safety enables maximum autonomy | verification-mesh, hbhc, viper-mcp, attestor |
| 🔮 | **Oracle** | Deep causal understanding of everything | causal-graph, counterfactual, science-pipeline, claim-verification |
| 🦎 | **Chameleon** | Perfect adaptation to any environment | drift-detector, skill-weaver, context-profiler, competence-map |
| 🧬 | **Singularity** | Recursive self-improvement → superintelligence | meta-evolution, recursive-reward, fork-worker |
| 🐝 | **Superorganism** | Collective intelligence > individual brilliance | colony, emergent-coord, gossip-memory, agent-lifecycle |

### Core Upgrades

| Upgrade | What It Does |
|---------|-------------|
| **Agent Loop 2.0** | Event-sourced, multi-stream, speculative, adaptable |
| **Memory Graph Tier** | KnowledgeGraph + MMR reranking + ACT-R decay + AutoDreamer + Federation |
| **MOSS Evolution** | Source-level self-modification with user-consent gates |
| **Competence Retrieval** | Context-aware skill ranking with regression protection |
| **Sibyl Harnesses** | Scientific trial-and-error for research agents |
| **Coalition Coordinator** | Task-driven agent coalition formation |
| **SpecBench Eval** | Multi-level evaluation with reward hacking detection |
| **VIPER-MCP Scan** | Taint-style vulnerability detection for MCP servers |
| **AGI Orchestrator** | Compound layer connecting all 5 plans |

### Run AGI Tests

```bash
# Install all AGI packages
make install-agi

# Run all AGI tests
make test-agi

# Run full pipeline integration test
python3 -m pytest tests/test_full_agi_pipeline.py -v
```

---

## 🧪 Testing

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_primary_agent.py

# Run with verbose output
pytest -v
```

---

## 📊 Project Structure

```
lyra/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── base.py         # Base agent classes
│   │   ├── primary.py      # Primary orchestrator
│   │   ├── code_agent.py   # Code specialist
│   │   ├── research_agent.py
│   │   ├── test_agent.py
│   │   └── review_agent.py
│   ├── core/               # Core types
│   │   └── task.py         # Task and result types
│   ├── coordination/       # Coordination logic (future)
│   ├── memory/            # Memory system (future)
│   └── safety/            # Safety layer (future)
├── tests/                 # Test suite
│   ├── test_task.py
│   ├── test_agents.py
│   └── test_primary_agent.py
├── config/                # Configuration files
├── docs/                  # Documentation
├── plans/                 # Implementation plans
├── demo.py               # Interactive demo
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

---

## 🎯 Roadmap

### Phase 1: Foundation ✅ (Complete)
- [x] Agent base classes
- [x] Task/Result types
- [x] Primary agent orchestrator
- [x] 4 specialist agents
- [x] Basic tests
- [x] Demo script
- [x] 71% test coverage

### Phase 2: Coordination ✅ (Complete)
- [x] Task allocator with multiple strategies
- [x] Load balancer with monitoring
- [x] Dependency manager with graph analysis
- [x] Conflict resolver with deadlock detection
- [x] 66 comprehensive tests
- [x] 95% coordination layer coverage
- [x] 83% overall coverage

### Phase 3: Intelligence
- [ ] Performance tracker
- [ ] Strategy learner
- [ ] Adaptive allocator
- [ ] Self-improvement

### Phase 4: Production
- [ ] Memory system
- [ ] Safety layer
- [ ] Monitoring
- [ ] Deployment

---

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Configure logging
export LYRA_LOG_LEVEL=INFO

# Optional: Configure agent timeouts
export LYRA_AGENT_TIMEOUT=300
```

### Agent Configuration

Agents can be configured via their constructors:

```python
code_agent = CodeAgent(agent_id="custom_code_agent")
code_agent.metadata["max_retries"] = 3
```

---

## 📈 Performance

Current implementation (Phase 1):

- **Task Routing**: < 10ms
- **Agent Selection**: < 5ms
- **Parallel Execution**: 3-4x speedup for independent tasks
- **Memory Footprint**: ~50MB base + ~10MB per agent

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run linting
ruff check src/
black src/

# Run type checking
mypy src/
```

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- Inspired by AutoGPT, LangChain, and CrewAI
- Built on modern async Python patterns
- Designed for extensibility and production use

---

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

## 🎓 Learn More

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Implementation Plans](plans/)
- [API Reference](docs/API.md)
- [Contributing Guide](CONTRIBUTING.md)

---

**Built with ❤️ by the Lyra Team**

*Empowering AI agents to work together like humans*
