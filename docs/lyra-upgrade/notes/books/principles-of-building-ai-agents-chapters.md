# Principles of Building AI Agents — Chapter Notes

**Author:** Sam Bhagwat (Founder/CEO Mastra, ex-Gatsby co-founder)
**Year:** 2025 (2nd Edition, May 2025)
**Core Thesis:** Building AI agents is a pragmatic engineering discipline, not black magic. The core skill is decomposing problems into well-designed tools, composing them into structured workflows, and systematically evaluating quality with evals. Agents are a layer on top of LLMs — they execute code, store/access memory, and communicate with other agents. Start simple (throw context at it), then add structure (tools), then add reliability (workflows, evals).

**Target Audience:** Web developers and software engineers transitioning to AI agent engineering. Assumes JavaScript/TypeScript fluency. Written from a Mastra framework perspective but principles are framework-agnostic.

**Structure:** 34 chapters across 9 parts. ~130 pages. Intentionally "back-pocket sized."

---

## Part I: Prompting a Large Language Model (LLM)

### Chapter 1: A Brief History of LLMs
- **Key insight:** LLMs emerged from the 2017 "Attention is All You Need" paper (Google). The architecture predicts the next token. ChatGPT (Nov 2022) was the viral breakout moment.
- **Relevant to Lyra:** Background only. No actionable patterns.

### Chapter 2: Choosing a Provider and Model
- **Key insight:** Start prototyping with hosted APIs (OpenAI, Anthropic, Google) even if you plan to use open-source. Use a model routing library to avoid vendor lock-in.
- **Best practices:**
  - Start with more expensive/accurate models during prototyping; optimize cost later
  - Exploit large context windows (Gemini Flash 1.5 Pro: 2M tokens) for early prototyping to skip context selection work
  - Reasoning models (o1, o3, Claude with extended thinking) are "report generators" — they need massive context up-front via many-shot prompting; without it, they "go off the rails"
- **Anti-patterns:** Prototyping with open-source models first — you'll debug infra instead of iterating on code
- **Relevant to Lyra §4.5 (Routing):** Model routing abstraction is essential. The book's recommendation to use a routing library matches Lyra's "cache-hit routing to cheap model; difficulty estimation for escalation" pattern.

### Chapter 3: Writing Great Prompts
- **Key insight:** Prompts are engineering artifacts, not casual conversation. Production prompts are "very detailed" (the book shows ~1/3 of a real bolt.new code-gen prompt as an example).
- **Best practices:**
  - Few-shot > single-shot > zero-shot: more examples = more precision, at the cost of token budget
  - "Seed crystal" approach: ask the same model to generate prompts for itself, then refine (Claude generates best prompts for Claude, GPT-4o for GPT-4o)
  - System prompt shapes tone/voice but rarely improves accuracy
  - Weird formatting tricks matter: CAPITALIZATION adds weight, XML-like structure improves instruction-following, Claude & GPT-4 respond better to structured prompts (task, context, constraints)
  - Test prompt variations with evals
- **Anti-patterns:** Assuming "the model will figure it out" from vague instructions
- **Relevant to Lyra §4.8 (Prompts):** Prompt CMS concept (Mastra built one into their local dev environment) maps to Lyra's need for prompt versioning and eval-driven iteration.

---

## Part II: Building an Agent

### Chapter 4: Agents 101
- **Key insight:** Agents are "AI employees rather than contractors" — they maintain context, have specific roles, and use tools. Agency is a spectrum (like self-driving car levels).
  - **Low autonomy:** Binary choices in a decision tree
  - **Medium autonomy:** Memory, tool calling, retry failed tasks
  - **High autonomy:** Planning, task decomposition, self-managed task queues
- **Best practices:** Focus on low-to-medium autonomy agents. High-autonomy agents are rare in production (as of May 2025).
- **Code example:** Mastra agent with persistent memory, model config, tool suite, workflow access.
- **Relevant to Lyra §4.1 (Fleet Orchestration):** The autonomy spectrum maps directly to Lyra's phased rollout: crash detection (low) → idle autonomy (medium) → background research (high).

### Chapter 5: Model Routing and Structured Output
- **Key insight:** Model routing is a cross-provider abstraction layer. Structured output (JSON schema) is essential for application integration.
- **Best practices:** Use structured output for extracting data from unstructured/semi-structured text (resumes, medical records, transcripts).
- **Relevant to Lyra §4.5 (Routing):** Directly confirms Lyra's routing architecture. The book uses vercel's AI SDK pattern; Lyra uses a similar abstraction.

### Chapter 6: Tool Calling
- **Key insight:** "Designing your tools: the most important step." The tool design is the hardest and most impactful part of agent engineering.
- **Best practices:**
  - Provide detailed descriptions in tool definition AND system prompt
  - Use specific input/output schemas
  - Use semantic naming (`multiplyNumbers` not `doStuff`)
  - "Describe both what it does AND when to call it"
  - **Critical pattern:** Write out the full list of tools before coding. Break the problem into clear, reusable operations — write each as a tool.
- **Case study — Alana's book recommendation agent:**
  - First attempt: dump all data into context window → agent couldn't reason structurally
  - Better approach: decompose into specific tools (corpus access, recommendations by investor, books by genre, sort by type)
  - Result: "agent could now intelligently analyze the corpus... just like a skilled human analyst"
  - **Takeaway:** "Think like an analyst. Break your problem into clear, reusable operations. Write each as a tool."
- **Anti-patterns:** Dumping raw data into context and hoping the agent figures it out; vague tool descriptions
- **Relevant to Lyra §4.7 (Plugins/Tools):** Directly validates Lyra's tool-first approach. The "think like an analyst" methodology is the book's strongest actionable pattern.

### Chapter 7: Agent Memory
- **Key insight:** Memory systems manage "longer-term context and historical interactions." Three-tier approach: working memory, hierarchical memory (recent + semantic recall), and memory processors.
- **Best practices:**
  - **Working memory:** Persistent user characteristics (like ChatGPT's memory of you). Stores long-term traits.
  - **Hierarchical memory:** Combine recent messages (sliding window `lastMessages`) with semantic recall (`semanticRecall` via RAG over past conversations). Set `topK` messages to retrieve; set `messageRange` for surrounding context.
  - **Memory processors:** Deliberately prune/control context before sending to LLM:
    - `TokenLimiter`: Count tokens, remove oldest messages until under limit (prevent context overflow errors)
    - `ToolCallFilter`: Strip tool calls from context to save tokens. Also useful to force agent to re-call tools instead of relying on cached results.
  - "As context windows continue to grow, developers often start by throwing everything in the context window and setting up memory later!" — pragmatically, many teams skip memory until they hit limits.
- **Anti-patterns:** Including verbose tool call history in every request (wasteful); never pruning context (hits limits); premature memory optimization when context windows are large enough
- **Relevant to Lyra §4.2 (Memory):** Directly maps to Lyra's layered memory approach. `TokenLimiter` ≈ Lyra's context budget management. `ToolCallFilter` ≈ Lyra's message pruning. Hierarchical memory ≈ Lyra's CraniMem (fast discrete) approach. The "start simple, add memory later" advice validates Lyra's phased rollout.

### Chapter 8: Dynamic Agents
- **Key insight:** Dynamic agents have runtime-configurable properties (instructions, model, tools) vs. static agents configured at creation time. This is a "tradeoff between predictability and power."
- **Best practices:**
  - Use dynamic agents when behavior needs to change based on user input, environment, or runtime context
  - Example: support agent that adjusts behavior based on user's subscription tier and language preferences
- **Relevant to Lyra §4.1 (Fleet):** Dynamic agent configuration maps to Lyra's need for per-worktree/per-session agent customization.

### Chapter 9: Agent Middleware
- **Key insight:** Middleware is the perimeter around the agent — the right place for guardrails, auth, and authorization. It's separate from the agent's inner loop.
- **Best practices:**
  - **Guardrails:** Sanitize input (prompt injection, PII requests, off-topic chats) and output
  - **Authentication/Authorization:** Two layers: (1) which resources the agent can access, (2) which users can access the agent
  - Models are improving at resisting prompt injection, but middleware perimeter is still essential
  - "Because agents are more powerful than pre-LLM data access patterns, you may need to spend more time ensuring they are permissioned accurately"
  - "Security through obscurity becomes less of a viable option when users can ask an agent to retrieve knowledge hidden in nooks and crannies"
- **Relevant to Lyra §4.9 (Commands) and §4.17 (Safety):** Middleware pattern directly supports Lyra's safety architecture. The two-layer permissioning model maps to Lyra's tool-gating and user-auth layers.

---

## Part III: Tools & MCP

### Chapter 10: Popular Third-Party Tools
- **Key insight:** Agents need browser automation (web scraping, computer use) and third-party integrations (email, calendar, CRM, HR, code). The ecosystem splits between developer-friendly ($10s-100s/month) and enterprise tools ($1000s/month).
- **Best practices:**
  - Browser tools face anti-bot detection, fragile setups (CSS changes break scrapers) — "just budget a bit of time for munging and glue work"
  - Use an "agentic iPaaS" (Composio, Pipedream, Apify) to avoid building bog-standard integrations for months
  - Tool hierarchy: cloud-based search APIs (Exa, Browserbase, Tavily) → open-source (Playwright) → agentic search (Stagehand, Browser Use)
- **Relevant to Lyra §4.7 (Plugins):** Integration strategy maps to Lyra's plugin architecture.

### Chapter 11: Model Context Protocol (MCP): Connecting Agents and Tools
- **Key insight:** MCP is "like a USB-C port for AI applications" — a universal adapter for tools. Proposed by Anthropic (Nov 2024), hit critical mass March 2025, supported by OpenAI and Google by April 2025.
- **Best practices:**
  - **MCP primitives:** Servers wrap tool sets (any language, communicate over HTTP). Clients (models/agents) query servers for available tools, request execution.
  - **When to use MCP:** If your roadmap has many third-party integrations (calendar, chat, email, web), build an MCP client to access them. If building tools for other agents, ship an MCP server.
  - **Ecosystem:** Vendors (Stripe) ship MCP servers; individual devs publish on GitHub; registries (Smithery, PulseMCP, mcp.run) catalogue and validate; frameworks (Mastra) provide abstractions.
- **Current challenges:**
  - **Discovery:** No centralized registry (fragmentation across registries). Anthropic working on a meta-registry.
  - **Quality:** No equivalent of npm's package scoring/verification badges yet.
  - **Configuration:** Each provider has its own config schema. Spec is long, clients don't always implement completely.
  - **Practical advice:** "There's alpha in playing around with MCP, but you probably don't want to roll your own... Look for a good framework or library in your language."
- **Relevant to Lyra §4.7 (Plugins):** Lyra's MCP-based plugin architecture directly aligns. The "don't roll your own MCP client" advice is important for Lyra's implementation.

---

## Part IV: Graph-Based Workflows

### Chapter 12: Workflows 101
- **Key insight:** "Graph-based workflows have emerged as a useful technique for building with LLMs when agents don't deliver predictable enough output." Sometimes you need to decompose a problem, define the decision tree, and have agents make binary decisions instead of one big decision.
- **Best practices:** Use workflows for: branching logic, parallel execution, checkpoints/suspend-resume, tracing.
- **Relevant to Lyra §4.1 (Fleet):** Workflow engine as architectural spine.

### Chapter 13: Branching, Chaining, Merging, Conditions
- **Key insight:** The four workflow primitives compose into any control flow pattern. Branching enables parallel LLM calls on the same input.
- **Best practices:**
  - **Branching:** Trigger multiple parallel LLM calls on same input (e.g., 12 parallel calls checking 12 symptoms in a medical record, instead of one call checking all 12 — "that's a lot to ask")
  - **Chaining:** `.then()` — each step waits for previous, has access to prior results via context
  - **Merging:** Converge parallel branches to combine results
  - **Conditions:** Define on the child step (not parent) for parallel execution semantics
  - "Decompose steps so the LLM only has to do ONE thing at ONE time. Usually no more than one LLM call in any step."
  - "Compose steps so input/output at each step is meaningful — you'll see it in your tracing"
  - Loops, retries, etc. are composed from these primitives
- **Relevant to Lyra §4.1 (Fleet Orchestration):** This is the architectural pattern for Lyra's dynamic workflow engine. "One LLM call per step" is a key constraint.

### Chapter 14: Suspend and Resume
- **Key insight:** Long-running workflows need persistence + resumption for human-in-the-loop and third-party dependencies.
- **Best practices:**
  - Don't keep a running process waiting for arbitrarily long third-party responses
  - Persist workflow state; provide `.suspend()` and `.resume()` functions
  - Watch for status changes and resume when ready
- **Relevant to Lyra §4.1 (Fleet):** Checkpoint/resume pattern for Lyra's long-running agent tasks, idle autonomy workflows.

### Chapter 15: Streaming Updates
- **Key insight:** Streaming is "critical for good UX in LLM apps." Users want to see progress, not a blank screen. It makes agents "feel faster and more reliable, even if the backend is still working hard."
- **Best practices:**
  - Stream LLM output tokens as they're generated (baseline)
  - Stream updates from each step in multi-step workflows (agent searching, planning, summarizing in sequence)
  - Use reactive tools (ElectricSQL, Turbo Streams) to sync backend updates directly to UI
  - Provide "escape hatches" — push partial results/progress updates even when functions are stuck waiting
  - **Case study:** OpenAI o1 pro showed a spinning box for 3 minutes (bad); Deep Research streamed back updates as it found results (good, felt "way snappier")
- **Anti-patterns:** Blocking the entire UI until the full response is ready
- **Relevant to Lyra §4.18 (Voice/Real-time):** Streaming UX patterns for Lyra's real-time interaction layer. Also relevant to Lyra's CLI interaction patterns.

### Chapter 16: Observability and Tracing
- **Key insight:** "Because LLMs are non-deterministic, the question isn't whether your application will go off the rails. It's when and how much." Teams that ship agents into production "talk about how important it is to look at production data for every step, of every run, of each of their workflows."
- **Best practices:**
  - Emit telemetry in **OpenTelemetry (OTel)** format — the industry standard trace format
  - **Trace view:** Shows latency of each step (parse_input, process_request, api_call, etc.)
  - **Input/output inspection:** View exact JSON inputs/outputs at each step for debugging
  - **Call metadata:** Status, start/end times, latency — key context for humans scanning anomalies
  - **Eval integration:** Side-by-side comparison of agent response vs. expected; overall score per PR (prevent regressions); score over time; filter by tags, run date
  - Need a cloud tool for production data; local tracing for development (Mastra does both)
- **Relevant to Lyra §4.16 (Reliability):** Observability as the foundation of reliability engineering. OTel emission is essential for Lyra's tracing infrastructure. The "not IF but WHEN and HOW MUCH" framing is foundational.

---

## Part V: Retrieval-Augmented Generation (RAG)

### Chapter 17: RAG 101
- **Key insight:** RAG pipeline: Chunk → Embed → Index → Query → (Rerank) → Synthesize. Each step has concrete implementation choices.
- **RAG pipeline steps:**
  - Chunking: Split documents into bite-sized pieces for search
  - Embedding: Transform text → vector (1536 dimensions, values 0-1), usually via OpenAI embeddings API or Voyage/Cohere
  - Indexing: Store vectors in a vector DB (pgvector, Pinecone, Chroma)
  - Querying: Compare query embedding to all chunks via cosine similarity (1536-dimensional search, like geospatial but in high dimensions)
  - Reranking: More computationally expensive post-processing to improve result ordering (run on top-K results, not full corpus)
  - Synthesis: Pass results as context to LLM for final answer
- **Relevant to Lyra §4.15 (Research):** RAG pipeline design for Lyra's research and ingestion subsystems.

### Chapter 18: Choosing a Vector Database
- **Key insight:** Vector DB feature set is "mostly commoditized" (as of 2025). The most important thing is preventing infra sprawl.
- **Best practices:**
  - If using Postgres already → pgvector (great choice)
  - New project → Pinecone (default, nice UI)
  - If cloud provider has managed vector DB → use that
  - Form factors: pgvector (OSS feature), Chroma (standalone OSS), Pinecone (standalone hosted), Cloudflare Vectorize/DataStax Astra (cloud-managed)
- **Relevant to Lyra §4.15:** Vector DB selection for Lyra's ingestion pipeline.

### Chapter 19: Setting Up Your RAG Pipeline
- **Key insight:** Chunking strategy and overlap window are the key choices. Good chunking balances context preservation with retrieval granularity.
- **Best practices:**
  - Chunking strategies: recursive, character-based, token-aware, format-specific (Markdown, HTML, JSON, LaTeX)
  - Hybrid queries: combine vector similarity + metadata filtering (dates, categories, custom attributes)
  - Start simple: "start by setting up a working pipeline and tweaking the normal parameters — embedding models, rerankers, chunking algorithms — first" before advanced techniques (LLM-generated metadata, graph databases)
  - One-time index setup: dimension size (match embedding model), similarity metric (cosine, euclidean, dot product)
- **Relevant to Lyra §4.15 (Research):** Chunking and hybrid query strategies for Lyra's SEMA-RAG approach.

### Chapter 20: Alternatives to RAG
- **Key insight:** "We're engineers. And engineers can over-engineer things. With RAG, you should fight that tendency. Start simple, check quality, get complex."
- **Three-tier approach (in order of preference):**
  1. **Full Context Loading:** Throw entire corpus into Gemini's 2M token context window. Simplest, most reliable. Limitations: cost, size constraints, potential distraction.
  2. **Agentic RAG:** Give agent tools to query data (market APIs, calculators, portfolio analysis) instead of searching documents. More precise than RAG (exact computation), but requires tool maintenance. Case study: investor built tools into an MCP server, gave to Windsurf agent.
  3. **Reasoning-Augmented Generation (ReAG):** Use 10x LLM budget to pre-process text asynchronously: high-temperature consensus checking, LLM-based metadata extraction, entity/relationship extraction. Asynchronous so latency doesn't matter.
  4. **Traditional RAG pipeline:** Only if #1-3 don't give good enough quality.
- **Relevant to Lyra §4.15 (Research):** This "start simple" hierarchy directly shapes Lyra's ingestion strategy. The book's advice to try full-context → agentic → ReAG → RAG maps to Lyra's grep-first → SEMA-RAG approach.

---

## Part VI: Multi-Agent Systems

### Chapter 21: Multi-Agent 101
- **Key insight:** Multi-agent systems are like specialized teams at a company. Design involves "a lot of skills used in organizational design." Replit agent is already a multi-agent system in production: planner → code manager → code writer + sandbox execution + error feedback loop.
- **Best practices:**
  - "Group related tasks into a job description where you could plausibly recruit someone"
  - Creative/generative tasks to one agent; review/analytical tasks to another
  - Consider network dynamics: three specialized agents gossiping to consensus vs. feeding output to a manager agent
  - "Start with the simplest version first"
  - Designs are fractal: "a hierarchy is just a supervisor of supervisors"
- **Relevant to Lyra §4.1 (Fleet Orchestration):** The organizational-design framing directly supports Lyra's fleet-centric architecture. "Start with the simplest version" validates phased rollout.

### Chapter 22: Agent Supervisor
- **Key insight:** The simplest multi-agent pattern: pass other agents as tools to a supervisor agent. Example: publisher agent supervising copywriter + editor agents.
- **Best practices:** Agent-as-tool is the most straightforward composability primitive.
- **Relevant to Lyra §4.1 (Fleet):** Supervisor daemon pattern maps to Lyra's fleet supervisor.

### Chapter 23: Control Flow
- **Key insight:** "Just as a project manager wouldn't start coding without a plan, agents should establish an approach before diving into execution." Align on architectural details first, add human checkpoints.
- **Best practices:** Engage agents on architectural details before execution; add human feedback checkpoints in workflows. This is the "planning agent" pattern from Replit/Lovable.
- **Relevant to Lyra §4.6 (Planning):** Control flow + human checkpoints maps to Lyra's PM agent and progressive disclosure.

### Chapter 24: Workflows as Tools
- **Key insight:** Multi-agent architecture is entirely about which primitive you're using and how you're arranging them. Workflows can be wrapped as tools for agents; tools can contain workflows. "All the primitives can be rearranged in the way you want, custom to the control flow you want."
- **Best practices:** For multi-step tasks, decompose each into individual workflows (with stipulated step order and structure), then pass workflows as tools to agents. "There's more certainty in doing it this way."
- **Relevant to Lyra §4.1 (Fleet):** This recursive composability (workflows-as-tools, tools-in-workflows) is Lyra's dynamic workflow engine design pattern.

### Chapter 25: Combining the Patterns
- **Key insight:** Production code-writing tools (Replit, Lovable) combine: planning agent (proposes architecture, gets user feedback) → code writing agents (writer + reviewer working together). Agents embody different steps in a workflow; workflows are steps (tools) for agents. These are inverse patterns — the primitives are rearrangeable.
- **Best practices:** Planning agent is "critical... if they're to create any good deliverables at all." User feedback loop between plan and execution is essential.
- **Relevant to Lyra §4.1 (Fleet) and §4.6 (Planning):** Directly validates Lyra's planning + execution agent separation.

### Chapter 26: Multi-Agent Standards
- **Key insight:** A2A (Google's Agent-to-Agent protocol) is for communicating with untrusted agents across organizational boundaries. MCP is for tool access; A2A is for agent-to-agent communication.
- **A2A mechanics:**
  - JSON metadata at `/.well-known/agent.json` (capabilities, endpoint URL, auth requirements)
  - Task queueing system: unique IDs, state machine (submitted → working → input-required → completed/failed/canceled)
  - Sync request-response AND streaming for long-running tasks (Server-Sent Events)
  - HTTP + JSON-RPC 2.0 with standard web auth (OAuth, API keys)
- **A2A vs. MCP:** A2A is younger; Microsoft supports it, OpenAI and Anthropic haven't. Possible they see MCP as competitive. "Expect one or multiple agent interoperability protocols from the big players to emerge."
- **Relevant to Lyra §4.1 (Fleet):** A2A for Lyra's cross-organizational agent communication. MCP+A2A duality maps to Lyra's plugin + fleet communication layers.

---

## Part VII: Evals

### Chapter 27: Evals 101
- **Key insight:** "While traditional software tests have clear pass/fail conditions, AI outputs are non-deterministic." Evals return scores between 0 and 1, not binary. Think of evals like performance testing in CI — some randomness, but correlation between test results and app quality over time.
- **Best practices:**
  - Unit-test-like evals (fast, might not capture right behavior) vs. E2E evals (right behavior, more flaky)
  - For RAG/workflow systems: test each step individually, then test system behavior as a whole
- **Relevant to Lyra §4.16 (Reliability):** Eval-first development methodology.

### Chapter 28: Textual Evals
- **Key insight:** Textual evals are "like a grad student TA grading your homework with a rubric — a bit pedantic, but they usually have a point."
- **Eval dimensions:**
  - **Accuracy & Reliability:** Hallucination detection (facts not in context), Faithfulness (accurate representation), Content similarity, Completeness, Answer relevancy
  - **Context Understanding:** Context position (should be at top), Context precision (logical grouping), Context relevancy, Contextual recall
  - **Output Quality:** Tone consistency, Prompt alignment (length, format, required elements), Summarization quality (retention, accuracy, conciseness), Keyword coverage
  - Toxicity & bias detection are "largely baked into leading models" — lower priority
- **Relevant to Lyra §4.16 (Reliability):** Eval rubric design for Lyra's verification subsystem.

### Chapter 29: Other Evals
- **Key insight:** Multiple eval types needed: classification/labeling, agent tool usage, prompt engineering, A/B testing, human data review.
- **Best practices:**
  - **Classification evals:** Accuracy of tagging/categorization (sentiment, topics, spam, entity extraction)
  - **Tool usage evals:** Measure how effectively agent calls external tools. Analogous to `expect(Fn).toBeCalled` in Jest.
  - **Prompt engineering evals:** Sensitivity to prompt variations, robustness to adversarial/ambiguous inputs. Prompt injection testing lives here.
  - **A/B testing:** Leaders at Perplexity and Replit "joke that they rely more on A/B testing of user metrics than evals per se." With enough traffic, agent quality degradation is quickly visible.
  - **Human data review:** High-performing teams regularly review production traces. "Many correctness aspects... can't be fully captured by rigid assertions, but human eyes catch these nuances."
- **Relevant to Lyra §4.16 (Reliability):** The A/B testing insight (user metrics > evals at scale) and human review practices map to Lyra's verification strategy. Tool usage evals map to Lyra's adversarial verification.

---

## Part VIII: Development & Deployment

### Chapter 30: Local Development
- **Key insight:** Agent development splits into frontend (chat interface, streaming, tool call display) and backend (where most complexity lives). Agent logic can't live client-side — it would leak API keys.
- **Best practices for local dev environment:**
  - **Agent Chat Interface:** Test conversations in browser, observe tool usage
  - **Workflow Visualizer:** Step-by-step execution, suspend/resume/replay
  - **Agent/workflow endpoints:** Curl-able localhost endpoints (enables Postman)
  - **Tool Playground:** Test tools directly, verify inputs/outputs without going through agent
  - **Tracing & Evals:** See inputs/outputs of each step, eval metrics as you iterate
- **Frontend frameworks for prototypes:** Assistant UI, Copilot Kit, Vercel AI SDK UI
- **Relevant to Lyra §4.19 (DX/Harness):** Local dev environment design for Lyra's harness engineering.

### Chapter 31: Deployment
- **Key insight:** "In May 2025, we're still generally in the Heroku era of agent deployment." Most teams: web server → Docker → auto-scaling platform.
- **Best practices:**
  - Agent workloads are long-running (like Temporal/Inngest durable execution) but tied to user requests
  - Serverless platforms struggle: function timeouts for long-running processes, bundle size issues, incomplete Node.js runtime support
  - Container services (AWS EC2, Digital Ocean) work for B2B use cases without sudden spikes
  - "The agent teams sleeping the soundest at night are the ones we see who figure out how to run their agents using auto-scaling managed services"
- **Relevant to Lyra §4.19 (Harness):** Deployment architecture for Lyra's fleet. Long-running agent workloads require durable execution patterns, not pure serverless.

---

## Part IX: Everything Else

### Chapter 32: Multimodal
- **Key insight:** Multimodal AI follows the same adoption curve as the internet and social media: text first, images later, video last. Voice and video are "younger and less mature... trickier to get right, and more computationally complex."
- **Image Generation:** Consumer breakthrough March 2025 (Ghibli-core). Use cases: marketing/e-commerce (mockups, try-on), game/film (asset prototyping, sketch-to-render).
- **Voice:**
  - Modalities: STT (speech-to-text), TTS (text-to-speech), S2S (speech-to-speech / realtime voice)
  - Realtime voice is challenging: audio info density is 1/1000 of text → more training data, more serving cost. Turn-taking ("voice activity detection") is hard — models lack visual/emotional cues, struggle with interruptions.
  - "While these products make great demos, there are not too many companies using realtime voice in production."
  - **Production pattern:** STT → LLM → TTS pipeline (not end-to-end S2S). Use one model to transcribe, another to generate response, a third to synthesize audio.
- **Video:** Not yet crossed from ML research into AI engineering. No "Ghibli moment" yet. Requires specialized knowledge and heavy GPU.
- **Relevant to Lyra §4.18 (Voice):** Directly validates Lyra's cascaded pipeline decision (VAD → cheap STT → LLM → fast TTS) over end-to-end S2S. The book's assessment that realtime voice isn't production-ready (May 2025) confirms Lyra's gating on <200ms latency.

### Chapter 33: Code Generation
- **Key insight:** Code generation agents unlock powerful workflows but require safety guardrails.
- **Best practices:**
  - **Feedback Loops:** Agent writes code → runs it → reads errors → tries again (iterative improvement)
  - **Sandboxing (CRITICAL):** "Always run generated code in a sandboxed environment. This prevents the agent from accidentally (or maliciously) running dangerous commands on your machine (like `rm -rf /`)."
  - **Code Analysis:** Give agents access to linters, static type checkers, analysis tools — "provides ground truth feedback and helps agents write higher-quality code"
- **Relevant to Lyra §4.1 (Fleet) and §4.17 (Safety):** Code generation safety directly shapes Lyra's sandboxed execution environment. Worktree isolation + sandboxing maps exactly to this pattern.

### Chapter 34: What's Next
- **Key insight:** The agent space is moving incredibly fast. Key trends:
  - Reasoning models will continue improving — but "what do agents built for reasoning models look like? We're not sure."
  - Agent learning: traces emit data, but feedback loops currently run through human programmers. Approaches being explored (SFT-as-a-service) but no clear winner.
  - Synthetic evals: auto-generating evals from tracing data with human approval.
  - Security will become more important: deployed agents will 10x-100x, and incidents will increase. (Written while reading about a GitHub MCP server vulnerability leaking private repos and API credentials.)
  - "The eternal September of AI will continue... In a field where the ground shifts constantly, we're all perpetual beginners."
- **Relevant to Lyra (Overall):** Security urgency validates Lyra's safety-first architecture. The agent learning trajectory maps to Lyra's Phase 4 self-evolution (parked for safety reasons).
