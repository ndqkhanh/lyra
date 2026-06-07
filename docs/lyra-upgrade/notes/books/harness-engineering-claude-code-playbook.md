# Harness Engineering: A Design Guide to Claude Code — Best Practices Playbook

> Extracted from *Harness Engineering: A Design Guide to Claude Code* by @wquguru (agentway.dev, 2026)
> 15 concrete practices distilled for Lyra's architecture and implementation

---

## Practice 1: The Three-Valued Permission Model
- **What:** Implement tool authorization as `allow | deny | ask` (not boolean yes/no). Deny is sticky per `tool_use_id`. Ask never auto-escalates to allow. Route "ask" decisions to coordinator, classifier, or interactive approval.
- **Why:** Boolean permissions collapse when the system genuinely cannot decide. A third state ("ask") is required so the system doesn't silently authorize dangerous operations or reject safe-but-unfamiliar ones. Terminals don't fill missing semantics — they only execute.
- **Lyra route:** §4.1 (Safety), §4.5 (Verification) — Lyra's tool sandbox and permission gateway.
- **Source:** Chapter 4 (§4.4-4.5); `useCanUseTool.tsx`, `PermissionResult.ts`

---

## Practice 2: Pre-Model Input Governance Pipeline
- **What:** Before every model invocation, run this exact governance sequence: (1) memory prefetch, (2) skill discovery prefetch, (3) slice valid messages after compact boundary, (4) apply tool result budget, (5) history snip, (6) microcompact, (7) context collapse, (8) autocompact last.
- **Why:** Delegating "turn chaos into order" to the model shifts runtime responsibility onto probability distributions. "Clean the site first, then execute" — it's less elegant but usually more stable. Runtime governs first, then passes cleaner inputs to the model.
- **Lyra route:** §3.3 (Context), §4.4 (Autonomy) — Lyra's context pipeline and agent loop.
- **Source:** Chapter 3 (§3.3); `query.ts:297-453`

---

## Practice 3: Post-Compact Semantic Reconstruction (Not Just Summarization)
- **What:** After compact, rebuild working context by: clearing stale readFileState, regenerating file attachments, reinjecting plan attachments, plan-mode attachments, invoked-skills attachments, deferred tools, MCP instruction deltas, running session-start hooks and post-compact hooks, and writing compact boundary messages with pre-compact token counts.
- **Why:** Compact that only produces a summary line leaves the agent "remembering roughly" but missing tool state, plan state, and attachment state — requiring turns to rediscover itself. Compact is a controlled reboot with semantic substrate restoration.
- **Lyra route:** §3.3 (Context), §3.4 (Memory) — Lyra's auto-compaction and COMPASS brief design.
- **Source:** Chapter 5 (§5.6); `compact.ts`

---

## Practice 4: Cache-Safe Fork Parameters for Subagents
- **What:** Every forked subagent must share `CacheSafeParams` with its parent: `systemPrompt`, `userContext`, `systemContext`, `toolUseContext`, `forkContextMessages`. Never casually change `maxOutputTokens` (affects cache keys). Without cache alignment, parallel acceleration becomes parallel waste.
- **Why:** Multi-agent is first a runtime economics problem. If each child re-burns parent context from scratch, what looks like parallel acceleration is re-computation waste. Fork is runtime-controlled branching — cache discipline comes first, then specialization.
- **Lyra route:** §4.2 (Multi-agent), §4.8 (Economics) — Lyra's worktree-isolated subagents and cost-weighted routing.
- **Source:** Chapter 7 (§7.2); `forkedAgent.ts`

---

## Practice 5: Default State Isolation with Explicit Opt-In Sharing
- **What:** Subagent mutable state is isolated by DEFAULT. Clone `readFileState`, create child abort controllers, suppress permission prompts in `getAppState`, make `setAppState` a no-op, recreate `nestedMemoryAttachmentTriggers` and `loadedNestedMemoryPaths`. Sharing requires explicit opt-in flags: `shareSetAppState`, `shareSetResponseLength`, `shareAbortController`.
- **Why:** The main value of child agents is containing local chaos away from the main thread. Research misreads, temporary file observations, exploratory reasoning, and in-flight tool decisions should not be blindly written back. Sharing requires consent; isolation is default ethics — closer to transactional database design than chat tabs.
- **Lyra route:** §4.2 (Multi-agent), §4.1 (Safety) — Lyra's worktree isolation model.
- **Source:** Chapter 7 (§7.3); `createSubagentContext()`

---

## Practice 6: Layered Recovery with Cost-Gated Escalation
- **What:** Recovery must escalate from lowest-cost/lowest-destructiveness to highest: for prompt-too-long — (1) flush staged context collapse, (2) reactive compact (once per turn), (3) surface error directly and skip stop hooks. Never hit every error with one giant hammer.
- **Why:** Good recovery tries to preserve fine-grained context first and escalates only when required. One-size-fits-all recovery burns context budget and creates self-reinforcing failure loops.
- **Lyra route:** §4.6 (Reliability) — Lyra's error recovery and crash detection paths.
- **Source:** Chapter 6 (§6.2-6.3); `query.ts:1065-1166`

---

## Practice 7: Continuation-First Truncation Recovery
- **What:** When max_output_tokens hits: (1) raise cap and retry (no meta-message), (2) if still failing, append a concise meta message: "continue directly; no apology; no recap; if cut mid-sentence, continue from that half sentence; split remaining work into smaller chunks."
- **Why:** Polite recaps after truncation burn additional budget and increase semantic drift. Eventually the system spends turns recapping itself instead of doing the task. Engineering politeness is not trapping users inside failure states.
- **Lyra route:** §4.6 (Reliability), §3.3 (Context) — Lyra's continuation strategies.
- **Source:** Chapter 6 (§6.4); `query.ts:1185+`

---

## Practice 8: Circuit Breakers on Automated Recovery
- **What:** Track `consecutiveFailures` on auto-compact. After `MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`, skip compact entirely and surface the issue. Recovery systems without brakes are like vehicles without brakes.
- **Why:** Source documents real-world waste: "large amounts of API calls were once wasted on repeated autocompact failure." Any automated recovery must be countable, rate-limited, and breakable. You may fail, but you may not fail infinitely without memory.
- **Lyra route:** §4.6 (Reliability) — Lyra's circuit-breaking for all automated recovery paths.
- **Source:** Chapter 6 (§6.5); `autoCompact.ts`

---

## Practice 9: Recovery for Recovery Itself
- **What:** Compact requests themselves can hit prompt-too-long. Implement `truncateHeadForPTLRetry()` — when compact input is too large, strip older API rounds in chunks from the head and retry compact. Prioritize restoring breathing over preserving high-fidelity history.
- **Why:** Many designs hide this scenario because it's embarrassing. Engineering systems prioritize survival over elegance. When the system is choking, first priority is not deadlocking the user.
- **Lyra route:** §4.6 (Reliability) — Lyra's multi-layered fallback paths.
- **Source:** Chapter 6 (§6.6); `compact.ts`

---

## Practice 10: Coordinator Synthesis as Non-Delegable Capability
- **What:** In multi-agent architectures, the coordinator MUST synthesize worker findings — digest and convert them into concrete prompts with specific files, locations, and changes. The coordinator must NEVER forward raw findings and outsource understanding again. "Always synthesize."
- **Why:** The scarce capability in multi-agent is not parallel output — it's recompressing distributed local knowledge into actionable, verifiable next steps. Without this, multi-agent degrades into polite task forwarding. Research can be distributed; understanding must reconverge.
- **Lyra route:** §4.2 (Multi-agent) — Lyra's coordinator/supervisor daemon design.
- **Source:** Chapter 7 (§7.4); `coordinatorMode.ts`

---

## Practice 11: Independent Verification with Role Separation
- **What:** Separate task flow into Research → Synthesis → Implementation → Verification. Verification must be an independent phase with independent role ownership. Verification proves effectiveness, not merely code existence: run tests with the feature enabled, investigate errors instead of dismissing them as unrelated, stay skeptical, test independently, do not rubber-stamp.
- **Why:** "I changed code" and "the change is correct" are separated by a wide river, and models are good at building paper bridges over it. Independent verification prevents "can modify code" from impersonating "can deliver outcomes."
- **Lyra route:** §4.5 (Verification) — Lyra's verification panel with identity anonymization, ReTAS, and collusion detection.
- **Source:** Chapter 7 (§7.5); `coordinatorMode.ts`

---

## Practice 12: Memory/Index Split with Hard Budgets
- **What:** Long-term memory entrypoint (MEMORY.md) is an INDEX only (max 200 lines, 25,000 bytes). Actual content goes in dedicated topic files. When entrypoint exceeds limits, trigger truncation with explicit warning: "only partial load performed; move details into topic files."
- **Why:** Entrypoint files are loaded frequently. Once they bloat, context is gradually dragged by index weight. An entry file that tries to be both table of contents and full text eventually becomes neither.
- **Lyra route:** §3.4 (Memory) — Lyra's Zettelkasten graph memory and COMPASS brief indexing.
- **Source:** Chapter 5 (§5.3); `memdir.ts`

---

## Practice 13: Session Memory as Operational Continuation Brief
- **What:** Session memory template sections: Current State, Task specification, Files and Functions, Workflow, Errors & Corrections, Codebase/System Documentation, Learnings, Key results, Worklog. MAX_SECTION_LENGTH = 2,000, MAX_TOTAL_SESSION_MEMORY_TOKENS = 12,000. Update with Edit tool only; never talk about note-taking itself; keep Current State aligned with latest work.
- **Why:** Session memory is not "save another copy of chat history." It distills the session into the minimum structure needed to continue working. Context budget is working memory, and working memory must stay operable.
- **Lyra route:** §3.4 (Memory), §3.3 (Context) — Lyra's session continuity and dreaming consolidation.
- **Source:** Chapter 5 (§5.4); `SessionMemory/prompts.ts`

---

## Practice 14: Team Rollout — Verification Definition Before Skill Count
- **What:** Standardize verification definition FIRST — which task classes need independent verification, what minimum actions verification must include (tests, local runs, logs, human acceptance), whether failed verification may be marked "done with known issues." Only then package recurring workflows into skills/commands. Skills answer: what task class, what tools by default, direct or forked execution, verifiable result required.
- **Why:** Even a smart system learns to satisfy the weakest bar available. If verification is vague, automation only speeds up ambiguity. Skills can replicate process, but only verification definitions replicate quality.
- **Lyra route:** §5 (Team Adoption), §4.5 (Verification) — Lyra's rollout strategy and quality gates.
- **Source:** Chapter 8 (§8.4)

---

## Practice 15: Prompt Precedence as Constitutional Structure
- **What:** Assemble system prompt with fixed precedence: `override > coordinator > agent > custom > default`, with `appendSystemPrompt` always last. In proactive mode, agent prompt APPENDS to default, never replaces it. Split prompt sections into cacheable vs. dynamic (uncacheable) segments. Prompt is not static copy — it connects to memory/CLAUDE.md systems.
- **Why:** Without fixed precedence, prompt degrades into a "graffiti board where whoever writes last is in charge." A general constitution can be extended by a job description but must not be wiped out by it. Customization is allowed; order is not abandoned.
- **Lyra route:** §2.1 (Skills), §3.4 (Memory) — Lyra's skill loading, CLAUDE.md layering, and prompt assembly.
- **Source:** Chapter 2 (§2.2-2.5); `systemPrompt.ts`, `prompts.ts`, `systemPromptSections.ts`

---

## Quick-Reference Mapping: Practices to Lyra Workstreams

| Practice | Lyra § | Key Mechanism |
|----------|--------|---------------|
| 1. Three-valued permissions | §4.1 Safety | allow/deny/ask tool gateway |
| 2. Pre-model governance | §3.3 Context | context pipeline before model call |
| 3. Semantic compact rebuild | §3.3 Context | COMPASS brief + state restoration |
| 4. Cache-safe fork params | §4.2 Multi-agent | worktree subagent context sharing |
| 5. Default state isolation | §4.2 Multi-agent | opt-in only mutable sharing |
| 6. Layered recovery escalation | §4.6 Reliability | cost-gated recovery branches |
| 7. Continuation-first truncation | §4.6 Reliability | no-polite-recap meta messages |
| 8. Recovery circuit breakers | §4.6 Reliability | consecutive failure counters |
| 9. Recovery self-recovery | §4.6 Reliability | compact's own PTL fallback |
| 10. Coordinator synthesis | §4.2 Multi-agent | digest-don't-forward rule |
| 11. Independent verification | §4.5 Verification | separate verifier role |
| 12. Memory index/body split | §3.4 Memory | MEMORY.md index + topic files |
| 13. Session continuation briefs | §3.4 Memory | structured templates with budgets |
| 14. Verify-first rollout | §5 Team Adoption | verification def before skill count |
| 15. Prompt precedence chain | §2.1 Skills | 5-layer fixed-order assembly |

---

## Anti-Pattern Catalog (from the book)

| Anti-Pattern | Why It Fails | Book Section |
|-------------|--------------|--------------|
| "Model is a teammate" | Models lack stable responsibility, accountability, sustained judgment | Ch.1, Ch.9 |
| "One universal prompt" | Conflicts emerge, behavior becomes unpredictable | Ch.2 |
| "Latest write wins" prompt order | Degrades into graffiti board | Ch.2 §2.3 |
| Boolean (yes/no) permissions | Can't express "system should not decide on behalf of user" | Ch.4 §4.4-4.5 |
| Bash treated identically to ReadTool | Bash is a risk amplifier, not a normal tool | Ch.4 §4.7 |
| "More context is always better" | Context is expensive, inflation-prone, self-polluting budget | Ch.5 §5.1 |
| "Under normal conditions" assumption | Errors are structurally present, not exceptional | Ch.6 §6.1 |
| One-size recovery hammer | Destroys fine-grained context; escalates cost unnecessarily | Ch.6 §6.2 |
| Retry without circuit breaker | Burns API calls on repeated failure (historically documented) | Ch.6 §6.5 |
| Multi-agent = parallel copies of same agent | Parallelized disorder, not uncertainty partitioning | Ch.7 §7.8 |
| Coordinator as forwarding service | Understanding outsourced, synthesis never happens | Ch.7 §7.4 |
| Verification = implementation self-check | "Feels fine" impersonates "verified correct" | Ch.7 §7.5 |
| Build skills before defining verification | Speeds up ambiguity; satisfies weakest bar in the room | Ch.8 §8.4 |
| CLAUDE.md as encyclopedic bulletin board | Loses stability and credibility; team stops knowing what's current | Ch.8 §8.3 |
| Hooks as first automation step | Moving parts exceed team readiness; debugging costs exceed replaced manual step | Ch.8 §8.7 |
