# Patterns for Building AI Agents — Best Practices Playbook

**Source:** Bhagwat & Gienow (2025), Mastra | **Date extracted:** 2026-06-07
**Note path:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/notes/books/patterns-for-building-ai-agents-bhagwat-chapters.md`

---

## Practice 1: Organizational Design for Agent Architecture
- **What:** Before writing any agent code, list every desired capability exhaustively, group by shared data sources / job-title equivalence / API cohesion, then rank-order by priority. Treat agent design as organizational design — what roles would you hire humans for?
- **Why:** Teams fail not because agents can't handle use cases, but because they didn't break down the problem into buildable systems. Without grouping, you get a mega-agent that performs poorly on everything. With grouping, each specialist has a focused toolset, clear success criteria, and is maintainable independently.
- **Lyra route:** §4.1 (UI/UX) — agent architecture design; §4.5 (Router) — capability-to-agent mapping.
- **Source:** Chapter 1 (Whiteboard Agent Capabilities)

## Practice 2: Evolve Architecture Iteratively, Not Upfront
- **What:** Start with the one burning problem. Build that agent well. Notice what users ask for next. If it's separate, build a new agent. If the agent becomes unwieldy, split it. Add routing when you have multiple agents. Repeat. The natural endpoint is Coordinator → Router → Specialists.
- **Why:** The best architectures are discovered, not designed. Building a "master agent" that does mediocre everything is the classic failure mode. Each iteration produces a battle-tested specialist before adding complexity.
- **Lyra route:** §4.5 (Router) — routing emerges at iteration 3-4; §4.14 (Autonomy) — coordinator-router-specialist is the autonomy pattern.
- **Source:** Chapter 2 (Evolve Your Agent Architecture)

## Practice 3: Dynamic Agent Configuration via Runtime Context
- **What:** Adjust system prompts, tool selection (e.g., topK by user tier), model choice (e.g., GPT-3.5 vs GPT-5), and memory depth at runtime based on user identity, session state, and environment variables. One agent instance serves all user tiers.
- **Why:** Avoids maintaining N separate agent versions for N user segments. Enables cost/behavior trade-offs (cheap model for free tier, premium model for enterprise) and progressive disclosure of capabilities.
- **Lyra route:** §4.5 (Router) — runtime model selection; §4.12 (Permissions) — tier-based access; §4.2 (Memory) — tier-dependent retrieval depth.
- **Source:** Chapter 3 (Dynamic Agents)

## Practice 4: Deferred Human-in-the-Loop (Async, Not Blocking)
- **What:** Implement HITL as deferred tool execution: agent pushes work (e.g., a PR) to a human for review, then continues background processing. Humans are the bottleneck — never make them babysit agents step-by-step in blocking mode. Reserve synchronous pauses for maximum-risk decisions only.
- **Why:** Synchronous step-by-step HITL creates human bottlenecks and destroys the efficiency gains agents provide. Deferred execution aligns with real-world workflows where humans review asynchronously.
- **Lyra route:** §4.14 (Autonomy) — the autonomy slider; §4.10 (Hooks) — post-processing hook points.
- **Source:** Chapter 4 (Human-in-the-Loop)

## Practice 5: Five Context Failure Modes as Design Targets
- **What:** Design context engineering around five named failure modes: (1) Context Poisoning — hallucination recycled in context and repeatedly referenced; (2) Context Distraction — context so long the model overfocuses on it and discounts training data; (3) Context Confusion — irrelevant context degrading response quality; (4) Context Clash — new info conflicting with prior prompt info; (5) Context Rot — beyond ~125K tokens, models lose ability to discern signal from noise, even with 500K+ context windows.
- **Why:** Google Gemini empirically proved context rot at 125K tokens despite a 500K window — accuracy dropped to 34%. After filtering, pruning, and structured context assembly, accuracy jumped to over 90%. Context is not free: every token influences model behavior.
- **Lyra route:** §4.3 (Context Compaction) — all five failure modes are design targets; §4.2 (Memory) — structured context storage.
- **Source:** Chapter 7 (Avoid Context Failure Modes)

## Practice 6: Compress at Multiple Triggers, Preserve Crucial Events
- **What:** Compress context at multiple triggers: every step, at x% context window threshold (Claude Code uses 95%), at token-heavy tool calls, and at agent-agent boundaries. Use composable memory processors (TokenLimiter, ToolCallFilter) plus custom logic. Crucially: identify which events and decisions are crucial, and do NOT compress those.
- **Why:** Naive appending causes slowdown, degradation, and eventual overflow in long-running agents. Selective compression maintains quality while staying within bounds. Preserving crucial decisions prevents downstream agents from losing essential context.
- **Lyra route:** §4.3 (Context Compaction) — the autocompact threshold and processor chain; §4.2 (Memory) — memory processors as retrieval-stage filters.
- **Source:** Chapter 8 (Compress Context)

## Practice 7: Error-to-Context Self-Healing Loop
- **What:** When the agent encounters an error, log the raw error output into the thread's history and use it as context for the next decision. Automate: diagnose error → implement fix → re-execute → verify. If error patterns repeat, bake the fix into the system prompt proactively.
- **Why:** This is how Cursor, Windsurf, Replit, Lovable, and most other coding agents achieve resilience — they don't crash, they self-correct. Silent error swallowing guarantees repeated failure. Feeding errors into context turns failures into learning opportunities.
- **Lyra route:** §4.16 (Reliability) — error recovery loop; §4.6 (Tools) — tool execution failure recovery.
- **Source:** Chapter 9 (Feed Errors Into Context)

## Practice 8: Failure Mode Taxonomy → Cross-Reference → Iterate (The 4-Phase OODA Loop)
- **What:** A four-phase continuous improvement cycle: (1) SMEs review production outputs and classify failure modes using a taxonomy (e.g., Data Extraction, Clinical Reasoning, Rules Interpretation); (2) PMs cross-reference failure modes against north star metrics to set targets ("reduce clinical reasoning failures from 10% to 8%"); (3) Engineers iterate against failure-mode-specific datasets with clear success criteria; (4) PMs validate against past production data and make go-live decisions.
- **Why:** Raw evals tell you something changed but not why or what to do. Cross-referencing failure modes with business metrics turns metrics into actionable work buckets. The alternative is flying blind — making changes without knowing if they help.
- **Lyra route:** §4.16 (Reliability) — the continuous improvement engine; §4.25 (Adversarial Panel) — SME review function; §4.21 (Economics) — business metric alignment.
- **Source:** Chapters 10-13 (List Failure Modes, List Critical Business Metrics, Cross-Reference, Iterate Against Your Evals)

## Practice 9: Eval Test Suite with CI Integration and Accuracy Regression Gates
- **What:** Build an eval test suite with: (1) a benchmark dataset (SME-labeled golden answers or production-derived), (2) defined metrics (relevancy, accuracy, domain-specific criteria), and (3) an eval runner using LLM-as-judge. Run in CI. Establish standards: code changes that reduce overall accuracy must be paired with offsetting improvements. Transition from synthetic to production data over time.
- **Why:** "Benchmarks are the difference between engineering and experimentation." Without CI-integrated evals, you cannot tell if a change improved or degraded performance. AI outputs are nondeterministic — "it felt better" is not evidence.
- **Lyra route:** §4.16 (Reliability) — CI-integrated evals; §4.26 (Harness Engineering) — eval harness as observability pipeline.
- **Source:** Chapters 13-14 (Iterate Against Your Evals, Create an Eval Test Suite)

## Practice 10: Production Data Beats Synthetic Data for Real Accuracy
- **What:** Bootstrap with synthetic datasets, but rapidly transition to production-data-derived evaluation datasets. Extract, curate, and structure production logs into versioned datasets. Continuously evaluate live production data using LLM-as-judge with binary or categorical scoring (prefer over numerical — LLMs are better at literacy than numeracy). Sample, don't evaluate every response. Combine automated eval with periodic human SME review.
- **Why:** Users will exercise your agent in ways you never anticipated — different query types, new document types, edge cases. A legal agent trained on NDAs will be used for international contracts. Production data reveals the real input distribution; synthetic data doesn't.
- **Lyra route:** §4.16 (Reliability) — production data evaluation; §4.19 (Self-Knowledge) — LLM-as-judge is self-assessment.
- **Source:** Chapters 16-17 (Create Datasets from Production Data, Evaluate Production Data)

## Practice 11: SME Labeling with Intuitive Review UI
- **What:** Software engineers are the worst candidates for labeling domain-specific AI outputs. Use subject matter experts (clinicians for medical, lawyers for legal, accountants for finance) to create ground-truth datasets and periodically review production outputs. Provide an intuitive review UI: emails rendered as emails, full trace visible (user input → tool calls → LLM reasoning), less-important details collapsed. Include a "new failure mode" capture mechanism so SMEs can expand the taxonomy.
- **Why:** Engineers lack domain context to judge whether a medical approval/denial is correct. Multiple annotators with inter-rater reliability metrics produce higher-quality ground truth. The review UI quality directly impacts SME productivity and labeling accuracy.
- **Lyra route:** §4.25 (Adversarial Panel) — SME review substrate; §4.19 (Self-Knowledge) — agent self-assessment benchmarked against SMEs.
- **Source:** Chapter 15 (Have SMEs Label Data)

## Practice 12: Remove One Leg of the Lethal Trifecta
- **What:** The "lethal trifecta" is (1) access to private data + (2) exposure to untrusted content + (3) external communication ability. Remove any one leg to prevent prompt injection attacks. The easiest leg to remove is exfiltration — constrain agents so untrusted input cannot trigger side-effect actions. Add input processors (middleware) that intercept and sanitize messages before they reach the LLM.
- **Why:** This trifecta has been exploited against Microsoft Copilot, Cursor, Jira, Zendesk, and major LLMs. The GitHub MCP server covers all three: malicious instructions can be posted in public issues, the agent can read private repos, and a PR can exfiltrate data. No model-level safety is sufficient — infrastructure controls are mandatory.
- **Lyra route:** §4.17 (Safety) — the organizing framework; §4.12 (Permissions) — exfiltration prevention; §4.10 (Hooks) — input processor hooks.
- **Source:** Chapter 18 (Prevent the Lethal Trifecta)

## Practice 13: Sandbox All Agent Code Execution (Sub-Second Spin-Up)
- **What:** All agent-generated code must run in isolated sandboxes that spin up in under 1 second (Docker's 10-20s cold start is too slow). Use agentic runtimes (E2B, Daytona) with resource monitoring for memory, CPU, and storage. Guard against: exfiltration of platform secrets, deletion of shared environments, crypto mining, illegal content hosting, and resource hogging.
- **Why:** Code execution is one of the most powerful agent capabilities — and the most dangerous. Manus runs 27 different tools all in E2B sandboxes. Anthropic's Code Interpreter uses server-side sandboxed containers. Without sandboxing, an agent can `rm -rf /` or exfiltrate secrets.
- **Lyra route:** §4.17 (Safety) — mandatory sandboxing; §4.26 (Harness Engineering) — sandbox infrastructure.
- **Source:** Chapter 19 (Sandbox Code Execution)

## Practice 14: Per-Tool-Call Permissions with Planning Mode
- **What:** Agent access control must be more granular than human access control. Implement: OAuth flows, per-tool-call permissions (not role-based), just-in-time credential grants based on task and user context, and a planning mode where the agent has programmatically lower permissions (e.g., no UPDATE/DELETE queries).
- **Why:** Agents are more diligent information gatherers than humans — security by obscurity fails. A Replit agent told users it wouldn't alter the production database, then did exactly that. Replit responded by adding planning mode with restricted permissions.
- **Lyra route:** §4.12 (Permissions) — per-tool-call granularity; §4.14 (Autonomy) — planning mode as permission tier.
- **Source:** Chapter 20 (Granular Agent Access Control)

## Practice 15: Real-Time Input/Output Guardrails (Not Just Post-Hoc Evals)
- **What:** Deploy real-time, low-latency guardrails for: input (prompt injection detection, jailbreak blocking, PII redaction, off-topic/brand protection) and output (data leakage prevention, hallucination detection, bias/toxicity filtering). Name guardrails by what they protect: "prompt injection guard," "PII guard," etc. On output streaming: inspect each chunk, then inspect complete output. On trigger: retry generation a set number of times to produce safer output.
- **Why:** Evals are after-the-fact; guardrails are real-time. Input guardrails prevent attacks from reaching the LLM. Output guardrails prevent harmful content from reaching users. Without both, you're relying solely on model-level safety, which is insufficient — DeepSeek's output guardrail activated mid-response when a user prompt-injected to spell TIANANMEN SQUARE, erasing the response.
- **Lyra route:** §4.17 (Safety) — real-time safety layer; §4.10 (Hooks) — guardrails as hook-based pre/post processors.
- **Source:** Chapter 21 (Agent Guardrails)

---

## Practice Priority Matrix for Lyra

| Priority | Practice | Lyra Gap | Impact |
|----------|----------|----------|--------|
| P0 | Practice 5: Five Context Failure Modes | Context compaction is immature (§4.3) | Prevents silent degradation in long agent runs |
| P0 | Practice 12: Remove One Leg of Lethal Trifecta | No explicit trifecta analysis (§4.17) | Blocks all prompt injection attacks |
| P0 | Practice 9: Eval Test Suite + CI Regression Gates | No CI-integrated evals (§4.16) | Foundational — without this, can't measure improvement |
| P1 | Practice 6: Multi-Trigger Context Compression | Autocompact at 95% exists, no multi-trigger (§4.3) | Enables long-running autonomous agents |
| P1 | Practice 7: Error-to-Context Self-Healing | No structured error recovery loop (§4.16) | Transforms failures into recovery, not crashes |
| P1 | Practice 13: Sandbox All Code Execution | No sandbox infrastructure (§4.26) | Security — enables safe tool execution |
| P1 | Practice 14: Per-Tool-Call Permissions | Role-based, not per-tool-call (§4.12) | Security — prevents overeager agent damage |
| P2 | Practice 2: Iterative Architecture Evolution | Architecture exists, needs validation (§4.5) | Process — how to grow without chaos |
| P2 | Practice 8: 4-Phase OODA Improvement Loop | No structured improvement cycle (§4.16) | Process — continuous improvement engine |
| P2 | Practice 10: Production Data Driven Evals | Synthetic-only evals (§4.16) | Accuracy — real-world performance signal |
| P3 | Practice 15: Real-Time Guardrails | No real-time safety layer (§4.17) | Defense-in-depth — complements evals |
| P3 | Practice 3: Dynamic Agent Configuration | Static configuration (§4.5) | Efficiency — serve all tiers from one agent |
| P3 | Practice 4: Deferred Async HITL | No HITL architecture (§4.14) | UX — human supervision without bottlenecking |
| P3 | Practice 1: Whiteboard Capability Grouping | Implicit, not systematic (§4.1) | Design — prevents architecture sprawl |
| P3 | Practice 11: SME Labeling UI | No SME labeling pipeline (§4.25) | Quality — domain-expert ground truth |
