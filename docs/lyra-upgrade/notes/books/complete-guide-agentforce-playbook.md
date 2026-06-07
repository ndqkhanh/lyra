# A Complete Guide to Agentforce — Best Practices Playbook

## Practice 1: Design for Non-Determinism (Embrace Adaptability, Manage Variability)
- **What:** Architect agent workflows as non-deterministic by default — agents produce variable outputs from similar inputs because they reason, not just execute rules. Accept this variability while bounding it with guardrails, topic scopes, and deterministic action blocks.
- **Why:** The core value of agents over rule-based automation is adaptability to unstructured data and changing circumstances. Trying to force deterministic behavior through overly rigid instructions eliminates this advantage. The winning pattern is "semi-deterministic" — agents are free to reason within defined boundaries.
- **Lyra route:** §4.2 (Workflow Design), §4.4 (Guardrails)
- **Source:** Chapter 1 (§Precursors, Table 1-1), Chapter 3 (§Agent Governance)

## Practice 2: Split Monolithic Agents into Specialized Multi-Agent Systems
- **What:** Instead of one generalist agent with many topics, build multiple focused agents (ideally 1-5 topics each) and orchestrate them via a supervisor/dispatcher model. Use Flow to chain agents for multi-step processes.
- **Why:** Each additional topic/action exponentially increases the risk of misclassification, hallucination, and intent-outcome misalignment. Specialized agents are more reliable, easier to test, and simpler to maintain. Multi-agent systems also scale better and are more resilient to individual agent failure.
- **Lyra route:** §4.1 (Multi-Agent Architecture)
- **Source:** Chapter 1 (§Rise of Multi-Agent Systems), Chapter 5 (§Simplify Topics and Actions, §Agent Chaining via Flow)

## Practice 3: Frame Guardrails Positively (Not Negatively)
- **What:** Write guardrails in the affirmative — "Only disclose product features and availability to partners" instead of "Do not disclose pricing details to partners." Structure instructions to describe acceptable behavior, not prohibited behavior.
- **Why:** LLMs sometimes struggle with multiple negative statements, misinterpreting them as positives and producing the exact behavior you tried to prevent. Positive framing reduces ambiguity and increases predictability.
- **Lyra route:** §4.4 (Safety Guardrails)
- **Source:** Chapter 2 (§Setting Guardrails)

## Practice 4: Implement Memory as a Three-Component System (State, Flow, Side Effects)
- **What:** Design agent memory architecture with three interacting components: State (session context — user data, committed tasks, conversation history), Flow (action sequence that reads and updates state), and Side Effects (persistent outputs that form long-term memory — CRM updates, sent emails, created records).
- **Why:** This three-component model ensures agents maintain coherent conversations (State), execute multi-step workflows reliably (Flow), and retain cross-session continuity (Side Effects). Without this architecture, agents revert to stateless chatbots.
- **Lyra route:** §4.3 (Memory Management)
- **Source:** Chapter 3 (§Short-Term and Long-Term Memory)

## Practice 5: Adopt a Two-Phase RAG Architecture (Offline Prep + Online Retrieval)
- **What:** Phase 1 (offline): Ingest data, segment into chunks using the right chunking strategy (semantic/window/section/conversation/prepend), embed vectors, index for search. Phase 2 (online): Vectorize user query at runtime, match against index, augment the prompt, generate the response.
- **Why:** The quality of RAG depends entirely on the offline preparation phase. Poor chunking produces nonsensical retrieval results even with perfect queries. Choose chunking strategy based on document structure; test with diverse documents and use cases. Prefer data graphs over complex merge fields to speed up retrieval.
- **Lyra route:** §4.3 (RAG Architecture)
- **Source:** Chapter 3 (§Data Retrieval and RAG, Tables 3-2, Figures 3-6/3-9)

## Practice 6: Use Headless Agents for Adaptive Reasoning in Automation Pipelines
- **What:** Embed agents as reasoning nodes inside Flow/Apex automations rather than always deploying them as chat interfaces. Headless agents add "agentic flavor" to rigid processes — validation, verification, qualification, enrichment, routing.
- **Why:** Headless agents are arguably more transformative than customer-facing chat agents. They can replace hard-coded decision elements with contextual reasoning, making automations adaptable to changing inputs and edge cases. They also avoid the UX overhead and security risks of exposed chat interfaces.
- **Lyra route:** §4.5 (Tool/Plugin Architecture), §4.1 (Orchestration)
- **Source:** Chapter 3 (§Agent Orchestration), Chapter 5 (§Agentic Decisioning, §Timed Agent Invocation)

## Practice 7: Practice AgentOps as Distinct from DevOps
- **What:** Treat agent life cycle management as a separate discipline. Key differences from DevOps: manage unpredictability instead of eliminating it, measure success against user intent alignment instead of failure rates, use A/B testing in production, maintain incident playbooks for agent-specific failure modes.
- **Why:** Applying rigid DevOps CI/CD to agents causes silent production failures. Agents are non-deterministic, adaptive entities — their behavior can change without configuration changes (due to data shifts, LLM updates, or reasoning drift). AgentOps accounts for these differences with real-time monitoring, semantic versioning, controlled rollback procedures, and agent sunset policies.
- **Lyra route:** §4.7 (Harness Engineering, Observability, CI/CD)
- **Source:** Chapter 3 (§AgentOps and Life Cycle Management, Table 3-13)

## Practice 8: Design Fallback and Failsafe Systems at Every Level
- **What:** Build fallback logic for all four failure levels: Topic (escalation topic + fallback topics like "General FAQ"), Action (Flow fault paths, Apex try-catch, prompt template fallback values), Data (merge field fallbacks, data quality checks), System (agent versioning, web form fallback when agent unavailable).
- **Why:** Agent failures are inevitable due to non-determinism, data issues, and underlying technical problems. Production-ready agents must degrade gracefully on every level. However, avoid excessive fallback logic — it slows responses, adds complexity, and can trigger when it shouldn't.
- **Lyra route:** §4.7 (Reliability, Failure Handling)
- **Source:** Chapter 5 (§Use Fallbacks and Failsafes, Table 5-3, Figure 5-5)

## Practice 9: Use Unit Economics for Agent ROI (Not Aggregate TCO)
- **What:** Evaluate agent business cases at the unit level — cost per outcome (e.g., cost per resolved case) vs. baseline. Model as: (Actions per resolution × resolution rate × conversation volume × per-action fee) against current cost of achieving the same outcome. Ensure marginal benefit exceeds unit cost.
- **Why:** Usage-based pricing makes aggregate TCO prediction impossible and misleading. Unit economics scale with volume — if each unit is profitable, the agent generates profit as operations grow. This shifts thinking from "how much will Agentforce cost?" to "which use cases are individually profitable?"
- **Lyra route:** §4.8 (Adoption Strategy)
- **Source:** Chapter 2 (§Usage-Based Pricing), Chapter 4 (§Build an Impactful Business Case)

## Practice 10: Apply the Five Responsible AI Principles as Design Constraints
- **What:** Design every agent solution against five principles: Accuracy (inference-time data grounding + iterative LLM response validation), Safety (adversarial red-teaming + toxicity/bias guardrails), Transparency (conversational explainability + clear AI disclosure), Empowerment (low-code tools + user training), Sustainability (efficient hardware + renewable energy).
- **Why:** Responsibility cannot be added after deployment — it must be embedded into architecture from the start. Autonomous agents carry significant risks (data leaks, biased decisions, reputational damage) that only compound as they scale. These five principles provide a concrete checklist for design reviews.
- **Lyra route:** §4.4 (Safety, Trust, Ethics)
- **Source:** Chapter 3 (§Trust and Ethics, Figure 3-14)

## Practice 11: Choose Retrieval Strategy Based on Use Case Complexity (Not Maximalism)
- **What:** Match retriever complexity to use case needs: individual retrievers for simple, single-dataset lookups; ensemble retrievers only when data is scattered across multiple sources; vector search for semantic understanding; hybrid search (vector + keyword) when both exact matches and meaning matter.
- **Why:** Each Data 360 query has a credit cost. Ensemble retrievers run multiple queries, combine, and re-rank — they're slower and more expensive. Individual retrievers are faster and cheaper. The principle is: don't use a sledgehammer when a scalpel works.
- **Lyra route:** §4.3 (Data Retrieval)
- **Source:** Chapter 3 (§Data Retrieval and RAG, Figures 3-7/3-8)

## Practice 12: Treat Instructions as Non-Sequential — Enforce Order with Variables and Filters
- **What:** Atlas Reasoning Engine processes instructions holistically, not in the order they are written. To enforce sequential execution, use variables and filters instead of relying on instruction ordering or numbered steps.
- **Why:** This is one of the most common sources of inconsistent agent behavior — developers assume numbered instructions execute in order, but the reasoning engine processes them as a whole to create its own execution plan. Variables and filters provide deterministic control over execution flow.
- **Lyra route:** §4.5 (Instruction/Prompt Engineering)
- **Source:** Chapter 2 (§Writing Instructions)

## Practice 13: Ingest Data Rather Than Integrate via Live APIs
- **What:** Pre-ingest external data into Data 360 instead of making live API calls from agent actions. Use MCP servers as the preferred alternative when direct API access is unavoidable.
- **Why:** Live API dependencies introduce latency, failure points, and maintenance overhead. Agents that rely heavily on real-time API calls are prone to timeouts and inconsistent behavior. Pre-ingested data is faster, more reliable, and allows Data 360's semantic layer to enrich it. If you must go external, MCP servers provide standardized, secure access patterns.
- **Lyra route:** §4.5 (Tool Architecture)
- **Source:** Chapter 5 (§Ingest Rather Than Integrate)

## Practice 14: Establish a Portfolio Approach to Use Case Development
- **What:** Maintain a continuously evolving pipeline of agent use cases rather than betting on a single perfect deployment. Use structured ideation (Value Proposition Canvas, Service Blueprints), a scoring table, and quarterly roadmap reviews. Velocity of learning matters more than perfection of any single use case.
- **Why:** The agentic AI landscape evolves rapidly. Organizations that over-polish their first use case lose momentum and miss learning opportunities. A portfolio approach reduces dependency on individual agents and creates a steady pipeline of value. It also makes it easier to retire underperforming agents without jeopardizing the entire initiative.
- **Lyra route:** §4.8 (Adoption Strategy)
- **Source:** Chapter 5 (§Scope the Right Use Cases), Chapter 4 (§Evaluate Current Maturity)

## Practice 15: Implement Real-Time Observability with Automated Incident Response
- **What:** Build an observability stack combining Agentforce Analytics (granular per-agent metrics), Command Center (high-level orchestration view), Testing Center (pre/post-deployment validation), and Digital Wallet (cost monitoring). Create incident playbooks with defect categorization, symptoms, and automated notification/response procedures. Monitor escalation rate as a primary health KPI.
- **Why:** Autonomous agents can cause damage silently — especially headless agents operating in the background. Real-time monitoring (not near-real-time) is non-negotiable because misconfigured guardrails can expose sensitive data, malfunctioning actions can corrupt business processes, and zombie agents (abandoned but still-active) are a serious security risk. Escalation rate is the single best indicator of agent-user alignment.
- **Lyra route:** §4.7 (Observability, Harness Engineering)
- **Source:** Chapter 3 (§Agent Performance and Scalability, §AgentOps and Life Cycle Management), Chapter 5 (§Use Fallbacks and Failsafes)
