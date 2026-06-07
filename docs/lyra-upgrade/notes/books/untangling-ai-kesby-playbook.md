# Untangling AI — Best Practices Playbook for Lyra

*Extracted from Matt Kesby's "Untangling AI: Driving Business Success Through Enterprise Automation and AI Agents" (Wiley, 2026)*

---

## Practice 1: The Four Core Agent Treatments — Architecture Patterns

- **What:** All AI agent deployments fall into exactly four architectural patterns, in increasing order of complexity and autonomy:
  1. **Single Agent Direct Chat** — User ↔ one specialized agent, grounded in domain knowledge. Best for knowledge retrieval, coaching, Q&A.
  2. **Multi-Agent Workflow** — Linear chain of specialist agents, each handling one step and passing output to the next. Best for sequential, standardized processes.
  3. **Multi-Agent Orchestration** — One "director" agent autonomously delegates to specialist sub-agents (manager → worker hierarchy). Agentic, probabilistic outputs.
  4. **Advanced AI Agent Automations** — Long-running, deterministic processes requiring low-code control (JavaScript). Best for 24/7 operations, multi-system integrations.

- **Why:** Each treatment has different failure modes, cost profiles, and reliability guarantees. Matching the architecture to the problem prevents over-engineering (using orchestration where a single agent suffices) and under-delivery (using a single agent where deterministic automation is required).

- **Lyra route:** §4.1 (Agent Architecture) — Lyra must support all four treatments natively, with clear guidance on when to use each. The treatments form Lyra's agent topology taxonomy.

- **Source:** Section 3.4 (The King Is Dead, Long Live the King), Section 5.5 (The Core Four AI Agents)

---

## Practice 2: The DDDEEE Implementation Flywheel

- **What:** A six-phase, repeatable framework for every AI agent/automation initiative:
  1. **Discover** — Map current state process, quantify Value Impact = (Current Time × Cost × Frequency) − (Future Time × Cost × Frequency), build business case.
  2. **Design** — Architect future-state workflow with AI agents at core, identify systems/data/integrations, create build plan with UX specs.
  3. **Deploy** — Build fast in iterative cycles (Agile-inspired). Focus on high-leverage actions first. Architect for model evolution (modular, swappable). Stress-test via unit/integration/UAT.
  4. **Educate** — Role-specific training, async learning materials, centralize knowledge in AI-connected wikis, assign clear ownership. "Ownership builds trust."
  5. **Execute** — Go live, collect data, track Value Impact vs hypothesis, continuous small optimizations.
  6. **Evaluate** — Formal comparison of results vs business case, present ROI to leadership, identify wins/gaps/learnings, celebrate success. "Reflection builds momentum."

- **Why:** Without a systematic framework, AI initiatives devolve into disconnected experiments with no measurable ROI. Each successful cycle builds confidence, skills, and budget for the next cycle — creating a compounding flywheel effect.

- **Lyra route:** §4.2 (Agent Lifecycle Management) — DDDEEE maps directly to Lyra's agent creation → deployment → monitoring → retirement lifecycle.

- **Source:** Section 4.4 (DDDEEE Framework)

---

## Practice 3: RAG + Tool Calling as Competitive Moat

- **What:** Combine two capabilities for every business-facing agent:
  - **RAG (Retrieval-Augmented Generation):** Give agents access to proprietary business documents, SOPs, past cases, customer data. Grounds agents in domain-specific knowledge that competitors cannot replicate.
  - **Tool Calling via MCP:** Connect agents to business systems (CRM, ERP, email, project management) through standardized Model Context Protocol, enabling agents to take action, not just answer questions.

- **Why:** General AI models are a commodity — every competitor has access to them. The competitive differentiation comes from what you put INTO the agents: your operational data, refined instructions, accumulated memories, and domain-specific processes. RAG + tool calling creates a data moat that compounds over time as agents learn from every interaction.

- **Lyra route:** §4.3 (Knowledge & Memory Systems), §4.1 (Tool Integration) — Lyra's plugin system + RAG architecture should be designed as a moat-building mechanism.

- **Source:** Section 0.4 (RAG: Making Your AI Agents Domain Experts), Section 6.2 (Value Is in the Data ... and It's the Data in Your AI Agents)

---

## Practice 4: Agent Instruction Template — Profile/Purpose/Scope/Process/Constraints

- **What:** Every agent should be defined using a structured instruction template:
  ```
  #Profile — Who the agent is (role, specialization, persona)
  ##Purpose — Why the agent exists (mission, goal statement)
  ##Scope — What the agent can and cannot do (boundaries)
  ##Process — How the agent works (step-by-step methodology)
  ##Constraints & Style — Rules, tone, limitations, guardrails
  ```
  Plus a Knowledge section for domain grounding (connected to live documents that auto-update).

- **Why:** Structured instructions ensure consistent agent behavior. When instructions are free-form, agents drift over time. The structure also makes agents auditable and reviewable by non-technical stakeholders. The "Constraints" section doubles as a built-in guardrail mechanism.

- **Lyra route:** §4.1 (Agent Configuration Schema) — This template should be Lyra's canonical agent definition format.

- **Source:** Section 3.4 (Building Your First AI Agent — Instagram Reels Script Writer example)

---

## Practice 5: The 5-Phase AI Agent Rollout Cadence

- **What:** Deploy agents in a deliberate, phased sequence over 12 months:
  - **Phase 1 (Months 1-2):** Single-agent direct chat only. Build organizational comfort. Establish knowledge bases. Train key team members.
  - **Phase 2 (Months 3-4):** Multi-agent workflows for standardized processes. Focus on high-impact, time-consuming tasks with predictable patterns. Measure and document efficiency gains.
  - **Phase 3 (Months 5-6):** Agentic orchestration for complex, decision-making processes. Enable agent-to-agent delegation. Implement feedback loops.
  - **Phase 4 (Months 7-12):** Advanced automations — long-running, deterministic processes integrated with existing business systems.
  - **Phase 5 (Ongoing):** Continuous evolution — regular performance assessment, agent retirement/creation cycles, integration of emerging capabilities.

- **Why:** Jumping straight to agentic orchestration without mastering single-agent and workflow patterns causes failures that erode organizational trust. The phased approach builds capability and confidence incrementally, and each phase's ROI funds the next.

- **Lyra route:** §4.2 (Adoption & Rollout Strategy) — This phased model provides a template for Lyra's own deployment roadmap.

- **Source:** Section 3.4 (Strategic Implementation Framework)

---

## Practice 6: Problem-First, Not Technology-First

- **What:** Always start AI initiatives with problem identification, not technology selection. The question is NOT "What agent should I build?" but "What are the goals for my team, and how could AI agents assist me in my specific position to deliver upon my goals?"

- **Why:** 63.8% of successful AI projects began with problem identification vs. only 24.7% that started with technology-push approaches (Kamruzzaman et al., 2025). Technology-first initiatives produce "solutions in search of a problem" and waste subscriptions. The PAD Framework (Problem → Abilities → Data) from University of Michigan provides the structure.

- **Lyra route:** §4.2 (Requirements & Scoping) — Lyra's agent creation flow should enforce problem-first discovery before any agent configuration.

- **Source:** Section 5.1 ("What AI Agents Should I Build?" Might Be the Wrong Question)

---

## Practice 7: The "What Else?" Discovery Technique

- **What:** When brainstorming AI opportunities with team members, ask "What else? What else? What else?" persistently until they exhaust their ideas. Apply to specific prompts: "What tasks take up most of your time? What else? What processes frustrate you? What else? What information do you wish you had faster? What else?"

- **Why:** The first idea people share is the safest, most obvious one. Real breakthrough insights lie beneath the surface. The technique also builds psychological safety by signaling that you value their judgment — shifting from dictating solutions to extracting expertise.

- **Lyra route:** §4.2 (Discovery & Requirements Elicitation) — This technique should be embedded in Lyra's onboarding and discovery workflows.

- **Source:** Section 5.2 (What Do We Need To Improve? What Else? What Else? What Else?)

---

## Practice 8: Layered AI Security Defense

- **What:** Defend against AI-specific threats with a layered approach:
  1. **Input validation** — Screen for anomalies, embedded instructions, hidden text (e.g., white-on-white prompt injection in resumes)
  2. **Guardrail prompting** — Explicitly instruct AI systems to ignore embedded instructions and flag suspicious inputs
  3. **Adversarial training** — Expose models to known attack patterns during development
  4. **Human oversight** — Mandatory HITL for high-stakes decisions (hiring, lending, legal)
  5. **Continuous monitoring** — Deploy AI-powered monitoring agents that watch for bias, security anomalies, and prompt injection in real time
  6. **Regular red-team exercises** — Experts attempt to compromise AI systems proactively

- **Why:** Prompt injection is a "digital Trojan horse" — already present in ~10% of AI-scanned resumes (ManpowerGroup, 2025). Traditional cybersecurity (firewalls, encryption, MFA) does not prevent these attacks. AI-specific threats require AI-specific defenses at every layer.

- **Lyra route:** §4.8 (Safety & Security) — Lyra's guardrail and monitoring architecture should implement all six layers.

- **Source:** Section 1.5 (Ethics, Privacy, Security), Section 3.3 (Data Readiness Audit — security section)

---

## Practice 9: Continuous Agent Training as Organizational Memory

- **What:** Treat every human-agent interaction as a training opportunity. When team members correct an agent's output, refine its instructions, or teach it a better approach, that knowledge should be captured as a permanent memory. Implement centralized learning with distributed execution — when one agent learns, all instances of that agent class benefit.

- **Why:** Over time, well-trained agents become more valuable than any single employee because they carry the collective intelligence of the entire organization. This is the same pattern Waymo uses: "When one car learns, all cars learn instantly." The compounding effect creates an un-replicable competitive advantage.

- **Lyra route:** §4.7 (Learning & Evolution) — Lyra's memory refinement loop should implement centralized learning with distributed execution.

- **Source:** Section 6.3 (It's Not One and Done: Training Your AI Agents)

---

## Practice 10: The Human Agency Scale for Autonomy Decisions

- **What:** Use the Stanford Human Agency Scale (HAS) to determine the right level of human involvement for each agent task:
  - **H1 (Full Automation):** Repetitive, low-risk tasks where error cost is low. Agent handles entirely.
  - **H2 (AI-Led + Human Oversight):** Agent takes primary responsibility, human reviews at key points. Default for most business applications.
  - **H3 (Equal Partnership):** Agent proposes, human decides, agent executes.
  - **H4 (Human-Led + AI Assistance):** Human leads, AI provides analysis and recommendations.
  - **H5 (Full Human Agency):** Human handles entirely. For highest-stakes decisions.

- **Why:** The binary "automate or not" question is too crude. HAS provides a nuanced framework that matches autonomy level to risk profile, enabling faster deployment of lower-risk automations while maintaining appropriate human control over consequential decisions.

- **Lyra route:** §4.1 (Agent Autonomy Levels) — HAS maps directly to Lyra's autonomy/confidence threshold system.

- **Source:** Section 0.4 (The Human Agency Scale), citing Shao et al., Stanford University (2025)

---

## Practice 11: Context Engineering Over Prompt Engineering

- **What:** Shift from prompt engineering (tactical, per-interaction) to context engineering (strategic, persistent). Context engineering involves curating and feeding the AI a rich, persistent body of information: company data, previous conversations, style guides, customer profiles, project goals. This transforms AI from a generic tool into a specialized digital team member with institutional knowledge.

- **Why:** Prompt engineering starts from zero every time — treating the AI like "an expert with amnesia." Context engineering ensures every answer is not just accurate but deeply relevant to the specific business context. It is the difference between hiring a brilliant consultant for a single meeting vs. giving them a full library, company history, and a seat at every meeting.

- **Lyra route:** §4.3 (Persistent Context & Memory) — Lyra's context management architecture should prioritize context engineering over raw prompt engineering.

- **Source:** Section 3.1 (Context Engineering: Beyond Prompt Engineering)

---

## Practice 12: Voice-First Capture and Mobile Orchestration

- **What:** Enable voice-to-AI capture for ideas, requests, and agent creation. Let users talk to their phone to: capture AI ideas, create new agents, query existing agents, review outputs, and approve HITL steps. The AI Command Room should have a mobile interface for real-time oversight.

- **Why:** The best ideas emerge outside the office — during commutes, walks, conversations. If capture requires sitting at a laptop, most ideas die. Voice-first capture plus mobile orchestration enables the "freedom through orchestration" vision where employees manage AI agents from anywhere.

- **Lyra route:** §4.4 (Voice & Real-Time Interaction) — Lyra's voice interface should be designed for agent orchestration, not just conversation.

- **Source:** Section 4.1 (Stop Typing, Start Talking), Section 4.5 (Command Room mobile access)

---

## Practice 13: The AACCE Hiring & Development Framework

- **What:** Hire and develop for five timeless skills that AI amplifies rather than replaces:
  - **Agility** — Learn, unlearn, relearn quickly. Mental, learning, change, and people agility.
  - **Articulate with Specificity** — Precise communication with both humans and AI systems (three levels: Basic Clarity → Contextual Precision → Strategic Alignment).
  - **Creativity** — Novel problem-solving, imagination, original ideas. "AI can remix; humans can originate."
  - **Critical Thinking** — Objective analysis, evaluation of information, sound judgment. "AI generates; humans validate."
  - **Empathy** — Understanding and sharing feelings. "AI can simulate; humans genuinely connect."

- **Why:** Technical skills become obsolete as AI advances. These five meta-skills compound in value because they complement and direct AI capabilities rather than competing with them.

- **Lyra route:** §4.2 (Team & Role Design) — The skills matrix for Lyra's development team and end-user training programs.

- **Source:** Section 2.5 (The Five Key Skills to Hire and How to Nurture Them from Within)

---

## Practice 14: OKRx Gamification for AI Adoption

- **What:** Use gamification (OKRx = Objectives, Key Results, X-Factors) to drive AI adoption. Create transparent, real-time dashboards showing every team member's AI agent usage, Value Impact generated, and progress against goals. Use this data for coaching (not punishment) — the AI Agent Coach built into the system can generate talking points grounded in high-trust communication methods.

- **Why:** Lencioni identifies "immeasurement" as a root cause of job misery. When employees cannot objectively prove their AI contribution, they fear being replaced. Transparent metrics counter this by giving them proof of value. Gamification creates "winnable games" that make AI adoption engaging rather than threatening.

- **Lyra route:** §4.9 (Observability & Dashboards) — Lyra's analytics layer should implement transparent Value Impact tracking with coaching-oriented defaults.

- **Source:** Section 4.5 (Your AI Command Room), Section 4.7 (Playing to Win: Managing Change Through Gamification)

---

## Practice 15: The Amplification Matrix for Change Management

- **What:** Use the Amplification Matrix to communicate AI's impact: show concrete before/after examples of how specific roles evolve from task-execution to strategic orchestration through AI augmentation. Frame AI as "Amplified Intelligence" (Human + AI), not "Artificial Intelligence" (AI instead of Human). Lead with "love not fear" — AI is enhancing human capability, not eliminating human roles.

- **Why:** The amygdala hijack (fear response) is biological, not rational. When people perceive AI as a threat, their brains literally cannot process new information effectively (fight/flight/freeze response). The Amplification Matrix bypasses this by showing AI as a tool that makes them more valuable, not less.

- **Lyra route:** §4.2 (Change Management & Adoption) — Lyra's onboarding and communication strategy.

- **Source:** Section 2.2 (Leading with Love Not Fear), Section 2.3 (Shift Fear of Job Loss)
