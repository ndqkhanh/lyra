# AutoResearchClaw Integration Guide

Complete guide for integrating AutoResearchClaw features into Lyra.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Integration Points](#integration-points)
4. [Usage Patterns](#usage-patterns)
5. [Configuration](#configuration)
6. [Performance Tuning](#performance-tuning)
7. [Troubleshooting](#troubleshooting)

## Overview

The `lyra-autoresearch` package brings five key AutoResearchClaw innovations to Lyra:

| Feature | Purpose | Integration Point |
|---------|---------|-------------------|
| Citation Verification | Eliminate hallucinated citations | Research output validation |
| Structured Debates | Refine hypotheses | Pre-experiment planning |
| Self-Healing Execution | Automatic failure recovery | Task execution wrapper |
| Evolution System | Learn from failures | Memoria integration |
| HITL Gates | Flexible collaboration | Pipeline orchestration |

## Installation

### Basic Installation

```bash
cd packages/lyra-autoresearch
pip install -e .
```

### With Development Tools

```bash
pip install -e ".[dev]"
```

### Verify Installation

```python
import lyra_autoresearch
print(lyra_autoresearch.__version__)  # Should print: 1.0.0
```

## Integration Points

### 1. Citation Verification in Research Tasks

**Use Case**: Validate citations in generated research documents

```python
from lyra_autoresearch import verify_citations

def validate_research_output(document: str) -> bool:
    """Validate citations in research document"""
    report = verify_citations(document)
    
    # Fail if integrity score < 0.95
    if report.integrity_score < 0.95:
        print(f"⚠️  Low citation integrity: {report.integrity_score:.2%}")
        print(f"Hallucinated: {report.hallucinated_count}")
        return False
    
    return True
```

**Integration**: Add to Lyra's research task post-processing

### 2. Debates in Hypothesis Formation

**Use Case**: Refine research questions before expensive experiments

```python
from lyra_autoresearch import run_debate, Perspective

def refine_hypothesis(hypothesis: str, context: str) -> str:
    """Refine hypothesis through structured debate"""
    result = run_debate(
        topic=hypothesis,
        context=context,
        perspectives=[
            Perspective.SKEPTIC,
            Perspective.OPTIMIST,
            Perspective.METHODOLOGIST,
        ],
        num_rounds=2,
    )
    
    return result.final_synthesis
```

**Integration**: Add to Lyra's research planning phase

### 3. Self-Healing in Task Execution

**Use Case**: Wrap Lyra's task executor for automatic recovery

```python
from lyra_autoresearch import execute_with_healing

def execute_lyra_task(task_fn, context):
    """Execute Lyra task with self-healing"""
    
    def refine(error, ctx):
        # Adjust parameters on failure
        ctx["retry_count"] = ctx.get("retry_count", 0) + 1
        return ctx
    
    def pivot(error, ctx):
        # Change approach on repeated failure
        ctx["strategy"] = "alternative"
        return ctx
    
    result = execute_with_healing(
        task_fn=task_fn,
        refine_fn=refine,
        pivot_fn=pivot,
        context=context,
    )
    
    return result
```

**Integration**: Wrap Lyra's `TaskExecutor.execute()` method

### 4. Evolution with Memoria

**Use Case**: Learn from failures and sync to Memoria

```python
from lyra_autoresearch import EvolutionEngine, LessonCategory, LessonSeverity

# Initialize with Memoria client
evolution = EvolutionEngine(memoria_client=lyra_memoria_client)

# Record lesson on failure
evolution.record_lesson(
    category=LessonCategory.EXPERIMENT,
    severity=LessonSeverity.ERROR,
    description="Experiment failed due to insufficient data",
    context={"dataset": "small", "required": "large"},
)

# Periodic evolution (e.g., daily)
skills = evolution.evolve(sync_to_memoria=True)
```

**Integration**: Add to Lyra's task failure handlers

### 5. HITL Gates in Pipelines

**Use Case**: Add human review points to research pipelines

```python
from lyra_autoresearch import create_gate_config, HITLMode

# Create gate orchestrator
gates = create_gate_config(
    mode=HITLMode.CRITICAL_GATES,
    interactive=True,
)

# Add gates to pipeline stages
def research_pipeline():
    # Stage 1: Hypothesis
    hypothesis = generate_hypothesis()
    decision = gates.process_gate("1", "Hypothesis", hypothesis)
    if not decision.approved:
        return
    
    # Stage 2: Experiment
    results = run_experiment()
    decision = gates.process_gate("2", "Results", results)
    if not decision.approved:
        return
    
    # Continue...
```

**Integration**: Add to Lyra's pipeline orchestrator

## Usage Patterns

### Pattern 1: Research Quality Assurance

```python
def research_qa_pipeline(document: str) -> dict:
    """Complete QA pipeline for research documents"""
    
    # 1. Citation verification
    citation_report = verify_citations(document)
    
    # 2. Debate-based review
    debate_result = run_debate(
        topic="Is this research sound?",
        context=document,
        perspectives=[Perspective.SKEPTIC, Perspective.METHODOLOGIST],
    )
    
    return {
        "citation_integrity": citation_report.integrity_score,
        "peer_review": debate_result.final_synthesis,
        "approved": citation_report.integrity_score > 0.95,
    }
```

### Pattern 2: Resilient Experiment Execution

```python
def resilient_experiment(experiment_config: dict) -> dict:
    """Execute experiment with automatic recovery"""
    
    def run_exp():
        return execute_experiment(experiment_config)
    
    def refine(error, ctx):
        # Adjust hyperparameters
        ctx["learning_rate"] *= 0.5
        return ctx
    
    def pivot(error, ctx):
        # Try different architecture
        ctx["model"] = "alternative_model"
        return ctx
    
    result = execute_with_healing(
        task_fn=run_exp,
        refine_fn=refine,
        pivot_fn=pivot,
    )
    
    return result.output if result.success else None
```

### Pattern 3: Continuous Learning

```python
def continuous_learning_loop():
    """Continuous learning from research runs"""
    
    evolution = EvolutionEngine()
    
    while True:
        # Run research
        try:
            result = run_research_task()
            
            # Record success
            evolution.record_lesson(
                category=LessonCategory.EXPERIMENT,
                severity=LessonSeverity.INFO,
                description="Research succeeded",
                context={"method": result.method},
            )
        
        except Exception as e:
            # Record failure
            evolution.record_lesson(
                category=LessonCategory.EXPERIMENT,
                severity=LessonSeverity.ERROR,
                description=f"Research failed: {e}",
                context={"error": str(e)},
            )
        
        # Periodic evolution
        if should_evolve():
            skills = evolution.evolve(sync_to_memoria=True)
            print(f"Learned {len(skills)} new skills")
```

## Configuration

### Environment Variables

```bash
# Citation verification
export OPENALEX_EMAIL="your@email.com"  # Optional: polite pool access

# LLM APIs (for debates)
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."

# Evolution storage
export EVOLUTION_STORE_PATH=".evolution/lessons.jsonl"
export SKILLS_DIR=".evolution/skills"
```

### Configuration Files

Create `autoresearch_config.yaml`:

```yaml
citations:
  openalex_email: "your@email.com"
  timeout: 10
  max_retries: 3

debates:
  default_model: "claude-3-5-sonnet-20241022"
  default_rounds: 2
  default_perspectives:
    - skeptic
    - optimist
    - methodologist

execution:
  max_refines: 3
  max_pivots: 2
  checkpoint_dir: ".checkpoints"

evolution:
  store_path: ".evolution/lessons.jsonl"
  skills_dir: ".evolution/skills"
  sync_to_memoria: true

hitl:
  default_mode: "critical_gates"
  interactive: false
```

Load configuration:

```python
import yaml
from pathlib import Path

config = yaml.safe_load(Path("autoresearch_config.yaml").read_text())
```

## Performance Tuning

### Citation Verification

**Optimization**: Cache API responses

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_verify_citation(citation_text: str):
    return verify_citations(citation_text)
```

**Rate Limiting**: Respect API limits

```python
from time import sleep

def batch_verify_citations(documents: list, delay: float = 0.5):
    """Verify citations with rate limiting"""
    results = []
    for doc in documents:
        result = verify_citations(doc)
        results.append(result)
        sleep(delay)  # Respect rate limits
    return results
```

### Debates

**Optimization**: Reduce rounds for simple questions

```python
def adaptive_debate(topic: str, complexity: str):
    """Adjust debate rounds based on complexity"""
    rounds = 3 if complexity == "high" else 1
    return run_debate(topic, num_rounds=rounds)
```

### Self-Healing

**Optimization**: Early abort on critical failures

```python
from lyra_autoresearch import FailureType

def smart_healing(task_fn):
    """Self-healing with early abort"""
    
    def should_abort(failure_type):
        # Abort immediately on critical failures
        return failure_type in [
            FailureType.RESOURCE_LIMIT,
            FailureType.DEPENDENCY_ERROR,
        ]
    
    # Custom executor with abort logic
    # ...
```

## Troubleshooting

### Issue: Citation verification fails

**Symptom**: All citations marked as HALLUCINATED

**Solution**: Check network connectivity and API access

```python
from lyra_autoresearch.citations import ArxivClient

client = ArxivClient()
result = client.lookup_by_id("1706.03762")
if result is None:
    print("Network or API issue")
```

### Issue: Debates timeout

**Symptom**: Debate hangs or times out

**Solution**: Reduce model size or rounds

```python
result = run_debate(
    topic=topic,
    context=context,
    num_rounds=1,  # Reduce rounds
    model="claude-3-haiku-20240307",  # Faster model
)
```

### Issue: Self-healing loops infinitely

**Symptom**: Executor never completes

**Solution**: Reduce max iterations

```python
result = execute_with_healing(
    task_fn=task,
    max_refines=2,  # Reduce from default 3
    max_pivots=1,   # Reduce from default 2
)
```

### Issue: Evolution not syncing to Memoria

**Symptom**: Skills not appearing in Memoria

**Solution**: Check Memoria client connection

```python
evolution = EvolutionEngine(memoria_client=your_client)

# Test connection
try:
    skills = evolution.evolve(sync_to_memoria=True)
    print(f"Synced {len(skills)} skills")
except Exception as e:
    print(f"Memoria sync failed: {e}")
```

## Best Practices

1. **Citation Verification**: Run on all generated research documents
2. **Debates**: Use for high-stakes decisions, skip for routine tasks
3. **Self-Healing**: Wrap all experimental code execution
4. **Evolution**: Record lessons consistently, evolve periodically
5. **HITL Gates**: Start with CRITICAL_GATES mode, adjust based on needs

## Next Steps

- Read [API Reference](README.md#api-reference)
- Try [Example Scripts](examples/)
- Review [Test Suite](tests/)
- Check [Performance Benchmarks](docs/benchmarks.md)

## Support

- Issues: [GitHub Issues](https://github.com/your-org/lyra/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/lyra/discussions)
- Email: support@lyra.ai
