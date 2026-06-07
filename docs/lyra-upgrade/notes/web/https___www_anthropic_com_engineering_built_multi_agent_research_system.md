# How we built our multi-agent research system (Anthropic Engineering Blog)

**Source:** https://www.anthropic.com/engineering/built-multi-agent-research-system
**Published:** June 13, 2025
**Authors:** Jeremy Hadfield, Barry Zhang, Kenneth Lien, Florian Scholz, Jeremy Fox, Daniel Ford (Anthropic apps engineering team)

---

## Key Technical Claims

1. **Multi-agent outperforms single-agent by 90.2%** on Anthropic's internal research eval, using a LeadResearcher (Opus 4) + subagents (Sonnet 4) pattern vs. a single Opus 4 agent.

2. **Parallel subagent spawning cuts latency by up to 90%** for complex queries — the orchestrator spawns 3-5 subagents in parallel (not serially), and subagents themselves issue 3+ parallel tool calls.

3. **Subagents act as intelligent compressors** — each explores different facets of a query in separate context windows, then returns only the most important tokens to the lead, effectively compressing vast corpora into digestible, relevant inputs.

4. **Token cost is real but bounded** — multi-agent systems use ~15x more tokens than chat; this is economically justified only for high-value research tasks.

5. **Heuristics over rigid rules** — the system encodes strategies from skilled human researchers (decomposition, source quality evaluation, adaptive searches, depth-vs-breadth tradeoffs) as prompt-level heuristics, not hard-coded logic.

6. **Bad tool descriptions are a major failure mode** — a dedicated tool-testing agent that rewrites MCP tool descriptions yielded a 40% decrease in task completion time.

7. **Extended thinking is the controllable scratchpad** — used for planning (assessing tools, determining subagent count, defining roles) by the lead; interleaved thinking used by subagents after tool results to evaluate quality and refine next queries.

8. **Single-judge LLM eval works best** — one LLM call with one prompt scoring 5 criteria (factual accuracy, citation accuracy, completeness, source quality, tool efficiency) was "most consistent and aligned with human judgements."

---

## Architecture/Mechanism Details

### Orchestrator-Worker Pattern

```
User Query
  → LeadResearcher (Claude Opus 4)
      → saves plan to Memory (survives 200K context truncation)
      → spawns specialized Subagents (Claude Sonnet 4) in parallel
          → each does web searches + interleaved thinking
          → returns compressed findings to Lead
      → Lead synthesizes, decides if more research needed
      → loop exits → CitationAgent processes documents → final output
```

### Key Components

- **LeadResearcher:** Analyzes user query, develops strategy, saves plan to external Memory (critical for persistence across long runs where the 200K context window would drop the plan). Enters iterative research loop.

- **Subagents:** Independently perform web searches, evaluate tool results using interleaved thinking, return findings. One subagent's prompt includes: objective, output format, tool/source guidance, clear task boundaries.

- **CitationAgent:** Post-research; processes documents and the report to identify specific citation locations.

- **Memory:** External, survives context truncation. Stores the research plan so the lead can retrieve it after context window resets.

- **Subagent output to filesystem artifact system:** Subagents persist work externally, return lightweight references to coordinator. Prevents information loss in multi-stage processing and reduces token overhead from copying large outputs through conversation history.

### 8 Prompt Engineering Principles

1. **Think like your agents** — build Console simulations with exact prompts/tools; watch step-by-step
2. **Teach the orchestrator how to delegate** — objective + output format + tool guidance + task boundaries per subagent
3. **Scale effort to query complexity** — explicit heuristics: 1 agent/3-10 calls (simple), 2-4 subagents/10-15 calls each (comparisons), >10 subagents (complex)
4. **Tool design and selection are critical** — agents examine all tools first, match tool to intent, prefer specialized over generic
5. **Let agents improve themselves** — Claude 4 models as prompt engineers; dedicated tool-testing agent rewrites MCP tool descriptions
6. **Start wide, then narrow down** — begin with short broad queries, evaluate, then progressively narrow
7. **Guide the thinking process** — extended thinking for planning; interleaved thinking for subagent evaluation
8. **Parallel tool calling transforms speed and performance** — lead spawns 3-5 subagents in parallel; subagents use 3+ tools in parallel

### Production Engineering

- **Rainbow deployments:** gradual traffic shifting, old + new versions run simultaneously
- **Resume capability:** can't restart on error (too expensive); built resume from error point with deterministic safeguards (retry logic, regular checkpoints)
- **Full production tracing** for debugging (bad queries, poor sources, tool failures)
- **Synchronous bottleneck acknowledged:** lead waits for subagents; can't steer mid-flight; subagents can't coordinate; entire system blocked on slowest subagent

### Evaluation Methodology

- **5-dimension LLM rubric:** factual accuracy, citation accuracy, completeness, source quality, tool efficiency
- **Single-judge LLM** most consistent and aligned with human judgements
- **Focus on outcomes + reasonable process,** not prescribed steps (since paths vary)
- **Human eval caught blind spots:** early agents chose SEO-optimized content farms over authoritative academic PDFs
- **Start small:** ~20 test cases sufficient when effect sizes are large (30% -> 80% improvements)

---

## Numbers & Benchmarks

| Metric | Value |
|--------|-------|
| Multi-agent vs. single-agent performance gain | +90.2% |
| Token usage variance on BrowseComp | 80% explained by token count alone |
| Overall BrowseComp variance (3 factors) | 95% explained by tokens + tool calls + model |
| Agent vs. chat token multiplier | ~4x |
| Multi-agent vs. chat token multiplier | ~15x |
| Parallelization latency reduction | Up to 90% |
| Tool-testing agent description rewrite improvement | 40% decrease in task completion time |
| Early eval sample size | ~20 queries |
| Lead model | Claude Opus 4 |
| Subagent model | Claude Sonnet 4 |

### Effort-Scaling Heuristics

| Query Complexity | Subagents | Calls per Agent |
|-----------------|-----------|-----------------|
| Simple fact-finding | 1 | 3-10 |
| Direct comparisons | 2-4 | 10-15 each |
| Complex research | >10 | divided responsibilities |

### Use Case Distribution
1. Developing software systems: 10%
2. Develop professional/technical content: 8%
3. Business growth/revenue strategies: 8%
4. Academic research and educational material: 7%
5. Research and verify information about people/orgs: 5%

---

## Transfer to Lyra

### The One Idea: Structured Memory-Persisted Orchestration with Interleaved Thinking

**Idea:** Lyra should adopt the **LeadResearcher pattern with explicit Memory persistence** — where an orchestrator agent saves its research plan to an external, context-window-safe memory store, spawns parallel subagents that use interleaved thinking, and retrieves the plan after context resets. The subagents return only compressed, relevance-filtered findings (not raw dumps), and the lead synthesizes across them.

This directly solves Lyra's current problem of context window pressure during deep research: instead of trying to fit everything into a single 200K context, the system uses Memory as a durable scratchpad and subagents as distributed processors. The explicit **effort-scaling heuristics** (1 agent for simple, 2-4 for comparisons, >10 for complex) give Lyra a concrete mechanism for routing query complexity to appropriate resource budgets.

### Workstream Route

This maps to the research agent training/automation lane. The structured orchestration + Memory persistence + interleaved thinking patterns should inform the design of Lyra's research agent orchestration workstream, specifically the subagent spawning and context management infrastructure.

### Suggested Action Items for Lyra

1. Implement a LeadResearcher agent that saves plans to durable Memory before spawning subagents
2. Add effort-scaling heuristics (simple/comparison/complex) to query routing logic
3. Enable interleaved thinking in subagents for post-tool-result evaluation
4. Add artifact-based filesystem output for subagents to reduce coordinator token burden
5. Build a CitationAgent pass as the final post-processing step
6. Use a single-judge LLM eval with the same 5-dimension rubric for Lyra's research quality gate
7. Implement rainbow deployment capability for non-breaking agent updates

---

*Rigor note created from: https://www.anthropic.com/engineering/built-multi-agent-research-system*
