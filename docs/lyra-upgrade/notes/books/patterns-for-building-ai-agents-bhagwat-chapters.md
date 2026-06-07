# Patterns for Building AI Agents — Chapter Notes

**Author:** Sam Bhagwat & Michelle Gienow | **Year:** 2025 | **Publisher:** Self-published (Mastra)

**Core Thesis:** Building production AI agents is a discipline of pragmatic patterns — not a one-shot model prompt. The book argues that agent reliability comes from systematic practices in four domains: agent architecture design, context engineering, evaluation methodology, and security constraints. These patterns are proven by real production teams at Anthropic, Cognition, Google, Cursor, Replit, and others. The book is a practitioner's desk reference, not a textbook.

**Target Audience:** Engineers and technical PMs who have built an MVP agent and are now hitting the "production gap" — where agents work in demos but fail under real-user diversity, context overflow, nondeterministic outputs, and novel security attacks.

---

## Part I: CONFIGURE YOUR AGENTS

### Chapter 1: Whiteboard Agent Capabilities
- **Key insight:** Agent architecture design is organizational design for AI. List every desired capability exhaustively, group by shared data sources / job-title equivalence / API cohesion, then rank-order agents by priority. This turns a wishlist into a buildable architecture.
- **Best practices:**
  - Write down everything you want the agent to do. Ask "What are we missing?" repeatedly.
  - Group capabilities by: same data sources, same job title could perform them, same API call returns them.
  - Natural divisions: department boundaries, task type (fetch vs. synthesize vs. act), business process stage.
- **Anti-patterns:** Starting with the "grand vision" outside-in view without doing the inside-out grouping exercise. Building a single mega-agent that tries to do everything.
- **Example:** A sales agent was decomposed into: 1 support agent + 1 sales agent with 3 subagents (discovery/research, account synthesis, next steps).
- **Relevant to Lyra §4.1:** Agent architecture design maps directly to Lyra's orchestration/routing layer.
- **Relevant to Lyra §4.5:** The grouping exercise is exactly what a model router should use to determine which specialist to invoke.

### Chapter 2: Evolve Your Agent Architecture
- **Key insight:** The best agent architectures are discovered iteratively, not designed upfront. Start with one burning problem, build that agent well, notice what users ask for next, then split or add agents and routing logic. This matches Anthropic's "Building Effective Agents" philosophy.
- **Best practices:**
  - Iterate: build one agent well → notice next user request → build separate agent if distinct → split if agent becomes unwieldy → add routing → repeat.
  - Each specialist agent should have a cohesive toolchain focused on a specific domain.
  - Sequential chaining (Coordinator → Router → Specialists) is often the natural endpoint.
- **Anti-patterns:** Building a "master content agent" that writes mediocre everything instead of specialized agents per format. Trying to design the full architecture upfront before any single agent works.
- **Example:** Content creation agent evolved through 5 iterations: LinkedIn writer → +social media agent → +router → +blog writer → +content coordinator for message consistency. Each agent is great at its specific format.
- **Relevant to Lyra §4.5 Router:** Router agent pattern emerges naturally in iteration 3 — reads requests, detects platform from context, routes to specialists.
- **Relevant to Lyra §4.14 Autonomy:** The coordinator-router-specialist architecture is a core autonomy pattern.

### Chapter 3: Dynamic Agents
- **Key insight:** Agents should adapt their system prompt, tools, memory, and model at runtime based on signals like user role, preferences, or system state. This avoids creating N separate agents for N user segments.
- **Best practices:**
  - Use runtime context (user metadata, session state, env vars) to drive agent configuration.
  - Map user tiers to: tool selection (e.g., topK=8 for free, topK=15 for enterprise), model selection (GPT-3.5 vs GPT-5), support depth.
  - This enables cost/behavior trade-offs without maintaining multiple agents.
- **Anti-patterns:** Creating separate agent instances for each user tier when one dynamic agent suffices. Hardcoding tier logic in system prompts instead of using runtime context injection.
- **Trade-off:** Reduces redundancy but introduces complexity in testing and consistency verification.
- **Relevant to Lyra §4.5 Router:** Runtime model selection by user tier is a cost-aware routing pattern.
- **Relevant to Lyra §4.12 Permissions:** Tier-based access control is a security concern.

### Chapter 4: Human-in-the-Loop (HITL)
- **Key insight:** HITL is not a fallback — it is a first-class architecture pattern. There are three modes: (1) in-the-loop (agent pauses for human input mid-execution), (2) post-processing (human reviews draft before delivery), (3) deferred tool execution (agent pushes to human async, continues background work). Deferred execution is most aligned with real-world workflows because humans should not be blocking bottlenecks.
- **Best practices:**
  - Inject human checkpoints at the point of maximum risk, not at every step.
  - Deferred tool execution: agent pushes a PR and asks for feedback, but continues processing in background.
  - Humans become the bottleneck in HITL — design for async, not blocking step-by-step.
- **Anti-patterns:** Requiring human approval at every single step (creates babysitting). Using HITL as a substitute for proper eval (fix the agent, don't route all failures to humans).
- **Relevant to Lyra §4.14 Autonomy:** HITL is the autonomy slider — Lyra needs configurable human checkpoints.
- **Relevant to Lyra §4.10 Hooks:** Deferred tool execution aligns with hook-based post-processing patterns.

---

## Part II: ENGINEER AGENT CONTEXT

**Intro to Context Engineering:** Andrej Karpathy's term; both an art and a science. Context engineering encompasses prompt engineering, RAG, tool calling, and agent state/history. The core challenge: Goldilocks problem — too little context = insufficient info; too much = the model loses its way.

### Chapter 5: Parallelize Carefully
- **Key insight:** Parallel subagent workflows are fragile because subagents working in isolation produce mutually incompatible outputs. A single-threaded linear agent preserves continuous context and is more reliable. This is a CONTROVERSIAL pattern — Devin (Cognition) avoids parallelization, but Claude Code relies on it heavily. The right answer depends on task decomposability.
- **Best practices:**
  - When subtasks are interdependent, use sequential execution.
  - Parallelism is safe when subtasks are truly independent with no shared state.
  - If you parallelize, share context between subagents (see Chapter 6).
- **Anti-patterns:** Splitting interdependent tasks into parallel subagents without context sharing — the "runner fleeing enemies" + "branching path system" incompatibility problem.
- **Example:** Building a Temple Run clone — parallelizing character movement and path generation produced incompatible outputs (runner game vs. branching adventure game).
- **Relevant to Lyra §4.13 Swarm/Fleet:** This is the key architectural tension Lyra must resolve — when to fan-out parallel vs. when to serialize.
- **Relevant to Lyra §4.2 Memory:** Parallel workflows require context sharing; memory architecture must support cross-agent state.

### Chapter 6: Share Context Between Subagents
- **Key insight:** When subagents must work in parallel, share the full execution trace — not just the final output. A single message ("I made a red button") loses the why. The full trace (user request, research on brand colors, user approval) enables downstream agents to make contextually consistent decisions.
- **Best practices:**
  - Pass the full trace including user request, intermediate reasoning, and approvals.
  - Check subagent outputs along the way for compatibility before combining.
  - Consider running subagents sequentially if outputs are deeply interdependent.
- **Anti-patterns:** Passing only final action messages between subagents. Assuming subagents will independently arrive at compatible designs.
- **Warning:** This is another contested pattern — Claude Code does NOT share context between subagents, while Devin is careful about it.
- **Relevant to Lyra §4.2 Memory:** Full-trace sharing requires a shared memory substrate.
- **Relevant to Lyra §4.13 Swarm/Fleet:** Agent communication protocol design.

### Chapter 7: Avoid Context Failure Modes
- **Key insight:** Five named context failure modes — poisoning (hallucination recycled in context), distraction (model overfocuses on context, ignores training data), confusion (irrelevant context degrades quality), clash (new info conflicts with prior context), rot (beyond ~100K tokens, models lose ability to discern signal from noise). Context is NOT free — every token influences model behavior.
- **Best practices:**
  - Use RAG to filter to top-K results rather than including all relevant information.
  - Use a context pruning tool to remove irrelevant information.
  - Store a structured version of context; assemble a compiled string before each LLM call.
- **Concrete benchmark:** Google Gemini team's Pokemon-playing agent. Performance degraded at ~125K tokens despite 500K context window. After fixes (RAG filtering, pruning, structured context), accuracy went from 34% to reliably over 90%.
- **Anti-patterns:** Assuming "bigger context window = dump everything in." Including irrelevant documents that trigger context confusion and clash.
- **Relevant to Lyra §4.3 Context Compaction:** These five failure modes are the primary design targets Lyra's compaction must address.
- **Relevant to Lyra §4.2 Memory:** Structured context storage is a memory architecture concern.

### Chapter 8: Compress Context
- **Key insight:** As agents perform complex/long-running tasks, appending all context to the window causes slowdown, quality degradation, and eventual overflow. Periodic context compression prunes irrelevant tokens while retaining what's needed for the next step. Multiple strategies exist: compress at every step, compress at x% threshold, prune oldest (hierarchical summarization), recursive summarization, compress at token-heavy post-process tool calls, and summarize at agent-agent boundaries.
- **Best practices:**
  - Claude Code: autocompact at 95% context window capacity, summarizes full trajectory.
  - Mastra: composable memory processors (TokenLimiter removes oldest messages, ToolCallFilter removes tool calls from LLM messages).
  - Custom logic via base MemoryProcessor class extension.
  - Identify crucial events/decisions and do NOT compress those.
- **Anti-patterns:** Naively appending all context indefinitely. Compressing crucial decisions that downstream agents need. Using a single compression strategy regardless of task phase.
- **Relevant to Lyra §4.3 Context Compaction:** This is the direct blueprint — autocompact threshold, custom processors, selective preservation.
- **Relevant to Lyra §4.2 Memory:** Memory processors for retrieval-stage filtering.

### Chapter 9: Feed Errors Into Context
- **Key insight:** Instead of crashing on error, log the error to the thread's history and use it as context for the next decision. This is a self-healing pattern. If you notice commonly repeated error patterns, put them into the system prompt proactively.
- **Best practices:**
  - Capture raw error output and integrate into context for agent correction.
  - Automate the feedback loop: diagnose error → implement fix → re-execute → verify.
  - If error patterns repeat, bake fixes into the prompt.
  - Most popular coding agents (Cursor, Windsurf, Replit, Lovable) all do this.
- **Anti-patterns:** Silently swallowing errors. Letting the agent retry without the error context (guarantees repeated failure). Not recognizing repeated error patterns as prompt-improvement opportunities.
- **Relevant to Lyra §4.16 Reliability:** Error-to-context is a core reliability pattern. Lyra's agent loop should auto-capture and feed back errors.
- **Relevant to Lyra §4.6 Tools:** Tool execution failures should follow this pattern — error → context → retry.

---

## Part III: EVALUATE AGENT RESPONSES

**Intro:** The challenge isn't that AI agents fail — it's that their failures are nondeterministic, nuanced, and often invisible. Raw accuracy tells you something changed but not why or what to do about it. Evals solve the "flying blind" problem.

### Chapter 10: List Failure Modes
- **Key insight:** Creating a classification process that categorizes not only which failures occur but WHY they occur is the foundation of systematic agent improvement. This is the ML concept of "interpretability" applied to agent engineering.
- **Best practices:**
  - Classify failures into buckets: data quality failures, reasoning failures, domain-specific rule misapplications.
  - Example taxonomy from medical agent: Medical Record Extraction failures, Clinical Reasoning failures, Rules Interpretation failures.
  - This classification directly feeds into which engineering projects to prioritize.
- **Anti-patterns:** Only tracking "did it fail?" without understanding why. Treating all failures as equal when root causes require different fixes.
- **Relevant to Lyra §4.16 Reliability:** Failure mode taxonomy is the first step for Lyra's eval system.
- **Relevant to Lyra §4.25 Adversarial Panel:** Adversarial review should target known failure modes.

### Chapter 11: List Critical Business Metrics
- **Key insight:** Engineering evals and business metrics are different things. Start with accuracy metrics (false positive/negative, overall accuracy), add domain-specific outcome metrics (missed critical terms, dollar loss prevention), and optionally benchmark against human team performance for the same task.
- **Best practices:**
  - "False approvals" was the north star for a medical claims agent (customer is insurance companies).
  - Overall accuracy improved from 95% to 99% over the course of the project.
  - Human team metrics provide a natural benchmark: "Is the agent better than the humans doing this now?"
- **Anti-patterns:** Using only accuracy as the metric when domain-specific business outcomes matter more. Measuring what's easy instead of what drives business value.
- **Relevant to Lyra §4.21 Economics:** Business metrics must drive cost-efficiency decisions.
- **Relevant to Lyra §4.16 Reliability:** North star metrics define what reliability means.

### Chapter 12: Cross-Reference Failure Modes and Success Metrics
- **Key insight:** Plot failure modes on y-axis against north star metrics on x-axis. This cross-correlation reveals which failure modes actually impact business outcomes — turning metrics into actionable engineering work buckets. The workflow: SME review → PM prioritization → Engineer experimentation → PM validation.
- **Best practices:**
  - Four-phase improvement cycle: (1) SME reviews and classifies failures, (2) PM cross-references and sets targets (e.g., "reduce failure rate from 10% to 8% on clinical reasoning"), (3) Engineers iterate against failure-mode-specific datasets, (4) PM validates against past production data and makes go-live decision.
  - This creates a tight OODA loop: classify → target → fix → validate.
- **Anti-patterns:** Letting engineers decide which failures to fix without business context. Having evals without a process to turn them into engineering priorities.
- **Relevant to Lyra §4.16 Reliability:** The four-phase cycle is Lyra's continuous improvement loop.
- **Relevant to Lyra §4.25 Adversarial Panel:** SMEs in adversarial panel role.

### Chapter 13: Iterate Against Your Evals
- **Key insight:** Benchmarks are the difference between engineering and experimentation. Measure against a test dataset in CI to surface and guard against accuracy regressions. Establish standards: if a code change reduces accuracy, it must be paired with offsetting improvements.
- **Best practices:**
  - CI-integrated accuracy benchmarks.
  - Clear targets: "95% → 99% on clinical reasoning dataset."
  - Confidence that improvements are real, not random.
- **Anti-patterns:** Making agent changes without measuring against a held-out test set. Assuming "it felt better" means improvement.
- **Relevant to Lyra §4.16 Reliability:** CI-integrated evals are non-negotiable for production Lyra.
- **Relevant to Lyra §4.26 Harness Engineering:** Eval harness as part of the observability pipeline.

### Chapter 14: Create an Eval Test Suite
- **Key insight:** Like unit testing for traditional software, an eval test suite prevents regressions when adding new agent capabilities. Key components: benchmark dataset (synthetic or SME-labeled), metrics (relevancy, accuracy, domain-specific), and an eval runner using LLM-as-judge comparing outputs against baseline.
- **Best practices:**
  - Start with synthetic datasets, then replace with real production data from early users.
  - Use LLM-as-judge: one test running in a loop comparing agent answers to baseline on each criterion.
  - Create a "golden answer" dataset: input/output pairs from SMEs in a CSV.
  - Choose metrics that match your rubric: completeness, fairness, relevancy, accuracy.
- **Anti-patterns:** Relying on synthetic data indefinitely — it won't match the input distribution of real users. One-size-fits-all metrics that don't capture domain-specific quality dimensions.
- **Relevant to Lyra §4.16 Reliability:** Eval test suite is the foundation of Lyra's reliability infrastructure.

### Chapter 15: Have SMEs Label Data
- **Key insight:** Software engineers are the WORST candidates for labeling AI outputs in most domains (healthcare, legal, accounting, etc.). You need domain experts to create ground-truth datasets and periodically review production outputs. Structure: overall grade + category tags + optional subjective feedback.
- **Best practices:**
  - Use multiple annotators per data point; measure inter-rater reliability.
  - Provide an intuitive review UI: emails rendered as emails, full trace visible (user input, tool calls, LLM reasoning), non-critical details collapsed.
  - Include a "domain knowledge addition" button so SMEs can identify new failure modes the taxonomy missed.
  - SMEs should review both during prototyping (initial dataset) and in production (periodic sampling).
- **Anti-patterns:** Having engineers label medical/legal outputs. Outsourcing annotation to generalists who lack domain context. Using only automated evals without human review.
- **Relevant to Lyra §4.25 Adversarial Panel:** SME labeling is the adversarial review substrate.
- **Relevant to Lyra §4.19 Self-Knowledge:** Agent self-assessment should be benchmarked against SME labels.

### Chapter 16: Create Datasets from Production Data
- **Key insight:** Production data is messy, unstructured, and full of edge cases — exactly what synthetic data misses. Extract, curate, and structure production logs into versioned evaluation datasets. Store at cloud scale with observability tools. Three top-level fields: inputs, expected outputs, metadata.
- **Best practices:**
  - Log production generations; assess quality manually or with LLM-as-judge.
  - Store evaluation test cases in observability tools instead of managing large JSONL/CSV files.
  - Store human SME reviews (thumbs up/down) to find new test cases.
  - Version datasets to track quality changes over time.
- **Anti-patterns:** Using only early synthetic data for evals while users exercise wildly different query patterns. Not versioning datasets so you can't track accuracy trends.
- **Relevant to Lyra §4.16 Reliability:** Production-data-driven evals as the ultimate reliability signal.

### Chapter 17: Evaluate Production Data
- **Key insight:** Production data shifts over time — new user types, new query patterns, distribution drift. Combine eval test suite with live production data using LLM-as-judge for continuous evaluation. Scoring: prefer binary (pass/fail) or categorical (good/fair/poor) over numerical (1-10) — LLMs are better at literacy than numeracy.
- **Best practices:**
  - Define evaluation prompt with specific criteria; LLM judge scores system input/outputs.
  - Binary or categorical scoring strongly preferred over numerical.
  - Sample — don't evaluate every response.
  - Combine automated evaluation with human evaluation of live data.
- **Example:** Legal contract agent trained on NDAs but users threw international contracts at it. Production data evaluation + partner review identified gaps in cross-jurisdictional reasoning.
- **Relevant to Lyra §4.16 Reliability:** Continuous production evaluation is the closing loop.
- **Relevant to Lyra §4.19 Self-Knowledge:** LLM-as-judge is a form of self-knowledge.

---

## Part IV: SECURE YOUR AGENTS

**Intro:** Traditional security assumes humans click buttons, code runs deterministically, and access maps to roles. Agents break all three. Security through strategic constraints.

### Chapter 18: Prevent the Lethal Trifecta
- **Key insight:** Simon Willison's "lethal trifecta": (1) access to private data + (2) exposure to untrusted content + (3) external communication ability = prompt injection vulnerability. Remove any one leg to prevent attacks. This has been successfully exploited against Microsoft Copilot, Cursor, Jira, Zendesk, and major LLMs.
- **Best practices:**
  - The easiest leg to remove is the exfiltration vector — constrain agents so untrusted input can't trigger side-effect actions.
  - Add input processors (middleware for agent conversations) to intercept and sanitize messages before they reach the LLM.
  - GitHub MCP server example: malicious instructions in public issues can trigger data exfiltration via PR. Fix via input processors that strip instruction-bearing content from external inputs.
- **Anti-patterns:** Giving agents access to private data + untrusted content + ability to send data out — the full trifecta. Relying solely on model-level safety without infrastructure controls.
- **Relevant to Lyra §4.17 Safety:** The lethal trifecta is the organizing framework for Lyra's safety architecture.
- **Relevant to Lyra §4.12 Permissions:** Exfiltration prevention through granular access control.

### Chapter 19: Sandbox Code Execution
- **Key insight:** Code execution is one of the most powerful agent capabilities but also the most dangerous. Sandboxes must spin up fast (Docker's 10-20s cold start is too slow), run in isolation from production systems, and guard against resource hogging (memory, CPU, storage).
- **Best practices:**
  - Use agentic runtimes like E2B or Daytona with sub-second spin-up times.
  - Sandbox all code execution — server-side, not local.
  - Measure resource usage to guard against inadvertent resource hogging.
  - Long-running agent processes are legitimate; design sandboxes to accommodate them.
  - Anthropic's Code Interpreter: sandboxed server-side container for Claude Code.
  - Manus: 27 different tools all run in E2B sandbox with sub-second spin-up.
- **Anti-patterns:** Running agent-generated code unsandboxed on shared infrastructure. Using Docker directly for per-request sandboxes (cold start too slow). Not monitoring resource usage.
- **Relevant to Lyra §4.17 Safety:** Sandbox execution is mandatory for Lyra's code-executing agents.
- **Relevant to Lyra §4.26 Harness Engineering:** Sandbox infrastructure is a harness engineering concern.

### Chapter 20: Granular Agent Access Control
- **Key insight:** Agents are more diligent than humans at information gathering, so "security by obscurity" fails. They're also ephemeral and act with unpredictable behavior. Access control must be more granular for agents than humans: OAuth flows, per-tool-call permissions (not role-based), planning mode with lower permissions, just-in-time credential grants.
- **Best practices:**
  - OAuth flows for agents (easier as MCP adds elicitation support).
  - Access based on individual tool calls, not roles — credentials granted JIT based on task and user context.
  - A planning mode where the agent has programmatically lower permissions (e.g., no UPDATE/DELETE).
  - Replit added planning mode after an agent ignored instructions and altered the production database.
- **Anti-patterns:** Using human-style role-based access for agents. Long-lived, broadly-scoped API keys. Assuming agents will respect "don't do X" instructions without programmatic enforcement.
- **Relevant to Lyra §4.12 Permissions:** Granular per-tool access control is the target architecture.
- **Relevant to Lyra §4.14 Autonomy:** Planning mode as a permission tier.

### Chapter 21: Agent Guardrails
- **Key insight:** Evals are after-the-fact; guardrails are real-time, low-latency filters that prevent problematic inputs from reaching the LLM and harmful outputs from reaching users. Input guardrails: prompt injection, jailbreaking, PII, off-topic/brand protection. Output guardrails: data leakage, hallucination, bias, toxicity.
- **Best practices:**
  - Name guardrails by what they protect against: "prompt injection guard," "PII guard," "off-topic guard."
  - Input guardrails are generally only required for user-facing agents.
  - Custom guardrails for brand safety (e.g., prevent Toyota agent from discussing other car brands).
  - When output streaming: inspect each chunk, then inspect the complete output afterward.
  - On guardrail trigger: retry generation a set number of times to produce safer output.
- **Anti-patterns:** Guardrails only in eval (post-hoc), none in production (real-time). Not testing guardrails against adversarial inputs. Assuming model-level safety is sufficient.
- **Example:** DeepSeek output guardrail activated mid-response when a user prompt-injected to spell TIANANMEN SQUARE — the model erased its response and defaulted to a predefined nonresponse.
- **Relevant to Lyra §4.17 Safety:** Agent guardrails are the real-time safety layer.
- **Relevant to Lyra §4.10 Hooks:** Guardrails as hook-based pre/post processors.

---

## Part V: THE FUTURE OF AGENTS

### Chapter 22: What's Next(ish)
- **Key insight:** Three trends for the next 6-12 months (from October 2025): (1) simulations to find optimal agent parameters when eval harnesses are strong, (2) agent learning — agents getting better at their 1,000th task vs. their 1st (currently not true), (3) synthetic eval generation — automating the tedious human-intensive eval creation process with specialized eval-writing agents.
- **Thesis:** Compute will continue to increase exponentially; compute cycles will be thrown at increasing agent accuracy. 2025-2035 is Karpathy's "decade of agents."
- **Relevant to Lyra §4.27 RL Optimizer:** Simulations for parameter optimization are the RL optimizer's domain.
- **Relevant to Lyra §4.24 Dreaming:** Agent learning during idle time.
- **Relevant to Lyra §4.16 Reliability:** Synthetic eval generation as a reliability infrastructure concern.

---

## Appendix: Cross-Cutting Themes

### Theme 1: Patterns, Not Principles
The book distinguishes itself from its predecessor "Principles of Building AI Agents" — principles are conceptual (what to build), patterns are pragmatic (how to build). Principles get through the first weeks; patterns are desk reference material until internalized.

### Theme 2: The Contested Patterns
Two patterns are explicitly marked as contested:
1. **Parallel vs. Sequential:** Devin avoids parallelization; Claude Code relies on it. Answer depends on task decomposability and whether subagents share context.
2. **Context Sharing:** Devin carefully shares context; Claude Code uses subagents without sharing context. Answer depends on whether subtasks are interdependent.

### Theme 3: Real Production Data Over Synthetic
Every chapter on evaluation emphasizes the transition from synthetic → production data. Synthetic data is for bootstrapping; production data is for accuracy under real-world distributions.

### Theme 4: The 125K Token Reality
Context windows may be 500K+ tokens, but effective context is ~125K tokens before degradation begins. The Google Gemini Pokemon agent benchmark found this threshold empirically. This contradicts "just dump everything in" intuition.

### Theme 5: Infrastructure-Scale Thinking
Security (sandboxes, granular access, guardrails) and evals (test suites, SME labeling, production datasets) both require infrastructure-scale investment. These are not afterthoughts — they are primary engineering concerns comparable to the agent logic itself.
