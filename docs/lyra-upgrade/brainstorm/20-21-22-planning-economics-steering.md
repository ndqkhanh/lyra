# Brainstorm — Planning (§4.20) + Economics (§4.21) + Steering (§4.22)

> Run 1 — June 3, 2026 | Combined brainstorm

---

## §4.20 Planning & Reasoning Layer

### Breakthrough Idea #1: MCTS + Value Agent for Code Tasks (SWE-Search Pattern)

**Sources Fused:** SWE-Search (ICLR 2025) + AFlow (ICLR 2025) + MC-DML (ICLR 2025) + Tree of Thoughts

**Core Mechanism:**
- **Search Tree:** Nodes = agent states (current code + context), Edges = agent actions (edit file, run test, search repo)
- **Value Agent:** Learns to estimate the value of being in a state (will this lead to a solution?)
- **MCTS:** Select → Expand → Simulate → Backpropagate over the action space
- **Hindsight Feedback (SWE-Search):** When a solution is found, replay the path and update value estimates (+23% improvement)
- **AFlow Extension:** Nodes can be ENTIRE WORKFLOWS (not just individual actions) — MCTS over workflow designs
- **MC-DML Memory:** In-trial memory (what worked in this search) + cross-trial memory (what worked in past similar searches)
- **Cost-Augmented MCTS:** Budget-aware — stop expanding unpromising branches early

**Integration:** Planning layer sits above memory + skills, feeds action decisions to agents via the workflow engine.

**Impact:** 5 | **Effort:** 5 | **Risk:** Medium

### Breakthrough Idea #2: IdleSpec — Speculative Planning During Tool Wait

**Sources Fused:** IdleSpec (2605.22154) + Speculative Decoding (2211.17192)

**Core Mechanism:**
- While agent waits for tool results (Bash, WebFetch), speculatively plan next actions
- Plan tree: root = current state, branches = possible tool outcomes → planned responses
- When tool result arrives, traverse the tree → find matching branch → execute pre-planned action
- 2-3× effective agent loop speedup
- Memory: cache common plans for repeated task patterns

**Impact:** 4 | **Effort:** 3 | **Risk:** Low

---

## §4.21 Performance & Cost Economics

### Breakthrough Idea #1: Prompt-Cache Hit-Rate Strategy Across the Fleet

**Core Mechanism:**
- Anthropic prompt cache: 5-min TTL, 90% cost reduction on cache hits
- Fleet strategy: batch similar queries within cache windows
- Static prefix: Lyra system prompt + skill frontmatter → always cached (never changes within session)
- Dynamic caching: when multiple sessions run similar tasks, stagger starts so later sessions hit the cache
- Token accounting per workflow: `budget.total`, `budget.spent()`, `budget.remaining()`
- Amdahl's Law for agents: parallelism stops paying when coordination overhead > speedup
- Cache-hit rate dashboard in /config → tune prefix design for hit rate

**Impact:** 4 | **Effort:** 3 | **Risk:** Low

### Breakthrough Idea #2: Speculative Decoding for Cheap Model Acceleration

**Sources Fused:** Speculative Decoding (ICML 2023) + Knowledge Access paper

**Core Mechanism:**
- Cheap draft model (Haiku) generates candidate tokens → expensive model (Sonnet/Opus) verifies in parallel
- 2-3× latency reduction at identical quality
- Most effective for: structured outputs (JSON), code generation, repetitive patterns
- Provider-dependent: only works when both draft and target models are from same provider with compatible tokenizers
- Lyra strategy: enable when both models are Anthropic; fall back to single-model inference otherwise

**Impact:** 3 | **Effort:** 4 | **Risk:** Medium

---

## §4.22 Human Steering & Interruptibility

### Breakthrough Idea #1: Agent View Steer-by-Exception Pattern

**Sources Fused:** Claude Code Agent View + COMPASS Meta-Thinker interventions

**Core Mechanism:**
- **Peek Panel:** See latest output / current question / PRs without attaching. Multiple-choice hotkeys for common replies.
- **Tab Suggested Reply:** Agent drafts a suggested human response (e.g., "Yes, deploy to staging"). Human presses Tab to accept/edit.
- **Attach/Detach:** Enter full conversation without stopping the session. `←` returns to fleet view.
- **Mid-Run Interruption:** Human can inject a message at any time ("also check the error logs", "stop, that approach is wrong")
- **Undo/Rewind:** Agent actions are reversible — undo last N actions, rewind to checkpoint
- **Trust Calibration:** Show confidence alongside suggestions. Low confidence → human should verify. High confidence → "Lyra is 92% confident in this."

### Breakthrough Idea #2: Natural-Language Correction Loop

**Core Mechanism:**
- Human says: "No, use async/await instead of callbacks"
- Agent: parses correction → identifies the SPECIFIC decision being corrected → applies correction → re-executes from that point
- Correction memory: common corrections become learned preferences (stored in semantic memory §4.2)
- Preference learning over time: "You always correct me to use async/await → I'll default to that for Python tasks"

**Impact:** 4 | **Effort:** 3 | **Risk:** Low

---

## Expert Check

**Senior Planning Specialist:** "SWE-Search's hindsight feedback (+23%) is the key insight for the planning layer. Most MCTS implementations don't learn from past searches. MC-DML's in-trial + cross-trial memory makes this even stronger."

**Senior Performance Engineer:** "The prompt-cache hit-rate strategy is where the real money is saved. A well-designed static prefix that hits cache 90% of the time saves more than any model routing optimization."

**Senior UX Designer:** "Steer-by-exception is the right interaction model for autonomous agents. Users don't want to babysit — they want to be notified when their judgment is needed. The key design principle: never block the agent on human input that could have been anticipated."
