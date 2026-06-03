# Brainstorm — Full Autonomy (§4.14)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Breakthrough Idea #1: Unattended Session Loop with Steer-by-Exception

**Sources Fused:** Claude Code Agent View + continuous-claude + COMPASS hierarchical oversight

**Core Mechanism:**
- Sessions run unattended via the supervisor daemon (§4.13) — no terminal required
- Continuous-operation loop: agent works → reports progress → checks for human input → continues
- Cheap-model row summaries (Haiku-class, refreshed ≤1/15s) so the loop reports status without big-model tokens
- COMPASS-inspired hierarchy:
  - **Main Agent** — tactical execution
  - **Meta-Thinker** — strategic oversight, decides: continue / pause / escalate to human
  - **Context Manager** — keeps concise progress briefs
- Human steers by exception: peek at fleet view, reply to Needs-Input sessions, attach only when needed
- Idle-stop: unattached sessions auto-pause after configurable timeout (default 1h), respawn on next peek

**Why It Beats Baseline:** Lyra requires an active terminal. Sessions die when terminal closes.
**Impact:** 5 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #2: Speculative Planning During Tool-Waiting Idle Time

**Sources Fused:** IdleSpec (2605.22154) + MetaClaw opportunistic fine-tuning

**Core Mechanism:**
- While waiting for tool results (Bash, WebFetch, etc.), the agent speculatively plans next steps
- IdleSpec: 2-3× agent loop speedup by overlapping planning with tool execution
- Three planning modes during idle:
  1. **Next-action prediction:** What will I do if the tool succeeds? If it fails?
  2. **Subtask decomposition:** If this result is complex, how will I break it down?
  3. **Memory retrieval:** What do I already know about this domain?
- When tool result arrives, planning is already done → immediate action
- MetaClaw integration: if idle > 5 minutes, opportunistically fine-tune on recent successes

**Why It Beats Baseline:** Lyra blocks synchronously on tool calls — no parallelism.
**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: Autonomy Escalation Ladder with Confidence Gating

**Sources Fused:** "LLMs Must Be Taught" (NeurIPS 2024) + Q-DAPS difficulty estimation + Agent View permission guard

**Core Mechanism:**
- Autonomy is NOT binary (on/off) — it's a LADDER with escalating privileges:
  - **Level 0 — Attended Only:** Human in the loop for every action (current Lyra)
  - **Level 1 — Read-Only Auto:** Agent can read/search without approval; writes need confirmation
  - **Level 2 — Low-Risk Auto:** Non-mutating actions auto-approved; mutating actions need confirmation
  - **Level 3 — Time-Boxed Auto:** All actions auto-approved for N minutes; human can interrupt
  - **Level 4 — Full Auto:** All actions auto-approved; human monitors by exception
- **Confidence Gate:** Agent must demonstrate calibrated confidence (Q-DAPS entropy + "Must Be Taught" calibration) above threshold before level-up
- **Permission Guard:** Levels 2+ require prior explicit human accept (Agent View security guardrail)
- **Auto-Downgrade:** If agent makes N mistakes in M minutes, auto-downgrade one level

**Why It Beats Baseline:** Lyra has no autonomy — every action needs human. The ladder makes autonomy incremental and reversible.
**Impact:** 5 | **Effort:** 3 | **Risk:** Low

---

## Expert Check

**Senior SRE:** "The autonomy escalation ladder (Idea #3) is the right approach. 'Full auto' is terrifying as a binary — a ladder with auto-downgrade makes it manageable. The confidence gate is essential."

**Senior Safety Engineer:** "The Agent View permission guardrail is the key safety mechanism. No auto-downgrade algorithm is perfect — the human must retain the ability to revoke autonomy at any time."

**Adversarial Skeptic:** "IdleSpec (Idea #2) sounds great but adds significant complexity to the agent loop. Is the 2-3× speedup measured on real agent workloads or synthetic benchmarks? Validate on Lyra-specific tasks before committing."

**Resolution:** Idea #3 (autonomy ladder) is the (A) parity tier — it's the minimum viable autonomy. Idea #1 (unattended loop) depends on §4.13 supervisor. Idea #2 (IdleSpec) is a Phase 2 optimization — validate on Lyra workloads first.
