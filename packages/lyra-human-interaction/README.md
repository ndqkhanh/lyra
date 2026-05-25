# Lyra Human Interaction

Human-agent interaction package for Lyra agents — explanations, negotiation,
feedback integration, alignment dialog, and interactive clarification.

## Features

- **Explanation Generation**: Tailored explanations at NOVICE, INTERMEDIATE,
  EXPERT, EXECUTIVE, and TECHNICAL levels with adaptive vocabulary and depth.
- **Negotiation Protocol**: Structured multi-round negotiation with phase
  tracking, agreement/disagreement detection, and compromise suggestion.
- **Feedback Integration**: Process corrections, preferences, ratings,
  suggestions, and clarification requests on agent decisions.
- **Alignment Dialog**: Structured dialogs to discover common ground and
  build shared understanding.
- **Interactive Clarification**: Proactive clarification requests when the
  agent is uncertain, with predefined answer options.

## Usage

```python
from lyra_human_interaction import HumanInteractionEngine

engine = HumanInteractionEngine()

# Generate an explanation
explanation = engine.generate_explanation(
    topic="Route Optimization",
    decision_context="Choosing fastest path",
    reasoning=["Analyzed traffic data", "Evaluated road conditions"],
    level="INTERMEDIATE",
)

# Start a negotiation
state = engine.start_negotiation(
    topic="Sprint scope",
    agent_proposal="Complete 5 stories",
)
```
