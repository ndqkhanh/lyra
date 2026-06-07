# Harness Engineering & Agent Infrastructure -- Thematic Synthesis

**Synthesis date:** 2026-06-07
**Sources audited:** 281 paper rigor notes, 80 book notes (40 chapters + 40 playbooks), 184 repo/doc notes
**Sources cited:** 22 papers, 2 books, 6 web notes

---

## 1. Frontier Techniques (ranked by evidence strength)

### Technique 1: The Continuous Query Loop with Formal State Management

- **Sources:** Harness Engineering: Claude Code, Ch.3 (book, chapters); Claude Code Definitive Guide, Practices 5, 6, 15 (book, playbook)
- **Mechanism:** The query loop (`queryLoop()`) is the execution center, not the model call. A formal state object maintains cross-iteration variables (messages, toolUseContext, autoCompactTracking, recoveryCount, turnCount, transition). Input governance happens BEFORE model invocation in a fixed pre-processing sequence: memory prefetch -> message slicing -> tool result budget -> history snip -> microcompact -> context collapse -> autocompact. Model output is consumed as an event stream (`for await`), enabling tool dispatch while streaming. Interrupt handling closes the ledger by injecting synthetic tool results for issued-but-unfinished calls. Seven distinct stop conditions distinguish completion, failure, recovery, and continuation.
- **Evidence:** This is reverse-engineered from Claude Code production source code (src/query.ts, src/QueryEngine.ts). The architecture has been battle-tested across millions of Claude Code sessions. Terminal-Bench 2.0 (2601.11868v1) validates the importance of harness quality: Claude Code + Claude Opus 4.5 achieves 52.1% resolution rate vs. same model + OpenHands at 51.9%, but Claude Code consumed 256.9M input tokens vs. 151.4M, suggesting the query loop's governance mechanisms produce meaningfully different efficiency profiles.
- **Maturity:** Production deployed (Claude Code, millions of sessions)

### Technique 2: Sandbox-Isolated Agent Execution Environments

- **Sources:** Claude Code Sandbox docs (web, Anthropic); OpenHands repository (web, All-Hands-AI); Terminal-Bench 2.0, 2601.11868v1 (paper); OSWorld, 2404.07972v2 (paper); Safety Survey, 2605.23989v1 (paper)
- **Mechanism:** Six tiers of isolation from per-command sandbox (Seatbelt on macOS, bubblewrap on Linux) to full VM. OpenHands separates app server from agent server, with the agent running inside Docker containers (or local processes, or remote hosts). Terminal-Bench 2.0 uses Docker containers with pinned dependencies and internet access, checking final container state (not agent trajectory). OSWorld uses full QEMU/KVM VMs with snapshot-based reproducibility. The key architectural pattern is that the sandbox boundary is an explicit system component, not an afterthought -- the agent runs in the sandbox, not on the host with sandboxed children.
- **Evidence:** OpenHands: SWE-bench 77.6% (reported on README badge). Terminal-Bench 2.0: 32,155 trials across 6 agents and 16 models, revealing that agent scaffolding quality yields up to 17 percentage point difference between agents using the same model (Gemini 2.5 Pro: 32.6% with Terminus 2 vs. 15.7% with OpenHands). Progent (2504.11703) demonstrates that without privilege control, ASR can reach 39.9% on AgentDojo; with sandboxing + policy enforcement, ASR drops to 1.0%.
- **Maturity:** Production deployed (Claude Code, OpenHands, Claude Code on the web)

### Technique 3: Least-Privilege Tool Access via Symbolic Policy Enforcement

- **Sources:** Progent, 2504.11703v3 (paper); Safety Survey, 2605.23989v1 (paper); Harness Engineering, Ch.4 (book, chapters)
- **Mechanism:** Tool calls are intercepted and checked against a security policy consisting of symbolic rules over tool names and arguments. Each rule `R ::= Effect t when {e_i}, fallback f` evaluates conditions over parameter values. An SMT solver (Z3) determines whether a proposed policy update is an expansion or narrowing. The allowed action space forms a monotonically decreasing sequence: `A(P_0) ⊇ A(P_1) ⊇ A(P_2) ⊇ ...`. Claude Code's permission model uses three-valued semantics (allow/deny/ask), with Bash receiving two dedicated governance layers (prompt guidance + permission/safety classification).
- **Evidence:** Progent on AgentDojo: ASR reduced from 39.9% to 1.0% (auto-approve) or 0.0% (manual approval), with utility maintained at 79.4% (identical to no-defense utility). On ASB benchmark: ASR reduced from 70.3% to 3.9%. Works across diverse agent LLMs (GPT-4o, Claude-Sonnet-4, Gemini-2.5-Flash, GPT-4.1, Meta-SecAlign-70B), all achieving <1.1% ASR. The SMT-based policy comparison is fully deterministic -- no ML heuristics.
- **Maturity:** Lab validated. Progent is a preprint (UC Berkeley/UCSB/NUS, 2025). The pattern mirrors Claude Code's production three-valued permission model.

### Technique 4: MCTS-Driven Agent Trajectory Search with Hindsight Feedback

- **Sources:** SWE-Search, 2410.20285v6 (paper); RAP, 2305.14992v2 (paper); AFlow, 2410.10762v4 (paper)
- **Mechanism:** Monte Carlo Tree Search wraps an LLM agent to enable non-linear exploration, backtracking, and iterative self-improvement. SWE-Search uses a modified UCT criterion: `UCT(s,a) = V(s,a) + C·√(ln N(s)/N(s,a)) + α·e^(-β(d-1)) - γ·√d` with an early depth bonus and late depth penalty. A Value Agent outputs both a scalar reward and natural language explanation; the explanation is injected as hindsight feedback when re-expanding from parent nodes. RAP repurposes the same frozen LLM as both world model and reasoning agent, using MCTS with four reward types (action likelihood, state confidence, self-evaluation, task-specific heuristics). AFlow uses MCTS to automatically discover agentic workflow architectures coded as Python classes.
- **Evidence:** SWE-Search on SWE-bench Lite (GPT-4o): +17% relative improvement (25.7% -> 31.0%). Average +23% across 5 diverse models. RAP on Blocksworld (LLaMA-33B): 0% -> 69% average success (surpasses GPT-4 CoT). AFlow: +5.7% over manually-designed workflows, +19.5% over ADAS, achieves GPT-4o-mini surpassing GPT-4o performance at 4.55% of the cost. However, cost multiplier is 5-14x for SWE-Search.
- **Maturity:** Lab validated (SWE-Search: ICLR 2025; RAP: EMNLP 2023; AFlow: preprint). Not production-deployed due to cost scaling.

### Technique 5: Deferred Capability Loading (Tool Search Pattern)

- **Sources:** Claude Code MCP docs (web, Anthropic); Harness Engineering, Ch.5 (book, chapters)
- **Mechanism:** At session start, only tool names and 2KB server instructions load into context. Full tool schemas are discovered on-demand via a semantic search tool when the LLM decides it needs a tool. Configurable modes: `true` (always defer), `auto` (load upfront if under 10% context window, defer otherwise), `auto:N` (custom threshold), `false` (load all upfront). Critical servers marked `alwaysLoad: true` bypass deferral. Dynamic tool updates via `list_changed` notifications allow mid-session capability changes.
- **Evidence:** This is production infrastructure in Claude Code (v2.1.121+). Numeric thresholds: tool descriptions truncated at 2KB, MCP output warning at 10K tokens, default max output 25K tokens, per-tool result ceiling 500K chars, automatic reconnection with exponential backoff (5 attempts, 1s-16s). These are empirically tuned production values, not research parameters.
- **Maturity:** Production deployed (Claude Code, millions of sessions)

### Technique 6: Structured Memory Graph with Community-Based Compression (Mind-Map)

- **Sources:** Agentic Reasoning, 2502.04644v2 (paper); AI for Auto-Research, 2605.18661v1 (paper)
- **Mechanism:** A knowledge graph is incrementally built from conversation turns via entity-relationship extraction. The Leiden algorithm partitions the graph into communities; each community is summarized by an LLM. When the reasoning agent becomes uncertain or lost in long chains, a GraphRAG retrieval over the knowledge graph returns relevant structured information. Unlike flat text memory, the graph preserves logical entity relationships that flat text loses. Community clustering + summarization provides compressed, queryable context that scales with reasoning length.
- **Evidence:** On the GAIA benchmark, Mind-Map achieves 66.13 average vs. 47.84 raw text memory, 49.83 ReadAgent, 53.49 MemoryBank, 55.10 MemGPT -- an 18-point improvement over flat memory. On the Werewolf game: 72% win rate with Mind-Map vs. 36% without. The core mechanism (Leiden community detection + LLM summarization + GraphRAG retrieval) is well-defined with open-source implementations available.
- **Maturity:** Lab validated (preprint 2025). Components are individually production-ready (GraphRAG by Microsoft, Leiden in python-igraph).

### Technique 7: Memory-Persisted Multi-Agent Orchestration with Interleaved Thinking

- **Sources:** Anthropic Engineering Blog (web, June 2025); Claude Code Definitive Guide, Practices 3, 4, 5, 10 (book, playbook)
- **Mechanism:** A LeadResearcher agent (Opus 4) saves plans to external Memory that survives context truncation, spawns parallel subagents (Sonnet 4) that independently search/evaluate, each returns only compressed findings. Subagents use interleaved thinking after tool results to evaluate quality and refine next queries. A CitationAgent processes final outputs. Heuristic effort-scaling: 1 agent for simple fact-finding (3-10 calls), 2-4 subagents for comparisons (10-15 calls each), >10 for complex research. Subagent output is persisted to filesystem artifacts; coordinator receives lightweight references, not full content dumps.
- **Evidence:** Multi-agent outperforms single-agent by 90.2% on Anthropic's internal research eval. Parallel subagent spawning cuts latency by up to 90%. A dedicated tool-testing agent that rewrites MCP tool descriptions yielded a 40% decrease in task completion time. Token cost is ~15x more than chat but economically justified for high-value tasks. The system is deployed in production at Anthropic with rainbow deployments, resume capability, and full production tracing.
- **Maturity:** Production deployed (Anthropic, at scale)

### Technique 8: Runtime Self-Inspection and Self-Healing via Monkey Patching

- **Sources:** Godel Agent, 2410.04444v4 (paper); Harness Engineering, Ch.6 (book, chapters)
- **Mechanism:** Four mandatory action primitives: `self_inspect` (introspect entire current algorithm from runtime memory), `interact` (measure policy performance on validation set), `self_update` (LLM generates replacement code applied via monkey patching), and `continue_improve` (recursive invocation for deeper optimization). The main function is recursive (not a loop), enabling modification of the main execution logic itself. Claude Code's recovery architecture provides the harness engineering counterpart: layered escalation (low-cost first, heavier last), circuit breakers (`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`), and anti-loop guards (`hasAttemptedReactiveCompact` flag).
- **Evidence:** Godel Agent (GPT-3.5 policy + GPT-4o optimizer): DROP 80.9%, MGSM 64.2%, MMLU 70.9%, GPQA 34.9% -- beating or matching Meta Agent Search on all 4 benchmarks at 20x lower cost ($15 vs $300). Ablation: -13.4% without thinking-before-acting, -14.8% without error handling, -7.1% without code running tool. However, 14% of optimization trials result in final performance worse than starting policy, and 4% of trials experience self-modification collapse. Claude Code's recovery layers have been hardened in production across millions of sessions.
- **Maturity:** Research concept (Godel Agent). The recovery architecture is production-deployed (Claude Code). Self-modifying code remains a research problem.

### Technique 9: Five-Stage Agent Lifecycle with Defense-in-Depth Assurance

- **Sources:** Safety Survey, 2605.23989v1 (paper); AI for Auto-Research, 2605.18661v1 (paper)
- **Mechanism:** The agent is analyzed across a five-stage lifecycle: Perceive -> Plan -> Act -> Reflect -> Learn. Each stage has distinct attack surfaces and mitigations. Safety is formalized via Constrained MDPs: `max_π J(π) s.t. J_ci(π) ≤ d_i`. A three-tier release gating system: Tier 0 (offline regression, CVR=0), Tier 1 (sandbox stress, CER<0.1%), Tier 2 (canary with auto-rollback). Process metrics (CVR for constraint violation rate, DCR for trace coverage, CompVR for component violations) complement outcome metrics (SR, SafetyScore).
- **Evidence:** This is a synthesis of 270+ publications. Key real-world findings: 26.1% of agent skill ecosystem (8,147 of 31,132 skills) contain vulnerabilities; CVSS 9.6 command injection via OpenClaw; 95.8% of rejected papers misclassified as acceptable by AI reviewers. Progent validates the policy enforcement component: ASR from 39.9% -> 1.0%. The lifecycle framework is validated by the "artifact generation outpaces scientific verification" finding -- errors propagate across stage boundaries in compound ways that isolated evaluation misses.
- **Maturity:** Mixed. The lifecycle taxonomy is research synthesis. The release-gating framework is conceptual. Policy enforcement (Progent) is lab-validated. Real-world CVEs confirm the threat model.

### Technique 10: Docker-Sandboxed CLI Agent Benchmarks with Outcome-Driven Evaluation

- **Sources:** Terminal-Bench 2.0, 2601.11868v1 (paper); AgentBench, 2308.03688v3 (paper); tau-bench, 2406.12045v1 (paper); GAIA, 2311.12983v1 (paper)
- **Mechanism:** Tasks execute in Docker containers with pinned dependencies and internet access. Verification tests check final container state (files, processes, outputs) -- not agent trajectory. This enables any valid solution path. Terminal-Bench 2.0's 7-stage quality control pipeline includes automated CI, LLM-backed checks, human review, multi-model probing, and adversarial exploit agent testing. AgentBench provides a five-category failure taxonomy (Completed, Context Limit Exceeded, Invalid Format, Invalid Action, Task Limit Exceeded) with per-task breakdown. tau-bench introduces `pass^k` -- probability that ALL k independent trials succeed -- measuring consistency, not just average success.
- **Evidence:** Terminal-Bench 2.0: 32,155 trials, ceiling at 62.9% (GPT-5.2 + Codex CLI), demonstrating that 37% of realistic CLI tasks remain unsolved. AgentBench: gpt-4 (4.01 overall) vs. best open-source codellama-34b (0.96) -- 4x gap. tau-bench: pass^8 < 25% for GPT-4o on retail tasks, meaning the agent solves the same task 8/8 times only 25% of the time. GAIA: GPT-4 + plugins scores 30.3% level 1, 9.7% level 2, 0% level 3 -- vs. human 93.9%/91.8%/87.3%.
- **Maturity:** Production deployed as benchmarks. The evaluation methodology is mature; the outcome metric is under production gate use.

---

## 2. Head-to-Head Comparisons

| Technique | Accuracy Impact | Latency | Memory/Context Cost | Engineering Complexity | Scalability | Evidence Strength |
|-----------|----------------|---------|---------------------|------------------------|-------------|-------------------|
| **Query Loop + State Management** | Foundational (enables all others) | Low overhead (governance is pre-model) | Saves context via pre-processing | High (requires full loop implementation) | Linear with sessions | Production (millions of sessions) |
| **Sandbox Isolation** | Eliminates certain failure classes | Startup: 2-15s per sandbox | Minimal (sandbox is external) | Medium (3 impl. patterns available) | Per-instance isolation | Production (Claude Code, OpenHands) |
| **Least-Privilege Policies** | ASR from 39.9% -> 1.0% (Progent) | Per-call intercept: negligible | Policy loaded once at session start | Medium (SMT solver integration) | Scales per-session | Lab validated with SMT proofs |
| **MCTS + Hindsight Feedback** | +23% avg across 5 models (SWE-Search) | 5-14x latency increase | Search tree in git-backed state | High (5 integration points) | Cost-limited (5-14x) | Lab validated (ICLR 2025) |
| **Deferred Tool Loading** | Context savings: loads only used tools | First-use discovery: 1 tool search call | Saves ~80% of tool schema budget | Medium (loader + router changes) | Enables 50+ plugin ecosystems | Production (Claude Code MCP) |
| **Mind-Map Memory** | +18 points GAIA, +36% Werewolf | Incremental graph updates per turn | Graph compression vs. raw text | High (4 new components) | Scales with conversation length | Lab validated (preprint) |
| **Memory-Persisted Orchestration** | +90.2% multi-agent vs single-agent | 90% latency reduction via parallel subagents | 15x tokens but subagent isolation | High (orchestrator + memory + subagents) | Production at Anthropic scale | Production deployed |
| **Self-Healing (Monkey Patching)** | +10.8% MGSM over Meta Agent Search | Recovery: per-iteration inspection | Historical memory growth, needs forgetting | Very High (runtime modification is fragile) | Breaks at complexity threshold | Research concept (14% failure rate) |

---

## 3. Convergences

### Convergence 1: The Harness, Not the Model, Determines Reliability

Every source converges on this. Harness Engineering: "System First, Model Second" (Preface, harneess-engineering-claude-code-chapters). Safety Survey (2605.23989v1): "Trustworthiness must be assessed at the system level, not the model level" because "agent autonomy qualitatively expands the risk surface." Terminal-Bench 2.0 (2601.11868v1): the same model (Gemini 2.5 Pro) achieves 32.6% with Terminus 2 vs. 15.7% with OpenHands -- a 17 percentage point gap from harness quality alone. tau-bench (2406.12045v1): Function Calling consistently outperforms ReAct and text-formatted methods by 13-19 percentage points -- tool interface quality matters more than prompting strategy. All sources agree: model capability is necessary but not sufficient; harness quality is the binding constraint on agent reliability.

### Convergence 2: Structured State Must Survive Context Truncation

Harness Engineering, Ch.3: "State is a formal object, not scattered booleans; it must be monotonic across turns." Anthropic Engineering Blog: "Lead researcher saves plan to Memory that survives 200K context truncation." Claude Code Definitive Guide, Practice 6: "The spec file survives context compaction, session restarts, and subagent failures." AFlow (2410.10762v4): The MCTS tree stores workflow code, modification history, evaluation scores, and optimizer reasoning across iterations. All sources converge on externalized, durable state as the foundation for long-running agent systems.

### Convergence 3: Verification Must Be Separated from Implementation

Harness Engineering, Ch.7: "Verification_worker != implementation_worker" is a lifecycle invariant. Anthropic Engineering Blog: "Verification is explicitly separated from implementation; coordinator prompt stacks implementation self-check PLUS independent verification worker." Claude Code Definitive Guide, Practice 1: "Always include verification criteria in agent prompts." tau-bench (2406.12045v1): The entire evaluation framework is based on verification of final database state against ground truth, not self-reported success. Safety Survey (2605.23989v1): Process metrics (CVR, DCR) catch intermediate violations that outcome-only evaluation misses. Independent verification is the single most cross-validated pattern.

### Convergence 4: Defense-in-Depth is Mandatory for Agent Systems

Claude Code Definitive Guide, Practice 8: "Layer multiple security mechanisms: deny via permissions.deny, restrict via sandbox allowlists, validate via PreToolUse hooks, log via MCP hooks. Never rely on a single layer." Safety Survey (2605.23989v1): "Mitigations across stages are complementary, not substitutable -- a poisoning attack at perceive cannot be fully neutralized by act-time guardrails." Claude Code Sandbox docs: "Sandbox boundaries reduce the impact of a breach but do not eliminate risk... Permission modes and isolation are orthogonal." Progent (2504.11703v3): Multi-policy enforcement where higher-priority policies are applied first and lower-priority policies can only further restrict. Every source with a security focus converges on layered defense.

### Convergence 5: Context is the Binding Budget Constraint

Harness Engineering, Ch.5: "Context is working memory, not a warehouse. Governance exists to keep the system able to continue work." Claude Code Definitive Guide, Practice 11: "The context budget is the binding constraint on every session." Anthropic Engineering Blog: "Subagents act as intelligent compressors -- each explores different facets in separate context windows, then returns only the most important tokens." Claude Code MCP docs: "Tool Search defers tool definitions to keep context usage low -- only tool names and server instructions load at session start." All sources agree: context is the scarcest resource, and governance mechanisms exist to preserve it for the task, not consume it with infrastructure overhead.

### Convergence 6: Layered Architectures (Exploration -> Execution -> Verification) are the Convergent Design Pattern

AI for Auto-Research (2605.18661v1): "Effective systems converge on layered architectures -- exploration + execution + verification layers." PosterForest (2508.21720v2): Separate Layout Agent and Content Agent with a shared Poster Tree and global feedback. Anthropic Engineering Blog: "Orchestrator plans -> subagents execute -> CitationAgent verifies/synthesizes." Harness Engineering, Ch.7: "Multi-agent depends on clear division of labor: research, implementation, verification, and synthesis must run under different constraint containers." OSWorld (2404.07972v2): Three-layer evaluation infrastructure (Coordinator -> VM -> Task Manager + Evaluator). Independent sources across research synthesis, production engineering, and benchmark design all converge on the same three-layer pattern.

---

## 4. Contradictions

### Contradiction 1: Search-Based vs. Greedy Agent Execution

SWE-Search (2410.20285v6), RAP (2305.14992v2), and AFlow (2410.10762v4) all demonstrate that MCTS-driven search substantially improves agent trajectory quality (+23%, +69%, +5.7% respectively). However, the Anthropic Engineering Blog explicitly does NOT use search-based execution -- it uses heuristic effort scaling with parallel subagents and relies on the orchestrator LLM's planning quality. Claude Code's production architecture uses deterministic, linear execution with pre-model governance, not tree search. The tension: search demonstrably improves accuracy, but production systems (Claude Code, Anthropic Research) achieve SOTA results without it through better harness design. This may be because search compensates for weak harness architecture, while a strong harness makes search unnecessary -- or it may be that search's cost multiplier (5-14x) is prohibitive for production and the field converges to harness quality as the more cost-effective investment.

### Contradiction 2: Prompt Engineering vs. Structured Policies for Safety

The Safety Survey (2605.23989v1) identifies prompt-based defenses (delimiting, spotlighting, instructional prevention) as a class of mitigations but notes they are fragile (ASR remains 25-73% under attack). Progent (2504.11703v3) demonstrates that SMT-based symbolic policies with deterministic enforcement achieve ASR <1.1%. Harness Engineering, Ch.4 argues that "tools are managed execution interfaces; permission is an organ of the system" -- implying that safety must be enforced at the tool/permission level, not the prompt level. The Claude Code Definitive Guide, Practice 7 advocates "backpressure via strict tooling" -- linting, type checking, and test suites as automated feedback. The contradiction: Should safety be prompt-encoded (cheap, flexible, but fragile) or structurally enforced (robust, but requires engineering investment)? The evidence strongly favors structural enforcement: Progent's 1.0% ASR vs. prompt-based defenses' 25-73% ASR.

### Contradiction 3: Self-Modification vs. Immutable Infrastructure

Godel Agent (2410.04444v4) demonstrates that runtime self-modification (monkey patching) enables discovering novel strategies that deterministic architectures cannot reach (e.g., autonomously switching from LLM reasoning to brute-force search). However, the failure rate is 14%, and 4% of trials experience self-modification collapse. Harness Engineering and the Claude Code architecture explicitly reject runtime self-modification: the query loop is a fixed structure with governed parameters, and recovery follows predetermined escalation paths. Claude Code's checkpoint system does NOT support modifying the agent's own execution logic. The tension: self-modification unlocks novel optimization strategies but introduces catastrophic fragility. The current evidence suggests self-modification is not production-ready, but the architectures that succeed (Godel Agent) show it is a legitimate frontier technique.

### Contradiction 4: Single-Judge vs. Multi-Agent Verification

Anthropic Engineering Blog: "Single-judge LLM eval works best -- one LLM call with one prompt scoring 5 criteria was most consistent and aligned with human judgments." SWE-Search (2410.20285v6): The Discriminator debate (5 agents, 3 rounds) improves selection accuracy from 73% to 84% over the single value function. The tension: multi-agent debate improves accuracy but adds complexity and cost. Anthropic's finding suggests that a well-designed single-judge prompt can match or exceed multi-agent debate for specific evaluation tasks, while SWE-Search shows debate helps when individual judgments are miscalibrated (value function only 73% accurate). The resolution may be that single-judge works for well-scoped evaluation rubrics, while debate is needed when individual evaluators are unreliable.

### Contradiction 5: Token Budget Scaling vs. Quality

Terminal-Bench 2.0 (2601.11868v1) finds that "higher token count does not necessarily correlate with better performance" -- Claude Code + Claude Opus 4.5 uses 256.9M input tokens for 52.1% resolution, while GPT-5.2 + Codex CLI achieves 62.9% with 137.5M input tokens. However, Anthropic Engineering Blog finds that on BrowseComp, 80% of score variance is explained by token count alone, and overall 95% is explained by tokens + tool calls + model. The apparent contradiction: token count correlates with performance on research tasks (BrowseComp) but not on engineering tasks (Terminal-Bench 2.0). Resolution: the nature of the task matters. Research tasks benefit from broad exploration (more tokens = more sources), while engineering tasks benefit from precision and structured reasoning (more tokens often mean confused, looping agents).

---

## 5. Open Problems

### Problem 1: No Lifecycle-Scale Evaluation Framework Exists

AI for Auto-Research (2605.18661v1) explicitly states: "No lifecycle-scale benchmark exists; cross-system comparison confounded by different base models, prompts, tools, compute budgets, and human-in-the-loop assumptions." Terminal-Bench 2.0, SWE-bench, AgentBench, tau-bench, GAIA, and AgentDojo each test one slice of agent capability. No benchmark evaluates an agent across the complete Perceive -> Plan -> Act -> Reflect -> Learn lifecycle. Safety Survey (2605.23989v1) notes that "exhaustive long-horizon evaluation is combinatorially impossible" with current methods. This is both a research opportunity and a practical limitation for Lyra's evaluation infrastructure.

### Problem 2: Agent Accountability Across Multi-Agent Interaction

Safety Survey (2605.23989v1): "Assigning responsibility requires protocol-aware traces, message authentication, and evaluation designs that separate individual from collective failure modes -- these are noted as open problems." When multiple agents interact, determining which agent caused a failure is unsolved. This matters for debugging, improvement, and safety attribution. No source provides a working solution.

### Problem 3: Safe Runtime Self-Modification

Godel Agent (2410.04444v4) shows 14% failure rate and 4% catastrophic self-modification collapse. No source demonstrates runtime self-modification with reliability suitable for production deployment. The Harness Engineering approach (predetermined recovery paths, circuit breakers) is safer but cannot discover novel optimizations. A synthesis that combines the safety of predetermined recovery with the flexibility of self-modification does not yet exist.

### Problem 4: Cost-Effective Multi-Turn Agent Evaluation

tau-bench (2406.12045v1) demonstrates that reliability measurement (`pass^k`) requires many independent trials per task. Running pass^8 on all tasks costs ~$3,200+ at gpt-4o pricing. Terminal-Bench 2.0's 32,155 trials represent a massive investment. Cost-effective methods for statistical reliability measurement of multi-turn agents do not exist.

### Problem 5: Context-Aware Tool Selection at Scale

Agentic Reasoning (2502.04644v2) finds that 3 carefully chosen tools outperform 109 LangChain tools -- "many capabilities already exist inside the reasoning model; external duplicates introduce noise and inappropriate tool selection." Claude Code's Tool Search defers tool schemas but does not solve the selection problem: when 50+ tools are available, how does the agent reliably select the right one? The current solution (semantic search + LLM judgment) has no formal guarantees and fails silently.

### Problem 6: Privacy Guarantees for Persistent Agent Memory

Safety Survey (2605.23989v1): "Once a secret leaks into agent memory/logs, it can persist and be replayed by future plans -- turning a single exposure into sustained compromise." The Moltbook breach exposed 32,000+ registered agents including API keys. While (epsilon, delta)-DP is formalized for training, dynamic privacy (runtime information flows across the agent loop) lacks equivalent guarantees. No source provides a working implementation.

### Problem 7: Autonomous Verification of Semantic Correctness

AI for Auto-Research (2605.18661v1): 58.6% of research code errors are semantic (code runs, wrong algorithm). MLR-Bench: 80% of fully autonomous results are fabricated. All sources agree that current verification methods catch syntactic errors but miss semantic ones. This is acknowledged as open by the Safety Survey and the Auto-Research survey.

---

## 6. Recommendations for Lyra

### Tier 1: Foundation (Must Implement)

1. **Continuous Query Loop with Formal State Management** (Technique 1)
   - **Rationale:** This is the architectural backbone from which all other capabilities derive. The Harness Engineering book's 10 principles and query loop architecture provide the template. Lyra's current architecture already has elements of this; formalizing it with monotonic state, pre-model governance sequence, event-stream consumption, interrupt ledger closure, and seven distinct stop conditions would make Lyra's execution foundation production-grade.
   - **Sources:** Harness Engineering Ch.3, Ch.6; Claude Code Definitive Guide, Practices 5, 6, 15

2. **Sandbox-Isolated Agent Execution** (Technique 2)
   - **Rationale:** Agent execution without sandboxing is indefensible given the CVEs (CVSS 9.6 command injection) and data from Progent (39.9% ASR without controls). Lyra should ship with at minimum the per-command Bash sandbox (Seatbelt/bubblewrap) and ideally a full-process sandbox runtime.
   - **Sources:** Claude Code Sandbox docs; Progent 2504.11703v3; Safety Survey 2605.23989v1

3. **Least-Privilege Tool Access** (Technique 3)
   - **Rationale:** Progent's 1.0% ASR vs. prompt-based defenses' 25-73% ASR is decisive. Symbolic policy enforcement with SMT-based narrowing guarantees provides formal safety properties that prompt-based defenses cannot match. Lyra's tool permission system should adopt the three-valued model (allow/deny/ask) with deterministic policy enforcement.
   - **Sources:** Progent 2504.11703v3; Harness Engineering Ch.4

### Tier 2: Performance (Should Implement)

4. **Memory-Persisted Orchestration with Effort Scaling** (Technique 7)
   - **Rationale:** The +90.2% improvement over single-agent on Anthropic's research eval is the strongest single performance gain documented. The pattern is well-defined, production-validated, and directly applicable to Lyra's multi-agent architecture. The heuristic effort scaling (1 agent for simple, 2-4 for comparisons, >10 for complex) provides Lyra with a concrete task routing mechanism.
   - **Sources:** Anthropic Engineering Blog; Claude Code Definitive Guide, Practices 3, 4, 5, 10

5. **Structured Memory Graph (Mind-Map)** (Technique 6)
   - **Rationale:** +18 points on GAIA and +36% on Werewolf represents the single largest documented improvement from a memory architecture change. All components have open-source implementations. This directly addresses Lyra's long-context coherence problem.
   - **Sources:** Agentic Reasoning 2502.04644v2

6. **Deferred Capability Loading** (Technique 5)
   - **Rationale:** As Lyra's plugin ecosystem scales to 50+ plugins, loading all tool schemas at startup will consume prohibitive context. The Tool Search pattern is production-validated and enables unbounded tool ecosystem growth without context degradation.
   - **Sources:** Claude Code MCP docs

### Tier 3: Advanced (Investigate for V2)

7. **MCTS with Hindsight Feedback for Complex Multi-Step Tasks** (Technique 4)
   - **Rationale:** +23% average improvement is compelling, but the 5-14x cost multiplier is prohibitive for default operation. A lightweight version using Lyra's test infrastructure as the primary value signal (bypassing the LLM Value Agent for routine states) could capture much of the benefit at acceptable cost.
   - **Sources:** SWE-Search 2410.20285v6; RAP 2305.14992v2

8. **Five-Stage Lifecycle with Process Metrics** (Technique 9)
   - **Rationale:** The lifecycle framework provides a principled structure for Lyra's evaluation infrastructure. Implementing CVR, DCR, and CompVR as process metrics alongside outcome metrics would catch intermediate failures that outcome-only evaluation misses. The three-tier release gating is directly applicable to Lyra's deployment pipeline.
   - **Sources:** Safety Survey 2605.23989v1; AI for Auto-Research 2605.18661v1

### Architectural Constitution (from Harness Engineering, Ch.9)

The following 10 principles should serve as Lyra's architectural constitution. Every workstream should satisfy the relevant principle before being marked complete.

1. Treat models as unstable components, not teammates
2. Prompt is part of the control plane
3. Query loop is the heartbeat of agent systems
4. Tools are managed execution interfaces
5. Context is working memory
6. Error paths are main paths
7. Recovery should optimize for continuation
8. Multi-agent matters because it partitions uncertainty
9. Verification must be independent
10. Team institutions matter more than personal tricks

### Evaluation Gates (from Safety Survey, 2605.23989v1)

Every Lyra release should pass:
- **Tier 0 (offline regression):** CVR = 0 (no constraint violations), DCR = 100% (full trace coverage)
- **Tier 1 (sandbox stress):** CER < 0.1% on high-risk scenario banks, pass^4 > 70% on domain-specific tasks
- **Tier 2 (canary):** Shadow deployment with automated rollback on safety metric degradation

### Key Architectural Rules

1. **Design permission before capability.** Claude Code's "deny is sticky" pattern -- once denied for a tool_use_id, permission cannot auto-escalate to allow.
2. **Rollback before autonomy.** Git-backed state tree with O(1) reversion to any prior state (SWE-Search pattern) combined with commit-frequently discipline.
3. **Verification before delivery.** Independent verification worker, never same agent as implementation. Process metrics (CVR, DCR) alongside outcome metrics.
4. **Context budgets before long dialogue.** Fixed budget thresholds, pre-model governance sequence, subagent isolation for high-volume operations.
5. **Lifecycle before multi-agent.** Subagent lifecycle invariants: cache-safe params, default state isolation, parent abort propagation, Start/Stop hook symmetry.
6. **Institutions before expecting team proficiency.** Layered CLAUDE.md, tiered approvals by risk, skills as workflow modules with verifiable contracts.

---

*Synthesis methodology: 22 papers + 2 books + 6 web notes examined. Claims cite sources by paper ID or book/web title. No unsupported assertions.*
