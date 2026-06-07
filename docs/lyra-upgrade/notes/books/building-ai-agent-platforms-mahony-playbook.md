# Building AI Agent Platforms — Best Practices Playbook

**Source:** Ben O'Mahony and Fabian Nonnenmacher, _Building AI Agent Platforms_ (O'Reilly, 2027 Early Release)
**Extracted:** 2026-06-07 | **Chapters available:** 1–2 of 18 planned

---

## Practice 1: Apply Eval-Driven Development (Not Pass/Fail Testing)

- **What:** Define evaluation criteria upfront — before writing any code. Use multi-dimensional confidence scores (accuracy, coherence, safety adherence) instead of binary pass/fail. Run an experimentation loop where every prompt change, model swap, or tool modification is measured against the eval baseline.
- **Why:** LLM output is non-deterministic and open-ended. Traditional unit tests cannot capture whether an AI application is improving or degrading. Without evals, development becomes aimless ("coasting on vibes"). Eval-Driven Development ensures every change is directly assessed against business-aligned metrics.
- **Lyra route:** §4.1 (Eval Harness), §4.3 (Experimentation Loop)
- **Source:** Chapter 1, "Testing" phase and "Aimless development without Evals" anti-pattern

---

## Practice 2: Prefer Graph-Based Agents Over Unstructured Autonomous Agents

- **What:** Define a high-level graph structure (state machine) within which the agent operates. The agent's autonomy is intentionally limited to deciding state transitions within the pre-defined graph, not inventing its own control flow from scratch.
- **Why:** Raw unstructured agents are unreliable — they choose inefficient paths, loop endlessly, or do too little work. A graph structure ensures systematic completion of necessary stages while preserving autonomy within each stage. The Deep Research pattern (Plan → Search → Evaluate → Report) is the canonical example. Orchestrated workflows using external engines (Airflow, Argo) are even more reliable when the control flow is strictly deterministic.
- **Lyra route:** §4.4 (Graph-based Agent Router), §4.2 (Workflow Orchestration)
- **Source:** Chapter 1, "Graph-based AI Agents" and "Orchestrated AI Workflows" patterns

---

## Practice 3: Build Specialized Sub-Systems, Not a God Agent

- **What:** Decompose complex AI applications into smaller, specialized subsystems — each an independently operable agent or tool with a focused responsibility. Combine them through orchestration or multi-agent collaboration rather than asking one monolithic agent to handle everything.
- **Why:** Any domain valuable enough to build an application in is too complex for a single agent to choose the most correct action efficiently. Specialized sub-systems bring unavoidable error cases under control. Also, simple focused tasks are better built as tools (possibly MCP servers) than as agents — they are cheaper, more reliable, and reusable by higher-level agents.
- **Lyra route:** §4.5 (Multi-Agent Architecture), §4.7 (Tool/Plugin System)
- **Source:** Chapter 1, "The God Agent" and "Applications that should just be a tool" anti-patterns

---

## Practice 4: Implement Dedicated Tracing From Day One

- **What:** Record the complete history of all internal AI application interactions: input prompts, model responses, tool calls, intermediate reasoning steps. Use a dedicated tracing system (not just logs) with structured spans.
- **Why:** LLMs are black boxes. Tracing is the only reliable way to debug issues, understand real user behavior, audit for compliance, and explain decisions. Without tracing, you cannot diagnose why an agent took a wrong action or why an eval score changed. This is the AI equivalent of distributed tracing in microservices.
- **Lyra route:** §4.6 (Observability/Tracing), §3.2 (Audit & Compliance)
- **Source:** Chapter 1, "Explainability and auditability" and "Operations and Monitoring"

---

## Practice 5: Keep Prompts in Version Control, Not a Dedicated Management System

- **What:** Store prompts as plain text files in the same version control repository as the code that invokes them. Make them variables in separate files to support A/B testing. Avoid building complex infrastructure for editing, sharing, and versioning prompts.
- **Why:** Prompts have limited reusability — they are tailored to specific use cases and often specific LLMs. Newer models are more robust to prompt perturbation, reducing the need for highly optimized shared prompts. A prompt that works with one model may fail with another. Keeping prompts in VCS near code dramatically simplifies platform maintenance, aids debugging, and allows non-technical stakeholders to contribute via GitHub UI. Exception: prompt hints for users can be served via a simple MCP server.
- **Lyra route:** §4.8 (Prompt Management), §5.2 (Golden Path Templates)
- **Source:** Chapter 2, "Over-Focusing on Prompt Management" anti-pattern

---

## Practice 6: Provide Escape Hatches at Every Abstraction Layer

- **What:** Design platform APIs with layered abstractions where users can drop down to lower levels and override any sensible default. Let teams bring their own tools, configure their own infrastructure, and deviate from the golden path when needed.
- **Why:** The platform team cannot anticipate every use case, especially in a rapidly evolving AI ecosystem. Rigid golden paths become golden cages that stifle innovation and drive teams away from the platform. Escape hatches preserve team autonomy while still providing value for common cases. "If your users haven't built something that surprised you, you probably didn't build a platform" (Gregor Hohpe).
- **Lyra route:** §5.1 (Plugin Architecture), §5.3 (Custom Tool Integration)
- **Source:** Chapter 2, "Escape Hatches" and "Golden Cage" anti-pattern

---

## Practice 7: Integrate Into Existing Platforms, Don't Build a Separate AI Runtime

- **What:** Extend the organization's existing Internal Development Platform (IDP), Data Platform, and MLOps Platform with AI-specific capabilities rather than building a standalone AI agent platform from scratch. Use the same runtime (e.g., Kubernetes), CI/CD, logging, auth, and monitoring as existing services.
- **Why:** AI applications are effectively microservices that call LLMs — they don't need a separate runtime. Building a parallel platform duplicates infrastructure, forces teams to learn new defaults, and fragments the ecosystem. Existing platforms are already battle-tested. Rebuilding basic capabilities (container orchestration, CI/CD, logging) is a massive undertaking that adds no unique value.
- **Lyra route:** §5.4 (Platform Integration), §2.1 (Infrastructure Architecture)
- **Source:** Chapter 2, "Separate Special Runtime for AI Applications" anti-pattern and "Existing Platform Ecosystem"

---

## Practice 8: Design Templates as Walking Skeletons (Omakase Principle)

- **What:** Provide minimal end-to-end project templates (walking skeletons) covering the full lifecycle: development → evaluation → deployment → monitoring. Include opinionated but non-mandatory technology choices. Start with the simplest common use case and avoid overloading templates with every platform capability.
- **Why:** The "Omakase" principle (chef's choice) lowers the entry barrier for teams new to AI Engineering — they trust the platform team's expertise to select good ingredients. Templates also enforce organization-wide macro-architecture rules (logging standards, auth, compliance scanning) automatically, making compliance easy rather than enforced through gatekeeping.
- **Lyra route:** §5.2 (Golden Path Templates), §3.1 (Bootstrap/Scaffolding)
- **Source:** Chapter 2, "Templates and Golden Path" and "Omakase Principle"

---

## Practice 9: Use Pre-Built Workflow Engines for Deterministic Orchestration

- **What:** When orchestrating a fixed-order sequence of tasks, use existing workflow/pipeline engines (Airflow, Argo Workflows, Temporal) instead of reimplementing orchestration inside agent code.
- **Why:** Workflow engines provide checkpointing, error handling, parallel execution, retries, and monitoring out of the box — features you will inevitably need. Reimplementing them within an agent or application adds unnecessary complexity and fragility. AI agents should be used for steps requiring LLM-driven decision-making, not for deterministic control flow.
- **Lyra route:** §4.2 (Workflow Orchestration), §4.4 (Agent Router)
- **Source:** Chapter 1, "Reimplementing orchestration within applications" anti-pattern and "Orchestrated AI Workflows"

---

## Practice 10: Design for Extreme Users (Novices AND Experts)

- **What:** When determining platform requirements, gather input from the extremes — the simplest and most complex use cases, and the most novice and most expert users — rather than focusing on the average. Address both ends; the middle will be served automatically.
- **Why:** Average-user design leads to platforms that satisfy no one fully. Designing for novices ensures low entry barriers (tutorials, sensible defaults, templates). Designing for experts ensures escape hatches and advanced capabilities (fine-tuning, custom orchestration, multi-agent patterns). As users and use cases evolve, they have a growth path without outgrowing the platform.
- **Lyra route:** §5.1 (API Design), §5.2 (Documentation Structure)
- **Source:** Chapter 2, "Identifying Core Platform Capabilities" and "Designing for Extreme Users"

---

## Practice 11: Structure Documentation with the Diátaxis Framework

- **What:** Organize platform documentation into four distinct types: **Tutorials** (step-by-step for beginners), **How-to guides** (task-oriented for experienced users), **Reference** (API definitions, config options), and **Explanation** (underlying concepts and design rationale). Practice Docs-as-Code: keep docs in VCS, generate from docstrings/tests where possible.
- **Why:** Different users need different kinds of documentation at different times. The Diátaxis framework prevents the common failure mode where documentation is a single undifferentiated blob that serves no one well. AI Engineering has a diverse audience (from AI novices to ML experts), making structured documentation especially critical.
- **Lyra route:** §5.2 (Documentation & Onboarding)
- **Source:** Chapter 2, "Comprehensive Documentation"

---

## Practice 12: Use the Mise-en-Place Principle for Platform Capabilities

- **What:** All platform components should be not just available, but organized and arranged for efficient composition. This means consistent auth across all services, unified observability backends, automatically injected connection details, pre-configured default permissions, and runtime composability between components (e.g., agent runtime seamlessly accessing the vector database).
- **Why:** A platform that is merely a fragmented collection of guides, tools, and services forces teams to waste time manually stitching components together. Mise-en-place ("everything in its place") ensures teams can pick and choose what they need in their current context while always having the option to extend into other capabilities over time.
- **Lyra route:** §5.3 (Service Integration), §2.2 (Service Mesh / Composition)
- **Source:** Chapter 2, "Integrating Capabilities Effectively" and "Mise-en-Place Principle"

---

## Practice 13: Treat the Platform as a Product, Not a Project

- **What:** Dedicate a product team with ongoing funding. Understand user needs through empathy (not just what they ask for). Win adoption through value, never mandate. Measure success by team autonomy and delivery acceleration, not feature completeness. Celebrate when users contribute back (internal open source).
- **Why:** Platforms built as one-off projects stagnate and become legacy the moment the project "ends." The AI ecosystem evolves too fast for project-based funding — platform capabilities must continuously adapt. Mandates mask poor product decisions; adoption through value forces the platform team to solve real problems.
- **Lyra route:** §5.0 (Platform Governance & Strategy)
- **Source:** Chapter 2, "Adopting a Product-Based Funding Model" and "Enforcing Mandates instead of Winning Adoption"

---

## Practice 14: Accept Imperfection — Plan for It Architecturally

- **What:** AI applications will never be perfectly accurate. Address this holistically: (1) business stakeholders must accept and quantify the risk of errors, (2) include human-in-the-loop review for consequential actions (e.g., booking confirmation), (3) implement guardrails — both deterministic software checks and LLM-based output validators, (4) use prompt engineering → RAG → fine-tuning as an accuracy-improvement escalation ladder.
- **Why:** Treating AI applications like deterministic software leads to unrealistic expectations and brittle architectures. The platform must provide tooling for all four mitigation strategies, and the development lifecycle must include explicit accuracy/risk decisions early in the Discovery & Planning phase.
- **Lyra route:** §4.9 (Safety/Guardrails), §4.1 (Evaluation), §3.3 (Human-in-the-Loop)
- **Source:** Chapter 1, "Imperfect accuracy" challenge and anti-patterns catalog
