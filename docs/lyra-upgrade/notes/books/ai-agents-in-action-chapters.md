# AI Agents in Action — Chapter Notes
**Author:** Micheal Lanham | **Year:** 2025 | **Publisher:** Manning Publications
**Core Thesis:** AI agents represent a paradigm shift from traditional UIs/APIs toward natural language AI interfaces. Building effective agents requires orchestrating five core components — profile/persona, actions/tools, memory/knowledge, reasoning/evaluation, and planning/feedback. The book teaches practical construction through open-source tooling (AutoGen, CrewAI, Semantic Kernel, Nexus) with strong emphasis on observable, controllable, and cost-aware agent engineering.

**Target Audience:** Developers with basic Python knowledge; no prior agent/LLM experience required. Practical, code-heavy approach with low-code options.

---

## Chapter 1: Introduction to Agents and Their World
- **Key insight:** Defines the agent spectrum: Direct LLM Interaction → Agent/Assistant Proxy → Agent/Assistant → Autonomous Agent. The distinction between autonomous and non-autonomous agents is crucial for trust and safety.
- **Five core agent components introduced:** Profile/Persona, Actions/Tool Use, Memory/Knowledge, Reasoning/Evaluation, Planning/Feedback. This framework powers the entire book.
- **Multi-agent definition:** Agent profiles that work together in various configurations (proxy-controlled workers, group chat, hierarchical). Multi-agent benefit is magnified single-agent benefit — parallel task handling + cross-agent feedback.
- **Best practices:** Autonomous agents require trust in decision-making, guardrails/evaluation, and clear goal definition. Most production agents are non-autonomous but still provide significant automation benefits.
- **Anti-patterns:** Assuming all agents must be autonomous. "Trust is acquired over time."
- **AI Interface concept:** Software/data will be interfaced via natural language, not UIs/APIs/SQL. "Semantic" re-branded as "AI Interface" throughout the book.
- **Relevant to Lyra §4.1 (architecture foundation):** The 5-component framework maps directly to Lyra's subsystem decomposition.

---

## Chapter 2: Harnessing the Power of Large Language Models
- **Key insight:** Practical setup chapter — OpenAI API, local LLMs via LM Studio, prompt engineering fundamentals. Establishes the technical substrate all subsequent chapters build on.
- **Prompt engineering tactics covered:** Detailed queries, personas, delimiters, specifying steps, examples, output length specification.
- **Best practices:** LM Studio enables local LLM experimentation without cloud dependency. Choose LLMs based on specific needs (cost, latency, capability tradeoff).
- **Relevant to Lyra §2.1 (model interface):** Basic LLM connectivity patterns. Mostly foundational — skip-deep for Lyra unless adding model-routing infrastructure.
- **Verdict:** SKIP deep-read. Foundation/tutorial content. Key takeaway: local LLM support matters for offline/air-gapped Lyra deployment.

---

## Chapter 3: Engaging GPT Assistants
- **Key insight:** OpenAI Assistants as the baseline "agent" form. GPTs run in ChatGPT (account cost); Assistants run via API (token cost). Assistants can use Code Interpreter, file uploads, custom actions.
- **Economics insight:** "Expensive GPT assistants" — Code Interpreter runs at $0.03/session. File uploads provide knowledge augmentation without external RAG.
- **Best practices:** Custom actions via OpenAPI schemas. Assistants as building blocks for more complex multi-agent systems.
- **Relevant to Lyra §5.1 (tool use):** Foundational pattern for tool-augmented agents. Skip-deep — mostly OpenAI-specific tutorial content.
- **Verdict:** SKIP deep-read. Tool-specific (OpenAI). Relevant only for understanding assistant-as-building-block pattern.

---

## Chapter 4: Exploring Multi-Agent Systems
- **Key insight:** Two primary multi-agent paradigms: Conversational (AutoGen) vs. Role-based sequential/hierarchical (CrewAI). AutoGen uses natural language communication between agents; CrewAI uses explicit tasks, goals, backstories.
- **AutoGen communication patterns:**
  - **Proxy communication:** UserProxy agent directs work to assistants, evaluates output, iterates. Pattern: Human→UserProxy→Assistant→feedback loop→Human.
  - **Nested chats:** Sequential agent delegation (like telephone game — information degrades).
  - **Group chat (GroupChatManager):** Shared conversation channel. All agents see all messages. Reduces information loss but more token-expensive.
  - **AutoGen cache:** SQLite-based message caching. Enables continuing interrupted conversations. Critical for long-running agent tasks.
- **CrewAI patterns:**
  - **Agents have:** role, goal, verbose, memory, backstory, allow_delegation, tools.
  - **Tasks have:** description, expected_output, agent assignment, async_execution, output_file.
  - **Crew has:** agents, tasks, process (sequential/hierarchical), memory, cache, max_rpm, share_crew.
  - **Hierarchical processing:** Adds a crew manager LLM that coordinates delegation. Costly — "often costs over double" without significantly better output.
- **AgentOps observability (CRITICAL for Lyra):**
  - Captures: total duration, prompt/completion tokens, LLM call timings, estimated cost.
  - **Repeat Thoughts plot:** Measures agent repetition. High repetition = agent indecisiveness. Trigger to change processing patterns/agent configuration.
  - Cost observation is essential: single joke cost ~$0.50. "Agents can be very powerful, but they can also become very costly."
- **Best practices:**
  - Prefer group chat over nested chat for complex collaboration (avoid information loss).
  - Docker-isolate agent code execution (AutoGen explicitly recommends Docker).
  - Prefer tools/actions over code generation — "code can be easily broken, needs to be maintained, and can change quickly."
  - Always add observability from day one.
  - Monitor token costs relentlessly — agent conversations are extremely verbose.
- **Anti-patterns:**
  - Hierarchical processing without clear benefit — doubles costs for marginal improvement.
  - Allowing agents to write code instead of providing tools.
  - Ignoring agent repetition — indicates broken feedback loops.
- **Relevant to Lyra §4.3 (multi-agent topology):** Core architectural patterns for Lyra's multi-agent subsystem. Group chat pattern for Lyra's agent collaboration. Observable cost tracking mandatory.

---

## Chapter 5: Empowering Agents with Actions
- **Key insight:** Actions = plugins = tools = functions = skills. Unified concept across frameworks with varying terminology. The book standardizes on "actions."
- **OpenAI function calling pattern:**
  - Function definitions are JSON Schema objects registered as "tools."
  - LLM never executes functions — it returns function name + parsed parameters.
  - Application layer extracts parameters, executes function, appends results to messages, re-calls LLM.
  - **Cost optimization:** Use simpler/cheaper models (GPT-3.5) for function routing. Function delegation is a simpler task than content generation.
- **Semantic Kernel (SK):**
  - **Semantic functions:** Prompt templates registered as plugins. Define via config.json + skprompt.txt files.
  - **Native functions:** Python code decorated with @kernel_function. Any code capability.
  - **Plugin composition:** Native functions can be embedded within semantic function flows. Semantic functions can call native functions, and vice versa.
  - **SK as agent host:** Kernel manages multiple plugins, chat interface can invoke any registered plugin.
  - **Cross-language:** Plugins developed in Python consumable in C#/Java. Native functions NOT cross-language yet.
- **Best practices:**
  - Always provide clear function descriptions (what the LLM reads to decide invocation).
  - Group related functions into plugins/skills folders for organizational clarity.
  - Use simpler models for function routing to reduce costs.
  - Semantic functions use "completion" type; native functions use "function" type in plugin definitions.
- **Anti-patterns:**
  - Poor function descriptions → LLM misroutes or ignores functions.
  - Too many registered functions → LLM confused about which to use. "More actions can confuse an agent."
- **Relevant to Lyra §5.1 (tool system):** Function definition patterns, registration, and routing are directly applicable. The semantic/native function split mirrors Lyra's need for prompt-based and code-based tools.

---

## Chapter 6: Building Autonomous Assistants
- **Key insight:** Behavior trees (from robotics/game AI, Brooks 1986) can orchestrate multi-agent autonomous workflows. Agentic Behavior Trees (ABTs) use prompts to direct actions and conditions — stochastic by nature.
- **GPT Assistants Playground features relevant to Lyra:**
  - Custom actions via `@agent_action` decorator — drop files into `assistant_actions/` folder, auto-discovered.
  - Local code execution (cheaper than OpenAI Code Interpreter's $0.03/run).
  - **Comprehensive logging:** Captures all tool/action use, assistant-to-assistant delegation chains.
  - **Manager Assistant pattern:** One assistant with elevated privileges that can install/manage other assistants.
- **Agent safety warnings (directly quoted):** "Watching an agent emerge new behaviors using actions can be fun, but things can quickly go astray." Agents have been observed: downloading files, executing code when not intended, iterating tool-to-tool endlessly, deleting files they shouldn't.
- **Best practices:**
  - Keep assistants goal-specific with minimal actions.
  - Docker-isolate code execution for safety.
  - Log everything — tools used, actions taken, inter-agent communication.
  - Use Manager Assistant sparingly (has access to all actions).
- **Anti-patterns:**
  - Giving agents too many actions → unintended behavior, safety risks.
  - Running agent code outside isolation → file system damage risk.
  - Ignoring agent logs → black-box operation.
- **Relevant to Lyra §6.1 (safety), §4.3 (orchestration):** Behavior trees as orchestration pattern. Safety guardrails from real-world agent failures. Logging architecture requirements.

---

## Chapter 7: Assembling and Using an Agent Platform (Nexus)
- **Key insight:** Nexus is the book's reference agent platform — designed for teaching, not production. Architecture reveals core design decisions for agent platforms.
- **Nexus architecture (4-layer):**
  1. **Streamlit Interface:** Web UI, chat, thread management, agent/action/profile selection.
  2. **Chat System:** Coordinates database, agent manager, action manager, profile manager.
  3. **Managers (plugin discovery):** Agents, actions, profiles dynamically discovered at runtime via plugin-like system (YAML files for profiles, Python decorators for actions).
  4. **Database:** SQLite storing chat threads, user participants, conversation history.
- **Profile/Persona design:** YAML-based. Persona = system prompt defining role, background, demographics. Profile = persona + tool configuration.
- **Agent engine abstraction:** Supports OpenAI, Azure OpenAI, Gemini, Claude, Groq. Each engine configured separately. Pluggable engine architecture.
- **Best practices:**
  - Plugin-based discovery (not hardcoded agents/actions).
  - Multi-engine support from day one (avoid vendor lock-in).
  - Session-based state with database persistence.
  - Separate concerns: chat threads, agents, actions, profiles, memory, planning all independently configurable.
- **Anti-patterns:**
  - Hardcoding agent capabilities → inflexible.
  - Single-model dependency → fragile.
- **Relevant to Lyra §3.1 (platform architecture):** Direct architectural reference. Plugin discovery pattern, multi-engine abstraction, profile management all applicable to Lyra's harness layer.

---

## Chapter 8: Understanding Agent Memory and Knowledge
- **Key insight:** Knowledge and memory use the same RAG retrieval mechanism but differ in population: knowledge is preloaded documents; memory evolves from ongoing interactions.
- **RAG pipeline (two-phase):**
  - **Phase 1 — Indexing:** Load → Transform/Chunk → Embed → Store in Vector DB.
  - **Phase 2 — Querying:** Embed query → Vector similarity search → Augment prompt → LLM generates.
- **Document splitting (CRITICAL for quality):**
  - **RecursiveCharacterTextSplitter:** Simple character-based with overlap. Good starting point.
  - **Token-based splitting (tiktoken):** Better alignment with LLM token boundaries. Irregular chunk sizes due to whitespace. "Significantly better results" than character splitting.
  - **Semantic splitting (ideal):** Split by meaning, not arbitrary boundaries. Requires LLM assistance.
  - **Multiple concurrent splitting:** Same document split multiple ways for multi-view embeddings.
- **Memory taxonomy (from cognitive science):**
  - **Sensory memory:** Brief input buffer (images, audio, haptic). Not yet standard in agent systems.
  - **Short-term/working memory:** Active conversation buffer. In Nexus: thread-level context.
  - **Long-term memory:** Semantic (facts, concepts), Episodic (events), Procedural (skills/processes).
- **Memory implementation patterns:**
  - **Basic memory:** Conversation → Memory function (LLM extraction) → Embed → Store → Augment future prompts.
  - **Semantic memory:** Additional preprocessing — converts user input → relevant questions → query vector DB. Better relevance extraction than basic memory.
  - **Memory function prompt example:** "Summarize the conversation and create a set of statements... Return a JSON object with 'summary' key."
- **Memory/knowledge compression (NOVEL CONCEPT):**
  - **Process:** k-means clustering on embeddings → LLM compression function per cluster → summarized items stored.
  - **When to compress:** Large or unbalanced clusters, redundant/duplicate information.
  - **Multi-pass compression:** Apply 2+ times for hierarchical knowledge levels. Multiple compression passes improve retrieval performance.
  - **Knowledge compression benefit:** More beneficial for verbose/literary documents than code. Repetitive code also benefits.
  - **Blended stores:** Consolidated knowledge + memory stores for specialized systems.
  - **Multi-store pattern:** Agents with different memory stores for different users/tasks, with selective sharing.
- **Best practices:**
  - Use token-based splitting over character-based.
  - Prefer OpenAI embeddings (text-embedding-ada-002) for general semantic similarity.
  - Implement memory compression for long-running agents.
  - Separate knowledge stores (documents) from memory stores (interactions).
  - Support multiple memory types per agent.
- **Anti-patterns:**
  - Loading entire documents without chunking (costly, worse results).
  - Skipping chunk overlap (truncates semantic units).
  - Never compressing memory (clutter degrades retrieval).
  - Single memory store for all purposes.
- **Relevant to Lyra §4.2 (memory), §8.1 (knowledge):** Core patterns for Lyra's memory subsystem. Compression architecture is novel and directly applicable. Multi-store pattern for Lyra's multi-tenant design.

---

## Chapter 9: Mastering Agent Prompts with Prompt Flow
- **Key insight:** Prompt engineering must be systematic, not ad-hoc. Microsoft's Prompt Flow provides DAG-based prompt construction, testing, and evaluation with embedding-based similarity scoring.
- **Profile evaluation methodology:**
  - **Rubrics:** Define criteria for good outputs. Structured evaluation dimensions.
  - **Grounding:** Measure how well output is anchored to provided context vs. hallucinated.
  - **Profile comparison:** Run multiple profiles against the same inputs, evaluate quantitatively.
  - **Batch processing:** Profile evaluation at scale.
- **Jinja2 templating:** Dynamic prompt construction with variables, conditionals, loops. Reusable profile templates.
- **Deployment:** Prompt flows can be deployed as APIs for production use.
- **Best practices:**
  - Evaluate prompts with embedding similarity scores before deployment.
  - Compare multiple profile variants systematically.
  - Ground outputs against reference context to detect hallucination.
  - Batch-process evaluation for iterative improvement.
- **Anti-patterns:**
  - Ad-hoc prompt changes without evaluation.
  - Single profile without comparison baseline.
  - No grounding measurement → undetected hallucinations.
- **Relevant to Lyra §4.4 (persona management):** Systematic prompt evaluation is critical for Lyra's persona subsystem. The rubrics+grounding methodology is directly transferable. Prompt Flow as evaluation harness inspiration.

---

## Chapter 10: Agent Reasoning and Evaluation
- **Key insight:** Reasoning and evaluation are distinct but complementary. Reasoning = how the agent thinks. Evaluation = how we verify the thinking. All prompt engineering strategies exist on a thought×planning axis.
- **Reasoning techniques (increasing sophistication):**
  - **Direct solution prompting:** Q&A, zero-shot, one-shot, few-shot.
  - **Chain of Thought (CoT):** Explicit reasoning steps before conclusion. Reduces errors on complex problems.
  - **Zero-shot CoT:** "Let's think step by step" — no examples needed, works surprisingly well.
  - **Prompt chaining:** Break problem into sequential subproblems, each solved independently.
- **Evaluation techniques:**
  - **Self-consistency:** Generate multiple reasoning paths, majority vote on final answer. Improves accuracy on reasoning tasks.
  - **Tree of Thought (ToT):** Explore multiple reasoning branches, evaluate each, prune poor branches, continue promising ones. More compute-intensive but better for complex/search problems.
- **Few-shot behavioral modification:** "We're forcing the LLM to hallucinate here" — deliberately altering LLM behavior through examples. Foundation for persona engineering.
- **Best practices:**
  - Use CoT for all non-trivial reasoning tasks.
  - Self-consistency (multiple samples + voting) improves reliability at cost of more API calls.
  - Evaluate reasoning quality, not just final answers.
  - Zero-shot CoT is remarkably effective for many tasks.
- **Relevant to Lyra §4.5 (reasoning):** Core reasoning patterns. Self-consistency and ToT are directly applicable to Lyra's evaluation subsystem.

---

## Chapter 11: Agent Planning and Feedback
- **Key insight:** "Agents and assistants who can't plan and only follow simple interactions are nothing more than chatbots." Planning is the essential agent differentiator. External planners (prompt-based) vs. internal planners (model-level, like Strawberry/O1 and Claude).
- **Planning without feedback vs. with feedback:**
  - **Without:** Basic planning, sequential planning, automatic reasoning with tool use.
  - **With:** Environmental feedback, human feedback, LLM feedback, adaptive constructive feedback.
- **Sequential planner architecture (from Nexus BasicNexusPlanner):**
  1. Load agent's available actions as formatted string.
  2. Inject goal + available functions into planner prompt template (few-shot examples).
  3. Submit planning prompt to LLM (NO chat history — isolated to focus on goal).
  4. Parse JSON plan from LLM response.
  5. **Execute locally** (not through LLM) — iterate tasks, handle for-each loops, accumulate context.
  6. Send final context + results to LLM for summarization.
- **Critical planning insight:** "Plan execution can be completed by any process, not necessarily by the agent. Executing a plan outside the LLM reduces the tokens and tool use the agent needs to perform." Also means LLMs without tool-use support can still use planners.
- **Model capability matrix:**
  - **GPT-4o, most open models:** Parallel actions only. Sequential planning requires external planner.
  - **OpenAI Assistants, Claude:** Internal sequential planning. Can chain dependent actions natively.
  - **Strawberry/O1:** Internal reasoning, planning, evaluation, AND feedback within the model.
- **Feedback generation technique:** When agent gets wrong answer → provide correct answer → ask LLM "please review what you did wrong and suggest feedback you could give yourself." → Extract feedback for system instructions. Works consistently on O1, less reliable on weaker models.
- **Application matrix (tables 11.1-11.4):** Comprehensive guide for when/where/how to implement planning, reasoning, evaluation, and feedback across 6 application types (personal assistant, customer bot, autonomous agent, collaborative workflow, game AI, research). Key patterns:
  - Planning: Essential for autonomous agents and research. Not needed for restricted customer bots.
  - Reasoning: Creates latency overhead. Disable for real-time; enable for complex tasks. "Heavy-reasoning applications may not be appropriate" for real-time.
  - Evaluation: Typically external/offline. Autonomous agents need both external (human review) and internal (cross-agent). Multi-agent internal evaluation = CrewAI/AutoGen pattern.
  - Feedback: Mostly external. ChatGPT now incorporates memory for sustained feedback. "Avoid the common feedback looping problem" — isolate feedback at end.
- **Safety warning (verbatim):** "While writing this book and working with and building agents over many hours, I have encountered several instances of agents going rogue with actions, from downloading files to writing and executing code when not intended, continually iterating from tool to tool, and even deleting files they shouldn't have."
- **Best practices:**
  - Limit agent actions to minimum needed. "More actions can confuse an agent into deciding which to use."
  - Execute plans locally, not through the LLM (token savings + model independence).
  - Isolate planning prompts from chat history (context pollution).
  - Use LLM self-feedback extraction for prompt improvement.
  - Match planning/reasoning depth to application latency requirements.
  - Implement action guardrails — "LLMs aren't going to take over the world, but they make mistakes and quickly get off track."
- **Anti-patterns:**
  - Deploying agents without planning → chatbots.
  - Too many actions → confusion, unintended behavior, safety risks.
  - Continuous feedback loops during execution → feedback looping problem.
  - Assuming one-size-fits-all for planning/reasoning/evaluation/feedback — varies by application.
- **Relevant to Lyra §4.6 (planning/execution), §6.1 (safety), §7.1 (evaluation):** Core planning architecture. Local plan execution pattern is directly applicable. Feedback extraction technique for continuous improvement. Safety guardrails based on real-world agent failures.
