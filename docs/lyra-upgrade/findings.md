# Lyra Upgrade — Deep Research Findings

> One row per technique. Mechanism, numbers, trade-offs, design rationale, gap-vs-baseline — all required.
> **Run 1:** June 3, 2026 | Live rows: building as agents return

---

## §3.1 — Claude Code Official Docs

### Anthropic Context Engineering (3 Strategies)
**Source:** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
**Mechanism (step-by-step):**
1. **Compaction:** Model summarizes conversation history nearing context window limit, preserving "architectural decisions, unresolved bugs, and implementation details" while removing redundant tool outputs. Claude Code keeps "five most recently accessed files" alongside compressed history. Lightest variant: tool-result clearing (remove raw outputs deep in history).
2. **Structured Note-Taking (Agentic Memory):** Agents persist notes to memory outside context window, pull back when relevant. Claude Code variant: maintain NOTES.md, read after context resets. Sonnet 4.5 ships file-based memory tool on Developer Platform for cross-session persistence.
3. **Sub-Agent Architectures:** Specialized sub-agents with clean, separate context windows. Each explores extensively (tens of thousands of tokens) but returns condensed summaries (1,000-2,000 tokens). Multi-agent research system showed "substantial improvement" over single-agent.

**Key Finding — "Less is More":**
- System prompts: find minimal viable prompt, add only what failure modes demand
- Tools: curate minimal viable set — "if a human engineer can't definitively say which tool should be used, an AI agent can't be expected to do better"
- Examples: diverse, canonical examples > exhaustive edge cases
- Context retrieval: "just in time" — maintain lightweight identifiers, dynamically load at runtime
- Context as "finite resource with diminishing marginal returns"; performance follows "gradient, not cliff"

**Trade-offs:**
- Gains: context efficiency, better attention allocation, improved pass rates on long tasks
- Costs: compaction risks information loss; memory tool requires disciplined note-taking; sub-agent summaries may miss details
- When wins: long-horizon tasks with many tool calls; loses: short single-turn tasks where overhead > benefit

**Design Rationale:** LLMs have finite attention budgets; every token competes. The "smallest possible set of high-signal tokens" maximizes outcome likelihood.

**Transferable Idea for Lyra:** Implement all 3 strategies: (1) auto-compaction when context nears limit, (2) file-based memory tool that persists across sessions, (3) sub-agent fan-out with condensed summaries. The "less is more" principle should guide Lyra's entire context engineering — start minimal, add only what evals show is needed.

**Gap vs Baseline:** `none` — Lyra has NO context management, NO memory tool, and sub-agent architecture is basic (no fan-out, no summaries). This is all new.

**Impact:** 5 | **Effort:** 4 | **Tier:** (A) Parity | **Last Verified:** Run 1

---

### Dynamic Workflows (Claude Code)
**Source:** https://claude.com/blog/introducing-dynamic-workflows-in-claude-code
**Mechanism:** Claude dynamically writes orchestration scripts that fan work across parallel subagents. Coordination happens "outside the conversation." Independent verification runs on every finding. Adversarial agents try to break results. Progress is saved as the run goes.

**Key Primitives (from blog):**
1. Dynamic planning: breaks prompt into subtasks
2. Parallel fan-out: "tens to hundreds of parallel subagents"
3. Independent verification on every finding
4. Adversarial checking: "independent attempts + adversarial agents working to break the result"
5. Convergence loops: "keeps iterating until answers converge"
6. Resumability: "progress saved as the run goes"

**Trade-offs:**
- Gains: quality via adversarial cross-check, speed via parallelism, reliability via resumability
- Costs: token multiplication (N agents = N× tokens), orchestration complexity
- When wins: complex multi-step tasks, thorough audits, deep research; loses: simple one-shot queries

**Design Rationale:** Single-pass LLM output is error-prone; multiple independent passes + adversarial checking converges on truth.

**Transferable Idea for Lyra:** Build the dynamic-workflow engine as a core Lyra subsystem. Adopt the understand→change→verify loop pattern. Implement independent verification + adversarial cross-check as the default quality pattern for research workflows.

**Gap vs Baseline:** `none` — Lyra has no workflow engine, no dynamic orchestration, no adversarial verification.

**Impact:** 5 | **Effort:** 5 | **Tier:** (B) Breakthrough | **Last Verified:** Run 1

---

### Companies as a Graph of Algorithms
**Source:** https://danielmiessler.com/blog/companies-graph-of-algorithms
**Mechanism:** Model any business process as a directed graph where nodes are discrete algorithm steps (transform inputs→outputs) and edges are handoffs. Recursively decomposable — "algorithms all the way down." AI both executes nodes AND understands interconnections, making every node "ripe for optimization or elimination."

**Transferable Idea for Lyra:** Model Lyra workflows as directed graphs. Task decomposition = recursive graph expansion until leaf nodes are agent-executable. Observability = every node addressable. Continuous optimization = agents evaluate their own graph for bottlenecks.

**Gap vs Baseline:** `none` — Lyra has no graph-based workflow model.

**Impact:** 3 | **Effort:** 3 | **Tier:** (A) Parity | **Last Verified:** Run 1

---

*More findings rows will be added as background research agents complete. This file is a living document — rows are appended, never deleted.*
