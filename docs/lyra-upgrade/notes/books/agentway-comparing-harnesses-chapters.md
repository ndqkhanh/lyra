# Agent Way / Comparative Harness Notes — Chapter Notes

**Author:** @wquguru | **Year:** 2026 (2026-04-01, rev fbf2b4) | **URL:** agentway.dev

**Core Thesis:** Claude Code and Codex converge on the shared conviction that models are untrustworthy and that a harness (control plane) is required to domesticate them — but they diverge fundamentally in *where order is placed*. Claude Code places order in the runtime loop (continuity, recovery, field governance), while Codex places order in explicit control-layer structures (typed instruction fragments, policy languages, thread/rollout/state infrastructure). The lesson for later builders is not to pick a side but to identify their primary contradiction and grow the corresponding skeleton first.

**Target Audience:** Engineers building or refactoring AI coding agent harnesses; teams evaluating agent architectures; researchers studying control-plane design for LLM-based systems.

---

## Reading Map & Preface (pp. 1-9)

- **Key insight:** This is Book Two of a series. Book One ("Nine Structural Judgments from Claude Code") extracts general Harness Engineering principles from Claude Code as a single specimen. This book compares Claude Code and Codex side-by-side to reveal which design choices are consensus and which are merely different engineering routes.
- **Key insight:** Both systems admit models are unreliable — "a model cannot be trusted to execute without constraints. Shells, filesystems, permissions, tool calls, teams, long sessions, and recovery paths are messy realities. A harness is that messy reality."
- **Key insight:** The comparison is "centered mainly on the harness" — the core challenge is keeping models from losing control in terminals, filesystems, permission boundaries, and team institutions.
- **Core diagnosis of weak systems:** Many third-party harnesses "advertise memory, skills, compaction, and multi-agent support, yet their context-governance axis still amounts to pushing more text into prompt first and truncating or rescuing later." This "inject first, rescue later" pattern looks more informative but burns tokens and weakens working semantics.
- **Best practices:**
  - Read Book One first to extract general Harness Engineering principles.
  - Then read this comparison to observe how principles land differently across two concrete systems.
  - If your biggest pain is long-session instability → start with Claude Code-style runtime discipline.
  - If your biggest pain is scattered rules and fuzzy boundaries → start with Codex-style explicit control layers.
- **Anti-patterns:** Assuming both books are duplicates; treating the comparison as a feature checklist; being "impressed by the apparent fullness of context" without checking whether governance is real.
- **Relevant to Lyra §1 (Architecture Foundation):** The entire premise — that a harness must be architected deliberately — mirrors Lyra's foundational question.

---

## Chapter 1: Why We Compare Claude Code and Codex (pp. 10-12)

- **Key insight:** Both systems share one critical admission: "the model cannot be trusted to operate unbounded shell, files, network, or state. It hallucinates, forgets context, and imagines confidence beyond correctness." Once a model touches a terminal, the question is "who cleans up the mess?"
- **Key insight:** Claude Code is "a system born from incident reviews" — read `query.ts`, `toolOrchestration.ts`, `compact.ts` and you see "a system that imagines failure, fatigue, and rollback."
- **Key insight:** Codex expresses distrust through explicit modules: threads, rollouts, fragment instructions, exec policies, sandboxing, and tool schemas. "Each declares its responsibilities instead of leaving them to the model's intuition."
- **Key insight:** The direction a team takes determines its culture. Runtime continuity → obsess over recovery, interruption, state pollution, tool choreography. Explicit control → obsess over instruction boundaries, config hierarchies, tool schemas, policy languages, persistent thread state.
- **Best practices:**
  - Do not treat harness design as a "who has more buttons" comparison.
  - Recognize which starting point your team naturally gravitates toward.
  - Avoid "mixing them without clarity and losing both runtime discipline and institutional order."
- **Anti-patterns:** Calling these systems "models that write code"; treating the comparison as a feature checklist.
- **Relevant to Lyra §2 (Control Plane):** Establishes the two fundamental philosophies Lyra must choose between or synthesize.

---

## Chapter 2: Two Control Planes — Dynamic Prompt Layers vs. Structured Fragments (pp. 13-16)

- **Key insight:** Both Claude Code and Codex treat prompts as part of a *behavioral control plane* — not merely tone-exercise. The difference is mechanism: dynamic runtime assembly vs. structured fragment injection.
- **Key insight — Claude Code assembly line:** System prompts are a production line: defaults → append prompts → agent roles → CLAUDE.md → memory → output styles. "Flexibility lets one loop handle many scenarios, but ordering is critical — wrong ordering dilutes instructions or lets conflicts slip through." The guiding intuition: "control follows the scene — it cannot freeze into static rules."
- **Key insight — Codex filing-room approach:** Instructions are typed, bounded fragments with markers (`AGENTS_MD_START_MARKER`, `SKILL_OPEN_TAG`, etc.), wrapped into `ResponseItem::Message` objects. "Codex tries hard not to make the model guess where a rule came from."
- **Invariants identified:**
  - Every fragment has matching (START_MARKER, END_MARKER).
  - Fragment source is identifiable (AGENTS_MD, SKILL, USER).
  - Precedence: project > team > default (monotonic).
  - CLAUDE.md overlay order: team → personal → project (later overrides earlier).
- **Trade-offs:** Runtime assembly is flexible but hard to formalize (agile but under-declared). Structured fragments are explicit but heavier — markers, types, serialization, injection all need definitions (clear but carrying ongoing structural cost).
- **Best practices:**
  - Separate control plane from tone/expression layer.
  - Define clear precedence rules for instruction layering.
  - Make instruction sources identifiable (who said this, why does it apply here).
  - Choose between dynamic assembly and structured fragments based on whether your primary worry is volatile sessions or unclear rule sources.
- **Anti-patterns:** Treating prompts as tone exercises; letting rules multiply without precedence; "one feels like a production floor, the other like a bureaucracy" — pick the skeleton that matches your instability.
- **Relevant to Lyra §2.1 (Prompt Architecture), §4.2 (Context Governance):** Directly applicable to how Lyra should layer system prompts and manage CLAUDE.md / AGENTS.md equivalents.

---

## Chapter 3: Where the Heartbeat Lives — Query Loop vs. Thread, Rollout, and State (pp. 17-23)

- **Key insight:** "Treating an agent system as 'multi-turn chat' is like treating a database as 'a patient notebook' — it hides the real architectural problem." Continuity is the hard thing: how this turn picks up from the last, how tool results merge, how interruption closes out, how overgrown context reorganizes, whether failure triggers retry or faithful reporting.
- **Key insight — Claude Code:** Continuity is compressed into `query()` and `queryLoop()`. The loop owns messages, tool-use context, compact tracking, output-token recovery counters, pending summaries, turn counts, transitions. "Claude Code treats them as legitimate loop states rather than avoiding them. The design has rough engineering texture — not always elegant, but often more robust."
- **Key insight — Codex:** Continuity is distributed across `codex_thread`, `thread_manager`, `rollout`, `state_db_bridge`, `state`, and `message_history`. Thread is a first-class concept in the SDK: `runStreamed()`, `thread.started`, thread sovereignty is literal. "Continuity is no longer 'the loop is still going' but 'a thread is being recorded and constrained by an explicit state structure.'"
- **Failure matrix:** Comprehensive comparison of how each system handles: user interrupt with tool in flight, model output truncation, prompt-too-long, process restart, recovery exhaustion.
- **Recovery comparison:** Claude Code = "emergency crew on site" (proximity enables faster response); Codex = "dispatch center with archives" (traceability enables audit).
- **Key insight:** "Whoever owns continuity defines the center of the harness." Sovereignty in the loop steers teams toward runtime questions; sovereignty in threads steers teams toward interface and governance questions.
- **Best practices:**
  - Decide explicitly where continuity sovereignty lives (main loop vs. thread+rollout+state).
  - Every interrupt must close `tool_result` (synthetic fallback counts).
  - Maintain a compact/truncation/recovery trio for long sessions.
  - Thread IDs and session indexing must be first-class concepts.
- **Anti-patterns:** Letting continuity be a side effect of looping; relying on the model to "remember" across turns; failing to close tool_result on interrupt.
- **Relevant to Lyra §3 (Query Loop/Continuity), §9 (Recovery):** Directly informs Lyra's heartbeat/loop architecture and recovery path design.

---

## Chapter 4: Tools, Sandboxes, and Policy Languages (pp. 24-29)

- **Key insight:** "A model saying the wrong thing wastes time; running the wrong command takes the directory, repository, processes, and workflow down with it. What distinguishes AI coding systems is who owns the final interpretive authority before a tool acts."
- **Key insight — Claude Code:** Tool governance is field-dispatch: concurrency depends on schema and `isConcurrencySafe()`, context modifications preserve replay order, streaming execution must handle interrupts. "The harness resembles a site supervisor attached to the model, watching which tool goes first, which can be parallelized, which must serialize, how results are accounted for."
- **Key insight — Codex:** Tools are typed interfaces first — `exec_command` owns explicit fields (cmd, workdir, shell, tty, yield_time_ms, max_output_tokens, login, approval parameters). `execpolicy` is its own crate (Policy, Rule, Evaluation, Decision, parser). "Execution boundaries have become a small policy language rather than a handful of if/else checks."
- **Concrete thresholds:**
  - `yield_time_ms`: max ms a single exec may block.
  - `max_output_tokens`: cap on tool output admitted into context.
  - `additional_properties=false`: blocks model from injecting stray args.
  - Bash subcommand cap: max compound subcommands per Bash call.
- **Approval decision tree (Codex):** schema validation → deny rules → ask rules → sandbox-relaxed allow → sandbox-strict ask.
- **Key insight:** "Sandbox, approval, and permission are not security accessories — for a coding agent they define what the product is." Claude Code = "executes while being watched"; Codex = "declares the execution contract before starting."
- **MCP and boundary migration:** "How extensions obey the general rules becomes the ballast: the team that thinks through boundary migration early keeps its extension ecosystem from degenerating into a junk closet."
- **Best practices:**
  - Tools must be schema-typed interfaces with `additional_properties=false`.
  - Approval policy must be independently evaluable (not buried in code if/else).
  - High-risk tools (Bash) get dedicated governance, not flat treatment.
  - Workdir, network, sandbox, and approval must all be explicitly expressible.
  - Design for boundary migration early — extensions must obey general rules.
- **Anti-patterns:** "If the only answer is 'we also have permission controls,' the permission system has not been designed." Single-string command interfaces for shell tools.
- **Relevant to Lyra §5 (Tool System), §10 (Safety/Sandbox):** Core reference for Lyra's tool permission model and execution policy design.

---

## Chapter 5: Skills, Hooks, and Local Rules — Village Law (pp. 30-33)

- **Key insight:** "Any general-purpose coding agent that starts real work for a team collides with the same fact: companies, repositories, directories, and people all have their own rules and habits. A system that cannot absorb those local institutions stays trapped in demo environments."
- **Key insight — Claude Code:** Local governance lives in CLAUDE.md, skills, hooks, and session memory. "Claude Code resembles an engineer who copies down local custom wherever it goes — highly practical across projects, directories, and local constraints, but without cleanup, knowledge expands as field patches."
- **Key insight — Codex:** Skills are installed, tracked by fingerprint, versioned assets. The hook engine splits events into `session_start`, `pre_tool_use`, `post_tool_use`, `user_prompt_submit`, `stop` — a formal lifecycle event system with `preview_*` and `run_*` paths. "Hook capability is made explainable."
- **Invariants for hooks:**
  - `session_start` fires once per thread before any tool_use.
  - `pre_tool_use` fires immediately before execution; `post_tool_use` after.
  - `stop` fires exactly once per thread termination path.
  - `preview_*` path never executes handlers; only `run_*` does.
  - Each handler has {event_name, matcher, timeout, source_path, display_order}.
  - Stable display_order ensures replayable ordering across runs.
  - Skill fingerprint mismatch → reinstall; match → skip.
- **Organizational implications:** Field-memory approach adapts faster to new repos but needs editorial cleanup at scale (textbooks by province). Structured injection expands more cleanly (uniform distribution, versioning, audit) but requires team to accept explicit institutions first.
- **Best practices:**
  - Local rules must be layerable by {directory, team, task type}.
  - Skills must be reusable institutional slices, not long prompts — with version/source/trigger boundary.
  - Hooks must attach to explicit lifecycle events (pre/post/session_start/stop).
  - Each {skill, rule, hook} carries {version, source, trigger boundary}.
- **Anti-patterns:** Everyone writing their own CLAUDE.md with no editorial cleanup; dropping callbacks wherever convenient instead of formal lifecycle events; absorbing field experience without institutionalization.
- **Relevant to Lyra §4.3 (Skills/Plugins), §4.4 (Hooks System), §7 (Team Governance):** Directly applicable to Lyra's plugin/hook architecture and team rollout strategy.

---

## Chapter 6: Delegation, Verification, and Persistent State (pp. 34-37)

- **Key insight:** "The real problem in multi-agent systems is responsibility." If one system executes, summarizes, verifies, and casually writes its own review, the result is "comforting and unreliable: 'good job.'"
- **Key insight — Claude Code:** Multi-agent handles outsourced exploration, split implementation, synthesis, and independent verification. "Verification must be independent from implementation — 'done' is not declared by the executing agent alone."
- **Key insight — Codex:** Delegation is a formal tool capability via `create_spawn_agent_tool_v*`, `create_wait_agent_tool_v*`, `create_send_message_tool`, `create_close_agent_tool_v*`. Preemption (`interrupt=true`), waiting (timeout min/default/max), and cleanup (`cascade=true`) are protocol fields.
- **Orphan/timeout failure matrix:** Documents parent abort cascade, wait_agent timeout handling, send_input preemption, close_agent cascade, child crash reporting, handle leak cleanup.
- **Key insight:** "Verification turns ceremonial mainly because state handoff is weak. What was done, why, which tools, which files — if that only lives in the executor's head, verification becomes serious-looking theater without material."
- **Key insight:** Claude Code repairs executors too immersed in the scene; Codex repairs collaboration that must leave structured evidence.
- **Best practices:**
  - Multi-agent's first purpose is responsibility split (parallelism is a bonus).
  - Independent verifier must exist (verifier != implementer).
  - Delegation must be an explicit tool or state event, not runtime magic.
  - Child-agent {failure, timeout, cancel} must have a named cleanup owner.
- **Anti-patterns:** Self-review/self-verification; multi-agent without responsibility partitioning; orphan subagents; weak state handoff making verification theatrical.
- **Relevant to Lyra §6 (Multi-Agent), §8 (Verification):** Core reference for Lyra's multi-agent delegation and verification architecture.

---

## Chapter 7: Convergence and Divergence (pp. 38-41)

- **Key insight:** "Yes, they genuinely converge." Both accept: prompt does not control everything, tools must be constrained, long sessions require state governance, local rules must enter the system, multi-agent requires role partitioning and verification.
- **Key insight — Claude Code's axis:** Begin from the query loop → handle continuity in runtime → preserve order with compaction, tool orchestration, interrupts, recovery → connect field rules through skills, hooks, verification.
- **Key insight — Codex's axis:** Begin from explicit module boundaries → turn instructions into fragments → turn tools into schemas → turn execution boundaries into policy → turn sessions into thread/rollout/state → turn local rules into structured assets and event systems.
- **Political metaphor:** Claude Code = "runtime republic" (power in main loop and field dispatch, order through continuous negotiation with reality). Codex = "constitutional control plane" (power written into types, fragments, policy, threads; runtime judges inside explicit framework).
- **Key insight:** "Harness is never only a pile of technical parts. It is also a way of distributing power. Who defines the boundary, who interprets state, and who owns the final authority of execution all eventually appear in architecture."
- **Three routes taxonomy:**
  1. Claude Code treats context as working memory (what must survive, what should be compressed).
  2. Codex treats context as structured units (source type, scope, state handoff).
  3. "OpenClaw family" treats context as a prompt container (what else can still be packed in before the limit) — the "inject first, rescue later" pattern.
- **Warning about the third route:** "Teams on the third route feel 'more informed' at first, then complain about two things at once — tokens burn fast and quality does not climb as context fattens. It is solving how much can be inserted, not what must be preserved for continued work."
- **Best practices:**
  - Choose one primary contradiction — do not try to be both fully dynamic and fully explicit simultaneously.
  - If you fear loss of control on site, strengthen the runtime heartbeat first.
  - If you fear institutional drift, make instruction, tool, policy, and state explicit first.
  - Once the primary contradiction stabilizes, gradually build the opposite side.
  - Avoid the "inject first, rescue later" context governance pattern.
- **Anti-patterns:** Splicing attractive features from both systems without making actual tradeoffs; refusing to make a tradeoff altogether; the "OpenClaw family" approach of context-as-container.
- **Relevant to Lyra §1 (Philosophy), §11 (Design Decisions):** Synthesizes the entire architectural debate into a decision framework for Lyra.

---

## Chapter 8: If You Need to Build Your Own Harness (pp. 42-47)

- **Key insight:** "The least interesting ending is the consumerist one — choose A or B." The useful question: whose lessons should you learn first, and which part first.
- **Three team shapes and their prescriptions:**
  - **Type 1 (long sessions lose control):** Learn Claude Code first. Stabilize the loop — institutional aesthetics can wait. Gate: 24h continuous session without token breaker, orphan subagents, or tool_result leaks.
  - **Type 2 (rules scattered, boundaries unclear):** Learn Codex first. Turn instruction, tool, policy, and thread into explicit concepts. Gate: any rule change lands via PR diff alone, no runtime code edits required.
  - **Type 3 (starting from scratch):** Most dangerous. Pick one primary contradiction, design main skeleton around it, add opposite side at minimum level. Gate: a new member can advance the checklist without verbal tutoring from the original author.
- **Staged builder checklists** provided for each team shape (weekly milestones).
- **What to learn from Claude Code:** Query loop state mind-set, compaction/context governance, tool orchestration/interrupt handling, subagent lifecycle/verification independence, treating failure paths as main paths.
- **What to learn from Codex:** Instruction fragmentation, tool schemas, explicit approval/policy expression, thread/rollout/state infrastructure, hook events and skill-asset management.
- **Key insight:** "Explicitness and flexibility are not natural enemies. The real question is whether you have defined clearly which things must be explicit and which can be left to field judgment."
- **Practical build order from zero:** (1) High-risk actions + minimum permission model; (2) Main loop or thread lifecycle; (3) Context governance + recovery paths; (4) Skills, local rules, hooks; (5) Multi-agent, platform capability, complex ecosystem. "In engineering, many design orders should follow the order of failure, not the order of demo aesthetics."
- **Best practices:**
  - Learn from Claude Code to understand on-site stability; learn from Codex to understand organizational order over time.
  - Teams learning only the first → rich in experience, poor in institution.
  - Teams learning only the second → elegant institutions, fragile field behavior.
  - The right reason to borrow something is that it repairs your weakness, not that someone else already built it.
  - Build order should follow the order of failure, not demo aesthetics.
- **Anti-patterns:** Choosing A or B like a consumer product; building a "failed compromise" that is neither stable nor governable; deferring structure while relying on experience alone; making runtime problems sound too elegant; letting the control layer dissolve into tacit understanding.
- **Relevant to Lyra §11 (Build Strategy):** The definitive chapter for Lyra's implementation roadmap and priority ordering.

---

## Appendix A: Source Map (pp. 48-51)

- Lists specific source files on both Claude Code and Codex sides that each chapter's analysis relies on. No new engineering content — purely a citation map.

## Appendix B: Checklists (pp. 52-55)

- **Six checklist domains:** Control plane, Continuity, Tool/Approval, Local Governance, Multi-Agent/Verification, System Classification (Claude Code-like, Codex-like, or unfinished prototype).
- **Six final diagnostic questions:**
  1. Who owns the final control, the model or the harness?
  2. Does continuity live mainly in the loop, or in threads and state?
  3. Before tools act, who stops the last dangerous move?
  4. How do local rules enter the system, and how are they layered?
  5. Who owns verification, and how is it kept independent?
  6. After something goes wrong, what evidence lets the team trace the path back?
- **Concrete thresholds reference:**
  - `MAX_ENTRYPOINT_LINES`: 200 (entry file line cap)
  - `MAX_SECTION_LENGTH`: 2,000 (session-memory per-section cap)
  - `MAX_TOTAL_SESSION_MEMORY_TOKENS`: 12,000 (session-memory total budget)
  - `AUTOCOMPACT_BUFFER_TOKENS`: 13,000 (autocompact warning buffer)
  - `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES`: 3 (breaker threshold)
  - `yield_time_ms`: per-tool (max ms a single exec may block)
  - `wait_agent.timeout`: min/default/max (child-agent wait window)
- **Event orderings:** session_start → user_prompt_submit → pre_tool_use → tool exec → post_tool_use → stop; spawn_agent → send_input* → wait_agent → close_agent (cascades).
- **Best practices:** Use these six questions as a litmus test for any agent harness. If a system can recite vocabulary from both sides but cannot explain who owns order, it is an unfinished prototype.
- **Relevant to Lyra §12 (Audit/QA):** Directly usable as Lyra's architecture review checklist.
