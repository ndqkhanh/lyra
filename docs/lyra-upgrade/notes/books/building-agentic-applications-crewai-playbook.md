# Building Agentic Applications with CrewAI and MCP — Best Practices Playbook

## Practice 1: Start Simple, Escalate Only With Reason
- **What:** Build your agentic system by progressing through four levels: single LLM call → augmented LLM with tools → simple agentic workflow → multi-agent system. Only advance when you have a concrete reason — each step adds power but also cost, complexity, and new failure modes.
- **Why:** A single well-prompted LLM call beats a multi-agent crew for many tasks. Over-engineering agentic systems is the most common failure mode. A workflow with one LLM classification step and one generation step is "agentic" enough for most production use cases.
- **Lyra route:** §4.1, §4.10 (system design decisions)
- **Source:** Chapter 1

## Practice 2: The Augmented LLM Diagnostic Framework
- **What:** Model every agent as an augmented LLM with exactly three capabilities: retrieval, tools, and memory. When things break (and they will), ask: "Which of these three capabilities failed?" — Did retrieval return irrelevant context? Did a tool fail? Did the model lose state?
- **Why:** This atomic mental model makes debugging agentic failures tractable. Instead of debugging a monolithic "agent," you isolate failures to one of three well-understood subsystems.
- **Lyra route:** §4.5 (observability and debugging)
- **Source:** Chapter 1

## Practice 3: The 80/20 Rule for Task Design
- **What:** Put 80% of your effort into designing tasks (description, expected output, tool specification), and only 20% into defining agents (role, goal, backstory). Even the best agent fails with poorly designed tasks, but well-designed tasks can elevate a simple agent to produce consistent, high-quality outputs.
- **Why:** Task descriptions are where context, constraints, and output expectations are communicated to the LLM. They are the highest-leverage artifact in the entire system. Vague tasks produce unpredictable results regardless of agent quality.
- **Lyra route:** §4.3 (task design and decomposition)
- **Source:** Chapters 1, 2

## Practice 4: Small Focused Agents, 3-10 Tools Max
- **What:** Keep agents focused on specific domains with 3-10 tools per agent. Avoid creating a single "god agent" with dozens of tools. As tool count grows, LLM tool-selection accuracy degrades sharply. Multiple smaller agents collaborating will always outperform one overloaded generalist.
- **Why:** LLM context windows degrade with length, and larger tool sets confuse model tool selection. From "12 Factor Agents" (Dex Horthy): keep agents focused, 20 steps max. Cursor enforces a 40-tool maximum. The author's experience shows performance degradation well before formal limits are reached.
- **Lyra route:** §4.2 (agent design), §4.8 (plugin/tool architecture)
- **Source:** Chapter 1

## Practice 5: Scope File-System Tools to a Base Directory
- **What:** Never give agents raw filesystem access. Implement or use scoped file tools that validate every path against a base directory, with explicit path traversal prevention using `os.path.realpath()` canonicalization and prefix checking.
- **Why:** CrewAI's built-in `FileReadTool` and `FileWriteTool` have no directory scoping — an agent could theoretically access any file on the machine. This is a security-critical anti-pattern that must be addressed with custom scoped tools (or the `crewai-fs-plus` package).
- **Lyra route:** §4.9 (security and safety)
- **Source:** Chapter 4

## Practice 6: Use Pydantic Output Models as Agent Contracts
- **What:** Define strict Pydantic output models for every agent in a multi-step pipeline. Each agent knows exactly what structured data it will receive and what it must produce. CrewAI automatically validates, parses, and runs a repair/retry loop on schema violations.
- **Why:** Free-form text between agents cascades errors — one agent's quirky output becomes the next agent's confusing input. Structured contracts make multi-agent pipelines reliable and testable. If parsing fails, CrewAI retries with specific error feedback.
- **Lyra route:** §4.3 (task design), §4.6 (inter-agent communication)
- **Source:** Chapters 2, 5

## Practice 7: Separate Agent Definition from Execution
- **What:** Design agents as definitions (role, goal, backstory, tools, templates) that are separate from the execution loop. Override system/prompt/response templates when default behavior needs tuning for a specific domain or model. The executor assembles the message stack, calls the LLM, handles tool calls, and iterates until completion or timeout.
- **Why:** This separation allows you to swap LLM providers, tune prompt templates per model, and reuse agent definitions across different execution contexts (crew, flow, solo) without rewriting the agent.
- **Lyra route:** §4.2 (agent architecture)
- **Source:** Chapter 2

## Practice 8: Embed Knowledge, Don't Prompt It
- **What:** Use automated RAG (via CrewAI's Knowledge feature or equivalent) instead of hard-coding context into prompts. Attach documents to crews or agents, let the system chunk (default 4000 chars / 200 overlap), embed, store in a vector DB, and auto-retrieve top-K relevant snippets at task time. Configure `results_limit` and `score_threshold` to control retrieval precision vs. token cost.
- **Why:** Hard-coded context in prompts bloats context windows and becomes stale. Automated RAG injects only the most semantically relevant chunks at runtime. Chunk size, overlap, retrieval limit, and score thresholds provide knobs to trade context quality against token usage.
- **Lyra route:** §4.4 (memory and context management)
- **Source:** Chapter 3

## Practice 9: Design Backstories With Specificity, Not Generality
- **What:** Agent backstories should claim specific experience ("Your 10 years of cataloging products for major e-commerce platforms"), name the domain details you care about ("materials, construction quality, distinguishing features"), and match the persona to the task's difficulty. When output is too shallow or generic, the backstory is the first thing to revisit.
- **Why:** Specific backstory details are not decoration — they signal to the model which observations matter and prime it to draw on the right kind of domain knowledge. "You are very knowledgeable" produces generic results; naming exact domains of expertise measurably improves output.
- **Lyra route:** §4.2 (agent design)
- **Source:** Chapter 5

## Practice 10: Use MCP as a Standardized Tool Bus
- **What:** Adopt MCP (Model Context Protocol) as the universal plug for AI tool integration. Build one MCP server per capability domain, and let any compatible client (Cursor, Claude Desktop, ChatGPT) discover and use it. Expose tools (executable actions), resources (read-only context, URI-addressable), and prompts (user-invokable slash commands).
- **Why:** Without MCP, each AI client requires a separate integration. MCP solves this integration problem once. It also creates a growing ecosystem of pre-built servers (Playwright for browser automation, GitHub, Slack, databases) that you can configure instead of building custom integrations.
- **Lyra route:** §4.8 (plugin/tool architecture), §4.9 (API and protocol design)
- **Source:** Chapter 4

## Practice 11: Match Embedding Models to Task Resolution
- **What:** Choose embedding dimensionality based on how similar your items are. For distinct categories (wristwatch vs. backpack), lower dimensions (768) suffice. For subtle variants (sneakers differing only in colorway), use higher dimensions (up to 3072). CRITICAL: never mix embedding models between indexing and querying — vectors from different models live in incompatible spaces.
- **Why:** Dimensions × 4 bytes per vector → storage tradeoffs matter. Higher dimensions quadruple index size but are necessary for fine-grained similarity search. Mixing models produces nonsense results.
- **Lyra route:** §4.4 (retrieval pipeline), §4.7 (multimodal processing)
- **Source:** Chapter 5

## Practice 12: Adopt Multimodal Embeddings for Cross-Modal Retrieval
- **What:** Use a multimodal embedding model (e.g., Gemini Embedding 2) that maps both text and images into the same vector space. This enables image-as-query — a photo can find semantically matching text entries and vice versa.
- **Why:** Keyword search fails at cross-modal retrieval ("red sneaker" won't match "crimson athletic shoe"). Multimodal embeddings solve this by mapping both modalities into a shared semantic space where proximity equals similarity.
- **Lyra route:** §4.7 (multimodal input handling)
- **Source:** Chapter 5

## Practice 13: Choose Process Types by Workflow Predictability
- **What:** Use *sequential* process (fixed pipeline: A→B→C) when each step depends on the previous output and order is known. Use *hierarchical* process (manager agent delegates dynamically) when task order needs adjustment, validation is critical, or subtask decomposition is context-dependent. Enable delegation between agents for peer-to-peer clarification without restructuring the pipeline.
- **Why:** Sequential is predictable and debuggable but rigid. Hierarchical is flexible but harder to control and more expensive (manager LLM overhead). Delegation adds dynamic collaboration between agents without giving up the overall process structure.
- **Lyra route:** §4.3 (workflow orchestration), §4.6 (multi-agent coordination)
- **Source:** Chapter 3

## Practice 14: Run Synchronous I/O in Thread Pools Under Async MCP Servers
- **What:** When exposing agentic crews through MCP servers (which use asyncio), run synchronous operations (Playwright, blocking LLM calls) in a separate thread via `loop.run_in_executor()` with a thread pool. Disable verbose/rich console output to prevent JSON-RPC message corruption.
- **Why:** MCP servers use asyncio for request handling. Synchronous I/O (Playwright's browser API, synchronous LLM clients) cannot run directly in an asyncio event loop without threading errors. A thread pool executor provides the isolation boundary needed.
- **Lyra route:** §4.5 (harness engineering), §4.8 (server architecture)
- **Source:** Chapter 4

## Practice 15: Trade Autonomy for Predictability in Production
- **What:** Favor agentic workflows (developer-defined code paths with LLM steps) over fully autonomous agents for production systems. Use agents only where you genuinely cannot predict the steps in advance (open-ended research, complex debugging). Route by task type, gate between steps, and keep human-in-the-loop for high-stakes actions.
- **Why:** Fully autonomous agents are powerful but hard to make reliable. Problems include compounding error rates across steps (95% step success × 10 steps = 60% overall), non-deterministic outputs, token cost multiplication (5-20x), context degradation, and evaluation difficulty. Workflows with gated steps provide safety without sacrificing LLM intelligence.
- **Lyra route:** §4.1 (architecture), §4.9 (safety), §4.10 (reliability)
- **Source:** Chapter 1
