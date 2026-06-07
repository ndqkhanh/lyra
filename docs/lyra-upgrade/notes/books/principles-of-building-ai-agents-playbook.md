# Principles of Building AI Agents — Best Practices Playbook

## Practice 1: Design Tools Like an Analyst, Not a Programmer
- **What:** Before writing any code, list out every tool your agent needs and map each to a specific, reusable operation. Think "what would a human analyst do step-by-step?" and encode each step as a tool with clear descriptions of both what it does AND when to call it.
- **Why:** This was the book's single most emphasized practice. Alana's book recommendation agent failed when dumping raw data into context but succeeded brilliantly when each analytical operation became a dedicated tool. "Think like an analyst. Break your problem into clear, reusable operations. Write each as a tool. If you do this, your agent will be much more capable, reliable, and useful."
- **Lyra route:** §4.7 (Plugins/Tools)
- **Source:** Chapter 6

## Practice 2: One LLM Call Per Workflow Step
- **What:** When building graph-based workflows, decompose steps so the LLM only does ONE thing at a time. Never put more than one LLM call in any single step. Compose steps so each step's input/output is independently meaningful (visible in tracing).
- **Why:** This maximizes predictability when agents alone aren't reliable enough. It also makes debugging tractable — each step's I/O is independently inspectable in traces. The book's medical record example: checking 12 symptoms in one call is unreliable; 12 parallel single-symptom calls is robust.
- **Lyra route:** §4.1 (Fleet Orchestration / Dynamic Workflow Engine)
- **Source:** Chapter 13

## Practice 3: Start Simple with RAG — Full Context First, Then Tools, Then RAG
- **What:** Follow a strict escalation hierarchy: (1) throw entire corpus into the largest context window available (Gemini 2M tokens), (2) write functions to access dataset and bundle in MCP server, (3) consider advanced pre-processing (ReAG with 10x LLM budget, async), (4) only then build a full RAG pipeline. "We're engineers. And engineers can over-engineer things. With RAG, you should fight that tendency."
- **Why:** Each step adds complexity and maintenance burden. Many use cases are solved by step 1 or 2. RAG pipelines have many tunable parameters (chunking strategy, embedding model, reranker) — optimize those before reaching for graph databases or LLM-generated metadata.
- **Lyra route:** §4.15 (Research / Ingestion)
- **Source:** Chapter 20

## Practice 4: Deliberately Prune Context with Memory Processors
- **What:** Use memory processors to modify retrieved messages before they reach the LLM. Employ `TokenLimiter` (count tokens, remove oldest until under limit) to prevent context overflow errors. Use `ToolCallFilter` (strip verbose tool call history) to save tokens and force agents to re-call tools rather than relying on stale cached results.
- **Why:** "Sometimes increasing your context window is not the right solution. It's counterintuitive but sometimes you want to deliberately prune your context window." Larger context windows create cost and distraction problems. Pruning is a precision tool for quality and cost.
- **Lyra route:** §4.2 (Memory) and §4.3 (Context)
- **Source:** Chapter 7

## Practice 5: Observability Is Non-Negotiable — The Question Is Not IF but WHEN
- **What:** Because LLMs are non-deterministic, your application WILL go off the rails. The question is when and how much. Emit OpenTelemetry (OTel) traces for every step of every run of every workflow. In production, inspect input/output JSON at each step. Integrate evals into the trace view for side-by-side comparison.
- **Why:** Teams that ship agents to production unanimously emphasize this. Without per-step I/O visibility, debugging agent failures is guesswork. The OTel standard ensures portability across observability vendors.
- **Lyra route:** §4.16 (Reliability) and §4.19 (Harness Engineering)
- **Source:** Chapter 16

## Practice 6: Use Cascaded Voice Pipeline, Not End-to-End Realtime S2S
- **What:** For voice agents in production (as of 2025), use STT → LLM → TTS pipeline rather than end-to-end speech-to-speech models. Speech-to-speech is not production-ready: audio info density is 1/1000 of text, turn-taking detection is unsolved, and latency makes demos better than deployments.
- **Why:** "While these products make great demos, there are not too many companies using realtime voice in production." Cascaded pipelines are simpler, more reliable, and benefit from mature STT/TTS models. Gate S2S adoption on <200ms latency being achievable.
- **Lyra route:** §4.18 (Voice)
- **Source:** Chapter 32

## Practice 7: Deploy on Container Services, Not Serverless
- **What:** Agent workloads are long-running (like Temporal/Inngest durable execution) but tied to user requests. Serverless platforms (Lambda, Vercel functions) hit function timeouts, bundle size limits, and incomplete runtime support. Use container services (AWS EC2, Digital Ocean) with auto-scaling for production. "The agent teams sleeping the soundest at night are the ones who figure out how to run their agents using auto-scaling managed services."
- **Why:** "In May 2025, we're still generally in the Heroku era of agent deployment." Agent workloads don't fit the request/response serverless model. Long-running processes with streaming, tool calls, and human-in-the-loop pauses require durable execution patterns.
- **Lyra route:** §4.19 (Harness Engineering / Deployment)
- **Source:** Chapter 31

## Practice 8: Middleware Is the Security Perimeter, Not the Agent's Inner Loop
- **What:** Place guardrails (input sanitization, PII detection, off-topic filtering, prompt injection defense), authentication, and authorization in middleware — the perimeter around the agent, not inside the agent's inner loop. Two-layer permissions: (1) which resources the agent accesses, (2) which users access the agent.
- **Why:** Because agents are more powerful than pre-LLM data access patterns, you need more rigorous permissioning. "Security through obscurity becomes less of a viable option when users can ask an agent to retrieve knowledge hidden in nooks and crannies." Models are improving at resisting prompt injection, but middleware is still essential.
- **Lyra route:** §4.17 (Safety)
- **Source:** Chapter 9

## Practice 9: Run A/B Tests on User Metrics — Evals Alone Are Insufficient
- **What:** After launching, run live A/B experiments comparing agent versions on real user behavior metrics. Leaders at Perplexity and Replit "joke that they rely more on A/B testing of user metrics than evals per se." With enough traffic, agent quality degradation becomes quickly visible. Complement with human review of production traces for nuanced correctness aspects.
- **Why:** Evals give scores between 0 and 1 with inherent randomness. They're like performance testing in CI — correlated with quality but imperfect. "Many correctness aspects (e.g., subtle domain knowledge, or an unusual user request) can't be fully captured by rigid assertions, but human eyes catch these nuances."
- **Lyra route:** §4.16 (Reliability / Verification)
- **Source:** Chapter 29

## Practice 10: Multi-Agent Design Is Organizational Design
- **What:** Design multi-agent systems like you'd design a team: group related tasks into job descriptions where you could plausibly recruit someone. Give creative/generative tasks to one agent, review/analytical tasks to another. Start with the simplest version (two agents, supervisor pattern) and only add complexity when proven necessary.
- **Why:** "We often joke that designing a multi-agent system involves a lot of skills used in organizational design." The Replit agent product already uses this pattern (planner → code manager → writer + sandbox + reviewer). Design patterns are fractal — a hierarchy is just a supervisor of supervisors. But "start with the simplest version first."
- **Lyra route:** §4.1 (Fleet Orchestration)
- **Source:** Chapters 21-25

## Practice 11: Always Sandbox Generated Code
- **What:** When building code-generation agents, always execute generated code in a sandboxed environment. Provide agents access to linters, static type checkers, and analysis tools for ground-truth feedback. Create feedback loops: agent writes code → runs it → reads errors → retries.
- **Why:** "This prevents the agent from accidentally (or maliciously) running dangerous commands on your machine (like `rm -rf /`)." Code analysis tools provide deterministic feedback in an otherwise non-deterministic system, dramatically improving code quality.
- **Lyra route:** §4.17 (Safety) and §4.1 (Fleet / Worktree isolation)
- **Source:** Chapter 33

## Practice 12: Don't Roll Your Own MCP — Use a Framework
- **What:** MCP provides a USB-C-like universal adapter for agent-tool communication. Use it for third-party integrations. But don't implement the MCP spec yourself — "There's alpha in playing around with MCP, but you probably don't want to roll your own, at least not right now. Look for a good framework or library in your language."
- **Why:** The MCP spec is long, each provider has its own config schema, and clients don't always implement the spec completely. Cursor and Windsurf implement MCP clients differently, creating subtle bugs. Registry fragmentation and lack of quality scoring (no npm-like verification badges) add risk. Framework abstractions handle this complexity.
- **Lyra route:** §4.7 (Plugins / MCP integration)
- **Source:** Chapter 11

## Practice 13: Evals Should Test Tools, Prompts, AND End-to-End Behavior
- **What:** Build a layered eval suite: tool usage evals (did the agent call the right function? analogous to `expect(Fn).toBeCalled`), prompt engineering evals (sensitivity to variations, robustness to adversarial input), textual evals (hallucination, faithfulness, completeness, tone, alignment), and end-to-end behavior evals. For workflows, test each step individually first.
- **Why:** Different eval types catch different failure modes. Tool usage evals catch the most common agent failures. Prompt engineering evals catch injection vulnerabilities. Textual evals assess output quality. No single eval type is sufficient.
- **Lyra route:** §4.16 (Reliability / Verification)
- **Source:** Chapters 28-29

## Practice 14: Use Reasoning Models as "Report Generators" with Many-Shot Prompting
- **What:** Reasoning models (o1, o3, Claude with extended thinking) are not chat models — treat them as "report generators." Give them massive context up-front via many-shot prompting. "If you do that, they can return high-quality responses. If not, they will go off the rails."
- **Why:** Reasoning models need extensive examples and context to produce quality output. With good context, they produce "surprisingly smart, high-quality answers to tough questions." Without it, they ramble or hallucinate. The trick is the same as always: "the more you help them up front, the better their reasoning gets."
- **Lyra route:** §4.5 (Routing) and §4.8 (Prompts)
- **Source:** Chapter 2

## Practice 15: Streaming Is Critical UX, Not a Nice-to-Have
- **What:** Stream not just LLM output tokens, but updates from each step in multi-step workflows (agent searching, planning, summarizing in sequence). Use reactive tools (ElectricSQL, Turbo Streams) to sync backend progress directly to UI. Provide escape hatches for partial results when functions are stuck.
- **Why:** Streaming makes agents "feel faster and more reliable, even if the backend is still working hard." The OpenAI o1 pro example (spinning box for 3 minutes, no feedback) vs. Deep Research (streaming updates as it found results) shows the UX gap is enormous. Users want to see progress, not a blank screen.
- **Lyra route:** §4.18 (Voice/Real-time) and §4.19 (CLI/UX)
- **Source:** Chapter 15
