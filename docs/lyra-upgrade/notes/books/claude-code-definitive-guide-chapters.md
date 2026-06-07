# Claude Code: The Definitive Guide to Agentic Development — Chapter Notes
**Author:** Vladimir Korostyshevskiy (orchestrator); written entirely by Claude Code | **Year:** February 2026 | **Core Thesis:** Claude Code is not a chatbot but an agentic loop — read context, plan, act, verify. Mastery comes from treating it as a delegation system with a finite context budget, not a question-answering machine. The developers who thrive are not faster coders but clearer thinkers who invest in verification infrastructure, context engineering, and organizational knowledge compounding.

---

## Chapter 1: Beyond the Getting-Started Guide
- **Key insight:** Claude Code is an agentic loop (~350 lines of core code), not a request-response pair. Understanding this mental model — briefing a colleague, not querying an oracle — is the single biggest productivity unlock.
- **Best practices:** Four-phase workflow (Explore → Plan → Implement → Commit); treat context as a scarce resource; use permission modes as workflow selectors (Plan mode for exploration, auto-accept for implementation); commit frequently as checkpoints.
- **Anti-patterns:** Micromanaging the agent; skipping exploration/planning and jumping to implementation.
- **Numbers:** Developers can fully delegate only 0–20% of tasks; 60%+ of work is AI-assisted but human-supervised; Claude Code builds 70–80% of a production stack today.
- **Relevant to Lyra §4.x:** Agentic loop architecture; delegation model; context budget awareness.

## Chapter 2: The Permission and Trust Architecture
- **Key insight:** The permission system is a five-scope hierarchy (Managed > CLI args > Local > Project > User) with deny-before-ask-before-allow evaluation. Hooks are the extensibility layer — 13+ lifecycle events giving programmable control over every phase of the agentic loop.
- **Best practices:** Layer defenses (permissions.deny + sandbox + hooks); use MCP over raw bash for sensitive data access; start with maximum restriction and paper-trading environments; deploy reference devcontainers for CI; write deny rules narrow and allow rules broad.
- **Anti-patterns:** Running `--dangerously-skip-permissions` outside an isolated container; assuming checkpoints cover bash-command side effects.
- **Hook types:** Command (deterministic checks), Prompt (LLM-evaluated judgment), Agent (multi-turn investigation with file access). Async hooks run in background without blocking.
- **Relevant to Lyra §4.x:** Defense-in-depth permission architecture; hook lifecycle events (PreToolUse, PostToolUse, Stop, SubagentStop, TaskCompleted); MCP as secure integration layer.

## Chapter 3: Context Engineering
- **Key insight:** CLAUDE.md is the always-on file — content costs context on *every request*. The developers who get extraordinary results are better context engineers, not better prompters. The context cost hierarchy: CLAUDE.md and MCP cost every turn; skills load on demand (descriptions only); subagents are isolated; hooks are zero-cost.
- **Best practices:** Keep CLAUDE.md under 500 lines; focus on what Claude cannot infer from code; use `@path/to/import` syntax for progressive disclosure; use Compact Instructions section for critical rules; end-of-session CLAUDE.md updates create compounding institutional memory; targeted additions that address specific observed errors outperform general instructions; spec documents survive compaction and session restarts.
- **Anti-patterns:** Putting reference material in CLAUDE.md instead of skills; bloat above 500 lines (instructions compete with each other); not updating CLAUDE.md after productive sessions; trusting auto-compaction at 95% instead of manual compaction at 80%.
- **Numbers:** Subagents are dramatic for context isolation — 14 subagents can run without exhausting the main 200K-token window (main session at 143K/200K after orchestration).
- **Relevant to Lyra §4.x:** CLAUDE.md as persistent agent memory; skills vs. always-on context; compaction strategy; institutional memory compounding.

## Chapter 4: Multi-Agent Orchestration
- **Key insight:** Subagents provide context isolation more than parallelism. The strict two-level hierarchy (orchestrator → workers, no recursion) is deliberate — recursive agent trees produce chaos. Agent teams add seven coordination primitives for sustained collaboration between specialists. The cheapest orchestration strategy is usually the correct one.
- **Best practices:** Plan before parallelizing (10K tokens of planning prevents 500K tokens of wasted execution); use expensive models for orchestration and cheap models for execution; start with a single agent and add agents only when the single agent is insufficient; define agent roles by concrete task ("Review files in src/api/ for SQL injection") not by personality ("You are the cautious reviewer"); keep subagent returns concise — write detailed findings to a file, return only the path.
- **Anti-patterns:** Multi-agent personality conflicts (four-agent trading hierarchy degraded to one because the consultant agent became obstructionist and the CEO deferred too readily); launching parallel agents without a plan; using teams when a single well-prompted session can handle the task.
- **Numbers:** QA swarm of 5 agents audited an entire blog (146 URLs, 83 posts) in ~3 minutes; plan-first pattern costs ~10K tokens vs. 500K+ for misdirected execution.
- **Relevant to Lyra §4.x:** Multi-agent architecture; subagent context isolation; agent team coordination primitives; persistent memory for agents; cost optimization (expensive brain, cheap hands).

## Chapter 5: MCP — Connecting Claude Code to Everything
- **Key insight:** Every MCP tool definition costs context tokens at session start. MCP is categorically more secure than raw bash for sensitive data access because credentials are server-side. Tool search defers loading for scale. The three-layer architecture (AI creation → visual display → no-code refinement) minimizes token costs.
- **Best practices:** Run `/mcp` at session start and when Claude's behavior changes unexpectedly; use deferred loading for 40+ tools; name tools with server-specific prefixes; build MCP servers for sensitive data sources instead of giving bash access; commit `.mcp.json` to version control; use MCP hook patterns (`mcp__server__tool`) for logging, validation, and transformation; classify data first, then choose access architecture.
- **Anti-patterns:** Using curl through bash for sensitive data (credentials in context); eagerly loading all MCP servers; expecting background subagents to use MCP tools.
- **Numbers:** Production deployments exist with 41+ MCP tools across multiple servers; a sovereign wealth fund serves ~9,000 portfolio managers with MCP integrations; Go + JavaScript architecture reported 80–90% token savings vs. direct code analysis.
- **Relevant to Lyra §4.x:** Plugin/tool interface architecture; secure external service integration; MCP as plugin model; tool search and deferred loading.

## Chapter 6: CI/CD and Headless Automation
- **Key insight:** The `-p` flag transforms Claude Code from an interactive REPL into a Unix utility. Devcontainers with network isolation and `--dangerously-skip-permissions` are the standard pattern for safe unattended execution. The fan-out pattern enables batch AI processing across repositories.
- **Best practices:** Fan-out pattern with `--allowedTools` for safe batch processing; async hooks for background test runners; TaskCompleted hooks block completion until tests pass; pre-commit hooks create automated backpressure at the commit boundary; use `--from-pr` to resume session context across review cycles; start interactive, identify repetitive patterns, progressively move to headless.
- **Anti-patterns:** Running headless outside containers with full permissions; not scoping allowedTools on fan-out operations.
- **Relevant to Lyra §4.x:** CI/CD integration for autonomous agent loops; headless execution; backpressure via pre-commit hooks.

## Chapter 7: IDE Integration Done Right
- **Key insight:** Claude Code's architecture separates engine from interface. The terminal is the primary surface; the IDE is a supplementary view. Cross-surface teleport (`/teleport`, `&` prefix) enables fluid session migration. The autocomplete gap is architectural, not accidental — no single tool dominates every interaction scale.
- **Best practices:** Terminal-first with IDE assists; hybrid toolchain (Claude Code for agentic work + separate inline completion tool); use cloud sessions for long-running tasks; teleport sessions between surfaces as needed.
- **Anti-patterns:** Trying to force terminal-grade functionality through the editor extension; relying exclusively on one surface.
- **Relevant to Lyra §4.x:** Surface-agnostic engine architecture; teleport/session migration pattern.

## Chapter 8: Prompt Craft for Agentic Tools
- **Key insight:** Verification criteria (tests, expected output, visual targets) are the single highest-leverage prompting technique — they convert one-shot generation into iterative refinement. Your linting configuration, type checker, and test suite are part of your prompt (backpressure). Spec-Driven Development (Research → Spec → Refine → Tasks → Done) is superior to prompt-code-debug-repeat.
- **Best practices:** Always provide verification criteria; plan before implementing (10K-token plan prevents 500K-token misdirection); state constraints explicitly (what cannot change, trade-off preferences, flexibility boundaries); use exhaustive questioning ("ask me questions exhaustively before starting"); strawman proposals give Claude something to react to; self-critique after complex implementations; use vague prompts for exploration, specific prompts for implementation.
- **Anti-patterns:** Vague implementation prompts; implicit constraints; trusting confident output without verification; correcting over and over in a degraded context (fix: `/clear` and write a better initial prompt).
- **Numbers:** Exhaustive questioning improves first-pass quality by 30–50%; TDD as backpressure produces dramatically better output; the difference between vague and specific implementation prompts is measured in debugging hours.
- **Relevant to Lyra §4.x:** Verification-first design; backpressure via tooling; Spec-Driven Development workflow; delegation mindset.

## Chapter 9: Working with Large and Legacy Codebases
- **Key insight:** Claude Code's effectiveness on large codebases is limited by task clarity and context quality, not codebase size. Git worktrees enable parallel independent sessions. The three-input workspace pattern (raw data + supplementary text + goal prompt) is a repeatable analysis methodology. The language barrier for legacy systems is dissolving.
- **Best practices:** Use git worktrees for parallel work on the same repo; deploy Explore subagents liberally; parallel research subagents for multi-perspective understanding; task dependency management with `blocks`/`blockedBy` for wave-based execution; spec-driven refactoring (research → specify → execute in parallel); CLAUDE.md as living data catalog replacement.
- **Numbers:** One documented case achieved 99.9% numerical accuracy across a 12.5M-line codebase in 7 hours; a three-year frontend rewrite completed in weeks; storage layer migration: 14 tasks, 15+ files, one afternoon (vs. 2–3 days manually).
- **Relevant to Lyra §4.x:** Spec-driven refactoring; parallel subagent research; CLAUDE.md as institutional memory.

## Chapter 10: Failure Modes and Recovery
- **Key insight:** Claude Code fails regularly — understanding how it fails is more valuable than understanding how it succeeds. The most common failure mode is context exhaustion (silent degradation, not errors). The slot machine approach (commit, time-box 30 minutes, accept-or-restart) often beats correction spirals.
- **Best practices:** Watch for context exhaustion tells (repeated suggestions, forgotten instructions, degraded coherence); re-establish bash state in every command (env vars do not persist); use `/checkpoint` for rewind (but git is the universal undo); commit before every complex task; after two failed corrections, `/clear` and write a better prompt; provide explicit simplicity constraints to counter Claude's complexity default.
- **Five named anti-patterns:** Kitchen sink session (fix: `/clear` between unrelated tasks); correcting over and over (fix: restart after 2 corrections); over-specified CLAUDE.md (fix: ruthless pruning); trust-then-verify gap (fix: always verify); infinite exploration (fix: scope narrowly or use subagents).
- **Numbers:** Roughly one-third of tasks succeed on first attempt (higher with verification infrastructure, lower without); the 33-day trading experiment showed 22.4% max drawdown despite 7.6% final gain.
- **Relevant to Lyra §4.x:** Failure mode catalog; slot machine recovery; anti-patterns catalog; context exhaustion mitigation; vibe coding/trading trap.

## Chapter 11: Team Adoption Patterns
- **Key insight:** Non-technical teams extract categorically different value (new capabilities) than engineers (augmented velocity). The guided adoption path (Q&A → small fixes → plan mode → full autonomy) prevents premature abandonment. The maintenance-to-scale progression maps months 1–3 (MVP), 3–6 (features), 6+ (hardening).
- **Best practices:** Commit CLAUDE.md to version control; share slash commands as team conventions; cross-team knowledge sharing (demonstrate workflows); create persona-adaptive CLAUDE.md for non-developers; centralized MCP configuration; organization-wide CLAUDE.md at system directories.
- **Numbers:** Legal team: accessibility tool built in 1 hour; marketing: ad creation from 2 hours to 15 minutes; enterprise: one org saved 500K+ hours, 89% AI adoption with 800+ agents; 75% of engineers save 8–10+ hours/week.
- **Relevant to Lyra §4.x:** Team adoption patterns; role-based tool assignment; non-technical user workflows; institutional knowledge compounding.

## Chapter 12: The Economics and Strategy of AI-Assisted Development
- **Key insight:** The real economic story is capability expansion, not speed. ~27% of AI-assisted tasks would not have been done at all without AI. Three compounding multipliers (agent capabilities × orchestration improvements × accumulated human experience) produce step-function gains. The developer's role shifts from code production to architecture, coordination, and quality evaluation.
- **Best practices:** Match model to task (Opus for architecture, Sonnet for implementation, Haiku for exploration); prompt caching amortizes CLAUDE.md costs across turns; per-seat pricing for stable usage, pay-as-you-go for variable patterns; hybrid toolchain (Claude Code + inline completion tool).
- **Numbers:** 70–90% timeline compression is consistent across case studies; 3-year rewrite → weeks; 3–6 month platform → 8 weeks; $multi-thousand professional services → a few evenings of AI-assisted work.
- **Relevant to Lyra §4.x:** Model routing by task complexity; cost optimization patterns; capability expansion framing.
