# AI Agents and Applications With LangChain, LangGraph, and MCP
## Chapter-Level Notes

**Author:** Roberto Infante
**Year:** 2026
**Publisher:** Manning Publications
**Pages:** ~450 (14 chapters + 5 appendices)
**Target audience:** Python developers comfortable with VS Code, virtual environments, and Jupyter; no prior LLM application experience required
**Core thesis:** Production-grade AI agents require composable components (LangChain), explicit control-flow graphs (LangGraph), standardized tool protocols (MCP), and layered safety mechanisms (guardrails, memory, evaluation) — not just a capable LLM.

---

## Part 1: Getting Started with LLMs

### Chapter 1 — Introduction to AI Agents and Applications
**Pages:** 3–26
**Focus:** Landscape mapping, framework rationale

**Key insights:**
- Three major LLM application patterns: engines (summarization/research), chatbots (RAG Q&A), and agents (tool-using, decision-making)
- LangChain provides modular building blocks: loaders, splitters, embeddings, retrievers, vector stores, prompts — so you don't reinvent plumbing
- LangGraph structures workflows as graphs and coordinates agent loops
- LangSmith adds visibility for debugging and evaluation
- Prompt engineering and RAG are the two pillars of grounded LLM systems

**Best practices:**
- Choose the right pattern before choosing the framework
- Understand where models succeed and where they struggle before building

**Anti-patterns:**
- Jumping to agents when a simple chain or RAG pipeline suffices
- Ignoring the cost/complexity trade-off of agentic architectures

**Lyra section mappings:** §4.1 (UI/UX) — architecture pattern selection, §4.2 (Memory) — RAG grounding

---

### Chapter 2 — Executing Prompts Programmatically
**Pages:** 27–51
**Focus:** Prompt design fundamentals, LangChain PromptTemplate

**Key insights:**
- Persona, context, instructions, inputs, and examples form the five-part prompt structure
- One-shot, few-shot, and chain-of-thought (CoT) prompting are progressive strategies
- LangChain's `PromptTemplate` and `FewShotPromptTemplate` enable programmatic prompt generation and iteration
- Prompt types covered: classification, sentiment analysis, summarization, composition, Q&A, reasoning
- Critical concept: prompt engineering is iterative, not one-shot

**Best practices:**
- Always include role/persona instructions for consistent agent behavior
- Use structured output (Pydantic models) instead of string parsing
- CoT prompting dramatically improves reasoning accuracy on multi-step tasks

**Anti-patterns:**
- Treating prompts as static strings rather than versioned, testable artifacts
- Omitting explicit refusal/fallback instructions

**Lyra section mappings:** §4.9 (Commands) — structured prompt templates, §4.3 (Context) — prompt composition

---

## Part 2: Summarization

### Chapter 3 — Summarizing Text Using LangChain
**Pages:** 55–68
**Focus:** Context window management, MapReduce/Refine patterns

**Key insights:**
- For documents larger than the context window: chunk, then apply Map, Reduce, or Refine strategies
- MapReduce: parallel summarization of chunks followed by a combine step
- Refine: iterative improvement, each chunk's summary is refined with the next chunk's content
- Document objects in LangChain encapsulate text + metadata

**Best practices:**
- Use MapReduce for speed on large corpora; Refine for coherence on single documents
- Progressive refinement produces higher-quality summaries than single-pass approaches

**Anti-patterns:**
- Single-pass summarization for documents exceeding context window
- Ignoring metadata when chunking — metadata loss breaks provenance

**Lyra section mappings:** §4.3 (Context) — context window management, §4.15 (Research) — document processing

---

### Chapter 4 — Building a Research Summarization Engine
**Pages:** 69–101
**Focus:** End-to-end research pipeline, LCEL composition

**Key insights:**
- Research engine pipeline: query rewriting -> web search -> web scraping -> summarization -> report generation
- LCEL (LangChain Expression Language) enables declarative chain composition with the `|` operator
- Sub-chains for each stage (Assistant Instructions, Web Searches, Search and Summarization, Web Research)
- Query rewriting improves search results by expanding/refining the user's question

**Best practices:**
- Break complex workflows into independently testable sub-chains
- Use query rewriting to bridge the gap between user language and search engine language
- LCEL chains are inherently retry-able and observable via LangSmith

**Anti-patterns:**
- Monolithic prompt design for multi-stage research tasks
- Raw web scraping without content extraction/cleaning

**Lyra section mappings:** §4.15 (Research) — research pipeline architecture, §4.5 (Router) — query routing

---

### Chapter 5 — Agentic Workflows with LangGraph
**Pages:** 103–117
**Focus:** State machines for agents, Node/Edge model

**Key insights:**
- Workflows: deterministic, predefined paths through a graph
- Agents: LLM-driven routing where the model decides which node to visit next
- Key decision heuristic: use workflows when the path is known; use agents when the path depends on runtime reasoning
- LangGraph core concepts: StateGraph, nodes (functions), edges (transitions), entry points, conditional routing
- State is a TypedDict with Annotated reducers (e.g., `operator.add` for message accumulation)
- Moving from LCEL chains to LangGraph: replace linear chains with explicit graph nodes for conditional branching

**Best practices:**
- Start with a workflow (deterministic graph) and add agent nodes only where runtime decisions are needed
- Each node should have a single responsibility
- Use conditional edges for branching logic; avoid embedding complex routing inside nodes

**Anti-patterns:**
- Using agents for purely deterministic flows (overhead without benefit)
- Embedding tool logic inside nodes instead of using the tool-calling protocol

**Lyra section mappings:** §4.5 (Router) — graph-based routing, §4.16 (Reliability) — state rehydration, §4.26 (Harness Engineering) — workflow orchestration

---

## Part 3: Q&A Chatbots

### Chapter 6 — RAG Fundamentals with ChromaDB
**Pages:** 121–141
**Focus:** RAG from scratch, vector stores, semantic search

**Key insights:**
- RAG pattern: Ingestion (chunk -> embed -> store) and Retrieval (embed query -> search -> inject into prompt)
- Vector stores convert text to embeddings; similarity search returns nearest neighbors
- Vector libraries (FAISS) vs vector databases (ChromaDB, Pinecone): libraries are in-process; databases are persistent and multi-user
- Full RAG implementation from scratch: embedding function, ChromaDB client, similarity search, LLM invocation with retrieved context

**Best practices:**
- Keep ingestion and retrieval as separate, independently testable stages
- Use vector databases (not libraries) for any production workload
- Always include source citations in RAG responses

**Anti-patterns:**
- Using raw similarity scores without threshold filtering (returns irrelevant chunks)
- Mixing different embedding models in the same collection

**Lyra section mappings:** §4.2 (Memory) — vector-based long-term memory, §4.3 (Context) — retrieval-augmented context

---

### Chapter 7 — Q&A Chatbots with LangChain and LangSmith
**Pages:** 143–169
**Focus:** Production RAG pipelines, LangSmith observability

**Key insights:**
- LangChain's RAG object model: loaders -> transformers -> embeddings -> vector stores -> retrievers
- Content ingestion: splitting documents, removing duplication, ingesting from folders
- Q&A pipeline: query vector store directly, or chain through a retriever + LLM
- LangSmith tracing: automatic capture of every chain step, tool call, and model invocation
- LangSmith enables debugging: inspect intermediate results, identify where retrieval failed

**Best practices:**
- Deduplicate content during ingestion to prevent redundant context
- Trace every production query to build an evaluation dataset
- Use LangSmith's annotation features to label good/bad responses for iterative improvement

**Anti-patterns:**
- Deploying RAG chatbots without observability (flying blind)
- Skipping content deduplication — leads to bloated context windows

**Lyra section mappings:** §4.3 (Context) — retrieval pipelines, §4.16 (Reliability) — observability/tracing, §4.26 (Harness Engineering) — evaluation datasets

---

## Part 4: Advanced RAG (Chapters 8–10)
*Skimmed — advanced RAG techniques for retrieval optimization. Core concepts: ParentDocumentRetriever, MultiVectorRetriever, HyDE, query decomposition, multi-backend routing (vector/SQL/knowledge graph), Reciprocal Rank Fusion. Relevant primarily to Lyra §4.2 (Memory) and §4.3 (Context) for multi-source retrieval patterns.*

---

## Part 5: AI Agents — MOST RELEVANT FOR LYRA

### Chapter 11 — Building Tool-Based Agents with LangGraph
**Pages:** 267–291
**Focus:** ReAct agent pattern, tool calling protocol, LangSmith debugging

**Key insights:**
- Tool calling protocol: the LLM receives tool definitions in its system prompt, decides which tool to call, emits a structured tool call, the application executes it, returns results to the LLM, which synthesizes a final answer
- Agent state tracks the full conversation: `messages` list accumulates HumanMessage, AIMessage, ToolMessage
- The ReAct agent loop: LLM node (reasons + decides action) -> Tool node (executes) -> back to LLM -> repeat until final answer
- LangGraph's `create_react_agent` provides prebuilt ReAct implementation
- System guidance dramatically improves tool selection: tell the agent explicitly which tool to use and when
- LangSmith traces show the full decision tree: which tool was called, what arguments, what results, what the LLM decided next

**Code architecture (critical):**
```
AgentState = TypedDict with messages (Annotated[list, operator.add])
├── llm_node: LLM decides which tool to call (or returns final response)
├── tool_node: executes tool calls from the LLM
└── Routing: conditional edge — if tool_calls exist, go to tool_node; else END
```

**Best practices:**
- Register tools with clear, specific descriptions — the LLM uses these to decide which tool to invoke
- Use system prompts to explicitly guide tool selection ("Use the weather tool ONLY when the user asks about weather")
- Debug with LangSmith: every tool call, its arguments, and its result are visible in traces
- Start with `create_react_agent` (prebuilt) before customizing the graph
- Explicitly constrain tool usage in the system prompt to prevent incorrect tool selection

**Anti-patterns:**
- Tool descriptions that are too vague — LLM selects the wrong tool or calls a tool when it should not
- Allowing the agent unbounded tool-calling loops without a `remaining_steps` limit
- Registering tools without typing — missing `args_schema` leads to malformed tool calls

**Lyra section mappings:** §4.7 (Plugins) — tool registration pattern, §4.5 (Router) — conditional routing, §4.16 (Reliability) — LangSmith-style tracing, §4.9 (Commands) — system prompt design

---

### Chapter 12 — Multi-Agent Systems
**Pages:** 293–307
**Focus:** Router pattern, Supervisor pattern, agent collaboration

**Key insights:**
- **Router pattern:** A classifier agent receives the user query, determines which specialist agent should handle it, and dispatches. Each query takes a "one-way ticket" — one agent handles it, then END.
- **Supervisor pattern:** A supervisor agent orchestrates multiple specialist agents as "sub-tools," invoking them potentially multiple times per query. Each specialist agent is wrapped as a tool the supervisor can call (`transfer_to_*`). This enables "return tickets" — agents can be revisited.
- Router implementation: LLM with structured output (Pydantic) classifying intent, then `Command(goto=agent_name)` to route
- Supervisor implementation: `create_supervisor(agents=[...], model=..., prompt=...)` — agents become tools for the supervisor
- Supervisor needs a more powerful model (e.g., GPT-5) because it must decompose complex multi-step requests and coordinate multiple agents
- LangSmith traces show multi-agent flows: supervisor -> transfer_to_agent -> agent execution -> back to supervisor -> next agent

**Architecture comparison:**
| Aspect | Router | Supervisor |
|--------|--------|------------|
| Agent invocation | One per query | Multiple per query |
| Complexity | Single-intent queries | Multi-part, cross-domain queries |
| State sharing | None between agents | Intermediate results passed via supervisor |
| Model requirement | Lightweight classifier | Powerful reasoning model |
| Use case | Customer service triage | Complex research, multi-step planning |

**Best practices:**
- Assign each agent a unique name for supervisor tool routing
- Provide explicit criteria for edge cases in router prompts (ambiguous queries -> default route or clarification)
- Use structured formats (JSON) not natural language when agents pass data between each other
- Include `current_agent` and `agent_history` fields in state to track handoffs
- Test router accuracy with a labeled dataset of queries with correct agent assignments
- Use a more powerful LLM for the supervisor than for leaf agents

**Anti-patterns:**
- Router that silently fails on ambiguous queries (provide a default or clarification path)
- Supervisor without visibility into specialist agent capabilities
- Unstructured inter-agent communication (parsing errors increase)
- Using the router pattern for multi-step queries that need multiple agents

**Lyra section mappings:** §4.5 (Router) — router agent pattern, §4.26 (Harness Engineering) — supervisor orchestration, §4.7 (Plugins) — agent-as-tool wrapping, §4.16 (Reliability) — agent handoff tracking

---

### Chapter 13 — Building and Consuming MCP Servers
**Pages:** 308–326
**Focus:** Model Context Protocol architecture, server implementation, tool integration

**Key insights:**
- MCP solves the "every team wraps every API" problem: providers expose tools via MCP servers; agents consume them through a standardized protocol
- Architecture: MCP Host (agent/application) -> MCP Client -> MCP Server (exposes tools) -> Resources (APIs, databases, files)
- MCP servers can be local (STDIO transport) or remote (Streamable HTTP transport)
- FastMCP 2 (Python): decorator-based tool definition (`@mcp.tool`), automatic schema generation from type hints, built-in error handling
- MCP Inspector: web UI for testing MCP servers interactively (list tools, run queries, inspect results)
- Integration with LangChain: `MultiServerMCPClient` aggregates tools from multiple MCP servers into a single tool list
- Local tools and remote MCP tools can be combined seamlessly in the same agent
- Major LLM providers (OpenAI, Google, Anthropic) have adopted MCP natively

**MCP server implementation pattern:**
```python
mcp = FastMCP("server-name")

@mcp.tool(description="Clear description of what the tool does")
async def my_tool(param: str) -> Dict:
    # Tool implementation
    return result

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8020)
```

**Key ecosystem resources:**
- Official MCP portal: github.com/modelcontextprotocol/servers
- mcp.so: 16,000+ community servers
- smithery.ai: 5,000+ tools
- mcpservers.org: ~1,500 servers

**Best practices:**
- Use official MCP SDKs (FastMCP 2) — never implement the protocol from scratch
- Test MCP servers with MCP Inspector before integrating into agents
- Use `MultiServerMCPClient` to aggregate tools from multiple MCP servers
- Combine MCP-provided tools with local tools in the same agent (they use identical interfaces)
- Configure authentication carefully — MCP servers often access sensitive resources
- Use HTTP transport for production (network-accessible), STDIO for local development

**Anti-patterns:**
- Implementing MCP protocol manually instead of using SDKs
- Hardcoding MCP server URLs — they should be configuration-driven
- Skipping MCP Inspector testing before agent integration
- Treating MCP tools differently from local tools in agent code

**Lyra section mappings:** §4.7 (Plugins) — MCP as standardized plugin protocol, §4.3 (Context) — external context via MCP, §4.26 (Harness Engineering) — tool ecosystem architecture, §4.9 (Commands) — tool discovery/consumption

---

### Chapter 14 — Productionizing AI Agents: Memory, Guardrails, and Beyond
**Pages:** 327–350
**Focus:** Short-term memory, checkpointing, layered guardrails, production deployment

#### 14.1 Memory (pages 328–337)

**Key insights:**
- Three memory scopes: short-term (session), long-term user (cross-session preferences), long-term application (global knowledge)
- LangGraph checkpoints: snapshots of graph state at each super-step (node execution), stored by a checkpointer
- Checkpointer stores: conversation history, tool outputs, intermediate variables, execution metadata
- `InMemorySaver` for development; `SqliteSaver` or `PostgresSaver` for production
- Thread ID (UUID) links checkpoints to a specific session — used to rehydrate state on subsequent turns
- `use_previous_response_id=True` with OpenAI Responses API: sends only the previous response ID instead of full history
- Checkpoints enable: conversational continuity, state rehydration after failure, human-in-the-loop pause/resume, workflow replay/inspection from any point
- Manual rewind: `get_state_history(config)` -> extract `checkpoint_id` -> build new config -> `invoke(None, new_config)` to rehydrate -> continue

**Memory implementation checklist:**
1. Generate `thread_id = uuid.uuid1()` at session start
2. Create config: `{"configurable": {"thread_id": thread_id}}`
3. Instantiate checkpointer: `InMemorySaver()` (dev) or `PostgresSaver` (prod)
4. Compile graph with checkpointer: `graph.compile(checkpointer=checkpointer)`
5. Pass config to every `invoke()` call

**Best practices:**
- Use PostgreSQL-based checkpointers for production (scalability, concurrency, persistence across restarts)
- Thread IDs should be UUIDs, stored per user session
- Enable `use_previous_response_id` when using OpenAI Responses API with LangGraph memory (mandatory — avoids duplicate submission errors)
- Checkpoints preserve ALL state, not just messages — use this for sophisticated recovery scenarios

**Anti-patterns:**
- Using `InMemorySaver` in production (state lost on restart)
- Not generating unique thread IDs per session (cross-user state pollution)
- Re-sending full history when `use_previous_response_id` is available (wastes tokens, causes errors with Responses API)

#### 14.2 Guardrails (pages 337–345)

**Key insights:**
- Three guardrail categories: rule-based (regex/patterns), retrieval-based (check against approved sources), model-based (compact classification models)
- Four insertion points: pre-model (input filtering), post-model (output validation), routing-stage (intent check), tool-level (action authorization)
- Layered guardrails are critical: router-level (domain relevance) + agent-level (sub-domain scope, e.g., Cornwall only)
- Implementation pattern: Pydantic `GuardrailDecision` model -> structured LLM output -> conditional routing to `guardrail_refusal` node or normal flow
- `pre_model_hook` in LangGraph ReAct agents: intercepts input before LLM, can prepend refusal instructions
- `post_model_hook`: validates LLM output before delivery
- Cost control is a guardrail benefit: blocking out-of-scope queries prevents resource abuse (users using your agent as free LLM access)

**Guardrail implementation pattern:**
```python
class GuardrailDecision(BaseModel):
    is_in_scope: bool
    reason: str

llm_guardrail = llm.with_structured_output(GuardrailDecision)

def pre_model_guardrail(state):
    decision = llm_guardrail.invoke(classifier_messages)
    if not decision.is_in_scope:
        return {"llm_input_messages": [SystemMessage(content=REFUSAL), *messages]}
    return {}  # Pass through unchanged
```

**Best practices:**
- Each agent should validate its own inputs, even if higher-level checks exist ("belt and suspenders")
- Router-level guardrails for fast fail-fast rejection; agent-level for scope precision
- Use structured output (Pydantic) for guardrail decisions — no string parsing
- Pre-model hooks block bad queries before they consume LLM tokens
- Post-model hooks catch hallucinated citations, biased language, leaked data, formatting errors

**Anti-patterns:**
- Relying solely on router-level guardrails without agent-level validation
- Using expensive LLM calls for guardrail classification — use compact models where possible
- Guardrails that silently drop queries instead of providing clear refusal messages

#### 14.3 Beyond This Chapter (pages 346–350)

**Key insights:**
- **Long-term memory:** Dedicated vector stores per user, periodic summarization + pruning, PII compliance controls
- **Human-in-the-loop:** Escalate ambiguous queries, incomplete data, high-impact decisions to human reviewers; log all decisions to improve automated thresholds
- **Post-model guardrails:** Filter outdated info, redact sensitive data, enforce brand tone, verify structured output formats
- **Evaluation:** Functional testing (correct answers), behavioral testing (policy/safety), performance testing (latency/cost), regression testing (prompt/tool/LLM changes)
- **Deployment:** LangGraph Platform (managed hosting + monitoring), Open Agent Platform (multi-agent orchestration runtime); both available as SaaS or private cloud deployment
- **Evaluation datasets:** 100+ query-answer pairs, labeled correct/incorrect, include edge cases and adversarial examples
- **Production monitoring:** track error rate, P95 latency, tokens per query, tool success rate; set alerts for anomalies
- **Staged rollout:** canary testing on traffic subsets before full deployment

**Best practices:**
- Build evaluation datasets continuously from production traces
- Use human-in-the-loop decisions as training data for improving guardrail thresholds
- Track accuracy, precision, recall, F1 scores across evaluation runs on new model versions
- Deploy with canary testing: gradual traffic increases with automated rollback on anomaly detection

**Anti-patterns:**
- Deploying without systematic evaluation (the most overlooked step)
- Treating evaluation as one-time rather than continuous
- Skipping human-in-the-loop for high-stakes agent actions

**Lyra section mappings:** §4.2 (Memory) — LangGraph checkpoints, vector-based long-term, §4.17 (Safety) — layered guardrails, §4.16 (Reliability) — evaluation, monitoring, staged rollout, §4.26 (Harness Engineering) — deployment, human-in-the-loop, observability, §4.3 (Context) — short-term conversational memory

---

## Appendices (A–E)
*Skipped per instructions — setup guides for Jupyter, LLM selection, SQLite installation, open-source LLMs.*

---

## Cross-Cutting Themes Across the Book

1. **Observability is not optional.** Every chapter from 7 onward emphasizes LangSmith tracing as essential, not nice-to-have. The agent's decision process is a black box without traces.

2. **Structured output everywhere.** Pydantic models for guardrail decisions, router classification, tool arguments — structured output eliminates brittle string parsing throughout the stack.

3. **Framework over raw API calls.** LangChain/LangGraph/MCP provide tested abstractions for common patterns (tool calling, checkpointing, multi-agent coordination) that are error-prone to implement from scratch.

4. **Layered defense.** Guardrails at router, agent, pre-model, post-model, and tool levels — no single check is sufficient.

5. **Progressive complexity.** Start with workflows, add agents only where runtime decisions are needed. Start with `create_react_agent`, customize only when necessary. Start with `InMemorySaver`, upgrade to PostgreSQL for production.
