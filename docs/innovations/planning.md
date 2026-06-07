# Planning & Reasoning: MCTS + CoT Tree Search with Deliberation Layer
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/20-planning.md) | [Code](../../src/lyra/context/)

## Abstract
Lyra's planning layer adds explicit deliberation over the memory + skills substrate. It supports multiple search strategies: Chain-of-Thought (single-pass), Tree-of-Thoughts (BFS/DFS with LLM state evaluation), MCTS with value-guided exploration (SWE-Search), and AFlow-style workflow search. The deliberation layer decides when explicit search beats single-pass reasoning based on a cost model (tie to economics §4.21).

## Method
Strategies are composable: a task can start with CoT for simple steps, escalate to ToT when branching is needed, and use MCTS for open-ended exploration. The planning output feeds into the agent loop as a structured plan (goal→subgoals→actions→verification).

## Conclusion
Implemented: CoT, ToT, MCTS strategies. Future: learned value functions, budget-aware search allocation.

## Working Flow

Not every task needs deep planning. Lyra decides how much to think based on the task's complexity.

When you send a message, the agent loop in `src/lyra/agent_loop/executor.py` classifies the task: simple (single-step), moderate (few branches), or complex (open-ended). Simple tasks get Chain-of-Thought — a single reasoning pass. Moderate tasks get Tree-of-Thoughts — Lyra explores 2-3 approaches in parallel, evaluates each with an LLM score, and picks the best. Complex tasks get MCTS — Lyra builds a search tree, explores promising branches deeper, and backpropagates success signals. The `WorkspaceReport` in `src/lyra/context/workspace.py` tracks the plan state throughout.

**Example:** You ask Lyra to design a database schema for a multi-tenant SaaS:
1. The classifier tags this as complex (open-ended, multiple valid solutions)
2. MCTS kicks in: Lyra explores 4 root approaches (single-DB, schema-per-tenant, DB-per-tenant, hybrid)
3. Each approach gets a score from an LLM evaluator based on: isolation, cost, complexity, migration ease
4. The top 2 approaches (schema-per-tenant, hybrid) get expanded with 3 sub-variations each
5. After 15 node evaluations, Lyra recommends schema-per-tenant with row-level security — citing 3 trade-offs
6. The plan is serialized as `PlanStep` objects and fed back into the agent loop for execution
