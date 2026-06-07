# Planning Guide — Structuring Agent Reasoning

> How Lyra plans complex tasks using CoT, Tree-of-Thoughts, and MCTS search strategies.

## Quickstart

The planning layer is invoked automatically when the agent detects a task is complex enough to warrant explicit deliberation:

```python
from lyra.context import PlanStep

# The agent loop automatically escalates:
# Simple task → single-pass Chain-of-Thought
# Branching needed → Tree-of-Thoughts (BFS/DFS)
# Open-ended exploration → MCTS with value-guided search
```

## Strategies

| Strategy | When to Use | Cost |
|----------|------------|------|
| **Chain-of-Thought** | Straightforward tasks, single solution path | 1× tokens |
| **Tree-of-Thoughts** | Multiple approaches to evaluate | 3-10× tokens |
| **MCTS** | Open-ended exploration, code generation | 5-50× tokens |
| **AFlow** | Workflow optimization | 2-5× tokens |

## Cost Model

The planning layer decides strategy based on task complexity and the economics budget (§4.21). A cost model gates escalation: if MCTS would cost more than the budget allows, it falls back to ToT or CoT.

## → Dive Deeper

- [Planning Concept](../concepts/05-plan-mode.md)
- [Planning Block](../blocks/04-plan-mode.md)
- [Innovation Doc](../innovations/planning.md)
- [Plan](../lyra-upgrade/plans/20-planning.md)
