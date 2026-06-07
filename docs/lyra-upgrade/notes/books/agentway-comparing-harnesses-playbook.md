# Agent Way / Comparative Harness Notes — Best Practices Playbook

**Source Book:** _Agent Way / Comparative Harness Notes: The Harness Design Philosophies of Claude Code and Codex_ (2026, @wquguru, agentway.dev)

---

## Practice 1: Identify Your Primary Contradiction Before Designing the Harness

- **What:** Before building or refactoring an agent harness, diagnose whether your primary problem is _runtime instability_ (long sessions spiraling out of control, brittle recovery, skipped verification) or _institutional disorder_ (scattered rules, fuzzy permission boundaries, untraceable instruction sources, non-reproducible team behavior). Build the skeleton that addresses your dominant contradiction first.
- **Why:** The two types of instability require fundamentally different architectural starting points. A team that fears loss of control on site needs a runtime-first harness (Claude Code pattern). A team that fears institutional drift needs an explicit-control-layer harness (Codex pattern). Trying to learn both fully at the same time produces "a failed compromise — neither a stable main loop nor a clear control plane."
- **Lyra route:** §1 (Architecture Philosophy), §11 (Build Strategy)
- **Source:** Chapter 7 (§7.4), Chapter 8 (§8.2 Type 3)
- **Concrete action:** Write down the one-sentence answer to: "The thing that will kill our agent in production is ___." If the answer is session-runtime chaos, build Claude Code-style. If it is governance entropy, build Codex-style.

---

## Practice 2: Decide Where Continuity Sovereignty Lives — and Own It Explicitly

- **What:** Continuity (how turns hand off, how tool results merge, how state survives interruption) is the architectural center of any agent harness. Make an explicit, documented choice about where sovereignty lives: in the main query loop (Claude Code) or in thread/rollout/state infrastructure (Codex). Do not let continuity be a side effect of internal control flow.
- **Why:** "Whoever owns continuity defines the center of the harness." If continuity is a by-product of the loop, you optimize for runtime recovery and field responsiveness. If continuity is carried by thread and state structures, you optimize for auditability, replayability, and out-of-session visibility. Not deciding means neither optimization happens.
- **Lyra route:** §3 (Query Loop / Continuity), §9 (Recovery)
- **Source:** Chapter 3 (§3.1-3.7)
- **Invariants:**
  - `assert continuity sovereignty ∈ {main loop, thread+rollout+state}`
  - `assert interrupt ⇒ tool_result closed (synthetic fallback counts)`
  - `assert long session has compact / truncation / recovery trio`
  - `assert thread.id / session indexing / persisted state = first-class concepts`

---

## Practice 3: Build Tool Governance as a Policy Language, Not a Pile of If/Else

- **What:** Tool permission boundaries should be independently evaluable, schema-typed, and composable — not buried inside runtime if/else chains. Define: tool schemas with `additional_properties=false` (no stray args), an explicit deny/ask/allow decision tree, dedicated governance for high-risk tools (Bash, shell, network), and turn-level parameters for sandbox mode, working directory, and network access.
- **Why:** "If the only answer is 'we also have permission controls,' the permission system has not been designed." A model running the wrong command takes the entire environment down. The permission system must be explainable, auditable, and independently verifiable — it is not a security accessory but the product definition itself.
- **Lyra route:** §5 (Tool System), §10 (Safety/Sandbox)
- **Source:** Chapter 4 (§4.1-4.7), Appendix B.3
- **Invariants:**
  - `assert tool = schema-typed interface, additional_properties=false`
  - `assert approval policy independently evaluable (not buried in code if/else)`
  - `assert high-risk tools (Bash etc) get dedicated governance`
  - `assert {workdir, network, sandbox, approval} explicitly expressible`
- **Concrete thresholds:**
  - `yield_time_ms`: per-tool max execution time before blocking
  - `max_output_tokens`: cap on tool output entering context
  - Bash subcommand cap: limit compound subcommands per call

---

## Practice 4: Make Instruction Sources Identifiable — Fragments, Not Free-Form Text

- **What:** Every instruction entering the system prompt should carry identifiable metadata: source type (AGENTS_MD, SKILL, USER, TEAM, PROJECT), precedence level, and explicit start/end markers. The assembly order must be documented and monotonic (project > team > default; later overrides earlier). An engineer should be able to trace why any given rule appears in the prompt.
- **Why:** When rules multiply without identifiable sources, semantic dilution and contradictory instructions become inevitable. Teams end up unable to explain why the agent behaves a certain way. Structured fragments enable programmatic governance (add, remove, reorder, merge rules without rewriting runtime logic) and make the control plane debuggable.
- **Lyra route:** §2.1 (Prompt Architecture), §4.2 (Context Governance)
- **Source:** Chapter 2 (§2.1-2.6)
- **Invariants:**
  - `assert every instruction has {source, type, precedence}`
  - `assert prompt separates control plane from output style`
  - `assert local-rule scope explicitly labeled`
  - `assert team-rule changes land via diff — not oral agreement`

---

## Practice 5: Context Governance Must Be Structured — Reject "Inject First, Rescue Later"

- **What:** Organize context by semantic unit type, lifetime, and duty — not by how much text can be crammed into the window. Claude Code treats context as working memory (what must survive, what should be compressed). Codex treats context as structured units (source type, scope, state handoff). Both are correct. The "inject first, rescue later" pattern — packing bootstrap files, skill descriptions, and workspace text until the window is tight, then truncating — is the hallmark of an unfinished harness.
- **Why:** "It is solving how much can be inserted, not what must be preserved for continued work." Token waste is the first cost; signal dilution is the deeper one — "the model sees more, but is not necessarily clearer about which working semantics matter next." Teams on the inject-first path "feel 'more informed' at first, then complain about two things at once — tokens burn fast and quality does not climb as context fattens."
- **Lyra route:** §4.2 (Context Governance), §4.1 (Memory Architecture)
- **Source:** Chapter 7 (§7.4 warning), Chapter 8 (§8.3 three-routes taxonomy), Reading Map
- **Concrete thresholds from the book:**
  - `MAX_SECTION_LENGTH`: 2,000 tokens per session-memory section
  - `MAX_TOTAL_SESSION_MEMORY_TOKENS`: 12,000 tokens total budget
  - `AUTOCOMPACT_BUFFER_TOKENS`: 13,000 tokens warning buffer
  - `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES`: 3 (breaker threshold)

---

## Practice 6: Verification Must Be Independent — Never Let the Implementer Certify

- **What:** Multi-agent architecture's first purpose is responsibility splitting, not parallelism. Always maintain a structural barrier between implementation and verification: the agent that writes code must never be the one that certifies it. Verification requires persistent state handoff — the verifier must have access to what was done, why, which tools, which files. Without this, "verification becomes serious-looking theater without material."
- **Why:** Self-review/self-certification produces "comforting and unreliable" results. The insight applies at every scale — from single-session task completion to multi-agent team pipelines. Claude Code emphasizes this through independent verification phases; Codex through auditable thread state and collaboration records. Both agree that "done" cannot be declared by the executing agent alone.
- **Lyra route:** §6 (Multi-Agent), §8 (Verification)
- **Source:** Chapter 6 (§6.1-6.6), Appendix B.5
- **Invariants:**
  - `assert multi-agent's first purpose is responsibility split; parallelism is a bonus`
  - `assert independent verifier exists (verifier != implementer)`
  - `assert delegation = explicit tool or explicit state event, not runtime magic`
  - `assert child-agent {failure, timeout, cancel} ⇒ named cleanup owner`

---

## Practice 7: Subagent Lifecycles Must Have Explicit Protocols

- **What:** Every subagent operation needs protocol-level clarity: spawn with explicit role/prompt/timeout/inherit_approval, send with preemption flag (interrupt=true for priority delivery), wait with min/default/max timeout windows, close with cascade option for descendant cleanup. Orphan handling, timeout recovery, crash reporting, and handle leak prevention must all be designed, not left to happenstance.
- **Why:** "The real problem in multi-agent systems is responsibility." When subagents can crash, hang, leak handles, or leave work incomplete, the system must have named cleanup owners and explicit closure semantics for every failure mode. Claude Code handles this through task cleanup and parent-child abort propagation; Codex through explicit protocol fields and state management.
- **Lyra route:** §6.2 (Subagent Lifecycle), §9 (Recovery)
- **Source:** Chapter 6 (§6.3, §6.5, skeleton code, orphan matrix), Appendix B.5
- **Concrete thresholds:**
  - `wait_agent.timeout`: {min, default, max} window for child-agent response
  - Handle leak: force close + evict on task end without explicit close
  - Cascade: `close_agent(handle, cascade=true)` closes all open descendants

---

## Practice 8: Hooks Need a Formal Lifecycle Event System

- **What:** Hooks must attach to explicit, ordered lifecycle events (`session_start → user_prompt_submit → pre_tool_use → tool exec → post_tool_use → stop`) with guaranteed firing semantics. Separate preview from execution paths (`preview_*` identifies which handlers match; `run_*` actually fires them). Each handler carries: event_name, matcher, timeout, source_path, display_order. Stable ordering ensures replayability.
- **Why:** "Hook capability is made explainable." Without explicit lifecycle events, hooks become ad-hoc callbacks dropped wherever convenient — impossible to reason about, debug, or version. A formal event system turns hooks from local hacks into team infrastructure.
- **Lyra route:** §4.4 (Hooks System), §7 (Team Governance)
- **Source:** Chapter 5 (§5.3, Codex skeleton code, invariants)
- **Invariants:**
  - `assert session_start fires once per thread before any tool_use`
  - `assert pre_tool_use fires immediately before execution; post_tool_use after`
  - `assert stop fires exactly once per thread termination path`
  - `assert preview_* path never executes handlers; only run_* does`
  - `assert each handler has {event_name, matcher, timeout, source_path, display_order}`
  - `assert stable display_order ⇒ replayable ordering across runs`

---

## Practice 9: Skills Are Institutional Assets — Version, Fingerprint, and Install Them

- **What:** Skills should be installed, managed, versionable assets with fingerprints — not text casually reread at startup. Installation should be idempotent (reinstall only when fingerprint mismatch detected). Each skill carries version, source directory, trigger boundary, and display metadata. Treat skills as reusable institutional slices, not long prompts.
- **Why:** Without versioning and fingerprinting, skills proliferate as unmanaged text fragments. Teams cannot tell which version of a skill is active, whether the skill has been modified locally, or whether updates have propagated. "Skill = reusable institutional slice, not long prompt" is the dividing line between a capability and a governance mechanism.
- **Lyra route:** §4.3 (Skills/Plugins), §7 (Team Rollout)
- **Source:** Chapter 5 (§5.3, Codex skills/src/lib.rs pattern, invariants)
- **Invariants:**
  - `assert skill fingerprint mismatch ⇒ reinstall; match ⇒ skip`
  - `assert {skill, rule, hook} carry {version, source, trigger boundary}`
  - `assert local rules layerable by {directory, team, task type}`

---

## Practice 10: Build in the Order of Failure, Not the Order of Demo Aesthetics

- **What:** The construction sequence for a new harness should follow the historical order in which incidents appear: (1) High-risk actions + minimum permission model. (2) Main loop or thread lifecycle. (3) Context governance + recovery paths. (4) Skills, local rules, hooks. (5) Multi-agent, platform capability, complex ecosystem. Do not build complex multi-agent coordination before you have a stable single-agent loop.
- **Why:** "In engineering, many design orders should follow the order of failure, not the order of demo aesthetics." Building capability features (skills, multi-agent, plugins) before hardening the core loop produces a system that looks impressive in demos but "feels lethal to operate" in production.
- **Lyra route:** §11 (Build Strategy/Roadmap)
- **Source:** Chapter 8 (§8.5)
- **Staged gates:**
  - Gate 1: 24h continuous session without token breaker, orphan subagents, or tool_result leaks.
  - Gate 2: Any rule change lands via PR diff alone, no runtime code edits required.
  - Gate 3: A new team member can advance the checklist without verbal tutoring from the original author.

---

## Practice 11: Distinguish Which Rules Must Be Explicit from Which Can Live in Runtime Judgment

- **What:** "Explicitness and flexibility are not natural enemies." The real design work is deciding: which rules must be written down first (instruction boundaries, tool schemas, permission policy, thread state), which judgments can remain in runtime (context ordering, recovery tactics, tool concurrency), which state must persist across sessions, and which experience only needs to live inside session memory. A good harness does not average the two philosophies — it distinguishes them.
- **Why:** The lazy false opposition — "explicit = heavy, rigid" vs. "flexible = agile, deferred structure" — leads to either over-engineering or under-governing. Claude Code is not anti-structure; it knows which troubles must be faced inside runtime. Codex is not anti-flexibility; it knows which boundaries turn into endless disputes if not declared early.
- **Lyra route:** §2 (Control Plane), §11 (Design Decisions)
- **Source:** Chapter 8 (§8.4)

---

## Practice 12: Treat the Model as an Untrustworthy Component — Not an Executor

- **What:** All harness design flows from one admission: "the model cannot be trusted to operate unbounded shell, files, network, or state. It hallucinates, forgets context, and imagines confidence beyond correctness." Design every layer (control plane, tool gate, recovery path, verification) as if the model will eventually produce wrong, dangerous, or incomplete output — because it will.
- **Why:** "Claude Code and Codex are aligned not because they both call tools, but because neither is willing to treat the model as a free-moving executor." Systems that trust the model to self-govern inevitably produce accidents at scale. The harness is the apparatus that keeps an unreliable model from burning the environment down. Success is measured by where and how the system places guardrails, not by how eloquently the model speaks.
- **Lyra route:** §1 (Foundation), §10 (Safety)
- **Source:** Preface, Chapter 1 (§1.1), Chapter 7 (§7.1)
- **Diagnostic:** "Who owns the final control, the model or the harness?" If the answer is ambiguous, the harness has not yet been built.

---

## Practice 13: Use the Six Diagnostic Questions as Architecture Litmus Tests

- **What:** For any agent harness (your own or a third-party one), ask these six questions. If any cannot be answered clearly, the harness is not yet at governance maturity:
  1. Who owns the final control, the model or the harness?
  2. Does continuity live mainly in the loop, or in threads and state?
  3. Before tools act, who stops the last dangerous move?
  4. How do local rules enter the system, and how are they layered?
  5. Who owns verification, and how is it kept independent?
  6. After something goes wrong, what evidence lets the team trace the path back?
- **Why:** "Once these six questions are asked, the system's political family usually reveals itself." Systems that can recite vocabulary from both Claude Code and Codex but cannot answer these questions are "closer to an unfinished prototype."
- **Lyra route:** §12 (Audit/QA), all workstreams
- **Source:** Appendix B (§B.6, B.7)

---

## Practice 14: Reject the "Feature Table" Mindset — Compare Skeletons, Not Checklists

- **What:** When evaluating agent harnesses, do not line up feature checkboxes ("skills", "sandboxes", "sub-agents", "memory"). Shared terminology does not mean shared skeletons. The real comparison is: where does each system place order? What uncertainty is each system designed to counter? Which layer owns the final authority over execution?
- **Why:** "Both Claude Code and Codex have skills, sandboxes, and sub-agents. But seeing shared terminology does not mean their skeletons are the same. It is like noting both cities have bridges — the real question is which river they are trying to cross." Feature-checklist evaluation produces false equivalence and leads teams to adopt systems whose architecture does not match their actual instability.
- **Lyra route:** §1 (Architecture Philosophy), §12 (Evaluation)
- **Source:** Preface, Chapter 1, Chapter 7

---

## Practice 15: Plan for Boundary Migration — Extensions Must Obey General Rules

- **What:** When designing the tool/plugin/extension system, establish early how new capabilities will inherit and comply with general governance rules (permission policies, sandbox constraints, approval chains). "How extensions obey the general rules becomes the ballast: the team that thinks through boundary migration early keeps its extension ecosystem from degenerating into a junk closet."
- **Why:** Extensions that bypass the general permission model create governance gaps that widen over time. Claude Code weaves external capabilities into the situational governance chain; Codex pulls them into the unified tool system as schema-defined, rule-governed objects. Both approaches work — but only if boundary migration is designed upfront, not retrofitted.
- **Lyra route:** §5.3 (Plugin System), §5.4 (MCP Integration)
- **Source:** Chapter 4 (§4.6)
