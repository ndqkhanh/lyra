# Quick Start Guide - Lyra Reasoning

Get started with Lyra Reasoning in 5 minutes!

## Installation

```bash
cd projects/lyra/packages/lyra-reasoning
pip install -e .
```

## Set Up API Key

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

Or in Python:
```python
import os
os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"
```

## Your First Reasoning Task

```python
from lyra_reasoning import DeepReasoningAgent

# Create agent
agent = DeepReasoningAgent()

# Simple reasoning
result = agent.reason(
    task="Explain why the sky appears blue",
    strategy="auto",  # Automatically selects best strategy
    depth="standard",  # Balanced performance
)

# View results
print("Conclusion:")
print(result.conclusion)
print(f"\nVerification Score: {result.verification_score:.2f}")
print(f"Strategy Used: {result.strategy_used.value}")
print(f"Tokens Used: {result.tokens_used}")
```

## Try Different Strategies

### Chain of Thought (Step-by-Step)
```python
result = agent.reason(
    task="Prove that the square root of 2 is irrational",
    strategy="cot",
    depth="comprehensive",
)
```

### Tree Search (Optimization)
```python
result = agent.reason(
    task="Find the optimal approach to implement a caching system",
    strategy="tree_search",
    depth="comprehensive",
)
```

### Multi-Agent Debate (Multiple Perspectives)
```python
result = agent.reason(
    task="Should AI research be regulated?",
    strategy="debate",
    depth="comprehensive",
)
```

### Hypothesis Generation (Research)
```python
result = agent.reason(
    task="Generate novel hypotheses for improving battery technology",
    strategy="hypothesis",
    depth="comprehensive",
)
```

## Adjust Reasoning Depth

```python
# Quick - Fast, less detailed
result = agent.reason(task="What is 2 + 2?", depth="quick")

# Standard - Balanced (default)
result = agent.reason(task="Explain photosynthesis", depth="standard")

# Comprehensive - Deep, detailed
result = agent.reason(task="Analyze quantum entanglement", depth="comprehensive")
```

## Get Full Reasoning Trace

```python
trace = agent.get_full_trace(
    task="Analyze the complexity of quicksort",
    strategy="cot",
    depth="comprehensive",
)

# View each step
for i, step in enumerate(trace.steps, 1):
    print(f"\nStep {i} ({step.step_type.value}):")
    print(step.content)
    print(f"Verification: {step.verification_score:.2f}")
```

## View Statistics

```python
# Get agent statistics
stats = agent.get_stats()

print(f"Total Traces: {stats['total_traces']}")
print(f"Patterns Learned: {stats['patterns_learned']}")

# Strategy performance
for perf in stats['strategy_performance']:
    print(f"\n{perf['strategy']}:")
    print(f"  Success Rate: {perf['success_rate']:.2%}")
    print(f"  Avg Tokens: {perf['avg_tokens']:.0f}")
```

## Self-Improvement

```python
# Run evolution cycle
report = agent.evolve()

print("Insights:")
for insight in report['insights']:
    print(f"  - {insight}")

print("\nRecommendations:")
for rec in report['recommendations']:
    print(f"  - {rec}")
```

## Custom Configuration

```python
from lyra_reasoning import ReasoningConfig, ReasoningStrategy

config = ReasoningConfig(
    strategy=ReasoningStrategy.TREE_SEARCH,
    depth="comprehensive",
    max_tokens=15000,
    max_steps=100,
    temperature=0.8,
    verification_threshold=0.8,
    enable_backtracking=True,
)

result = agent.reason(
    task="Design an optimal distributed consensus algorithm",
    config=config,
)
```

## Common Patterns

### Research Pipeline
```python
# 1. Generate hypotheses
hypotheses = agent.reason(
    task="Generate research hypotheses for quantum computing",
    strategy="hypothesis",
    depth="comprehensive",
)

# 2. Analyze feasibility
analysis = agent.reason(
    task="Analyze the feasibility of quantum error correction",
    strategy="cot",
    depth="comprehensive",
)

# 3. Debate approach
debate = agent.reason(
    task="What's the best approach to quantum error correction?",
    strategy="debate",
    depth="comprehensive",
)
```

### Iterative Refinement
```python
# Initial solution
v1 = agent.reason(
    task="Design a distributed consensus algorithm",
    strategy="tree_search",
    depth="standard",
)

# Refine
v2 = agent.reason(
    task="Improve the consensus algorithm for fault tolerance",
    strategy="tree_search",
    depth="comprehensive",
)

# Optimize
v3 = agent.reason(
    task="Optimize the algorithm for performance",
    strategy="tree_search",
    depth="comprehensive",
)

print(f"Improvement: {v3.verification_score - v1.verification_score:.2f}")
```

## Tips for Best Results

### 1. Choose the Right Strategy
- **auto**: Let the agent decide (recommended)
- **cot**: Logical reasoning, proofs, explanations
- **tree_search**: Optimization, multiple solutions
- **debate**: Controversial topics, balanced analysis
- **hypothesis**: Research, novel ideas

### 2. Adjust Depth Based on Task
- **quick**: Simple questions, fast answers
- **standard**: Most tasks, balanced
- **comprehensive**: Complex problems, deep analysis

### 3. Monitor Verification Scores
- **> 0.8**: High quality reasoning
- **0.6-0.8**: Good reasoning
- **< 0.6**: May need refinement

### 4. Use Memory
```python
# Retrieve similar past reasoning
similar = agent.memory.retrieve_similar("machine learning", k=5)

# Get best strategy for task type
best = agent.memory.get_best_strategy("algorithm analysis")
```

### 5. Evolve Regularly
```python
# After ~20-50 reasoning tasks
if agent.get_stats()['total_traces'] >= 20:
    report = agent.evolve()
```

## Troubleshooting

### API Key Issues
```python
# Check if key is set
import os
print(os.environ.get("ANTHROPIC_API_KEY"))
```

### Low Verification Scores
- Try increasing depth: `depth="comprehensive"`
- Use more specific tasks
- Check if task is too ambiguous

### High Token Usage
- Use `depth="quick"` for simple tasks
- Set `max_tokens` in config
- Monitor with `result.tokens_used`

### Slow Performance
- Use `depth="quick"` for faster results
- Check task complexity
- Consider using simpler strategies

## Next Steps

1. **Read the full README**: `README.md`
2. **Try the examples**: `examples/basic_usage.py`
3. **Explore advanced features**: `examples/advanced_usage.py`
4. **Check the API reference**: See `README.md` API section
5. **Contribute**: See `CONTRIBUTING.md`

## Getting Help

- **Documentation**: Check README.md
- **Examples**: See examples/ directory
- **Issues**: GitHub Issues
- **Questions**: GitHub Discussions

## Example Output

```
Task: Explain why the sky appears blue

Conclusion:
The sky appears blue due to Rayleigh scattering. When sunlight enters Earth's 
atmosphere, it collides with gas molecules. Blue light has a shorter wavelength 
and is scattered more than other colors, making the sky appear blue to our eyes.

Verification Score: 0.87
Strategy Used: cot
Tokens Used: 2,450
Duration: 8.3s
Success: True
```

Happy reasoning! 🚀
