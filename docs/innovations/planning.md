# Planning & Reasoning: MCTS + CoT Tree Search with Deliberation Layer
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/20-planning.md) | [Code](../../src/lyra/context/)

## Abstract
Lyra's planning layer adds explicit deliberation over the memory + skills substrate. It supports multiple search strategies: Chain-of-Thought (single-pass), Tree-of-Thoughts (BFS/DFS with LLM state evaluation), MCTS with value-guided exploration (SWE-Search), and AFlow-style workflow search. The deliberation layer decides when explicit search beats single-pass reasoning based on a cost model (tie to economics §4.21).

## Method
Strategies are composable: a task can start with CoT for simple steps, escalate to ToT when branching is needed, and use MCTS for open-ended exploration. The planning output feeds into the agent loop as a structured plan (goal→subgoals→actions→verification).

## Conclusion
Implemented: CoT, ToT, MCTS strategies. Future: learned value functions, budget-aware search allocation.
