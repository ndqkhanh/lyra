# Lyra AutoResearch

Complete AutoResearchClaw integration for Lyra - bringing state-of-the-art autonomous research capabilities to the Lyra ecosystem.

## Overview

This package implements five key innovations from AutoResearchClaw (arXiv:2605.20025):

1. **4-Layer Citation Verification** - Eliminates hallucinated citations
2. **Structured Multi-Agent Debates** - Refines hypotheses through adversarial thinking
3. **Self-Healing Execution** - Automatic failure recovery with Pivot/Refine loops
4. **Cross-Run Evolution** - Learns from failures across research runs
5. **7-Mode HITL Collaboration** - Flexible human-AI collaboration spectrum

## Installation

```bash
cd packages/lyra-autoresearch
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### Citation Verification

```python
from lyra_autoresearch import verify_citations

# Verify citations in a document
text = """
Recent work on transformers [Vaswani et al., 2017] has shown...
See arXiv:1706.03762 for details.
"""

report = verify_citations(text)
print(f"Integrity Score: {report.integrity_score:.2f}")
print(f"Verified: {report.verified_count}/{report.total_count}")

for result in report.results:
    print(f"  {result.citation.raw_text}: {result.status.value}")
```

### Structured Debates

```python
from lyra_autoresearch import run_debate, Perspective
from anthropic import Anthropic

# Run a debate to refine a hypothesis
client = Anthropic()

result = run_debate(
    topic="Can we improve transformer efficiency with sparse attention?",
    context="Current transformers have O(n²) complexity...",
    perspectives=[
        Perspective.SKEPTIC,
        Perspective.OPTIMIST,
        Perspective.METHODOLOGIST,
    ],
    num_rounds=2,
    llm_client=client,
)

print(result.final_synthesis)
print(f"Consensus: {result.consensus_reached}")
```

### Self-Healing Execution

```python
from lyra_autoresearch import execute_with_healing

def risky_task():
    # Task that might fail
    result = complex_computation()
    return result

def refine_approach(error, context):
    # Adjust parameters on failure
    context["retry_count"] = context.get("retry_count", 0) + 1
    return context

def pivot_hypothesis(error, context):
    # Fundamental change on repeated failure
    context["approach"] = "alternative_method"
    return context

result = execute_with_healing(
    task_fn=risky_task,
    refine_fn=refine_approach,
    pivot_fn=pivot_hypothesis,
    max_refines=3,
    max_pivots=2,
)

if result.success:
    print(f"Success after {result.iterations} iterations")
    print(f"Insights: {result.insights}")
```

### Evolution System

```python
from lyra_autoresearch import (
    EvolutionEngine,
    LessonCategory,
    LessonSeverity,
)

# Initialize evolution engine
engine = EvolutionEngine()

# Record lessons from failures
engine.record_lesson(
    category=LessonCategory.EXPERIMENT,
    severity=LessonSeverity.ERROR,
    description="Hyperparameter tuning failed due to insufficient search space",
    context={"param": "learning_rate", "range": "0.001-0.01"},
    run_id="run_001",
)

# Run evolution cycle (extract lessons → synthesize skills)
skills = engine.evolve(sync_to_memoria=True)
print(f"Synthesized {len(skills)} new skills")
```

### Human-in-the-Loop Gates

```python
from lyra_autoresearch import create_gate_config, HITLMode

# Create gate orchestrator
gates = create_gate_config(
    mode=HITLMode.CRITICAL_GATES,  # Only critical decision points
    interactive=True,  # Terminal-based approval
)

# Process a stage
decision = gates.process_gate(
    stage_id="9",
    stage_name="Experiment Design",
    output=experiment_design,
)

if decision.approved:
    if decision.modified_output:
        experiment_design = decision.modified_output
    # Proceed with execution
```

## Architecture

### Citation Verification (4 Layers)

```
Layer 1: arXiv ID Lookup
    ↓ (if fails)
Layer 2: DOI Resolution (CrossRef)
    ↓ (if fails)
Layer 3: Title Search (OpenAlex → Semantic Scholar → arXiv)
    ↓ (if fails)
Layer 4: LLM Relevance Scoring
```

**Verification Status:**
- `VERIFIED`: API confirms + similarity ≥ 0.80
- `SUSPICIOUS`: Found but metadata diverges (0.50 ≤ sim < 0.80)
- `HALLUCINATED`: Not found or similarity < 0.50
- `SKIPPED`: Cannot verify (missing title)

### Self-Healing Execution

```
Task Execution
    ↓ (fails)
Failure Analysis → Classify FailureType
    ↓
Pivot/Refine Decision
    ├─→ REFINE: Adjust method, keep hypothesis
    │   (syntax errors, runtime errors, timeouts)
    └─→ PIVOT: Change hypothesis fundamentally
        (null results, assumption violations, resource limits)
    ↓
Apply Strategy → Retry
```

### Evolution System

```
Research Run
    ↓
Failure/Success Analysis
    ↓
LessonEntry Extraction
    ↓
EvolutionStore (JSONL)
    ↓
High-Severity Lessons (ERROR/CRITICAL)
    ↓
Skill Synthesis (SKILL.md)
    ↓
Memoria Integration
    ↓
Next Research Run (with learned skills)
```

## Configuration

### Environment Variables

```bash
# Optional: OpenAlex polite pool access
export OPENALEX_EMAIL="your@email.com"

# LLM API keys (for debates)
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
```

### Custom Configuration

```python
from lyra_autoresearch import CitationVerifier, DebatePanel, SelfHealingExecutor

# Citation verifier with custom email
verifier = CitationVerifier(openalex_email="your@email.com")

# Debate panel with custom perspectives
from lyra_autoresearch import Perspective
panel = DebatePanel(
    perspectives=[
        Perspective.SKEPTIC,
        Perspective.PRAGMATIST,
        Perspective.DOMAIN_EXPERT,
    ],
    llm_client=client,
    model="claude-3-5-sonnet-20241022",
)

# Self-healing executor with custom limits
executor = SelfHealingExecutor(
    max_refines=5,
    max_pivots=3,
    checkpoint_dir=Path(".checkpoints"),
)
```

## API Reference

### Citations Module

- `CitationVerifier` - 4-layer verification system
- `verify_citations(text)` - Convenience function
- `VerifyStatus` - Verification status enum
- `VerificationReport` - Complete verification report

### Debate Module

- `DebatePanel` - Multi-agent debate orchestrator
- `run_debate(topic, context)` - Convenience function
- `Perspective` - Agent perspective enum
- `DebateResult` - Complete debate transcript

### Execution Module

- `SelfHealingExecutor` - Self-healing executor
- `execute_with_healing(task_fn)` - Convenience function
- `FailureType` - Failure classification enum
- `ExecutionStrategy` - Pivot/Refine/Abort enum

### Evolution Module

- `EvolutionEngine` - Complete evolution system
- `EvolutionStore` - Lesson persistence
- `SkillSynthesizer` - Lesson-to-skill conversion
- `LessonCategory` - Lesson category enum

### HITL Module

- `GateOrchestrator` - Gate management
- `create_gate_config(mode)` - Convenience function
- `HITLMode` - Collaboration mode enum
- `HITLPolicy` - Gate policy enum

## Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=lyra_autoresearch --cov-report=html tests/
```

Skip integration tests (require network):
```bash
pytest -m "not integration" tests/
```

## Performance

Based on AutoResearchClaw's ARCBench evaluation:

| Metric | Improvement vs Baseline |
|--------|------------------------|
| Citation Integrity | +104.4% |
| Writing Quality | +65.3% |
| Reproducibility | +53.4% |
| Novelty | +50.0% |
| Correctness | +39.3% |
| **Overall** | **+54.7%** |

## Integration with Lyra

This package is designed to integrate seamlessly with Lyra's existing architecture:

- **Memory System**: Evolution lessons sync to Lyra's Memoria
- **Skills Format**: Uses SKILL.md (agentskills.io standard)
- **Multi-Agent**: Debate system leverages Lyra's agent infrastructure
- **Execution**: Self-healing wraps Lyra's task execution

## Roadmap

- [x] Phase 1: Citation Verification
- [x] Phase 2: Structured Debates
- [x] Phase 3: Self-Healing Execution
- [x] Phase 4: Evolution System
- [x] Phase 5: HITL Gates
- [ ] Phase 6: Full 23-stage pipeline
- [ ] Phase 7: ARCBench integration
- [ ] Phase 8: Domain-specific prompt engineering

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Citation

If you use this package in research, please cite:

```bibtex
@article{autoresearchclaw2025,
  title={AutoResearchClaw: Autonomous Research with Self-Healing and Multi-Agent Debates},
  author={AIMING Lab},
  journal={arXiv preprint arXiv:2605.20025},
  year={2025}
}
```

## References

- **Paper**: [AutoResearchClaw (arXiv:2605.20025)](https://arxiv.org/abs/2605.20025)
- **Original Code**: [github.com/aiming-lab/AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw)
- **Lyra**: [Lyra Documentation](../../README.md)
- **agentskills.io**: [Agent Skills Standard](https://agentskills.io)
