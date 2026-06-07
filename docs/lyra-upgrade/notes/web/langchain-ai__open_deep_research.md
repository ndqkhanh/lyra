# langchain-ai/open_deep_research -- Deep-Read

Source: https://github.com/langchain-ai/open_deep_research
Cloned at: /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/langchain-ai__open_deep_research
Commit pinned: ca3951d (GPT-5 evaluation), 6532a41 (defaults baseline)

---

## 1. Headline Feature & Mechanism

**Headline**: An open-source, configurable deep research agent built on LangGraph that achieves #6 on the Deep Research Bench Leaderboard (RACE score 0.4344). It parallel-fans-out research tasks via a supervisor subgraph to multiple researcher subgraphs, each running independent tool-calling loops, then compresses and aggregates findings into a final report.

**How the code really works** (read from `deep_researcher.py`):

1. **Clarify phase** (`clarify_with_user`): The agent first checks user messages for ambiguity using `ClarifyWithUser` structured output. If the user's intent is unclear, it asks a clarifying question; otherwise it proceeds to write a research brief.

2. **Research Brief** (`write_research_brief`): Transforms user messages into a structured `research_brief` (a single paragraph describing the task) using a `ResearchQuestion` structured output model. Initializes the supervisor subgraph's message stack with a system prompt + the brief.

3. **Supervisor loop** (`supervisor` -> `supervisor_tools` -> `supervisor` ...):
   - The supervisor is a LangGraph subgraph of its own (`StateGraph(SupervisorState)`) with two nodes: `supervisor` (LLM call) and `supervisor_tools` (tool execution).
   - The supervisor can call three tools: `ConductResearch` (spawn a sub-researcher), `ResearchComplete` (signal done), and `think_tool` (strategic reflection).
   - The `think_tool` is a deliberate architectural choice -- it forces the supervisor to think *before* delegating and *after* receiving results, in a separate step (the prompt says "Do not call think_tool with any other tools in parallel").
   - On `supervisor_tools`, all `ConductResearch` calls are executed in parallel via `asyncio.gather(*research_tasks)`, bounded by `max_concurrent_research_units` (default: 5). Overflow research calls are rejected with an error message. The supervisor loops until `ResearchComplete`, `max_researcher_iterations` (default: 6), or no tool calls.

4. **Researcher subgraph** (`researcher` -> `researcher_tools` -> `researcher` ... -> `compress_research`):
   - Each `ConductResearch` call spawns a fresh invocation of the `researcher_subgraph` -- a standalone `StateGraph(ResearcherState, output=ResearcherOutputState)` that runs its own tool-calling loop.
   - Researchers use `tavily_search`, `web_search`, `think_tool`, MCP tools, and `ResearchComplete`. Search results from Tavily are automatically summarized using a separate summarization model (`gpt-4.1-mini` by default).
   - When the researcher is done (no more tool calls, max iterations, or `ResearchComplete`), it proceeds to `compress_research` which uses a compression model (`gpt-4.1`) to condense all tool outputs and AI messages into a structured summary with citations.

5. **Final report** (`final_report_generation`): Takes all compressed research findings (`notes`) and the original `research_brief` and generates a comprehensive markdown report with citations. Has retry logic with progressive truncation for token-limit errors.

**Key concurrency pattern**: The supervisor and researchers share the same underlying `configurable_model` (initialized via `init_chat_model` with configurable fields), but are parameterized with different model names per role (research, compression, summarization, final report). All four model roles are independently configurable.

---

## 2. Architecture & Core Modules

### File Map

```
src/open_deep_research/
  deep_researcher.py    # Main graph: 4 top-level nodes + 2 subgraphs (~720 lines)
  configuration.py      # Pydantic Configuration with OAP UI metadata (~250 lines)
  state.py              # State types: AgentState, SupervisorState, ResearcherState (~90 lines)
  prompts.py            # 8 prompt templates for all phases (~370 lines)
  utils.py              # Search tools, MCP tools, token limit helpers (~920 lines)
src/security/
  auth.py               # LangGraph Auth integration via Supabase JWT (~155 lines)
src/legacy/
  graph.py              # Plan-and-execute legacy approach
  multi_agent.py        # Supervisor-researcher multi-agent legacy approach
langgraph.json          # Entry point: deep_researcher graph
pyproject.toml          # Dependencies, version 0.0.16
```

### Data Flow

```
User Msg
  |
  v
[clarify_with_user] --(if ambiguous)--> END (ask question)
  |
  v
[write_research_brief] --(research_brief)-->
  |
  v
[research_supervisor]  <== SUBGRAPH
  |-- supervisor (LLM) --> supervisor_tools (parallel fan-out)
  |     |-- ConductResearch --> [researcher_subgraph] x N (parallel)
  |     |     |-- researcher --> researcher_tools --> researcher (loop)
  |     |     `-- compress_research --> compressed_research + raw_notes
  |     |-- think_tool --> reflection
  |     `-- ResearchComplete --> exit
  |
  v
[final_report_generation] --> Final Markdown Report
```

### Configuration Hierarchy

The `Configuration` class (Pydantic) serves double duty:
- Runtime config via `RunnableConfig` (merged from env vars + LangGraph configurable fields)
- UI metadata via `x_oap_ui_config` annotations for Open Agent Platform

Key configuration fields:
- 4 model roles: `research_model`, `summarization_model`, `compression_model`, `final_report_model` (all independently set)
- Search API: `tavily` (default), `anthropic`, `openai`, or `none`
- Concurrency: `max_concurrent_research_units` (1-20), `max_researcher_iterations` (1-10)
- Tool limits: `max_react_tool_calls` (1-30 per researcher)
- MCP: `mcp_config` (URL + tool list + auth), `mcp_prompt`

### Architecture Pattern

**LangGraph state machine with nested supervisor subgraphs**. The pattern is:

- A supervisor subgraph owns the research orchestration. It can spawn parallel child subgraphs (researchers) that each run their own tool-calling loop.
- Each researcher subgraph produces structured output (`compressed_research` + `raw_notes`), which the supervisor collects.
- The parent graph is sequential (clarify -> brief -> research -> report), but the research phase internally parallelizes via the supervisor.
- This is NOT a DAG of fixed nodes -- it is a dynamic loop with a delegation-based parallelism model. The LLM decides how to break down work and when to stop.

---

## 3. Performance / Benchmarks

All numbers from the official Deep Research Bench (100 PhD-level tasks, 22 fields, LLM-as-judge via Gemini):

| Model Config | RACE Score | Total Cost | Total Tokens |
|---|---|---|---|
| GPT-5 (research) + GPT-4.1-mini (summarization) + GPT-4.1 (compression/report) | **0.4943** | -- | 204,640,896 |
| Claude Sonnet 4 (research) + GPT-4.1-mini (summ) + GPT-4.1 (comp/report) | **0.4401** | $187.09 | 138,917,050 |
| GPT-4.1 (all roles, submission to leaderboard) | **0.4344** | $87.83 | 207,005,549 |
| GPT-4.1 (all roles, default) | **0.4309** | $45.98 | 58,015,332 |

Key observations:
- GPT-5 as the research model gave the best score (+14.7% over GPT-4.1 baseline), but likely consumed much higher token counts (the default test consumed 58M, the GPT-5 test consumed 204M).
- Claude Sonnet 4 was more expensive ($187) than GPT-4.1 ($46) for comparable RACE scores (0.4401 vs 0.4309), suggesting GPT-4.1 is more token-efficient for this architecture.
- The full evaluation run on 100 examples costs $45-$187 depending on model selection.
- The system is ranked #6 on the leaderboard (as of August 2, 2025).

---

## 4. Trade-offs

### Wins

1. **Supervisor parallelism is effective**. The supervisor can dynamically decide how to decompose research and fan-out N parallel researchers. The `think_tool` step between each delegation forces strategic reflection.

2. **Model-role separation**. Four independently configurable model roles (research, summarization, compression, final report) allow cost-quality tradeoffs -- use a cheap model for summarization and a powerful one for research/report writing.

3. **Multi-provider support**. Works with OpenAI, Anthropic, Google, Groq, DeepSeek, and any model via `init_chat_model`. Search supports Tavily, OpenAI native web search, Anthropic native web search, DuckDuckGo, Exa, and MCP servers.

4. **Retry resilience**. Every model call has structured retry logic, and token-limit errors trigger progressive context truncation (remove last AI message, retry up to 3 times).

5. **MCP extensibility**. Custom tools can be added via MCP servers with OAuth token exchange, authentication wrapping, and tool name conflict resolution.

### Losses / Limitations

1. **No source-level verification or adversarial checking**. The system compresses and cites sources but does not cross-validate claims or detect hallucinations. The compression step explicitly says "repeat key information verbatim" -- it optimizes for lossless compression, not fact-checking.

2. **No iterative refinement of the final report**. The final report is generated in one pass from compressed notes. There is no self-critique, outline-first-then-write, or multi-draft loop in the report generation phase. (The legacy `graph.py` had plan-and-execute with human-in-the-loop, which was removed for performance.)

3. **Compression is a bottleneck**. All researcher findings are serialized through a single compression step before being passed to the final report writer. If a researcher produces very long output, the compression model's limited context can lose information (addressed by retry with truncation, but that loses messages).

4. **No shared state between researchers**. The prompt explicitly says "sub-agents can't see other agents' work." This prevents one researcher from building on another's findings within the same iteration. Redundant searching is possible.

5. **Cost scales with parallelism**. The README warns that running the full 100-example evaluation costs $45-$187. With `max_concurrent_research_units=5`, API rate limits are a real concern.

6. **Token limit handling is fragile**. The `MODEL_TOKEN_LIMITS` dict in `utils.py` has a prominent comment: "This may be out of date or not applicable to your models. Please update this as needed." The truncation strategy removes entire AI messages from history, which can lose context.

7. **No memory/persistence of past research**. Each session is stateless -- the agent cannot build on previous research sessions or maintain a knowledge base of past findings.

---

## 5. Design Rationale

The blog post mentioned in the README ("The Bitter Lesson" by R. Lance Martin, July 30, 2025) provides the design philosophy:

1. **"Bias towards single agent for simplicity"** (from the supervisor prompt). The architecture explicitly prefers a single researcher for simple queries, only fanning out when there's "clear opportunity for parallelization." This is grounded in the observation that multi-agent coordination overhead often outweighs gains for simple tasks.

2. **Think_tool isolation**. The prompt explicitly forbids calling `think_tool` with other tools in parallel. This is a deliberate slowdown -- it forces the model to reflect *after* searching and *before* deciding next actions, mimicking how a human researcher would work.

3. **Separation of concerns via subgraphs**. The researcher subgraph is isolated from the supervisor and has its own state, its own tool loop, and its own compression step. This prevents one researcher's token consumption from affecting others and makes the system's parallelism clean.

4. **Compression as a gating function**. Rather than passing raw tool outputs to the final report writer (which could exceed context), each researcher's output is compressed by a separate model call. This is the key architectural insight: the system trades cost for reliability by ensuring the final writer always receives bounded, structured input.

5. **Configuration as a first-class concept**. The Configuration class has dual-purpose annotations (Pydantic fields + UI metadata), reflecting the LangGraph Platform design philosophy that agents should be configurable through a GUI (Open Agent Platform) without code changes.

---

## 6. Transfer to Lyra

### Transferable Idea: Supervisor-Subgraph Research Parallelism with Compression Pipeline

Lyra's current research pipeline (Phase 1, as described in `brainstorm/15-research.md` and `05-router.md`) is primarily sequential: gather sources, synthesize, report. The open_deep_research architecture suggests a concrete improvement:

**Adopt a bounded parallelism model**: A Lyra "Research Supervisor" node receives a query, decomposes it into parallel sub-tasks, and fans out to "Research Worker" subgraphs that each run their own independent tool-calling loop (web search, code search, MCP tools). A compression step per worker produces structured, bounded output. The supervisor collects these, reflects, and either spawns more researchers or signals completion.

This maps directly to Lyra's existing `router.md` concept (a query planner that decomposes tasks) but adds the execution-side parallelism and compression that Lyra currently lacks.

### Workstream Route

**Section 4.x**: **Section 4.1 (Research Pipeline)** -- this is the primary fit. The supervisor-subgraph pattern is a direct upgrade to Lyra's research pipeline.

**Impact**: **High** (9/10) -- Parallel research would significantly reduce end-to-end research time and improve source coverage. The compression pipeline ensures bounded context for synthesis.

**Effort**: **Medium** (6/10) -- Requires adding LangGraph subgraph support (or equivalent parallel state machine), implementing the supervisor/researcher decomposition logic, and adding the compression step. Lyra already has web search and source gathering tools, so the main effort is the orchestration layer.

**Tier**: **T1** -- This is a core capability upgrade that directly affects user-facing research quality and speed.

### LICENSE

MIT -- fully compatible for incorporation into Lyra. Can be used, modified, and distributed without restriction.
