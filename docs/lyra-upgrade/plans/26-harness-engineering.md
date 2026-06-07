# Workstream Plan: Harness Engineering -- The Meta-Discipline (§4.26)

> Run 2 -- June 7, 2026. Rewritten with deep-read evidence from 12 papers, 3 books, 5 web notes.

## Evidence Base

Sources actually consulted and cited in this plan, numbered for cross-reference:

1. **Harness Engineering: A Design Guide to Claude Code** (book, @wquguru, agentway.dev, 2026) -- Chapters 1-9 + Appendices A-C. Reverse-engineered from Claude Code production source (`src/query.ts`, `src/QueryEngine.ts`, `src/tools/*`, `src/compact.ts`, `src/coordinatorMode.ts`, etc.)
2. **Claude Code: The Definitive Guide to Agentic Development** (book, playbook) -- Practices 1-15, including verification criteria, context isolation via subagents, spec-driven development, defense-in-depth.
3. **Agent Way / Comparative Harness Notes** (book, @wquguru, 2026) -- Comparative analysis of Claude Code vs. Codex harness philosophies; 7 practices distilled.
4. **Anthropic Engineering Blog: "How we built our multi-agent research system"** (web, June 2025) -- LeadResearcher + subagents pattern; +90.2% multi-agent vs. single-agent; 90% latency reduction via parallel subagents; effort-scaling heuristics.
5. **Anthropic: "Effective Context Engineering for AI Agents"** (web, September 2025) -- Attention budget, context rot, progressive disclosure, just-in-time retrieval, compaction mechanics, sub-agent clean context separation.
6. **Terminal-Bench 2.0** (paper, 2601.11868v1, Jan 2026) -- 32,155 trials across 16 models x 6 agents; CLI agent benchmark; 7-stage task validation pipeline; outcome-driven evaluation; harness quality yields 17pp gap between agents using same model.
7. **Progent: Securing AI Agents with Privilege Control** (paper, 2504.11703v3, 2025) -- SMT-based symbolic policy enforcement; ASR reduction 39.9% -> 1.0% on AgentDojo; monotonic confinement theorem; production code at `sunblaze-ucb/progent`.
8. **Safety Survey: Towards Trustworthy Agentic AI** (paper, 2605.23989v1, May 2026) -- Five-stage lifecycle (Perceive/Plan/Act/Reflect/Learn); three-tier release gating (CVR=0 -> CER<0.1% -> canary auto-rollback); synthesis of 270+ publications.
9. **SWE-Search: MCTS + Iterative Refinement** (paper, 2410.20285v6, ICLR 2025) -- +23% mean improvement across 5 models; modified UCT with depth bonus/penalty; hindsight feedback loop; 5-14x cost multiplier.
10. **tau-bench** (paper, 2406.12045v1, June 2024) -- pass^k reliability metric; function calling outperforms ReAct by 13-19pp; gpt-4o <50% overall; pass^8 <25% on retail.
11. **Agentic Reasoning: Mind-Map** (paper, 2502.04644v2, 2025) -- Structured knowledge graph + Leiden community detection + GraphRAG retrieval; +18 points GAIA vs. flat memory; +36% Werewolf win rate.
12. **AI for Auto-Research** (paper, 2605.18661v1, May 2026) -- Four-phase research lifecycle; 58.6% of research code errors are semantic; convergence on layered architectures (exploration + execution + verification).
13. **Godel Agent** (paper, 2410.04444v4, 2025) -- Recursive self-improvement via monkey patching; 14% failure rate; autonomous strategy discovery (LLM reasoning -> brute-force search).
14. **OSWorld** (paper, 2404.07972v2, April 2024) -- Full-VM sandboxed agent evaluation; QEMU/KVM snapshots; 369 tasks; best model 12.24% vs. human 72.36%.
15. **OpenHands** (repo, All-Hands-AI/OpenHands) -- Sandbox abstraction (Docker/Process/Remote); SWE-bench 77.6%; app-server/agent-server separation; MCP for git operations.
16. **Claude Code MCP docs + Sandbox docs** (web, Anthropic) -- Tool Search deferred loading; sandbox tiers (Seatbelt/bubblewrap -> full VM); three-valued permission model.
17. **Claude Code Definitive Guide Playbook** (book, playbook) -- Practice 8: Defense in Depth; Practice 5: Context Isolation via Subagents; Practice 15: Commit-Frequently Recovery.
18. **sierra-research/tau-bench** (repo) -- pass^k implementation; POMDP formalization; user simulation with hidden instruction.
19. **laude-institute/terminal-bench** (repo) -- Docker-sandboxed CLI benchmark with 7-stage QC pipeline.
20. **sunblaze-ucb/progent** (repo) -- MCP proxy + Z3 SMT solver policy enforcement; middleware chain pattern.

---

## Current Lyra Baseline

Lyra's existing harness (from plan v1, confirmed accurate by synthesis):

**Context Engineering:**
- "Less is more" principle (Anthropic): 15-line system prompt, 3 tools, 2 canonical examples
- Context budget by component: system prompt (15%), skills (10%), conversation (50%), tool outputs (15%), memory (10%)
- Auto-compaction (§4.3) and memory (§4.2) as implementation vehicles

**Evaluation Infrastructure:**
- Capability evals (ceiling): SWE-bench Verified, tau-bench, Terminal-Bench, GAIA -- weekly
- Regression evals (floor): Lyra-specific task suite -- every commit
- Simulation personas: adversarial users (novice, malicious, ambiguous, expert)
- Anti-contamination: rotated tasks, held-out splits, benchmark leakage detection

**Safety Architecture:**
- 5-layer defense-in-depth (§4.17): Prompt -> Schema -> Runtime -> Tool -> Lifecycle
- Every new capability ships with its safety counterpart
- Self-evolution gated behind safety validator

**Methodology:**
- AI-native SDLC: spec-to-code pipelines, agent lanes in CI/CD
- Adversarial review gates (§4.25)
- BMAD Method: Behavior -> Model -> Adapt -> Deploy

**Platform Prerequisites:**
- CI/CD + IaC + observability + security scanning
- "Agents accelerate broken practices -- fix foundations first" (Netflix)
- Lyra dogfoods Lyra

**Expert Review (from Run 1):**
- Skeptic: "Port Claude Code's implementation directly -- don't invent unless evidence proves it's better."
- Resolution: Parity port is (A) tier baseline. Breakthrough enhancements must beat Claude Code on at least one measurable dimension (latency, token cost, multi-provider compatibility, UX simplicity) with cited evidence.

**Gap assessment:** The existing plan correctly identifies the 5 pillars and adopts good principles, but lacks:
- Concrete architecture: no formal query loop design with state management
- Specific evaluation gates with numeric thresholds
- Tool permission architecture beyond boolean allow/deny
- Recovery path design (circuit breakers, layered escalation)
- Multi-agent lifecycle invariants
- Context governance budgets with explicit thresholds

---

## Breakthrough Proposals

Each proposal is a COMBINATION of 2+ source techniques. None is a single-source copy.

---

### Proposal 1: The Governed Query Loop -- Fusing Pre-Model Context Governance + Three-Valued Permission Model + Layered Recovery with Circuit Breakers

**Fused sources:** Harness Engineering (Ch.3, Ch.4, Ch.6) + Claude Code Definitive Guide (Practices 1, 2, 6, 8, 11, 15) + Agent Way Comparative Notes (Practices 2, 3) + Terminal-Bench 2.0 (2601.11868v1)

**What it is:** A formal execution loop where:

1. **Pre-model governance pipeline** (Harness Engineering Ch.3) runs BEFORE every model invocation: memory prefetch -> message slicing -> tool result budget -> history snip -> microcompact -> context collapse -> autocompact. The model never receives raw, unbudgeted context.

2. **Formal state object** maintains cross-iteration variables: `messages`, `toolUseContext`, `autoCompactTracking`, `recoveryCount`, `turnCount`, `transition`. State is monotonic across turns. Not scattered booleans.

3. **Three-valued permission model** (Harness Engineering Ch.4 + Progent 2504.11703v3): `allow | deny | ask` routed to coordinator/classifier/approval. Deny is sticky per `tool_use_id`. Ask never auto-escalates. Bash gets TWO dedicated governance layers (prompt guidance + permission classification).

4. **Event-stream consumption** via `for await` -- tool dispatch happens while streaming, not after. Interrupt handling closes the ledger: synthetic tool results for issued-but-unfinished calls.

5. **Layered recovery escalation** (Harness Engineering Ch.6): prompt-too-long -> flush collapse -> reactive compact (once per turn) -> surface error. Circuit breakers: `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`. Continuation-first truncation: "continue directly; no apology; no recap."

6. **Seven distinct stop conditions**: completion, failure, recovery, continuation -- never conflate "turn ended" with "task completed."

**Why this combination wins:**
- The pre-model governance pipeline (Harness Engineering) + the three-valued permission model (Progent) together solve the problem that each source identifies individually: models should not receive ungoverned context AND should not freely execute tool calls. Fusing them creates a single entry gate where context is sanitized AND tool intent is authorized before model invocation.
- The recovery escalation + circuit breakers prevent the self-reinforcing failure loops that Terminal-Bench 2.0 documents (agents burning tokens on repeated failures).
- Terminal-Bench 2.0 shows harness quality produces 17pp difference between agents using the SAME model (Gemini 2.5 Pro: 32.6% Terminus 2 vs. 15.7% OpenHands). The query loop + permission model + recovery design IS what creates that gap.

**Trade-offs:**
- Win: Formal state object enables resume, audit, and inter-agent handoff that scattered booleans cannot. The recovery escalation with circuit breakers prevents the most expensive failure mode (infinite retry loops).
- Win: Three-valued permission model eliminates the boolean collapse problem: the system can honestly say "I don't know" without silently authorizing dangerous operations OR rejecting safe-but-unfamiliar ones.
- Loss: Engineering complexity is high -- requires implementing all 8 pre-model governance steps, 3-state permission routing, 7 stop conditions, and recovery path testing for each. Total ~3-4 weeks for solid v1.
- Loss: The governance pipeline adds latency per turn (~50-200ms for memory prefetch + message slicing + budget checks). Acceptable given quality gains (Terminal-Bench: harness quality > token count for performance).

**Impact: 5/5 | Effort: 5/5 | Tier: (A) Foundation**

---

### Proposal 2: SMT-Backed Least-Privilege Tool Sandbox -- Fusing Progent's Symbolic Policies + OpenHands' Sandbox Abstraction + OSWorld's VM Snapshot Isolation

**Fused sources:** Progent (2504.11703v3) + OpenHands (All-Hands-AI/OpenHands repo) + OSWorld (2404.07972v2) + Claude Code Sandbox docs + Safety Survey (2605.23989v1)

**What it is:**

1. **Symbolic policy enforcement** (Progent): Every tool call is intercepted and checked against a security policy of symbolic rules over tool names and arguments. Rules support comparisons, string matching, boolean operators, array operations. Default-deny posture.

2. **SMT-based monotonic confinement** (Progent): Z3 SMT solver determines whether a proposed policy update is expansion or narrowing. Narrowing auto-applied; expansion requires explicit approval. The allowed action space monotonically decreases: `A(P0) ⊇ A(P1) ⊇ A(P2) ⊇ ...`

3. **Sandbox abstraction layer** (OpenHands): Three isolation tiers behind a single `SandboxService` interface:
   - **Tier 1 (Per-command):** Seatbelt (macOS) / bubblewrap (Linux) -- Claude Code default
   - **Tier 2 (Process):** Separate agent process with isolated filesystem -- OpenHands Process sandbox
   - **Tier 3 (Container):** Docker container with pinned dependencies and internet access -- OpenHands Docker + Terminal-Bench pattern

4. **VM snapshot reproducibility** (OSWorld): For high-assurance evaluations, full QEMU/KVM VM snapshots enable exact state reproduction and clean-room verification. The sandbox boundary is an explicit system component, not an afterthought.

5. **Defense-in-depth layering** (Safety Survey + Claude Code Definitive Guide Practice 8): `permissions.deny` (file-level) -> sandbox allowlists (network-level) -> PreToolUse hooks (input validation) -> Progent policy (argument-level) -> MCP hooks (logging). No single layer.

**Why this combination wins:**
- Progent alone provides argument-level security but no filesystem/network isolation. OpenHands alone provides process isolation but no argument-level policy enforcement. Fusing them creates a sandbox where the agent's filesystem access is contained AND its tool arguments are symbolically validated.
- The SMT-based monotonic confinement theorem (Progent) provides a FORMAL guarantee that policy can only narrow without approval. No ML heuristic, no probabilistic detection -- deterministic. Combined with Docker process isolation, this is the strongest practical agent security architecture documented.
- Safety Survey's real-world data validates the threat: CVSS 9.6 command injection CVEs in agent systems, 26.1% of agent skills contain vulnerabilities, 32,000+ registered agents exposed in a single breach. Prompt-only defenses achieve 25-73% ASR; Progent achieves 1.0% ASR.
- The three-tier sandbox abstraction (Tier 1 low-overhead for dev, Tier 3 full isolation for production) mirrors the progressive complexity pattern that OpenHands validated across deployments.

**Trade-offs:**
- Win: Progent's 1.0% ASR vs. prompt-based defenses' 25-73% ASR is decisive. The SMT-based policy comparison is fully deterministic.
- Win: Three-tier sandbox abstraction enables progressive security -- developers use Tier 1 for fast iteration, production uses Tier 3, evaluation uses VM snapshots.
- Win: Monotonic confinement theorem provides a provable security property that prompt-based systems cannot offer.
- Loss: Z3 SMT solver dependency adds computational overhead per policy comparison. Docker sandbox adds 2-15s startup latency per session.
- Loss: Proxy mode (Progent's MCP proxy pattern) cannot protect built-in tools that bypass MCP interfaces. Requires adapter per agent framework (LangChain, OpenAI SDK, etc.).
- Loss: Engineering complexity is high -- SMT policy language, sandbox abstraction, and VM snapshot management are three substantial subsystems. ~4-6 weeks for v1.

**Impact: 5/5 | Effort: 5/5 | Tier: (A) Foundation**

---

### Proposal 3: Structured Memory Graph with Coordinator-Synthesized Multi-Agent Orchestration -- Fusing Mind-Map + Anthropic Multi-Agent Research + Context Engineering Progressive Disclosure

**Fused sources:** Agentic Reasoning / Mind-Map (2502.04644v2) + Anthropic Engineering Blog (web, June 2025) + Effective Context Engineering (web, Sept 2025) + Harness Engineering (Ch.5, Ch.7) + Claude Code Definitive Guide (Practices 3, 4, 5, 10)

**What it is:**

1. **Structured memory graph** (Mind-Map): A knowledge graph incrementally built from conversation turns via entity-relationship extraction. Leiden algorithm partitions the graph into communities; each community is summarized by an LLM. When the agent becomes uncertain or lost in long chains, GraphRAG retrieval over the knowledge graph returns relevant structured information.

2. **Memory-persisted coordinator** (Anthropic Blog): LeadResearcher agent (Opus 4 level) saves research plan to external Memory that survives 200K+ context truncation. Spawns parallel subagents (Sonnet 4 level) that independently search/evaluate, each returning only compressed findings (~1,000-2,000 tokens). Coordinator MUST synthesize -- never forward raw findings.

3. **Heuristic effort scaling** (Anthropic Blog): 1 agent / 3-10 calls for simple fact-finding; 2-4 subagents / 10-15 calls each for comparisons; >10 subagents for complex research. This is concrete task routing, not abstract "use multi-agent."

4. **Progressive disclosure** (Context Engineering post): Agents carry lightweight identifiers (file paths, paper slugs, tool signatures) -- not full content. Orchestrator reads abstracts/section headings first, then retrieves specific sections on demand. Mirrors human research cognition: maintain what is necessary in working memory, retrieve the rest on demand.

5. **Context-isolated subagents** (Claude Code Definitive Guide Practice 5): Subagents run in their own context windows. Only the summary returns. The orchestrator's context stays lean, focused on coordination. Post-compact semantic reconstruction (Harness Engineering Ch.5) rebuilds working context: clear stale readFileState, regenerate file attachments, reinject plan/skills, write compact boundary messages.

6. **Cache-safe fork parameters** (Harness Engineering Ch.7): Every forked subagent shares `CacheSafeParams` with parent: `systemPrompt`, `userContext`, `systemContext`, `toolUseContext`, `forkContextMessages`. Without cache alignment, parallel acceleration becomes parallel waste.

**Why this combination wins:**
- Mind-Map alone provides structured memory but no multi-agent orchestration. Anthropic's multi-agent system provides orchestration but uses flat Memory, not structured knowledge graphs. Fusing them creates an orchestrator whose Memory is a queryable graph with community-compressed summaries -- not a flat text dump.
- Mind-Map's +18-point GAIA improvement and +36% Werewolf win rate demonstrate that structured memory outperforms flat memory by a large margin. Anthropic's +90.2% multi-agent vs. single-agent gain demonstrates that orchestration multiplies capability. Combining them should produce multiplicative, not additive, gains.
- The progressive disclosure pattern addresses the context rot problem that the Anthropic Context Engineering post identifies as the binding constraint. Agents discover context incrementally instead of drowning in it upfront.
- The cache-safe fork parameters + coordinator synthesis rule (Harness Engineering Ch.7) prevent the two most common multi-agent failure modes: cache misalignment (parallel waste) and coordinator-as-forwarding-service (understanding not reconverged).

**Trade-offs:**
- Win: Structured memory graph scales with conversation length where flat memory degrades. The Leiden community detection + LLM summarization pipeline is well-defined with open-source implementations (python-igraph, GraphRAG by Microsoft).
- Win: Subagent context isolation is the single most cost-effective context management strategy: coordinator stays at ~143K/200K tokens while 14 subagents complete a complex migration (documented in Claude Code Definitive Guide).
- Win: Heuristic effort scaling provides concrete, debuggable task routing without brittle rules.
- Loss: Token cost multiplier is ~15x over chat (Anthropic Blog). Economically justified only for high-value research/engineering tasks. Must gate behind cost-weighted routing.
- Loss: Memory graph construction per turn adds latency (incremental entity extraction + relationship linking + periodic community re-clustering). Acceptable for long-horizon tasks, expensive for short ones.
- Loss: Coordinator synthesis is a non-delegable capability -- if the coordinator model is weak, the entire system degrades. The Opus/Sonnet tier split is essential. Running this with all Haiku-level models would fail.

**Impact: 5/5 | Effort: 4/5 | Tier: (B) Breakthrough**

---

### Proposal 4: Outcome-Driven Evaluation Pipeline with Process Metrics -- Fusing Terminal-Bench 2.0's Property-Based Verification + tau-bench's pass^k + Safety Survey's Three-Tier Release Gating

**Fused sources:** Terminal-Bench 2.0 (2601.11868v1) + tau-bench (2406.12045v1) + Safety Survey (2605.23989v1) + AI for Auto-Research (2605.18661v1) + Claude Code Definitive Guide (Practice 1)

**What it is:**

1. **Outcome-driven evaluation** (Terminal-Bench 2.0): Verification tests check final output state (files, data, task completion markers), NOT agent trajectory or tool-call sequence. This enables creative solution paths without penalizing non-canonical approaches.

2. **pass^k reliability metric** (tau-bench): Probability that ALL k independent trials succeed. Measures consistency, not just average success. pass^8 < 25% for GPT-4o on retail tasks means the agent solves the same task 8/8 times only 25% of the time. This is the correct metric for production readiness.

3. **Property-based verification predicates** (Terminal-Bench 2.0): Define verification as predicates that check properties of final output -- not golden-output comparison. Can be composed: `verify_file_exists(path) AND verify_content_matches(path, pattern) AND verify_test_passes(test_suite)`.

4. **Process metrics + outcome metrics** (Safety Survey): Complement outcome metrics with CVR (Constraint Violation Rate -- how often policy/permission breaks occur), DCR (Trace Coverage -- what fraction of agent steps are instrumented), and CompVR (Component Violation Rate -- per-module safety failures).

5. **Three-tier release gating** (Safety Survey): Tier 0 (offline regression, CVR=0, DCR=100%) -> Tier 1 (sandbox stress, CER<0.1% on high-risk scenario banks, pass^4 >70%) -> Tier 2 (canary with auto-rollback on safety metric degradation).

6. **Anti-saturation refresh** (Terminal-Bench 2.0 + Safety Survey): When eval saturates (100% pass rate = useless signal), replace with harder variant. Terminal-Bench's adversarial exploit agent probes verification predicates for design flaws that enable cheating.

7. **Verification criteria embedded in agent prompts** (Claude Code Definitive Guide Practice 1): Test commands, expected output, behavioral descriptions. Converts one-shot generation into automatic generate-test-fix loop.

**Why this combination wins:**
- Terminal-Bench 2.0's outcome-driven evaluation + tau-bench's pass^k together solve the reliability measurement problem that neither solves alone. Terminal-Bench tells you "did it work once?" tau-bench tells you "does it work reliably?" Combined, they answer "does it work correctly AND consistently?"
- Safety Survey's process metrics fill the gap that outcome-only evaluation leaves: an agent can produce a correct final answer while violating constraints at intermediate steps. CVR catches intermediate tool misuse that outcome metrics miss.
- The three-tier release gating maps directly to Lyra's deployment pipeline and provides concrete, numeric pass/fail thresholds -- unlike the current plan's vague "adversarial review gates."
- The adversarial exploit agent (Terminal-Bench 2.0) closes the loop: it actively probes for design flaws in verification predicates that would allow cheating, preventing the evaluation from becoming gamed.

**Trade-offs:**
- Win: Property-based verification is deterministic, fast, and enables regression testing across model upgrades. No LLM-judge subjectivity for routine evaluations.
- Win: pass^k provides a statistical reliability guarantee that pass@1 cannot. Required for production deployment confidence.
- Win: Process metrics catch the intermediate violations that the Safety Survey identifies as the primary blind spot of outcome-only evaluation.
- Loss: pass^k requires k independent trials per task. At pass^8 with GPT-4o pricing, ~$3,200+ for a full run (tau-bench data). Cost-prohibitive for every-commit regression testing. Mitigation: pass^4 for regression (cheaper), pass^8 for weekly capability evals.
- Loss: Property-based verification predicates require engineering investment per task class. Terminal-Bench 2.0's 7-stage pipeline costs ~3 reviewer-hours per task. This is amortized across evaluations but represents significant upfront investment.
- Loss: Process metrics (CVR, DCR, CompVR) require trace schemas and instrumentation that add latency per agent step. Acceptable for evaluation; overhead for production requires optimization.

**Impact: 4/5 | Effort: 4/5 | Tier: (A) Foundation**

---

### Proposal 5: Deferred Capability Loading with Context Budget Governance -- Fusing Claude Code MCP Tool Search + Context Engineering Progressive Disclosure + Memory/Index Split with Hard Budgets

**Fused sources:** Claude Code MCP docs / Tool Search (web) + Effective Context Engineering (Anthropic, web) + Harness Engineering (Ch.5) + Agent Way Comparative Notes (Practice 5) + Agentic Reasoning (2502.04644v2)

**What it is:**

1. **Deferred tool loading** (Claude Code MCP): At session start, only tool names and 2KB server instructions load into context. Full tool schemas discovered on-demand via semantic search when the LLM decides it needs a tool. Configurable modes: `true` (always defer), `auto` (load upfront if under 10% context window, defer otherwise), `auto:N` (custom threshold), `false` (load all upfront).

2. **Memory/index split** (Harness Engineering Ch.5): Long-term memory entrypoint is an INDEX only (max 200 lines, 25,000 bytes). Actual content in dedicated topic files. When entrypoint exceeds limits, truncate with explicit warning. Session memory templates with hard budgets: `MAX_SECTION_LENGTH = 2,000`, `MAX_TOTAL_SESSION_MEMORY_TOKENS = 12,000`.

3. **Progressive disclosure for capability** (Context Engineering post): Agents carry lightweight identifiers (tool names, skill slugs), not full tool schemas. Assembly understanding layer by layer -- tool schemas loaded only when the agent demonstrates intent to use them.

4. **Context budget by component with explicit thresholds** (Harness Engineering Ch.5 + Agent Way Practice 5):
   - System prompt: 15% of context window
   - Skills: 10% (names only; full schemas deferred)
   - Conversation: 50%
   - Tool outputs: 15% (per-result ceiling: 500K chars; MCP output warning at 10K tokens)
   - Memory: 10%

5. **3 carefully chosen tools > 109 tools** (Agentic Reasoning 2502.04644v2): "Many capabilities already exist inside the reasoning model; external duplicates introduce noise and inappropriate tool selection." The harness should gate tool additions by eval: does adding this tool improve pass rate? If not, remove it.

6. **Context cost hierarchy for architecture decisions** (Claude Code Definitive Guide Practice 11): CLAUDE.md and MCP cost tokens every request; skills cost only descriptions until invoked; subagents run isolated; hooks are zero-context. Choose the right mechanism for each type of information.

**Why this combination wins:**
- Deferred tool loading alone solves the startup context problem but doesn't address ongoing context governance. Memory/index split alone provides structure but doesn't address tool schema bloat. Fusing them creates a unified context governance regime: tools, memory, skills, and conversation each get explicit budgets with hard thresholds.
- Agentic Reasoning's finding that 3 carefully chosen tools outperform 109 LangChain tools provides the empirical justification for the "every addition gated by eval" discipline. Tool Search enables unbounded tool ecosystem growth without context degradation -- you can have 50+ plugins but only ever load 3-5 schemas into context.
- The context cost hierarchy (Claude Code Definitive Guide Practice 11) prevents the "wrong mechanism" failure mode: putting reference material in CLAUDE.md wastes context on every request; putting always-needed rules in a skill means they're violated when the skill isn't loaded.
- Production-hardened numeric thresholds from Claude Code (2KB tool descriptions, 10K token MCP output warning, 25K default max output, 500K per-tool result ceiling, 200 lines / 25KB memory entrypoint) provide concrete implementation targets -- not research parameters, empirically tuned production values.

**Trade-offs:**
- Win: Tool Search enables Lyra's plugin ecosystem to scale to 50+ plugins without context degradation. Without it, loading all tool schemas at startup becomes the binding constraint on plugin count.
- Win: Memory/index split prevents the entrypoint bloat problem: "An entry file that tries to be both table of contents and full text eventually becomes neither."
- Win: Context cost hierarchy provides a decision framework, not just thresholds. Engineers can reason about "where does this information belong?" instead of guessing.
- Loss: First-use tool discovery adds 1 tool search call latency. Small cost for rarely-used tools; can be pre-loaded for frequently-used tools via `alwaysLoad: true`.
- Loss: Managing multiple budgets (system prompt, skills, conversation, tool outputs, memory) requires monitoring infrastructure that doesn't exist yet. Budget violations must be surfaced, not silently exceeded.
- Loss: The "every addition gated by eval" discipline requires evaluation infrastructure (Proposal 4) to be operational first. Without eval gates, the discipline is aspirational, not enforceable.

**Impact: 4/5 | Effort: 3/5 | Tier: (B) Breakthrough**

---

### Proposal 6: Adversarial Verification Panel -- Fusing SWE-Search's Discriminator Debate + Harness Engineering's Independent Verification + Safety Survey's Multi-Agent Attribution + Godel Agent's Self-Inspection

**Fused sources:** SWE-Search (2410.20285v6) + Harness Engineering (Ch.7) + Agent Way Comparative Notes (Practice 6) + Safety Survey (2605.23989v1) + Godel Agent (2410.04444v4)

**What it is:**

1. **Independent verification role** (Harness Engineering Ch.7 + Agent Way Practice 6): `verification_worker != implementation_worker` is a lifecycle invariant. The agent that writes code must never be the one that certifies it. Verification is an independent phase with independent role ownership.

2. **Multi-agent discriminator debate** (SWE-Search): Up to 5 discriminator agents each evaluate all candidate solutions and vote for the best one. 3 debate rounds where agents argue for/against solutions. Improves selection accuracy from value function's 73% to 84%. Key insight: individual judge calibration is unreliable; multi-agent debate surfaces miscalibration.

3. **Process metric verification** (Safety Survey): CVR catches policy/permission breaks. DCR ensures trace coverage. CompVR tracks per-component violations. These complement the discriminator debate by providing objective, non-LLM-judge signals.

4. **Adversarial exploit agent** (Terminal-Bench 2.0 pattern): A dedicated agent probes verification predicates and solution candidates for design flaws that would allow cheating. Mirrors Terminal-Bench 2.0's adversarial exploit agent that probes benchmark tasks.

5. **Identity-anonymized verification** (original Lyra concept, validated by Safety Survey): Verifiers do not know which agent produced which output. Prevents reputation bias. Combined with collusion detection: if verifier A consistently approves verifier B's rejected outputs, flag for investigation.

6. **Self-inspection for verification coverage** (Godel Agent pattern): After verification completes, a self-inspection pass checks: were all changed files verified? Were all edge cases tested? Were all constraint types checked? This is the `self_inspect` primitive from Godel Agent, used for verification completeness rather than self-modification.

**Why this combination wins:**
- SWE-Search's discriminator debate improves accuracy from 73% to 84% but doesn't prevent collusion or bias. Identity anonymization + process metrics close that gap.
- Harness Engineering's independent verification is a binary invariant (verifier != implementer) but doesn't specify HOW verification works. SWE-Search's discriminator debate + Safety Survey's process metrics provide the HOW.
- The adversarial exploit agent closes the loop: verification predicates can be gamed, and the exploit agent actively probes for gullible predicates. This prevents the evaluation from becoming stale.
- Godel Agent's self-inspection primitive, repurposed for verification coverage rather than self-modification, provides a principled "did we actually check everything?" pass that static verification checklists miss.

**Trade-offs:**
- Win: Discriminator debate + process metrics + adversarial probing create a verification system that is harder to game than any single-layer approach.
- Win: Identity anonymization prevents the most common verification failure mode: reputation bias ("Opus said it, so it's probably right").
- Loss: Multi-agent verification adds significant cost: 5 discriminator agents x 3 debate rounds = 15 LLM calls per verification. Only justified for high-risk changes (auth, payments, core architecture).
- Loss: Adversarial exploit agent requires creative attack generation -- an unsolved problem in the general case. The agent can only find flaws it knows how to look for.
- Loss: Process metrics (CVR, DCR) require trace schemas per component. Adding a new component requires adding new trace instrumentation -- a maintenance burden.

**Impact: 3/5 | Effort: 4/5 | Tier: (C) Advanced -- Investigate for V2**

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4) -- Governed Query Loop + Sandbox + Least-Privilege

**Milestone 1.1 (Week 1-2): Formal Query Loop with State Management**
- Implement `QueryLoop` class with formal state object (messages, toolUseContext, autoCompactTracking, recoveryCount, turnCount, transition)
- Implement pre-model governance pipeline: memory prefetch -> message slicing -> tool result budget -> history snip -> microcompact -> context collapse -> autocompact
- Implement event-stream consumption (`for await` pattern) with tool dispatch during streaming
- Implement interrupt ledger closure: synthetic tool results for issued-but-unfinished calls
- Implement 7 distinct stop conditions
- **Gate:** Query loop passes Terminal-Bench 2.0 5-task subset >= Claude Code baseline (52.1%)

**Milestone 1.2 (Week 2-3): Three-Valued Permission Model**
- Implement `allow | deny | ask` permission routing with sticky deny per `tool_use_id`
- Implement Bash-specific dual governance layers (prompt guidance + permission classification)
- Implement `partitionToolCalls()` for safe/unsafe tool separation
- Implement `StreamingToolExecutor` with interruptBehavior per tool (cancel vs. block)
- **Gate:** All tool calls pass through permission gateway; Bash calls receive dual-governance classification

**Milestone 1.3 (Week 3-4): Sandbox Abstraction + Progent-Style Policy Enforcement**
- Implement `SandboxService` interface with three backends (PerCommand, Process, Docker)
- Implement SMT-based symbolic policy enforcement: intercept tool calls, check against policy rules, validate narrowing vs expansion
- Implement defense-in-depth layering: permissions.deny -> sandbox allowlists -> PreToolUse hooks -> policy enforcement -> MCP hooks
- Implement monotonic confinement: `A(P0) ⊇ A(P1) ⊇ A(P2) ⊇ ...`
- **Gate:** ASR < 5% on AgentDojo task subset (baseline: 39.9% no defense, target: Progent's 1.0%)

### Phase 2: Performance (Weeks 5-8) -- Memory Graph + Multi-Agent Orchestration + Context Governance

**Milestone 2.1 (Week 5-6): Structured Memory Graph**
- Implement entity-relationship extraction from conversation turns
- Implement Leiden community detection + LLM community summarization
- Implement GraphRAG retrieval for uncertainty resolution during long reasoning chains
- Implement memory/index split: MEMORY.md index (max 200 lines, 25KB) + topic files
- Implement session memory templates with hard budgets (MAX_SECTION_LENGTH=2,000, MAX_TOTAL=12,000)
- **Gate:** Memory retrieval accuracy on Lyra-internal QA benchmark >= flat memory baseline + 10 points (target: Mind-Map's +18 point GAIA improvement)

**Milestone 2.2 (Week 6-7): Memory-Persisted Multi-Agent Orchestration**
- Implement LeadResearcher agent that saves plans to durable Memory before spawning subagents
- Implement heuristic effort scaling: 1 agent (simple), 2-4 (comparisons), >10 (complex)
- Implement coordinator synthesis rule: "Always synthesize. Never forward raw findings."
- Implement context-isolated subagents with cache-safe fork parameters
- Implement default state isolation with explicit opt-in sharing
- **Gate:** Multi-agent task completion rate >= single-agent baseline + 20% on Lyra research tasks

**Milestone 2.3 (Week 7-8): Context Budget Governance + Deferred Loading**
- Implement Tool Search deferred loading with configurable modes (true/auto/auto:N/false)
- Implement context budget monitoring: system prompt (15%), skills (10%), conversation (50%), tool outputs (15%), memory (10%)
- Implement progressive disclosure for research content: read abstract first, then sections on demand
- Implement tool result clearing as lightweight compaction between phases
- Implement context cost hierarchy: material classified as CLAUDE.md / skill / MCP / subagent / hook
- **Gate:** Context utilization after 50-turn sessions <= 90% of window; no budget threshold violations without explicit alert

### Phase 3: Evaluation Infrastructure (Weeks 9-10)

**Milestone 3.1 (Week 9): Outcome-Driven Evaluation Pipeline**
- Implement property-based verification predicates (not golden-output comparison)
- Implement pass^k statistical reliability metric (pass^4 for regression, pass^8 for capability)
- Implement 7-stage task validation pipeline (simplified from Terminal-Bench 2.0): automated CI -> LLM check -> human review -> multi-model probing
- **Gate:** Lyra regression eval suite passes pass^4 >= 80% on every commit

**Milestone 3.2 (Week 10): Process Metrics + Release Gating**
- Implement CVR (Constraint Violation Rate), DCR (Trace Coverage), CompVR (Component Violation Rate)
- Implement three-tier release gating: Tier 0 (offline, CVR=0) -> Tier 1 (sandbox, CER<0.1%) -> Tier 2 (canary, auto-rollback)
- Implement adversarial exploit agent to probe verification predicates
- **Gate:** Process metrics dashboard live; Tier 0 gating enforced in CI

### Phase 4: Advanced (Weeks 11-12) -- Adversarial Verification + Team Adoption Infrastructure

**Milestone 4.1 (Week 11): Adversarial Verification Panel**
- Implement independent verification role separation (verifier != implementer)
- Implement multi-agent discriminator debate for high-risk changes (5 agents, 3 rounds)
- Implement identity-anonymized verification with collusion detection
- Implement self-inspection for verification coverage completeness
- **Gate:** Verification panel catch rate >= 95% for injected errors on Lyra-internal test suite

**Milestone 4.2 (Week 12): Team Adoption Infrastructure**
- Implement layered CLAUDE.md with fixed precedence (project > team > default)
- Implement tiered approvals by risk (read < workspace mutation < git push/external network/sensitive env)
- Implement staged rollout: Week 1 (CLAUDE.md + verification defined), Week 2 (tiered approvals + first 3 skills), Week 3 (hooks + stale-memory maintenance + baseline replay)
- **Gate:** A newcomer can use Lyra for standard tasks without an expert standing by (Harness Engineering Ch.8 gate criterion)

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Query loop complexity kills iteration speed.** Formal state + 8 governance steps + 7 stop conditions = substantial engineering. Risk of over-engineering before validating simpler approaches. | Medium | High | Phase-gate: implement minimal loop (state object + 3 governance steps + 3 stop conditions) first, validate on 10 tasks, THEN add remaining governance steps. |
| **SMT policy language complexity exceeds team capability.** Z3 SMT solver + symbolic rule language is specialized infrastructure. Only Progent authors have demonstrated successful integration. | Medium | High | If Z3 integration proves too complex, fall back to JSON Schema validation without SMT subset-checking. Progent's ablation shows `Disable Update` (initial policy only, no SMT) still achieves 2.5% ASR -- 16x better than no defense. |
| **Structured memory graph adds latency that degrades interactive use.** Entity extraction + Leiden clustering + LLM summarization per turn may add 2-5s latency. | Medium | Medium | Incremental updates: extract entities per turn, run Leiden only every N turns (N=10 default), summarize communities only on query. Accept latency for long-horizon tasks; disable for interactive mode. |
| **Coordinator synthesis is a single point of failure.** If the coordinator model fails to synthesize correctly, the entire multi-agent system degrades to polite task forwarding. | High | High | Coordinator model must be strongest available (Opus tier). Implement synthesis quality check: coordinator output must reference specific findings from >=50% of subagent reports. If check fails, escalate to human review. |
| **pass^k cost makes every-commit evaluation infeasible.** pass^8 costs ~$3,200+ per full run at GPT-4o pricing. | High | Medium | Tier evaluation: pass^4 for every-commit regression (cheaper), pass^8 for weekly capability evals. Use cheaper models for initial filtering (if pass^1 fails, don't run pass^k). |
| **Adversarial exploit agent cannot find novel attack vectors.** The exploit agent can only probe for design flaws it knows how to look for. Truly novel attacks may slip through. | Medium | Medium | Supplement automated exploit agent with periodic human red-teaming (monthly). Use Safety Survey's attack taxonomy (poisoning, perturbation, injection, boundary confusion) as probe template. |
| **Tool ecosystem growth triggers context budget violations despite deferred loading.** Even with Tool Search, 200+ plugins means the tool name list alone may exceed budget. | Low | High | Implement tool namespace grouping: related tools share a single namespace entry; specific tool selected after namespace chosen. Monitor tool index size as an explicit budget line item. |
| **Circuit breakers trigger too aggressively, blocking legitimate work.** `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` may be too low for tasks that genuinely require multiple compaction cycles. | Low | Medium | Make circuit breaker thresholds configurable per task complexity. Track false-positive breaker triggers via telemetry and tune. Default: 3 for standard tasks, 10 for complex research. |

---

## Impact x Effort Matrix

Proposals ranked by (impact, effort) with tier assignment:

```
Impact
  5 | [P1: Query Loop]     [P2: SMT Sandbox]
    | [P3: Memory+Orch]     


  4 | [P4: Eval Pipeline]  [P6: Verification Panel]
    | [P5: Context Gov]


  3 |
    |


  2 |
    |


  1 |
    +------------------------------------------
      1      2      3      4      5    Effort
```

| Proposal | Impact | Effort | Tier | Rationale |
|----------|--------|--------|------|-----------|
| **P1: Governed Query Loop** | 5 | 5 | (A) Foundation | The architectural backbone. Enables all other proposals. Claude Code's loop architecture validated across millions of sessions. Must be correct before anything else. |
| **P2: SMT-Backed Sandbox** | 5 | 5 | (A) Foundation | Security is non-negotiable. Progent's 1.0% ASR vs. prompt-based 25-73% ASR is decisive. CVSS 9.6 agent CVEs in the wild. Must implement before exposing Lyra to untrusted tasks. |
| **P3: Memory Graph + Multi-Agent** | 5 | 4 | (B) Breakthrough | +90.2% multi-agent gain + +18 point GAIA gain = multiplicative potential. Slightly lower effort than P1/P2 because components have open-source implementations. |
| **P4: Eval Pipeline + Process Metrics** | 4 | 4 | (A) Foundation | Without reliable evaluation, Proposals 1-3 cannot be validated. Three-tier release gating provides concrete numeric thresholds. Must implement alongside P1/P2. |
| **P5: Context Budget Governance** | 4 | 3 | (B) Breakthrough | Highest impact-to-effort ratio. Production-hardened thresholds from Claude Code. Deferred tool loading enables unbounded plugin ecosystem. Lowest engineering risk of all proposals. |
| **P6: Adversarial Verification Panel** | 3 | 4 | (C) Advanced | High cost (15 LLM calls per verification) limits applicability to high-risk changes. Identity anonymization + multi-agent debate are valuable but can be deferred to V2. |

### Implementation Sequencing

```
Phase 1 (Weeks 1-4):  P1 (Query Loop) + P2 (Sandbox) + P4 (Eval Pipeline)
                      -- Foundation must be correct first.

Phase 2 (Weeks 5-8):  P3 (Memory Graph+Orch) + P5 (Context Governance)
                      -- Performance multipliers on top of working foundation.

Phase 3 (Weeks 9-10): P4 completion (process metrics, release gating)
                      -- Evaluation infrastructure must be operational before V2.

Phase 4 (Weeks 11-12): P6 (Verification Panel) + Team Adoption
                       -- Advanced verification; team rollout infrastructure.
```

### Parity Port (Minimum Viable Harness)

Per the Skeptic's challenge from Run 1: before implementing any breakthrough proposal, ship a parity port of Claude Code's harness architecture. This is the baseline that breakthrough proposals must beat:

1. Query loop with formal state, event-stream consumption, interrupt ledger
2. Three-valued permission model with sticky deny
3. Sandbox abstraction (per-command minimum)
4. Context budget with hard thresholds
5. Layered recovery with circuit breakers
6. Independent verification role separation

**Parity gate:** Lyra's parity port performs within 5% of Claude Code on Terminal-Bench 2.0 subset (target: 47-52%). If it does not, do not proceed to breakthrough proposals -- fix the parity port.

---

## Architectural Constitution

From Harness Engineering (Ch.9), serving as invariant gates for all Lyra workstreams:

1. **Treat models as unstable components, not teammates** -- Models may speak like teammates but do not gain teammate-grade stability, accountability, or sustained judgment.

2. **Prompt is part of the control plane** -- Together with runtime, tool schema, memory, and hooks, prompt forms the control plane. If treated as persona decoration, you get rhetorical performance without discipline.

3. **Query loop is the heartbeat of agent systems** -- Real agents depend on continuous execution loops. Input governance, stream consumption, tool scheduling, recovery branches, and stop conditions all belong to heartbeat.

4. **Tools are managed execution interfaces** -- Once models touch shell/filesystem/Git/networks, tools must be scheduled, authorized, interruptible, and ledger-closed.

5. **Context is working memory** -- Being able to stuff context doesn't mean context should be stuffed. Govern in layers. Compact preserves semantic substrate for continued work.

6. **Error paths are main paths** -- Prompt-too-long, max-output-tokens, interrupts, hook loops, compact failures are ordinary weather. Recovery must exist at design time.

7. **Recovery should optimize for continuation** -- After truncation, continuation beats summary. When compaction fails, first restore breathing.

8. **Multi-agent matters because it partitions uncertainty** -- Different responsibility containers for research, implementation, verification, synthesis. State isolated, roles separated, coordinator reconverges.

9. **Verification must be independent** -- Implementers overtrust their own changes. Models do so even more. Verification should be a dedicated independent phase with independent role ownership.

10. **Team institutions matter more than personal tricks** -- Layered CLAUDE.md, explicit approval boundaries, executable skills, lifecycle hooks, traceable transcripts, unified verification definitions.

### Closing Triad

> Harness over excitement, institutions over cleverness, verification over confidence.

### Six-Item Final Checklist

- [ ] Design permission before capability
- [ ] Rollback before autonomy
- [ ] Verification before delivery
- [ ] Context budgets before long dialogue
- [ ] Lifecycle before multi-agent
- [ ] Institutions before expecting team proficiency

---

*Plan methodology: 20 sources examined (12 papers + 3 books + 5 web notes). Every technique cites specific source by paper ID or book/web title + chapter. Breakthrough proposals are combinations of 2+ sources with trade-off depth. Impact x effort rankings use cited benchmark data, not intuition. Run 2 rewrites Run 1 with deep-read evidence throughout.*
