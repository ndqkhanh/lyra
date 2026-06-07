# AI Agents in Practice — Best Practices Playbook

**Source:** Alto, Valentina. *AI Agents in Practice*. Packt Publishing, July 2025.
**Scope:** Design, implementation, and operational patterns for production AI agent systems.

---

## Practice 1: Adopt the Three-Tier Agent Hierarchy
- **What:** Structure agent systems in three layers: execution agents (low-level — API calls, DB queries, no decision-making), reasoning agents (mid-level — analyze data, determine actions, select tools), and orchestration/planning agents (high-level — break down tasks, distribute, adapt dynamically).
- **Why:** Prevents any single agent from being overwhelmed. Each agent focuses only on its abstraction level. Enables adaptive, generalizable intelligence without manual intervention. Mirrors proven patterns in software architecture, corporate structures, and AI systems like OpenAI's Operator.
- **Lyra route:** §4.2 (Agent Architecture), §4.7 (Multi-Agent)
- **Source:** Chapter 3, Chapter 7

---

## Practice 2: Treat Every Agent as a Potential Tool for Other Agents
- **What:** When designing agents, provide them with natural-language descriptions of their capabilities so they can be consumed as "tools" by higher-level agents. This creates composable, reusable agent units across the organization.
- **Why:** Enables hierarchical and network workflow patterns. An SQL agent becomes a tool for a project manager agent; a calendar agent becomes a tool for a scheduling agent. Mirrors microservice design: each agent encapsulates its logic and tools, communicates via structured messages.
- **Lyra route:** §4.2 (Component Anatomy), §4.7 (Multi-Agent Coordination)
- **Source:** Chapter 3 (p.54), Chapter 7 (p.165)

---

## Practice 3: Use Natural-Language Tool Descriptions, Not Just Function Signatures
- **What:** Every tool, agent component, or plugin must come with a human-readable natural-language description. The LLM reads these descriptions to reason about which tool to invoke, when, and with what parameters — without hardcoded routing logic.
- **Why:** This is what transforms a static function into an agentic capability. The LLM can adaptively select tools based on user intent, rephrase queries, and chain operations. Without descriptions, the agent cannot autonomously decide tool usage.
- **Lyra route:** §4.5 (Tool System)
- **Source:** Chapter 2 (p.32-33), Chapter 5

---

## Practice 4: Build a Three-Layer Memory Architecture (STM + Semantic Cache + LTM)
- **What:** Implement: (1) Short-term memory as a rolling context window for immediate coherence; (2) Semantic cache as a vector-based, session-scoped transient layer for meaning-based retrieval of recent interactions; (3) Long-term memory with semantic (facts), episodic (events), and procedural (know-how) subtypes, backed by persistent storage.
- **Why:** Each layer serves a different purpose. STM maintains conversation coherence. Semantic cache enables low-latency recall of recently discussed topics even when they've fallen out of the context window — without the cost of a full DB query. LTM enables personalization, learning, and continuity across sessions. Together they prevent the statelessness problem.
- **Lyra route:** §4.3 (Memory Architecture)
- **Source:** Chapter 4

---

## Practice 5: Choose Workflow Autonomy Level Based on Predictability Requirements
- **What:** Match the workflow pattern to how predictable the task execution path is. Sequential workflows for predictable pipelines (most control). Hierarchical workflows for complex tasks where execution order is unclear but oversight is needed. Network/group-chat workflows for highly adaptive, collaborative scenarios (most autonomy).
- **Why:** More autonomy = more flexibility but less predictability. A customer support agent with sentiment-based escalation needs conditional workflows. A research assistant team with dynamic collaboration needs network or group chat. Choosing wrong leads to either brittleness (insufficient autonomy) or unpredictability (excessive autonomy).
- **Lyra route:** §4.4 (Orchestrator), §4.7 (Multi-Agent Workflows)
- **Source:** Chapter 3 (p.49-53), Chapter 7 (p.169-174)

---

## Practice 6: Implement Hybrid Memory Retrieval (Metadata Filtering + Vector Search)
- **What:** Before performing expensive vector similarity operations, first filter the memory store using explicit structured metadata: user ID, topic tags, timestamps, or other scoped fields. Then apply semantic vector search within the filtered subset.
- **Why:** Increases precision (only relevant user's memories), improves relevance (context is properly scoped), and improves performance (narrower search space before vector operations). Essential for multi-user applications.
- **Lyra route:** §4.3 (Memory Retrieval)
- **Source:** Chapter 4 (p.81-82)

---

## Practice 7: Use Agentic RAG — Treat Vector Databases as Callable Tools, Not Fixed Pipeline Steps
- **What:** Instead of a fixed RAG pipeline (embed query → retrieve top-K → inject → generate), give the agent the vector database as a tool with a natural-language description. Let the agent decide: whether retrieval is needed, how to formulate the query, which source to target, whether to retry with different filters, and how to synthesize multi-source results.
- **Why:** Transforms retrieval from a passive backend operation into part of the agent's decision-making loop. Adds autonomy, adaptability, and contextual awareness. The agent can reformulate queries, filter by recency/credibility, and combine vector DB results with other tool outputs.
- **Lyra route:** §4.5 (Tool System), §4.3 (Knowledge Retrieval)
- **Source:** Chapter 5 (p.102-105)

---

## Practice 8: Manage Temporal Decay in Memory Systems
- **What:** Implement three strategies: (1) Time-aware retrieval — attach timestamps to memories, use recency scoring during retrieval; (2) Reinforcement mechanisms — boost scores for frequently accessed items, "pin" critical memories; (3) Memory pruning — periodically evaluate entries by age, access frequency, and relevance, archive or delete low-value items.
- **Why:** Without decay management, outdated information clutters memory, degrades retrieval quality, and increases latency. Just as humans forget unreinforced information, agents must manage information relevance over time.
- **Lyra route:** §4.3 (Memory Maintenance)
- **Source:** Chapter 4 (p.83-84)

---

## Practice 9: Design for Trajectory Transparency
- **What:** Log every intermediate action, tool invocation, reasoning step, and state transition. Make each agent's decision chain traceable so developers and users can reconstruct "how and why" a particular answer was generated — not just the final output.
- **Why:** LLMs can appear explainable without being transparent (post-hoc rationalization). Agent trajectories provide genuine transparency since they record actual decisions, function calls, and subgoals. Essential for debugging, audit, accountability, and user trust.
- **Lyra route:** §4.9 (Safety & Observability)
- **Source:** Chapter 9 (p.223)

---

## Practice 10: Implement a Layered Guardrail System
- **What:** Deploy four guardrail categories: (1) Preemptive design constraints (coded limits, refusal rules); (2) Real-time monitors (separate module evaluating each output, "LLM-as-judge" pattern); (3) Human fallback mechanisms (escalation triggers for complex/emotional/high-stakes situations); (4) Policy guardrails (ethical review sign-off, compliance checklists before production deployment).
- **Why:** No single guardrail type is sufficient. Preemptive constraints catch known cases; real-time monitors catch emergent behavior; human fallback handles edge cases; policy ensures governance. Together they form a defense-in-depth safety architecture.
- **Lyra route:** §4.9 (Safety Architecture)
- **Source:** Chapter 9 (p.235-237)

---

## Practice 11: Use Explicit Operational Bounds for Agent Autonomy
- **What:** Define explicit constraints on agent operations: "Cannot issue refunds above $Y without approval," "Will not exceed speed X," "Must escalate to human when sentiment is negative beyond threshold Z." These bounds are encoded in the system message and enforced by the orchestrator.
- **Why:** Autonomy without bounds leads to the control problem. Explicit constraints enable safe delegation while maintaining human oversight. They act as a "big red button" mechanism — the agent knows its limits before acting.
- **Lyra route:** §4.9 (Safety Constraints)
- **Source:** Chapter 9 (p.228-229)

---

## Practice 12: Separate Memory Hot Path from Background Processing
- **What:** Hot path memory: the agent consciously writes important facts during active reasoning (e.g., via a `manage_memory` tool, storing user preferences immediately). Background memory: async post-interaction processing that extracts summaries, themes, and metadata from full conversation histories.
- **Why:** Hot path enables real-time personalization (agent remembers and adapts mid-conversation). Background memory enables long-term learning (system improves between sessions without impacting response latency). Together they make agents both reactive and reflective.
- **Lyra route:** §4.3 (Memory Write Strategies)
- **Source:** Chapter 4 (p.85-86, LangMem description)

---

## Practice 13: Adopt MCP for Tool Interoperability, A2A-Inspired Patterns for Internal Agent Communication
- **What:** Use the Model Context Protocol (MCP) paradigm for standardized tool/resource/prompt interfaces. For internal multi-agent coordination, adopt A2A-inspired patterns: agent cards (capability descriptions), structured task requests with schemas, async processing with status updates, and multi-turn clarification support.
- **Why:** MCP avoids vendor lock-in for tool interfaces (tools become interchangeable across hosts). A2A-style patterns enable loosely coupled agent ecosystems where agents can be built by different teams, run on different platforms, yet collaborate through a shared protocol. Together they form the foundation for scalable, interoperable agent systems.
- **Lyra route:** §4.8 (Protocols & Interoperability)
- **Source:** Chapter 8

---

## Practice 14: Select the Orchestrator Based on Use Case, Not Hype
- **What:** Match orchestrator to task profile:
  - Modular prototyping with strong ecosystem → LangChain
  - Data retrieval-heavy apps → LlamaIndex (combined with LangChain)
  - Multi-agent research/collaboration → AutoGen
  - Data analytics/code-first workflows → TaskWeaver
  - Complex stateful multi-agent with dynamic routing → LangGraph
  - Enterprise Microsoft ecosystem → Semantic Kernel
  - Simple multi-agent with guardrails → OpenAI Agents SDK
- **Why:** No single "best" orchestrator exists. Each optimizes for different constraints: ease-of-use vs flexibility, single-agent vs multi-agent, code-driven vs conversational. Wrong choice leads to fighting the framework.
- **Lyra route:** §4.4 (Orchestrator Selection)
- **Source:** Chapter 3 (p.61-63), Chapter 7 (p.174-179)
