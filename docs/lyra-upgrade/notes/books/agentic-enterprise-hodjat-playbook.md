# The Agentic Enterprise — Best Practices Playbook
**Source:** Hodjat & Blondeau, *The Agentic Enterprise* (O'Reilly, 2026 Early Release)
**Extracted:** 11 practices from Introduction, Ch1, and Ch2

---

## Practice 1: Natural Language as Inter-Agent Protocol

- **What:** Use natural language (NL) as the communication protocol between agents, rather than rigid API contracts. Each agent's LLM maps intent expressed in NL to its specific tool calls. Structured data that must not be degraded by LLM processing is passed separately through code channels (`sly_data` pattern).
- **Why:** NL is robust to API changes (the LLM absorbs the mapping), self-documenting (human operators can read agent communication logs), and rich enough to express complex intent. It eliminates brittle point-to-point API rewiring when back-end services change.
- **Lyra route:** §4.1 (Multi-Agent Architecture) — This directly informs Lyra's inter-agent message format. Consider a dual-channel design: NL for intent/routing, structured payloads for data fidelity.
- **Source:** Introduction

---

## Practice 2: The LLM+Code Duality (Divide Agent Responsibilities)

- **What:** Every agent's behavior should be split between what the LLM handles (reasoning, unstructured I/O, intent mapping, generation) and what code handles (deterministic rules, consistency, structured data transformation, guard conditions). Never force the LLM to do what code can do deterministically. Never force code to handle what requires semantic understanding.
- **Why:** LLMs are inconsistent and non-deterministic; code is consistent and deterministic. Forcing LLMs to handle deterministic tasks wastes context tokens, increases latency, and introduces hallucination risk. Forcing code to handle semantic tasks creates brittle, rigid systems.
- **Lyra route:** §4.5 (Tool definitions) and §4.9 (Harness engineering) — Lyra's tool definitions and pre/post-processing hooks should embody this split. Deterministic validation, data transformation, and guard logic stay in code; intent interpretation and generation stay in the LLM.
- **Source:** Introduction (Figure I-10 and surrounding discussion)

---

## Practice 3: Safeguard Agents as External Monitors

- **What:** For every operational agent, deploy a separate "safeguard agent" whose sole responsibility is to monitor the operational agent's proposed behavior against ethics, compliance, and regulation guidelines. The safeguard agent intervenes when behavior is non-compliant. Never embed safety instructions as "be careful" system prompts in the operational agent.
- **Why:** LLMs lack meta-cognition — they do not know what they don't know. Asking an agent to self-police ("do X, but be careful") is ineffective because the same reasoning process that decided to act is asked to evaluate the action. An external safeguard agent provides independent oversight, similar to separation of duties in human organizations.
- **Lyra route:** §4.7 (Safety) — This is the single most actionable safety pattern from the book. Lyra should have an independent safety/safeguard layer, not safety instructions embedded in worker agent prompts.
- **Source:** Introduction

---

## Practice 4: The Planning-Actuation-Critic Triad

- **What:** Structure complex agent workflows as three specialized agents: a Planner (generates plan options), an Actuation agent (executes via real API/tool calls), and a Critic agent (validates outputs for plausibility and completeness, sends back for refinement if needed). This is the agentic equivalent of plan-execute-verify.
- **Why:** Separation of concerns prevents the agent that plans from being the same agent that validates its own plan. The Critic catches hallucinations, implausible outputs, and incomplete results before they reach the user or downstream systems.
- **Lyra route:** §4.1 (Multi-Agent Architecture) — This triad is a canonical architecture Lyra could adopt for complex multi-step tasks. It maps to supervisor (planner) → worker (actuator) → verifier (critic).
- **Source:** Introduction (Figure I-5)

---

## Practice 5: Agent Autonomy Is Non-Negotiable — But Bounded

- **What:** Every agent must have some autonomy (deciding which tools to use, in what order, and how). If an agent's behavior is 100% predetermined, it should be a software module, not an agent. However, autonomy must be bounded by: deterministic rule overrides for known failure modes, LLM uncertainty estimation with confidence thresholds for deferral, and human-in-the-loop for high-risk decisions.
- **Why:** The value of agents comes from their ability to handle unexpected situations and reason adaptively. Stripping all autonomy eliminates this value. The engineering challenge is defining the *boundary* of autonomy, not eliminating it.
- **Lyra route:** §4.8 (Planning/Strategy) and §4.7 (Safety) — Lyra's autonomy policy should define explicit autonomy levels per agent type and per operation risk level.
- **Source:** Introduction

---

## Practice 6: Context Budgeting via Specialization

- **What:** Rather than fighting context window limits with a single large-context agent, decompose responsibilities into specialized agents. Each agent gets a focused system prompt, shorter dialog history, targeted memory, and fewer tool descriptions. The result: each agent stays more faithful to its instructions because its context is smaller and more specific.
- **Why:** Even million-token context windows have a "faithfulness ceiling" — LLMs struggle to respect everything in a large context. Specialization reduces context per agent, improving reliability. It also enables using smaller/cheaper/faster LLMs for specialized agents, with larger models reserved for complex coordination.
- **Lyra route:** §4.2 (Memory) and §4.3 (Context) — This is the primary architectural argument for Lyra's multi-agent design over a monolithic agent. Document this rationale in Lyra's architecture.
- **Source:** Chapter 1

---

## Practice 7: Intent Logging as First-Class Observability

- **What:** Every agent logs its *intent* (in natural language) on every transaction or tool call, explaining *why* it acted and *what* it did. This is distinct from traditional software logging (terse, voluminous, context-free). Intent logs are human-readable, semantically rich, and auditable.
- **Why:** Traditional logs tell you *what* happened but not *why*. Agent intent logs provide decision rationale, making debugging, compliance auditing, and behavior analysis tractable. Intent logs are also the foundation for collecting fine-tuning data.
- **Lyra route:** §4.9 (Harness Engineering/Observability) — Lyra should implement structured intent logging as a core harness capability, not as an afterthought.
- **Source:** Introduction (list of agentification benefits)

---

## Practice 8: Per-Agent Fine-Tuning from Production Data

- **What:** Deploy a multi-agent system, collect usage data labeled by human auditors as acceptable/unacceptable per agent, then fine-tune each agent's LLM *separately* using its own labeled data. This is only practical in a multi-agent architecture — a monolithic do-everything agent cannot be fine-tuned for diverse, potentially conflicting behaviors.
- **Why:** Specialization makes fine-tuning tractable. Each agent's behavior space is narrow enough that collected data is coherent and labels are consistent. Fine-tuning improves reliability without needing larger models.
- **Lyra route:** §4.6 (Learning/Self-Improvement) — This is Lyra's continuous improvement pipeline: collect per-agent performance data, label, fine-tune, redeploy. This is a production-grade evolution strategy.
- **Source:** Chapter 1

---

## Practice 9: Agents as Long-Running Services, Not Chatbots

- **What:** Design agents as event-driven, stateful, always-on services — not as transactional request-response chatbots. Agents should wake on events (code merges, sensor readings, schedule triggers), proactively communicate with users or other agents, and maintain long-term mission state.
- **Why:** The chatbot paradigm (wake on text, respond, sleep) underuses agent capabilities. Real enterprise agents need to monitor environments, react to events, open PRs, handle reviewer feedback, and run continuous optimization loops.
- **Lyra route:** §4.9 (Harness Engineering) — Lyra's agent lifecycle should support daemon/worker patterns, not just request-response. This affects how agents are deployed, monitored, and recovered.
- **Source:** Chapter 1

---

## Practice 10: Incremental Multi-Agent Deployment with Sandbox Testing

- **What:** Build agent networks incrementally. Test each agent in isolation first, then test within a sandboxed multi-agent system, before plugging into the live agent network. New agent sub-networks should be pluggable without re-engineering existing agents (enabled by NL-based inter-agent communication).
- **Why:** Multi-agent systems are complex and emergent. Incremental deployment with sandbox gates prevents a faulty new agent from destabilizing the production agent network. The NL protocol means new agents can join without API contract changes in existing agents.
- **Lyra route:** §4.9 (Harness Engineering) and §4.7 (Safety) — Lyra's deployment pipeline should have explicit isolation → sandbox → production gates for new agents.
- **Source:** Chapter 1 (referencing AAOSA coordination mechanism)

---

## Practice 11: Six-Dimensional Organizational Readiness Assessment

- **What:** Before deploying agentic AI, assess organizational readiness across six dimensions using a simple Red/Amber/Green (RAG) maturity model: (1) Leadership alignment, (2) Technical infrastructure, (3) Governance and risk, (4) Architecture, (5) Technical resource availability, (6) Change management. Prioritize investments based on RAG status.
- **Why:** Agentic AI is not just a technology deployment — it requires organizational change. The PoC-to-production gap (observed in Franklin Templeton and Allianz cases) is primarily organizational, not technical. Readiness assessment prevents premature production deployment.
- **Lyra route:** §4.8 (Strategy) — This framework informs Lyra's own deployment readiness and can be offered as a Lyra capability (agentic readiness audit).
- **Source:** Chapter 2

---

## Bonus: Key Reference Papers Cited

| Paper | ArXiv ID | Relevance |
|-------|----------|-----------|
| Multi-agent scaling laws (1000+ agents) | 2406.07155 | Evidence for multi-agent scaling analogous to neural scaling laws |
| Decomposition critical for agentic efficiency | 2502.04358 | Position paper on task decomposition in multi-agent systems |
| Unknown unknowns in ML/RL creative actions | 2501.13075 | Co-authored by authors; limitations of current ML for creative tasks |
