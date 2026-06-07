# Building LLM Agents with RAG, Knowledge Graphs & Reflection — Chapter Notes

**Author:** Mira S. Devlin | **Year:** 2025 | **Core Thesis:** Autonomous AI agents emerge from the fusion of four pillars — retrieval (RAG), structured knowledge (Knowledge Graphs), reflective reasoning (Cognitive Loops), and multi-agent collaboration. An LLM generates text; an agent generates outcomes. The architectural answer to hallucination, memory loss, and shallow reasoning is to connect language models to live data, structured relationships, self-evaluation loops, and specialized collaborating sub-agents.

---

## Chapter 1: The New Age of AI Agents

- **Key insight:** The book defines AI agents as systems with an LLM as reasoning core, coupled with memory, external data retrieval, and tool interfaces to autonomously achieve goals. The "Agentic Loop" (Perceive → Retrieve → Reason → Act → Reflect) separates agents from models. The "R³A" principle (Retrieval, Reasoning, Reflection, Action) forms the four cognitive pillars.
- **Best practices:**
  - Design agents as systems of cooperating components (planners, retrievers, critics, memory managers), not monoliths.
  - Build from minimal agentic loop: Decision → Retrieval → Composition. Do not reach for heavy frameworks prematurely.
  - Use a two-prompt pattern: Controller prompt (decide if external data needed) + Composer prompt (synthesize grounded answer).
  - Keep temperature low (0.2) for factual agent tasks, enforce strict JSON output for controller decisions.
  - Accept "I don't know" / "insufficient context" as valid outputs — never let the agent speculate.
  - Treat source attribution as first-class: every answer must cite or disclose sources.
- **Anti-patterns:**
  - Equating fluency with intelligence — LLMs predict text, agents achieve goals.
  - Building agents without a feedback loop — one-shot reasoning with no reflection.
  - Hardcoding API keys in source code; always use environment variables.
- **Relevant to Lyra §4.x:** This chapter establishes the foundational agent architecture pattern that Lyra's harness should embody. The R³A loop is the template for any Lyra workstream. The simple "decide → retrieve → compose" pattern is directly applicable to Lyra's Q&A, research, and action subsystems.

---

## Chapter 2: How LLMs Think: The Transformer and Beyond

- **Key insight:** LLMs are stateless, correlation-driven predictors with three critical limitations — no persistent memory (context window is sliding, not permanent), hallucination (optimize for probability not truth), and fragile causal reasoning (pattern recognition, not logic). These limitations are the EXACT reasons agentic architecture exists. Memory gaps are solved by vector stores + KGs; hallucinations are reduced by RAG; reasoning gaps are bridged by reflection loops + multi-agent collaboration.
- **Best practices:**
  - Understand the training ladder: Pretraining (broad knowledge) → Fine-tuning (domain specialization) → Instruction-tuning (alignment and safety via RLHF/DPO).
  - Use different model stages modularly: pretrained base for reasoning, fine-tuned retriever for precision, instruction-tuned orchestrator for user interaction.
  - Function calling is the bridge from language to action — detect intent, generate structured JSON calls, execute, return results to model for synthesis.
  - Embeddings encode semantic meaning geometrically; use cosine similarity as standard metric. Store both vectors AND metadata (source, date, type).
  - Context window defines working memory, embeddings define semantic memory — they are complementary hemispheres of AI cognition.
  - Model selection matters: ChatGPT (broad/general), Gemini (multimodal/large context), Claude (safety/reasoning depth). Mix models in agent chains for strengths.
  - Chain-of-Thought prompting improves reasoning accuracy 20-40%. Embed reasoning scaffolding in system prompts.
- **Anti-patterns:**
  - Treating LLMs as omniscient — they predict, they do not know.
  - Ignoring model "fingerprinting" differences — architecture, alignment, and modality support dictate agent design choices.
  - Neglecting embedding model consistency — switch models mid-pipeline breaks retrieval.
- **Relevant to Lyra §4.x:** This chapter provides the theoretical grounding for Lyra's memory system design (§4.2), context management (§4.3), and model routing decisions (§4.4). The "triad of limitations" is the exact problem statement Lyra's architecture solves.

---

## Chapter 3: RAG — The Backbone of Truthful Agents

- **Key insight:** RAG = Retriever + Ranker + Generator. This trinity converts prediction into precision. A compact LLM + good retriever can outperform massive standalone models. RAG is not a patch — it is a paradigm shift. The retriever finds; the ranker filters; the generator reasons. "Good retrieval is 80% of good generation." RAG reduces factual error rates by up to 70% in enterprise deployments.
- **Best practices:**
  - **Chunking:** 400-800 tokens per chunk, 10-20% overlap, semantic boundary awareness (avoid mid-sentence cuts). Prefer section/header-based chunking for structured docs.
  - **Embedding:** Use consistent model across entire corpus. Normalize to unit length. Batch to reduce latency. Re-embed when models improve.
  - **Retrieval:** Prioritize recall during retrieval stage, then improve precision with re-ranker (cross-encoder). Hybrid keyword + semantic search best for production.
  - **Prompt grounding:** Always use "Use ONLY the provided CONTEXT to answer" in system prompt. Temperature ≤ 0.3 for factual tasks. Require citations.
  - **Vector DB selection:** FAISS for control/research, Pinecone for production/scale, Chroma for prototyping/simplicity, Weaviate for hybrid graph+vector systems.
  - **Evaluation:** Measure Recall@k and Precision@k for retrieval, Faithfulness and Hallucination Rate for generation. Evaluate retrieval independently before connecting LLM.
  - **Debugging:** Inspect top-k chunks first. Log similarity scores (irrelevant chunks usually < 0.6 cosine). Visualize embeddings via PCA/t-SNE.
  - **Enterprise RAG:** 5 layers — Data Ingestion, Vectorization, Retrieval, Reasoning (LLM), Orchestration (routing, access control, caching, monitoring).
  - **Security:** Never embed secrets or PII. Use local embedding models if external API poses compliance risk. Row-level access control in vector DBs.
- **Anti-patterns:**
  - Feeding entire documents without chunking — overwhelms context window with noise.
  - Using keyword search alone for semantic tasks.
  - Skipping re-ranking — top-k by similarity is not top-k by usefulness.
  - Not having a fallback for "insufficient context" — the model will hallucinate to please.
  - Treating evaluation as one-time — RAG systems degrade silently without continuous monitoring.
- **Relevant to Lyra §4.x:** Directly applicable to Lyra's RAG subsystem (§4.3), verification pipeline (§4.16), and knowledge integration (§4.2). The evaluation metrics and debugging checklists are directly transferable.

---

## Chapter 4: Knowledge Graphs — Giving Structure to Chaos

- **Key insight:** RAG retrieves facts; knowledge graphs explain how they connect. KG + RAG = GraphRAG, enabling multi-hop reasoning, entity disambiguation, verification, and explainable inference. LLMs propose; structured systems verify and persist. The synergy: LLMs provide language understanding, KGs provide precision and context stability.
- **Best practices:**
  - **Entity design:** Stable, reusable nodes with unique IDs, types, and attributes. Think nouns of your domain.
  - **Relationship design:** Verbs of your graph — directional, typed, with optional properties (date, confidence, role). Each edge should enable a question you actually need to answer.
  - **Contextual paths:** Multi-hop reasoning chains that provide explainable traces from question to answer.
  - **Graph construction:** Define ontology first → LLM-assisted triple extraction → validate and normalize entities → store with provenance → generate contextual paths.
  - **LLM-KG interface:** Intent recognition → Query construction (Cypher/SPARQL) → Execute → Interpret results → Optionally update with human-in-the-loop validation.
  - **Safe updates workflow:** LLM extracts candidate triples → confidence scoring → human approval queue → graph update → logging/versioning. LLM suggests; never unilaterally rewrites.
  - **Cypher vs. SPARQL:** Cypher for property graphs (Neo4j, operational), SPARQL for RDF/semantic graphs (ontology-driven, linked open data).
  - **Neo4j vs. ArangoDB:** Neo4j when relationships are central (research, analytics, enterprise KGs). ArangoDB when mixing text, metadata, and relationships in one workflow.
  - **Design principles:** Think semantically not structurally. Keep relationships actionable. Use typed entities. Avoid over-connecting. Always store provenance.
- **Anti-patterns:**
  - Treating KG as a database — it is a map of meaning, not just storage.
  - Letting KGs decay — without dynamic updates they become irrelevant. LLMs extend lifespan through automated fact extraction.
  - Generating Cypher/SPARQL without validation — always log and verify queries.
  - Connecting everything — not every entity pair needs a link; focus on relevance.
- **Relevant to Lyra §4.x:** Directly applicable to Lyra's knowledge management (§4.2), structured reasoning (§4.4), and explainability (§4.17). The GraphRAG hybrid pattern is a candidate architecture for Lyra's context engine.

---

## Chapter 5: Cognitive Loops — The Mind of an Agent

- **Key insight:** The Plan → Act → Reflect → Revise cycle is what separates reactive chatbots from self-improving agents. Without this loop, an LLM is a calculator; with it, it becomes a learner. Reflection introduces metacognition — the ability to evaluate one's own reasoning. "Intelligence = Reflection × Memory × Time." Reflective agents pay a latency cost but gain long-term reliability.
- **Best practices:**
  - **Short-Term Memory (STM):** The context window — holds current subgoal, intermediate results, last-step success/failure. Volatile, fades when window fills.
  - **Long-Term Memory (LTM):** Persistent in vector DB or KG — stores reflections, summaries, outcomes from past loops. Enables cross-session learning.
  - **Memory integration with cognitive loop:** Plan consults LTM → Act updates STM → Reflect stores learned lessons in LTM → Revise uses LTM to adjust strategy.
  - **Forgetting strategies:** Time decay, relevance pruning, compression (summarize related experiences into meta-insights). Retain wisdom not clutter.
  - **Self-evaluation prompts:** Structured meta-prompts after each major action: "What was intended? Was it achieved? If not, why? What changes next time?"
  - **Action models:** Define tool selection policy, execution logic, observation collection, failure handling. Log everything for traceability.
  - **Reflective vs. Reactive:** Reactive agents = fast, stateless, predictable but fragile. Reflective agents = slower, stateful, self-correcting, suitable for reliability-critical domains (medicine, law, finance). Reflection is non-optional for accountability.
  - **Quantitative metrics for self-evaluation:** Accuracy, completeness, hallucination rate, response time. Log and track trajectory over time.
- **Anti-patterns:**
  - Reflection without memory — forgetting what was learned defeats the purpose.
  - Infinite reflection loops — always bound with max_revisions (start with 1-2).
  - Self-evaluation without structured criteria — leads to vague or self-justifying critiques.
  - Treating STM as sufficient for long tasks — it is not; LTM is essential.
- **Relevant to Lyra §4.x:** This is the core of Lyra's self-improvement and reliability workstreams (§4.5, §4.16). The Plan-Act-Reflect-Revise cycle is the operating model for Lyra's own cognitive architecture. Memory hierarchy design is critical for §4.2.

---

## Chapter 6: Multi-Agent Systems — Collaboration & Coordination

- **Key insight:** Three pillars of multi-agent success — defined roles, effective communication, delegation protocols. The Planner-Executor-Evaluator (PEE) triad is the most stable design. Frameworks like MetaGPT and ReflectionChain reduce hallucinations by 30-40% through peer review. Multi-agent systems multiply not just capability but perspective. "No single model contains the whole truth, but in dialogue, they approach it."
- **Best practices:**
  - **Role archetypes:** Planner (strategy, decomposition), Executor (action, tools), Critic/Evaluator (quality, verification), Researcher (retrieval, synthesis), Mediator (conflict resolution).
  - **Coordination models:** Hierarchical (manager → workers, good for sequential tasks), Peer-to-Peer (negotiation/voting, good for debate/research), Hybrid (clusters of specialists coordinated by managers — dominant in CrewAI, MetaGPT).
  - **Communication:** Structured message passing with sender, receiver, intent, content. Log all turns for audit trail.
  - **Delegation cycle:** Intention → Assignment → Execution → Reporting → Evaluation. Recursive — agents can delegate sub-tasks forming nested coordination trees.
  - **Shared memory:** Central context store (vector DB + KG + message log) for state persistence, coordinated reflection, context reuse across agents.
  - **Conflict resolution strategies:** Majority voting (simple), evidence-based arbitration (structured), mediator escalation (complex), consensus with revision (iterative). Document all resolutions in shared memory.
  - **Cooperative memory:** Shared structured repository where agents store collective experience — prevents re-learning the same lessons, enables cumulative intelligence.
  - **Framework selection:** CrewAI for role-driven sequential workflows (easiest). LangGraph for complex stateful dynamic collaboration (most flexible). AutoGPT for self-directed exploratory tasks (most autonomous). Combine for hybrid: CrewAI roles + LangGraph orchestration + AutoGPT-like autonomy for sub-agents.
  - **PEE loop:** Planner interprets → Executor acts → Evaluator reviews → Planner revises → repeat until criteria met. Each agent focused on single cognitive function.
  - **Emergent properties:** Parallelization, error correction through peer review, diverse perspective synthesis, emergent creativity from agent interaction.
- **Anti-patterns:**
  - Undefined roles causing duplicated work or dropped tasks.
  - Communication without protocols — agents get stuck in feedback loops or misinterpret goals.
  - Single-agent overreach — one agent trying to do everything (plan, execute, evaluate) without checks.
  - Memory silos — agents operate on stale or inconsistent state.
  - "Runaway loops" in autonomous frameworks — need supervision gates, max iteration bounds, human-in-the-loop for critical tasks.
- **Relevant to Lyra §4.x:** This chapter is directly applicable to Lyra's multi-agent orchestration (§4.6), task decomposition/routing (§4.5), verification pipeline (§4.16), and team-based execution (§4.7). The PEE triad should inform Lyra's internal agent topology.

---

## Summary Statistics

- **Total chapters:** 6 (plus Introduction/Preface)
- **Part I:** 3 chapters (cognitive foundations)
- **Part II:** 3 chapters (engineering intelligence)
- **"Agent in Action" sections:** 6 (one per chapter), implementing progressively complex systems
- **Core frameworks referenced:** LangChain, CrewAI, LangGraph, AutoGPT, MetaGPT, FAISS, Pinecone, Chroma, Weaviate, Neo4j, ArangoDB
- **Key models referenced:** GPT-4/GPT-4o-mini, Claude 3, Gemini 1.5
- **Measured improvements cited:** RAG factual accuracy +70%, hallucination reduction 30-40% with multi-agent peer review, research time reduction 45% with KG-powered discovery, case review time reduction 60% with KG+LLM AML systems
