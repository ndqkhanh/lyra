# Brainstorm — Context Optimization & Auto-Compaction (§4.3)

> Run 1 — June 3, 2026 | ≥3 cross-source breakthrough ideas required

## Breakthrough Idea #1: Anthropic 3-Strategy Framework + lean-ctx Output Compression

**Sources Fused:** Anthropic Context Engineering + lean-ctx + COMPASS hierarchical

**Core Mechanism:**
- **Strategy 1 — Compaction:** When context reaches 80% of window, summarize conversation preserving architectural decisions, unresolved bugs, implementation details. Continue with compressed context + 5 most recently accessed files.
- **Strategy 2 — Structured Note-Taking:** Agent maintains NOTES.md (or graph memory) outside context. After compaction, reads notes to re-establish coherence. No special infrastructure — just file read/write.
- **Strategy 3 — Sub-Agent Architectures:** Heavy exploration work isolated in sub-agents. Sub-agent uses 10K+ tokens, returns 1-2K token summary. Context separation of concerns.
- **lean-ctx Integration:** Shell hook compresses CLI output BEFORE it reaches the LLM. Token Dense Dialect for tool output shorthand. 89-99% token reduction on tool outputs.

**Impact:** 5 | **Effort:** 3 | **Risk:** Low

---

## Breakthrough Idea #2: COMPASS Hierarchical Context with Meta-Thinker Interventions

**Sources Fused:** COMPASS (2510.08790) + ACON adaptive compression

**Core Mechanism:**
- **Main Agent** — tactical execution with full context
- **Meta-Thinker** — strategic oversight, reads compressed progress briefs (not full context), issues interventions when the main agent is stuck/looping/off-track
- **Context Manager** — maintains concise progress briefs (ACON: 26-54% compression), injects only when relevant
- Meta-Thinker runs on a cheaper model (Haiku-class) to minimize cost
- Intervention types: "you're repeating yourself", "consider approach X", "escalate to human"

**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Breakthrough Idea #3: ExtAgents Distributed Context for Ultra-Long Documents

**Sources Fused:** ExtAgents (2505.21471) + MemAgent segment processing

**Core Mechanism:**
- When a task requires processing more data than fits in context (e.g., a 1M-token codebase), distribute across agents:
  - Each agent receives a segment of the input
  - Agents process independently, return structured findings
  - Orchestrator synthesizes findings
- MemAgent segment processing: long text processed in segments, memory overwrite strategy (newer relevant info overwrites older), DAPO optimization
- Avoids context-extension information loss (no long-context training needed)
- ∞Bench+ benchmark target: multi-hop QA over massive documents

**Impact:** 4 | **Effort:** 4 | **Risk:** Medium

---

## Expert Check

**Senior AI Engineer:** "Idea #1 (Anthropic 3-strategy + lean-ctx) is the immediate win. Compaction + note-taking + sub-agents covers 90% of context problems. lean-ctx's output compression is the highest-ROI single change — 89-99% token reduction on tool output."

**Senior Performance Engineer:** "The 'less is more' principle from Anthropic should drive everything. Start Lyra's system prompt at 15 lines, tools at 3, examples at 2 canonical ones. Add only what evals show is needed. Every token competes for attention."

**Adversarial Skeptic:** "COMPASS (Idea #2) adds a Meta-Thinker that itself consumes context. Does the overhead of running a second model pay for itself in improved main-agent performance? Prove on Lyra-specific long-horizon tasks."

**Resolution:** Idea #1 is the (A) parity tier — ship immediately. Idea #2 is a Phase 2 optimization — validate on long-horizon Lyra tasks. Idea #3 is for ultra-long document processing — niche but powerful.
