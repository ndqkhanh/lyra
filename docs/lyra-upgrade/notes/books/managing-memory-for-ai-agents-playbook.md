# Managing Memory for AI Agents — Best Practices Playbook

## Practice 1: Implement Importance Scoring for Memory Retention
- **What:** Calculate memory importance based on four dimensions: recency, frequency of reference, user engagement metrics, and keyword relevance. Not all data deserves equal storage priority. Use these scores to drive promotion/demotion/summarization/dropping decisions.
- **Why:** Context windows are finite and quadratic attention makes them expensive. Without importance scoring, agents either forget critical information (FIFO loss) or waste context budget on irrelevant data. Importance scoring enables intelligent triage — the agent keeps what matters and discards what does not.
- **Lyra route:** §4.1 (MemoryManager), §4.2 (ImportanceScorer)
- **Source:** Chapter 1, "Managing Context Window Limitations"; Chapter 2, "Types of Long-Term Memory"; Conclusion

## Practice 2: Use Cascading Memory Systems (Agent-Driven Promotion)
- **What:** Let the agent itself decide what to promote from short-term to long-term storage and what to retrieve, rather than hardcoding retention rules. Memories should transition between episodic, semantic, and procedural tiers based on usage patterns — mirroring human memory consolidation (REM sleep compressing short-term to long-term).
- **Why:** Hardcoded retention rules cannot adapt to changing user priorities, project contexts, or domain shifts. Agent-driven cascading enables the system to dynamically reallocate memory resources based on actual usage. Unused long-term memories get summarized or dropped; frequently accessed short-term memories get promoted.
- **Lyra route:** §4.1 (Memory Architecture), §4.3 (Memory Transitions)
- **Source:** Chapter 1, "Cascading Memory Systems"; Chapter 2, "Types of Long-Term Memory"

## Practice 3: Adopt a Multimodel Strategy (Expensive for Planning, Cheap for Execution)
- **What:** Use a hierarchy of models: a highly capable but expensive model (e.g., Claude Opus 4) for complex cognitive tasks — high-level planning, complex reasoning, problem decomposition. Delegate individual straightforward subtasks to a fleet of smaller, faster, cost-effective models (e.g., Claude Sonnet 4, Gemini Flash 2.5, GPT-5 mini).
- **Why:** One-size-fits-all model selection is economically inefficient. System 2 (deliberate reasoning) costs significantly more than System 1 (fast execution). Early exit inference and speculative decoding can recover most of System 2 quality with 2-3x less latency/token usage. For enterprises running hundreds of agents, sparse models (MoE) or lightweight specialized agents scale far more cost-effectively than monolithic deployment.
- **Lyra route:** §3.1 (Model Router), §3.2 (Capability-Based Routing)
- **Source:** Chapter 3, "The Rise of the Multimodel Strategy"

## Practice 4: Build Evaluation Frameworks Beyond Public Benchmarks
- **What:** Develop domain-specific evaluation frameworks testing three dimensions: (1) task completion — did the agent achieve its goal in a timely, correct manner? (2) tool correctness and efficiency — correct tools with correct parameters, no redundant calls? (3) reasoning coherence and relevance — logical chain of thought that directly contributes to solving the problem? Use LLM-as-a-Judge with chain-of-thought prompting for scalable, repeatable evaluation.
- **Why:** Public benchmarks (MMLU, HumanEval, etc.) are useful signals but cannot guarantee performance on your proprietary use case. An agent that scores well on generic benchmarks may fail catastrophically on your domain-specific tasks. LLM-as-a-Judge with detailed rubrics and ground-truth data enables evaluation at scale without manual review of thousands of outputs.
- **Lyra route:** §6.1 (Eval Harness), §6.2 (LLM-as-a-Judge)
- **Source:** Chapter 3, "A Framework for Empirical Evaluation"; "The LLM-as-a-Judge Methodology"

## Practice 5: Abstract Vendor APIs Behind Internal Interfaces
- **What:** Build modular, composable architectures with abstractions around all external vendor APIs (model providers, memory backends, vector stores). The internal API remains consistent and agnostic to the external provider. Example: a GenAI chat-completion service that dynamically routes between GPT-5, Sonnet 4, and an internally hosted model — only the service needs updating on vendor switch, not application code.
- **Why:** Agent memory and model vendor lock-in is the most consequential architectural risk. Conversation histories, user metadata, and vector embeddings stored on external systems incur substantial egress fees and migration challenges. Abstracting behind internal interfaces preserves the option to switch vendors, adopt new models, or bring components in-house without rewriting application logic.
- **Lyra route:** §5.1 (Provider Interfaces), §5.2 (Plugin Abstraction Layer)
- **Source:** Chapter 4, "Architectural Strategies for Portability"; "The Nature of AI Lock-In"

## Practice 6: Use Named Entity Recognition (NER) for Structured Memory Retrieval
- **What:** Implement a three-phase NER pipeline: (1) extract entities (people, locations, organizations, dates) with confidence scores and cross-turn linking; (2) store entities as structured metadata alongside embeddings, enabling hybrid semantic+entity search; (3) enable entity-filtered queries ("What did John say about the budget?" filters for both person AND topic).
- **Why:** Pure semantic search is fuzzy and imprecise ("bank" as financial institution vs. riverside). NER dramatically shrinks the search space by adding structured precision to fuzzy retrieval. Production systems (Redis Agent Memory Server, Mem0g, LangChain) already include entity recognition modules. NER also enables knowledge graphs connecting entities over time, reducing confusion from ambiguous references and pronoun resolution failures.
- **Lyra route:** §4.2 (Context Extraction), §4.4 (Knowledge Graph)
- **Source:** Chapter 2, "Enhancing Memory Accuracy with Named-Entity Recognition"

## Practice 7: Design for the Feedback Loop — More Usage = Smarter System
- **What:** Architect organizational agent systems so that each interaction enriches the shared knowledge base. As more employees interact with agents, stored context becomes accessible to other team members, transforming tacit knowledge into shared resources. This creates a compounding advantage — the more people use the system, the smarter and more valuable it becomes.
- **Why:** A 2023 call center study (Brynjolfsson et al., NBER) demonstrated this quantitatively: novice workers improved productivity by 34% when AI assistants captured and disseminated top-performer expertise. Experienced workers saw minimal gains — the AI democratized expertise. Organizations that start early build exponentially more valuable knowledge systems. Each interaction is not just a transaction but a deposit into organizational memory.
- **Lyra route:** §4.4 (Collective/Shared Memory), §7.2 (Cross-Agent Synchronization)
- **Source:** Chapter 5, "From Individual to Collective Intelligence"; "Looking Forward: The Feedback Loop"

## Practice 8: Implement Cross-Agent Knowledge Synchronization
- **What:** Ensure discoveries, learned patterns, and problem-solving approaches captured by one agent benefit the entire agent fleet. Maintain version-controlled agent memory with rollback capability and historical analysis. Use hierarchical storage tiers (short-term, long-term, archival) with clear promotion/demotion rules.
- **Why:** Siloed agent knowledge wastes computational and human resources — every agent rediscovering what another already learned. Version-controlled memory enables rollback from corrupted or degraded memory states. Hierarchical storage ensures cost-efficient retrieval (hot data in fast stores, cold data in cheap archival).
- **Lyra route:** §7.2 (Cross-Agent Sync), §4.1 (Memory Tiers)
- **Source:** Chapter 5, "Memory-Preservation Strategies"

## Practice 9: Build Agent Memory Around Transactive Memory Systems (TMS)
- **What:** Design shared agent memory as a Transactive Memory System — a group-level knowledge sharing system for encoding, storing, and retrieving information from different knowledge areas. The goal is "knowing what other team members know" and assembling distributed knowledge into a coherent "group mind." AI agents serve as the binding layer that persists organizational knowledge beyond any individual's tenure.
- **Why:** TMS is directly associated with team effectiveness in organizational psychology research. When a senior engineer's problem-solving approach can be captured and made accessible to junior team members through AI agents, it is not just preserving information — it is democratizing expertise. This dampens the impact of retirements, promotions, and role changes that naturally erase critical institutional insights.
- **Lyra route:** §4.4 (Collective Memory), §7.0 (Multi-Agent Architecture)
- **Source:** Chapter 5, "From Individual to Collective Intelligence"

## Practice 10: Use Semantic Caching for Frequently Accessed Knowledge
- **What:** Cache queries against knowledge bases by processing the semantics of the content being passed. Frequently retrieved information gets prioritized in cache. Works exceptionally well for single-shot questions in internal LLM or RAG systems where many users query the same corpus.
- **Why:** Like search engines cache frequent queries ("What time are the playoffs today?"), agents should cache frequent knowledge-base lookups. This is both more computationally effective and more cost-effective than re-embedding and re-retrieving for every query. However, be aware of the limitation: semantic caching breaks down in multiturn conversations where context shifts dynamically.
- **Lyra route:** §4.2 (Retrieval Cache), §3.3 (Token Budget Management)
- **Source:** Chapter 1, "Managing Context Window Limitations"; Chapter 2, "Redis Semantic Caching"; Conclusion

## Practice 11: Prefer Directional Refactoring — Framework First, Custom Later
- **What:** Start agent projects with established frameworks (LangGraph, AutoGen, CrewAI) for proof-of-concept and exploration. Once scope solidifies and the agent becomes core to the business, graduate to a custom stack. The directional rule is: you can always refactor from framework to customization, but it is much harder to go the other way.
- **Why:** Frameworks provide lower barrier to entry, up-to-date documentation, and thousands of users who have validated patterns. They are ideal for learning, fast iteration, and stakeholder demos. But when agents become core to competitive advantage, frameworks turn into strategic liabilities by limiting differentiation and rapid iteration. The graduated approach captures early speed without sacrificing long-term control.
- **Lyra route:** §2.1 (Architecture Decisions), §2.2 (Build-vs-Buy Framework)
- **Source:** Chapter 4, "The Case for Frameworks"; "The Case for Build"

## Practice 12: Preserve Decision Context, Not Just Decisions
- **What:** When capturing organizational knowledge through AI agents, preserve the context around decisions: why certain choices were made, what alternatives were considered, and what constraints existed at the time. Use dynamic knowledge graphs following the Zettelkasten method — each new memory generates comprehensive notes with contextual descriptions, keywords, and tags, creating an interconnected web of related information.
- **Why:** Traditional documentation methods capture *what* was decided but not *why*. When circumstances change, understanding the original reasoning is essential to determining whether a decision should be revisited. Without context preservation, institutional knowledge degrades to a collection of seemingly arbitrary choices.
- **Lyra route:** §4.4 (Knowledge Graph), §7.3 (Decision Trace)
- **Source:** Chapter 5, "Capturing Institutional Knowledge"

## Practice 13: Containerize Agent Applications for Maximum Portability
- **What:** Encapsulate the entire agent application and its dependencies into a single portable container. Deploy on any cloud platform (AWS, Google Cloud, Azure) or on-premises. This decouples the agent application from its underlying host environment.
- **Why:** Containerization is one of the key architectural decisions for avoiding vendor lock-in and ensuring deployment flexibility. As agents become central to business operations, the ability to move between cloud providers or bring hosting in-house becomes strategically critical. Containerization also simplifies reproducible testing and CI/CD.
- **Lyra route:** §8.1 (Deployment), §2.3 (Infrastructure Abstraction)
- **Source:** Chapter 4, "Architectural Strategies for Portability"

## Practice 14: Implement Checkpointing with TTL-Based Cleanup
- **What:** Periodically save agent internal state (conversation threads, learned patterns, working memory) to persistent storage. Use time-to-live (TTL) features for automatic cleanup of old, irrelevant data. Redis is a popular choice for real-time checkpointing due to speed.
- **Why:** Checkpointing ensures agents do not lose their place across sessions or long conversations. Without it, every new session starts from scratch. TTL-based cleanup prevents unbounded storage growth from stale data. The key insight: checkpointing is not just about saving state — it is about making that state retrievable and actionable in the dynamic, nondeterministic world of agent interactions.
- **Lyra route:** §4.1 (Session Persistence), §4.3 (State Management)
- **Source:** Chapter 1, "Persistence via Checkpointing"; Chapter 5, "Memory-Preservation Strategies"

## Practice 15: Measure Task Completion, Tool Efficiency, and Reasoning Coherence Separately
- **What:** When evaluating agent performance, decompose success into three independently measurable dimensions rather than a single binary pass/fail: (1) task completion (did substantive work get completed in a timely, correct manner?), (2) tool correctness and efficiency (correct tools, correct parameters, no redundant calls?), (3) reasoning coherence and relevance (logical chain of thought that directly contributes to solving the problem?).
- **Why:** A single pass/fail metric obscures the root cause of agent failures. An agent might complete a task (dimension 1 passes) but burn excessive tokens on wrong tool calls (dimension 2 fails) or produce the right answer through incoherent reasoning that would fail on similar inputs (dimension 3 fails). Decomposed metrics enable targeted improvement — fix tool definitions (dimension 2) without touching reasoning prompts (dimension 3).
- **Lyra route:** §6.1 (Eval Harness), §6.3 (Metric Decomposition)
- **Source:** Chapter 3, "Creating Use-Case-Specific Test Criteria"
