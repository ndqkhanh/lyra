# Lyra Interpretability

Agent interpretability and decision tracing for multi-agent systems.

## Features

- **Decision Tracing** — Record full reasoning chains with step-by-step explanations
- **Feature Attribution** — Score and rank features influencing each decision
- **Saliency Maps** — Token-level saliency scores for input text
- **Counterfactual Explanations** — Generate alternative outcomes by modifying factors
- **Interpretability Reports** — Aggregate transparency scoring across agents
- **Natural Language Explanations** — Human-readable decision breakdowns

## Installation

```bash
pip install lyra-interpretability
```

## Quick Start

```python
from lyra_interpretability import InterpretabilityEngine

# Create engine
engine = InterpretabilityEngine()

# Trace a decision
trace = engine.trace_decision(
    agent_id="agent-1",
    input_text="Should I deploy safety-critical code?",
    reasoning=[
        "Verify all tests pass",
        "Check security review status",
        "Assess deployment risk",
    ],
    decision="Deploy after review",
    confidence=0.85,
    alternatives=["Deploy now", "Hold for manual review"],
)

# Get feature attributions
attributions = engine.attribute_features("Safety and security are critical")
for attr in attributions:
    print(f"  #{attr.rank} {attr.feature}: {attr.score:.3f}")

# Generate a counterfactual
counterfactual = engine.generate_counterfactual(
    trace, changed_factor="security", new_value="not reviewed"
)

# Generate aggregate report
report = engine.generate_report("agent-1")
print(f"Transparency score: {report.overall_transparency_score:.2%}")

# Explain a decision in natural language
explanation = engine.explain_decision("agent-1", trace.decision_id)
print(explanation)
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Version

Current version: **0.1.0**

## License

MIT License
