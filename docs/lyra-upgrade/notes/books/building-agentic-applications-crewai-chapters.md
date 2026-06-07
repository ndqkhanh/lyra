# Building Agentic Applications with CrewAI and MCP — Chapter Notes
**Author:** Max Gfeller | **Year:** 2026 (MEAP v2) | **Core Thesis:** Production agentic systems are built by composing small, focused augmented LLMs (agents with retrieval + tools + memory) into crews and workflows, starting simple and adding complexity only where it pays off. MCP standardizes the tool-integration layer.

---

## Chapter 1: Understanding Agentic Applications

- **Key insight:** The augmented LLM (retrieval + tools + memory) is the atomic building block of ALL agentic systems. Every multi-agent system is just multiple augmented LLMs coordinating. When things break, the diagnostic question is always: "Which of these three capabilities failed?"
- **Key insight:** Anthropic's distinction between *AI agents* (LLM dynamically directs its own reasoning loop) and *agentic workflows* (developer-defined code paths with dynamic routing) is critical. Most production systems are closer to workflows with agentic elements. Trade flexibility for predictability.
- **Key insight:** The "start simple" progression: single LLM call → augmented LLM with tools → agentic workflow → multi-agent system. Move up only with concrete reason — each step adds power but also cost, complexity, and new failure modes.
- **Five design patterns** (from Anthropic + Andrew Ng): (1) Prompt chaining — sequential LLM calls with programmatic "gates" between steps; (2) Routing — classify input, send to specialized handler; (3) Parallelization — sectioning (split subtasks) or voting (diverse perspectives); (4) Orchestrator-workers — central LLM dynamically decomposes and delegates; (5) Evaluator-optimizer — generator + critic loop until quality bar is met.
- **Numbers:** A step that succeeds 95% of the time, chained across 10 steps → ~60% overall success rate. Chain 20 steps → below 40%. Agentic systems consume 5-20x more tokens than a single prompt-response pair.
- **Anti-patterns:** Single agent with dozens of tools (Cursor caps at 40 tools; 3-10 tools per agent is recommended). The LLM gets lost with too many tools.
- **CrewAI primitives:** Agents (Role-Goal-Backstory), Tasks (Pydantic output schemas), Tools, Crews (multi-agent teams), Flows (deterministic workflows).
- **Relevant to Lyra §4.1, §4.2, §4.3, §4.10:** Foundational architecture patterns for multi-agent systems, tool-scoping, and reliability.

---

## Chapter 2: Creating and Running a Single Agent

- **Key insight:** Role-Goal-Backstory works because LLMs are excellent at role-playing. The effect is strongest with smaller/cheaper models.
- **Key insight:** The 80/20 rule — put 80% of effort into task design, 20% into agent definition. Well-designed tasks can elevate a simple agent; even the best agent fails with poorly designed tasks.
- **Key insight:** CrewAI's internal architecture separates *agent definition* from *agent execution*. Three composable templates (system_template, prompt_template, response_template) are assembled per LLM call. All three are overridable.
- **Agent executor loop:** Assemble message stack from templates → send to LLM → if tool call, execute tool → append observation → repeat → return final answer or hit iteration/time limit.
- **Structured output:** Pass a Pydantic model as `response_format`. CrewAI converts to JSON schema, bakes formatting instructions into the system prompt, parses the response, validates against schema, and runs a repair/retry loop on failure.
- **Tool scoping directive:** An agent should NOT have access to too many tools. Performance degrades with large tool sets. The limit depends on model capability, context size, and tool description clarity.
- **Custom prompt templates:** Override system/prompt/response templates for transparency and domain-specific behavior. Default system template includes psychological nudges ("Your job depends on it").
- **Model selection strategy:** Different agents should use different models. Complex reasoning → o3/o4-mini/gpt-5 or claude-4-opus. Creative writing → claude-4-sonnet. Speed → gpt-5-mini/nano or claude-4-sonnet.
- **Relevant to Lyra §4.2:** Agent identity design, structured output pipelines, repair/retry patterns.

---

## Chapter 3: Building a Multi-Agent Crew

- **Key insight:** YAML configuration separates prose (prompts, instructions) from Python logic. This is the default for new CrewAI projects, and it provides cleaner maintenance.
- **Key insight (Knowledge/RAG):** CrewAI's built-in RAG layer: attach documents → automatic chunking (default 4000 chars, 200 overlap) → embed → store in local ChromaDB → at task time, automatically retrieve top-K most relevant snippets into context. NO manual tool call needed.
- **KnowledgeConfig parameters:** `results_limit` (chunks per query) and `score_threshold` (minimum similarity, 0.0-1.0). Too many chunks → longer prompts, higher token usage, reduced model effectiveness.
- **Knowledge storage:** ChromaDB under platform-specific paths. Collections separated by scope (crew-level vs agent-level). Survives restarts without re-embedding.
- **Process types:** *Sequential* (fixed order, each builds on previous) vs *Hierarchical* (manager agent dynamically delegates). Sequential is the default.
- **Delegation:** `allow_delegation=True` equips agents with two built-in tools: *Ask Question Tool* (peer-to-peer clarification) and *Delegate Work Tool* (hand off subtasks). Can restrict via `allowed_agents` parameter.
- **Three memory types:** Short-term (current execution), long-term (persists insights across runs), entity memory (structured facts about people/companies/concepts).
- **Custom tool building:** Extend `BaseTool`, define Pydantic input schema, implement `_run()`. Tools are instantiated with developer-configured parameters (e.g., base_path for images).
- **Relevant to Lyra §4.4, §4.5, §4.6:** Memory architecture, knowledge/RAG injection, delegation patterns.

---

## Chapter 4: Exposing Agents with MCP

- **Key insight:** MCP (Model Context Protocol) is an open standard under the Linux Foundation's Agentic AI Foundation. It standardizes the client-server contract for tool discovery and invocation.
- **Three roles:** Host (application like Cursor/Claude Desktop), Client (one per server, speaks the protocol), Server (process exposing capabilities).
- **Three capability types:** Tools (verbs — executable actions), Resources (nouns — read-only context, URI-addressable), Prompts (reusable templates for user-invoked commands).
- **Transport:** stdio (local subprocess, low-latency, no networking) vs Streamable HTTP (remote, introduced 2025, enables team/hosted servers). Many clients (ChatGPT) only support remote HTTP.
- **Security MUST:** File-system tools must be scoped to a base directory with path traversal prevention. CrewAI's built-in file tools do NOT enforce this. Custom tools with `validate_and_resolve_path()` are required.
- **MCPServerAdapter:** Connects any MCP server to a CrewAI agent. Automatically discovers tools and wraps them as CrewAI-compatible tools. Used to give agents browser automation via Playwright MCP.
- **Production MCP patterns:** Move from local stdio to remote HTTP. Add OAuth authentication. Replace local Playwright with cloud browser (BrowserBase). Clone repo → run crew → commit + create PR.
- **Thread pool executor:** MCP servers use asyncio; Playwright uses sync API. Must run crew in a separate thread via `loop.run_in_executor()`. Disable verbose mode to avoid JSON-RPC corruption.
- **Relevant to Lyra §4.8, §4.9:** Plugin/tool architecture, MCP integration, security scoping.

---

## Chapter 5: Building Multimodal Crews

- **Key insight:** Two forms of multimodality: (1) *Generative* — vision LLM describes what it sees (used by image analysis agent). (2) *Embedding-based* — multimodal embedding model maps text AND images into the same vector space (used for catalog similarity search).
- **Key insight:** Multimodal embeddings enable image-as-query — a photo of a red sneaker finds "crimson athletic shoe" in the text catalog because both live in the same semantic vector space.
- **Critical rule:** You MUST use the same embedding model for indexing and querying. Vectors from different models live in incompatible spaces — mixing produces meaningless results.
- **Embedding dimensionality:** Gemini Embedding 2 max 3072 dims. Higher = finer distinctions but larger storage and slower search. 768 suffices for distinct categories; 3072 needed for subtle product variants. Each vector = dims × 4 bytes.
- **Agent backstory design principles:** (1) Claim specific experience, not generic expertise. (2) Name the domain details you care about — they signal to the model which observations matter. (3) Match persona to task difficulty. When output is too shallow, revisit the backstory first.
- **Structured output as agent contracts:** Pydantic output models enforce strict interfaces between agents in a sequential crew. Each agent knows exactly what it will receive/produce. Enables reliable multi-agent pipelines.
- **Production readiness:** Add API layer (FastAPI), queue (Redis/Celery), human review UI, image preprocessing (background removal, normalization), automated index rebuilding pipeline.
- **ChromaDB details:** Uses cosine similarity. Local embedded DB — no external services, no network latency. Not suitable for billion-scale; consider pgvector/Pinecone/Weaviate for production.
- **Relevant to Lyra §4.7:** Multimodal input handling, embedding strategy, agent-to-agent structured contracts.

---

## Status Note

This is a MEAP (Manning Early Access Program) v2 with only Chapters 1-5 available. The TOC lists planned chapters for 6-9 and Appendices A-F:

- **Ch 6:** Building Complex Flows (CrewAI Flows — deterministic multi-step orchestration with conditional logic, parallel processing, error recovery, state management)
- **Ch 7:** Creating a Chatbot with Copilotkit
- **Ch 8:** Building Extensible AI Systems with MCP Server Consumption
- **Ch 9:** Building Human-in-the-Loop Workflows
- **App A:** Setting up development environment (uv, Python 3.12+, API keys)
- **App B:** Deploying agents in production
- **App C:** Testing, evaluation, and monitoring
- **App D:** Security and compliance considerations
- **App E:** Local agents with Ollama
- **App F:** Performance optimization and scaling
