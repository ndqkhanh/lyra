# Planning & Reasoning: MCTS + CoT Tree Search with Deliberation Layer
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/20-planning.md) | [Code](../../src/lyra/context/)

## Abstract
Lyra's planning layer adds explicit deliberation over the memory + skills substrate. It supports multiple search strategies: Chain-of-Thought (single-pass), Tree-of-Thoughts (BFS/DFS with LLM state evaluation), MCTS with value-guided exploration (SWE-Search), and AFlow-style workflow search. The deliberation layer decides when explicit search beats single-pass reasoning based on a cost model (tie to economics §4.21).

## Method
Strategies are composable: a task can start with CoT for simple steps, escalate to ToT when branching is needed, and use MCTS for open-ended exploration. The planning output feeds into the agent loop as a structured plan (goal→subgoals→actions→verification).

## Use Cases

**Scenario 1: Complex multi-step refactoring plan.** A developer needs to migrate a monolithic authentication system from Django's built-in auth to OAuth 2.0 with social login providers. The task has 12 files to touch, 3 migration phases, and zero room for downtime. Instead of reasoning through all dependencies mentally, the developer dumps the problem into Lyra's planning layer. MCTS explores several migration strategies — big-bang, phased with feature flags, parallel system with proxy. Each gets scored on risk, timeline, and test coverage. The planner outputs a structured plan with ordered subgoals: (1) add OAuth library, (2) create provider abstraction, (3) dual-write auth tokens, (4) flip feature flag, (5) remove old code. Each step has a verification check. No files touched out of order.

**Scenario 2: Architecture design exploration.** A team is choosing between event-driven and request-driven architecture for a new notification service. They don't write code yet — they use Lyra's Tree-of-Thoughts planner to explore design branches. ToT spawns 3 parallel approaches: a pub/sub system with RabbitMQ, a serverless event bus with SNS+SQS, and a hybrid with in-process dispatcher. The LLM evaluator scores each on latency, operational cost, team skill fit, and scalability. The pub/sub approach wins. The planner produces a one-page architecture summary with trade-offs documented. The team takes it straight into their design review meeting.

**Scenario 3: Debugging a heisenbug that only appears in production.** A developer is chasing a race condition that only happens under production load — impossible to reproduce locally. Chain-of-Thought would miss the subtle timing dependency. The developer feeds the repro logs and code into Lyra's MCTS planner. MCTS builds a hypothesis tree: lock contention, cache invalidation, database isolation level, connection pool exhaustion. Each hypothesis gets expanded with diagnostic steps. The planner converges on the database isolation level branch after 8 evaluations and suggests adding `SELECT FOR UPDATE`. The fix deploys. The bug never reappears.

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
