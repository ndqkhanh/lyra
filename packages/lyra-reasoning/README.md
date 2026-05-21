# Lyra Reasoning - Deep Reasoning Research Agent

A breakthrough reasoning system that combines test-time compute scaling (o1/o3-style) with multiple reasoning engines, multi-level verification, and self-improvement capabilities.

## 🌟 Key Features

### Test-Time Compute Scaling
- **Dynamic Budget Allocation**: Automatically scales compute based on task difficulty
- **Adaptive Depth Control**: Quick, standard, or comprehensive reasoning modes
- **Smart Resource Management**: Efficient token and time budget utilization

### Multiple Reasoning Engines
- **Chain of Thought (CoT)**: Step-by-step logical reasoning
- **Tree Search**: Explores multiple solution paths with backtracking
- **Multi-Agent Debate**: Synthesizes insights from multiple perspectives
- **Hypothesis Generation**: Creates and evaluates novel hypotheses

### Multi-Level Verification
- **Step Verification**: Validates each reasoning step
- **Trace Verification**: Ensures logical coherence across the entire reasoning chain
- **External Verification**: Checks claims against evidence
- **Cross-Agent Verification**: Multiple independent verifiers for consensus

### Reasoning Memory
- **Pattern Recognition**: Learns successful reasoning patterns
- **Strategy Performance Tracking**: Monitors which strategies work best
- **Cross-Session Learning**: Builds knowledge across multiple sessions
- **Similar Task Retrieval**: Finds and reuses relevant past reasoning

### Self-Improvement
- **Evolution Engine**: Automatically improves reasoning capabilities
- **Performance Analysis**: Identifies strengths and weaknesses
- **Strategy Synthesis**: Creates new reasoning approaches
- **Continuous Learning**: Gets better with every task

## 🚀 Quick Start

### Installation

```bash
# Install from source
cd projects/lyra/packages/lyra-reasoning
pip install -e .

# Or install from PyPI (when published)
pip install lyra-reasoning
```

### Basic Usage

```python
from lyra_reasoning import DeepReasoningAgent

# Initialize agent
agent = DeepReasoningAgent()

# Simple reasoning
result = agent.reason(
    task="Explain why the sky appears blue",
    strategy="auto",  # Automatically selects best strategy
    depth="standard",
)

print(result.conclusion)
print(f"Verification Score: {result.verification_score:.2f}")
```

### Advanced Usage

```python
from lyra_reasoning import DeepReasoningAgent, ReasoningConfig, ReasoningStrategy

# Custom configuration
config = ReasoningConfig(
    strategy=ReasoningStrategy.TREE_SEARCH,
    depth="comprehensive",
    max_tokens=15000,
    verification_threshold=0.8,
    enable_backtracking=True,
)

agent = DeepReasoningAgent()

result = agent.reason(
    task="Design an optimal distributed consensus algorithm",
    config=config,
)
```

## 📚 Examples

### Chain of Thought Reasoning

```python
result = agent.reason(
    task="Prove that the square root of 2 is irrational",
    strategy="cot",
    depth="comprehensive",
)
```

### Tree Search for Optimal Solutions

```python
result = agent.reason(
    task="Find the optimal approach to implement a caching system",
    strategy="tree_search",
    depth="comprehensive",
)
```

### Multi-Agent Debate

```python
result = agent.reason(
    task="Should AI research be regulated?",
    strategy="debate",
    depth="comprehensive",
)
```

### Hypothesis Generation

```python
result = agent.reason(
    task="Generate novel hypotheses for improving battery technology",
    strategy="hypothesis",
    depth="comprehensive",
)
```

### Getting Full Reasoning Trace

```python
trace = agent.get_full_trace(
    task="Analyze the complexity of quicksort",
    strategy="cot",
    depth="comprehensive",
)

for step in trace.steps:
    print(f"{step.step_type.value}: {step.content}")
    print(f"Verification: {step.verification_score:.2f}\n")
```

## 🧠 Reasoning Strategies

### Auto (Recommended)
Automatically selects the best strategy based on:
- Task difficulty
- Task type (proof, analysis, generation, etc.)
- Historical performance
- Available compute budget

### Chain of Thought (CoT)
Best for:
- Logical reasoning
- Mathematical proofs
- Step-by-step analysis
- Explanations

### Tree Search
Best for:
- Optimization problems
- Multiple solution paths
- Complex decision-making
- Algorithm design

### Multi-Agent Debate
Best for:
- Controversial topics
- Multiple perspectives
- Balanced analysis
- Decision-making under uncertainty

### Hypothesis Generation
Best for:
- Research ideation
- Novel solutions
- Creative thinking
- Exploratory analysis

## 🎯 Reasoning Depth

### Quick
- Fast responses
- Lower token usage
- Good for simple tasks
- ~1,000-3,000 tokens

### Standard (Default)
- Balanced performance
- Moderate token usage
- Good for most tasks
- ~3,000-10,000 tokens

### Comprehensive
- Deep analysis
- Higher token usage
- Best for complex tasks
- ~10,000-30,000 tokens

## 🔍 Verification System

The verification system provides multi-level quality assurance:

```python
result = agent.reason(task="...", strategy="cot", depth="comprehensive")

# Overall verification score (0.0 - 1.0)
print(f"Overall: {result.verification_score:.2f}")

# Detailed metrics
print(f"Step Scores: {result.metadata['step_scores']}")
print(f"Trace Score: {result.metadata['trace_score']}")
print(f"Passed: {result.success}")
```

### Verification Levels

1. **Step Verification**: Each reasoning step is validated
2. **Trace Verification**: Overall logical coherence
3. **External Verification**: Claims checked against evidence
4. **Cross-Agent Verification**: Multiple independent verifiers

## 💾 Memory and Learning

### Storing and Retrieving Reasoning

```python
# Reasoning is automatically stored
agent.reason(task="Explain neural networks", strategy="cot", depth="standard")

# Retrieve similar past reasoning
similar = agent.memory.retrieve_similar("deep learning", k=5)

# Get best strategy for a task type
best_strategy = agent.memory.get_best_strategy("machine learning")
```

### Learned Patterns

```python
# Get learned reasoning patterns
patterns = agent.memory.get_patterns()

for pattern in patterns:
    print(f"{pattern.name}: {pattern.success_rate:.2%} success rate")
```

### Strategy Performance

```python
# Get performance metrics
performance = agent.memory.get_strategy_performance()

for perf in performance:
    print(f"{perf.strategy.value}:")
    print(f"  Success Rate: {perf.success_rate:.2%}")
    print(f"  Avg Tokens: {perf.avg_tokens:.0f}")
```

## 🔄 Evolution and Self-Improvement

```python
# Run evolution cycle
report = agent.evolve()

print("New Strategies:", report['new_strategies'])
print("Insights:", report['insights'])
print("Recommendations:", report['recommendations'])

# Get statistics
stats = agent.get_stats()
print(f"Total Traces: {stats['total_traces']}")
print(f"Patterns Learned: {stats['patterns_learned']}")
```

## 📊 Performance Benchmarks

### Latency
- Simple tasks: < 10s
- Medium tasks: 10-30s
- Complex tasks: 30-120s

### Token Efficiency
- Quick depth: 1,000-3,000 tokens
- Standard depth: 3,000-10,000 tokens
- Comprehensive depth: 10,000-30,000 tokens

### Verification Accuracy
- High-quality reasoning: > 0.8 score
- Good reasoning: 0.6-0.8 score
- Needs improvement: < 0.6 score

## 🧪 Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run benchmarks
pytest tests/benchmarks/ -v -s

# Run with coverage
pytest --cov=lyra_reasoning --cov-report=html
```

## 📖 API Reference

### DeepReasoningAgent

```python
class DeepReasoningAgent:
    def __init__(
        self,
        api_key: Optional[str] = None,
        storage_path: str = ".lyra/reasoning/",
    )
    
    def reason(
        self,
        task: str,
        strategy: str = "auto",
        depth: str = "standard",
        config: Optional[ReasoningConfig] = None,
    ) -> ReasoningResult
    
    def get_full_trace(
        self,
        task: str,
        **kwargs
    ) -> ReasoningTrace
    
    def evolve(self) -> dict
    
    def get_stats(self) -> dict
```

### ReasoningConfig

```python
@dataclass
class ReasoningConfig:
    strategy: ReasoningStrategy = ReasoningStrategy.AUTO
    depth: ReasoningDepth = ReasoningDepth.STANDARD
    max_tokens: int = 10000
    max_steps: int = 50
    temperature: float = 0.7
    verification_threshold: float = 0.7
    enable_backtracking: bool = True
    enable_verification: bool = True
```

### ReasoningResult

```python
@dataclass
class ReasoningResult:
    task: str
    conclusion: str
    reasoning_trace: dict
    verification_score: float
    strategy_used: ReasoningStrategy
    tokens_used: int
    duration: float
    success: bool
    metadata: dict
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Inspired by:
- OpenAI's o1/o3 test-time compute scaling
- Anthropic's Constitutional AI
- Google's Chain-of-Thought prompting
- Meta's Tree of Thoughts

## 📞 Support

- Documentation: [docs.lyra-ai.dev](https://docs.lyra-ai.dev)
- Issues: [GitHub Issues](https://github.com/yourusername/lyra/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/lyra/discussions)

## 🗺️ Roadmap

- [ ] Additional reasoning strategies (Monte Carlo Tree Search, Beam Search)
- [ ] Multi-modal reasoning (images, code, data)
- [ ] Distributed reasoning across multiple agents
- [ ] Real-time reasoning optimization
- [ ] Integration with external knowledge bases
- [ ] Custom verification rules
- [ ] Reasoning visualization tools
- [ ] Production deployment guides

---

Built with ❤️ by the Lyra team
