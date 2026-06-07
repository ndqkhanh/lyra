# AI Agents Bible -- Best Practices Playbook

**Source:** Tomasz Dylik, *AI Agents Bible (5 Books in 1)*, 2025
**Extracted for:** Lyra Agent Harness Engineering
**Note:** This playbook extracts 12 operationally actionable practices. The book is platform-focused (n8n, Make.com, Custom GPTs) and directed at business builders. Practices are adapted to Lyra's agent harness context where appropriate.

---

## Practice 1: Implement the ReAct Loop with Structured Logging for Auditability

- **What:** Every agent action should follow the Thought -> Action -> Observation cycle. Log every Thought step explicitly -- what the agent reasons, what it plans to do next, and why. The Observation captures the result. This creates a full audit trail.
- **Why:** Without explicit reasoning logs, the agent is a black box. You cannot debug errors, spot bias, or prove accountability. ReAct logging transforms the system from opaque to auditable -- essential for compliance (EU AI Act) and trust. The audit trail also enables self-correction: the agent learns from past resolved sequences and becomes faster/more accurate on repeat.
- **Lyra route:** §4.1 (Execution Loop), §4.7 (Safety/Governance)
- **Source:** Chapter 2 (Agent Loop), Chapter 13 (Security), Chapter 16 (Ethics/ReAct for auditability)

## Practice 2: Adopt the Manager/Worker/Critic Multi-Agent Pattern

- **What:** Structure multi-agent systems with three role types: a Manager that decomposes goals and tracks progress, specialized Workers that execute narrow-domain tasks, and a Critic that verifies outputs against standards. The Manager uses a comprehensive brief (A-CROFTC: Agent, Context, Role, Objective, Format, Tone, Constraints) as the system's "genetic code."
- **Why:** A single general-purpose agent fails at complex, multi-step projects -- it slows down, loses context, and produces shallow results. Specialization via clear roles is more reliable, easier to debug, and enables parallel execution. The Manager/Worker/Critic pattern is the minimum viable multi-agent architecture.
- **Lyra route:** §4.1 (Agent Runtime), §4.4 (Sub-Agent Orchestration)
- **Source:** Chapter 10 (Multi-Agent Architectures)

## Practice 3: Model Routing by Task Complexity -- Pay for Intelligence Only When Needed

- **What:** Implement a model router that classifies each task by complexity. Route simple tasks (classification, summarization, reformatting) to smaller, cheaper, faster models (e.g., Claude Haiku, Llama 3 8B). Route complex multi-step reasoning tasks to premium models. Set hard API limits (max_rpm, budget caps) to prevent loop-induced runaway costs.
- **Why:** Using a premium model for everything is "like using a senior lawyer to sort your inbox." Autonomy has a hidden cost downside: each step incurs token expense. Without routing, ROI becomes a guess. Logging token usage per transaction reveals hidden cost sources (verbose prompts, long contexts, repeated work from failed tool calls).
- **Lyra route:** §4.5 (Model Routing), §4.6 (Cost/Observability)
- **Source:** Chapter 2 (Cost optimization tip), Chapter 12 (Performance Tuning)

## Practice 4: Chunking Strategy as a First-Class Optimization Target

- **What:** For any RAG/knowledge retrieval system, invest heavily in chunking strategy *before* tuning anything else. Chunk size directly affects accuracy, speed, and cost. Too small = loses context (technically relevant but practically useless). Too large = includes noise (model gets distracted). Test embedding model fit against your specific document type.
- **Why:** Most RAG failures (irrelevant or incomplete answers) are retrieval problems, not generation problems. Chunking is called "one of the biggest levers you have" in the book. It is often underestimated as a minor preparatory step, but it is the foundation of retrieval quality.
- **Lyra route:** §4.2 (Memory/Context), §4.3 (Knowledge Grounding)
- **Source:** Chapter 11 (RAG -- Chunking section)

## Practice 5: Structured Output Parsing for Production Reliability

- **What:** Always use a structured OUTPUT PARSER that forces predictable JSON output from AI agent nodes. Define output schemas from JSON examples rather than writing complex schemas by hand. This makes downstream processing nodes reliable because they can depend on a known data contract.
- **Why:** The biggest problem with AI in production isn't the model -- it's unclear prompts and tool definitions that produce unpredictable results. Structured output makes AI reliable in production. Without it, downstream steps break on unexpected formats.
- **Lyra route:** §4.1 (Agent Runtime), §4.4 (Tool/Plugin Interface)
- **Source:** Chapter 7 (AI Nodes / OUTPUT PARSER)

## Practice 6: Human-in-the-Loop as a Guardrail, Not Micromanagement

- **What:** For high-stakes or irreversible actions (financial transactions, data deletion, mass communications, critical system changes), require human confirmation before execution. Define clear thresholds that trigger HITL (e.g., refund above $500, PII access, outbound campaigns). The pattern preserves AI speed and scale while keeping human accountability where it belongs.
- **Why:** Full autonomy for high-stakes decisions is too risky. HITL prevents costly errors, provides explicable governance (EU AI Act compliance), and maintains trust. It also serves as a safety net that stops endless loops and wasted effort via confidence thresholds (<90% confidence -> escalate).
- **Lyra route:** §4.7 (Safety)
- **Source:** Chapter 2 (Confidence thresholds), Chapter 13 (HITL Framework)

## Practice 7: Error Trigger as the Boundary Between Hobby and Production

- **What:** Every production workflow must include an ERROR TRIGGER that defines a planned response to failure: alert, log, recover, and move on. The pattern changes failure from "someone notices later" to a structured, observable response. Instrument with centralized log management.
- **Why:** Many teams skip error handling because of the extra setup cost -- "but they stop skipping it after their first real problem." Without explicit error triggers, failures are silent until they cascade. Good error management makes workflows more reliable and resilient.
- **Lyra route:** §4.6 (Observability), §4.7 (Safety/Recovery)
- **Source:** Chapter 7 (ERROR TRIGGER node), Chapter 13 (Security -- logging)

## Practice 8: Least Privilege for Agent-Tool Bindings

- **What:** Every agent should have access *only* to the tools, data, and APIs it requires for its specific task. An agent that analyzes traffic should not access the customer database. An agent that drafts emails should not be able to send without approval. Permissions are the first and best line of defense.
- **Why:** The more tools you provide an agent, the larger the blast radius when something goes wrong. Least privilege limits damage from unintended actions and prompt injection attacks. This is not a post-deployment layer -- it is an architectural requirement from the start.
- **Lyra route:** §4.7 (Safety / Tool Access Control)
- **Source:** Chapter 13 (Compliance and Access Control)

## Practice 9: The 5 Essential AgentOps KPIs

- **What:** Track these five metrics for every agent deployment:
  1. **Actual Automation Rate:** % of tasks resolved end-to-end with zero human intervention (purest ROI measure)
  2. **Escalation Rate:** % of tasks handed to humans (exposes knowledge gaps)
  3. **Hallucination Rate:** frequency of factually incorrect answers (target <2% for customer-facing)
  4. **CSAT on AI-handled tickets:** direct customer sentiment
  5. **Task Adherence:** consistency with defined SOPs (compliance and quality control)
- **Why:** "You can't manage a digital workforce based on gut feelings." These KPIs translate agent performance into measurable business impact and provide early warning of degradation. They also demonstrate ethical AI management for governance and compliance.
- **Lyra route:** §4.6 (Observability/Evaluation), §4.8 (Deployment/Adoption)
- **Source:** Chapter 12 (AgentOps), Chapter 14 (5 Essential KPIs)

## Practice 10: The 6-Question Pre-Deployment Ethics Framework

- **What:** Before deploying any agent, answer six questions:
  1. Fairness -- How have we audited for bias in training data and agent design?
  2. Transparency -- Can we explain *why* the agent made a specific decision? Is reasoning auditable?
  3. Accountability -- Who is responsible if the agent harms a customer? What is the remediation process?
  4. Human Oversight -- Is there a human in the loop at critical points? When can humans override?
  5. Privacy -- How are we protecting PII? Are storage and handling secure and compliant?
  6. Intended Use -- How could this agent be misused? What safeguards prevent misuse?
- **Why:** "Five minutes upfront can prevent major incidents in fairness, accountability, and privacy." Ethics is a competitive advantage in the Agent Economy -- trust is the differentiator. Pre-deployment review catches high-risk problems early, when they're still easy to fix.
- **Lyra route:** §4.7 (Safety), §4.8 (Governance)
- **Source:** Chapter 16 (6-Question Ethics Framework)

## Practice 11: POC -> POV -> Scale as the Adoption Roadmap

- **What:** Structure AI deployment in three phases: Quarter 1 -- Proof of Concept (technical feasibility, 1-2 quick-win use cases, pilot team), Quarter 2 -- Proof of Value (measurable business result, e.g., 25% reduction in response time, rigorous KPI tracking), Quarters 3-4 -- Value Expansion (multi-agent systems, governance procedures, cross-functional deployment). Start from the "High Impact, Low Complexity" quadrant.
- **Why:** 74% of companies struggle to scale AI. The #1 mistake is starting with high-complexity projects that fail to deliver before leadership buy-in runs out. The phased approach builds momentum, proves value at each stage, and gives time to build skills and governance. Each phase gates the next on real evidence.
- **Lyra route:** §4.8 (Deployment Strategy), §4.9 (Roadmap)
- **Source:** Chapter 14 (12-Month Scaling Framework), Chapter 15 (Lean Methodology)

## Practice 12: Intent Preservation via Documentation (Sticky Note Pattern)

- **What:** In every workflow or prompt chain, preserve design intent: assumptions, branch meanings, ownership, test notes, and known watchpoints. This is not decoration -- it is about making the system maintainable. "A workflow that works but can't be safely changed isn't an asset, it's a risk."
- **Why:** Long-term problems in production systems aren't just technical -- they're about forgetting why choices were made. Without intent preservation, future maintainers (including future-you) cannot safely modify the system. This is especially critical in prompt chains where small wording changes can dramatically alter agent behavior.
- **Lyra route:** §4.1 (Prompt Management), §4.6 (Observability/Documentation)
- **Source:** Chapter 7 (STICKY NOTE -- "the most-used node 'does nothing,' and that's exactly why it's important")
