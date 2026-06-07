# Building LLM Agents with RAG, Knowledge Graphs & Reflection — Best Practices Playbook

## Practice 1: The R³A Agentic Loop (Retrieve → Reason → Reflect → Act)

- **What:** Every agent should implement a continuous cycle: Perceive input → Retrieve external knowledge → Reason about context → Act via tools → Reflect on outcome → Revise and iterate. This is the heartbeat of autonomous intelligence.
- **Why:** Without a loop, an LLM generates text and stops. With a loop, it pursues goals, learns from failure, and improves over time. The loop separates a model from an agent.
- **Lyra route:** §4.5 (Self-improvement loops), §4.16 (Reliability)
- **Source:** Chapter 1 (Section 2, 5), Chapter 5 (Section 1)

## Practice 2: Minimal Agentic Pattern — Decide, Retrieve, Compose

- **What:** The smallest reliable agent consists of three steps: (1) Controller prompt decides if external data is needed, (2) Retrieval fetches relevant context, (3) Composer prompt synthesizes a grounded answer with citations. Start here before adding complexity.
- **Why:** Demonstrates all four cognitive pillars in under 200 lines. Framework-free pattern that scales to enterprise architectures. Reduces hallucination by grounding every answer in retrieved evidence.
- **Lyra route:** §4.3 (Context/RAG), §4.4 (Routing)
- **Source:** Chapter 1 (Section 6), Chapter 3 (Section 1, 6)

## Practice 3: Strict Grounding Prompts (Context-Bound Generation)

- **What:** System prompts must explicitly constrain the LLM: "Use ONLY the provided CONTEXT to answer. If not in context, say 'Not enough information.'" Enforce citations, keep temperature ≤ 0.3, and require structured output (JSON with answer + sources).
- **Why:** Single most effective anti-hallucination technique. When combined with retrieval, reduces fabricated claims to near-zero in well-engineered systems. Creates auditability through citation trails.
- **Lyra route:** §4.3 (RAG pipeline), §4.17 (Safety)
- **Source:** Chapter 3 (Sections 2, 5, 6), Chapter 5 (Section 6)

## Practice 4: Chunking + Embedding Hygiene

- **What:** Document chunking at 400-800 tokens with 10-20% overlap, preserving sentence boundaries. Use consistent embedding model across entire corpus. Normalize vectors to unit length. Store source/metadata alongside each vector. Re-embed corpus when embedding models improve.
- **Why:** "Good retrieval is 80% of good generation." Poor chunking breaks semantic continuity (too small) or introduces noise (too large). Embedding model inconsistency silently degrades retrieval quality and produces irrelevant results.
- **Lyra route:** §4.2 (Memory), §4.3 (Context/RAG)
- **Source:** Chapter 3 (Sections 3, 4)

## Practice 5: Two-Stage Retrieval — Recall First, Precision Second

- **What:** First stage: fast semantic retrieval (top-k=20) prioritizing recall to capture all relevant candidates. Second stage: cross-encoder re-ranking on top results (keep top 3-5) to maximize precision. Combine keyword + vector search for hybrid retrieval.
- **Why:** Similarity does not equal usefulness. Pure vector similarity returns thematically related but contextually irrelevant passages. Two-stage pipeline ensures the LLM receives only high-signal context, preventing context window pollution.
- **Lyra route:** §4.3 (RAG pipeline), §4.4 (Routing)
- **Source:** Chapter 3 (Section 2, 6)

## Practice 6: RAG Evaluation as Continuous Process

- **What:** Measure Recall@k and Precision@k for retrieval quality independently. Measure Faithfulness (claims grounded in context), Hallucination Rate, and Answer Groundedness for generation. Track metrics continuously in production with periodic human sampling, automated dashboards, and alerts for metric drops.
- **Why:** RAG systems degrade silently — retrieval drift, data staleness, embedding model changes all erode quality over time. Evaluation is not a one-time gate; it is an ongoing discipline. Without it, subtle factual errors accumulate undetected.
- **Lyra route:** §4.16 (Reliability), verification subsystem
- **Source:** Chapter 3 (Section 5)

## Practice 7: Knowledge Graphs for Multi-Hop Reasoning and Explainability

- **What:** Combine vector-based RAG with a knowledge graph (GraphRAG pattern). RAG finds relevant passages; the KG traces how entities connect. LLMs generate Cypher/SPARQL queries to traverse explicit relationships, then synthesize structured + unstructured results into grounded answers.
- **Why:** Pure RAG cannot answer multi-hop questions like "Which researchers at Stanford collaborate with DeepMind on reinforcement learning?" — that requires traversing chained relationships. KGs provide explainable reasoning traces: every answer can be mapped back through explicit edges.
- **Lyra route:** §4.2 (Knowledge management), §4.17 (Explainability)
- **Source:** Chapter 4 (Sections 1, 3, 4, 6)

## Practice 8: Plan-Act-Reflect-Revise as Universal Agent Operating Model

- **What:** Every agent action follows a four-phase cycle: Plan (decompose goal into subtasks) → Act (execute via tools/APIs) → Reflect (structured self-evaluation: what worked, what failed, what is missing) → Revise (adjust plan based on reflection, retry if needed). Bound with max_revisions.
- **Why:** Transforms single-pass generation into iterative improvement. The Reflect phase introduces metacognition — the agent evaluates its own output before presenting it. Revision closes the loop, ensuring continuous quality improvement without human intervention.
- **Lyra route:** §4.5 (Self-improvement), §4.16 (Reliability)
- **Source:** Chapter 5 (Sections 1, 4, 6)

## Practice 9: Dual Memory Architecture — Short-Term + Long-Term

- **What:** Short-Term Memory (STM) = context window, holds immediate reasoning state. Long-Term Memory (LTM) = vector DB + KG, persists reflections, summaries, and lessons across sessions. Every cognitive loop phase interacts with both: Plan consults LTM, Act updates STM, Reflect stores learnings in LTM, Revise uses LTM to adjust.
- **Why:** Without LTM, every session is a reboot — the agent forgets everything it learned. Without STM hygiene, the context window fills with noise. The combination enables experience accumulation: past mistakes inform future strategies.
- **Lyra route:** §4.2 (Memory architecture), §4.3 (Context management)
- **Source:** Chapter 5 (Sections 2, 3, 4)

## Practice 10: Structured Self-Evaluation with Strict Critic Prompts

- **What:** Use a separate critic prompt/system that evaluates agent output against the original question and retrieved context. Require structured JSON output: issues (list), required_fixes (concrete edits), verdict (approve/revise). Be strict: mark any unsupported claim. Apply fixes through a reviser prompt that preserves correct content.
- **Why:** Self-evaluation without structure produces vague self-justification. Structured criteria force the critic to be specific. Separate critic/reviser roles prevent the agent from "approving" its own work without genuine scrutiny.
- **Lyra route:** §4.16 (Verification), §4.17 (Safety)
- **Source:** Chapter 5 (Section 6)

## Practice 11: Planner-Executor-Evaluator (PEE) Triad for Multi-Agent Design

- **What:** The most stable multi-agent topology: Planner (decompose goals into actionable tasks), Executor (perform assigned subtasks with tools), Evaluator (verify accuracy, coherence, alignment with intent). Closed feedback loop: Planner → Executor → Evaluator → Planner revises → repeat until approved.
- **Why:** Prevents hallucination cascades (bad outputs feeding worse ones). Each agent focuses on a single cognitive function (strategy / action / critique). Supports iterative improvement and real-time self-correction. Mirrors proven human organizational structures.
- **Lyra route:** §4.6 (Multi-agent orchestration), §4.7 (Task delegation)
- **Source:** Chapter 6 (Sections 1, 4, 6)

## Practice 12: Cooperative Memory for Multi-Agent Learning

- **What:** All agents in a multi-agent system share a central memory store (vector DB + KG + message log). Agents consult shared history before taking action, store reflections and resolutions, and access other agents' learnings. Memory synchronization with versioning prevents stale-state conflicts.
- **Why:** Without shared memory, agents duplicate work, repeat mistakes, and operate on inconsistent state. Cooperative memory transforms isolated agent actions into cumulative group intelligence — the system does not re-learn the same lessons.
- **Lyra route:** §4.2 (Memory), §4.6 (Multi-agent coordination)
- **Source:** Chapter 6 (Sections 5, 6)

## Practice 13: Conflict Resolution as a Feature, Not a Bug

- **What:** When agents disagree, use structured resolution: Mediator agent detects conflict → requests justifications → applies strategy (majority vote, evidence arbitration, mediator decision, consensus with revision) → stores resolution rationale in shared memory for future reference.
- **Why:** Disagreement is a sign of cognitive diversity, not system failure. Resolved conflicts sharpen collective reasoning. Storing resolutions creates a "self-growing constitution" — future agents reference past decisions to prevent recurrence.
- **Lyra route:** §4.6 (Coordination), §4.16 (Consistency)
- **Source:** Chapter 6 (Section 5)

## Practice 14: Memory with Intelligent Forgetting

- **What:** Not all memories should persist forever. Implement: time decay (gradually lower importance of old memories), relevance pruning (remove memories misaligned with current domain), compression (summarize related experiences into higher-level meta-insights).
- **Why:** Unbounded memory leads to context overload, retrieval drift, and noise accumulation. Compression mirrors human cognition — retain wisdom, not clutter. Example: 100 JSON-error logs → one meta-reflection: "When parsing JSON from APIs, ensure proper encoding and retry on failure."
- **Lyra route:** §4.2 (Memory management)
- **Source:** Chapter 5 (Section 2)

## Practice 15: Human-in-the-Loop for Knowledge Graph Updates

- **What:** LLMs extract candidate triples from unstructured text and propose KG updates with confidence scores. All proposed updates queue for human approval before ingestion. Log every modification for traceability. This applies especially to enterprise/regulated domains where factual errors are costly.
- **Why:** LLMs can hallucinate relationships just as they hallucinate text. Unilateral KG updates corrupt structured knowledge, amplifying errors downstream. The principle: "LLMs propose; structured systems verify and persist."
- **Lyra route:** §4.2 (Knowledge management), §4.17 (Safety)
- **Source:** Chapter 4 (Section 2)

---

## Quick Reference: Which Practice for Which Lyra Workstream

| Workstream | Primary Practices |
|---|---|
| §4.2 Memory | 4, 9, 12, 14, 15 |
| §4.3 Context/RAG | 2, 3, 4, 5, 6 |
| §4.4 Routing | 2, 5 |
| §4.5 Self-improvement | 1, 8, 10 |
| §4.6 Multi-agent orchestration | 11, 12, 13 |
| §4.7 Task delegation | 11 |
| §4.16 Reliability/Verification | 6, 8, 10, 13 |
| §4.17 Safety/Explainability | 3, 7, 10, 15 |
