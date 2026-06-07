# AI Agents in Action — Best Practices Playbook
**Source:** Micheal Lanham, *AI Agents in Action* (Manning, 2025)
**Extracted for:** Lyra agent harness upgrade

---

## Practice 1: Execute Plans Locally, Not Through the LLM
- **What:** In a planner, construct the plan via LLM prompt (isolated, no chat history), parse the JSON plan, then execute each step in a local executor. Only send final aggregated results back to the LLM for summarization.
- **Why:** Reduces token consumption dramatically. Decouples plan execution from LLM capabilities — allows models without tool-use support to use planners. Prevents the LLM from going off-script mid-execution. Execution can use any runtime (Python, Docker, API calls).
- **Lyra route:** §4.6 — Planning subsystem architecture
- **Source:** Chapter 11, Section 11.3

---

## Practice 2: Use Group Chat, Not Nested Chat, for Complex Multi-Agent Collaboration
- **What:** In multi-agent systems, use a shared conversation channel (GroupChatManager in AutoGen) where all agents see all messages, rather than sequential nested delegation chains. The group chat manager coordinates responses to reduce overlap.
- **Why:** Nested chats are like the telephone game — information degrades with each sequential pass. Group chat preserves full context for all agents, enabling better collaboration on long-running tasks. Tradeoff: more token-expensive but worth it for complex tasks.
- **Lyra route:** §4.3 — Multi-agent topology
- **Source:** Chapter 4, Section 4.3

---

## Practice 3: Prefer Tools/Actions Over Code Generation
- **What:** Give agents pre-built, tested functions (tools/actions) to accomplish tasks rather than asking agents to write and execute code to solve problems.
- **Why:** Agent-generated code "can be easily broken, needs to be maintained, and can change quickly." Tools are deterministic, testable, and maintainable. Code generation should be the last resort, not the primary interaction pattern. AutoGen Studio's skill system demonstrates this: adding an `describe_image` skill instead of asking agents to write image analysis code.
- **Lyra route:** §5.1 — Tool system design
- **Source:** Chapter 4, Section 4.1.2; Chapter 6, Section 6.2.2

---

## Practice 4: Implement Agent Observability from Day One
- **What:** Integrate an observability platform (AgentOps or equivalent) that captures: total session duration, prompt and completion tokens per call, LLM call timings, estimated cost per run, tool/action invocation traces, and agent repetition metrics.
- **Why:** Agent conversations are extremely verbose and costly. A single joke generation cost ~$0.50. Without cost observability, you cannot optimize. The "Repeat Thoughts" metric reveals when agents are stuck in indecision loops — trigger to reconfigure agent processing patterns. "It's essential to observe what those costs are in terms of practicality and commercialization."
- **Lyra route:** §3.2 — Observability and monitoring
- **Source:** Chapter 4, Section 4.4.2

---

## Practice 5: Compress Agent Memory Periodically
- **What:** Apply k-means clustering to memory/knowledge embeddings, then use an LLM compression function to summarize each cluster into concise representations. Store compressed items as new embeddings.
- **Why:** Uncompressed memory becomes cluttered with redundant, repetitive, and duplicate information, degrading retrieval quality. Multi-pass compression (compressing 2+ times) creates hierarchical knowledge levels that improve retrieval performance. Knowledge compression is especially beneficial for verbose/literary documents; memory compression benefits from periodic application. Multiple compression levels enable efficient multi-resolution retrieval.
- **Lyra route:** §4.2 — Memory subsystem; §8.1 — Knowledge management
- **Source:** Chapter 8, Section 8.7

---

## Practice 6: Limit Agent Actions to the Minimum Needed
- **What:** Give each agent only the specific actions/tools required for its assigned goal. Do not register all available functions to every agent.
- **Why:** Three reasons: (1) "More actions can confuse an agent into deciding which to use or even how to solve a goal." (2) APIs have limits on the number of tools per request. (3) Safety — "Agents may use your actions in ways you didn't intend." The book documents real cases of agents going rogue: downloading files, executing code when not intended, deleting files, iterating endlessly between tools.
- **Lyra route:** §5.1 — Tool system; §6.1 — Safety
- **Source:** Chapter 11, Section 11.1; Chapter 6, Section 6.3.1

---

## Practice 7: Use Token-Based Document Splitting for RAG
- **What:** Split documents using tokenization (e.g., `tiktoken` encoder) rather than character-based splitting. Apply chunk overlap (10-25 tokens) to prevent semantic truncation.
- **Why:** Token-based splitting "provides a better base for how the text will be interpreted by language models and for semantic similarity." Removes irrelevant whitespace. Produces "significantly better results" than character-based splitting in retrieval tasks. The ideal is semantic splitting (by meaning), but token-based is the pragmatic sweet spot.
- **Lyra route:** §8.1 — Knowledge ingestion pipeline
- **Source:** Chapter 8, Section 8.4.2

---

## Practice 8: Use Cheaper Models for Function Routing
- **What:** Route user requests to simpler/cheaper models (GPT-3.5 class) for the function-calling step (identifying which tool to invoke and extracting parameters), reserving expensive models for content generation.
- **Why:** "Delegating functions is a more straightforward task and can be done using older, cheaper, less sophisticated language models." Significant cost savings without quality loss since function routing requires classification, not generation. Pattern demonstrated in the book's `parallel_functions.py` example.
- **Lyra route:** §5.2 — Model routing and cost optimization
- **Source:** Chapter 5, Section 5.2.2

---

## Practice 9: Isolate Agent Code Execution in Containers
- **What:** Run all agent-executed code inside Docker containers (AutoGen's recommendation) or isolated virtual environments (Playground's approach). Never execute agent-generated code directly on the host system.
- **Why:** Safety — agents can and do write destructive code. Docker "can isolate and virtualize the agents' environment, thus isolating potentially harmful code." Also prevents agent code from blocking the main process (e.g., Pygame windows). The book explicitly warns about agent code execution risks.
- **Lyra route:** §6.1 — Safety sandboxing
- **Source:** Chapter 4, Section 4.1.1; Chapter 6, Section 6.2.2

---

## Practice 10: Evaluate Prompts Systematically with Embedding Similarity
- **What:** Use prompt flow DAGs with embedding-based evaluation: generate output → embed prediction → embed expected answer → compute cosine similarity. Compare multiple profile variants against the same inputs.
- **Why:** Ad-hoc prompt changes lead to regression. Systematic evaluation with similarity scoring provides quantitative prompt quality measurement. Batch processing enables profile comparison at scale. Grounding evaluation (checking output against reference context) detects hallucination.
- **Lyra route:** §4.4 — Persona evaluation; §7.1 — Quality assurance
- **Source:** Chapter 9, Sections 9.4-9.7; Chapter 10, Section 10.1.1

---

## Practice 11: Use Self-Consistency Voting for Reasoning Reliability
- **What:** For reasoning tasks, generate multiple independent reasoning paths (different samples/temperatures), then take the majority-vote answer. Implementation: run the same prompt N times, collect answers, select the most frequent.
- **Why:** Single reasoning paths can be wrong with high confidence (demonstrated with Strawberry/O1 on the time travel problem — confidently wrong). Self-consistency improves accuracy on reasoning tasks by aggregating diverse reasoning traces. Tradeoff: N× cost for improved reliability. Use selectively for high-stakes decisions.
- **Lyra route:** §4.5 — Reasoning subsystem; §7.1 — Evaluation
- **Source:** Chapter 10, Section 10.3.1

---

## Practice 12: Extract LLM Self-Feedback for Continuous Improvement
- **What:** When an agent gets a wrong answer: provide the correct answer, ask the LLM to "review what you did wrong and suggest feedback you could give yourself when trying to solve similar future problems." Extract the generated feedback and incorporate it into system instructions.
- **Why:** Enables continuous prompt improvement without human prompt engineering. The LLM identifies its own failure modes and suggests corrective strategies. Works consistently on advanced models (O1, Claude). Even when the LLM can't fix itself, the feedback provides actionable prompt improvements for future runs.
- **Lyra route:** §4.6 — Feedback loops; §7.2 — Continuous improvement
- **Source:** Chapter 11, Section 11.4

---

## Practice 13: Separate Knowledge Stores from Memory Stores
- **What:** Maintain distinct vector stores for knowledge (preloaded documents, reference material) and memory (conversation history, user preferences, extracted facts). Support multiple memory types per agent (semantic, episodic, procedural).
- **Why:** Knowledge and memory use the same RAG mechanism but have different update patterns and lifecycles. Knowledge is loaded once, compressed once; memory evolves continuously and needs periodic compression. Multi-store architecture enables selective sharing (different memory stores for different users/groups). Agents may need different memory types for different tasks.
- **Lyra route:** §4.2 — Memory architecture; §8.1 — Knowledge management
- **Source:** Chapter 8, Sections 8.5-8.7

---

## Practice 14: Match Planning/Reasoning Depth to Application Latency Requirements
- **What:** Not all applications need deep reasoning. Classify by latency sensitivity: real-time (no reasoning), near-real-time (light CoT), batch/autonomous (full reasoning + evaluation + feedback). Use the application matrix from Chapter 11.
- **Why:** "Reasoning is a process that requires the LLM to think through a problem, and this often requires longer response times." Heavy reasoning is inappropriate for real-time personal assistants and game AI. Autonomous agents and research tasks benefit from maximum reasoning. "Multiple agents — those with reasoning and those without" may serve different roles in the same system.
- **Lyra route:** §4.5 — Reasoning configuration; §4.6 — Planning depth control
- **Source:** Chapter 11, Section 11.5.2

---

## Practice 15: Design for Plugin-Based Agent Capability Discovery
- **What:** Use a plugin architecture where agents, actions, profiles, and planners are dynamically discovered at runtime (YAML files for profiles, Python decorators for actions, folder-based plugin loading). Never hardcode agent capabilities.
- **Why:** Enables extension without code changes. New actions = drop a file in a folder. New agent profiles = add a YAML file. This pattern from Nexus demonstrates how to keep an agent platform extensible while maintaining teaching simplicity. The `@agent_action` decorator pattern from the Playground is equally applicable.
- **Lyra route:** §3.1 — Platform architecture; §5.1 — Plugin system
- **Source:** Chapter 7, Sections 7.1-7.5; Chapter 6, Section 6.2.2
