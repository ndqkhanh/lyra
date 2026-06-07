# Harness Engineering: A Design Guide to Claude Code — Chapter Notes

**Author:** @wquguru (agentway.dev) | **Year:** 2026 | **Core Thesis:** AI coding agents require a harness — continuously active control structures (prompt layering, query loops, tool permission systems, context governance, recovery paths, multi-agent verification) — because models are inherently unstable components. Reliability comes from the harness, not from model intelligence. "System First, Model Second."

**Source files analyzed:** `constants/prompts.ts`, `query.ts`, `QueryEngine.ts`, `toolOrchestration.ts`, `StreamingToolExecutor.ts`, `useCanUseTool.tsx`, `claudemd.ts`, `memdir.ts`, `autoCompact.ts`, `compact.ts`, `forkedAgent.ts`, `coordinatorMode.ts`, `LocalAgentTask.tsx`, `hooksConfigManager.ts`, `systemPrompt.ts`

---

## Preface: Harness, Terminals, and Engineering Constraints

- **Key insight:** Harness Engineering is defined as "continuously active control structures that bound model behavior in engineering environments." A model that outputs only text creates interpretation cost when it fails; a model that runs commands, writes files, and modifies repositories creates execution artifacts when it fails.
- **Best practices:** Design the system assuming the model is unstable by nature. The design question is not "is the model smart enough" but "does the system impose enough constraint."
- **Anti-patterns:** Treating the model as a teammate with stable responsibility; treating the harness as an accessory layer or "emotional defense against model capability."
- **Design rationale:** Claude Code is worth studying because it stays deliberately restrained — it does not assume model correctness, tool safety, that more context is always better, that errors are rare, or that multi-agent equals stronger capability.
- **Relevant to Lyra:** Foundation for Lyra's entire architectural philosophy — the supervisor daemon, worktree isolation, and verification panel all embody "harness thinking."

---

## Chapter 1: Why Harness Engineering Matters

- **Key insight:** Five harness layers emerge from Claude Code source: (1) constrained conversation system with context boundaries, (2) continuous query loop with stateful multi-turn execution, (3) tool scheduling discipline (parallel vs. serial by concurrency safety), (4) high-density constraints on Bash (the most dangerous tool), (5) errors treated as main-path conditions, not exceptions.
- **Best practices:**
  - Package high-risk capability as high-constraint capability (Bash needs special governance, not generic treatment)
  - Split prompt into layers with explicit responsibilities
  - Runtime decides parallel/serial tool execution based on tool properties — never let the model decide
  - Error handling must have recovery paths designed at runtime, not as afterthought catch blocks
- **Anti-patterns:** Trusting Bash tool equally with read-only tools; letting models decide tool execution order; treating failures as rare exceptions.
- **Numbers/benchmarks:** Source cited: `src/constants/prompts.ts:175-199`, `src/query.ts:219-241`, `src/services/tools/toolOrchestration.ts:19-63`
- **First principle:** "The key capability of an agent system is constrained execution."
- **Relevant to Lyra §3.1, §3.2, §4.1:** Lyra's provider abstraction, tool permission system, and worktree isolation directly implement these layers.

---

## Chapter 2: Prompt Is Not Personality — Prompt Is the Control Plane

- **Key insight:** Claude Code's system prompt is not one monolithic text but a layered assembly of behavioral blocks — closer to a runtime protocol than to a character biography. The prompt defines identity, system-level rules (permissions, denied-action behavior, auto-compact awareness), and engineering constraints (no casual requirement addition, no hiding failed validation).
- **Best practices:**
  - Structure prompt with strict precedence: `override > coordinator > agent > custom > default`, with `appendSystemPrompt` always last
  - Split prompt sections into cacheable vs. uncacheable (dynamic) segments — cache behavior is control-plane design
  - Prompt must integrate with memory/CLAUDE.md systems, not float as isolated decoration
  - In proactive mode, agent prompt APPENDS to default prompt, never replaces it
  - `buildMemoryLines()` extends prompt duty from "constrain current behavior" to "constrain how future knowledge is deposited"
- **Anti-patterns:** Treating prompt as persona text; writing one "universal prompt"; allowing "latest write wins" precedence; ignoring cache cost of prompt composition.
- **Numbers/benchmarks:** Precedence chain: 5 layers, append always last. Source: `buildEffectiveSystemPrompt()` at `src/utils/systemPrompt.ts:28`
- **Second principle:** "Prompt is valuable only when it is integrated into explicit control structure."
- **Relevant to Lyra §2.1 (Skills), §3.4 (Memory):** Lyra's skill loading and CLAUDE.md layering should follow this precedence model.

---

## Chapter 3: Query Loop — The Heartbeat of an Agent System

- **Key insight:** The query loop (`queryLoop()`) is the execution center, not the model call. The loop maintains cross-iteration state (`messages`, `toolUseContext`, `autoCompactTracking`, `maxOutputTokensRecoveryCount`, `hasAttemptedReactiveCompact`, `pendingToolUseSummary`, `turnCount`, `transition`). Input governance happens BEFORE model invocation — memory prefetch, message slicing, tool result budget, history snip, microcompact, context collapse, autocompact.
- **Best practices:**
  - State is a formal object, not scattered booleans; it must be monotonic across turns
  - Put context governance BEFORE model reasoning: "clean the site first, then execute"
  - Model output must be consumed as an event stream (`for await`), not a synchronous blob — enables tool dispatch while streaming
  - Interrupt handling must close the ledger: synthetic tool results for issued-but-unfinished calls, never leave dangling `tool_use` blocks
  - Stop conditions must distinguish: completion, failure, recovery, continuation — never conflate "turn ended" with "task completed"
- **Anti-patterns:** Treating agent as one-shot Q&A; no cross-turn state object; "retry if failed" as only stop condition; no interrupt ledger closure.
- **Stop-condition failure matrix:** 7 distinct stop paths documented with pre-state, trigger, and next-action columns.
- **Third principle:** "The core capability of an agent system is maintaining a recoverable execution loop."
- **Relevant to Lyra §4.4 (Autonomy):** Lyra's agent loop must replicate this governance-before-invocation pattern, especially the interrupt ledger and multi-state stop semantics.
- **Relevant to Lyra §3.3 (Context):** The pre-model governance sequence (memory prefetch → slice → budget → snip → microcompact → collapse → autocompact) is the exact pattern Lyra's context pipeline should follow.

---

## Chapter 4: Tools, Permissions, and Interrupts

- **Key insight:** Tools are managed execution interfaces, not natural extensions of model capability. Permission is an organ of the system with three-valued semantics (allow/deny/ask), not a boolean. Interrupt is first-class semantics with dedicated lifecycle handling.
- **Best practices:**
  - `partitionToolCalls()` separates safe/unsafe tools by `isConcurrencySafe()`, executing safe in parallel batches and unsafe serially
  - In parallel paths, context modifiers are buffered and replayed in original block order — parallelism may improve throughput but must not break causality
  - Permission chain: `hasPermissionsToUseTool()` → allow/deny/ask; deny is sticky for the same `tool_use_id`; ask never auto-escalates to allow
  - `StreamingToolExecutor` defines interruptBehavior per tool (cancel vs. block) and generates synthetic error messages for sibling failure, user interrupt, and streaming fallback
  - Bash gets TWO governance layers: prompt guidance (detailed rules for git/PRs/hooks) + permission/safety classification (subcommand-count cap, classifier routing)
- **Anti-patterns:** Allowing model intent to equal execution authority; treating Bash identically to read tools; boolean (yes/no) permission models; no tool-result closure on interrupt.
- **Concrete pattern:** Three-valued permission model (allow/deny/ask) with explicit routing for ask-state (coordinator, swarm worker, classifier, interactive approval).
- **Fourth principle:** "Tools are managed execution interfaces; permission is an organ of the agent system."
- **Relevant to Lyra §4.1 (Safety), §4.5 (Verification):** Lyra's Bash sandboxing and permission tiering should adopt the three-valued model and Bash-specific high-density constraints.

---

## Chapter 5: Context Governance — Memory, CLAUDE.md, and Compact as a Budgeting Regime

- **Key insight:** Context is working memory, not a warehouse. Claude Code governs context as an "expensive, inflation-prone, self-polluting budget" with explicit thresholds and hard limits. The MEMORY.md entrypoint is an INDEX (max 200 lines, 25,000 bytes), not body text. Session memory templates distill sessions into operational continuation briefs (MAX_TOTAL_SESSION_MEMORY_TOKENS = 12,000), not chat log dumps.
- **Best practices:**
  - Split instruction sources into layers: managed (`/etc/claude-code/CLAUDE.md`), user (`~/.claude/CLAUDE.md`), project (root & `.claude/CLAUDE.md`), local (`CLAUDE.local.md`) — loaded by precedence and directory proximity
  - CLAUDE.md supports `@include` but only for explicitly allowed text extensions — prevents accidental binary/doc inclusion
  - Session memory template sections: Current State, Task specification, Files and Functions, Workflow, Errors & Corrections, Codebase Documentation, Learnings, Key results, Worklog
  - `getEffectiveContextWindowSize()` subtracts `MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20,000` for compact output reserve; `AUTOCOMPACT_BUFFER_TOKENS = 13,000` for early-warning buffer
  - Post-compact reconstruction: clear stale readFileState, regenerate file attachments, reinject plans, plan mode, invoked skills, deferred tools, MCP deltas, session hooks, compact boundary messages
  - Per-skill truncation beats dropping — "even when cutting, keep critical leading constraints rather than dropping whole blocks"
- **Anti-patterns:** Mixing long-lived policy with temporary chat context; letting entrypoint files bloat (index becomes neither TOC nor body); treating compact as "summarize the chat" instead of "controlled reboot with runtime semantic restoration."
- **Budget thresholds:** MAX_ENTRYPOINT_LINES=200, MAX_ENTRYPOINT_BYTES=25,000, MAX_SECTION_LENGTH=2,000, MAX_TOTAL_SESSION_MEMORY_TOKENS=12,000, MAX_OUTPUT_TOKENS_FOR_SUMMARY=20,000, AUTOCOMPACT_BUFFER_TOKENS=13,000, MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES=3
- **Fifth principle:** "Context is working memory. Governance exists to keep the system able to continue work."
- **Relevant to Lyra §3.4 (Memory), §3.3 (Context):** Lyra's Zettelkasten memory, COMPASS briefs, and dreaming consolidation should adopt the index-vs-body split and budget thresholds. The post-compact semantic restoration pipeline is critical for Lyra's auto-compaction design.

---

## Chapter 6: Errors and Recovery — An Agent System That Keeps Working After Failure

- **Key insight:** The least trustworthy sentence in engineering is "under normal conditions." Claude Code does not treat errors as rare. Recovery is a predesigned runtime mechanism with layered escalation (low-cost first, heavier last), circuit breakers, and anti-loop guards. Recovery should prioritize continuation over politeness.
- **Best practices:**
  - Some errors are withheld from immediate surfacing and routed through recovery branches first (prompt_too_long, media_size_error, max_output_tokens)
  - Recovery layers for prompt-too-long: (1) `recoverFromOverflow()` flush staged collapse, (2) `tryReactiveCompact()`, (3) surface directly + skip stop hooks
  - `hasAttemptedReactiveCompact` flag prevents dead loops — same-class failures are not blindly retried after compact already attempted
  - For max_output_tokens: first raise cap (lower cost), then if still failing, append meta message: "continue directly; no apology; no recap; continue from half-sentence; split into smaller chunks"
  - Auto-compact circuit breaker: `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3` — after threshold, skip compact entirely rather than burning API calls
  - Compact itself can hit prompt-too-long → `truncateHeadForPTLRetry()` strips older API rounds in chunks and retries
  - Interrupt is a state transition requiring semantic closure, not a UX event
- **Anti-patterns:** One-size-fits-all recovery hammer; retry-without-circuit-breaker; polite recaps after truncation (burns budget, increases drift); no recovery for recovery tools themselves.
- **"True engineering politeness is not trapping users inside failure states."**
- **Sixth principle:** "An agent system shows its reliability by maintaining explainable, bounded, and resumable execution order after failure."
- **Portable principles:** Layer recovery paths; recovery logic must be loop-safe; automated recovery needs counters and circuit breakers; after truncation, continuation beats summary; interruptions are semantic failure states requiring closure; reliability is proven by whether the system can still explain itself after errors.
- **Relevant to Lyra §4.6 (Reliability), §4.1 (Safety):** Lyra's crash detection, recovery branches, and circuit-breaking should replicate this layered recovery escalation pattern.

---

## Chapter 7: Multi-Agent Work and Verification — Managing Instability Through Division of Labor

- **Key insight:** Multi-agent is not about speed — it's about partitioning uncertainty into different containers (research, implementation, verification, synthesis) with clear responsibility boundaries. Fork is a runtime-control problem first: cache safety, state isolation, lifecycle observability.
- **Best practices:**
  - First principle of forked agents is CACHE SAFETY: `CacheSafeParams` includes `systemPrompt`, `userContext`, `systemContext`, `toolUseContext`, `forkContextMessages` — must match parent for prompt-cache hits
  - State isolation by DEFAULT: `createSubagentContext()` isolates all mutable state; sharing requires explicit opt-in flags (`shareSetAppState`, `shareSetResponseLength`, `shareAbortController`)
  - Coordinator mode's most important rule: "Always synthesize. When workers return findings, coordinator must digest and convert them into concrete prompts; must not forward raw findings and outsource understanding again"
  - Verification is explicitly separated from implementation: coordinator prompt stacks "implementation self-check PLUS independent verification worker"
  - Verification applies to memory too, not just code: "when memory conflicts with present reality, trust the current observed state and update or delete stale memory"
  - Subagent lifecycle: `SubagentStart` and `SubagentStop` hooks; parent abort propagates to children; cleanup handlers prevent orphan tasks; exit code 2 feeds stderr back to subagent for continuation
- **Anti-patterns:** No cache alignment between parent and child (parallel waste, not parallel acceleration); sharing mutable state by default; "multi-agent" where all agents do the same thing; coordinator as a forwarding service; verification as an afterthought.
- **Lifecycle invariants:** `child.CacheSafeParams == parent.CacheSafeParams`; `child.mutable_state isolated unless opt_in.share_*`; `parent.abort ⇒ propagate(child.abort)`; `SubagentStart fired ⇒ SubagentStop fired eventually`; `verification_worker ≠ implementation_worker`
- **Seventh principle:** "Multi-agent systems depend on clear division of labor: research, implementation, verification, and synthesis must run under different constraint containers."
- **Relevant to Lyra §4.2 (Multi-agent), §4.5 (Verification):** Lyra's coordinator-worker model, verification panel (identity anonymization + ReTAS + collusion detection), and worktree isolation directly map to these patterns. The "verification_worker ≠ implementation_worker" invariant is foundational.

---

## Chapter 8: Team Adoption — Turning a Smart Tool into a Sustainable Workflow

- **Key insight:** Expert success does not automatically translate to safe team reuse. Personal technique works because of continuous supervision, background knowledge, and situational judgment — none of which transfer automatically. The team problem is turning order that lived in expert heads into a workflow ordinary contributors can repeat.
- **Best practices:**
  - **Staged rollout order (not "build skills first"):** Week 1 — layered CLAUDE.md live, shared verification defined, forbidden zones encoded as repo-level constraints. Week 2 — approvals tiered by consequence, first ≤3 skills with precondition/postcondition/verification contract, explicit "done with known issues" policy. Week 3 — stop/post-tool-use hooks, monthly stale-memory maintenance, baseline replay (Git diff/PR/CI) gap-free.
  - **CLAUDE.md should be stable, not encyclopedic:** Repository-level hard constraints, shared verification expectations, collaboration discipline. NOT: rapidly changing temporary processes, narrow-task instructions, details better expressed as commands/skills/scripts.
  - **Verification definition matters earlier than skill count:** Standardize what "done" means (which task classes need independent verification, minimum verification actions, whether failed verification can be marked "done with known issues") before building many skills.
  - **Skills are workflow modules, not institutional objects:** Answer: what task class, what tools by default, direct or forked execution, verifiable result required.
  - **Tiered approvals by risk, not tool name:** Read/listings/analysis = lower risk; workspace mutation = higher; Git push/external network/sensitive env = highest. Control irreversibility and environment sensitivity.
  - **Hooks belong AFTER baseline governance is stable:** Hooks are advanced automation. Start with instruction files, code-review rules, CI expectations, small skill set.
  - **Baseline replayability before advanced audit trails:** Git diffs + PR comments + CI logs (layer 1, baseline) before transcript paths + tool-call records + hook events (layer 2, advanced).
- **Anti-patterns:** Building many skills before defining verification; elaborate approval taxonomy from day one; CLAUDE.md as running bulletin board; hooks as first automation step; chasing full agent auditability before having clean review standards.
- **Gate criterion:** "A newcomer can use it without an expert standing by — the workflow is mature."
- **Eighth principle:** "Team adoption works best when acceptable boundaries, verification standards, and recurring workflows become stable early."
- **Relevant to Lyra §5 (Team adoption/rollout):** Lyra's rollout strategy should follow this staged approach — verification definitions first, approvals tiered by risk, skills as workflow modules, hooks deferred.

---

## Chapter 9: Ten Principles of Harness Engineering

- **Key insight:** Synthesis chapter compressing all findings into 10 principles distilled from source-code structure, not from abstract philosophy.
- **The 10 Principles:**
  1. **Treat models as unstable components, not teammates** — Models may speak like teammates but do not gain teammate-grade stability, accountability, or sustained judgment.
  2. **Prompt is part of the control plane** — Together with runtime, tool schema, memory, and hooks, prompt forms the control plane. If treated as persona decoration, you get rhetorical performance without discipline.
  3. **Query loop is the heartbeat of agent systems** — Real agents depend on continuous execution loops. Input governance, stream consumption, tool scheduling, recovery branches, and stop conditions all belong to heartbeat.
  4. **Tools are managed execution interfaces** — Once models touch shell/filesystem/Git/networks, tools must be scheduled, authorized, interruptible, and ledger-closed.
  5. **Context is working memory** — Being able to stuff context doesn't mean context should be stuffed. Govern in layers. Compact preserves semantic substrate for continued work.
  6. **Error paths are main paths** — Prompt-too-long, max-output-tokens, interrupts, hook loops, compact failures are ordinary weather. Recovery must exist at design time.
  7. **Recovery should optimize for continuation** — After truncation, continuation beats summary. When compaction fails, first restore breathing.
  8. **Multi-agent matters because it partitions uncertainty** — Different responsibility containers for research, implementation, verification, synthesis. State isolated, roles separated, coordinator reconverges.
  9. **Verification must be independent** — Implementers overtrust their own changes. Models do so even more. Verification should be a dedicated independent phase with independent role ownership.
  10. **Team institutions matter more than personal tricks** — Layered CLAUDE.md, explicit approval boundaries, executable skills, lifecycle hooks, traceable transcripts, unified verification definitions.
- **One final sentence:** "Harness Engineering asks how systems can still behave like engineering systems when models themselves are not reliable."
- **Closing triad:** Harness over excitement, institutions over cleverness, verification over confidence.
- **Relevant to Lyra:** These 10 principles are Lyra's architectural constitution. Every workstream (§2-§5) should map back to one or more of these principles.

---

## Appendix A: Checklists — Turning Principles into Executable Constraints

- **Key insight:** Principles without checklists decay into judgments that sound right but don't hold up in practice. Six checklists provided.
- **A.1 Agent Runtime Design Checklist:** Explicit query loop? Cross-turn state object? Event-stream model output? Interrupt ledger closure? Distinct stop semantics? Context budgeting for long sessions?
- **A.2 Prompt Design Checklist:** Layered with explicit duties? Source precedence explicit? Dangerous operations as explicit rules? Runtime enforcement separated from prompt? Team-maintainable?
- **A.3 Tool and Permission Design Checklist:** Unified orchestration? Concurrency safety proof required? Allow/deny/ask branching? High-risk tools special-cased? Interrupt/fallback/sibling-failure closure semantics? Causal chain preserved?
- **A.4 Context Governance Checklist:** Long-lived rules vs. session memory vs. temporary dialogue layered? Entrypoint/body separation? Token budgets? Compact output space pre-reserved? Post-compact work-semantics restored? Compact-failure recovery strategy?
- **A.5 Error Recovery Checklist:** Recoverable errors routed to recovery branches first? Layered from low to high destructiveness? Anti-loop guards? Continuation over recap after truncation? Counters and circuit breakers? Interrupts as failure states requiring closure?
- **A.6 Multi-Agent Checklist:** Cache-safe params? Default state isolation? Role separation (research/implementation/verification/synthesis)? Coordinator synthesizes? Independent verification? Observable/interruptible/reclaimable lifecycle? Parent abort propagation?
- **A.7 Team Adoption Checklist:** Layered CLAUDE.md? Verification standardized before skill scale-up? Approvals tiered by consequence? Hooks at appropriate timing? Transcript/task/hook evidence retained? Stale-memory maintenance policy?
- **A.9 Final Short Checklist (six items):** Design permission before capability; rollback before autonomy; verification before delivery; context budgets before long dialogue; lifecycle before multi-agent; institutions before expecting team proficiency.
- **A.10 Implementation Seeds:** Four pseudocode skeletons for `queryLoop`, `permissionDecision`, `forkAgent`, `recoverFromError`.
- **Relevant to Lyra:** These checklists should be used as Lyra's implementation gates — each workstream's plan should satisfy the relevant checklist before marking complete.

---

## Appendix B: Diagrams — Drawing the Runtime Skeleton

- Six diagrams: (1) Global control plane (5 layers: user interaction, control plane, execution loop, external capability, persistence/observability), (2) Query loop main cycle + recovery branches, (3) Tool batch ordering + StreamingToolExecutor, (4) Context sources + compact rebuild, (5) Coordinator-worker flow + verification separation, (6) Team governance map.
- **Key insight:** Claude Code is "an explicit state-machine system, not a pile of prompts plus a few tools." The model is neither topmost nor bottommost — it's one phase inside the query loop.

---

## Appendix C: Source Map — Which Files Ground Each Chapter

- Maps all 9 chapters to their primary supporting source files (`src/constants/prompts.ts`, `src/query.ts`, `src/QueryEngine.ts`, `src/services/tools/*`, `src/utils/*`, `src/coordinator/*`, `src/hooks/*`, `src/memdir/*`, `src/tasks/*`) with brief argument-basis statements for each.
- **Relevant to Lyra:** This source map is the traceability model Lyra's own architecture should replicate — every architectural claim should be traceable to a specific implementation location.
